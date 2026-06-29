"""BMS state and energy accounting."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
SETTINGS_FILE = DATA_DIR / "monitor_settings.json"


class BMSMonitorState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.values: dict = {}
        self.last_update: float | None = None
        self.charge_energy_kwh = 0.0
        self.discharge_energy_kwh = 0.0
        self._energy_last = time.time()
        self.pack_name = os.environ.get("PACK_NAME", "Tesla Pack")
        self.pack_size_kwh = float(os.environ.get("PACK_SIZE_KWH", "75"))
        self._load_settings()

    def _load_settings(self) -> None:
        if not SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(SETTINGS_FILE.read_text())
            if "pack_name" in data:
                self.pack_name = str(data["pack_name"])
            if "pack_size_kwh" in data:
                self.pack_size_kwh = float(data["pack_size_kwh"])
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    def save_settings(self, pack_name: str | None = None, pack_size_kwh: float | None = None) -> None:
        with self._lock:
            if pack_name is not None:
                self.pack_name = pack_name
            if pack_size_kwh is not None:
                self.pack_size_kwh = pack_size_kwh
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(
                json.dumps({"pack_name": self.pack_name, "pack_size_kwh": self.pack_size_kwh})
            )

    def reset_energy(self) -> None:
        with self._lock:
            self.charge_energy_kwh = 0.0
            self.discharge_energy_kwh = 0.0
            self._energy_last = time.time()

    def merge(self, parsed: dict) -> None:
        with self._lock:
            self.values.update(parsed)
            self.last_update = time.time()

            if "power" in parsed or "current" in parsed:
                power = self.values.get("power")
                if power is not None:
                    now = time.time()
                    delta = now - self._energy_last
                    self._energy_last = now
                    if power < 0:
                        self.discharge_energy_kwh += abs(power) * delta / 3600.0 / 1000.0
                    elif power > 0:
                        self.charge_energy_kwh += power * delta / 3600.0 / 1000.0

            self._enrich_derived()

    def _enrich_derived(self) -> None:
        current = self.values.get("current")
        if current is not None:
            if current > 1:
                self.values["battery_status"] = "Charging"
            elif current < -1:
                self.values["battery_status"] = "Discharging"
            else:
                self.values["battery_status"] = "Idle"

        power = self.values.get("power")
        if power is not None:
            self.values["charge"] = power if power > 0 else 0
            self.values["discharge"] = abs(power) if power < 0 else 0

        soc = self.values.get("state_of_charge")
        if soc is not None:
            self.values["available_energy"] = round(self.pack_size_kwh * soc / 100.0, 2)

        low = self.values.get("lowest_cell")
        high = self.values.get("highest_cell")
        if low is not None and high is not None:
            self.values["cell_difference"] = round(high - low, 4)

        self.values["charge_energy"] = round(self.charge_energy_kwh, 3)
        self.values["discharge_energy"] = round(self.discharge_energy_kwh, 3)

    def snapshot(self) -> dict:
        with self._lock:
            live = dict(self.values)
            return {
                "live": live,
                "pack": {
                    "pack_name": self.pack_name,
                    "pack_size_kwh": self.pack_size_kwh,
                },
                "last_update": self.last_update,
                "listening": True,
                "summary": self._summary(live),
            }

    def _summary(self, live: dict) -> str:
        current = live.get("current")
        power = live.get("power")
        soc = live.get("state_of_charge")
        available = live.get("available_energy")

        if current is None:
            return "Waiting for data…"

        if current > 1:
            if available is not None and power and abs(power) > 0:
                hours = (self.pack_size_kwh - available) / (abs(power) / 1000.0)
                return self._format_hours(hours, "to Full")
            return "Charging"
        if current < -1:
            if available is not None and power and abs(power) > 0:
                hours = available / (abs(power) / 1000.0)
                return self._format_hours(hours, "to Empty")
            return "Discharging"
        return "Idle"

    @staticmethod
    def _format_hours(hours: float, suffix: str) -> str:
        if hours <= 0:
            return "Idle"
        formatted = f"{hours:.1f}" if hours < 10 else str(int(round(hours)))
        return f"{formatted} hrs {suffix}"
