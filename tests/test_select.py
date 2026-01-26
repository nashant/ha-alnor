"""Test the Alnor select platform."""
from unittest.mock import patch

from alnor_sdk.models import DeviceMode
import pytest

from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from custom_components.alnor.const import DOMAIN


async def test_select_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
) -> None:
    """Test select platform setup."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
        patch(
            "custom_components.alnor.coordinator.HeatRecoveryUnitController",
            return_value=mock_hru_controller,
        ),
        patch(
            "custom_components.alnor.coordinator.ExhaustFanController",
            return_value=mock_exhaust_controller,
        ),
        patch(
            "custom_components.alnor.coordinator.SensorController",
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Verify mode select entities were created
    state = hass.states.get("select.living_room_hru_mode")
    assert state is not None
    assert state.state == "home"

    state = hass.states.get("select.bathroom_fan_mode")
    assert state is not None


async def test_select_option(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test selecting an option."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
        patch(
            "custom_components.alnor.coordinator.HeatRecoveryUnitController",
            return_value=mock_hru_controller,
        ),
        patch(
            "custom_components.alnor.coordinator.ExhaustFanController",
        ),
        patch(
            "custom_components.alnor.coordinator.SensorController",
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {
                ATTR_ENTITY_ID: "select.living_room_hru_mode",
                ATTR_OPTION: "party",
            },
            blocking=True,
        )

        mock_hru_controller.set_mode.assert_called_with(DeviceMode.PARTY)


async def test_select_available_options(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test available options."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
        patch(
            "custom_components.alnor.coordinator.HeatRecoveryUnitController",
            return_value=mock_hru_controller,
        ),
        patch(
            "custom_components.alnor.coordinator.ExhaustFanController",
        ),
        patch(
            "custom_components.alnor.coordinator.SensorController",
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("select.living_room_hru_mode")
        assert state is not None

        options = state.attributes["options"]
        assert "standby" in options
        assert "away" in options
        assert "home" in options
        assert "home_plus" in options
        assert "auto" in options
        assert "party" in options
