"""Poll Sunny WebBox RPC and publish to MQTT."""

from __future__ import annotations

import logging
import time

from app.webbox_rpc import MIN_POLL_INTERVAL, OVERVIEW_MAP, PROCESS_MAP, WebBoxClient, WebBoxConfig

log = logging.getLogger(__name__)


class WebBoxPoller:
    def __init__(
        self,
        config: WebBoxConfig,
        mqtt_client=None,
        si_device: str = "sunny_island",
        enabled_metrics: set[str] | None = None,
    ) -> None:
        self.config = config
        self.mqtt = mqtt_client
        self.si_device = si_device
        self.enabled_metrics = enabled_metrics
        self.client = WebBoxClient(config)
        self.last_values: dict[str, str | float] = {}
        self.last_channels: list[str] = []

    def _publish(self, key: str, value: str | float) -> None:
        if self.enabled_metrics and key not in self.enabled_metrics:
            return
        if not self.mqtt:
            return
        self.mqtt.publish(f"tesla_evtv/{self.si_device}/{key}", str(value), retain=True)

    def poll_once(self) -> dict[str, str | float]:
        values: dict[str, str | float] = {}

        try:
            overview = self.client.get_plant_overview()
            for meta, mqtt_key in OVERVIEW_MAP.items():
                if meta in overview:
                    values[mqtt_key] = overview[meta]
                    self._publish(mqtt_key, overview[meta])
        except Exception as err:
            log.warning("WebBox GetPlantOverview failed: %s", err)

        device_key = self.client.find_device_key()
        if device_key:
            try:
                process = self.client.get_process_data(device_key)
                if not self.last_channels and process:
                    try:
                        self.last_channels = self.client.get_process_data_channels(device_key)
                        log.info("WebBox SI channels (%s): %s", device_key, self.last_channels[:12])
                    except Exception:
                        pass
                for meta, raw in process.items():
                    mqtt_key = PROCESS_MAP.get(meta, f"webbox_{meta.lower()}")
                    values[mqtt_key] = raw
                    self._publish(mqtt_key, raw)
                    # Also publish raw meta for discovery flexibility
                    raw_key = f"webbox_{meta}"
                    values[raw_key] = raw
                    self._publish(raw_key, raw)
            except Exception as err:
                log.warning("WebBox GetProcessData failed: %s", err)
        else:
            log.warning("WebBox: no Sunny Island device found — set webbox_device_key in add-on config")

        self.last_values = values
        return values

    def run(self) -> None:
        if not self.config.enabled:
            return
        interval = max(MIN_POLL_INTERVAL, self.config.poll_interval)
        log.info(
            "WebBox RPC %s://%s:%s (poll every %ss)",
            self.config.mode,
            self.config.host,
            self.config.port if self.config.mode == "http" else 34268,
            interval,
        )
        while True:
            try:
                self.poll_once()
            except Exception as err:
                log.exception("WebBox poll error: %s", err)
            time.sleep(interval)
