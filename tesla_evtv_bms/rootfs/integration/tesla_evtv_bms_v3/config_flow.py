from homeassistant import config_entries
import voluptuous as vol

from .const import CONF_MODULE_COUNT, CONF_MODULES_IN_SERIES, CONF_NAME, CONF_PORT, DOMAIN
from .pack_config import (
    DEFAULT_MODULE_COUNT,
    DEFAULT_MODULES_IN_SERIES,
    DEFAULT_PACK,
    compute_pack_settings,
)

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
        }
    )


def _apply_module_defaults(user_input: dict) -> dict:
    computed = compute_pack_settings(
        int(user_input[CONF_MODULE_COUNT]),
        int(user_input[CONF_MODULES_IN_SERIES]),
        float(user_input["min_cell_volts"]),
        float(user_input["max_cell_volts"]),
    )
    user_input["pack_size"] = computed["pack_size"]
    user_input["cells_in_series"] = computed["cells_in_series"]
    user_input["nominal_voltage"] = computed["nominal_voltage"]
    return user_input


class TeslaEVTVBMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            user_input = _apply_module_defaults(user_input)
            await self.async_set_unique_id(user_input[CONF_NAME].lower())
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_pack_schema(user_input),
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
        defaults = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            return self.async_create_entry(title="", data=_apply_module_defaults(user_input))

        return self.async_show_form(
            step_id="init",
            data_schema=_pack_schema({**defaults, **(user_input or {})}),
        )


async def async_get_options_flow(config_entry):
    return TeslaEVTVBMSOptionsFlowHandler(config_entry)
