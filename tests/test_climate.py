"""Test the Alnor climate platform."""

from unittest.mock import patch

from alnor_sdk.models import VentilationMode
from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    HVACMode,
)
from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant


async def test_climate_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
) -> None:
    """Test climate platform setup."""
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

    # Verify climate entity was created for HRU
    state = hass.states.get("climate.alnor_living_room_hru")
    assert state is not None
    assert state.state == HVACMode.FAN_ONLY
    assert state.attributes["current_temperature"] == 20.0  # supply_temperature

    # Verify no climate entity for exhaust fan
    state = hass.states.get("climate.alnor_bathroom_fan")
    assert state is None


async def test_climate_hvac_mode_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test setting HVAC mode to OFF."""
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
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.alnor_living_room_hru",
                ATTR_HVAC_MODE: HVACMode.OFF,
            },
            blocking=True,
        )

        mock_hru_controller.set_speed.assert_called_with(0)


async def test_climate_hvac_mode_fan_only(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test setting HVAC mode to FAN_ONLY."""
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

        # Set speed to 0 first to test turning on
        mock_hru_controller.get_state.return_value.speed = 0

        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {
                ATTR_ENTITY_ID: "climate.alnor_living_room_hru",
                ATTR_HVAC_MODE: HVACMode.FAN_ONLY,
            },
            blocking=True,
        )

        mock_hru_controller.set_speed.assert_called_with(50)


async def test_climate_preset_mode(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test setting preset mode."""
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
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: "climate.alnor_living_room_hru",
                ATTR_PRESET_MODE: "party",
            },
            blocking=True,
        )

        mock_hru_controller.set_mode.assert_called_with(VentilationMode.PARTY)


async def test_climate_attributes(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test climate entity attributes."""
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

    state = hass.states.get("climate.alnor_living_room_hru")
    assert state is not None
    assert state.attributes["indoor_temperature"] == 22.5
    assert state.attributes["outdoor_temperature"] == 10.0
    assert state.attributes["exhaust_temperature"] == 21.0
    assert state.attributes["preheater_demand"] == 10
    assert state.attributes["bypass_position"] == 0
    assert state.attributes["exhaust_fan_speed"] == 45
    assert state.attributes["supply_fan_speed"] == 48
    assert state.attributes["filter_days_remaining"] == 60


async def test_climate_preset_mode_auto_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test that setting a non-standby preset mode automatically turns on the system."""
    mock_config_entry.add_to_hass(hass)

    # Set initial state to OFF (speed = 0)
    from alnor_sdk.models import DeviceState, VentilationMode

    mock_hru_controller.get_state.return_value = DeviceState(
        device_id="device_hru_1",
        speed=0,  # System is OFF
        mode=VentilationMode.STANDBY,
        indoor_temperature=22.5,
        outdoor_temperature=10.0,
        exhaust_temperature=21.0,
        supply_temperature=20.0,
        exhaust_fan_speed=0,
        supply_fan_speed=0,
        filter_days_remaining=60,
        bypass_position=0,
        preheater_demand=0,
        fault_status=0,
        fault_code=0,
    )

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

        # Set a non-standby preset mode (e.g., "party")
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: "climate.alnor_living_room_hru",
                ATTR_PRESET_MODE: "party",
            },
            blocking=True,
        )

        # Verify mode was set
        mock_hru_controller.set_mode.assert_called_with(VentilationMode.PARTY)
        # Verify system was turned on (set_speed called with 50)
        mock_hru_controller.set_speed.assert_called_with(50)


async def test_climate_preset_mode_standby_turns_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test that setting standby preset mode turns off the system."""
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

        # Set standby preset mode
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            {
                ATTR_ENTITY_ID: "climate.alnor_living_room_hru",
                ATTR_PRESET_MODE: "standby",
            },
            blocking=True,
        )

        # Verify mode was set to standby
        from alnor_sdk.models import VentilationMode

        mock_hru_controller.set_mode.assert_called_with(VentilationMode.STANDBY)
        # Verify system was turned off (set_speed called with 0)
        mock_hru_controller.set_speed.assert_called_with(0)
