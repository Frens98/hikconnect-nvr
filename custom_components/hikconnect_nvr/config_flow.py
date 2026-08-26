"""Config flow for direct Hik-Connect NVR setup."""

from __future__ import annotations

from hashlib import sha256

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import HikConnectDirectClient, HikConnectNvrApiError
from .const import (
    CONF_APP_KEY,
    CONF_SECRET_KEY,
    CONF_SERVER_ADDRESS,
    CONF_STREAM_QUALITY,
    DOMAIN,
    STREAM_QUALITY_MAIN,
    STREAM_QUALITY_SUB,
)

DEFAULT_SERVER_ADDRESS = "https://ieu.hikcentralconnect.com"


class HikConnectNvrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle direct Hik-Connect OpenAPI setup."""

    VERSION = 2

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Set up direct Hik-Connect HLS streaming."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = HikConnectDirectClient(
                async_get_clientsession(self.hass),
                user_input[CONF_SERVER_ADDRESS],
                user_input[CONF_APP_KEY],
                user_input[CONF_SECRET_KEY],
                user_input[CONF_STREAM_QUALITY],
            )
            try:
                await client.cameras()
            except HikConnectNvrApiError:
                errors["base"] = "cannot_connect"
            else:
                app_key_hash = sha256(user_input[CONF_APP_KEY].encode()).hexdigest()
                await self.async_set_unique_id(f"direct:{app_key_hash}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Hik-Connect NVR", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SERVER_ADDRESS,
                        default=user_input.get(CONF_SERVER_ADDRESS, DEFAULT_SERVER_ADDRESS)
                        if user_input
                        else DEFAULT_SERVER_ADDRESS,
                    ): str,
                    vol.Required(CONF_APP_KEY, default=user_input.get(CONF_APP_KEY, "") if user_input else ""): str,
                    vol.Required(CONF_SECRET_KEY): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Required(
                        CONF_STREAM_QUALITY,
                        default=user_input.get(CONF_STREAM_QUALITY, STREAM_QUALITY_MAIN)
                        if user_input
                        else STREAM_QUALITY_MAIN,
                    ): vol.In([STREAM_QUALITY_MAIN, STREAM_QUALITY_SUB]),
                }
            ),
            errors=errors,
        )

    async def async_migrate_entry(self, hass, config_entry: ConfigEntry) -> bool:
        """Allow retired Stream App entries to be removed from the UI cleanly."""
        if config_entry.version == 1:
            hass.config_entries.async_update_entry(config_entry, version=self.VERSION)
        return True
