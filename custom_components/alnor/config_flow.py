"""Config flow for Alnor integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from alnor_sdk.communication import AlnorCloudApi, ModbusClient
from alnor_sdk.exceptions import CloudAuthenticationError
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import (
    CONF_HUMIDITY_COOLDOWN,
    CONF_HUMIDITY_HIGH_MODE,
    CONF_HUMIDITY_HYSTERESIS,
    CONF_HUMIDITY_LOW_MODE,
    CONF_HUMIDITY_SENSORS,
    CONF_HUMIDITY_TARGET,
    CONF_LOCAL_IPS,
    CONF_SYNC_ZONES,
    DEFAULT_HUMIDITY_COOLDOWN,
    DEFAULT_HUMIDITY_HIGH_MODE,
    DEFAULT_HUMIDITY_HYSTERESIS,
    DEFAULT_HUMIDITY_LOW_MODE,
    DEFAULT_HUMIDITY_TARGET,
    DEFAULT_SYNC_ZONES,
    DOMAIN,
    MODBUS_PORT,
)

_LOGGER = logging.getLogger(__name__)


class AlnorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alnor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._username: str | None = None
        self._password: str | None = None
        self._sync_zones: bool = DEFAULT_SYNC_ZONES
        self._hru_devices: dict[str, Any] = {}
        self._hru_devices_list: list[tuple[str, Any]] = []  # List of (device_id, device) tuples
        self._current_device_index: int = 0
        self._humidity_config: dict[str, Any] = {}  # Store config as we go through devices

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()

            # Validate credentials
            api = None
            try:
                api = AlnorCloudApi(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
                await api.connect()

                # Store credentials and sync_zones for next step
                self._username = user_input[CONF_USERNAME]
                self._password = user_input[CONF_PASSWORD]
                self._sync_zones = user_input.get(CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES)

                # Fetch devices to see if we have any HRUs
                from alnor_sdk.models import ProductType

                # Get bridges first (SDK returns Bridge objects)
                bridges = await api.get_bridges()

                # Get all devices from all bridges (SDK returns Device objects)
                all_devices = []
                for bridge in bridges:
                    devices = await api.get_devices(bridge.bridge_id)
                    all_devices.extend(devices)

                # Filter for HRU devices
                self._hru_devices = {}
                for device in all_devices:
                    if device.product_type == ProductType.HEAT_RECOVERY_UNIT:
                        self._hru_devices[device.device_id] = device

                await api.disconnect()

                # If we have HRU devices, go to humidity config step
                if self._hru_devices:
                    return await self.async_step_humidity_setup()

                # No HRU devices, create entry directly
                return self.async_create_entry(
                    title=self._username,
                    data={
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                    },
                    options={
                        CONF_SYNC_ZONES: self._sync_zones,
                    },
                )

            except CloudAuthenticationError:
                errors["base"] = "invalid_auth"
                _LOGGER.warning("Invalid authentication credentials")

            except Exception as err:
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Unexpected exception during setup: %s", err)

            finally:
                # Always disconnect API to prevent unclosed session warnings
                if api:
                    try:
                        await api.disconnect()
                    except Exception:
                        pass  # Ignore errors during cleanup

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_SYNC_ZONES, default=DEFAULT_SYNC_ZONES): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_humidity_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure humidity sensors for HRU devices during initial setup.

        This presents one device at a time with clean field names.
        """
        # Initialize device list on first call
        if not self._hru_devices_list:
            self._hru_devices_list = list(self._hru_devices.items())
            self._current_device_index = 0

        if user_input is not None:
            # Store config for current device
            current_device_id, _current_device = self._hru_devices_list[self._current_device_index]

            # Store custom device name if provided
            device_name = user_input.get("device_name", "")
            if device_name and device_name.strip():
                self._humidity_config[f"device_name_{current_device_id}"] = device_name.strip()

            # Get the list of humidity sensors from user input (multi-select returns list)
            sensor_list = user_input.get(CONF_HUMIDITY_SENSORS, [])

            if sensor_list:
                # Store with device-specific keys
                self._humidity_config[f"{CONF_HUMIDITY_SENSORS}_{current_device_id}"] = sensor_list
                self._humidity_config[f"{CONF_HUMIDITY_HYSTERESIS}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_HYSTERESIS, DEFAULT_HUMIDITY_HYSTERESIS
                )
                self._humidity_config[f"{CONF_HUMIDITY_TARGET}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_TARGET, DEFAULT_HUMIDITY_TARGET
                )
                self._humidity_config[f"{CONF_HUMIDITY_HIGH_MODE}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_HIGH_MODE, DEFAULT_HUMIDITY_HIGH_MODE
                )
                self._humidity_config[f"{CONF_HUMIDITY_LOW_MODE}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_LOW_MODE, DEFAULT_HUMIDITY_LOW_MODE
                )
                self._humidity_config[f"{CONF_HUMIDITY_COOLDOWN}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_COOLDOWN, DEFAULT_HUMIDITY_COOLDOWN
                )

            # Move to next device
            self._current_device_index += 1

            # If more devices, show next device's config
            if self._current_device_index < len(self._hru_devices_list):
                return await self.async_step_humidity_setup()

            # All devices configured, create entry
            options = {
                CONF_SYNC_ZONES: self._sync_zones,
                **self._humidity_config,  # Add all device-specific humidity configs
            }

            return self.async_create_entry(
                title=self._username,
                data={
                    CONF_USERNAME: self._username,
                    CONF_PASSWORD: self._password,
                },
                options=options,
            )

        # Show form for current device with clean field names
        current_device_id, current_device = self._hru_devices_list[self._current_device_index]
        device_name = current_device.name if current_device.name else "Unknown Device"

        # Build schema with clean field names (no device_id suffix)
        schema_dict = {
            vol.Optional("device_name", default=device_name): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_HUMIDITY_SENSORS, default=[]): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="humidity",
                    multiple=True,
                )
            ),
            vol.Optional(CONF_HUMIDITY_TARGET, default=DEFAULT_HUMIDITY_TARGET): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=1, unit_of_measurement="%", mode="slider"
                )
            ),
            vol.Optional(CONF_HUMIDITY_HYSTERESIS, default=DEFAULT_HUMIDITY_HYSTERESIS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=20, step=1, unit_of_measurement="%", mode="slider"
                )
            ),
            vol.Optional(CONF_HUMIDITY_HIGH_MODE, default=DEFAULT_HUMIDITY_HIGH_MODE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["auto", "away", "home", "home_plus", "party"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="ventilation_mode",
                )
            ),
            vol.Optional(CONF_HUMIDITY_LOW_MODE, default=DEFAULT_HUMIDITY_LOW_MODE): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["auto", "away", "home", "home_plus", "standby"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="ventilation_mode",
                )
            ),
            vol.Optional(CONF_HUMIDITY_COOLDOWN, default=DEFAULT_HUMIDITY_COOLDOWN): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=300, step=10, unit_of_measurement="s", mode="slider"
                )
            ),
        }

        # Show progress
        progress_text = f"Device {self._current_device_index + 1} of {len(self._hru_devices_list)}"
        from homeassistant.util import slugify
        device_slug = slugify(device_name)

        return self.async_show_form(
            step_id="humidity_setup",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "device_name": device_name,
                "device_slug": device_slug,
                "progress": progress_text,
            },
        )

    def _format_hru_info(self, devices: dict[str, Any]) -> str:
        """Format HRU device information for display.

        Args:
            devices: Dict mapping device_id to Device object
        """
        info_lines = []
        for device_id, device in devices.items():
            name = device.name if device.name else "Unknown"
            # Show device name with slugified version to help match with entities
            from homeassistant.util import slugify
            device_slug = slugify(name)
            info_lines.append(f"• {name} → Entity IDs will use: alnor_{device_slug}")
        return "\n".join(info_lines)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauth when credentials are invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate new credentials
            api = None
            try:
                api = AlnorCloudApi(
                    username=self.context["entry_id"],
                    password=user_input[CONF_PASSWORD],
                )
                await api.connect()
                await api.disconnect()

                # Update the config entry with new password
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data={
                        CONF_USERNAME: self.context["entry_id"],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

            except CloudAuthenticationError:
                errors["base"] = "invalid_auth"
                _LOGGER.warning("Invalid authentication credentials during reauth")

            except Exception as err:
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Unexpected exception during reauth: %s", err)

            finally:
                # Always disconnect API to prevent unclosed session warnings
                if api:
                    try:
                        await api.disconnect()
                    except Exception:
                        pass  # Ignore errors during cleanup

        # Show reauth form
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"username": self.context.get("entry_id", "")},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AlnorOptionsFlow:
        """Get the options flow for this handler."""
        return AlnorOptionsFlow(config_entry)


class AlnorOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Alnor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._devices: list[dict[str, Any]] = []
        self._hru_devices_list: list[tuple[str, Any]] = []
        self._current_device_index: int = 0
        self._humidity_config: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Check if user wants to configure local IPs
            if "configure_local" in user_input and user_input["configure_local"]:
                return await self.async_step_local_config()

            # Check if user wants to configure humidity
            if "configure_humidity" in user_input and user_input["configure_humidity"]:
                return await self.async_step_humidity_config()

            # Update options (preserve existing humidity settings)
            new_options = {
                CONF_SYNC_ZONES: user_input.get(CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES),
                CONF_LOCAL_IPS: self.config_entry.options.get(CONF_LOCAL_IPS, {}),
            }

            # Preserve all humidity settings
            for key in self.config_entry.options:
                if key.startswith(CONF_HUMIDITY_SENSORS) or key.startswith("humidity_"):
                    new_options[key] = self.config_entry.options[key]

            return self.async_create_entry(title="", data=new_options)

        # Get current options
        current_sync_zones = self.config_entry.options.get(CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SYNC_ZONES, default=current_sync_zones): bool,
                    vol.Optional("configure_local", default=False): bool,
                    vol.Optional("configure_humidity", default=False): bool,
                }
            ),
        )

    async def async_step_local_config(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Configure local IP addresses for devices."""
        errors: dict[str, str] = {}

        # Get coordinator to access devices
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]

        if user_input is not None:
            # Extract local IPs from user input
            local_ips: dict[str, str] = {}

            for device_id in coordinator.devices:
                ip_key = f"local_ip_{device_id}"
                if ip_key in user_input and user_input[ip_key]:
                    ip_address = user_input[ip_key].strip()

                    if ip_address:
                        # Validate IP by trying to connect
                        try:
                            modbus_client = ModbusClient(ip_address, MODBUS_PORT)
                            await asyncio.wait_for(
                                modbus_client.connect(),
                                timeout=5.0,
                            )
                            await modbus_client.disconnect()

                            local_ips[device_id] = ip_address
                            _LOGGER.info(
                                "Validated local IP %s for device %s",
                                ip_address,
                                device_id,
                            )

                        except TimeoutError:
                            errors[ip_key] = "timeout"
                            _LOGGER.warning(
                                "Timeout connecting to %s for device %s",
                                ip_address,
                                device_id,
                            )

                        except Exception as err:
                            errors[ip_key] = "cannot_connect"
                            _LOGGER.warning(
                                "Failed to connect to %s for device %s: %s",
                                ip_address,
                                device_id,
                                err,
                            )

            if not errors:
                # Update options with new local IPs (preserve humidity settings)
                new_options = {
                    CONF_SYNC_ZONES: self.config_entry.options.get(
                        CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES
                    ),
                    CONF_LOCAL_IPS: local_ips,
                }

                # Preserve all humidity settings
                for key in self.config_entry.options:
                    if key.startswith(CONF_HUMIDITY_SENSORS) or key.startswith("humidity_"):
                        new_options[key] = self.config_entry.options[key]

                return self.async_create_entry(title="", data=new_options)

        # Build schema with device names
        current_local_ips = self.config_entry.options.get(CONF_LOCAL_IPS, {})
        schema_dict = {}

        for device_id, _device in coordinator.devices.items():
            ip_key = f"local_ip_{device_id}"
            current_ip = current_local_ips.get(device_id, "")

            schema_dict[vol.Optional(ip_key, default=current_ip)] = str

        return self.async_show_form(
            step_id="local_config",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"device_info": self._format_device_info(coordinator.devices)},
        )

    async def async_step_humidity_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure humidity control for Heat Recovery Units.

        This presents one device at a time with clean field names.
        """
        from alnor_sdk.models import ProductType

        # Get coordinator to access devices
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]

        # Get only HRU devices
        hru_devices = {
            device_id: device
            for device_id, device in coordinator.devices.items()
            if device.product_type == ProductType.HEAT_RECOVERY_UNIT
        }

        if not hru_devices:
            # No HRU devices, skip this step
            return await self.async_step_init()

        # Initialize device list on first call
        if not self._hru_devices_list:
            self._hru_devices_list = list(hru_devices.items())
            self._current_device_index = 0

        if user_input is not None:
            # Store config for current device
            current_device_id, _current_device = self._hru_devices_list[self._current_device_index]

            # Store custom device name if provided
            device_name = user_input.get("device_name", "")
            if device_name and device_name.strip():
                self._humidity_config[f"device_name_{current_device_id}"] = device_name.strip()

            # Get the list of humidity sensors from user input (multi-select returns list)
            sensor_list = user_input.get(CONF_HUMIDITY_SENSORS, [])

            if sensor_list:
                # Store with device-specific keys
                self._humidity_config[f"{CONF_HUMIDITY_SENSORS}_{current_device_id}"] = sensor_list
                self._humidity_config[f"{CONF_HUMIDITY_HYSTERESIS}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_HYSTERESIS, DEFAULT_HUMIDITY_HYSTERESIS
                )
                self._humidity_config[f"{CONF_HUMIDITY_TARGET}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_TARGET, DEFAULT_HUMIDITY_TARGET
                )
                self._humidity_config[f"{CONF_HUMIDITY_HIGH_MODE}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_HIGH_MODE, DEFAULT_HUMIDITY_HIGH_MODE
                )
                self._humidity_config[f"{CONF_HUMIDITY_LOW_MODE}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_LOW_MODE, DEFAULT_HUMIDITY_LOW_MODE
                )
                self._humidity_config[f"{CONF_HUMIDITY_COOLDOWN}_{current_device_id}"] = user_input.get(
                    CONF_HUMIDITY_COOLDOWN, DEFAULT_HUMIDITY_COOLDOWN
                )
            else:
                # User left sensors empty - clear any existing config for this device
                for key in list(self.config_entry.options.keys()):
                    if key.endswith(f"_{current_device_id}"):
                        # Don't copy old config to new options
                        pass

            # Move to next device
            self._current_device_index += 1

            # If more devices, show next device's config
            if self._current_device_index < len(self._hru_devices_list):
                return await self.async_step_humidity_config()

            # All devices configured, create entry
            new_options = {
                CONF_SYNC_ZONES: self.config_entry.options.get(CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES),
                CONF_LOCAL_IPS: self.config_entry.options.get(CONF_LOCAL_IPS, {}),
                **self._humidity_config,  # Add all device-specific humidity configs
            }

            return self.async_create_entry(title="", data=new_options)

        # Show form for current device with clean field names
        current_device_id, current_device = self._hru_devices_list[self._current_device_index]
        device_name = current_device.name if current_device.name else "Unknown Device"

        # Get current values for this device
        current_device_name = self.config_entry.options.get(f"device_name_{current_device_id}", device_name)
        sensors_key = f"{CONF_HUMIDITY_SENSORS}_{current_device_id}"
        current_sensors = self.config_entry.options.get(sensors_key, [])
        current_hysteresis = self.config_entry.options.get(
            f"{CONF_HUMIDITY_HYSTERESIS}_{current_device_id}", DEFAULT_HUMIDITY_HYSTERESIS
        )
        current_target = self.config_entry.options.get(
            f"{CONF_HUMIDITY_TARGET}_{current_device_id}", DEFAULT_HUMIDITY_TARGET
        )
        current_high_mode = self.config_entry.options.get(
            f"{CONF_HUMIDITY_HIGH_MODE}_{current_device_id}", DEFAULT_HUMIDITY_HIGH_MODE
        )
        current_low_mode = self.config_entry.options.get(
            f"{CONF_HUMIDITY_LOW_MODE}_{current_device_id}", DEFAULT_HUMIDITY_LOW_MODE
        )
        current_cooldown = self.config_entry.options.get(
            f"{CONF_HUMIDITY_COOLDOWN}_{current_device_id}", DEFAULT_HUMIDITY_COOLDOWN
        )

        # Build schema with clean field names (no device_id suffix)
        schema_dict = {
            vol.Optional("device_name", default=current_device_name): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_HUMIDITY_SENSORS, default=current_sensors): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    device_class="humidity",
                    multiple=True,
                )
            ),
            vol.Optional(CONF_HUMIDITY_TARGET, default=current_target): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=100, step=1, unit_of_measurement="%", mode="slider"
                )
            ),
            vol.Optional(CONF_HUMIDITY_HYSTERESIS, default=current_hysteresis): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1, max=20, step=1, unit_of_measurement="%", mode="slider"
                )
            ),
            vol.Optional(CONF_HUMIDITY_HIGH_MODE, default=current_high_mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["auto", "away", "home", "home_plus", "party"],
                    translation_key="ventilation_mode",
                )
            ),
            vol.Optional(CONF_HUMIDITY_LOW_MODE, default=current_low_mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["auto", "away", "home", "home_plus", "standby"],
                    translation_key="ventilation_mode",
                )
            ),
            vol.Optional(CONF_HUMIDITY_COOLDOWN, default=current_cooldown): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0, max=300, step=10, unit_of_measurement="s", mode="slider"
                )
            ),
        }

        # Show progress
        progress_text = f"Device {self._current_device_index + 1} of {len(self._hru_devices_list)}"
        from homeassistant.util import slugify
        device_slug = slugify(device_name)

        return self.async_show_form(
            step_id="humidity_config",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "device_name": device_name,
                "device_slug": device_slug,
                "progress": progress_text,
            },
        )

    def _format_device_info(self, devices: dict[str, Any]) -> str:
        """Format device information for display."""
        info_lines = []
        for device_id, device in devices.items():
            info_lines.append(f"• {device.name} (ID: {device_id})")
        return "\n".join(info_lines)

    def _format_hru_info(self, devices: dict[str, Any]) -> str:
        """Format HRU device information for display.

        Args:
            devices: Dict mapping device_id to Device object
        """
        info_lines = []
        for device_id, device in devices.items():
            name = device.name if device.name else "Unknown"
            # Show device name with slugified version to help match with entities
            from homeassistant.util import slugify
            device_slug = slugify(name)
            info_lines.append(f"• {name} → Entity IDs will use: alnor_{device_slug}")
        return "\n".join(info_lines)
