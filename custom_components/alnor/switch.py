"""Switch platform for Alnor integration."""

from __future__ import annotations

import logging
from typing import Any

from alnor_sdk.models import ProductType
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_HUMIDITY_SENSORS, DOMAIN
from .coordinator import AlnorDataUpdateCoordinator
from .entity import AlnorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alnor switch platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    _LOGGER.debug("Setting up switch platform for Alnor")

    entities = []

    # Add humidity control switch for HRUs with configured humidity sensors
    for device_id, device in coordinator.devices.items():
        _LOGGER.debug(
            "Checking device %s (type: %s) for switch setup",
            device.name,
            device.product_type,
        )
        if device.product_type == ProductType.HEAT_RECOVERY_UNIT:
            humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{device_id}"
            humidity_sensors = entry.options.get(humidity_sensors_key)
            _LOGGER.debug(
                "HRU device %s: humidity_sensors_key=%s, configured_sensors=%s",
                device.name,
                humidity_sensors_key,
                humidity_sensors,
            )
            if humidity_sensors:
                entities.append(AlnorHumidityControlSwitch(coordinator, device_id, hass))
                _LOGGER.info(
                    "Created humidity control switch for device %s",
                    device.name,
                )
            else:
                _LOGGER.debug(
                    "Skipping humidity control switch for device %s - no humidity sensors configured",
                    device.name,
                )

    _LOGGER.debug("Adding %d switch entities", len(entities))
    async_add_entities(entities)


class AlnorHumidityControlSwitch(AlnorEntity, SwitchEntity, RestoreEntity):
    """Switch to enable/disable automatic humidity control."""

    _attr_icon = "mdi:water-percent"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"alnor_{device_id}_humidity_control"
        self._attr_name = "Humidity Control"
        # Set suggested entity_id using device slug
        self._attr_suggested_object_id = f"alnor_{self._device_slug}_humidity_control"
        self._is_on = True  # Default to ON
        self._hass = hass

    @property
    def is_on(self) -> bool:
        """Return true if humidity control is enabled."""
        return self._is_on

    @property
    def available(self) -> bool:
        """Only available if humidity sensors configured."""
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        sensor_ids = self.coordinator.config_entry.options.get(humidity_sensors_key)
        return super().available and sensor_ids is not None and len(sensor_ids) > 0

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Restore previous state if available
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == STATE_ON

        # Enable humidity control if switch is on
        if self._is_on:
            await self._update_humidity_entity(True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on humidity control."""
        self._is_on = True
        self.async_write_ha_state()

        # Enable humidity control on climate entity
        await self._update_humidity_entity(True)

        _LOGGER.info("Enabled humidity control for device %s", self.device_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off humidity control."""
        self._is_on = False
        self.async_write_ha_state()

        # Disable humidity control on climate entity
        await self._update_humidity_entity(False)

        _LOGGER.info("Disabled humidity control for device %s", self.device_id)

    async def _update_humidity_entity(self, enable: bool) -> None:
        """Update the humidity control entity state.

        Attempts to find and control the associated humidifier entity
        by searching for entities with matching device_id.
        """
        from homeassistant.components.humidifier import DOMAIN as HUMIDIFIER_DOMAIN

        action = "enable" if enable else "disable"

        # Try humidifier first (preferred approach)
        humidifier_component = self._hass.data.get(HUMIDIFIER_DOMAIN)
        if humidifier_component and hasattr(humidifier_component, "entities"):
            _LOGGER.debug(
                "Searching %d humidifier entities for device: %s",
                len(humidifier_component.entities),
                self.device_id,
            )
            for entity in humidifier_component.entities:
                if hasattr(entity, "device_id") and entity.device_id == self.device_id:
                    _LOGGER.debug(
                        "Found humidifier entity for device %s, attempting to %s humidity control",
                        self.device_id,
                        action,
                    )
                    try:
                        if enable:
                            if hasattr(entity, "enable_humidity_control"):
                                entity.enable_humidity_control()
                                _LOGGER.info("Enabled humidity control for device: %s", self.device_id)
                                return
                            else:
                                _LOGGER.warning(
                                    "Humidifier entity for device %s missing enable_humidity_control method",
                                    self.device_id,
                                )
                        else:
                            if hasattr(entity, "disable_humidity_control"):
                                entity.disable_humidity_control()
                                _LOGGER.info("Disabled humidity control for device: %s", self.device_id)
                                return
                            else:
                                _LOGGER.warning(
                                    "Humidifier entity for device %s missing disable_humidity_control method",
                                    self.device_id,
                                )
                    except Exception as err:
                        _LOGGER.error(
                            "Error updating humidity control for device %s: %s",
                            self.device_id,
                            err,
                            exc_info=True,
                        )
                        return
            _LOGGER.debug("No matching humidifier entity found for device: %s", self.device_id)
        else:
            _LOGGER.debug("No humidifier component or entities available")

        # If we didn't find a humidifier entity, log a warning
        _LOGGER.warning(
            "Could not find humidifier entity for device %s to %s humidity control",
            self.device_id,
            action,
        )
