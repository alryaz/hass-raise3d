"""Custom integration for Raise3D printers with Home Assistant."""

from __future__ import annotations

__all__ = (
    # Home Assistant requirements
    "async_setup_entry",
    "async_setup",
    "async_unload_entry",
    "async_migrate_entry",
    # Component methods
    "async_initialize_api_from_configuration",
    "async_fetch_device_info",
    "make_platform_async_setup_entry",
    "convert_unempty",
    "wrap_convert_unempty",
    # Component classes
    "Raise3DEntity",
    "Raise3DCoordinatorEntity",
    "Raise3DUpdateCoordinator",
    "Raise3DEntityDescription",
    "Raise3DCoordinatorEntityDescription",
    # Submodules
    "camera",
    "sensor",
    "const",
    "config_flow",
    "api",
    "binary_sensor",
    "number",
    "button",
)

import asyncio
import logging
from abc import abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, final, Any, Mapping, Iterable, Awaitable, Generic

import aiohttp
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription, Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import (
    async_migrate_entries,
    RegistryEntry,
    RegistryEntryDisabler,
    RegistryEntryHider,
)
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from typing_extensions import TypeVar

from custom_components.raise3d.api import (
    Raise3DHostBasedStatefulAPI,
    Raise3DAPIBase,
    APIDataResponse,
    Raise3DPrinterAPI,
    Raise3DStatefulAPI,
)
from custom_components.raise3d.const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_PORT,
    CONF_PASSWORD,
    DEFAULT_MANUFACTURER,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

RAISE3D_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: RAISE3D_SCHEMA})}, extra=vol.ALLOW_EXTRA
)


def convert_unempty(value: Any):
    if isinstance(value, str) and not value.strip():
        return None
    return value


def wrap_convert_unempty(converter):
    def _wrapper(value: Any):
        value = convert_unempty(value)
        return None if value is None else converter(value)

    return _wrapper


async def _async_call_api_method(
    __method: Callable[[Raise3DAPIBase], ...],
    __logger: logging.Logger | logging.LoggerAdapter = _LOGGER,
    *args,
    **kwargs,
):
    method_name = __method.__name__
    try:
        return await __method(*args, **kwargs)
    except aiohttp.ServerDisconnectedError:
        __logger.warning("Connection aborted while updating '%s'", method_name)
    except aiohttp.ClientOSError as exc:
        if exc.errno != 104:
            raise
        __logger.warning("Connection error while updating '%s'", method_name)
    except aiohttp.ClientResponseError as exc:
        if exc.status != 429:
            raise
        __logger.warning("Too many requests while updating '%s'", method_name)

    await asyncio.sleep(1.5)
    return await __method(*args, **kwargs)


@dataclass(frozen=True, kw_only=True)
class Raise3DEntityDescription(EntityDescription):
    """Describes Raise3D entity."""

    def __post_init__(self):
        if self.translation_key is None:
            object.__setattr__(self, "translation_key", self.key)


@dataclass(frozen=True, kw_only=True)
class Raise3DCoordinatorEntityDescription(Raise3DEntityDescription):
    """Describes Raise3D entity."""

    update_method_name: str
    """Method to request data."""

    attribute: str = None
    """Attribute to extract from the data."""

    converter: Callable[[Any], Any] | None = convert_unempty
    """Function to convert the extracted attribute."""

    additional_attributes: dict[str, str] | None = None
    """Additional attributes (parsed from method dict return)."""

    def __post_init__(self):
        super().__post_init__()
        if self.attribute is None:
            object.__setattr__(self, "attribute", self.key)
        if isinstance(self.update_method_name, Callable):
            object.__setattr__(
                self, "update_method_name", self.update_method_name.__name__
            )


class Raise3DUpdateCoordinator(DataUpdateCoordinator[APIDataResponse | None]):
    """Raise3D Update Coordinator class."""

    __slots__ = ("__update_method_name",)

    def __init__(self, *args, update_method_name: str, **kwargs) -> None:
        self.__update_method_name = update_method_name
        super().__init__(*args, **kwargs)

    @property
    def raise3d_api(self) -> Raise3DHostBasedStatefulAPI:
        return self.hass.data[DOMAIN][self.config_entry.entry_id][0]

    @final
    @property
    def update_method_name(self) -> str:
        return self.__update_method_name

    @final
    async def _async_update_data(self) -> APIDataResponse | None:
        """Fetch the latest data from the source."""
        try:
            return await _async_call_api_method(
                getattr(self.raise3d_api, self.update_method_name), self.logger
            )
        except aiohttp.ClientResponseError as exc:
            if exc.status == 404:
                self.logger.warning(
                    f"API does not support '{self.update_method_name}', stopping updater"
                )
                await self.async_shutdown()
                return None
            raise


_TRaise3DEntityDescription = TypeVar(
    "_TRaise3DEntityDescription", bound=Raise3DEntityDescription
)


class BaseRaise3DEntity(Entity, Generic[_TRaise3DEntityDescription]):
    entity_description: _TRaise3DEntityDescription

    _attr_has_entity_name = True

    def __init__(
        self,
        entity_description: _TRaise3DEntityDescription,
        logger: logging.Logger | logging.LoggerAdapter = _LOGGER,
    ) -> None:
        self.entity_description = entity_description
        self.logger = logger
        self._attr_unique_id = (
            f"{self.config_entry.unique_id}__{entity_description.key}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        return self.hass.data[DOMAIN][self.config_entry.entry_id][2]

    @property
    def raise3d_api(self) -> Raise3DHostBasedStatefulAPI:
        return self.hass.data[DOMAIN][self.config_entry.entry_id][0]

    @property
    @abstractmethod
    def config_entry(self) -> ConfigEntry:
        raise NotImplementedError

    async def async_call_method_by_name(self, method_name: str, *args, **kwargs):
        return await _async_call_api_method(
            getattr(self.raise3d_api, method_name), self.logger, *args, **kwargs
        )


class Raise3DEntity(
    BaseRaise3DEntity[_TRaise3DEntityDescription], Generic[_TRaise3DEntityDescription]
):
    def __init__(
        self, config_entry: ConfigEntry, entity_description: _TRaise3DEntityDescription
    ) -> None:
        self._config_entry = config_entry
        super().__init__(entity_description)

    @property
    def config_entry(self) -> ConfigEntry:
        return self._config_entry


_TRaise3DCoordinatorEntityDescription = TypeVar(
    "_TRaise3DCoordinatorEntityDescription", bound=Raise3DCoordinatorEntityDescription
)


class Raise3DCoordinatorEntity(
    BaseRaise3DEntity[_TRaise3DCoordinatorEntityDescription],
    CoordinatorEntity[Raise3DUpdateCoordinator],
    Generic[_TRaise3DCoordinatorEntityDescription],
):
    """Raise3D Coordinator Entity class."""

    def __init__(self, coordinator: Raise3DUpdateCoordinator, *args, **kwargs) -> None:
        """Initialize the sensor."""
        self._attr_native_value = None
        self._attr_available = False
        CoordinatorEntity.__init__(self, coordinator)
        super().__init__(*args, **kwargs)

    @property
    def config_entry(self) -> ConfigEntry:
        return self.coordinator.config_entry

    @callback
    def _process_coordinator_data(self, data: APIDataResponse) -> None:
        _LOGGER.debug("Updating %s with data: %s", self.entity_description.key, data)

        if self.entity_description.attribute in data:
            value = data[self.entity_description.attribute]
            if self.entity_description.converter:
                value = self.entity_description.converter(value)
            self._attr_native_value = value
        else:
            self._attr_available = False
            self._attr_native_value = None

    @final
    @callback
    def _handle_coordinator_update(self, write: bool = True) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        self._attr_device_info = self.hass.data[DOMAIN][
            self.coordinator.config_entry.entry_id
        ][2]
        self._attr_available = data is not None

        if self._attr_available:
            self._process_coordinator_data(data)

        super()._handle_coordinator_update()


# noinspection PyUnusedLocal
async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Raise3D component."""
    hass.data[DOMAIN] = {}
    return True


@callback
def async_get_coordinator(
    hass: HomeAssistant, entry: ConfigEntry, update_method_name: str
) -> Raise3DUpdateCoordinator:
    # Iterate over the collected update_method_names
    coordinators = hass.data[DOMAIN][entry.entry_id][1]
    if update_method_name not in coordinators:
        coordinator = Raise3DUpdateCoordinator(
            hass,
            _LOGGER,
            config_entry=entry,
            name="Raise3D Updater for '{}' method".format(update_method_name),
            update_interval=timedelta(seconds=entry.data[CONF_SCAN_INTERVAL]),
            update_method_name=update_method_name,
        )
        coordinators[update_method_name] = coordinator
    return coordinators[update_method_name]


async def async_fetch_device_info(raise3d_api: Raise3DPrinterAPI):
    # We assume most of this info doesn't change across usage.
    # Otherwise, a configuration reload fixes everything.
    system_info = await raise3d_api.get_system_info()
    device_info_data = DeviceInfo(
        manufacturer=DEFAULT_MANUFACTURER,
        serial_number=system_info["Serial_number"],
        sw_version=f"{system_info['version']} / {system_info['api_version']}",
        hw_version=system_info["firmware_version"],
        identifiers={(DOMAIN, system_info["machine_id"])},
    )
    info_value: str | None
    if info_value := system_info.get("model"):
        device_info_data["model"] = info_value
    if info_value := system_info.get("machine_name"):
        device_info_data["name"] = info_value

    return device_info_data


async def async_initialize_api_from_configuration(
    hass: HomeAssistant,
    data: Mapping[str, Any],
    options: Mapping[str, Any] | None = None,
) -> Raise3DHostBasedStatefulAPI:
    raise3d_api = Raise3DHostBasedStatefulAPI(
        host=data[CONF_HOST],
        printer_port=data[CONF_PORT],
        printer_password=data[CONF_PASSWORD],
        session=async_get_clientsession(hass, verify_ssl=True),
    )
    await raise3d_api.login()
    return raise3d_api


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    from custom_components.raise3d.config_flow import Raise3DFlowHandler

    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )
    data = {**config_entry.data}

    if config_entry.version > Raise3DFlowHandler.VERSION or (
        config_entry.version == Raise3DFlowHandler.VERSION
        and config_entry.minor_version > Raise3DFlowHandler.MINOR_VERSION
    ):
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:

        # Update unique ID of the configuration entry
        raise3d_api = await async_initialize_api_from_configuration(
            hass, data, config_entry.options
        )
        system_info = await raise3d_api.get_system_info()
        new_unique_id = system_info["machine_id"]

        _LOGGER.debug(
            "Entry unique_id on entry unique ID upgrade: {} -> {}".format(
                config_entry.unique_id, new_unique_id
            )
        )

        hass.config_entries.async_update_entry(
            config_entry, version=2, minor_version=1, unique_id=new_unique_id
        )

    if config_entry.version == 2:

        if config_entry.minor_version == 1:
            # Rename unique IDs to avoid CONF_NAME changing stuff.
            from homeassistant.const import CONF_NAME

            _LOGGER.debug(
                "Entry unique_id on entity unique IDs upgrade: {}".format(
                    config_entry.unique_id
                )
            )

            def _collect_entity_keys():
                from importlib import import_module

                renamed_unique_ids_ = {}
                for entity_platform in PLATFORMS:
                    module = import_module(
                        f"custom_components.raise3d.{entity_platform}"
                    )
                    # Collect update_method_names if ENTITY_DESCRIPTIONS is present
                    for entity_description in getattr(
                        module, "ENTITY_DESCRIPTIONS", ()
                    ):
                        old_unique_id = (
                            f"{data[CONF_NAME]}_data_{entity_description.key}"
                        )
                        new_unique_id_ = (
                            f"{config_entry.unique_id}__{entity_description.key}"
                        )
                        renamed_unique_ids_[old_unique_id] = (
                            entity_platform,
                            new_unique_id_,
                        )
                return renamed_unique_ids_

            # noinspection PyTypeChecker
            renamed_unique_ids = await hass.async_add_executor_job(_collect_entity_keys)

            def _refactor_unique_ids(data: RegistryEntry) -> dict[str, Any] | None:
                try:
                    entity_platform, new_unique_id = renamed_unique_ids[data.unique_id]
                except KeyError:
                    return None
                else:
                    # For entities whose platforms sustained, update unique id.
                    if entity_platform == data.platform:
                        return {"new_unique_id": new_unique_id}

                    # For entities whose platforms migrated, disable and hide.
                    return {
                        "new_unique_id": new_unique_id + "__obsolete",
                        "disabled_by": RegistryEntryDisabler.INTEGRATION,
                        "hidden_by": RegistryEntryHider.INTEGRATION,
                    }

            await async_migrate_entries(
                hass, config_entry.entry_id, _refactor_unique_ids
            )

            # Remove redundant CONF_NAME from data
            data.pop(CONF_NAME, None)

            hass.config_entries.async_update_entry(
                config_entry, version=2, minor_version=2, data=data
            )

        if config_entries.minor_version == 2:
            # Lowercase all unique IDs
            def _lowercase_unique_ids(data: RegistryEntry) -> dict[str, Any]:
                return {
                    "new_unique_id": data.unique_id.lower(),
                }

            await async_migrate_entries(
                hass, config_entry.entry_id, _lowercase_unique_ids
            )

            hass.config_entries.async_update_entry(
                config_entry, version=2, minor_version=3, data=data
            )

    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""

    # Initialize and connect API
    raise3d_api = await async_initialize_api_from_configuration(
        hass, entry.data, entry.options
    )
    device_info_data = await async_fetch_device_info(raise3d_api)
    coordinators: dict[str, Raise3DUpdateCoordinator] = {}

    # Store data for future use
    hass.data[DOMAIN][entry.entry_id] = (raise3d_api, coordinators, device_info_data)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Perform first config entry refresh
    coordinator_refresh_tasks = {
        coordinator: hass.async_create_task(
            coordinator.async_config_entry_first_refresh()
        )
        for coordinator in coordinators.values()
    }
    if coordinator_refresh_tasks:
        await asyncio.wait(
            coordinator_refresh_tasks.values(), return_when=asyncio.ALL_COMPLETED
        )
        for coordinator, task in coordinator_refresh_tasks.items():
            if task.exception():
                _LOGGER.error(
                    "Error during first refresh via '%s': %s",
                    coordinator.update_method_name,
                    task.exception(),
                )

    return True


async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload Raise3D entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if not unload_ok:
        return False

    hass.data[DOMAIN].pop(entry.entry_id)
    return True


def make_platform_async_setup_entry(
    entity_descriptions: Iterable[Raise3DEntityDescription],
    platform_class: type[BaseRaise3DEntity],
    logger: logging.Logger | logging.LoggerAdapter = _LOGGER,
) -> Callable[[HomeAssistant, ConfigEntry, AddEntitiesCallback], Awaitable[bool]]:
    async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> bool:
        """Do the setup entry."""
        entities = []

        for entity_description in entity_descriptions:
            if issubclass(platform_class, Raise3DCoordinatorEntity):
                # noinspection PyArgumentList,PyUnresolvedReferences
                sensor = platform_class(
                    coordinator=async_get_coordinator(
                        hass, entry, entity_description.update_method_name
                    ),
                    entity_description=entity_description,
                )
            elif issubclass(platform_class, Raise3DEntity):
                # noinspection PyArgumentList
                sensor = platform_class(
                    config_entry=entry, entity_description=entity_description
                )
            else:
                raise ValueError("invalid platform_class: {}".format(platform_class))
            entities.append(sensor)

        logger.debug("Entities added : %i", len(entities))

        async_add_entities(entities)

        return True

    return async_setup_entry
