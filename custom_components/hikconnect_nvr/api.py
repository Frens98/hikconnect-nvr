"""Direct Hik-Connect OpenAPI client."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from xml.etree import ElementTree

from aiohttp import ClientError, ClientSession


class HikConnectNvrApiError(Exception):
    """Raised when Hik-Connect data cannot be retrieved."""


class HikConnectDirectClient:
    """Experimental direct Hik-Connect OpenAPI client.

    This returns Hikvision's original, time-limited HLS URL directly to Home
    Assistant's stream engine; no separate local stream service is required.
    """

    def __init__(
        self,
        session: ClientSession,
        server_address: str,
        app_key: str,
        secret_key: str,
        stream_quality: str,
    ) -> None:
        self._session = session
        self._server_address = server_address.rstrip("/")
        self._app_key = app_key
        self._secret_key = secret_key
        self._stream_quality = "2" if stream_quality.upper().startswith("SUB") else "1"
        self._token_lock = asyncio.Lock()
        self._access_token: str | None = None
        self._area_domain: str | None = None
        self._token_expires_at = datetime.min.replace(tzinfo=UTC)
        self._cameras: dict[str, dict[str, Any]] = {}

    async def cameras(self) -> list[dict[str, Any]]:
        """Return all cameras visible to the OpenAPI application."""
        cameras: list[dict[str, Any]] = []
        for page_index in range(1, 100):
            result = await self._api_post(
                "/api/hccgw/resource/v1/areas/cameras/get",
                {
                    "pageIndex": str(page_index),
                    "pageSize": 500,
                    "filter": {
                        "areaID": "-1",
                        "includeSubArea": "1",
                        "deviceID": "",
                        "deviceSerialNo": "",
                    },
                },
            )
            page = result.get("data", {}).get("camera", [])
            if not isinstance(page, list):
                raise HikConnectNvrApiError("Invalid camera response")
            for value in page:
                if not isinstance(value, dict) or not value.get("id"):
                    continue
                device = value.get("device") or {}
                device_info = device.get("devInfo") or {}
                camera = {
                    "id": str(value["id"]),
                    "name": value.get("name") or str(value["id"]),
                    "device_serial": device_info.get("serialNo") or "",
                    "device_id": device_info.get("id") or "",
                }
                cameras.append(camera)
                self._cameras[camera["id"]] = camera
            if len(page) < 500:
                break
        return cameras

    async def nvr(self) -> dict[str, Any]:
        """Return NVR availability and HDD data, when the proxy exposes it."""
        cameras = await self.cameras()
        disk = await self._disk(cameras[0]) if cameras else None
        return {"online": bool(cameras), "cameraCount": len(cameras), "disk": disk}

    async def stream_url(self, camera_id: str) -> str:
        """Return the unmodified, temporary Hikvision HLS URL."""
        camera = self._cameras.get(camera_id)
        if camera is None:
            await self.cameras()
            camera = self._cameras.get(camera_id)
        if camera is None:
            raise HikConnectNvrApiError(f"Unknown camera: {camera_id}")
        if not camera["device_serial"]:
            raise HikConnectNvrApiError(f"Hik-Connect returned no device serial for camera {camera_id}")
        result = await self._api_post(
            "/api/hccgw/video/v1/live/address/get",
            {
                "resourceId": camera_id,
                "deviceSerial": camera["device_serial"],
                "type": "1",
                "protocol": 2,
                "quality": self._stream_quality,
                "expireTime": 600,
            },
        )
        url = result.get("data", {}).get("url")
        if not isinstance(url, str) or not url:
            raise HikConnectNvrApiError("Hik-Connect returned no HLS live stream URL")
        return url

    async def _disk(self, camera: dict[str, Any]) -> dict[str, str] | None:
        if not camera["device_id"]:
            return None

        async def get_isapi(path: str) -> ElementTree.Element:
            result = await self._api_post(
                "/api/hccgw/video/v1/isapi/proxypass",
                {
                    "method": "GET",
                    "url": path,
                    "id": camera["device_id"],
                    "contentType": "application/xml",
                    "body": "",
                },
            )
            payload = result.get("data")
            if not isinstance(payload, str):
                raise HikConnectNvrApiError("Hik-Connect returned invalid NVR storage data")
            return ElementTree.fromstring(payload)

        try:
            storage = await get_isapi("/ISAPI/ContentMgmt/Storage/hdd")
            hdd = next((element for element in storage.iter() if _local_name(element.tag) == "hdd"), None)
            if hdd is None:
                return None
            disk_id = _value(hdd, "id") or "1"
            smart = await get_isapi(f"/ISAPI/ContentMgmt/Storage/hdd/{disk_id}/SMARTTest/status")
        except (ElementTree.ParseError, HikConnectNvrApiError):
            return None

        return {
            "name": _value(hdd, "hddName"),
            "model": _value(hdd, "hddModel"),
            "status": _value(hdd, "status"),
            "capacity": _value(hdd, "capacity"),
            "freeSpace": _value(hdd, "freeSpace"),
            "temperature": _value(smart, "temprature"),
            "powerOnDays": _value(smart, "powerOnDay"),
            "smartStatus": _value(smart, "selfEvaluaingStatus"),
            "smartHealth": _value(smart, "allEvaluaingStatus"),
            "smartTestStatus": _value(smart, "selfTestStatus"),
        }

    async def _api_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        token = await self._token()
        if self._area_domain is None:
            raise HikConnectNvrApiError("Hik-Connect returned no API area domain")
        try:
            async with self._session.post(
                f"{self._area_domain.rstrip('/')}{path}",
                json=body,
                headers={"Token": token},
                raise_for_status=True,
            ) as response:
                result = await response.json(content_type=None)
        except (ClientError, TimeoutError, ValueError) as err:
            raise HikConnectNvrApiError(str(err)) from err
        return _success(result, path)

    async def _token(self) -> str:
        if self._access_token and self._token_expires_at > datetime.now(UTC) + timedelta(minutes=5):
            return self._access_token
        async with self._token_lock:
            if self._access_token and self._token_expires_at > datetime.now(UTC) + timedelta(minutes=5):
                return self._access_token
            try:
                async with self._session.post(
                    f"{self._server_address}/api/hccgw/platform/v1/token/get",
                    json={"appKey": self._app_key, "secretKey": self._secret_key},
                    raise_for_status=True,
                ) as response:
                    result = await response.json(content_type=None)
            except (ClientError, TimeoutError, ValueError) as err:
                raise HikConnectNvrApiError(str(err)) from err
            data = _success(result, "token/get").get("data", {})
            token = data.get("accessToken")
            area_domain = data.get("areaDomain")
            expires_at = data.get("expireTime")
            if not isinstance(token, str) or not isinstance(area_domain, str) or not isinstance(expires_at, int):
                raise HikConnectNvrApiError("Hik-Connect returned an invalid token response")
            self._access_token = token
            self._area_domain = area_domain
            self._token_expires_at = datetime.fromtimestamp(expires_at, UTC)
            return token


def _success(result: Any, operation: str) -> dict[str, Any]:
    if not isinstance(result, dict) or str(result.get("errorCode")) != "0":
        message = result.get("message") if isinstance(result, dict) else "Invalid response"
        raise HikConnectNvrApiError(f"Hik-Connect {operation} failed: {message}")
    return result


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _value(root: ElementTree.Element, name: str) -> str:
    element = next((value for value in root.iter() if _local_name(value.tag) == name), None)
    return element.text or "" if element is not None else ""
