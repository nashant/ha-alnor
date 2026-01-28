"""Mixin for shared humidity control logic."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Protocol

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HUMIDITY_COOLDOWN,
    CONF_HUMIDITY_HIGH_MODE,
    CONF_HUMIDITY_HYSTERESIS,
    CONF_HUMIDITY_LOW_MODE,
    CONF_HUMIDITY_SENSORS,
    CONF_HUMIDITY_TARGET,
    DEFAULT_HUMIDITY_COOLDOWN,
    DEFAULT_HUMIDITY_HIGH_MODE,
    DEFAULT_HUMIDITY_HYSTERESIS,
    DEFAULT_HUMIDITY_LOW_MODE,
)

_LOGGER = logging.getLogger(__name__)


class HumidityControlEntity(Protocol):
    """Protocol for entities that support humidity control."""

    hass: HomeAssistant
    device_id: str
    coordinator: Any  # AlnorDataUpdateCoordinator

    async def _set_ventilation_mode(self, mode: str) -> None:
        """Set ventilation mode - must be implemented by entity."""
        ...

    def _get_current_mode(self) -> str | None:
        """Get current ventilation mode - must be implemented by entity."""
        ...


class HumidityControlMixin:
    """Mixin providing shared humidity control functionality.

    Entities using this mixin must implement:
    - _set_ventilation_mode(mode: str) -> None
    - _get_current_mode() -> str | None
    - Provide: hass, device_id, coordinator attributes
    """

    def __init__(self) -> None:
        """Initialize humidity control state."""
        self._humidity_control_enabled = False
        self._last_mode_change: datetime | None = None

    def _get_current_humidity(self: HumidityControlEntity) -> int | None:
        """Get maximum humidity from all configured sensors.

        Returns:
            Maximum humidity value from all sensors, or None if unavailable
        """
        humidity_sensors_key = f"{CONF_HUMIDITY_SENSORS}_{self.device_id}"
        humidity_sensor_ids = self.coordinator.config_entry.options.get(humidity_sensors_key, [])

        if not humidity_sensor_ids:
            _LOGGER.debug("No humidity sensors configured for device %s", self.device_id)
            return None

        humidity_values = []
        for sensor_id in humidity_sensor_ids:
            sensor_state = self.hass.states.get(sensor_id)
            if sensor_state and sensor_state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                try:
                    humidity_values.append(int(float(sensor_state.state)))
                except (ValueError, TypeError):
                    _LOGGER.debug(
                        "Failed to parse humidity from sensor %s: %s",
                        sensor_id,
                        sensor_state.state,
                    )
                    continue

        result = max(humidity_values) if humidity_values else None
        _LOGGER.debug(
            "Current humidity for device %s: %s (from %d sensors)",
            self.device_id,
            result,
            len(humidity_values),
        )
        return result

    def _get_humidity_config(self: HumidityControlEntity) -> dict[str, Any]:
        """Get humidity control configuration for this device.

        Returns:
            Dict with keys: hysteresis, target, high_mode, low_mode, cooldown
        """
        options = self.coordinator.config_entry.options

        # Build config keys
        hysteresis_key = f"{CONF_HUMIDITY_HYSTERESIS}_{self.device_id}"
        target_key = f"{CONF_HUMIDITY_TARGET}_{self.device_id}"
        high_mode_key = f"{CONF_HUMIDITY_HIGH_MODE}_{self.device_id}"
        low_mode_key = f"{CONF_HUMIDITY_LOW_MODE}_{self.device_id}"
        cooldown_key = f"{CONF_HUMIDITY_COOLDOWN}_{self.device_id}"

        return {
            "hysteresis": options.get(hysteresis_key, DEFAULT_HUMIDITY_HYSTERESIS),
            "target": options.get(target_key),
            "high_mode": options.get(high_mode_key, DEFAULT_HUMIDITY_HIGH_MODE),
            "low_mode": options.get(low_mode_key, DEFAULT_HUMIDITY_LOW_MODE),
            "cooldown": options.get(cooldown_key, DEFAULT_HUMIDITY_COOLDOWN),
        }

    async def _check_humidity_control(self: HumidityControlEntity) -> None:
        """Check humidity and adjust mode if needed.

        Uses single hysteresis value:
        - If humidity > target + hysteresis: switch to high mode
        - If humidity < target - hysteresis: switch to low mode
        - Otherwise: stay in current mode (hysteresis band)
        """
        if not self._humidity_control_enabled:
            _LOGGER.debug("Humidity control disabled for device %s", self.device_id)
            return

        config = self._get_humidity_config()
        current = self._get_current_humidity()

        if current is None or config["target"] is None:
            _LOGGER.debug(
                "Humidity control check skipped for device %s - missing data",
                self.device_id,
            )
            return

        # Cooldown: prevent rapid mode switching
        if self._last_mode_change:
            elapsed = (dt_util.utcnow() - self._last_mode_change).total_seconds()
            if elapsed < config["cooldown"]:
                _LOGGER.debug(
                    "Humidity control cooldown active for device %s (%.0fs remaining)",
                    self.device_id,
                    config["cooldown"] - elapsed,
                )
                return

        # Calculate thresholds with capping to keep within valid range (1-99%)
        upper_threshold = min(config["target"] + config["hysteresis"], 99)
        lower_threshold = max(config["target"] - config["hysteresis"], 1)
        current_mode = self._get_current_mode()

        _LOGGER.debug(
            "Thresholds for device %s: lower=%d%%, upper=%d%% (target=%d%%, hysteresis=%d%%)",
            self.device_id,
            lower_threshold,
            upper_threshold,
            config["target"],
            config["hysteresis"],
        )

        # Switch to high mode if above upper threshold
        if current > upper_threshold and current_mode != config["high_mode"]:
            _LOGGER.info(
                "Humidity %.1f%% > %.1f%% for device %s, switching to %s",
                current,
                upper_threshold,
                self.device_id,
                config["high_mode"],
            )
            await self._set_ventilation_mode(config["high_mode"])
            self._last_mode_change = dt_util.utcnow()

        # Switch to low mode if below lower threshold
        elif current < lower_threshold and current_mode != config["low_mode"]:
            _LOGGER.info(
                "Humidity %.1f%% < %.1f%% for device %s, switching to %s",
                current,
                lower_threshold,
                self.device_id,
                config["low_mode"],
            )
            await self._set_ventilation_mode(config["low_mode"])
            self._last_mode_change = dt_util.utcnow()
        else:
            _LOGGER.debug(
                "No mode change needed for device %s: current=%.1f, thresholds=[%.1f, %.1f]",
                self.device_id,
                current,
                lower_threshold,
                upper_threshold,
            )

    def enable_humidity_control(self) -> None:
        """Enable automatic humidity control.

        This will cause the entity to automatically adjust ventilation modes
        based on humidity readings from configured sensors. The entity will
        check humidity levels during updates and after sensor changes.
        """
        self._humidity_control_enabled = True
        _LOGGER.info("Enabled humidity control for device %s", self.device_id)

    def disable_humidity_control(self) -> None:
        """Disable automatic humidity control.

        Stops the automatic adjustment of ventilation modes based on humidity.
        Manual control via mode selection will still work.
        """
        self._humidity_control_enabled = False
        _LOGGER.info("Disabled humidity control for device %s", self.device_id)

    def _build_hvac_state_attributes(self: HumidityControlEntity) -> dict[str, Any]:
        """Build common HVAC state attributes.

        Returns:
            Dictionary of state attributes for HVAC devices
        """
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
        }

        # Add connection mode
        connection_mode = self.coordinator.connection_modes.get(self.device_id)
        if connection_mode:
            attrs["connection_mode"] = connection_mode

        # Add preheater_available if exists
        if hasattr(state, "preheater_available"):
            attrs["preheater_available"] = state.preheater_available

        return attrs
