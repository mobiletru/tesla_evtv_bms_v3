"""Decode SMA Sunny Island CAN bus frames (BMS + inverter)."""

from __future__ import annotations

import struct
from typing import Any

INVALID_U16 = 0xFFFF
INVALID_S16 = -32768

# BMS → Sunny Island (closed-loop)
CAN_ID_LIMITS = 0x351
CAN_ID_SOC = 0x355
CAN_ID_MEASUREMENTS = 0x356
CAN_ID_ALARMS = 0x35A
CAN_ID_BMS_ID = 0x35E
CAN_ID_BMS_INFO = 0x35F

# Sunny Island → bus (cluster / telemetry)
CAN_ID_GRID_POWER = 0x300
CAN_ID_INVERTER_POWER = 0x301
CAN_ID_GRID_KVAR = 0x302
CAN_ID_INVERTER_KVAR = 0x303
CAN_ID_OUTPUT_VOLTAGE = 0x304
CAN_ID_DC_MEASUREMENTS = 0x305
CAN_ID_STATUS = 0x307
CAN_ID_LOAD_POWER = 0x308
CAN_ID_INPUT_VOLTAGE = 0x309

BMS_IDS = {CAN_ID_LIMITS, CAN_ID_SOC, CAN_ID_MEASUREMENTS, CAN_ID_ALARMS, CAN_ID_BMS_ID, CAN_ID_BMS_INFO}
SMA_IDS = {
    CAN_ID_GRID_POWER,
    CAN_ID_INVERTER_POWER,
    CAN_ID_GRID_KVAR,
    CAN_ID_INVERTER_KVAR,
    CAN_ID_OUTPUT_VOLTAGE,
    CAN_ID_DC_MEASUREMENTS,
    CAN_ID_STATUS,
    CAN_ID_LOAD_POWER,
    CAN_ID_INPUT_VOLTAGE,
}
SMA_ALL_IDS = BMS_IDS | SMA_IDS

FRAME_NAMES = {
    CAN_ID_LIMITS: "BMS limits",
    CAN_ID_SOC: "BMS SOC",
    CAN_ID_MEASUREMENTS: "BMS measurements",
    CAN_ID_ALARMS: "BMS alarms",
    CAN_ID_BMS_ID: "BMS ID string",
    CAN_ID_BMS_INFO: "BMS info",
    CAN_ID_GRID_POWER: "SI grid power",
    CAN_ID_INVERTER_POWER: "SI inverter power",
    CAN_ID_GRID_KVAR: "SI grid kVAr",
    CAN_ID_INVERTER_KVAR: "SI inverter kVAr",
    CAN_ID_OUTPUT_VOLTAGE: "SI output voltage",
    CAN_ID_DC_MEASUREMENTS: "SI DC bus",
    CAN_ID_STATUS: "SI status",
    CAN_ID_LOAD_POWER: "SI load power",
    CAN_ID_INPUT_VOLTAGE: "SI input voltage",
}


def _u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _s16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<h", data, offset)[0]


def _invalid_u16(value: int) -> bool:
    return value == INVALID_U16


def _invalid_s16(value: int) -> bool:
    return value == INVALID_S16


def _scale_u16(value: int, scale: float, unit: str) -> str | None:
    if _invalid_u16(value):
        return None
    return f"{value * scale:.1f}{unit}"


def _scale_s16(value: int, scale: float, unit: str) -> str | None:
    if _invalid_s16(value):
        return None
    return f"{value * scale:.1f}{unit}"


def _alarm_bits(byte_val: int, labels: list[str]) -> list[str]:
    active = []
    for bit, label in enumerate(labels):
        if byte_val & (1 << bit):
            active.append(label)
    return active


def decode_frame(can_id: int, data: bytes) -> dict[str, Any]:
    """Return structured decode for a CAN frame."""
    payload = data[:8].ljust(8, b"\x00")
    result: dict[str, Any] = {
        "can_id": can_id,
        "can_id_hex": f"0x{can_id:03X}",
        "name": FRAME_NAMES.get(can_id, "unknown"),
        "raw": payload.hex(" "),
        "direction": "bms" if can_id in BMS_IDS else "sma" if can_id in SMA_IDS else "other",
    }

    if can_id == CAN_ID_LIMITS:
        charge_v = _u16(payload, 0)
        charge_i = _s16(payload, 2)
        discharge_i = _s16(payload, 4)
        discharge_v = _u16(payload, 6)
        result.update(
            {
                "charge_voltage_v": None if _invalid_u16(charge_v) else charge_v / 10.0,
                "charge_current_a": None if _invalid_s16(charge_i) else charge_i / 10.0,
                "discharge_current_a": None if _invalid_s16(discharge_i) else discharge_i / 10.0,
                "discharge_voltage_v": None if _invalid_u16(discharge_v) else discharge_v / 10.0,
            }
        )

    elif can_id == CAN_ID_SOC:
        soc = _u16(payload, 0)
        soh = _u16(payload, 2)
        soc_hi = _u16(payload, 4)
        result.update(
            {
                "soc_pct": None if _invalid_u16(soc) else soc,
                "soh_pct": None if _invalid_u16(soh) else soh,
                "soc_hi_pct": None if _invalid_u16(soc_hi) else soc_hi / 100.0,
            }
        )

    elif can_id == CAN_ID_MEASUREMENTS:
        volts = _s16(payload, 0)
        current = _s16(payload, 2)
        temp_c = _s16(payload, 4)
        result.update(
            {
                "battery_voltage_v": None if _invalid_s16(volts) else volts / 100.0,
                "battery_current_a": None if _invalid_s16(current) else current / 10.0,
                "battery_temp_c": None if _invalid_s16(temp_c) else temp_c / 10.0,
            }
        )

    elif can_id == CAN_ID_ALARMS:
        alarms = []
        warnings = []
        if payload[0] & (1 << 2):
            alarms.append("high_voltage")
        if payload[0] & (1 << 4):
            alarms.append("low_voltage")
        if payload[0] & (1 << 6):
            alarms.append("high_temp")
        if payload[1] & (1 << 0):
            alarms.append("low_temp")
        result["alarms"] = alarms
        result["warnings"] = warnings

    elif can_id == CAN_ID_BMS_ID:
        result["bms_id"] = payload.decode("ascii", errors="replace").strip("\x00")

    elif can_id == CAN_ID_BMS_INFO:
        chem = _u16(payload, 0)
        capacity = _u16(payload, 4)
        result["cell_chemistry"] = chem
        result["capacity_ah"] = None if _invalid_u16(capacity) else capacity
        result["hw_version"] = payload[2]
        result["sw_version"] = payload[6]

    elif can_id == CAN_ID_GRID_POWER:
        result["master_grid_kw"] = _s16(payload, 0) / 10.0
        result["slave_grid_kw"] = _s16(payload, 2) / 10.0

    elif can_id == CAN_ID_INVERTER_POWER:
        result["master_inverter_kw"] = _s16(payload, 0) / 10.0
        result["slave_inverter_kw"] = _s16(payload, 2) / 10.0

    elif can_id == CAN_ID_DC_MEASUREMENTS:
        dc_v = _u16(payload, 0)
        dc_i = _s16(payload, 2)
        result["dc_voltage_v"] = None if _invalid_u16(dc_v) else dc_v / 10.0
        result["dc_current_a"] = None if _invalid_s16(dc_i) else dc_i / 10.0

    elif can_id == CAN_ID_OUTPUT_VOLTAGE:
        result["output_voltage_v"] = _u16(payload, 0) / 10.0
        result["output_freq_hz"] = _u16(payload, 6) / 100.0

    elif can_id == CAN_ID_INPUT_VOLTAGE:
        result["input_voltage_v"] = _u16(payload, 0) / 10.0
        result["grid_freq_hz"] = _u16(payload, 6) / 100.0

    elif can_id == CAN_ID_STATUS:
        status_byte = payload[1]
        result["ac2_relay_closed"] = bool(status_byte & 0x80)
        result["ac2_voltage_valid"] = bool(status_byte & 0x40)

    elif can_id == CAN_ID_LOAD_POWER:
        result["load_power_kw"] = _s16(payload, 0) / 10.0

    return result


def format_frame(decoded: dict[str, Any]) -> str:
    """Single-line human-readable frame summary."""
    can_id = decoded["can_id"]
    name = decoded["name"]
    parts = [f"{decoded['can_id_hex']} {name}"]

    if can_id == CAN_ID_LIMITS:
        parts.append(f"charge {_fmt(decoded.get('charge_voltage_v'), 'V')}/{_fmt(decoded.get('charge_current_a'), 'A')}")
        parts.append(f"discharge {_fmt(decoded.get('discharge_current_a'), 'A')}/{_fmt(decoded.get('discharge_voltage_v'), 'V')}")

    elif can_id == CAN_ID_SOC:
        parts.append(f"SOC {_fmt(decoded.get('soc_pct'), '%')} SOH {_fmt(decoded.get('soh_pct'), '%')}")

    elif can_id == CAN_ID_MEASUREMENTS:
        parts.append(
            f"{_fmt(decoded.get('battery_voltage_v'), 'V')} "
            f"{_fmt(decoded.get('battery_current_a'), 'A')} "
            f"{_fmt(decoded.get('battery_temp_c'), '°C')}"
        )

    elif can_id == CAN_ID_ALARMS:
        alarms = decoded.get("alarms") or []
        parts.append("alarms=" + (",".join(alarms) if alarms else "none"))

    elif can_id == CAN_ID_DC_MEASUREMENTS:
        parts.append(f"DC {_fmt(decoded.get('dc_voltage_v'), 'V')} {_fmt(decoded.get('dc_current_a'), 'A')}")

    elif can_id == CAN_ID_GRID_POWER:
        parts.append(f"grid master={decoded.get('master_grid_kw')}kW slave={decoded.get('slave_grid_kw')}kW")

    elif can_id == CAN_ID_INVERTER_POWER:
        parts.append(f"inv master={decoded.get('master_inverter_kw')}kW slave={decoded.get('slave_inverter_kw')}kW")

    elif can_id == CAN_ID_BMS_ID:
        parts.append(f"id={decoded.get('bms_id', '')!r}")

    else:
        parts.append(f"raw={decoded['raw']}")

    return " | ".join(parts)


def _fmt(value: Any, unit: str) -> str:
    if value is None:
        return "—"
    if unit == "%":
        return f"{value:.0f}{unit}"
    return f"{value:.1f}{unit}"
