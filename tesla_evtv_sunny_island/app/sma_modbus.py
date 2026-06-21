"""SMA Sunny Island Modbus register map and decoding (SMA Modbus profile, unit ID 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Documented SMA register addresses (decimal). Read 2 registers for 32-bit values.
REGISTERS: dict[str, dict[str, Any]] = {
    "active_power": {"address": 30775, "type": "s32", "scale": 1, "unit": "W"},
    "battery_current": {"address": 30843, "type": "s32", "scale": 0.001, "unit": "A"},
    "battery_soc": {"address": 30845, "type": "u32", "scale": 1, "unit": "%"},
    "battery_temp": {"address": 30849, "type": "s32", "scale": 1, "unit": "°C"},
    "battery_voltage": {"address": 30851, "type": "u32", "scale": 0.01, "unit": "V"},
    "grid_purchase_power": {"address": 30865, "type": "s32", "scale": 1, "unit": "W"},
    "grid_feed_in_power": {"address": 30867, "type": "s32", "scale": 1, "unit": "W"},
    "system_state": {"address": 30201, "type": "u32", "scale": 1, "unit": None},
}

# Map modbus keys → mqtt_discovery sunny_island sensor keys where applicable
MQTT_KEY_MAP = {
    "battery_voltage": "dc_voltage",
    "battery_current": "dc_current",
    "active_power": "inverter_power",
    "grid_purchase_power": "grid_power",
    "grid_feed_in_power": "grid_feed_in_power",
    "battery_soc": "si_battery_soc",
    "battery_temp": "si_battery_temp",
    "system_state": "system_state",
}

# Modbus values in W → publish as kW for these MQTT keys
KW_KEYS = {"grid_power", "inverter_power", "grid_feed_in_power"}


@dataclass
class ModbusConfig:
    enabled: bool
    mode: str  # tcp or rtu
    host: str
    port: int
    unit_id: int
    serial_port: str
    baudrate: int
    poll_interval: float


def decode_registers(registers: list[int], reg_type: str) -> int | None:
    if len(registers) < 2:
        return None
    value = (registers[0] << 16) | registers[1]
    if reg_type == "s32" and value >= 0x80000000:
        value -= 0x100000000
    if value in (0xFFFFFFFF, -2147483648, 2147483647):
        return None  # SMA NaN / invalid
    return value


def scale_value(raw: int | None, scale: float) -> float | None:
    if raw is None:
        return None
    return round(raw * scale, 3 if scale < 1 else 1)


def poll_all(client, unit_id: int) -> dict[str, float | int | None]:
    """Read all configured registers. Tries holding then input registers."""
    from pymodbus.exceptions import ModbusException

    out: dict[str, float | int | None] = {}
    for key, meta in REGISTERS.items():
        address = meta["address"]
        raw = None
        for method in ("read_holding_registers", "read_input_registers"):
            try:
                fn = getattr(client, method)
                result = fn(address=address, count=2, slave=unit_id)
                if result.isError():
                    continue
                raw = decode_registers(list(result.registers), meta["type"])
                if raw is not None:
                    break
            except (ModbusException, AttributeError, TypeError):
                # pymodbus 3.x uses device_id instead of slave on some versions
                try:
                    fn = getattr(client, method)
                    result = fn(address=address, count=2, device_id=unit_id)
                    if not result.isError():
                        raw = decode_registers(list(result.registers), meta["type"])
                        if raw is not None:
                            break
                except Exception:
                    pass
        out[key] = scale_value(raw, meta["scale"])
    return out
