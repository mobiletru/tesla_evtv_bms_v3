"""Transmit SMA Sunny Island CAN frames through a PCAN / SocketCAN adapter."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant

from .const import PCAN_INTERFACE_PCAN, PCAN_INTERFACE_SOCKETCAN, SMA_MESSAGE_INTERVAL
from .sma_can import build_sma_messages

_LOGGER = logging.getLogger(__name__)


class PcanTransmitter:
    """Periodically send SMA CAN frames on can0 (SocketCAN) or Peak PCAN."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        interface: str,
        channel: str,
        bitrate: int,
        get_state,
    ) -> None:
        self._hass = hass
        self._name = name
        self._interface = interface
        self._channel = channel
        self._bitrate = bitrate
        self._get_state = get_state
        self._bus = None
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_error: str | None = None

    @property
    def active(self) -> bool:
        return self._running

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def async_start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        _LOGGER.info(
            "Started Sunny Island 6048 CAN transmitter for %s on %s/%s @ %s bps",
            self._name,
            self._interface,
            self._channel,
            self._bitrate,
        )

    async def async_stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._bus is not None:
            await self._hass.async_add_executor_job(self._shutdown_bus)
        _LOGGER.info("Stopped Sunny Island CAN transmitter for %s", self._name)

    def _shutdown_bus(self) -> None:
        if self._bus is not None:
            self._bus.shutdown()
            self._bus = None

    def _ensure_bus(self) -> None:
        if self._bus is not None:
            return
        import can  # noqa: PLC0415

        if self._interface == PCAN_INTERFACE_SOCKETCAN:
            # Home Assistant OS: PCAN USB typically appears as can0 via SocketCAN.
            self._bus = can.interface.Bus(
                interface=PCAN_INTERFACE_SOCKETCAN,
                channel=self._channel,
            )
        else:
            self._bus = can.interface.Bus(
                interface=PCAN_INTERFACE_PCAN,
                channel=self._channel,
                bitrate=self._bitrate,
            )

    def _send_message(self, can_id: int, payload: bytes) -> None:
        import can  # noqa: PLC0415

        self._ensure_bus()
        msg = can.Message(
            arbitration_id=can_id,
            data=payload[:8].ljust(8, b"\x00"),
            is_extended_id=False,
        )
        self._bus.send(msg)

    async def _run(self) -> None:
        while self._running:
            try:
                values, config = self._get_state()
                if values.get("state_of_charge") is not None:
                    messages = build_sma_messages(values, config)
                    for can_id, payload in messages:
                        await self._hass.async_add_executor_job(
                            self._send_message, can_id, payload
                        )
                        await asyncio.sleep(SMA_MESSAGE_INTERVAL)
                else:
                    await asyncio.sleep(SMA_MESSAGE_INTERVAL * 4)
                self._last_error = None
            except asyncio.CancelledError:
                raise
            except ImportError:
                self._last_error = "python-can is not installed"
                _LOGGER.error("CAN support requires python-can on the Home Assistant host.")
                await asyncio.sleep(5.0)
            except OSError as err:
                self._last_error = str(err)
                _LOGGER.warning(
                    "CAN transmit error for %s (%s/%s): %s",
                    self._name,
                    self._interface,
                    self._channel,
                    err,
                )
                self._shutdown_bus()
                await asyncio.sleep(2.0)
            except Exception as err:  # noqa: BLE001
                self._last_error = str(err)
                _LOGGER.exception("Unexpected CAN transmit error for %s", self._name)
                self._shutdown_bus()
                await asyncio.sleep(2.0)
