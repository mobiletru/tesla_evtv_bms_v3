"""Home Assistant MQTT discovery for configurable BMS and Sunny Island sensors."""

from __future__ import annotations

import json
import os
from typing import Any

# BMS metrics from EVTV UDP
BMS_SENSORS: dict[str, dict[str, Any]] = {
    "state_of_charge": {"name": "State of Charge", "unit": "%", "device_class": "battery", "group": "pack"},
    "volts": {"name": "Pack Voltage", "unit": "V", "device_class": "voltage", "group": "pack"},
    "current": {"name": "Pack Current", "unit": "A", "device_class": "current", "group": "pack"},
    "power": {"name": "Pack Power", "unit": "W", "device_class": "power", "group": "pack"},
    "lowest_cell": {"name": "Lowest Cell", "unit": "V", "device_class": "voltage", "group": "cells"},
    "highest_cell": {"name": "Highest Cell", "unit": "V", "device_class": "voltage", "group": "cells"},
    "average_cell": {"name": "Average Cell", "unit": "V", "device_class": "voltage", "group": "cells"},
    "max_temp": {"name": "Max Temperature", "unit": "°F", "device_class": "temperature", "group": "temps"},
    "min_temp": {"name": "Min Temperature", "unit": "°F", "device_class": "temperature", "group": "temps"},
    "battery_status": {"name": "Battery Status", "unit": None, "device_class": None, "group": "status"},
}

# Outbound SMA closed-loop limits (computed before CAN transmit)
SMA_LIMIT_SENSORS: dict[str, dict[str, Any]] = {
    "charge_voltage": {"name": "SMA Charge Voltage", "unit": "V", "device_class": "voltage"},
    "charge_current": {"name": "SMA Charge Current Limit", "unit": "A", "device_class": "current"},
    "discharge_current": {"name": "SMA Discharge Current Limit", "unit": "A", "device_class": "current"},
    "discharge_voltage": {"name": "SMA Discharge Voltage Limit", "unit": "V", "device_class": "voltage"},
}

# Sunny Island metrics from CAN watch (decoded field → sensor key)
SUNNY_ISLAND_SENSORS: dict[str, dict[str, Any]] = {
    "dc_voltage": {"name": "DC Voltage", "unit": "V", "device_class": "voltage", "can_id": 0x305, "field": "dc_voltage_v"},
    "dc_current": {"name": "DC Current", "unit": "A", "device_class": "current", "can_id": 0x305, "field": "dc_current_a"},
    "grid_power": {"name": "Grid Power", "unit": "kW", "device_class": "power", "can_id": 0x300, "field": "master_grid_kw"},
    "grid_power_slave": {"name": "Grid Power Slave", "unit": "kW", "device_class": "power", "can_id": 0x300, "field": "slave_grid_kw"},
    "inverter_power": {"name": "Inverter Power", "unit": "kW", "device_class": "power", "can_id": 0x301, "field": "master_inverter_kw"},
    "inverter_power_slave": {"name": "Inverter Power Slave", "unit": "kW", "device_class": "power", "can_id": 0x301, "field": "slave_inverter_kw"},
    "load_power": {"name": "Load Power", "unit": "kW", "device_class": "power", "can_id": 0x308, "field": "load_power_kw"},
    "input_voltage": {"name": "Input Voltage", "unit": "V", "device_class": "voltage", "can_id": 0x309, "field": "input_voltage_v"},
    "grid_frequency": {"name": "Grid Frequency", "unit": "Hz", "device_class": None, "can_id": 0x309, "field": "grid_freq_hz"},
    "output_voltage": {"name": "Output Voltage", "unit": "V", "device_class": "voltage", "can_id": 0x304, "field": "output_voltage_v"},
}

# Sunny Island via Modbus RS485 / TCP (SMA profile unit ID 3)
MODBUS_SI_SENSORS: dict[str, dict[str, Any]] = {
    "dc_voltage": {"name": "DC Voltage (Modbus)", "unit": "V", "device_class": "voltage"},
    "dc_current": {"name": "DC Current (Modbus)", "unit": "A", "device_class": "current"},
    "inverter_power": {"name": "Inverter Power (Modbus)", "unit": "kW", "device_class": "power"},
    "grid_power": {"name": "Grid Power (Modbus)", "unit": "kW", "device_class": "power"},
    "grid_feed_in_power": {"name": "Grid Feed-in (Modbus)", "unit": "kW", "device_class": "power"},
    "si_battery_soc": {"name": "SI Battery SOC (Modbus)", "unit": "%", "device_class": "battery"},
    "si_battery_temp": {"name": "SI Battery Temp (Modbus)", "unit": "°C", "device_class": "temperature"},
    "system_state": {"name": "SI System State", "unit": None, "device_class": None},
}

BMS_DEVICE = {
    "manufacturer": "EVTV",
    "model": "Tesla BMS V3",
}

SI_DEVICE = {
    "manufacturer": "SMA",
    "model": "Sunny Island 6048",
}


def _parse_list_env(name: str, default: list[str]) -> set[str]:
    raw = os.environ.get(name, "")
    if not raw:
        return set(default)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return set(str(x) for x in parsed)
    except json.JSONDecodeError:
        pass
    return set(x.strip() for x in raw.split(",") if x.strip())


def load_publish_config() -> dict[str, Any]:
    """Read enabled metric sets from environment (bashio JSON lists)."""
    return {
        "publish_mqtt": os.environ.get("PUBLISH_MQTT", "true").lower() == "true",
        "bms_device": os.environ.get("DEVICE_NAME", "tesla_bms"),
        "si_device": os.environ.get("SUNNY_ISLAND_DEVICE_NAME", "sunny_island"),
        "bms": _parse_list_env(
            "PUBLISH_BMS",
            [
                "state_of_charge", "volts", "current", "power",
                "lowest_cell", "highest_cell", "average_cell",
                "max_temp", "min_temp", "battery_status",
            ],
        ),
        "sma_limits": _parse_list_env(
            "PUBLISH_SMA_LIMITS",
            ["charge_voltage", "charge_current", "discharge_current", "discharge_voltage"],
        ),
        "sunny_island": _parse_list_env(
            "PUBLISH_SUNNY_ISLAND",
            ["dc_voltage", "dc_current", "grid_power", "inverter_power", "load_power", "input_voltage"],
        ),
        "modbus_enabled": os.environ.get("MODBUS_ENABLED", "false").lower() == "true",
        "modbus": _parse_list_env(
            "PUBLISH_MODBUS",
            [
                "dc_voltage", "dc_current", "inverter_power", "grid_power",
                "grid_feed_in_power", "si_battery_soc", "si_battery_temp", "system_state",
            ],
        ),
    }


def _device_block(device_id: str, name: str, meta: dict) -> dict:
    return {
        "identifiers": [device_id],
        "name": name,
        "manufacturer": meta["manufacturer"],
        "model": meta["model"],
    }


def _discovery_payload(
    object_id: str,
    name: str,
    state_topic: str,
    unique_id: str,
    device: dict,
    unit: str | None = None,
    device_class: str | None = None,
) -> dict:
    payload: dict[str, Any] = {
        "name": name,
        "state_topic": state_topic,
        "unique_id": unique_id,
        "object_id": object_id,
        "device": device,
    }
    if unit:
        payload["unit_of_measurement"] = unit
    if device_class:
        payload["device_class"] = device_class
    return payload


def publish_all_discovery(client, cfg: dict[str, Any]) -> None:
    """Publish MQTT discovery for all enabled sensors."""
    if not cfg["publish_mqtt"]:
        return

    bms_id = cfg["bms_device"]
    si_id = cfg["si_device"]
    bms_dev = _device_block(bms_id, "Tesla BMS", BMS_DEVICE)
    si_dev = _device_block(si_id, "Sunny Island", SI_DEVICE)

    for key in cfg["bms"]:
        if key not in BMS_SENSORS:
            continue
        meta = BMS_SENSORS[key]
        topic = f"homeassistant/sensor/{bms_id}/{key}/config"
        payload = _discovery_payload(
            object_id=key,
            name=meta["name"],
            state_topic=f"tesla_evtv/{bms_id}/{key}",
            unique_id=f"{bms_id}_{key}",
            device=bms_dev,
            unit=meta["unit"],
            device_class=meta["device_class"],
        )
        client.publish(topic, json.dumps(payload), retain=True)

    for key in cfg["sma_limits"]:
        if key not in SMA_LIMIT_SENSORS:
            continue
        meta = SMA_LIMIT_SENSORS[key]
        object_id = f"sma_{key}"
        topic = f"homeassistant/sensor/{bms_id}/{object_id}/config"
        payload = _discovery_payload(
            object_id=object_id,
            name=meta["name"],
            state_topic=f"tesla_evtv/{bms_id}/sma/{key}",
            unique_id=f"{bms_id}_{object_id}",
            device=bms_dev,
            unit=meta["unit"],
            device_class=meta["device_class"],
        )
        client.publish(topic, json.dumps(payload), retain=True)

    for key in cfg["sunny_island"]:
        if key not in SUNNY_ISLAND_SENSORS:
            continue
        meta = SUNNY_ISLAND_SENSORS[key]
        topic = f"homeassistant/sensor/{si_id}/{key}/config"
        payload = _discovery_payload(
            object_id=key,
            name=meta["name"],
            state_topic=f"tesla_evtv/{si_id}/{key}",
            unique_id=f"{si_id}_{key}",
            device=si_dev,
            unit=meta["unit"],
            device_class=meta["device_class"],
        )
        client.publish(topic, json.dumps(payload), retain=True)

    if cfg.get("modbus_enabled"):
        for key in cfg.get("modbus", set()):
            if key not in MODBUS_SI_SENSORS:
                continue
            meta = MODBUS_SI_SENSORS[key]
            topic = f"homeassistant/sensor/{si_id}/{key}/config"
            payload = _discovery_payload(
                object_id=key,
                name=meta["name"],
                state_topic=f"tesla_evtv/{si_id}/{key}",
                unique_id=f"{si_id}_modbus_{key}",
                device=si_dev,
                unit=meta["unit"],
                device_class=meta["device_class"],
            )
            client.publish(topic, json.dumps(payload), retain=True)


def extract_sunny_island_values(decoded: dict) -> dict[str, Any]:
    """Map a decoded CAN frame to flat Sunny Island sensor values."""
    values = {}
    can_id = decoded.get("can_id")
    for key, meta in SUNNY_ISLAND_SENSORS.items():
        if meta["can_id"] != can_id:
            continue
        field = meta["field"]
        val = decoded.get(field)
        if val is not None:
            values[key] = val
    return values


def sma_limits_to_mqtt(limits: dict[str, float]) -> dict[str, float]:
    """Map compute_closed_loop_limits keys to MQTT sensor keys."""
    return {
        "charge_voltage": limits["charge_voltage"],
        "charge_current": limits["charge_current_limit"],
        "discharge_current": limits["discharge_current_limit"],
        "discharge_voltage": limits["discharge_voltage_limit"],
    }
