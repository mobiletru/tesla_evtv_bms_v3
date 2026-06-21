#!/usr/bin/env python3
"""Home Assistant OS add-on: EVTV BMS UDP -> MQTT sensors + Sunny Island CAN on can0."""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import sys
import threading
import time

import can
import paho.mqtt.client as mqtt

from app.pack_config import compute_pack_settings
from app.parser import enrich_values, parse_udp_packet
from app.sma_can import SMA_MESSAGE_INTERVAL, build_sma_messages

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("tesla_evtv_haos")


SENSOR_MAP = {
    "state_of_charge": ("%", "battery"),
    "volts": ("V", "voltage"),
    "current": ("A", "current"),
    "power": ("W", "power"),
    "lowest_cell": ("V", "voltage"),
    "highest_cell": ("V", "voltage"),
    "average_cell": ("V", "voltage"),
    "max_temp": ("°F", "temperature"),
    "min_temp": ("°F", "temperature"),
    "battery_status": (None, None),
}


class Bridge:
    def __init__(self) -> None:
        self.device = os.environ.get("DEVICE_NAME", "tesla_bms")
        self.udp_port = int(os.environ.get("UDP_PORT", "6850"))
        self.can_iface = os.environ.get("CAN_INTERFACE", "can0")
        self.can_bitrate = int(os.environ.get("CAN_BITRATE", "500000"))
        self.sma_enabled = os.environ.get("SMA_ENABLED", "true").lower() == "true"
        self.invert_current = os.environ.get("INVERT_CURRENT", "false").lower() == "true"
        self.setup_can = os.environ.get("SETUP_CAN", "true").lower() == "true"

        pack = compute_pack_settings(
            int(os.environ.get("MODULE_COUNT", "36")),
            int(os.environ.get("MODULES_IN_SERIES", "2")),
            float(os.environ.get("MIN_CELL_VOLTS", "3.2")),
            float(os.environ.get("MAX_CELL_VOLTS", "4.1")),
        )
        pack["min_cell_volts"] = float(os.environ.get("MIN_CELL_VOLTS", "3.2"))
        pack["max_cell_volts"] = float(os.environ.get("MAX_CELL_VOLTS", "4.1"))
        pack["charge_current_limit"] = float(os.environ.get("CHARGE_CURRENT", "100"))
        pack["discharge_current_limit"] = float(os.environ.get("DISCHARGE_CURRENT", "100"))
        pack["invert_current"] = self.invert_current
        self.config = pack
        self.values: dict = {}
        self._lock = threading.Lock()
        self._bus: can.Bus | None = None
        self._mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._setup_mqtt()

    def _setup_mqtt(self) -> None:
        host = os.environ.get("MQTT_HOST", "core-mosquitto")
        port = int(os.environ.get("MQTT_PORT", "1883"))
        user = os.environ.get("MQTT_USER", "")
        password = os.environ.get("MQTT_PASSWORD", "")
        if user:
            self._mqtt.username_pw_set(user, password)
        self._mqtt.connect(host, port, 60)
        self._mqtt.loop_start()
        log.info("MQTT connected to %s:%s", host, port)

    def setup_can_interface(self) -> None:
        if not self.setup_can:
            log.info("Skipping CAN setup (SETUP_CAN=false)")
            return
        cmds = [
            ["ip", "link", "set", self.can_iface, "down"],
            ["ip", "link", "set", self.can_iface, "type", "can", "bitrate", str(self.can_bitrate)],
            ["ip", "link", "set", self.can_iface, "up"],
        ]
        for cmd in cmds:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                log.warning("CAN setup command failed: %s -> %s", cmd, result.stderr.strip())
        log.info("CAN interface %s configured at %s bps", self.can_iface, self.can_bitrate)

    def _ensure_bus(self) -> None:
        if self._bus is None:
            self._bus = can.interface.Bus(interface="socketcan", channel=self.can_iface)

    def publish_discovery(self) -> None:
        for key, (unit, device_class) in SENSOR_MAP.items():
            topic = f"homeassistant/sensor/{self.device}/{key}/config"
            payload = {
                "name": f"{self.device} {key.replace('_', ' ').title()}",
                "state_topic": f"tesla_evtv/{self.device}/{key}",
                "unique_id": f"{self.device}_{key}",
                "device": {
                    "identifiers": [self.device],
                    "name": self.device,
                    "manufacturer": "EVTV",
                    "model": "Tesla BMS V3 + Sunny Island",
                },
            }
            if unit:
                payload["unit_of_measurement"] = unit
            if device_class:
                payload["device_class"] = device_class
            self._mqtt.publish(topic, json.dumps(payload), retain=True)

    def publish_state(self, values: dict) -> None:
        for key in SENSOR_MAP:
            if key in values and values[key] is not None:
                self._mqtt.publish(f"tesla_evtv/{self.device}/{key}", str(values[key]), retain=True)

    def send_sma(self) -> None:
        if not self.sma_enabled:
            return
        with self._lock:
            if self.values.get("state_of_charge") is None:
                return
            values = enrich_values(self.values, self.config)
            messages = build_sma_messages(values, self.config)
        self._ensure_bus()
        for can_id, payload in messages:
            msg = can.Message(
                arbitration_id=can_id,
                data=payload[:8].ljust(8, b"\x00"),
                is_extended_id=False,
            )
            self._bus.send(msg)
            time.sleep(SMA_MESSAGE_INTERVAL)

    def udp_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", self.udp_port))
        log.info("Listening for EVTV BMS UDP on port %s", self.udp_port)
        while True:
            data, addr = sock.recvfrom(1024)
            parsed = parse_udp_packet(data)
            if not parsed:
                continue
            with self._lock:
                self.values.update(parsed)
                values = enrich_values(self.values, self.config)
            self.publish_state(values)
            log.debug("UDP update from %s: %s", addr, parsed)

    def sma_loop(self) -> None:
        log.info("SMA Sunny Island CAN output on %s (enabled=%s)", self.can_iface, self.sma_enabled)
        while True:
            try:
                self.send_sma()
            except Exception as err:
                log.exception("SMA transmit error: %s", err)
                if self._bus:
                    self._bus.shutdown()
                    self._bus = None
                time.sleep(2.0)

    def run(self) -> None:
        parallel = self.config["module_count"] // self.config["modules_in_series"]
        log.info(
            "Pack: %s modules (2S%sP), %.1f kWh, %.1f V nominal, %s cells in series",
            self.config["module_count"],
            parallel,
            self.config["pack_size"],
            self.config["nominal_voltage"],
            self.config["cells_in_series"],
        )
        self.setup_can_interface()
        self.publish_discovery()
        threading.Thread(target=self.sma_loop, daemon=True).start()
        self.udp_loop()


def main() -> int:
    try:
        Bridge().run()
    except KeyboardInterrupt:
        return 0
    except Exception:
        log.exception("Fatal error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
