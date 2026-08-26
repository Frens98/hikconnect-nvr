"""Sensors for Hik-Connect NVR."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfInformation, UnitOfTemperature, UnitOfTime
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HikConnectNvrCoordinator


async def async_setup_entry(hass, entry: ConfigEntry[HikConnectNvrCoordinator], async_add_entities: AddEntitiesCallback) -> None:
    """Set up NVR and HDD data sensors."""
    coordinator = entry.runtime_data
    async_add_entities([
        HikConnectNvrValue(coordinator, "Camera count", "camera_count", "cameraCount"),
        HikConnectNvrValue(coordinator, "HDD status", "hdd_status", "status", disk=True),
        HikConnectNvrValue(
            coordinator,
            "HDD free space",
            "hdd_free_space",
            "freeSpace",
            disk=True,
            device_class=SensorDeviceClass.DATA_SIZE,
            native_unit=UnitOfInformation.MEGABYTES,
        ),
        HikConnectNvrValue(
            coordinator,
            "HDD capacity",
            "hdd_capacity",
            "capacity",
            disk=True,
            device_class=SensorDeviceClass.DATA_SIZE,
            native_unit=UnitOfInformation.MEGABYTES,
        ),
        HikConnectNvrValue(
            coordinator,
            "HDD temperature",
            "hdd_temperature",
            "temperature",
            disk=True,
            device_class=SensorDeviceClass.TEMPERATURE,
            native_unit=UnitOfTemperature.CELSIUS,
        ),
        HikConnectNvrValue(
            coordinator,
            "HDD powered-on days",
            "hdd_powered_on_days",
            "powerOnDays",
            disk=True,
            device_class=SensorDeviceClass.DURATION,
            native_unit=UnitOfTime.DAYS,
        ),
        HikConnectNvrValue(coordinator, "HDD SMART health", "hdd_smart_health", "smartHealth", disk=True),
    ])


class HikConnectNvrValue(CoordinatorEntity[HikConnectNvrCoordinator], SensorEntity):
    """A read-only value reported by the NVR."""

    _attr_has_entity_name = True
    def __init__(
        self,
        coordinator: HikConnectNvrCoordinator,
        name: str,
        unique_id: str,
        field: str,
        *,
        disk: bool = False,
        device_class: SensorDeviceClass | None = None,
        native_unit: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "nvr")},
            name="Hik-Connect NVR",
            manufacturer="Hikvision",
            model="Hik-Connect NVR (OpenAPI)",
        )
        self._field = field
        self._disk = disk
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = native_unit

    @property
    def native_value(self):
        source = self.coordinator.data["nvr"].get("disk") or {} if self._disk else self.coordinator.data["nvr"]
        value = source.get(self._field)
        if self._attr_device_class is not None and value not in (None, ""):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
        return value
