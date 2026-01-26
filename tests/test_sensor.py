"""Test the Alnor sensor platform."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant


async def test_sensor_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_sensor_controller,
) -> None:
    """Test sensor platform setup."""
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
            return_value=mock_sensor_controller,
        ),
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    # Verify HRU sensors were created
    state = hass.states.get("sensor.living_room_hru_indoor_temperature")
    assert state is not None
    assert state.state == "22.5"

    state = hass.states.get("sensor.living_room_hru_outdoor_temperature")
    assert state is not None
    assert state.state == "10.0"

    state = hass.states.get("sensor.living_room_hru_filter_days_remaining")
    assert state is not None
    assert state.state == "60"

    # Verify CO2 sensor was created
    state = hass.states.get("sensor.office_co2_sensor_co2_level")
    assert state is not None
    assert state.state == "650"


async def test_sensor_values(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test sensor values are correct."""
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

        # Check various sensor values
        state = hass.states.get("sensor.living_room_hru_exhaust_fan_speed")
        assert state is not None
        assert state.state == "45"
        assert state.attributes["unit_of_measurement"] == "%"

        state = hass.states.get("sensor.living_room_hru_supply_fan_speed")
        assert state is not None
        assert state.state == "48"

        state = hass.states.get("sensor.living_room_hru_bypass_position")
        assert state is not None
        assert state.state == "0"

        state = hass.states.get("sensor.living_room_hru_preheater_demand")
        assert state is not None
        assert state.state == "10"
