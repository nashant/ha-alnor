"""Test the Alnor coordinator."""

from unittest.mock import patch

import pytest
from alnor_sdk.exceptions import CloudAuthenticationError
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.alnor.const import (
    CONF_LOCAL_IPS,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LOCAL,
)
from custom_components.alnor.coordinator import AlnorDataUpdateCoordinator


async def test_coordinator_setup(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
    mock_sensor_controller,
) -> None:
    """Test coordinator setup."""
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
            return_value=mock_sensor_controller,
        ),
    ):
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

    # Verify API was connected
    mock_api.connect.assert_called_once()

    # Verify devices were discovered
    assert len(coordinator.devices) == 3
    assert "device_hru_1" in coordinator.devices
    assert "device_exhaust_1" in coordinator.devices
    assert "device_co2_1" in coordinator.devices

    # Verify controllers were created
    assert len(coordinator.controllers) == 3

    # Verify data was fetched
    assert len(coordinator.data) == 3
    assert "device_hru_1" in coordinator.data


async def test_coordinator_update(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
) -> None:
    """Test coordinator data update."""
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
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Verify get_state was called for each controller
        assert mock_hru_controller.get_state.call_count >= 1


async def test_coordinator_auth_failure(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
) -> None:
    """Test coordinator handles authentication failure."""
    mock_config_entry.add_to_hass(hass)

    # Make API connection fail with auth error
    mock_api.connect.side_effect = CloudAuthenticationError(401, "Invalid credentials")

    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
    ):
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)

        # Call _async_setup directly to test exception handling
        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_setup()


async def test_coordinator_connection_failure(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
) -> None:
    """Test coordinator handles connection failure."""
    mock_config_entry.add_to_hass(hass)

    # Make API connection fail
    mock_api.connect.side_effect = Exception("Connection error")

    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
    ):
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)

        # Call _async_setup directly to test exception handling
        with pytest.raises(UpdateFailed):
            await coordinator._async_setup()


async def test_coordinator_local_connection(
    hass: HomeAssistant,
    mock_api,
    mock_modbus_client,
    mock_hru_controller,
) -> None:
    """Test coordinator with local Modbus connection."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.alnor.const import DOMAIN

    # Create config entry with local IP configured
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="test@example.com",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        options={
            "sync_zones": True,
            CONF_LOCAL_IPS: {
                "device_hru_1": "192.168.1.100",
            },
        },
        unique_id="test@example.com",
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
            "custom_components.alnor.coordinator.ModbusClient",
            return_value=mock_modbus_client,
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
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Verify Modbus connection was attempted
        mock_modbus_client.connect.assert_called()

        # Verify connection mode is local
        assert coordinator.connection_modes.get("device_hru_1") == CONNECTION_MODE_LOCAL


async def test_coordinator_local_fallback_to_cloud(
    hass: HomeAssistant,
    mock_api,
    mock_modbus_client,
    mock_hru_controller,
) -> None:
    """Test coordinator falls back to cloud when local fails."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.alnor.const import DOMAIN

    # Create config entry with local IP configured
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="test@example.com",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        options={
            "sync_zones": True,
            CONF_LOCAL_IPS: {
                "device_hru_1": "192.168.1.100",
            },
        },
        unique_id="test@example.com",
    )
    mock_config_entry.add_to_hass(hass)

    # Make Modbus connection fail
    mock_modbus_client.connect.side_effect = Exception("Connection failed")

    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
        patch(
            "custom_components.alnor.coordinator.ModbusClient",
            return_value=mock_modbus_client,
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
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Verify connection mode fell back to cloud
        assert coordinator.connection_modes.get("device_hru_1") == CONNECTION_MODE_CLOUD


async def test_coordinator_per_device_error_handling(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_hru_controller,
    mock_exhaust_controller,
) -> None:
    """Test coordinator handles per-device errors gracefully."""
    mock_config_entry.add_to_hass(hass)

    # Make one controller fail
    mock_hru_controller.get_state.side_effect = Exception("Device error")

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
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Verify other devices still have data
        assert "device_exhaust_1" in coordinator.data

        # Failed device should not be in data
        assert "device_hru_1" not in coordinator.data


async def test_coordinator_zone_sync(
    hass: HomeAssistant,
    mock_api,
) -> None:
    """Test coordinator zone synchronization."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.alnor.const import DOMAIN

    # Create config entry with zone sync enabled
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="test@example.com",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        options={
            "sync_zones": True,
            "local_ips": {},
        },
        unique_id="test@example.com",
    )
    mock_config_entry.add_to_hass(hass)

    # Create some areas in Home Assistant
    from homeassistant.helpers import area_registry as ar

    area_reg = ar.async_get(hass)
    area_reg.async_create("Living Room")
    area_reg.async_create("Bedroom")

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
        ),
        patch(
            "custom_components.alnor.coordinator.SensorController",
        ),
    ):
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        # Verify zones were checked/created
        mock_api.list_zones.assert_called()
        # Bedroom should be created (Living Room already exists in mock)
        mock_api.create_zone.assert_called()


async def test_coordinator_get_device_info(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
) -> None:
    """Test coordinator get_device_info helper."""
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
        ),
        patch(
            "custom_components.alnor.coordinator.SensorController",
        ),
    ):
        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        await coordinator.async_refresh()

        device_info = coordinator.get_device_info("device_hru_1")

        assert device_info["name"] == "Alnor Living Room HRU"
        assert device_info["manufacturer"] == "Alnor"
        assert "identifiers" in device_info
