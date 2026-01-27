"""Test the Alnor binary sensor platform."""

from unittest.mock import patch

from alnor_sdk.models import DeviceState, VentilationMode
from homeassistant.core import HomeAssistant

from custom_components.alnor.const import ATTR_FAULT_CODE


async def test_binary_sensor_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
) -> None:
    """Test binary sensor platform setup."""
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

    # Verify fault sensors were created
    state = hass.states.get("binary_sensor.alnor_living_room_hru_fault")
    assert state is not None
    assert state.state == "off"  # No fault

    state = hass.states.get("binary_sensor.alnor_bathroom_fan_fault")
    assert state is not None


async def test_binary_sensor_fault_detected(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test binary sensor detects faults."""
    # Set up controller with fault
    mock_hru_controller.get_state.return_value = DeviceState(
        device_id="device_hru_1",
        speed=50,
        mode=VentilationMode.HOME,
        indoor_temperature=22.5,
        outdoor_temperature=10.0,
        exhaust_temperature=21.0,
        supply_temperature=20.0,
        exhaust_fan_speed=45,
        supply_fan_speed=48,
        filter_days_remaining=60,
        bypass_position=0,
        preheater_demand=10,
        fault_status=1,  # Fault present
        fault_code=42,
    )

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

        state = hass.states.get("binary_sensor.alnor_living_room_hru_fault")
        assert state is not None
        assert state.state == "on"  # Fault detected
        assert state.attributes[ATTR_FAULT_CODE] == 42
