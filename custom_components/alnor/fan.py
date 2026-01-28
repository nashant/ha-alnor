"""Fan platform for Alnor integration."""

from __future__ import annotations

import logging
from typing import Any

from alnor_sdk.models import ProductType, VentilationMode
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import DOMAIN
from .coordinator import AlnorDataUpdateCoordinator
from .entity import AlnorEntity

_LOGGER = logging.getLogger(__name__)

# Speed range for fan control (0-100%)
SPEED_RANGE = (1, 100)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alnor fan platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Add fan entity only for exhaust fans
    # HRUs use either humidifier (if humidity sensors configured) or select (if no sensors)
    for device_id, device in coordinator.devices.items():
        if device.product_type == ProductType.EXHAUST_FAN:
            # Always create fan for exhaust fans
            if device_id in coordinator.controllers:
                entities.append(AlnorFan(coordinator, device_id))
                _LOGGER.debug("Added fan entity for exhaust fan device %s", device.name)

    async_add_entities(entities)


class AlnorFan(AlnorEntity, FanEntity):
    """Representation of an Alnor fan."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    _attr_preset_modes = [
        VentilationMode.STANDBY.value,
        VentilationMode.AWAY.value,
        VentilationMode.HOME.value,
        VentilationMode.HOME_PLUS.value,
        VentilationMode.AUTO.value,
        VentilationMode.PARTY.value,
    ]

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"alnor_{device_id}_fan"
        self._attr_name = None  # Use device name

    @property
    def is_on(self) -> bool:
        """Return true if the fan is on."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            return False
        return state.speed > 0

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            return None

        # Convert speed (0-100) to percentage
        if state.speed == 0:
            return 0

        return ranged_value_to_percentage(SPEED_RANGE, state.speed)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        state = self.coordinator.data.get(self.device_id)
        if not state or not state.mode:
            return None
        return state.mode.value if hasattr(state.mode, "value") else state.mode

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
            return

        # Convert percentage to speed value (0-100)
        speed = int(percentage_to_ranged_value(SPEED_RANGE, percentage))

        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device %s", self.device_id)
            return

        try:
            await controller.set_speed(speed)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error(
                "Failed to set speed for device %s: %s",
                self.device_id,
                err,
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device %s", self.device_id)
            return

        try:
            mode = VentilationMode(preset_mode)
            await controller.set_mode(mode)
            await self.coordinator.async_request_refresh()
        except ValueError:
            _LOGGER.error("Invalid preset mode: %s", preset_mode)
        except Exception as err:
            _LOGGER.error(
                "Failed to set preset mode for device %s: %s",
                self.device_id,
                err,
            )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            # Default to 50% speed or last known speed
            state = self.coordinator.data.get(self.device_id)
            last_speed = state.speed if state and state.speed > 0 else 50
            await self.async_set_percentage(ranged_value_to_percentage(SPEED_RANGE, last_speed))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device %s", self.device_id)
            return

        try:
            await controller.set_speed(0)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error(
                "Failed to turn off device %s: %s",
                self.device_id,
                err,
            )
