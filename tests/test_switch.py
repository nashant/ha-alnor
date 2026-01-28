"""Test switch platform."""

from unittest.mock import AsyncMock, MagicMock, patch

from alnor_sdk.models import DeviceState, ProductType, VentilationMode
import pytest
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.alnor.const import CONF_HUMIDITY_SENSORS, DOMAIN


@pytest.fixture
def mock_hru_state():
    """Create mock Heat Recovery Unit state."""
    return DeviceState(
        device_id="device_hru_1",
        speed=50,
        mode=VentilationMode.HOME,
        indoor_temperature=21.0,
        outdoor_temperature=5.0,
        supply_temperature=18.0,
        exhaust_temperature=19.0,
        supply_fan_speed=1500,
        exhaust_fan_speed=1500,
        filter_days_remaining=180,
        bypass_position=0,
        preheater_demand=25,
        preheater_available=True,
        fault_code=0,
    )


async def test_switch_setup_without_humidity_sensor(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
) -> None:
    """Test switch platform setup without humidity sensor configured."""
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

    # Verify no switch was created (no humidity sensors configured)
    state = hass.states.get("switch.alnor_living_room_hru_humidity_control")
    assert state is None


async def test_switch_setup_with_humidity_sensor(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
    mock_hru_state,
) -> None:
    """Test switch platform setup with humidity sensor configured."""
    mock_config_entry.add_to_hass(hass)

    # Add humidity sensor configuration
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            f"{CONF_HUMIDITY_SENSORS}_device_hru_1": ["sensor.bathroom_humidity"],
        },
    )

    # Mock controller to return state
    mock_hru_controller.get_state = AsyncMock(return_value=mock_hru_state)

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
        await hass.async_block_till_done()

    # Verify switch was created
    state = hass.states.get("switch.alnor_living_room_hru_humidity_control")
    assert state is not None
    assert state.state == STATE_ON


async def test_switch_turn_on(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
    mock_hru_state,
) -> None:
    """Test turning on humidity control."""
    mock_config_entry.add_to_hass(hass)

    # Add humidity sensor configuration
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            f"{CONF_HUMIDITY_SENSORS}_device_hru_1": ["sensor.bathroom_humidity"],
        },
    )

    # Mock controller to return state
    mock_hru_controller.get_state = AsyncMock(return_value=mock_hru_state)

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
        await hass.async_block_till_done()

        # Turn on the switch
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.alnor_living_room_hru_humidity_control"},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("switch.alnor_living_room_hru_humidity_control")
        assert state is not None
        assert state.state == STATE_ON


async def test_switch_turn_off(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
    mock_hru_state,
) -> None:
    """Test turning off humidity control."""
    mock_config_entry.add_to_hass(hass)

    # Add humidity sensor configuration
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            f"{CONF_HUMIDITY_SENSORS}_device_hru_1": ["sensor.bathroom_humidity"],
        },
    )

    # Mock controller to return state
    mock_hru_controller.get_state = AsyncMock(return_value=mock_hru_state)

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
        await hass.async_block_till_done()

        # Turn on first
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.alnor_living_room_hru_humidity_control"},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Then turn off
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.alnor_living_room_hru_humidity_control"},
            blocking=True,
        )
        await hass.async_block_till_done()

        state = hass.states.get("switch.alnor_living_room_hru_humidity_control")
        assert state is not None
        assert state.state == STATE_OFF
