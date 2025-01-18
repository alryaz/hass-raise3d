"""Raise3D Integration camera entity."""

from __future__ import annotations

__all__ = (
    "async_setup_entry",
    "ENTITY_DESCRIPTIONS",
    "Raise3DCamera",
    "Raise3DCameraEntityDescription",
)

import asyncio
import logging
from dataclasses import dataclass

from homeassistant.components.camera import (
    Camera,
    CameraEntityFeature,
    CameraEntityDescription,
)

from custom_components.raise3d import (
    Raise3DCoordinatorEntity,
    make_platform_async_setup_entry,
    Raise3DCoordinatorEntityDescription,
)
from custom_components.raise3d.api import Raise3DPrinterAPI, APIDataResponse
from custom_components.raise3d.const import DEFAULT_MANUFACTURER

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Raise3DCameraEntityDescription(
    Raise3DCoordinatorEntityDescription, CameraEntityDescription
):
    """A class that represents Raise3D entity description for camera object(s)."""


class Raise3DCamera(Raise3DCoordinatorEntity[Raise3DCameraEntityDescription], Camera):
    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_brand = DEFAULT_MANUFACTURER

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        Camera.__init__(self)

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        return asyncio.run_coroutine_threadsafe(
            self.async_camera_image(width, height), self.hass.loop
        ).result()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        return await self.coordinator.raise3d_api.get_snapshot()

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        await self.coordinator.async_request_refresh()
        if not (
            self.coordinator.data and self.coordinator.data.get("is_camera_connected")
        ):
            return None
        return self.coordinator.raise3d_api.camera_stream_url

    def _process_coordinator_data(self, data: APIDataResponse) -> None:
        # Since there is a single camera entity, we can just check if the camera is connected
        self._attr_available = bool(self.coordinator.data.get("is_camera_connected"))
        super()._process_coordinator_data(data)
        if self.stream:
            # @TODO: formatted this way in case we need to do something with
            #        the stream further down the line.
            if not self._attr_available:
                pass
            elif self.stream.source != self.coordinator.raise3d_api.camera_stream_url:
                self.logger.debug("Willingly updating stream URL on change for %s", self.entity_id)
                self.stream.update_source(self.coordinator.raise3d_api.camera_stream_url)


# noinspection PyArgumentList
ENTITY_DESCRIPTIONS = [
    Raise3DCameraEntityDescription(
        key="camera",
        update_method_name=Raise3DPrinterAPI.get_camera_info,
    ),
]

async_setup_entry = make_platform_async_setup_entry(
    ENTITY_DESCRIPTIONS, Raise3DCamera, _LOGGER
)
