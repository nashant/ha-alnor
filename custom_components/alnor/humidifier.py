"""Humidifier platform for Alnor integration."""

from __future__ import annotations

import logging
from datetime import datetime
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
    CONF_HUMIDITY_COOLDOWN,
    CONF_HUMIDITY_HIGH_MODE,
    CONF_HUMIDITY_HYSTERESIS,
    CONF_HUMIDITY_LOW_MODE,
    CONF_HUMIDITY_SENSORS,
    CONF_HUMIDITY_TARGET,
    DOMAIN,
)
from .coordinator import AlnorDataUpdateCoordinator
from .entity import AlnorEntity

_LOGGER = logging.getLogger(__name__)

# Cooldown period between automatic mode changes (seconds) - now configurable per device
# This constant is kept for backwards compatibility but defaults are in const.py
HUMIDITY_CONTROL_COOLDOWN = 60  # Default fallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alnor humidifier platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    _LOGGER.info("Setting up humidifier platform for Alnor")

    entities = []

    # Add humidifier entity only for Heat Recovery Units with humidity sensors configured
    for device_id, device in coordinator.devices.items():
        _LOGGER.info(
            "Checking device %s (type: %s) for humidifier setup",
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
                entities.append(AlnorHumidifier(coordinator, device_id))
                _LOGGER.info(
                    "Created humidifier entity for device %s",
                    device.name,
                )
            else:
                _LOGGER.info(
                    "Skipping humidifier entity for device %s - no humidity sensors configured",
                    device.name,
                )

    _LOGGER.info("Adding %d humidifier entities", len(entities))
    async_add_entities(entities)


class AlnorHumidifier(AlnorEntity, HumidifierEntity):
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
        self._attr_unique_id = f"{device_id}_humidifier"
        self._attr_name = None  # Use device name
        # Set suggested entity_id using device slug
        self._attr_suggested_object_id = f"alnor_{self._device_slug}"

        # Humidity control state
        self._last_mode_change: datetime | None = None
        self._humidity_control_enabled = False
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
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        humidity_sensor_ids = self.coordinator.config_entry.options.get(
            humidity_sensors_key, []
        )

        if not humidity_sensor_ids:
            _LOGGER.info("No humidity sensors configured for device %s", self.device_id)
            return None

        # Get humidity from all sensors and return the maximum
        humidity_values = []
        for sensor_id in humidity_sensor_ids:
            sensor_state = self.hass.states.get(sensor_id)
            if sensor_state and sensor_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                try:
                    value = int(float(sensor_state.state))
                    humidity_values.append(value)
                    _LOGGER.info(
                        "Sensor %s value: %d for device %s",
                        sensor_id,
                        value,
                        self.device_id,
                    )
                except (ValueError, TypeError) as err:
                    _LOGGER.info(
                        "Failed to parse humidity from sensor %s: %s (error: %s)",
                        sensor_id,
                        sensor_state.state,
                        err,
                    )
                    continue
            else:
                _LOGGER.info(
                    "Sensor %s unavailable or unknown for device %s (state: %s)",
                    sensor_id,
                    self.device_id,
                    sensor_state.state if sensor_state else "None",
                )

        result = max(humidity_values) if humidity_values else None
        _LOGGER.info(
            "Current humidity for device %s: %s (from %d sensors)",
            self.device_id,
            result,
            len(humidity_values),
        )
        return result

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            return {}

        attrs = {
            "indoor_temperature": state.indoor_temperature,
            "outdoor_temperature": state.outdoor_temperature,
            "supply_temperature": state.supply_temperature,
            "exhaust_temperature": state.exhaust_temperature,
            "preheater_demand": state.preheater_demand,
            "bypass_position": state.bypass_position,
            "exhaust_fan_speed": state.exhaust_fan_speed,
            "supply_fan_speed": state.supply_fan_speed,
            "filter_days_remaining": state.filter_days_remaining,
            "speed": state.speed,
        }

        # Add connection mode from parent class
        connection_mode = self.coordinator.connection_modes.get(self.device_id)
        if connection_mode:
            attrs["connection_mode"] = connection_mode

        # Add preheater_available if attribute exists
        if hasattr(state, "preheater_available"):
            attrs["preheater_available"] = state.preheater_available

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
        _LOGGER.info("async_set_mode called for device %s with mode: %s", self.device_id, mode)

        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device %s", self.device_id)
            return

        try:
            ventilation_mode = VentilationMode(mode)
            _LOGGER.info("Setting mode to %s for device %s", ventilation_mode, self.device_id)
            await controller.set_mode(ventilation_mode)
            _LOGGER.info("Mode set successfully for device %s", self.device_id)

            # Automatically adjust speed based on mode
            state = self.coordinator.data.get(self.device_id)
            if mode == VentilationMode.STANDBY.value:
                # Standby mode turns the system off
                if state and state.speed > 0:
                    _LOGGER.info("Setting speed to 0 for standby mode on device %s", self.device_id)
                    await controller.set_speed(0)
            else:
                # Non-standby modes turn the system on if it's off
                if state and state.speed == 0:
                    _LOGGER.info("Setting speed to 50 for non-standby mode on device %s", self.device_id)
                    await controller.set_speed(50)  # Turn on to medium speed

            _LOGGER.info("Requesting coordinator refresh for device %s", self.device_id)
            await self.coordinator.async_request_refresh()
            _LOGGER.info("Mode change completed successfully for device %s", self.device_id)
        except ValueError as err:
            _LOGGER.error("Invalid ventilation mode: %s (error: %s)", mode, err)
        except Exception as err:
            _LOGGER.error(
                "Failed to set mode for device %s: %s",
                self.device_id,
                err,
                exc_info=True,
            )

    async def _check_humidity_control(self) -> None:
        """Check humidity and adjust mode if needed.

        Uses single hysteresis value like binary_sensor:
        - If humidity > target + hysteresis: switch to high mode
        - If humidity < target - hysteresis: switch to low mode
        - Otherwise: stay in current mode (creates hysteresis band)
        """
        if not self._humidity_control_enabled:
            _LOGGER.info("Humidity control check skipped - not enabled for device %s", self.device_id)
            return

        options = self.coordinator.config_entry.options

        # Get per-device configuration
        hysteresis_key = f"{CONF_HUMIDITY_HYSTERESIS}_{self.device_id}"
        target_key = f"{CONF_HUMIDITY_TARGET}_{self.device_id}"
        high_mode_key = f"{CONF_HUMIDITY_HIGH_MODE}_{self.device_id}"
        low_mode_key = f"{CONF_HUMIDITY_LOW_MODE}_{self.device_id}"

        hysteresis = options.get(hysteresis_key, 5)
        target = options.get(target_key)
        high_mode = options.get(high_mode_key, "home_plus")
        low_mode = options.get(low_mode_key, "home")

        current = self.current_humidity

        _LOGGER.info(
            "Humidity control check for device %s: current=%s, target=%s, hysteresis=%s, high_mode=%s, low_mode=%s",
            self.device_id,
            current,
            target,
            hysteresis,
            high_mode,
            low_mode,
        )

        if current is None or target is None:
            _LOGGER.info(
                "Humidity control check skipped - missing data for device %s (current=%s, target=%s)",
                self.device_id,
                current,
                target,
            )
            return

        # Cooldown: prevent rapid mode switching
        if self._last_mode_change:
            cooldown_key = f"{CONF_HUMIDITY_COOLDOWN}_{self.device_id}"
            cooldown = options.get(cooldown_key, HUMIDITY_CONTROL_COOLDOWN)

            elapsed = (datetime.now() - self._last_mode_change).total_seconds()
            if elapsed < cooldown:
                _LOGGER.debug(
                    "Humidity control cooldown active for device %s (%.0fs remaining)",
                    self.device_id,
                    cooldown - elapsed,
                )
                return

        # Single hysteresis creates a band: target ± hysteresis
        upper_threshold = target + hysteresis
        lower_threshold = target - hysteresis

        current_mode = self.mode

        _LOGGER.info(
            "Humidity thresholds for device %s: lower=%.1f, upper=%.1f, current=%.1f, current_mode=%s",
            self.device_id,
            lower_threshold,
            upper_threshold,
            current,
            current_mode,
        )

        # Switch to high mode if above upper threshold
        if current > upper_threshold:
            if current_mode != high_mode:
                _LOGGER.info(
                    "Humidity %.1f%% > %.1f%% (target %d%% + %d%% hysteresis) for device %s, switching to %s",
                    current,
                    upper_threshold,
                    target,
                    hysteresis,
                    self.device_id,
                    high_mode,
                )
                await self.async_set_mode(high_mode)
                self._last_mode_change = datetime.now()
            else:
                _LOGGER.info(
                    "Humidity %.1f%% > %.1f%% but already in high mode %s for device %s",
                    current,
                    upper_threshold,
                    high_mode,
                    self.device_id,
                )

        # Switch to low mode if below lower threshold
        elif current < lower_threshold and current_mode != low_mode:
            _LOGGER.info(
                "Humidity %.1f%% < %.1f%% (target %d%% - %d%% hysteresis) for device %s, switching to %s",
                current,
                lower_threshold,
                target,
                hysteresis,
                self.device_id,
                low_mode,
            )
            await self.async_set_mode(low_mode)
            self._last_mode_change = datetime.now()
        else:
            _LOGGER.info(
                "No mode change needed for device %s: current=%.1f, lower=%.1f, upper=%.1f, mode=%s",
                self.device_id,
                current,
                lower_threshold,
                upper_threshold,
                current_mode,
            )

    def enable_humidity_control(self) -> None:
        """Enable automatic humidity control."""
        self._humidity_control_enabled = True
        self._subscribe_to_sensors()
        _LOGGER.info(
            "Enabled humidity control for device %s (control_enabled=%s)",
            self.device_id,
            self._humidity_control_enabled,
        )

        # Trigger immediate humidity check
        self.hass.async_create_task(self._check_humidity_control())

    def disable_humidity_control(self) -> None:
        """Disable automatic humidity control."""
        self._humidity_control_enabled = False
        self._unsubscribe_from_sensors()
        _LOGGER.info("Disabled humidity control for device %s", self.device_id)

    def _subscribe_to_sensors(self) -> None:
        """Subscribe to humidity sensor state changes."""
        if self._sensor_listener_unsub is not None:
            return  # Already subscribed

        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        sensor_ids = self.coordinator.config_entry.options.get(humidity_sensors_key, [])

        if not sensor_ids:
            return

        # Subscribe to state changes for all configured humidity sensors
        self._sensor_listener_unsub = async_track_state_change_event(
            self.hass,
            sensor_ids,
            self._humidity_sensor_changed,
        )
        _LOGGER.info(
            "Subscribed to humidity sensor changes for device %s: %s",
            self.device_id,
            sensor_ids,
        )

    def _unsubscribe_from_sensors(self) -> None:
        """Unsubscribe from humidity sensor state changes."""
        if self._sensor_listener_unsub is not None:
            self._sensor_listener_unsub()
            self._sensor_listener_unsub = None
            _LOGGER.info(
                "Unsubscribed from humidity sensor changes for device %s",
                self.device_id,
            )

    @callback
    def _humidity_sensor_changed(self, event: Event) -> None:
        """Handle humidity sensor state change.

        This is called immediately when any configured humidity sensor changes.
        """
        _LOGGER.info(
            "Humidity sensor callback triggered for device %s: entity=%s",
            self.device_id,
            event.data.get("entity_id"),
        )

        # Get the new state
        new_state = event.data.get("new_state")
        if not new_state or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.info(
                "Skipping humidity sensor change - state unavailable/unknown for device %s",
                self.device_id,
            )
            return

        _LOGGER.info(
            "Humidity sensor changed for device %s: %s = %s",
            self.device_id,
            event.data.get("entity_id"),
            new_state.state,
        )

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
