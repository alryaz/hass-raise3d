import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, Any, Mapping, Sequence

from homeassistant.components.button import ButtonEntityDescription, ButtonEntity

from custom_components.raise3d import (
    make_platform_async_setup_entry,
    wrap_convert_unempty,
    Raise3DEntity,
    Raise3DEntityDescription,
)
from custom_components.raise3d.api import Raise3DPrinterAPI, JobActionValue

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Raise3DButtonEntityDescription(Raise3DEntityDescription, ButtonEntityDescription):
    """A class that represents Raise3D entity description for button object(s)."""

    button_method_name: str
    """Method to call when the button is pressed."""

    button_method_keywords: Mapping[str, Any] | None = None
    button_method_positionals: Sequence[Any] | None = None

    converter: Callable[[Any], float | None] = wrap_convert_unempty(float)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.button_method_name, Callable):
            object.__setattr__(
                self, "button_method_name", self.button_method_name.__name__
            )


class Raise3DButtonEntity(Raise3DEntity[Raise3DButtonEntityDescription], ButtonEntity):
    """A class that represents a Raise3D number entity."""

    def press(self) -> None:
        """Set new value."""
        return asyncio.run_coroutine_threadsafe(
            self.async_press(), self.hass.loop
        ).result()

    async def async_press(self) -> None:
        """Set new value."""
        await self.async_call_method_by_name(
            self.entity_description.button_method_name,
            *(self.entity_description.button_method_positionals or ()),
            **(self.entity_description.button_method_keywords or {}),
        )


# noinspection PyArgumentList
ENTITY_DESCRIPTIONS = [
    Raise3DButtonEntityDescription(
        key="recover_last_job",
        icon="mdi:restart",
        button_method_name=Raise3DPrinterAPI.recover_last_job,
        # device_class=ButtonDeviceClass.RESTART,
    ),
    Raise3DButtonEntityDescription(
        key="move_home",
        icon="mdi:home",
        button_method_name=Raise3DPrinterAPI.move_home,
    ),
]

for axis, directions in {
    "x": ("left", "right"),  # Negative: left, Positive: right
    "y": ("backward", "forward"),  # Negative: backward, Positive: forward
    "z": ("down", "up"),  # Negative: down, Positive: up
}.items():
    for i, direction in enumerate(directions, start=0):
        # noinspection PyArgumentList
        ENTITY_DESCRIPTIONS.append(
            Raise3DButtonEntityDescription(
                key=f"move_{'positive' if i else 'negative'}_{axis}",
                name=f"Relative move {direction}",
                icon="mdi:cursor-move",
                button_method_name=Raise3DPrinterAPI.axis_control,
                button_method_keywords={
                    axis: 1 if i else -1,
                    "is_relative_pos": True,
                },
            )
        )

for action in JobActionValue:
    # noinspection PyArgumentList
    ENTITY_DESCRIPTIONS.append(
        Raise3DButtonEntityDescription(
            key=f"job_action_{action.name.lower()}",
            name=f"{action.name.title()} current job",
            icon=f"mdi:{'play' if action == JobActionValue.RESUME else action.name.lower()}",
            button_method_name=Raise3DPrinterAPI.set_current_job,
            button_method_positionals=[action.value],
        )
    )

async_setup_entry = make_platform_async_setup_entry(
    ENTITY_DESCRIPTIONS, Raise3DButtonEntity, _LOGGER
)
