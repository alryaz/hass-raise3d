"""Adds config flow for Raise3D Integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL

from custom_components.raise3d import async_initialize_api_from_configuration
from custom_components.raise3d.api import DEFAULT_PRINTER_PORT
from custom_components.raise3d.const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_PORT,
    CONF_PASSWORD,
)

CONFIG_FLOW_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PRINTER_PORT): cv.port,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)


class Raise3DFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Raise3D."""

    VERSION = 2
    MINOR_VERSION = 2
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        schema = CONFIG_FLOW_SCHEMA

        if user_input is not None:
            try:
                raise3d_api = await async_initialize_api_from_configuration(
                    self.hass, user_input
                )
                system_info = await raise3d_api.get_system_info()
            except aiohttp.ClientError as exc:
                if isinstance(exc, aiohttp.ClientResponseError) and exc.status == 403:
                    errors[CONF_PASSWORD] = "invalid_password"
                else:
                    errors[CONF_HOST] = "connection_error"
            else:
                await self.async_set_unique_id(system_info["machine_id"])
                self._abort_if_unique_id_configured()

                # noinspection PyTypeChecker
                return self.async_create_entry(
                    title=system_info["machine_name"], data=user_input
                )

            schema = self.add_suggested_values_to_schema(schema, user_input)

        # noinspection PyTypeChecker
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
