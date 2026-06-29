"""Parse EVTV LiteCAN UDP packets."""

VALID_CAN_IDS = {0x150, 0x151, 0x650, 0x651, 0x683}


def parse_udp_packet(payload: bytes) -> dict | None:
    if len(payload) < 12:
        return None

    can_id = payload[8] + (payload[9] << 8) + (payload[10] << 16) + (payload[11] << 24)
    if can_id not in VALID_CAN_IDS:
        return None

    def u16(b0, b1):
        return b0 + (b1 << 8)

    def s16(b0, b1):
        return int.from_bytes(bytes([b0, b1]), byteorder="little", signed=True)

    def s32(b):
        return int.from_bytes(b, byteorder="little", signed=True)

    def c_to_f(c):
        return round(c * 9 / 5 + 32, 1)

    result = {}

    if can_id == 0x650:
        result["state_of_charge"] = payload[0] / 2
    elif can_id == 0x651:
        result["lowest_cell"] = u16(payload[0], payload[1]) / 1000
        result["highest_cell"] = u16(payload[2], payload[3]) / 1000
        result["average_cell"] = u16(payload[4], payload[5]) / 1000
        result["max_cells"] = payload[6]
        result["active_cells"] = payload[7]
    elif can_id == 0x151:
        current = s32(payload[0:4]) / 100.0
        power = s32(payload[4:8]) / 100.0
        volts = power / current if current else 0
        result.update({"current": round(current, 2), "power": round(power), "volts": round(volts, 1)})
    elif can_id == 0x683:
        result["freq_shift_volts"] = u16(payload[2], payload[3]) / 100
        result["tcch_amps"] = u16(payload[4], payload[5]) / 10
    elif can_id == 0x150:
        current = s16(payload[0], payload[1]) * -1
        volts = u16(payload[2], payload[3]) / 10.0
        result.update(
            {
                "current": round(current, 2),
                "power": round(volts * current),
                "volts": round(volts, 1),
                "max_temp": c_to_f(payload[6]),
                "min_temp": c_to_f(payload[7]),
            }
        )

    return result
