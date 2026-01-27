"""Switch platform for Alnor integration."""

from __future__ import annotations

import logging
from typing import Any

from alnor_sdk.models import ProductType
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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

    _LOGGER.info("Setting up switch platform for Alnor")

    entities = []

    # Add humidity control switch for HRUs with configured humidity sensors
    for device_id, device in coordinator.devices.items():
        _LOGGER.info(
            "Checking device %s (type: %s) for switch setup",
            device.name,
            device.product_type,
        )
        if device.product_type == ProductType.HEAT_RECOVERY_UNIT:
            humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{device_id}"
            humidity_sensors = entry.options.get(humidity_sensors_key)
            _LOGGER.info(
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
                _LOGGER.info(
                    "Skipping humidity control switch for device %s - no humidity sensors configured",
                    device.name,
                )

    _LOGGER.info("Adding %d switch entities", len(entities))
    async_add_entities(entities)


class AlnorHumidityControlSwitch(AlnorEntity, SwitchEntity):
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
        self._attr_unique_id = f"{device_id}_humidity_control"
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

        # If switch defaults to ON, enable humidity control on the humidifier entity
        if self._is_on:
            await self._update_climate_entity(True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on humidity control."""
        self._is_on = True
        self.async_write_ha_state()

        # Enable humidity control on climate entity
        await self._update_climate_entity(True)

        _LOGGER.info("Enabled humidity control for device %s", self.device_id)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off humidity control."""
        self._is_on = False
        self.async_write_ha_state()

        # Disable humidity control on climate entity
        await self._update_climate_entity(False)

        _LOGGER.info("Disabled humidity control for device %s", self.device_id)

    async def _update_climate_entity(self, enable: bool) -> None:
        """Update the humidity control entity state."""
        from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
        from homeassistant.components.humidifier import DOMAIN as HUMIDIFIER_DOMAIN

        # Try humidifier first (new approach)
        humidifier_component = self._hass.data.get(HUMIDIFIER_DOMAIN)
        if humidifier_component:
            _LOGGER.info(
                "Found humidifier component with %d entities",
                len(humidifier_component.entities) if hasattr(humidifier_component, "entities") else 0,
            )
            for entity in humidifier_component.entities:
                if hasattr(entity, "device_id") and entity.device_id == self.device_id:
                    _LOGGER.info(
                        "Found humidifier entity for device %s, setting humidity control to %s",
                        self.device_id,
                        enable,
                    )
                    if enable:
                        entity.enable_humidity_control()
                    else:
                        entity.disable_humidity_control()
                    return
            _LOGGER.info("No matching humidifier entity found for device %s", self.device_id)
        else:
            _LOGGER.info("No humidifier component found in hass.data")

        # Fall back to climate entity (old approach)
        climate_component = self._hass.data.get(CLIMATE_DOMAIN)
        if not climate_component:
            _LOGGER.info("No climate component found in hass.data")
            return

        _LOGGER.info(
            "Found climate component with %d entities",
            len(climate_component.entities) if hasattr(climate_component, "entities") else 0,
        )
        # Find our climate entity by device_id
        for entity in climate_component.entities:
            if hasattr(entity, "device_id") and entity.device_id == self.device_id:
                _LOGGER.info(
                    "Found climate entity for device %s, setting humidity control to %s",
                    self.device_id,
                    enable,
                )
                if enable:
                    entity.enable_humidity_control()
                else:
                    entity.disable_humidity_control()
                return

        _LOGGER.warning(
            "Could not find humidifier or climate entity for device %s to %s humidity control",
            self.device_id,
            "enable" if enable else "disable",
        )
