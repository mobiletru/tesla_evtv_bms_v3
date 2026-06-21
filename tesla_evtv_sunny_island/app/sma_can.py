"""SMA Sunny Island 6048 CAN message builder."""

from __future__ import annotations

import struct
from typing import Any

from app.charge_control import compute_closed_loop_limits

INVALID_U16 = 0xFFFF
CAN_ID_LIMITS = 0x351
CAN_ID_SOC = 0x355
CAN_ID_MEASUREMENTS = 0x356
CAN_ID_ALARMS = 0x35A
SMA_MESSAGE_INTERVAL = 0.25


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _pack_u16(value: int) -> bytes:
    return struct.pack("<H", value & 0xFFFF)


def _pack_s16(value: int) -> bytes:
    value = max(-32768, min(32767, value))
    return struct.pack("<h", value)


def _f_to_celsius(temp_f: float) -> float:
    return (temp_f - 32.0) * 5.0 / 9.0


def build_limits_message(charge_v, charge_i, discharge_i, discharge_v):
    payload = b"".join(
        [
            _pack_u16(int(_clamp(charge_v, 41.0, 63.0) * 10)),
            _pack_s16(int(_clamp(charge_i, 0.0, 1200.0) * 10)),
            _pack_s16(int(_clamp(discharge_i, 0.0, 1200.0) * 10)),
            _pack_u16(int(_clamp(discharge_v, 41.0, 48.0) * 10)),
        ]
    )
    return CAN_ID_LIMITS, payload


def build_soc_message(soc: float, soh: float = 100.0):
    soc = _clamp(soc, 0.0, 100.0)
    soh = _clamp(soh, 0.0, 100.0)
    payload = b"".join(
        [
            _pack_u16(int(round(soc))),
            _pack_u16(int(round(soh))),
            _pack_u16(int(round(soc * 100))),
            _pack_u16(INVALID_U16),
        ]
    )
    return CAN_ID_SOC, payload


def build_measurements_message(volts: float, current: float, temp_c: float):
    payload = b"".join(
        [
            _pack_s16(int(round(volts * 100))),
            _pack_s16(int(round(current * 10))),
            _pack_s16(int(round(temp_c * 10))),
            _pack_u16(INVALID_U16),
        ]
    )
    return CAN_ID_MEASUREMENTS, payload


def build_alarms_message(values: dict[str, Any]):
    payload = bytearray(8)
    if values.get("low_volt") == "Critical":
        payload[0] |= 1 << 4
    if values.get("high_volt") == "Critical":
        payload[0] |= 1 << 2
    max_temp = values.get("max_temp")
    min_temp = values.get("min_temp")
    if max_temp is not None and max_temp >= 140:
        payload[0] |= 1 << 6
    if min_temp is not None and min_temp <= 14:
        payload[1] |= 1 << 0
    return CAN_ID_ALARMS, bytes(payload)


def build_sma_messages(values: dict[str, Any], config: dict[str, Any]):
    soc = values.get("state_of_charge", 0.0)
    volts = values.get("volts", 0.0)
    current = values.get("current", 0.0)
    if config.get("invert_current"):
        current = -current

    max_temp = values.get("max_temp")
    min_temp = values.get("min_temp")
    if max_temp is not None and min_temp is not None:
        temp_c = (_f_to_celsius(max_temp) + _f_to_celsius(min_temp)) / 2.0
    elif max_temp is not None:
        temp_c = _f_to_celsius(max_temp)
    elif min_temp is not None:
        temp_c = _f_to_celsius(min_temp)
    else:
        temp_c = 25.0

    limits = compute_closed_loop_limits(values, config)

    return [
        build_limits_message(
            limits["charge_voltage"],
            limits["charge_current_limit"],
            limits["discharge_current_limit"],
            limits["discharge_voltage_limit"],
        ),
        build_soc_message(soc),
        build_measurements_message(volts, current, temp_c),
        build_alarms_message(values),
    ]
