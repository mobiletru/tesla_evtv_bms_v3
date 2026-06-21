#!/usr/bin/env python3
"""Home Assistant OS add-on: EVTV BMS, SMA Sunny Island CAN, live dashboard."""

from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import time

import can
import paho.mqtt.client as mqtt

from app.can_monitor import CanWatchService
from app.can_setup import setup_can_interface
from app.charge_control import compute_closed_loop_limits
from app.live_settings import LiveSettings
from app.modbus_poll import SunnyIslandModbus
from app.mqtt_discovery import load_publish_config, publish_all_discovery, sma_limits_to_mqtt
from app.pack_config import compute_pack_settings
from app.parser import enrich_values, parse_udp_packet
from app.settings_mqtt import SettingsMqtt
from app.sma_can import SMA_MESSAGE_INTERVAL, build_sma_messages
from app.sma_modbus import ModbusConfig
from app.webbox_poll import WebBoxPoller
from app.webbox_rpc import WebBoxConfig
from app.web_dashboard import start_web_dashboard

logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("tesla_evtv_haos")


class Bridge:
    def __init__(self) -> None:
        self.publish_cfg = load_publish_config()
        self.device = self.publish_cfg["bms_device"]
        self.si_device = self.publish_cfg["si_device"]
        self.udp_port = int(os.environ.get("UDP_PORT", "6850"))
        self.can_iface = os.environ.get("CAN_INTERFACE", "can0")
        self.can_bitrate = int(os.environ.get("CAN_BITRATE", "500000"))
        self.invert_current = os.environ.get("INVERT_CURRENT", "false").lower() == "true"
        self.setup_can = os.environ.get("SETUP_CAN", "true").lower() == "true"
        self.can_watch_filter = os.environ.get("CAN_WATCH_FILTER", "sma")
        self.can_watch_summary = float(os.environ.get("CAN_WATCH_SUMMARY_INTERVAL", "30"))
        self.web_enabled = os.environ.get("WEB_ENABLED", "true").lower() == "true"
        self.web_port = int(os.environ.get("WEB_PORT", "8099"))

        self.modbus_cfg = ModbusConfig(
            enabled=self.publish_cfg.get("modbus_enabled", False),
            mode=os.environ.get("MODBUS_MODE", "rtu"),
            host=os.environ.get("MODBUS_HOST", "192.168.1.100"),
            port=int(os.environ.get("MODBUS_PORT", "502")),
            unit_id=int(os.environ.get("MODBUS_UNIT_ID", "3")),
            serial_port=os.environ.get("MODBUS_SERIAL", "/dev/ttyUSB0"),
            baudrate=int(os.environ.get("MODBUS_BAUDRATE", "9600")),
            poll_interval=float(os.environ.get("MODBUS_POLL_INTERVAL", "5")),
        )

        self.webbox_cfg = WebBoxConfig(
            enabled=self.publish_cfg.get("webbox_enabled", False),
            host=os.environ.get("WEBBOX_HOST", "192.168.0.168"),
            port=int(os.environ.get("WEBBOX_PORT", "80")),
            mode=os.environ.get("WEBBOX_MODE", "http"),
            password=os.environ.get("WEBBOX_PASSWORD", ""),
            poll_interval=float(os.environ.get("WEBBOX_POLL_INTERVAL", "30")),
            device_key=os.environ.get("WEBBOX_DEVICE_KEY", ""),
            device_name_filter=os.environ.get("WEBBOX_DEVICE_FILTER", "sunny island"),
        )

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
        pack["sma_enabled"] = os.environ.get("SMA_ENABLED", "true").lower() == "true"
        pack["can_watch_enabled"] = os.environ.get("CAN_WATCH_ENABLED", "true").lower() == "true"

        self.settings = LiveSettings(pack)
        self.config = self.settings.get_config()
        self.values: dict = {}
        self.last_sma_limits: dict = {}
        self.last_modbus: dict = {}
        self.last_webbox: dict = {}
        self._modbus: SunnyIslandModbus | None = None
        self._lock = threading.Lock()
        self._bus: can.Bus | None = None
        self._mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._settings_mqtt: SettingsMqtt | None = None
        self._setup_mqtt()

    @property
    def sma_enabled(self) -> bool:
        return bool(self.settings.get("sma_enabled", True))

    @property
    def can_watch_enabled(self) -> bool:
        return bool(self.settings.get("can_watch_enabled", True))

    def _setup_mqtt(self) -> None:
        host = os.environ.get("MQTT_HOST", "core-mosquitto")
        port = int(os.environ.get("MQTT_PORT", "1883"))
        user = os.environ.get("MQTT_USER", "")
        password = os.environ.get("MQTT_PASSWORD", "")
        if user:
            self._mqtt.username_pw_set(user, password)
        self._mqtt.on_connect = self._on_mqtt_connect
        self._mqtt.on_message = self._on_mqtt_message
        self._mqtt.connect(host, port, 60)
        self._mqtt.loop_start()
        self._settings_mqtt = SettingsMqtt(self._mqtt, self.device, self.settings)
        self.settings.register_callback(self._on_setting_changed)
        log.info("MQTT connected to %s:%s", host, port)

    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        if self._settings_mqtt:
            self._settings_mqtt.subscribe()

    def _on_mqtt_message(self, client, userdata, msg) -> None:
        if self._settings_mqtt:
            self._settings_mqtt.handle_message(msg.topic, msg.payload.decode())

    def _on_setting_changed(self, key: str, value) -> None:
        with self._lock:
            self.config = self.settings.get_config()
        if self._settings_mqtt:
            self._settings_mqtt._publish_setting_state(key, value)
        if key == "can_watch_enabled":
            log.info("CAN watch %s", "enabled" if value else "disabled")

    def apply_settings(self, updates: dict) -> dict:
        errors = self.settings.apply(updates)
        if not errors:
            with self._lock:
                self.config = self.settings.get_config()
            if self._settings_mqtt:
                for key in updates:
                    if key not in errors:
                        self._settings_mqtt._publish_setting_state(key, self.settings.get(key))
        return errors

    def _ensure_bus(self) -> None:
        if self._bus is None:
            self._bus = can.interface.Bus(interface="socketcan", channel=self.can_iface)

    def publish_discovery(self) -> None:
        publish_all_discovery(self._mqtt, self.publish_cfg)
        if self._settings_mqtt:
            self._settings_mqtt.publish_discovery()
            self._settings_mqtt.publish_all_states()

    def publish_state(self, values: dict) -> None:
        if not self.publish_cfg["publish_mqtt"]:
            return
        for key in self.publish_cfg["bms"]:
            if key in values and values[key] is not None:
                self._mqtt.publish(f"tesla_evtv/{self.device}/{key}", str(values[key]), retain=True)

    def _publish_sma_limits(self, limits: dict[str, float]) -> None:
        if not self.publish_cfg["publish_mqtt"]:
            return
        mapped = sma_limits_to_mqtt(limits)
        for key in self.publish_cfg["sma_limits"]:
            if key in mapped:
                self._mqtt.publish(f"tesla_evtv/{self.device}/sma/{key}", str(mapped[key]), retain=True)
        if self._settings_mqtt:
            self._settings_mqtt.publish_sma_output(limits)

    def send_sma(self) -> None:
        if not self.sma_enabled:
            time.sleep(1.0)
            return
        with self._lock:
            if self.values.get("state_of_charge") is None:
                return
            values = enrich_values(self.values, self.config)
            messages = build_sma_messages(values, self.config)
            self.last_sma_limits = compute_closed_loop_limits(values, self.config)
        self._publish_sma_limits(self.last_sma_limits)
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
        log.info("SMA Sunny Island CAN output on %s", self.can_iface)
        while True:
            try:
                self.send_sma()
            except Exception as err:
                log.exception("SMA transmit error: %s", err)
                if self._bus:
                    self._bus.shutdown()
                    self._bus = None
                time.sleep(2.0)

    def can_watch_loop(self) -> None:
        mqtt_client = self._mqtt if self.publish_cfg["publish_mqtt"] else None
        service = CanWatchService(
            iface=self.can_iface,
            filter_mode=self.can_watch_filter,
            summary_interval=self.can_watch_summary,
            mqtt_client=mqtt_client,
            si_device=self.si_device,
            enabled_si_metrics=self.publish_cfg["sunny_island"],
            bus=self._bus,
            enabled_fn=lambda: self.can_watch_enabled,
        )
        service.run()

    def modbus_loop(self) -> None:
        mqtt_client = self._mqtt if self.publish_cfg["publish_mqtt"] else None
        self._modbus = SunnyIslandModbus(
            self.modbus_cfg,
            mqtt_client=mqtt_client,
            si_device=self.si_device,
        )
        original_publish = self._modbus._publish

        def cached_publish(values):
            self.last_modbus = dict(values)
            original_publish(values)

        self._modbus._publish = cached_publish
        self._modbus.run()

    def webbox_loop(self) -> None:
        mqtt_client = self._mqtt if self.publish_cfg["publish_mqtt"] else None
        poller = WebBoxPoller(
            self.webbox_cfg,
            mqtt_client=mqtt_client,
            si_device=self.si_device,
            enabled_metrics=self.publish_cfg.get("webbox"),
        )
        interval = max(30.0, self.webbox_cfg.poll_interval)
        log.info(
            "WebBox RPC http://%s:%s/rpc every %ss",
            self.webbox_cfg.host,
            self.webbox_cfg.port,
            interval,
        )
        while True:
            try:
                self.last_webbox = poller.poll_once()
            except Exception as err:
                log.warning("WebBox poll error: %s", err)
            time.sleep(interval)

    def run(self) -> None:
        cfg = self.config
        parallel = cfg["module_count"] // cfg["modules_in_series"]
        log.info(
            "Pack: %s modules (2S%sP), %.1f kWh, %.1f V nominal, %s cells in series",
            cfg["module_count"],
            parallel,
            cfg["pack_size"],
            cfg["nominal_voltage"],
            cfg["cells_in_series"],
        )
        if self.setup_can:
            setup_can_interface(self.can_iface, self.can_bitrate)
        elif not self.setup_can:
            log.info("Skipping CAN setup (SETUP_CAN=false)")

        self._ensure_bus()
        self.publish_discovery()

        if self.web_enabled:
            start_web_dashboard(self, "0.0.0.0", self.web_port)
            log.info("Live settings dashboard: http://<ha-host>:{}/", self.web_port)

        threading.Thread(target=self.sma_loop, daemon=True).start()
        threading.Thread(target=self.can_watch_loop, daemon=True).start()
        if self.modbus_cfg.enabled:
            threading.Thread(target=self.modbus_loop, daemon=True).start()
        if self.webbox_cfg.enabled:
            threading.Thread(target=self.webbox_loop, daemon=True).start()
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
