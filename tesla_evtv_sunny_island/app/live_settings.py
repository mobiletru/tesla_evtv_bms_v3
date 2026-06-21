"""Runtime settings that can be changed live from the dashboard or MQTT."""

from __future__ import annotations

import threading
from typing import Any, Callable

from app.pack_config import compute_pack_settings

# field -> (type, min, max, step) for numbers; switches have type "switch"
LIVE_FIELDS: dict[str, dict[str, Any]] = {
    "charge_current_limit": {"type": "number", "min": 0, "max": 200, "step": 1, "unit": "A", "label": "Charge current limit"},
    "discharge_current_limit": {"type": "number", "min": 0, "max": 200, "step": 1, "unit": "A", "label": "Discharge current limit"},
    "min_cell_volts": {"type": "number", "min": 2.5, "max": 3.5, "step": 0.05, "unit": "V", "label": "Min cell voltage"},
    "max_cell_volts": {"type": "number", "min": 3.8, "max": 4.2, "step": 0.05, "unit": "V", "label": "Max cell voltage"},
    "sma_enabled": {"type": "switch", "label": "SMA CAN transmit"},
    "can_watch_enabled": {"type": "switch", "label": "CAN bus monitor"},
    "invert_current": {"type": "switch", "label": "Invert current sign"},
}


class LiveSettings:
    """Thread-safe runtime config merged with pack calculations."""

    def __init__(self, initial: dict[str, Any]) -> None:
        self._lock = threading.Lock()
        self._config = dict(initial)
        self._on_change: list[Callable[[str, Any], None]] = []
        self._recalculate_pack()

    def register_callback(self, callback: Callable[[str, Any], None]) -> None:
        self._on_change.append(callback)

    def _recalculate_pack(self) -> None:
        pack = compute_pack_settings(
            self._config["module_count"],
            self._config["modules_in_series"],
            self._config["min_cell_volts"],
            self._config["max_cell_volts"],
        )
        for key in ("cells_in_series", "nominal_voltage", "charge_voltage", "discharge_voltage_limit", "pack_size"):
            self._config[key] = pack[key]

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default)

    def snapshot_for_api(self, live_values: dict | None = None) -> dict[str, Any]:
        with self._lock:
            out = {
                "settings": {k: self._config.get(k) for k in LIVE_FIELDS},
                "pack": {
                    "module_count": self._config.get("module_count"),
                    "modules_in_series": self._config.get("modules_in_series"),
                    "pack_size_kwh": self._config.get("pack_size"),
                    "cells_in_series": self._config.get("cells_in_series"),
                    "nominal_voltage": self._config.get("nominal_voltage"),
                    "charge_voltage": self._config.get("charge_voltage"),
                    "discharge_voltage_limit": self._config.get("discharge_voltage_limit"),
                },
                "live": live_values or {},
            }
        return out

    def apply(self, updates: dict[str, Any]) -> dict[str, str]:
        errors: dict[str, str] = {}
        with self._lock:
            for key, raw in updates.items():
                if key not in LIVE_FIELDS:
                    errors[key] = "unknown setting"
                    continue
                meta = LIVE_FIELDS[key]
                try:
                    if meta["type"] == "switch":
                        value = str(raw).lower() in ("true", "1", "on", "yes")
                    else:
                        value = float(raw)
                        value = max(meta["min"], min(meta["max"], value))
                        if meta["step"] >= 1:
                            value = round(value)
                        else:
                            value = round(value, 2)
                except (TypeError, ValueError):
                    errors[key] = "invalid value"
                    continue
                self._config[key] = value
                for cb in self._on_change:
                    cb(key, value)
            self._recalculate_pack()
        return errors
