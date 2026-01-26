"""Test the Alnor integration init."""

from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.alnor import async_reload_entry, async_setup_entry, async_unload_entry
from custom_components.alnor.const import DOMAIN


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_api,
) -> None:
    """Test setting up the integration."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.alnor.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
    ):
        assert await async_setup_entry(hass, mock_config_entry)
        await hass.async_block_till_done()

    # Verify coordinator was created and stored
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]


async def test_setup_entry_api_failure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_api,
) -> None:
    """Test setup fails when API connection fails."""
    mock_config_entry.add_to_hass(hass)

    # Make API connection fail
    mock_api.connect.side_effect = Exception("Connection failed")

    with (
        patch(
            "custom_components.alnor.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
    ):
        with pytest.raises(Exception):
            await async_setup_entry(hass, mock_config_entry)


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_api,
) -> None:
    """Test unloading the integration."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.alnor.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
    ):
        assert await async_setup_entry(hass, mock_config_entry)
        await hass.async_block_till_done()

    # Now unload
    assert await async_unload_entry(hass, mock_config_entry)
    await hass.async_block_till_done()

    # Verify coordinator was removed
    assert mock_config_entry.entry_id not in hass.data[DOMAIN]


async def test_reload_entry(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test reloading the integration."""
    mock_config_entry.add_to_hass(hass)

    with patch("homeassistant.config_entries.ConfigEntries.async_reload") as mock_reload:
        await async_reload_entry(hass, mock_config_entry)
        mock_reload.assert_called_once_with(mock_config_entry.entry_id)
