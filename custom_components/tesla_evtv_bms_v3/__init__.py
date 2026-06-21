import logging
import socket

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_CHARGE_CURRENT,
    CONF_CHARGE_VOLTAGE,
    CONF_DISCHARGE_CURRENT,
    CONF_DISCHARGE_VOLTAGE,
    CONF_INVERT_CURRENT,
    CONF_LITECAN_HOST,
    CONF_LITECAN_PORT,
    CONF_MODULE_COUNT,
    CONF_MODULES_IN_SERIES,
    CONF_PCAN_BITRATE,
    CONF_PCAN_CHANNEL,
    CONF_PCAN_INTERFACE,
    CONF_SMA_ENABLED,
    CONF_SMA_MODE,
    DEFAULT_LITECAN_PORT,
    DEFAULT_PCAN_BITRATE,
    DEFAULT_PCAN_CHANNEL,
    DEFAULT_PCAN_INTERFACE,
    DOMAIN,
    PLATFORMS,
    SIGNAL_UPDATE_ENTITY,
    SMA_MODE_LITECAN,
    SMA_MODE_PCAN,
)
from .pack_config import DEFAULT_CHARGE_CURRENT, DEFAULT_DISCHARGE_CURRENT, DEFAULT_PACK, compute_pack_settings
from .sma_transmitter import LiteCanTransmitter
from .parser import parse_udp_packet
from .pcan_transmitter import PcanTransmitter

_LOGGER = logging.getLogger(__name__)


def _entry_settings(entry: ConfigEntry) -> dict:
    data = {**entry.data, **entry.options}
    module_count = int(data.get(CONF_MODULE_COUNT, DEFAULT_PACK["module_count"]))
    modules_in_series = int(data.get(CONF_MODULES_IN_SERIES, DEFAULT_PACK["modules_in_series"]))
    min_cell = float(data.get("min_cell_volts", 3.2))
    max_cell = float(data.get("max_cell_volts", 4.1))
    computed = compute_pack_settings(module_count, modules_in_series, min_cell, max_cell)

    return {
        CONF_MODULE_COUNT: module_count,
        CONF_MODULES_IN_SERIES: modules_in_series,
        "pack_size": data.get("pack_size", computed["pack_size"]),
        "cells_in_series": data.get("cells_in_series", computed["cells_in_series"]),
        "nominal_voltage": data.get("nominal_voltage", computed["nominal_voltage"]),
        "min_cell_volts": min_cell,
        "max_cell_volts": max_cell,
        "charge_voltage": data.get(CONF_CHARGE_VOLTAGE, computed["charge_voltage"]),
        "charge_current_limit": data.get(CONF_CHARGE_CURRENT, DEFAULT_CHARGE_CURRENT),
        "discharge_current_limit": data.get(CONF_DISCHARGE_CURRENT, DEFAULT_DISCHARGE_CURRENT),
        "discharge_voltage_limit": data.get(CONF_DISCHARGE_VOLTAGE, computed["discharge_voltage_limit"]),
        "invert_current": data.get(CONF_INVERT_CURRENT, False),
        CONF_SMA_ENABLED: data.get(CONF_SMA_ENABLED, False),
        CONF_SMA_MODE: data.get(CONF_SMA_MODE, SMA_MODE_PCAN),
        CONF_LITECAN_HOST: data.get(CONF_LITECAN_HOST, ""),
        CONF_LITECAN_PORT: data.get(CONF_LITECAN_PORT, DEFAULT_LITECAN_PORT),
        CONF_PCAN_INTERFACE: data.get(CONF_PCAN_INTERFACE, DEFAULT_PCAN_INTERFACE),
        CONF_PCAN_CHANNEL: data.get(CONF_PCAN_CHANNEL, DEFAULT_PCAN_CHANNEL),
        CONF_PCAN_BITRATE: data.get(CONF_PCAN_BITRATE, DEFAULT_PCAN_BITRATE),
    }


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def _async_start_sma_transmitter(hass: HomeAssistant, entry: ConfigEntry, name_lower: str) -> None:
    settings = _entry_settings(entry)
    if not settings[CONF_SMA_ENABLED]:
        return

    pack = hass.data[DOMAIN][name_lower]

    def get_state():
        return pack.get("values", {}), pack.get("config", {})

    mode = settings[CONF_SMA_MODE]
    if mode == SMA_MODE_PCAN:
        transmitter = PcanTransmitter(
            hass,
            entry.data["name"],
            settings[CONF_PCAN_INTERFACE],
            settings[CONF_PCAN_CHANNEL],
            settings[CONF_PCAN_BITRATE],
            get_state,
        )
    elif mode == SMA_MODE_LITECAN:
        transmitter = LiteCanTransmitter(
            hass,
            entry.data["name"],
            settings[CONF_LITECAN_HOST],
            settings[CONF_LITECAN_PORT],
            get_state,
        )
    else:
        _LOGGER.error("Unknown Sunny Island transmit mode: %s", mode)
        return

    await transmitter.async_start()
    pack["sma_transmitter"] = transmitter


async def _async_stop_sma_transmitter(pack: dict) -> None:
    transmitter = pack.pop("sma_transmitter", None)
    if transmitter is not None:
        await transmitter.async_stop()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    name = entry.data["name"]
    port = entry.data["port"]
    name_lower = name.lower()
    settings = _entry_settings(entry)

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][name_lower] = {
        "entities": {},
        "values": {},
        "config": settings,
    }

    def udp_callback(sock):
        try:
            data, _ = sock.recvfrom(1024)
            parsed = parse_udp_packet(data, port)
            if parsed:
                name_data = hass.data[DOMAIN][name_lower]
                previous_values = name_data.get("values", {})
                merged_values = {**previous_values, **parsed}

                async_dispatcher_send(
                    hass,
                    SIGNAL_UPDATE_ENTITY.format(name_lower),
                    merged_values,
                )
        except BlockingIOError:
            pass
        except Exception as err:
            _LOGGER.error("[%s] UDP read error on %s: %s", DOMAIN, name, err)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", port))
        sock.setblocking(False)
        hass.loop.add_reader(sock, udp_callback, sock)
        hass.data[DOMAIN][name_lower]["socket"] = sock
        _LOGGER.info("Started UDP listener for %s on port %d", name, port)
    except OSError as err:
        _LOGGER.error("Failed to bind UDP socket on port %d for %s: %s", port, name, err)
        return False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_start_sma_transmitter(hass, entry, name_lower)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    name_lower = entry.data["name"].lower()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and DOMAIN in hass.data and name_lower in hass.data[DOMAIN]:
        data = hass.data[DOMAIN].pop(name_lower)
        await _async_stop_sma_transmitter(data)
        sock = data.get("socket")
        if sock:
            hass.loop.remove_reader(sock)
            sock.close()
        _LOGGER.info("Closed UDP listener for %s", name_lower)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
