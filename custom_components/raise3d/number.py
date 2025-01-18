import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature

from custom_components.raise3d import (
    Raise3DCoordinatorEntity,
    Raise3DCoordinatorEntityDescription,
    make_platform_async_setup_entry,
    wrap_convert_unempty,
)
from custom_components.raise3d.api import Raise3DPrinterAPI

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Raise3DNumberEntityDescription(
    Raise3DCoordinatorEntityDescription, NumberEntityDescription
):
    """A class that represents Raise3D entity description for number object(s)."""

    commit_method_name: str
    """Method to call when the number is committed."""

    converter: Callable[[Any], float | None] = wrap_convert_unempty(float)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.commit_method_name, Callable):
            object.__setattr__(
                self, "commit_method_name", self.commit_method_name.__name__
            )


class Raise3DNumberEntity(
    Raise3DCoordinatorEntity[Raise3DNumberEntityDescription], NumberEntity
):
    """A class that represents a Raise3D number entity."""

    def set_native_value(self, value: float) -> None:
        """Set new value."""
        return asyncio.run_coroutine_threadsafe(
            self.async_set_native_value(value), self.hass.loop
        ).result()

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        await self.async_call_method_by_name(
            self.entity_description.commit_method_name, value
        )
        await asyncio.sleep(1.5)
        await self.coordinator.async_request_refresh()


# noinspection PyArgumentList
ENTITY_DESCRIPTIONS = [
    Raise3DNumberEntityDescription(
        key="heatbed_tar_temp",
        icon="mdi:heat-wave",
        update_method_name=Raise3DPrinterAPI.get_basic_info,
        commit_method_name=Raise3DPrinterAPI.set_heatbed_temp,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=110,
        mode=NumberMode.BOX,
    ),
    Raise3DNumberEntityDescription(
        key="fan_tar_speed",
        icon="mdi:fan",
        update_method_name=Raise3DPrinterAPI.get_basic_info,
        commit_method_name=Raise3DPrinterAPI.set_fan_speed,
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        mode=NumberMode.BOX,
    ),
]

for nozzle_name, (update_method, commit_flowrate, commit_temp) in {
    "Left nozzle": (
        Raise3DPrinterAPI.get_left_nozzle_info,
        Raise3DPrinterAPI.set_left_nozzle_flowrate,
        Raise3DPrinterAPI.set_left_nozzle_temp,
    ),
    "Right nozzle": (
        Raise3DPrinterAPI.get_right_nozzle_info,
        Raise3DPrinterAPI.set_right_nozzle_flowrate,
        Raise3DPrinterAPI.set_right_nozzle_temp,
    ),
}.items():
    prefix = "".join(word[0].upper() for word in nozzle_name.split(" "))

    # noinspection PyArgumentList
    ENTITY_DESCRIPTIONS.extend(
        [
            Raise3DNumberEntityDescription(
                name=f"{nozzle_name} target extrusion speed",
                key=f"{prefix}_flow_tar_rate",
                attribute="flow_tar_rate",
                icon="mdi:printer-3d-nozzle-outline",
                update_method_name=update_method,
                commit_method_name=commit_flowrate,
                native_unit_of_measurement=PERCENTAGE,
                native_step=1,
                native_min_value=1,
                native_max_value=300,
                mode=NumberMode.BOX,
            ),
            Raise3DNumberEntityDescription(
                name=f"{nozzle_name} target temperature",
                key=f"{prefix}_nozzle_tar_temp",
                attribute="nozzle_tar_temp",
                icon="mdi:printer-3d-nozzle-heat",
                update_method_name=update_method,
                commit_method_name=commit_temp,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                native_step=1,
                mode=NumberMode.BOX,
            ),
        ]
    )

async_setup_entry = make_platform_async_setup_entry(
    ENTITY_DESCRIPTIONS, Raise3DNumberEntity, _LOGGER
)
