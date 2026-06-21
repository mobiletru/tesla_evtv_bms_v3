import logging
import socket

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_MODULE_COUNT, CONF_MODULES_IN_SERIES, DOMAIN, PLATFORMS, SIGNAL_UPDATE_ENTITY
from .pack_config import DEFAULT_PACK, compute_pack_settings
from .parser import parse_udp_packet

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
    }


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    name = entry.data["name"]
    port = entry.data["port"]
    name_lower = name.lower()

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hass.data[DOMAIN][name_lower] = {
        "entities": {},
        "values": {},
        "config": _entry_settings(entry),
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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    name_lower = entry.data["name"].lower()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and DOMAIN in hass.data and name_lower in hass.data[DOMAIN]:
        data = hass.data[DOMAIN].pop(name_lower)
        sock = data.get("socket")
        if sock:
            hass.loop.remove_reader(sock)
            sock.close()
        _LOGGER.info("Closed UDP listener for %s", name_lower)

    return unload_ok
