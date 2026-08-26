"""Hik-Connect NVR integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HikConnectDirectClient
from .const import (
    CONF_APP_KEY,
    CONF_SECRET_KEY,
    CONF_SERVER_ADDRESS,
    CONF_STREAM_QUALITY,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import HikConnectNvrCoordinator

type HikConnectNvrConfigEntry = ConfigEntry[HikConnectNvrCoordinator]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: HikConnectNvrConfigEntry) -> bool:
    """Set up Hik-Connect NVR from a config entry."""
    if CONF_APP_KEY not in entry.data:
        _LOGGER.warning(
            "This entry uses the retired Hik-Connect NVR Stream App. Remove it "
            "after confirming the direct Hik-Connect entities work."
        )
        return True

    client = HikConnectDirectClient(
        async_get_clientsession(hass),
        entry.data[CONF_SERVER_ADDRESS],
        entry.data[CONF_APP_KEY],
        entry.data[CONF_SECRET_KEY],
        entry.data[CONF_STREAM_QUALITY],
    )
    coordinator = HikConnectNvrCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HikConnectNvrConfigEntry) -> bool:
    """Unload a config entry."""
    if CONF_APP_KEY not in entry.data:
        return True
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
