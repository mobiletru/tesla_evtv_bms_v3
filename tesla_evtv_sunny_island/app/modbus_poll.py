"""Modbus RTU/TCP polling loop for Sunny Island."""

from __future__ import annotations

import logging
import time

from app.sma_modbus import MQTT_KEY_MAP, ModbusConfig, poll_all

log = logging.getLogger(__name__)


class SunnyIslandModbus:
    def __init__(self, config: ModbusConfig, mqtt_client=None, si_device: str = "sunny_island") -> None:
        self.config = config
        self.mqtt = mqtt_client
        self.si_device = si_device
        self._client = None
        self.last_values: dict[str, float | int | None] = {}

    def _connect(self):
        from pymodbus.client import ModbusSerialClient, ModbusTcpClient

        if self.config.mode == "tcp":
            client = ModbusTcpClient(host=self.config.host, port=self.config.port)
        else:
            client = ModbusSerialClient(
                port=self.config.serial_port,
                baudrate=self.config.baudrate,
                bytesize=8,
                parity="E",
                stopbits=1,
                timeout=3,
            )
        if not client.connect():
            raise ConnectionError(f"Modbus {self.config.mode} connect failed")
        return client

    def _publish(self, values: dict) -> None:
        if not self.mqtt:
            return
        for modbus_key, value in values.items():
            if value is None:
                continue
            mqtt_key = MQTT_KEY_MAP.get(modbus_key, modbus_key)
            if mqtt_key in KW_KEYS and isinstance(value, (int, float)):
                value = round(value / 1000.0, 3)
            self.mqtt.publish(f"tesla_evtv/{self.si_device}/{mqtt_key}", str(value), retain=True)

    def run(self) -> None:
        if not self.config.enabled:
            log.info("Modbus disabled")
            return

        log.info(
            "Sunny Island Modbus %s (unit_id=%s, interval=%ss)",
            f"TCP {self.config.host}:{self.config.port}" if self.config.mode == "tcp"
            else f"RTU {self.config.serial_port} @ {self.config.baudrate}",
            self.config.unit_id,
            self.config.poll_interval,
        )

        while True:
            try:
                if self._client is None:
                    self._client = self._connect()
                values = poll_all(self._client, self.config.unit_id)
                self.last_values = values
                self._publish(values)
                log.debug("Modbus poll: %s", {k: v for k, v in values.items() if v is not None})
            except Exception as err:
                log.warning("Modbus poll error: %s", err)
                if self._client:
                    try:
                        self._client.close()
                    except Exception:
                        pass
                    self._client = None
                time.sleep(5.0)
                continue
            time.sleep(self.config.poll_interval)
