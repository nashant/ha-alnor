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

from .const import (
    CONF_LOCAL_IPS,
    CONF_SYNC_ZONES,
    DEFAULT_SYNC_ZONES,
    DOMAIN,
    MODBUS_PORT,
)

_LOGGER = logging.getLogger(__name__)


class AlnorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alnor."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()

            # Validate credentials
            try:
                api = AlnorCloudApi()
                await api.connect(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )

                # Create entry
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        CONF_SYNC_ZONES: user_input.get(CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES),
                    },
                )

            except CloudAuthenticationError:
                errors["base"] = "invalid_auth"
                _LOGGER.warning("Invalid authentication credentials")

            except Exception as err:
                errors["base"] = "cannot_connect"
                _LOGGER.exception("Unexpected exception during setup: %s", err)

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

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Check if user wants to configure local IPs
            if "configure_local" in user_input and user_input["configure_local"]:
                return await self.async_step_local_config()

            # Update options
            return self.async_create_entry(
                title="",
                data={
                    CONF_SYNC_ZONES: user_input.get(CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES),
                    CONF_LOCAL_IPS: self.config_entry.options.get(CONF_LOCAL_IPS, {}),
                },
            )

        # Get current options
        current_sync_zones = self.config_entry.options.get(CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SYNC_ZONES, default=current_sync_zones): bool,
                    vol.Optional("configure_local", default=False): bool,
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
                # Update options with new local IPs
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_SYNC_ZONES: self.config_entry.options.get(
                            CONF_SYNC_ZONES, DEFAULT_SYNC_ZONES
                        ),
                        CONF_LOCAL_IPS: local_ips,
                    },
                )

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

    def _format_device_info(self, devices: dict[str, Any]) -> str:
        """Format device information for display."""
        info_lines = []
        for device_id, device in devices.items():
            info_lines.append(f"• {device.name} (ID: {device_id})")
        return "\n".join(info_lines)
