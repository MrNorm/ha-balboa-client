"""Config flow for Balboa Spa (Serial-to-IP)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaFlowFormStep,
    SchemaOptionsFlowHandler,
)

from .const import CONF_SYNC_TIME, DEFAULT_PORT, DOMAIN
from .pybalboa import SpaClient
from .pybalboa.exceptions import SpaConnectionError

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {vol.Required(CONF_SYNC_TIME, default=False): bool}
)
OPTIONS_FLOW = {"init": SchemaFlowFormStep(OPTIONS_SCHEMA)}


async def _validate_input(data: dict[str, Any]) -> dict[str, str]:
    """Open a connection long enough to confirm the spa responds."""
    host = data[CONF_HOST]
    port = data.get(CONF_PORT, DEFAULT_PORT)
    try:
        async with SpaClient(host, port) as spa:
            if not await spa.async_configuration_loaded():
                raise CannotConnect
            return {
                "title": spa.model or f"Balboa Spa ({host})",
                "formatted_mac": format_mac(spa.mac_address),
            }
    except SpaConnectionError as err:
        raise CannotConnect from err


class BalboaSerialConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a Balboa Spa (Serial-to-IP) config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SchemaOptionsFlowHandler:
        """Get the options flow."""
        return SchemaOptionsFlowHandler(config_entry, OPTIONS_FLOW)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                }
            )
            try:
                info = await _validate_input(user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during validation")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    info["formatted_mac"], raise_on_progress=False
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
