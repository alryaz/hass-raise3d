"""Binary sensor platform for Raise3D."""

__all__ = (
    "async_setup_entry",
    "ENTITY_DESCRIPTIONS",
    "Raise3DBinarySensorEntity",
    "Raise3DBinarySensorEntityDescription",
)

import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import callback

from custom_components.raise3d import (
    Raise3DCoordinatorEntity,
    Raise3DCoordinatorEntityDescription,
    make_platform_async_setup_entry,
)
from custom_components.raise3d.api import Raise3DPrinterAPI, APIDataResponse
from custom_components.raise3d.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Raise3DBinarySensorEntityDescription(
    Raise3DCoordinatorEntityDescription, BinarySensorEntityDescription
):
    """A class that represents Raise3D entity description for binary sensor object(s)."""

    icon: str | tuple[str, str] | None = None
    """Icon to use in the frontend, if any; two icons for on and off/unavailable states."""


class Raise3DBinarySensorEntity(
    Raise3DCoordinatorEntity[BinarySensorEntityDescription], BinarySensorEntity
):
    @property
    def icon(self) -> str | None:
        """Return the icon."""
        icon = self.entity_description.icon
        if isinstance(icon, tuple):
            return icon[0] if self.available and self.is_on else icon[1]

    @callback
    def _process_coordinator_data(self, *args, **kwargs) -> None:
        """Handle updated data from the coordinator."""
        super()._process_coordinator_data(*args, **kwargs)
        self._attr_is_on = self._attr_native_value is True if self.available else None


ENTITY_DESCRIPTIONS = [
    Raise3DBinarySensorEntityDescription(
        key="is_camera_connected",
        icon=("mdi:webcam", "mdi:webcam-off"),
        update_method_name=Raise3DPrinterAPI.get_camera_info,
        converter=lambda x: isinstance(x, str)
        and x.lower() == "true"
        or isinstance(x, bool)
        and x,
        device_class=BinarySensorDeviceClass.PRESENCE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
]

async_setup_entry = make_platform_async_setup_entry(
    ENTITY_DESCRIPTIONS, Raise3DBinarySensorEntity, _LOGGER
)
