"""Climate platform for Alnor integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from alnor_sdk.models import ProductType, VentilationMode
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
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

# Cooldown period between automatic mode changes (seconds)
HUMIDITY_CONTROL_COOLDOWN = 120


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alnor climate platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Add climate entity only for Heat Recovery Units
    for device_id, device in coordinator.devices.items():
        if device.product_type == ProductType.HEAT_RECOVERY_UNIT:
            entities.append(AlnorClimate(coordinator, device_id))
            _LOGGER.debug(
                "Added climate entity for device %s",
                device.name,
            )

    async_add_entities(entities)


class AlnorClimate(AlnorEntity, ClimateEntity):
    """Climate entity for Alnor Heat Recovery Units."""

    _attr_fan_modes = [
        VentilationMode.STANDBY.value,
        VentilationMode.AWAY.value,
        VentilationMode.HOME.value,
        VentilationMode.HOME_PLUS.value,
        VentilationMode.AUTO.value,
        VentilationMode.PARTY.value,
    ]
    _attr_translation_key = "alnor_climate"
    _attr_min_humidity = 0
    _attr_max_humidity = 100

    @property
    def temperature_unit(self) -> str:
        """Return temperature unit.

        Only return temperature unit when humidity control is not configured.
        """
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        has_humidity_control = bool(self.coordinator.config_entry.options.get(humidity_sensors_key))

        if has_humidity_control:
            # Don't report temperature unit to avoid temperature-focused UI
            return UnitOfTemperature.CELSIUS  # Still need to return something for compatibility
        return UnitOfTemperature.CELSIUS

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return available HVAC modes.

        When humidity control is configured, return empty list to hide HVAC mode control.
        Device is controlled via fan modes for humidity management.
        """
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        if self.coordinator.config_entry.options.get(humidity_sensors_key):
            # Humidity control mode: no HVAC mode selector (always running)
            # Return empty list to hide the HVAC mode control entirely
            return []
        else:
            # Manual mode: can turn on/off
            return [HVACMode.OFF, HVACMode.FAN_ONLY]

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_climate"
        self._attr_name = None  # Use device name
        # Set suggested entity_id using device slug
        self._attr_suggested_object_id = f"alnor_{self._device_slug}"

        # Humidity control state
        self._last_mode_change: datetime | None = None
        self._humidity_control_enabled = False

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return supported features.

        Order matters: TARGET_HUMIDITY first to make it the default display.
        """
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        has_humidity_control = bool(self.coordinator.config_entry.options.get(humidity_sensors_key))

        if has_humidity_control:
            # With humidity control: humidity target FIRST, then fan mode
            # No TURN_ON/TURN_OFF to force card to focus on humidity
            features = ClimateEntityFeature.TARGET_HUMIDITY | ClimateEntityFeature.FAN_MODE
        else:
            # Without humidity control: fan mode and on/off
            features = (
                ClimateEntityFeature.FAN_MODE
                | ClimateEntityFeature.TURN_ON
                | ClimateEntityFeature.TURN_OFF
            )

        return features

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Return current HVAC mode.

        Returns None when humidity control is configured to force card to show humidity.
        """
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        has_humidity_control = bool(self.coordinator.config_entry.options.get(humidity_sensors_key))

        # With humidity control, return None to hide HVAC mode from UI
        # This should force the climate card to show humidity as primary control
        if has_humidity_control:
            return None

        # Without humidity control, can be OFF or FAN_ONLY
        state = self.coordinator.data.get(self.device_id)
        if not state or state.speed == 0:
            return HVACMode.OFF
        return HVACMode.FAN_ONLY

    @property
    def hvac_action(self) -> str | None:
        """Return current HVAC action.

        When humidity sensors are configured, indicate we're in fan/humidity mode.
        This helps the UI prioritize humidity display.
        """
        from homeassistant.components.climate import HVACAction

        state = self.coordinator.data.get(self.device_id)
        if not state:
            return None

        if state.speed == 0:
            return HVACAction.IDLE

        # If humidity sensors configured, indicate we're in fan mode (for humidity control)
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        if self.coordinator.config_entry.options.get(humidity_sensors_key):
            return HVACAction.FAN

        return HVACAction.FAN

    @property
    def current_temperature(self) -> float | None:
        """Return supply air temperature.

        Return None when humidity sensors are configured to make humidity the primary display.
        """
        # If humidity sensors are configured, don't show temperature as primary
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        if self.coordinator.config_entry.options.get(humidity_sensors_key):
            return None

        state = self.coordinator.data.get(self.device_id)
        return state.supply_temperature if state else None

    @property
    def target_humidity(self) -> int | None:
        """Return target humidity percentage from configuration."""
        target_key = f"{CONF_HUMIDITY_TARGET}_{self.device_id}"
        return self.coordinator.config_entry.options.get(target_key)

    @property
    def current_humidity(self) -> int | None:
        """Return maximum humidity from all linked sensors."""
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        humidity_sensor_ids = self.coordinator.config_entry.options.get(humidity_sensors_key, [])

        if not humidity_sensor_ids:
            return None

        # Get humidity from all sensors and return the maximum
        humidity_values = []
        for sensor_id in humidity_sensor_ids:
            sensor_state = self.hass.states.get(sensor_id)
            if sensor_state and sensor_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                try:
                    humidity_values.append(int(float(sensor_state.state)))
                except (ValueError, TypeError):
                    continue

        return max(humidity_values) if humidity_values else None

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode (ventilation mode)."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            return None
        return state.mode.value if hasattr(state.mode, "value") else state.mode

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            return {}

        attrs = {
            "indoor_temperature": state.indoor_temperature,
            "outdoor_temperature": state.outdoor_temperature,
            "exhaust_temperature": state.exhaust_temperature,
            "preheater_demand": state.preheater_demand,
            "bypass_position": state.bypass_position,
            "exhaust_fan_speed": state.exhaust_fan_speed,
            "supply_fan_speed": state.supply_fan_speed,
            "filter_days_remaining": state.filter_days_remaining,
        }

        # Add connection mode from parent class
        connection_mode = self.coordinator.connection_modes.get(self.device_id)
        if connection_mode:
            attrs["connection_mode"] = connection_mode

        # Add preheater_available if attribute exists
        if hasattr(state, "preheater_available"):
            attrs["preheater_available"] = state.preheater_available

        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode.

        With humidity control, only FAN_ONLY is available. Use fan modes to control.
        """
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        has_humidity_control = bool(self.coordinator.config_entry.options.get(humidity_sensors_key))

        if has_humidity_control:
            # In humidity control mode, ignore OFF commands
            # User should use fan mode "standby" instead
            _LOGGER.debug(
                "Ignoring HVAC mode change in humidity control mode for device %s",
                self.device_id,
            )
            return

        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device %s", self.device_id)
            return

        try:
            if hvac_mode == HVACMode.OFF:
                await controller.set_speed(0)
            elif hvac_mode == HVACMode.FAN_ONLY:
                # Turn on to medium speed if currently off
                await controller.set_speed(50)
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error(
                "Failed to set HVAC mode for device %s: %s",
                self.device_id,
                err,
            )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode (ventilation mode).

        Setting a fan mode automatically turns on the system (except standby).
        """
        controller = self.coordinator.controllers.get(self.device_id)
        if not controller:
            _LOGGER.error("No controller found for device %s", self.device_id)
            return

        try:
            mode = VentilationMode(fan_mode)
            await controller.set_mode(mode)

            # Automatically turn on the system when setting a non-standby mode
            # Standby mode turns the system off
            state = self.coordinator.data.get(self.device_id)
            if fan_mode == "standby":
                # Standby mode turns the system off
                if state and state.speed > 0:
                    await controller.set_speed(0)
            else:
                # Non-standby modes turn the system on if it's off
                if state and state.speed == 0:
                    await controller.set_speed(50)  # Turn on to medium speed

            await self.coordinator.async_request_refresh()
        except ValueError:
            _LOGGER.error("Invalid fan mode: %s", fan_mode)
        except Exception as err:
            _LOGGER.error(
                "Failed to set fan mode for device %s: %s",
                self.device_id,
                err,
            )

    async def async_set_humidity(self, humidity: int) -> None:
        """Set target humidity percentage.

        Stores the new target humidity in config options.
        """
        if not 0 <= humidity <= 100:
            _LOGGER.error("Invalid humidity value: %s (must be 0-100)", humidity)
            return

        target_key = f"{CONF_HUMIDITY_TARGET}_{self.device_id}"

        # Update the config entry options with new target humidity
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

        # Trigger immediate humidity check if control is enabled
        if self._humidity_control_enabled:
            await self._check_humidity_control()

    async def _check_humidity_control(self) -> None:
        """Check humidity and adjust mode if needed.

        Uses single hysteresis value like binary_sensor:
        - If humidity > target + hysteresis: switch to high mode
        - If humidity < target - hysteresis: switch to low mode
        - Otherwise: stay in current mode (creates hysteresis band)
        """
        if not self._humidity_control_enabled:
            return

        options = self.coordinator.config_entry.options

        # Get per-device configuration
        hysteresis_key = f"{CONF_HUMIDITY_HYSTERESIS}_{self.device_id}"
        target_key = f"{CONF_HUMIDITY_TARGET}_{self.device_id}"
        high_mode_key = f"{CONF_HUMIDITY_HIGH_MODE}_{self.device_id}"
        low_mode_key = f"{CONF_HUMIDITY_LOW_MODE}_{self.device_id}"

        hysteresis = options.get(hysteresis_key, 5)
        target = options.get(target_key)
        high_mode = options.get(high_mode_key, "party")
        low_mode = options.get(low_mode_key, "home")

        current = self.current_humidity

        if current is None or target is None:
            return

        # Cooldown: prevent rapid mode switching
        if self._last_mode_change:
            elapsed = (datetime.now() - self._last_mode_change).total_seconds()
            if elapsed < HUMIDITY_CONTROL_COOLDOWN:
                _LOGGER.debug(
                    "Humidity control cooldown active for device %s (%.0fs remaining)",
                    self.device_id,
                    HUMIDITY_CONTROL_COOLDOWN - elapsed,
                )
                return

        # Single hysteresis creates a band: target ± hysteresis
        upper_threshold = target + hysteresis
        lower_threshold = target - hysteresis

        current_mode = self.fan_mode

        # Switch to high mode if above upper threshold
        if current > upper_threshold and current_mode != high_mode:
            _LOGGER.info(
                "Humidity %.1f%% > %.1f%% (target %d%% + %d%% hysteresis) for device %s, switching to %s",
                current,
                upper_threshold,
                target,
                hysteresis,
                self.device_id,
                high_mode,
            )
            await self.async_set_fan_mode(high_mode)
            self._last_mode_change = datetime.now()

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
            await self.async_set_fan_mode(low_mode)
            self._last_mode_change = datetime.now()

    def enable_humidity_control(self) -> None:
        """Enable automatic humidity control."""
        self._humidity_control_enabled = True
        _LOGGER.info("Enabled humidity control for device %s", self.device_id)

    def disable_humidity_control(self) -> None:
        """Disable automatic humidity control."""
        self._humidity_control_enabled = False
        _LOGGER.info("Disabled humidity control for device %s", self.device_id)

    async def async_update(self) -> None:
        """Update entity state and check humidity control."""
        await super().async_update()

        # Check humidity control on each update if enabled
        if self._humidity_control_enabled:
            await self._check_humidity_control()
