"""Test the Alnor fan platform."""

from unittest.mock import patch

from alnor_sdk.models import VentilationMode

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PRESET_MODE,
    DOMAIN as FAN_DOMAIN,
    SERVICE_SET_PERCENTAGE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant


async def test_fan_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
) -> None:
    """Test fan platform setup."""
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

    # Verify fan entity was created for exhaust fan only (HRU uses climate entity)
    state = hass.states.get("fan.alnor_living_room_hru")
    assert state is None  # HRU should not have fan entity

    state = hass.states.get("fan.alnor_bathroom_fan")
    assert state is not None
    assert state.state == "on"
    assert state.attributes["percentage"] == 60


async def test_fan_turn_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_exhaust_controller,
) -> None:
    """Test turning on the fan."""
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

        await hass.services.async_call(
            FAN_DOMAIN,
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: "fan.alnor_bathroom_fan",
                ATTR_PERCENTAGE: 75,
            },
            blocking=True,
        )

        mock_exhaust_controller.set_speed.assert_called_with(75)


async def test_fan_turn_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_exhaust_controller,
) -> None:
    """Test turning off the fan."""
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

        await hass.services.async_call(
            FAN_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: "fan.alnor_bathroom_fan"},
            blocking=True,
        )

        mock_exhaust_controller.set_speed.assert_called_with(0)


async def test_fan_set_percentage(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_exhaust_controller,
) -> None:
    """Test setting fan speed percentage."""
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

        await hass.services.async_call(
            FAN_DOMAIN,
            SERVICE_SET_PERCENTAGE,
            {
                ATTR_ENTITY_ID: "fan.alnor_bathroom_fan",
                ATTR_PERCENTAGE: 80,
            },
            blocking=True,
        )

        mock_exhaust_controller.set_speed.assert_called_with(80)


async def test_fan_set_preset_mode(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_exhaust_controller,
) -> None:
    """Test setting fan preset mode."""
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

        await hass.services.async_call(
            FAN_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: "fan.alnor_bathroom_fan",
                ATTR_PRESET_MODE: "auto",
            },
            blocking=True,
        )

        mock_exhaust_controller.set_mode.assert_called_with(VentilationMode.AUTO)
