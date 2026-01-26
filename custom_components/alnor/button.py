"""Button platform for Alnor integration."""

from __future__ import annotations

import logging

from alnor_sdk.models import ProductType
from homeassistant.components.button import ButtonEntity
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
    """Set up Alnor button platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Add filter reset button for HRU devices only
    for device_id, device in coordinator.devices.items():
        if device.product_type == ProductType.HEAT_RECOVERY_UNIT:
            if device_id in coordinator.controllers:
                entities.append(AlnorFilterResetButton(coordinator, device_id))
                _LOGGER.debug("Added filter reset button for device %s", device.name)

    async_add_entities(entities)


class AlnorFilterResetButton(AlnorEntity, ButtonEntity):
    """Representation of an Alnor filter reset button."""

    _attr_icon = "mdi:air-filter"

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the filter reset button."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_filter_reset"
        self._attr_name = "Reset filter timer"

    async def async_press(self) -> None:
        """Handle the button press - reset filter timer."""
        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device %s", self.device_id)
            return

        try:
            # Check if controller has reset_filter_timer method
            if hasattr(controller, "reset_filter_timer"):
                await controller.reset_filter_timer()
                await self.coordinator.async_request_refresh()
                _LOGGER.info("Filter timer reset for device %s", self.device_id)
            else:
                _LOGGER.warning(
                    "Controller for device %s does not support filter reset",
                    self.device_id,
                )

        except Exception as err:
            _LOGGER.error(
                "Failed to reset filter timer for device %s: %s",
                self.device_id,
                err,
            )
