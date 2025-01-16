"""Setup Sensor platform for Raise3D."""

from __future__ import annotations

__all__ = (
    "async_setup_entry",
    "ENTITY_DESCRIPTIONS",
    "Raise3DSensor",
    "Raise3DSensorEntityDescription",
)

import logging
from dataclasses import dataclass
from datetime import datetime, UTC

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfInformation,
    EntityCategory,
    UnitOfLength,
    UnitOfTime,
    PERCENTAGE,
    UnitOfTemperature,
)

from custom_components.raise3d import (
    Raise3DCoordinatorEntity,
    Raise3DCoordinatorEntityDescription,
    make_platform_async_setup_entry,
    wrap_convert_unempty,
)
from custom_components.raise3d.api import (
    Raise3DPrinterAPI,
    JobStatusValue,
    RunningStatusValue,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class Raise3DSensorEntityDescription(
    Raise3DCoordinatorEntityDescription, SensorEntityDescription
):
    """Describes Raise3D sensor entity."""


# noinspection PyArgumentList
ED_PRINTER_SYSTEM_INFORMATION = [
    Raise3DSensorEntityDescription(
        key="Serial_number",
        icon="mdi:numeric",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="api_version",
        icon="mdi:numeric",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="battery",
        icon="mdi:battery-outline",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        converter=wrap_convert_unempty(float),
    ),
    Raise3DSensorEntityDescription(
        key="brightness",
        icon="mdi:brightness-6",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        converter=wrap_convert_unempty(int),
    ),
    Raise3DSensorEntityDescription(
        key="date_time",
        icon="mdi:calendar-clock",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        device_class=SensorDeviceClass.TIMESTAMP,
        converter=wrap_convert_unempty(
            lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        ),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    Raise3DSensorEntityDescription(
        key="firmware_version",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="language",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    Raise3DSensorEntityDescription(
        key="machine_id",
        icon="mdi:printer-3d",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="machine_ip",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    Raise3DSensorEntityDescription(
        key="machine_name",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="model",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="nozzies_num",
        icon="mdi:printer-3d-nozzle",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="storage_available",
        icon="mdi:sd",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    Raise3DSensorEntityDescription(
        key="update",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="version",
        icon="mdi:numeric",
        update_method_name=Raise3DPrinterAPI.get_system_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
]

# noinspection PyArgumentList
ED_CAMERA_INFORMATION = [
    Raise3DSensorEntityDescription(
        key="camerserver_URI",
        icon="mdi:ip-network-outline",
        update_method_name=Raise3DPrinterAPI.get_camera_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    Raise3DSensorEntityDescription(
        key="password",
        icon="mdi:key",
        update_method_name=Raise3DPrinterAPI.get_camera_info,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=True,
    ),
    #     Raise3DSensorEntityDescription(
    #         #         key="user_name",
    #         icon="mdi:account",
    #         update_method_name=Raise3DPrinterAPI.get_camera_info,
    #     ),
]

# noinspection PyArgumentList
ED_PRINTER_RUNNING_STATUS = [
    Raise3DSensorEntityDescription(
        key="running_status",
        icon="mdi:state-machine",
        update_method_name=Raise3DPrinterAPI.get_running_status,
        device_class=SensorDeviceClass.ENUM,
        options=[status.value for status in RunningStatusValue],
    ),
]

# noinspection PyArgumentList
ED_PRINTER_BASIC_INFORMATION = [
    Raise3DSensorEntityDescription(
        key="fan_cur_speed",
        icon="mdi:fan",
        update_method_name=Raise3DPrinterAPI.get_basic_info,
    ),
    # Raise3DSensorEntityDescription(
    #     #     key="fan_tar_speed",
    #     icon="mdi:fan",
    #     update_method_name=Raise3DPrinterAPI.get_basic_info,
    # ),
    Raise3DSensorEntityDescription(
        key="feed_cur_rate",
        icon="mdi:printer-3d-nozzle-outline",
        update_method_name=Raise3DPrinterAPI.get_basic_info,
    ),
    Raise3DSensorEntityDescription(
        key="feed_tar_rate",
        icon="mdi:printer-3d-nozzle-outline",
        update_method_name=Raise3DPrinterAPI.get_basic_info,
    ),
    Raise3DSensorEntityDescription(
        key="heatbed_cur_temp",
        icon="mdi:heat-wave",
        update_method_name=Raise3DPrinterAPI.get_basic_info,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    # Raise3DSensorEntityDescription(
    #     #     key="heatbed_tar_temp",
    #     icon="mdi:heat-wave",
    #     update_method_name=Raise3DPrinterAPI.get_basic_info,
    #     device_class=SensorDeviceClass.TEMPERATURE,
    #     state_class=SensorStateClass.MEASUREMENT,
    #     native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    # ),
]

ED_NOZZLE_INFORMATION = []

for nozzle_name, update_method in {
    "Left nozzle": Raise3DPrinterAPI.get_left_nozzle_info,
    "Right nozzle": Raise3DPrinterAPI.get_right_nozzle_info,
}.items():
    prefix = "".join([word[0].upper() for word in nozzle_name.split()])
    # noinspection PyArgumentList
    ED_NOZZLE_INFORMATION.extend(
        [
            Raise3DSensorEntityDescription(
                # name=f"{nozzle_name} current extrusion speed",
                key=f"{prefix}_flow_cur_rate",
                attribute="flow_cur_rate",
                icon="mdi:printer-3d-nozzle-outline",
                update_method_name=update_method,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=PERCENTAGE,
            ),
            # Raise3DSensorEntityDescription(
            #     name=f"{nozzle_name} target extrusion speed",
            #     key=f"{prefix}_flow_tar_rate",
            #     attribute="flow_tar_rate",
            #     icon="mdi:printer-3d-nozzle-outline",
            #     update_method_name=update_method,
            #     state_class=SensorStateClass.MEASUREMENT,
            #     native_unit_of_measurement=PERCENTAGE,
            # ),
            Raise3DSensorEntityDescription(
                # name=f"{nozzle_name} current temperature",
                key=f"{prefix}_nozzle_cur_temp",
                attribute="nozzle_cur_temp",
                icon="mdi:printer-3d-nozzle-heat",
                update_method_name=update_method,
                device_class=SensorDeviceClass.TEMPERATURE,
                state_class=SensorStateClass.MEASUREMENT,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            ),
            # Raise3DSensorEntityDescription(
            #     name=f"{nozzle_name} target temperature",
            #     key=f"{prefix}_nozzle_tar_temp",
            #     attribute="nozzle_tar_temp",
            #     icon="mdi:printer-3d-nozzle-heat",
            #     update_method_name=update_method,
            #     device_class=SensorDeviceClass.TEMPERATURE,
            #     state_class=SensorStateClass.MEASUREMENT,
            #     native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            # ),
        ]
    )

# noinspection PyArgumentList
ED_PRINTER_CURRENT_JOB_INFORMATION = [
    Raise3DSensorEntityDescription(
        key="file_name",
        icon="mdi:file-outline",
        update_method_name=Raise3DPrinterAPI.get_current_job,
    ),
    Raise3DSensorEntityDescription(
        key="print_progress",
        # icon="mdi:progress-helper",
        update_method_name=Raise3DPrinterAPI.get_current_job,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=PERCENTAGE,
    ),
    Raise3DSensorEntityDescription(
        key="printed_layer",
        icon="mdi:layers",
        update_method_name=Raise3DPrinterAPI.get_current_job,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    Raise3DSensorEntityDescription(
        key="total_layer",
        icon="mdi:layers",
        update_method_name=Raise3DPrinterAPI.get_current_job,
    ),
    Raise3DSensorEntityDescription(
        key="printed_time",
        icon="mdi:clock",
        update_method_name=Raise3DPrinterAPI.get_current_job,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
    ),
    Raise3DSensorEntityDescription(
        key="total_time",
        # icon="mdi:clock",
        update_method_name=Raise3DPrinterAPI.get_current_job,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
    ),
    Raise3DSensorEntityDescription(
        key="remaining_time",
        # icon="mdi:clock",
        update_method_name=Raise3DPrinterAPI.get_current_job,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
    ),
    Raise3DSensorEntityDescription(
        key="job_id",
        update_method_name=Raise3DPrinterAPI.get_current_job,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    Raise3DSensorEntityDescription(
        key="job_status",
        icon="mdi:bell-circle-outline",
        update_method_name=Raise3DPrinterAPI.get_current_job,
        device_class=SensorDeviceClass.ENUM,
        options=[status.value for status in JobStatusValue],
    ),
]


# noinspection PyArgumentList
ED_STATISTICS = [
    Raise3DSensorEntityDescription(
        key="printed_file_num",
        icon="mdi:file-multiple-outline",
        update_method_name=Raise3DPrinterAPI.get_statistics,
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    Raise3DSensorEntityDescription(
        key="printed_total_time",
        icon="mdi:timer-sand",
        update_method_name=Raise3DPrinterAPI.get_statistics,
        native_unit_of_measurement="seconds",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    Raise3DSensorEntityDescription(
        key="printed_used_filament_left",
        icon="mdi:printer-3d-nozzle-outline",
        update_method_name=Raise3DPrinterAPI.get_statistics,
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        converter=wrap_convert_unempty(float),
    ),
    Raise3DSensorEntityDescription(
        key="printed_used_filament_right",
        icon="mdi:printer-3d-nozzle-outline",
        update_method_name=Raise3DPrinterAPI.get_statistics,
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        converter=wrap_convert_unempty(float),
    ),
    Raise3DSensorEntityDescription(
        key="printed_used_filament",
        icon="mdi:printer-3d-nozzle-outline",
        update_method_name=Raise3DPrinterAPI.get_statistics,
        native_unit_of_measurement=UnitOfLength.METERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        converter=wrap_convert_unempty(float),
    ),
]


ENTITY_DESCRIPTIONS = (
    ED_PRINTER_SYSTEM_INFORMATION
    + ED_CAMERA_INFORMATION
    + ED_PRINTER_RUNNING_STATUS
    + ED_PRINTER_BASIC_INFORMATION
    + ED_NOZZLE_INFORMATION
    + ED_PRINTER_CURRENT_JOB_INFORMATION
    + ED_STATISTICS
)


class Raise3DSensor(
    Raise3DCoordinatorEntity[Raise3DSensorEntityDescription], SensorEntity
):
    """Raise3D Sensor class."""


async_setup_entry = make_platform_async_setup_entry(
    ENTITY_DESCRIPTIONS, Raise3DSensor, _LOGGER
)
