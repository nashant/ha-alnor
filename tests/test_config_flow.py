"""Test the Alnor config flow."""

from unittest.mock import patch

from alnor_sdk.exceptions import CloudAuthenticationError
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.alnor.const import CONF_LOCAL_IPS, CONF_SYNC_ZONES, DOMAIN


async def test_user_form(hass: HomeAssistant, mock_api) -> None:
    """Test the user config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.alnor.config_flow.AlnorCloudApi",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",
                CONF_SYNC_ZONES: True,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "test@example.com"
    assert result["data"] == {
        CONF_USERNAME: "test@example.com",
        CONF_PASSWORD: "test_password",
    }
    assert result["options"] == {
        CONF_SYNC_ZONES: True,
    }


async def test_user_form_invalid_auth(hass: HomeAssistant, mock_api) -> None:
    """Test invalid authentication."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Make authentication fail
    mock_api.connect.side_effect = CloudAuthenticationError(401, "Invalid credentials")

    with patch(
        "custom_components.alnor.config_flow.AlnorCloudApi",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "wrong_password",
                CONF_SYNC_ZONES: False,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_form_cannot_connect(hass: HomeAssistant, mock_api) -> None:
    """Test connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Make connection fail
    mock_api.connect.side_effect = Exception("Connection error")

    with patch(
        "custom_components.alnor.config_flow.AlnorCloudApi",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",
                CONF_SYNC_ZONES: True,
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_form_already_configured(hass: HomeAssistant, mock_api) -> None:
    """Test duplicate configuration."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    # Create an existing entry
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        title="test@example.com",
        data={
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "test_password",
        },
        options={},
        unique_id="test@example.com",
    )
    existing_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.alnor.config_flow.AlnorCloudApi",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_USERNAME: "test@example.com",
                CONF_PASSWORD: "test_password",
                CONF_SYNC_ZONES: True,
            },
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
) -> None:
    """Test options flow."""
    mock_config_entry.add_to_hass(hass)

    # Set up the coordinator data
    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
    ):
        from custom_components.alnor.coordinator import AlnorDataUpdateCoordinator

        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = coordinator

        # Mock devices
        coordinator.devices = {
            "device1": type("Device", (), {"name": "Device 1"})(),
            "device2": type("Device", (), {"name": "Device 2"})(),
        }

    # Start options flow
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Update sync_zones only
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYNC_ZONES: False,
            "configure_local": False,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SYNC_ZONES: False,
        CONF_LOCAL_IPS: {},
    }


async def test_options_flow_local_config(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_modbus_client,
) -> None:
    """Test options flow with local IP configuration."""
    mock_config_entry.add_to_hass(hass)

    # Set up the coordinator data
    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
    ):
        from custom_components.alnor.coordinator import AlnorDataUpdateCoordinator

        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = coordinator

        # Mock devices
        from alnor_sdk.models import Device, ProductType

        coordinator.devices = {
            "device1": Device(
                device_id="device1",
                product_id="0001c89f",
                name="Device 1",
                product_type=ProductType.HEAT_RECOVERY_UNIT,
                host="",
            ),
        }
        coordinator.device_to_bridge = {"device1": "bridge123"}

    # Start options flow
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    # Choose to configure local
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYNC_ZONES: True,
            "configure_local": True,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "local_config"

    # Configure local IP
    with patch(
        "custom_components.alnor.config_flow.ModbusClient",
        return_value=mock_modbus_client,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                "local_ip_device1": "192.168.1.100",
            },
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_SYNC_ZONES: True,
        CONF_LOCAL_IPS: {
            "device1": "192.168.1.100",
        },
    }


async def test_options_flow_local_config_invalid_ip(
    hass: HomeAssistant,
    mock_config_entry,
    mock_api,
    mock_modbus_client,
) -> None:
    """Test options flow with invalid local IP."""
    mock_config_entry.add_to_hass(hass)

    # Set up the coordinator data
    with (
        patch(
            "custom_components.alnor.coordinator.AlnorCloudApi",
            return_value=mock_api,
        ),
        patch(
            "custom_components.alnor.coordinator.CloudClient",
        ),
    ):
        from custom_components.alnor.coordinator import AlnorDataUpdateCoordinator

        coordinator = AlnorDataUpdateCoordinator(hass, mock_config_entry)
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][mock_config_entry.entry_id] = coordinator

        # Mock devices
        from alnor_sdk.models import Device, ProductType

        coordinator.devices = {
            "device1": Device(
                device_id="device1",
                product_id="0001c89f",
                name="Device 1",
                product_type=ProductType.HEAT_RECOVERY_UNIT,
                host="",
            ),
        }
        coordinator.device_to_bridge = {"device1": "bridge123"}

    # Start options flow and navigate to local config
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SYNC_ZONES: True,
            "configure_local": True,
        },
    )

    # Make connection fail
    mock_modbus_client.connect.side_effect = Exception("Connection failed")

    with patch(
        "custom_components.alnor.config_flow.ModbusClient",
        return_value=mock_modbus_client,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                "local_ip_device1": "192.168.1.100",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "local_config"
    assert "local_ip_device1" in result["errors"]
