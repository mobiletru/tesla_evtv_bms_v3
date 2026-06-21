"""Tesla module pack calculations."""

TESLA_MODULE_KWH = 5.2
TESLA_MODULE_CELLS = 6
TESLA_MODULE_NOMINAL_VOLTS = 22.2

SMA_MIN_BUS_VOLTS = 41.0
SMA_MAX_BUS_VOLTS = 63.0
SMA_MAX_DISCHARGE_LIMIT = 48.0


def compute_pack_settings(
    module_count: int,
    modules_in_series: int,
    min_cell_volts: float,
    max_cell_volts: float,
) -> dict:
    if modules_in_series > module_count:
        modules_in_series = module_count
    cells_in_series = modules_in_series * TESLA_MODULE_CELLS
    nominal_voltage = modules_in_series * TESLA_MODULE_NOMINAL_VOLTS
    charge_voltage = min(SMA_MAX_BUS_VOLTS, cells_in_series * max_cell_volts)
    discharge_voltage = max(
        SMA_MIN_BUS_VOLTS,
        min(SMA_MAX_DISCHARGE_LIMIT, cells_in_series * min_cell_volts),
    )
    return {
        "module_count": module_count,
        "modules_in_series": modules_in_series,
        "pack_size": round(module_count * TESLA_MODULE_KWH, 1),
        "cells_in_series": cells_in_series,
        "nominal_voltage": round(nominal_voltage, 1),
        "charge_voltage": round(charge_voltage, 1),
        "discharge_voltage_limit": round(discharge_voltage, 1),
        "charge_current_limit": 100.0,
        "discharge_current_limit": 100.0,
    }
