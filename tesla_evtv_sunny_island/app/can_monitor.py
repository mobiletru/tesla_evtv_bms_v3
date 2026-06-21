"""Watch and decode SMA Sunny Island CAN traffic on SocketCAN."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from collections import Counter

import can

from app.can_setup import read_can_stats, setup_can_interface
from app.mqtt_discovery import SUNNY_ISLAND_SENSORS, extract_sunny_island_values
from app.sma_decode import BMS_IDS, CAN_ID_LIMITS, CAN_ID_SOC, SMA_ALL_IDS, decode_frame, format_frame

log = logging.getLogger("sma_can_monitor")

BMS_TIMEOUT_S = 60.0
BMS_WARN_IDS = {CAN_ID_LIMITS, CAN_ID_SOC}


class CanWatchService:
    """Passive CAN listener with SMA frame decode and optional MQTT publish."""

    def __init__(
        self,
        iface: str,
        filter_mode: str = "sma",
        summary_interval: float = 30,
        mqtt_client=None,
        si_device: str = "sunny_island",
        enabled_si_metrics: set[str] | None = None,
        bus: can.Bus | None = None,
    ) -> None:
        self.iface = iface
        self.filter_mode = filter_mode
        self.summary_interval = summary_interval
        self.mqtt = mqtt_client
        self.si_device = si_device
        self.enabled_si_metrics = enabled_si_metrics or set(SUNNY_ISLAND_SENSORS)
        self.bus = bus
        self._owns_bus = bus is None
        self.counts: Counter[int] = Counter()
        self.last_seen: dict[int, float] = {}
        self.last_decoded: dict[int, dict] = {}

    def _ensure_bus(self) -> None:
        if self.bus is None:
            self.bus = can.interface.Bus(interface="socketcan", channel=self.iface)
            self._owns_bus = True

    def _passes_filter(self, can_id: int) -> bool:
        if self.filter_mode == "all":
            return True
        if self.filter_mode == "sma":
            return can_id in SMA_ALL_IDS
        if self.filter_mode == "bms":
            return can_id in BMS_IDS
        return True

    def _check_bms_health(self, now: float) -> None:
        for can_id in BMS_WARN_IDS:
            last = self.last_seen.get(can_id)
            if last is None:
                continue
            age = now - last
            if age > BMS_TIMEOUT_S:
                log.error(
                    "BMS frame %s missing for %.0fs — Sunny Island may fault F952 ExtBMSTimeout",
                    f"0x{can_id:03X}",
                    age,
                )
            elif age > 30:
                log.warning("BMS frame %s stale (%.0fs)", f"0x{can_id:03X}", age)

    def _publish_mqtt(self, decoded: dict) -> None:
        if not self.mqtt:
            return
        values = extract_sunny_island_values(decoded)
        for key, value in values.items():
            if key not in self.enabled_si_metrics:
                continue
            self.mqtt.publish(f"tesla_evtv/{self.si_device}/{key}", str(value), retain=True)

    def _print_summary(self, now: float) -> None:
        log.info("--- CAN watch summary (%s) ---", self.iface)
        log.info("Bus: %s", read_can_stats(self.iface))
        if self.counts:
            top = ", ".join(f"0x{cid:03X}×{n}" for cid, n in self.counts.most_common(8))
            log.info("Frame counts: %s", top)
        for can_id in sorted(BMS_WARN_IDS | {0x305, 0x300, 0x301}):
            if can_id in self.last_decoded:
                age = now - self.last_seen.get(can_id, now)
                log.info("[%0.0fs ago] %s", age, format_frame(self.last_decoded[can_id]))

    def run(self, setup_can: bool = False, bitrate: int = 500000) -> None:
        if setup_can and self._owns_bus:
            setup_can_interface(self.iface, bitrate)

        self._ensure_bus()
        log.info(
            "CAN watch on %s (filter=%s, summary every %.0fs, mqtt metrics=%s)",
            self.iface,
            self.filter_mode,
            self.summary_interval,
            len(self.enabled_si_metrics) if self.mqtt else 0,
        )

        last_summary = time.monotonic()
        while True:
            msg = self.bus.recv(timeout=1.0)
            now = time.monotonic()
            if msg is None:
                self._check_bms_health(now)
                if now - last_summary >= self.summary_interval:
                    self._print_summary(now)
                    last_summary = now
                continue

            can_id = msg.arbitration_id
            if not self._passes_filter(can_id):
                continue

            decoded = decode_frame(can_id, bytes(msg.data))
            self.counts[can_id] += 1
            self.last_seen[can_id] = now
            self.last_decoded[can_id] = decoded

            log.info("[watch] %s", format_frame(decoded))
            self._publish_mqtt(decoded)

            if now - last_summary >= self.summary_interval:
                self._print_summary(now)
                last_summary = now


def _build_mqtt():
    import paho.mqtt.client as mqtt

    host = os.environ.get("MQTT_HOST", "core-mosquitto")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    user = os.environ.get("MQTT_USER", "")
    password = os.environ.get("MQTT_PASSWORD", "")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if user:
        client.username_pw_set(user, password)
    client.connect(host, port, 60)
    client.loop_start()
    return client


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch SMA Sunny Island CAN bus")
    parser.add_argument("--interface", default=os.environ.get("CAN_INTERFACE", "can0"))
    parser.add_argument("--bitrate", type=int, default=int(os.environ.get("CAN_BITRATE", "500000")))
    parser.add_argument("--setup-can", action="store_true", default=os.environ.get("SETUP_CAN", "false").lower() == "true")
    parser.add_argument("--no-setup-can", action="store_false", dest="setup_can")
    parser.add_argument("--filter", choices=["all", "sma", "bms"], default=os.environ.get("CAN_FILTER", "sma"))
    parser.add_argument("--summary-interval", type=float, default=float(os.environ.get("SUMMARY_INTERVAL", "30")))
    parser.add_argument("--mqtt", action="store_true", default=os.environ.get("PUBLISH_MQTT", "false").lower() == "true")
    parser.add_argument("--device-name", default=os.environ.get("SUNNY_ISLAND_DEVICE_NAME", "sunny_island"))
    parser.add_argument("--log-level", default=os.environ.get("LOG_LEVEL", "INFO"))
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    mqtt_client = _build_mqtt() if args.mqtt else None
    service = CanWatchService(
        iface=args.interface,
        filter_mode=args.filter,
        summary_interval=args.summary_interval,
        mqtt_client=mqtt_client,
        si_device=args.device_name,
    )
    try:
        service.run(setup_can=args.setup_can, bitrate=args.bitrate)
    except KeyboardInterrupt:
        log.info("Stopped.")
        return 0
    except Exception:
        log.exception("Fatal error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
