"""Binary sensor platform for Alnor integration."""

from __future__ import annotations

import logging

from alnor_sdk.models import ProductType
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_FAULT_CODE, DOMAIN
from .coordinator import AlnorDataUpdateCoordinator
from .entity import AlnorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alnor binary sensor platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Add fault sensor for HRU and exhaust fan devices
    for device_id, device in coordinator.devices.items():
        if device.product_type in [
            ProductType.HEAT_RECOVERY_UNIT,
            ProductType.EXHAUST_FAN,
        ]:
            entities.append(AlnorFaultSensor(coordinator, device_id))
            _LOGGER.debug("Added fault sensor for device %s", device.name)

    async_add_entities(entities)


class AlnorFaultSensor(AlnorEntity, BinarySensorEntity):
    """Representation of an Alnor fault sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the fault sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_fault"
        self._attr_name = "Fault"

    @property
    def is_on(self) -> bool:
        """Return true if fault is detected."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            return False

        # Check if device has fault status
        if hasattr(state, "fault_status"):
            return state.fault_status != 0

        return False

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        """Return additional state attributes."""
        # Get base attributes (includes connection mode)
        attributes = super().extra_state_attributes or {}

        # Add fault code if there's a fault
        if self.is_on:
            state = self.coordinator.data.get(self.device_id)
            if state and hasattr(state, "fault_code"):
                attributes[ATTR_FAULT_CODE] = state.fault_code

        return attributes if attributes else None
