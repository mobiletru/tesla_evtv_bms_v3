"""Dynamic charge/discharge limits for SMA closed-loop control."""

from __future__ import annotations

from typing import Any


def compute_closed_loop_limits(
    values: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, float]:
    """Compute live 0x351 limits from EVTV BMS cell data.

    Sunny Island closed-loop charge uses:
    - charge voltage setpoint (hard limit on-grid)
    - charge current limit (BMS tells SI how much charge current is allowed)
    """
    charge_v = config["charge_voltage"]
    charge_i = config["charge_current_limit"]
    discharge_i = config["discharge_current_limit"]
    discharge_v = config["discharge_voltage_limit"]

    max_cell = config["max_cell_volts"]
    min_cell = config["min_cell_volts"]
    highest = values.get("highest_cell")
    lowest = values.get("lowest_cell")
    soc = values.get("state_of_charge")

    # Charge current taper as highest cell approaches max (closed-loop charge)
    if highest is not None:
        if highest >= max_cell:
            charge_i = 0.0
        elif highest >= max_cell - 0.02:
            charge_i = min(charge_i, 2.0)
        elif highest >= max_cell - 0.10:
            headroom = max_cell - highest
            charge_i = charge_i * max(0.05, headroom / 0.10)

    # Reduce charge near full SoC if cell data is missing
    if highest is None and soc is not None and soc >= 98:
        charge_i = min(charge_i, 5.0)

    # High temperature charge derate (~45 C / 113 F)
    max_temp = values.get("max_temp")
    if max_temp is not None and max_temp >= 113:
        charge_i = min(charge_i, charge_i * 0.5)

    # Low temperature — limit charge (cold charge protection)
    min_temp = values.get("min_temp")
    if min_temp is not None and min_temp <= 32:
        charge_i = 0.0

    # Discharge taper at low cell voltage
    if lowest is not None:
        if lowest <= min_cell:
            discharge_i = 0.0
        elif lowest <= min_cell + 0.10:
            headroom = lowest - min_cell
            discharge_i = discharge_i * max(0.05, headroom / 0.10)

    return {
        "charge_voltage": charge_v,
        "charge_current_limit": round(charge_i, 1),
        "discharge_current_limit": round(discharge_i, 1),
        "discharge_voltage_limit": discharge_v,
    }
