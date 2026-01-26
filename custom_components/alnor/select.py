"""Select platform for Alnor integration."""
from __future__ import annotations

import logging

from alnor_sdk.models import DeviceMode, ProductType

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AlnorDataUpdateCoordinator
from .entity import AlnorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alnor select platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Add mode select for HRU and exhaust fan devices
    for device_id, device in coordinator.devices.items():
        if device.product_type in [
            ProductType.HRU_PREMAIR_450,
            ProductType.HRU_PREMAIR_500,
            ProductType.VMC_02VJ04,
            ProductType.VMC_EXHAUST_FAN,
        ]:
            if device_id in coordinator.controllers:
                entities.append(AlnorModeSelect(coordinator, device_id))
                _LOGGER.debug("Added mode select for device %s", device.name)

    async_add_entities(entities)


class AlnorModeSelect(AlnorEntity, SelectEntity):
    """Representation of an Alnor mode select."""

    _attr_options = [
        DeviceMode.STANDBY.value,
        DeviceMode.AWAY.value,
        DeviceMode.HOME.value,
        DeviceMode.HOME_PLUS.value,
        DeviceMode.AUTO.value,
        DeviceMode.PARTY.value,
    ]

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the mode select."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_mode"
        self._attr_name = "Mode"

    @property
    def current_option(self) -> str | None:
        """Return the current selected mode."""
        state = self.coordinator.data.get(self.device_id)
        if not state or not state.mode:
            return None
        return state.mode.value

    async def async_select_option(self, option: str) -> None:
        """Change the selected mode."""
        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device %s", self.device_id)
            return

        try:
            mode = DeviceMode(option)
            await controller.set_mode(mode)
            await self.coordinator.async_request_refresh()
        except ValueError:
            _LOGGER.error("Invalid mode: %s", option)
        except Exception as err:
            _LOGGER.error(
                "Failed to set mode for device %s: %s",
                self.device_id,
                err,
            )
