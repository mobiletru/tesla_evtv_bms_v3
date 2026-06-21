"""Build SMA Sunny Island 6048 CAN messages from EVTV BMS values."""

from __future__ import annotations

import struct
from typing import Any

INVALID_U16 = 0xFFFF

CAN_ID_LIMITS = 0x351
CAN_ID_SOC = 0x355
CAN_ID_MEASUREMENTS = 0x356
CAN_ID_ALARMS = 0x35A


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _pack_u16(value: int) -> bytes:
    return struct.pack("<H", value & 0xFFFF)


def _pack_s16(value: int) -> bytes:
    value = max(-32768, min(32767, value))
    return struct.pack("<h", value)


def _f_to_celsius(temp_f: float) -> float:
    return (temp_f - 32.0) * 5.0 / 9.0


def wrap_litecan_udp(can_id: int, payload: bytes) -> bytes:
    """Wrap an 8-byte CAN payload in the EVTV LiteCAN UDP format."""
    data = payload[:8].ljust(8, b"\x00")
    return data + struct.pack("<I", can_id & 0x7FF)


def build_limits_message(
    charge_voltage: float,
    charge_current: float,
    discharge_current: float,
    discharge_voltage: float,
) -> tuple[int, bytes]:
    """CAN 0x351 - charge/discharge limits (mandatory)."""
    payload = b"".join(
        [
            _pack_u16(int(_clamp(charge_voltage, 41.0, 63.0) * 10)),
            _pack_s16(int(_clamp(charge_current, 0.0, 1200.0) * 10)),
            _pack_s16(int(_clamp(discharge_current, 0.0, 1200.0) * 10)),
            _pack_u16(int(_clamp(discharge_voltage, 41.0, 48.0) * 10)),
        ]
    )
    return CAN_ID_LIMITS, payload


def build_soc_message(soc: float, soh: float = 100.0) -> tuple[int, bytes]:
    """CAN 0x355 - state of charge (mandatory)."""
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


def build_measurements_message(
    volts: float,
    current: float,
    temp_c: float,
) -> tuple[int, bytes]:
    """CAN 0x356 - battery measurements (mandatory)."""
    payload = b"".join(
        [
            _pack_s16(int(round(volts * 100))),
            _pack_s16(int(round(current * 10))),
            _pack_s16(int(round(temp_c * 10))),
            _pack_u16(INVALID_U16),
        ]
    )
    return CAN_ID_MEASUREMENTS, payload


def _set_alarm_bit(payload: bytearray, byte_index: int, bit_index: int, active: bool) -> None:
    mask = 1 << bit_index
    if active:
        payload[byte_index] = (payload[byte_index] & ~mask) | mask
    else:
        payload[byte_index] &= ~mask


def build_alarms_message(values: dict[str, Any]) -> tuple[int, bytes]:
    """CAN 0x35A - alarms and warnings."""
    payload = bytearray(8)

    low_volt = values.get("low_volt", "Normal")
    high_volt = values.get("high_volt", "Normal")

    _set_alarm_bit(payload, 0, 4, low_volt == "Critical")
    _set_alarm_bit(payload, 0, 2, high_volt == "Critical")

    max_temp = values.get("max_temp")
    min_temp = values.get("min_temp")
    if max_temp is not None and max_temp >= 140:
        _set_alarm_bit(payload, 0, 6, True)
    if min_temp is not None and min_temp <= 14:
        _set_alarm_bit(payload, 1, 0, True)

    return CAN_ID_ALARMS, bytes(payload)


def build_sma_messages(
    values: dict[str, Any],
    config: dict[str, Any],
) -> list[tuple[int, bytes]]:
    """Build mandatory Sunny Island CAN messages from live BMS data."""
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

    return [
        build_limits_message(
            config["charge_voltage"],
            config["charge_current_limit"],
            config["discharge_current_limit"],
            config["discharge_voltage_limit"],
        ),
        build_soc_message(soc),
        build_measurements_message(volts, current, temp_c),
        build_alarms_message(values),
    ]


def build_sma_udp_frames(
    values: dict[str, Any],
    config: dict[str, Any],
) -> list[bytes]:
    """Build LiteCAN UDP packets for each SMA CAN message."""
    return [
        wrap_litecan_udp(can_id, payload)
        for can_id, payload in build_sma_messages(values, config)
    ]
