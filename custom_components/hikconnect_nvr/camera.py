"""Camera entities for Hik-Connect NVR."""

from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HikConnectNvrCoordinator


async def async_setup_entry(hass, entry: ConfigEntry[HikConnectNvrCoordinator], async_add_entities: AddEntitiesCallback) -> None:
    """Set up cameras from the current discovery result."""
    coordinator = entry.runtime_data
    async_add_entities(HikConnectNvrCamera(coordinator, camera) for camera in coordinator.data["cameras"])


class HikConnectNvrCamera(CoordinatorEntity[HikConnectNvrCoordinator], Camera):
    """A stream-only Hik-Connect camera."""

    _attr_has_entity_name = True
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, coordinator: HikConnectNvrCoordinator, camera: dict) -> None:
        # CoordinatorEntity deliberately does not call super().__init__().
        # Camera has essential stream/cache setup in its own initializer, so
        # both bases must be initialized explicitly.
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._camera_id = camera["id"]
        self._attr_name = camera.get("name") or self._camera_id
        self._attr_unique_id = f"{self._camera_id}_live"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "nvr")},
            name="Hik-Connect NVR",
            manufacturer="Hikvision",
            model="Hik-Connect NVR (OpenAPI)",
        )

    async def stream_source(self) -> str:
        """Return the HLS source for Home Assistant's stream engine."""
        return await self.coordinator.client.stream_url(self._camera_id)

    @property
    def use_stream_for_stills(self) -> bool:
        """Let Home Assistant create stills from the supported HLS stream."""
        return True
