"""SMA Sunny WebBox JSON-RPC client (SWebBoxRPC-BA-en-14)."""

from __future__ import annotations

import hashlib
import json
import logging
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

RPC_VERSION = "1.0"
MIN_POLL_INTERVAL = 30.0


@dataclass
class WebBoxConfig:
    enabled: bool = False
    host: str = "192.168.0.168"
    port: int = 80
    mode: str = "http"  # http or udp
    password: str = ""
    poll_interval: float = 30.0
    device_key: str = ""  # auto-discover Sunny Island if empty
    device_name_filter: str = "sunny island"


@dataclass
class WebBoxClient:
    config: WebBoxConfig
    _req_id: int = 0
    _cached_device_key: str = field(default="", init=False)

    def _next_id(self) -> str:
        self._req_id += 1
        return str(self._req_id)

    def _passwd_hash(self) -> str | None:
        if not self.config.password:
            return None
        return hashlib.md5(self.config.password.encode("utf-8")).hexdigest()

    def call(self, proc: str, params: dict | None = None, use_password: bool = False) -> dict:
        payload: dict[str, Any] = {
            "version": RPC_VERSION,
            "proc": proc,
            "id": self._next_id(),
            "format": "JSON",
        }
        if use_password:
            passwd = self._passwd_hash()
            if passwd:
                payload["passwd"] = passwd
        if params:
            payload["params"] = params

        if self.config.mode == "udp":
            return self._call_udp(payload)
        return self._call_http(payload)

    def _call_http(self, payload: dict) -> dict:
        url = f"http://{self.config.host}:{self.config.port}/rpc"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            raise ConnectionError(f"WebBox HTTP {err.code}: {err.read()[:200]}") from err
        except urllib.error.URLError as err:
            raise ConnectionError(f"WebBox unreachable: {err}") from err

        if "error" in data:
            raise RuntimeError(f"WebBox RPC error: {data['error']}")
        return data.get("result", data)

    def _call_udp(self, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(15)
        try:
            sock.sendto(body, (self.config.host, 34268))
            data, _ = sock.recvfrom(65535)
        finally:
            sock.close()
        parsed = json.loads(data.decode("utf-8"))
        if "error" in parsed:
            raise RuntimeError(f"WebBox RPC error: {parsed['error']}")
        return parsed.get("result", parsed)

    def get_plant_overview(self) -> dict[str, str]:
        result = self.call("GetPlantOverview")
        overview = result.get("overview") or []
        out: dict[str, str] = {}
        for item in overview:
            meta = item.get("meta")
            value = item.get("value")
            if meta and value is not None:
                out[str(meta)] = str(value)
        return out

    def get_devices(self) -> list[dict]:
        result = self.call("GetDevices")
        return result.get("devices") or []

    def find_device_key(self, name_filter: str | None = None) -> str | None:
        if self.config.device_key:
            return self.config.device_key
        if self._cached_device_key:
            return self._cached_device_key

        filt = (name_filter or self.config.device_name_filter).lower()

        def walk(devices: list) -> str | None:
            for dev in devices:
                key = (dev.get("key") or "").strip()
                name = (dev.get("name") or "").lower()
                if filt in name or filt.replace(" ", "") in key.lower():
                    return key
                children = dev.get("children")
                if children:
                    found = walk(children)
                    if found:
                        return found
            return None

        key = walk(self.get_devices())
        if key:
            self._cached_device_key = key
            log.info("WebBox auto-discovered device key: %s", key)
        return key

    def get_process_data_channels(self, device_key: str) -> list[str]:
        result = self.call("GetProcessDataChannels", {"device": device_key})
        if isinstance(result, dict):
            channels = result.get(device_key)
            if isinstance(channels, list):
                return [str(c) for c in channels]
        return []

    def get_process_data(self, device_key: str, channels: list[str] | None = None) -> dict[str, str]:
        device_obj: dict[str, Any] = {"key": device_key}
        if channels:
            device_obj["channels"] = channels
        result = self.call("GetProcessData", {"devices": [device_obj]})
        out: dict[str, str] = {}
        for dev in result.get("devices") or []:
            for ch in dev.get("channels") or []:
                meta = ch.get("meta") or ch.get("name")
                value = ch.get("value")
                if meta and value is not None:
                    out[str(meta)] = str(value)
        return out

    def get_parameter(self, device_key: str, channels: list[str] | None = None) -> dict[str, str]:
        device_obj: dict[str, Any] = {"key": device_key}
        if channels:
            device_obj["channels"] = channels
        result = self.call("GetParameter", {"devices": [device_obj]}, use_password=True)
        out: dict[str, str] = {}
        for dev in result.get("devices") or []:
            for ch in dev.get("channels") or []:
                meta = ch.get("meta") or ch.get("name")
                value = ch.get("value")
                if meta is not None:
                    out[str(meta)] = "" if value is None else str(value)
        return out

    def set_parameter(self, device_key: str, channels: list[dict]) -> dict[str, str]:
        """channels: [{"meta": "...", "value": "..."}]"""
        result = self.call(
            "SetParameter",
            {"devices": [{"key": device_key, "channels": channels}]},
            use_password=True,
        )
        out: dict[str, str] = {}
        for dev in result.get("devices") or []:
            for ch in dev.get("channels") or []:
                meta = ch.get("meta") or ch.get("name")
                value = ch.get("value")
                if meta is not None:
                    out[str(meta)] = "" if value is None else str(value)
        return out


# Plant overview meta → MQTT sensor key
OVERVIEW_MAP = {
    "GriPwr": "webbox_plant_power",
    "GriEgyTdy": "webbox_energy_today",
    "GriEgyTot": "webbox_energy_total",
    "OpStt": "webbox_plant_status",
}

# Common Sunny Island process channel metas → MQTT keys
PROCESS_MAP = {
    "Pac": "inverter_power",
    "Udc": "dc_voltage",
    "Idc": "dc_current",
    "BatSOC": "si_battery_soc",
    "BatChrg": "si_battery_soc",
    "BatVtg": "dc_voltage",
    "BatCur": "dc_current",
    "GriPwr": "grid_power",
    "OpStt": "webbox_device_status",
}
