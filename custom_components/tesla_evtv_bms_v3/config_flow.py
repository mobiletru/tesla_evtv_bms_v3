import logging

from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

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
    CONF_NAME,
    CONF_PCAN_BITRATE,
    CONF_PCAN_CHANNEL,
    CONF_PCAN_INTERFACE,
    CONF_PORT,
    CONF_SMA_ENABLED,
    CONF_SMA_MODE,
    DEFAULT_LITECAN_PORT,
    DEFAULT_PCAN_BITRATE,
    DEFAULT_PCAN_CHANNEL,
    DEFAULT_PCAN_INTERFACE,
    DOMAIN,
    PCAN_INTERFACE_PCAN,
    PCAN_INTERFACE_SOCKETCAN,
    SMA_MODE_LITECAN,
    SMA_MODE_PCAN,
)
from .pack_config import (
    DEFAULT_CHARGE_CURRENT,
    DEFAULT_DISCHARGE_CURRENT,
    DEFAULT_MODULE_COUNT,
    DEFAULT_MODULES_IN_SERIES,
    DEFAULT_PACK,
    compute_pack_settings,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 6850
DEFAULT_MIN_VOLTS = 3.2
DEFAULT_MAX_VOLTS = 4.1


def _resolved_pack(defaults: dict | None = None) -> dict:
    defaults = defaults or {}
    module_count = int(defaults.get(CONF_MODULE_COUNT, DEFAULT_MODULE_COUNT))
    modules_in_series = int(defaults.get(CONF_MODULES_IN_SERIES, DEFAULT_MODULES_IN_SERIES))
    min_cell = float(defaults.get("min_cell_volts", DEFAULT_MIN_VOLTS))
    max_cell = float(defaults.get("max_cell_volts", DEFAULT_MAX_VOLTS))
    computed = compute_pack_settings(module_count, modules_in_series, min_cell, max_cell)
    computed["pack_size"] = defaults.get("pack_size", computed["pack_size"])
    computed["cells_in_series"] = defaults.get("cells_in_series", computed["cells_in_series"])
    computed[CONF_CHARGE_VOLTAGE] = defaults.get(CONF_CHARGE_VOLTAGE, computed["charge_voltage"])
    computed[CONF_DISCHARGE_VOLTAGE] = defaults.get(
        CONF_DISCHARGE_VOLTAGE, computed["discharge_voltage_limit"]
    )
    return computed


def _pack_schema(defaults: dict | None = None) -> vol.Schema:
    defaults = defaults or {}
    pack = _resolved_pack(defaults)
    return vol.Schema(
        {
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.Coerce(int),
            vol.Required(
                CONF_MODULE_COUNT,
                default=int(defaults.get(CONF_MODULE_COUNT, DEFAULT_MODULE_COUNT)),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=64)),
            vol.Required(
                CONF_MODULES_IN_SERIES,
                default=int(defaults.get(CONF_MODULES_IN_SERIES, DEFAULT_MODULES_IN_SERIES)),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
            vol.Required("pack_size", default=pack["pack_size"]): vol.Coerce(float),
            vol.Required("cells_in_series", default=pack["cells_in_series"]): vol.Coerce(int),
            vol.Required("min_cell_volts", default=defaults.get("min_cell_volts", DEFAULT_MIN_VOLTS)): vol.Coerce(float),
            vol.Required("max_cell_volts", default=defaults.get("max_cell_volts", DEFAULT_MAX_VOLTS)): vol.Coerce(float),
            vol.Required(CONF_SMA_ENABLED, default=defaults.get(CONF_SMA_ENABLED, False)): bool,
            vol.Optional(CONF_SMA_MODE, default=defaults.get(CONF_SMA_MODE, SMA_MODE_PCAN)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=SMA_MODE_PCAN, label="Peak PCAN USB adapter"),
                        selector.SelectOptionDict(value=SMA_MODE_LITECAN, label="EVTV LiteCAN UDP gateway"),
                    ]
                )
            ),
            vol.Optional(CONF_PCAN_INTERFACE, default=defaults.get(CONF_PCAN_INTERFACE, DEFAULT_PCAN_INTERFACE)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=PCAN_INTERFACE_SOCKETCAN,
                            label="SocketCAN (can0 on Home Assistant OS)",
                        ),
                        selector.SelectOptionDict(
                            value=PCAN_INTERFACE_PCAN,
                            label="Peak PCAN API (PCAN_USBBUS1 on Windows)",
                        ),
                    ]
                )
            ),
            vol.Optional(CONF_PCAN_CHANNEL, default=defaults.get(CONF_PCAN_CHANNEL, DEFAULT_PCAN_CHANNEL)): str,
            vol.Optional(CONF_PCAN_BITRATE, default=defaults.get(CONF_PCAN_BITRATE, DEFAULT_PCAN_BITRATE)): vol.Coerce(int),
            vol.Optional(CONF_LITECAN_HOST, default=defaults.get(CONF_LITECAN_HOST, "")): str,
            vol.Optional(CONF_LITECAN_PORT, default=defaults.get(CONF_LITECAN_PORT, DEFAULT_LITECAN_PORT)): vol.Coerce(int),
            vol.Optional(CONF_CHARGE_VOLTAGE, default=pack[CONF_CHARGE_VOLTAGE]): vol.Coerce(float),
            vol.Optional(CONF_CHARGE_CURRENT, default=defaults.get(CONF_CHARGE_CURRENT, DEFAULT_CHARGE_CURRENT)): vol.Coerce(float),
            vol.Optional(CONF_DISCHARGE_CURRENT, default=defaults.get(CONF_DISCHARGE_CURRENT, DEFAULT_DISCHARGE_CURRENT)): vol.Coerce(float),
            vol.Optional(CONF_DISCHARGE_VOLTAGE, default=pack[CONF_DISCHARGE_VOLTAGE]): vol.Coerce(float),
            vol.Optional(CONF_INVERT_CURRENT, default=defaults.get(CONF_INVERT_CURRENT, False)): bool,
        }
    )


def _apply_module_defaults(user_input: dict) -> dict:
    """Recompute pack size and SMA voltages from module layout."""
    computed = compute_pack_settings(
        int(user_input[CONF_MODULE_COUNT]),
        int(user_input[CONF_MODULES_IN_SERIES]),
        float(user_input["min_cell_volts"]),
        float(user_input["max_cell_volts"]),
    )
    user_input["pack_size"] = computed["pack_size"]
    user_input["cells_in_series"] = computed["cells_in_series"]
    user_input["nominal_voltage"] = computed["nominal_voltage"]
    user_input[CONF_CHARGE_VOLTAGE] = computed["charge_voltage"]
    user_input[CONF_DISCHARGE_VOLTAGE] = computed["discharge_voltage_limit"]
    return user_input


def _validate_sma(user_input: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not user_input.get(CONF_SMA_ENABLED):
        return errors

    mode = user_input.get(CONF_SMA_MODE, SMA_MODE_PCAN)
    if mode == SMA_MODE_PCAN and not user_input.get(CONF_PCAN_CHANNEL):
        errors[CONF_PCAN_CHANNEL] = "required"
    if mode == SMA_MODE_LITECAN and not user_input.get(CONF_LITECAN_HOST):
        errors[CONF_LITECAN_HOST] = "required"
    return errors


class TeslaEVTVBMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            errors = _validate_sma(user_input)
            if not errors:
                user_input = _apply_module_defaults(user_input)
                await self.async_set_unique_id(user_input[CONF_NAME].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_pack_schema(user_input),
            errors=errors,
            description_placeholders={
                "info": (
                    f"36-module default: 2S18P, {DEFAULT_PACK['nominal_voltage']} V nominal, "
                    f"{DEFAULT_PACK['pack_size']} kWh"
                ),
            },
        )


class TeslaEVTVBMSOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors = {}
        defaults = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            errors = _validate_sma(user_input)
            if not errors:
                return self.async_create_entry(title="", data=_apply_module_defaults(user_input))

        return self.async_show_form(
            step_id="init",
            data_schema=_pack_schema({**defaults, **(user_input or {})}),
            errors=errors,
        )


async def async_get_options_flow(config_entry):
    return TeslaEVTVBMSOptionsFlowHandler(config_entry)
