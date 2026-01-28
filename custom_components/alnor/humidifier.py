"""Humidifier platform for Alnor integration."""

from __future__ import annotations

import logging
from typing import Any

from alnor_sdk.models import ProductType, VentilationMode
from homeassistant.components.humidifier import (
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_HUMIDITY_SENSORS,
    CONF_HUMIDITY_TARGET,
    DEFAULT_STARTUP_SPEED,
    DOMAIN,
)
from .coordinator import AlnorDataUpdateCoordinator
from .entity import AlnorEntity
from .humidity_control_mixin import HumidityControlMixin

_LOGGER = logging.getLogger(__name__)

# Humidity control cooldown is now configurable per device via options
# Default value is defined in const.py as DEFAULT_HUMIDITY_COOLDOWN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alnor humidifier platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    _LOGGER.debug("Setting up humidifier platform for Alnor")

    entities = []

    # Add humidifier entity only for Heat Recovery Units with humidity sensors configured
    for device_id, device in coordinator.devices.items():
        if device.product_type == ProductType.HEAT_RECOVERY_UNIT:
            humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{device_id}"
            humidity_sensors = entry.options.get(humidity_sensors_key)
            if humidity_sensors:
                entities.append(AlnorHumidifier(coordinator, device_id))
                _LOGGER.info(
                    "Created humidifier entity for device %s with %d sensor(s)",
                    device.name,
                    len(humidity_sensors),
                )
    async_add_entities(entities)


class AlnorHumidifier(AlnorEntity, HumidifierEntity, HumidityControlMixin):
    """Humidifier entity for Alnor Heat Recovery Units with humidity control."""

    _attr_available_modes = [
        VentilationMode.STANDBY.value,
        VentilationMode.AWAY.value,
        VentilationMode.HOME.value,
        VentilationMode.HOME_PLUS.value,
        VentilationMode.AUTO.value,
        VentilationMode.PARTY.value,
    ]
    _attr_min_humidity = 0
    _attr_max_humidity = 100
    _attr_translation_key = "alnor_humidifier"

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the humidifier entity."""
        super().__init__(coordinator, device_id)
        HumidityControlMixin.__init__(self)
        self._attr_unique_id = f"alnor_{device_id}_humidifier"
        self._attr_name = None  # Use device name
        # Set suggested entity_id using device slug
        self._attr_suggested_object_id = f"alnor_{self._device_slug}"

        # Sensor subscription state
        self._sensor_listener_unsub = None

        # Cache target humidity to avoid reloading integration on every change
        target_key = f"{CONF_HUMIDITY_TARGET}_{self.device_id}"
        self._target_humidity = coordinator.config_entry.options.get(target_key)

    @property
    def supported_features(self) -> HumidifierEntityFeature:
        """Return supported features."""
        return HumidifierEntityFeature.MODES

    @property
    def is_on(self) -> bool:
        """Return true if humidifier is on (not in standby)."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            return False

        # Device is "on" if not in standby mode
        current_mode = state.mode.value if hasattr(state.mode, "value") else state.mode
        return current_mode != VentilationMode.STANDBY.value

    @property
    def mode(self) -> str | None:
        """Return current ventilation mode."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            _LOGGER.warning("No coordinator data for device %s", self.device_id)
            return None

        mode = state.mode.value if hasattr(state.mode, "value") else state.mode
        _LOGGER.debug("Device %s mode: %s", self.device_id, mode)
        return mode

    @property
    def target_humidity(self) -> int | None:
        """Return target humidity percentage from cached value."""
        return self._target_humidity

    @property
    def current_humidity(self) -> int | None:
        """Return maximum humidity from all linked sensors."""
        return self._get_current_humidity()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = self._build_hvac_state_attributes()

        # Add humidifier-specific attributes
        state = self.coordinator.data.get(self.device_id)
        if state:
            attrs["speed"] = state.speed

        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the humidifier (switch from standby to home mode)."""
        await self.async_set_mode(VentilationMode.HOME.value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the humidifier (switch to standby mode)."""
        await self.async_set_mode(VentilationMode.STANDBY.value)

    async def async_set_humidity(self, humidity: int) -> None:
        """Set target humidity percentage."""
        if not 0 <= humidity <= 100:
            _LOGGER.error("Invalid humidity value: %s (must be 0-100)", humidity)
            return

        # Update cached target humidity (avoids integration reload)
        self._target_humidity = humidity

        # Persist to config entry options in background
        # Note: This will eventually trigger a reload via the update listener,
        # but the entity will remain functional until then
        target_key = f"{CONF_HUMIDITY_TARGET}_{self.device_id}"
        new_options = dict(self.coordinator.config_entry.options)
        new_options[target_key] = humidity

        self.hass.config_entries.async_update_entry(
            self.coordinator.config_entry,
            options=new_options,
        )

        _LOGGER.info(
            "Updated target humidity to %d%% for device %s",
            humidity,
            self.device_id,
        )

        # Update the entity state to reflect new target
        self.async_write_ha_state()

        # Trigger immediate humidity check if control is enabled
        if self._humidity_control_enabled:
            await self._check_humidity_control()

    async def async_set_mode(self, mode: str) -> None:
        """Set ventilation mode."""
        _LOGGER.debug("Setting mode to '%s' for device: %s", mode, self.device_id)

        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device: %s", self.device_id)
            return

        try:
            ventilation_mode = VentilationMode(mode)
            await controller.set_mode(ventilation_mode)

            # Automatically adjust speed based on mode
            state = self.coordinator.data.get(self.device_id)
            if mode == VentilationMode.STANDBY.value:
                # Standby mode turns the system off
                if state and state.speed > 0:
                    await controller.set_speed(0)
            else:
                # Non-standby modes turn the system on if it's off
                if state and state.speed == 0:
                    await controller.set_speed(DEFAULT_STARTUP_SPEED)  # Turn on to medium speed

            await self.coordinator.async_request_refresh()
            _LOGGER.debug("Mode change completed for device: %s", self.device_id)
        except ValueError as err:
            _LOGGER.error(
                "Invalid ventilation mode '%s' for device %s: %s", mode, self.device_id, err
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to set mode for device %s: %s",
                self.device_id,
                err,
                exc_info=True,
            )

    async def _set_ventilation_mode(self, mode: str) -> None:
        """Set ventilation mode for protocol."""
        await self.async_set_mode(mode)

    def _get_current_mode(self) -> str | None:
        """Get current mode for protocol."""
        return self.mode

    def enable_humidity_control(self) -> None:
        """Enable automatic humidity control."""
        HumidityControlMixin.enable_humidity_control(self)
        self._subscribe_to_sensors()
        self.hass.async_create_task(self._check_humidity_control())

    def disable_humidity_control(self) -> None:
        """Disable automatic humidity control."""
        HumidityControlMixin.disable_humidity_control(self)
        self._unsubscribe_from_sensors()

    def _subscribe_to_sensors(self) -> None:
        """Subscribe to humidity sensor state changes.

        This enables event-driven updates rather than polling, ensuring
        immediate response to humidity changes.
        """
        if self._sensor_listener_unsub is not None:
            return  # Already subscribed

        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        sensor_ids = self.coordinator.config_entry.options.get(humidity_sensors_key, [])

        if not sensor_ids:
            return

        # Subscribe to state changes for all configured humidity sensors
        # This provides immediate, event-driven updates
        self._sensor_listener_unsub = async_track_state_change_event(
            self.hass,
            sensor_ids,
            self._humidity_sensor_changed,
        )
        _LOGGER.debug(
            "Subscribed to humidity sensor changes for device %s: %s",
            self.device_id,
            sensor_ids,
        )

    def _unsubscribe_from_sensors(self) -> None:
        """Unsubscribe from humidity sensor state changes."""
        if self._sensor_listener_unsub is not None:
            self._sensor_listener_unsub()
            self._sensor_listener_unsub = None

    @callback
    def _humidity_sensor_changed(self, event: Event) -> None:
        """Handle humidity sensor state change.

        This is called immediately when any configured humidity sensor changes,
        ensuring updates are event-driven rather than polling-based.
        """
        # Get the new state
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        # Always update the humidifier entity state immediately to reflect new humidity
        self.async_write_ha_state()

        # Trigger immediate humidity check only if control is enabled
        if self._humidity_control_enabled:
            self.hass.async_create_task(self._check_humidity_control())

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Always subscribe to sensor changes to keep humidity display updated
        self._subscribe_to_sensors()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()

        # Unsubscribe from sensor changes
        self._unsubscribe_from_sensors()

    async def async_update(self) -> None:
        """Update entity state and check humidity control."""
        await super().async_update()

        # Check humidity control on each update if enabled
        if self._humidity_control_enabled:
            await self._check_humidity_control()
