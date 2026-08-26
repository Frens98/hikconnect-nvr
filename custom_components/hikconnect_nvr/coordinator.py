"""Coordinator for Hik-Connect NVR."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HikConnectNvrApiError
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN


class HikConnectNvrCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch cameras and NVR health from the Stream service."""

    def __init__(self, hass: HomeAssistant, client) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            cameras = await self.client.cameras()
            nvr = await self.client.nvr()
        except HikConnectNvrApiError as err:
            raise UpdateFailed(f"Unable to update Hik-Connect NVR: {err}") from err
        return {"cameras": cameras, "nvr": nvr}
