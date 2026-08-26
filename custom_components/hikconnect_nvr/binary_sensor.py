"""Binary sensors for Hik-Connect NVR."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HikConnectNvrCoordinator


async def async_setup_entry(hass, entry: ConfigEntry[HikConnectNvrCoordinator], async_add_entities: AddEntitiesCallback) -> None:
    """Set up NVR online status."""
    async_add_entities([HikConnectNvrOnline(coordinator=entry.runtime_data)])


class HikConnectNvrOnline(CoordinatorEntity[HikConnectNvrCoordinator], BinarySensorEntity):
    """Whether the NVR is currently visible through Hik-Connect."""

    _attr_has_entity_name = True
    _attr_name = "Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: HikConnectNvrCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = "nvr_online"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "nvr")},
            name="Hik-Connect NVR",
            manufacturer="Hikvision",
            model="Hik-Connect NVR (OpenAPI)",
        )

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["nvr"].get("online"))
