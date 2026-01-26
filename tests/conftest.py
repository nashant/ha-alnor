"""Fixtures for Alnor integration tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from alnor_sdk.models import Device, DeviceState, ProductType, VentilationMode
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock setting up a config entry."""
    with patch("custom_components.alnor.async_setup_entry", return_value=True) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_api():
    """Mock AlnorCloudApi."""
    api = MagicMock()
    api.connect = AsyncMock(return_value=None)
    api.get_bridges = AsyncMock(
        return_value=[
            {
                "id": "bridge123",
                "name": "Main Bridge",
            }
        ]
    )
    api.get_devices = AsyncMock(
        return_value=[
            {
                "id": "device_hru_1",
                "name": "Living Room HRU",
                "productId": "0001c89f",
                "host": "192.168.1.100",
            },
            {
                "id": "device_exhaust_1",
                "name": "Bathroom Fan",
                "productId": "0001c844",
                "host": None,
            },
            {
                "id": "device_co2_1",
                "name": "Office CO2 Sensor",
                "productId": "0001c845",
                "host": None,
            },
        ]
    )
    api.list_zones = AsyncMock(
        return_value=[
            {"id": "zone1", "name": "Living Room"},
        ]
    )
    api.create_zone = AsyncMock(return_value={"id": "zone2", "name": "Bedroom"})
    return api


@pytest.fixture
def mock_cloud_client():
    """Mock CloudClient."""
    client = MagicMock()
    client.read_register = AsyncMock(return_value=42)
    return client


@pytest.fixture
def mock_modbus_client():
    """Mock ModbusClient."""
    client = MagicMock()
    client.connect = AsyncMock(return_value=None)
    client.disconnect = AsyncMock(return_value=None)
    client.read_register = AsyncMock(return_value=42)
    return client


@pytest.fixture
def mock_hru_controller():
    """Mock HeatRecoveryUnitController."""
    controller = MagicMock()
    controller.get_state = AsyncMock(
        return_value=DeviceState(
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
            fault_status=0,
            fault_code=0,
        )
    )
    controller.set_speed = AsyncMock(return_value=None)
    controller.set_mode = AsyncMock(return_value=None)
    controller.reset_filter_timer = AsyncMock(return_value=None)
    return controller


@pytest.fixture
def mock_exhaust_controller():
    """Mock ExhaustFanController."""
    controller = MagicMock()
    controller.get_state = AsyncMock(
        return_value=DeviceState(
            device_id="device_exhaust_1",
            speed=60,
            mode=VentilationMode.AUTO,
            fault_status=0,
            fault_code=0,
        )
    )
    controller.set_speed = AsyncMock(return_value=None)
    controller.set_mode = AsyncMock(return_value=None)
    return controller


@pytest.fixture
def mock_sensor_controller():
    """Mock SensorController."""
    controller = MagicMock()
    controller.get_state = AsyncMock(
        return_value=DeviceState(
            device_id="device_co2_1",
            co2_level=650,
            temperature=23.0,
            humidity=45,
        )
    )
    return controller


@pytest.fixture
def mock_device_hru():
    """Mock HRU Device."""
    return Device(
        device_id="device_hru_1",
        product_id="0001c89f",
        name="Living Room HRU",
        product_type=ProductType.HEAT_RECOVERY_UNIT,
        host="192.168.1.100",
    )


@pytest.fixture
def mock_device_exhaust():
    """Mock Exhaust Fan Device."""
    return Device(
        device_id="device_exhaust_1",
        product_id="0001c844",
        name="Bathroom Fan",
        product_type=ProductType.EXHAUST_FAN,
        host="",
    )


@pytest.fixture
def mock_device_co2():
    """Mock CO2 Sensor Device."""
    return Device(
        device_id="device_co2_1",
        product_id="0001c845",
        name="Office CO2 Sensor",
        product_type=ProductType.CO2_SENSOR_VMS,
        host="",
    )


@pytest.fixture
def mock_config_entry():
    """Mock ConfigEntry."""
    from homeassistant.config_entries import ConfigEntry

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test_password",
    }
    entry.options = {
        "sync_zones": True,
        "local_ips": {},
    }
    entry.add_update_listener = MagicMock()
    entry.async_on_unload = MagicMock()
    return entry
