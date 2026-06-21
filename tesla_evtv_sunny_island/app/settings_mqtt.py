"""MQTT discovery and command handling for live dashboard settings."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.live_settings import LIVE_FIELDS

if TYPE_CHECKING:
    from app.live_settings import LiveSettings

log = logging.getLogger(__name__)

DEVICE = {
    "identifiers": ["tesla_evtv_settings"],
    "name": "Tesla BMS Settings",
    "manufacturer": "EVTV",
    "model": "Live Settings",
}


class SettingsMqtt:
    def __init__(self, mqtt_client, device_name: str, settings: LiveSettings) -> None:
        self._mqtt = mqtt_client
        self._device = device_name
        self._settings = settings
        self._base = f"tesla_evtv/{device_name}"

    def publish_discovery(self) -> None:
        for key, meta in LIVE_FIELDS.items():
            if meta["type"] == "number":
                component = "number"
                payload = {
                    "name": meta["label"],
                    "unique_id": f"{self._device}_setting_{key}",
                    "command_topic": f"{self._base}/set/{key}",
                    "state_topic": f"{self._base}/settings/{key}",
                    "min": meta["min"],
                    "max": meta["max"],
                    "step": meta["step"],
                    "unit_of_measurement": meta["unit"],
                    "mode": "slider",
                    "device": DEVICE,
                }
            else:
                component = "switch"
                payload = {
                    "name": meta["label"],
                    "unique_id": f"{self._device}_setting_{key}",
                    "command_topic": f"{self._base}/set/{key}",
                    "state_topic": f"{self._base}/settings/{key}",
                    "payload_on": "true",
                    "payload_off": "false",
                    "device": DEVICE,
                }
            topic = f"homeassistant/{component}/{self._device}/setting_{key}/config"
            self._mqtt.publish(topic, json.dumps(payload), retain=True)

        # Read-only live SMA output sensors
        for key, label, unit in (
            ("sma_charge_voltage", "SMA charge voltage", "V"),
            ("sma_charge_current", "SMA charge current", "A"),
            ("sma_discharge_current", "SMA discharge current", "A"),
        ):
            topic = f"homeassistant/sensor/{self._device}/{key}/config"
            payload = {
                "name": label,
                "unique_id": f"{self._device}_{key}",
                "state_topic": f"{self._base}/{key}",
                "unit_of_measurement": unit,
                "device": DEVICE,
            }
            self._mqtt.publish(topic, json.dumps(payload), retain=True)

    def publish_all_states(self) -> None:
        config = self._settings.get_config()
        for key in LIVE_FIELDS:
            value = config.get(key)
            if value is not None:
                self._publish_setting_state(key, value)

    def _publish_setting_state(self, key: str, value) -> None:
        if LIVE_FIELDS[key]["type"] == "switch":
            payload = "true" if value else "false"
        else:
            payload = str(value)
        self._mqtt.publish(f"{self._base}/settings/{key}", payload, retain=True)

    def publish_sma_output(self, limits: dict[str, float]) -> None:
        mapping = {
            "charge_voltage": "sma_charge_voltage",
            "charge_current_limit": "sma_charge_current",
            "discharge_current_limit": "sma_discharge_current",
        }
        for src, dst in mapping.items():
            if src in limits:
                self._mqtt.publish(f"{self._base}/{dst}", str(limits[src]), retain=True)

    def subscribe(self) -> None:
        for key in LIVE_FIELDS:
            self._mqtt.subscribe(f"{self._base}/set/{key}")

    def handle_message(self, topic: str, payload: str) -> None:
        prefix = f"{self._base}/set/"
        if not topic.startswith(prefix):
            return
        key = topic[len(prefix) :]
        if key not in LIVE_FIELDS:
            return
        errors = self._settings.apply({key: payload})
        if errors:
            log.warning("Setting rejected %s: %s", key, errors[key])
            return
        value = self._settings.get(key)
        self._publish_setting_state(key, value)
        log.info("Live setting updated via MQTT: %s = %s", key, value)
