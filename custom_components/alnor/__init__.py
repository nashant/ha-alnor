"""The Alnor Ventilation integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import AlnorDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alnor from a config entry."""
    _LOGGER.info("Setting up Alnor integration (entry_id=%s)", entry.entry_id)

    # Create coordinator
    coordinator = AlnorDataUpdateCoordinator(hass, entry)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Note: We don't register an update listener because most option changes
    # (like target humidity) don't require a full reload. Entities read options
    # dynamically. Only structural changes (like adding humidity sensors) require
    # manual reconfiguration via the UI.

    _LOGGER.info("Alnor integration setup complete")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Alnor integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up coordinator and API connection
    if unload_ok:
        coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN].pop(entry.entry_id)

        # Close all Modbus TCP client connections
        for device_id, modbus_client in coordinator.modbus_clients.items():
            try:
                await modbus_client.disconnect()
                _LOGGER.info("Closed Modbus connection for device %s", device_id)
            except Exception as err:
                _LOGGER.warning("Error disconnecting Modbus client for device %s: %s", device_id, err)

        # Close API session to prevent unclosed client warnings
        if coordinator.api:
            try:
                await coordinator.api.disconnect()
                _LOGGER.info("Closed Alnor Cloud API connection")
            except Exception as err:
                _LOGGER.warning("Error disconnecting from Alnor API: %s", err)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    _LOGGER.debug("Reloading Alnor integration")
    await hass.config_entries.async_reload(entry.entry_id)
