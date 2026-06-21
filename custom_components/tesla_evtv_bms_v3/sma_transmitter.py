"""Transmit SMA Sunny Island CAN frames to an EVTV LiteCAN UDP gateway."""

from __future__ import annotations

import asyncio
import logging
import socket

from homeassistant.core import HomeAssistant

from .const import SMA_MESSAGE_INTERVAL
from .sma_can import build_sma_udp_frames

_LOGGER = logging.getLogger(__name__)


class LiteCanTransmitter:
    """Periodically send SMA CAN frames over UDP to a LiteCAN bridge."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        host: str,
        port: int,
        get_state,
    ) -> None:
        self._hass = hass
        self._name = name
        self._host = host
        self._port = port
        self._get_state = get_state
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
            "Started Sunny Island 6048 LiteCAN transmitter for %s -> %s:%s",
            self._name,
            self._host,
            self._port,
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
        self._sock.close()
        _LOGGER.info("Stopped Sunny Island LiteCAN transmitter for %s", self._name)

    async def _run(self) -> None:
        while self._running:
            try:
                values, config = self._get_state()
                if values.get("state_of_charge") is not None:
                    frames = build_sma_udp_frames(values, config)
                    for frame in frames:
                        await self._hass.async_add_executor_job(
                            self._sock.sendto, frame, (self._host, self._port)
                        )
                        await asyncio.sleep(SMA_MESSAGE_INTERVAL)
                else:
                    await asyncio.sleep(SMA_MESSAGE_INTERVAL * 4)
                self._last_error = None
            except asyncio.CancelledError:
                raise
            except OSError as err:
                self._last_error = str(err)
                _LOGGER.warning(
                    "LiteCAN transmit error for %s: %s",
                    self._name,
                    err,
                )
                await asyncio.sleep(1.0)
            except Exception as err:  # noqa: BLE001
                self._last_error = str(err)
                _LOGGER.exception(
                    "Unexpected LiteCAN transmit error for %s",
                    self._name,
                )
                await asyncio.sleep(1.0)
