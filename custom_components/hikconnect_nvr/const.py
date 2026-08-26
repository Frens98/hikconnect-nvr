"""Constants for Hik-Connect NVR."""

from typing import Final

DOMAIN: Final = "hikconnect_nvr"
PLATFORMS: Final = ["binary_sensor", "camera", "sensor"]
CONF_APP_KEY: Final = "app_key"
CONF_SECRET_KEY: Final = "secret_key"
CONF_SERVER_ADDRESS: Final = "server_address"
CONF_STREAM_QUALITY: Final = "stream_quality"
STREAM_QUALITY_MAIN: Final = "Main stream (HD)"
STREAM_QUALITY_SUB: Final = "Sub stream (SD)"
DEFAULT_SCAN_INTERVAL_SECONDS: Final = 60
