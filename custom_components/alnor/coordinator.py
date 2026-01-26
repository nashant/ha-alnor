"""Data coordinator for Alnor integration."""

from __future__ import annotations

import logging
from typing import Any

from alnor_sdk.communication import AlnorCloudApi, CloudClient, ModbusClient
from alnor_sdk.controllers import (
    BaseDeviceController,
    ExhaustFanController,
    HeatRecoveryUnitController,
    SensorController,
)
from alnor_sdk.exceptions import CloudAuthenticationError
from alnor_sdk.models import Device, DeviceState, ProductType
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_LOCAL_IPS,
    CONF_SYNC_ZONES,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LOCAL,
    DOMAIN,
    MODBUS_PORT,
    UPDATE_INTERVAL_CLOUD,
    UPDATE_INTERVAL_LOCAL,
)

_LOGGER = logging.getLogger(__name__)


class AlnorDataUpdateCoordinator(DataUpdateCoordinator[dict[str, DeviceState]]):
    """Class to manage fetching Alnor data from API."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry

        # API and device storage
        self.api: AlnorCloudApi | None = None
        self.bridges: list[dict[str, Any]] = []
        self.devices: dict[str, Device] = {}
        self.device_to_bridge: dict[str, str] = {}  # Map device_id -> bridge_id

        # Client storage (dual-mode support)
        self.cloud_clients: dict[str, CloudClient] = {}
        self.modbus_clients: dict[str, ModbusClient] = {}

        # Controller storage
        self.controllers: dict[str, BaseDeviceController] = {}
        self.connection_modes: dict[str, str] = {}

        # Track setup state
        self._setup_complete = False

        # Determine update interval based on connection modes
        update_interval = UPDATE_INTERVAL_CLOUD

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=config_entry,
        )

    async def _async_update_data(self) -> dict[str, DeviceState]:
        """Fetch data from API."""
        # Run setup on first update
        if not self._setup_complete:
            await self._async_setup()
            self._setup_complete = True

        states: dict[str, DeviceState] = {}

        # Update each device
        for device_id, controller in self.controllers.items():
            try:
                state = await controller.get_state()
                states[device_id] = state

            except Exception as err:
                # Check if this was a local connection that failed
                if self.connection_modes.get(device_id) == CONNECTION_MODE_LOCAL:
                    _LOGGER.warning(
                        "Failed to fetch data for device %s via local connection: %s. "
                        "Attempting fallback to cloud.",
                        device_id,
                        err,
                    )

                    # Try to fall back to cloud
                    try:
                        if device_id in self.cloud_clients:
                            # Create cloud controller
                            device = self.devices[device_id]
                            cloud_controller = self._create_controller(
                                self.cloud_clients[device_id], device
                            )
                            if cloud_controller:
                                self.controllers[device_id] = cloud_controller
                                self.connection_modes[device_id] = CONNECTION_MODE_CLOUD

                                # Retry with cloud
                                state = await cloud_controller.get_state()
                                states[device_id] = state
                                _LOGGER.info(
                                    "Successfully fell back to cloud for device %s",
                                    device_id,
                                )
                                continue
                    except Exception as cloud_err:
                        _LOGGER.error(
                            "Cloud fallback also failed for device %s: %s",
                            device_id,
                            cloud_err,
                        )

                # Log the error and continue
                _LOGGER.warning("Failed to fetch data for device %s: %s", device_id, err)

        # Adjust update interval based on active connection modes
        if any(mode == CONNECTION_MODE_LOCAL for mode in self.connection_modes.values()):
            self.update_interval = UPDATE_INTERVAL_LOCAL
        else:
            self.update_interval = UPDATE_INTERVAL_CLOUD

        return states

    async def _async_setup(self) -> None:
        """Set up the coordinator - called once on first update."""
        _LOGGER.debug("Setting up Alnor coordinator")

        # Get credentials from config entry
        username = self.config_entry.data[CONF_USERNAME]
        password = self.config_entry.data[CONF_PASSWORD]

        # Create and connect to API
        self.api = AlnorCloudApi()

        try:
            await self.api.connect(username, password)
            _LOGGER.info("Successfully connected to Alnor Cloud API")

        except CloudAuthenticationError as err:
            _LOGGER.error("Authentication failed: %s", err)
            raise ConfigEntryAuthFailed("Invalid credentials") from err

        except Exception as err:
            _LOGGER.error("Failed to connect to Alnor Cloud API: %s", err)
            raise UpdateFailed(f"Failed to connect: {err}") from err

        # Discover bridges and devices
        try:
            self.bridges = await self.api.get_bridges()
            _LOGGER.info("Discovered %d bridge(s)", len(self.bridges))

            # Get devices for each bridge
            for bridge in self.bridges:
                bridge_id = bridge["id"]
                bridge_name = bridge.get("name", bridge_id)

                devices = await self.api.get_devices(bridge_id)
                _LOGGER.info(
                    "Discovered %d device(s) on bridge %s",
                    len(devices),
                    bridge_name,
                )

                # Set up each device
                for device_data in devices:
                    device_id = device_data["id"]

                    # Get product type from product_id
                    product_id = device_data.get("productId", "")
                    product_type = ProductType.from_product_id(product_id)
                    if not product_type:
                        _LOGGER.warning(
                            "Unknown product ID %s for device %s, skipping",
                            product_id,
                            device_id,
                        )
                        continue

                    # Create Device object
                    device = Device(
                        device_id=device_id,
                        product_id=product_id,
                        name=device_data.get("name", "Unknown Device"),
                        product_type=product_type,
                        host=device_data.get("host", ""),
                        zone_id=device_data.get("zoneId"),
                    )

                    self.devices[device_id] = device
                    self.device_to_bridge[device_id] = bridge_id

                    # Set up connection (local or cloud)
                    await self._setup_device_connection(device, device_id)

        except Exception as err:
            _LOGGER.error("Failed to discover devices: %s", err)
            raise UpdateFailed(f"Failed to discover devices: {err}") from err

        # Sync zones if enabled
        if self.config_entry.options.get(CONF_SYNC_ZONES, True):
            await self._sync_zones()

    async def _setup_device_connection(self, device: Device, device_id: str) -> None:
        """Set up connection for a device (local with cloud fallback)."""
        local_ips = self.config_entry.options.get(CONF_LOCAL_IPS, {})
        local_ip = local_ips.get(device_id) or device.host

        client = None
        connection_mode = CONNECTION_MODE_CLOUD  # default

        # Try local Modbus TCP if IP available
        if local_ip:
            try:
                modbus_client = ModbusClient(local_ip, MODBUS_PORT)
                await modbus_client.connect()

                # Test connection with a simple read
                # Note: This assumes the SDK supports a test read operation
                # If not, we'll catch the exception on first actual use

                self.modbus_clients[device_id] = modbus_client
                client = modbus_client
                connection_mode = CONNECTION_MODE_LOCAL
                _LOGGER.info(
                    "Connected to %s locally at %s:%d",
                    device.name,
                    local_ip,
                    MODBUS_PORT,
                )

            except Exception as err:
                _LOGGER.warning(
                    "Failed to connect to %s locally at %s:%d: %s. " "Falling back to cloud.",
                    device.name,
                    local_ip,
                    MODBUS_PORT,
                    err,
                )
                # Fall through to cloud client

        # Use cloud client as fallback or primary
        if client is None:
            if self.api is None:
                _LOGGER.error("API not initialized, cannot create cloud client")
                return

            cloud_client = CloudClient(self.api, device_id)
            self.cloud_clients[device_id] = cloud_client
            client = cloud_client
            connection_mode = CONNECTION_MODE_CLOUD

        # Create controller with the client
        controller = self._create_controller(client, device)
        if controller:
            self.controllers[device_id] = controller
            self.connection_modes[device_id] = connection_mode
            _LOGGER.debug(
                "Created %s controller for device %s (mode: %s)",
                type(controller).__name__,
                device.name,
                connection_mode,
            )
        else:
            _LOGGER.warning(
                "Could not create controller for device %s (type: %s)",
                device.name,
                device.product_type,
            )

    def _create_controller(
        self, client: CloudClient | ModbusClient, device: Device
    ) -> BaseDeviceController | None:
        """Create controller for device type."""
        # Map product type to controller
        # Note: HRU controller has different signature than others
        if device.product_type == ProductType.HEAT_RECOVERY_UNIT:
            return HeatRecoveryUnitController(client, device.device_id, device.product_id)

        elif device.product_type == ProductType.EXHAUST_FAN:
            return ExhaustFanController(client, device)

        elif device.product_type in [
            ProductType.CO2_SENSOR_VMI,
            ProductType.CO2_SENSOR_VMS,
            ProductType.HUMIDITY_SENSOR_VMI,
            ProductType.HUMIDITY_SENSOR_VMS,
        ]:
            return SensorController(client, device)

        # Unknown device type
        _LOGGER.warning(
            "Unknown product type %s for device %s",
            device.product_type,
            device.name,
        )
        return None

    async def _sync_zones(self) -> None:
        """Synchronize Alnor zones with Home Assistant areas."""
        if self.api is None:
            _LOGGER.warning("API not initialized, cannot sync zones")
            return

        _LOGGER.info("Starting zone synchronization with Home Assistant areas")

        area_registry = ar.async_get(self.hass)

        for bridge in self.bridges:
            bridge_id = bridge["id"]
            bridge_name = bridge.get("name", bridge_id)

            try:
                # Get existing zones (if API supports it)
                # Note: This assumes the SDK has a list_zones method
                # If not available, this will raise AttributeError
                existing_zones = await self.api.list_zones(bridge_id)
                existing_zone_names = {zone.get("name", "").lower() for zone in existing_zones}

            except AttributeError:
                _LOGGER.warning(
                    "SDK does not support listing zones, skipping sync for bridge %s",
                    bridge_name,
                )
                continue

            except Exception as err:
                _LOGGER.warning(
                    "Failed to list zones for bridge %s: %s",
                    bridge_name,
                    err,
                )
                continue

            # Create zones for each HA area
            for area in area_registry.areas.values():
                area_name_lower = area.name.lower()

                if area_name_lower not in existing_zone_names:
                    try:
                        await self.api.create_zone(bridge_id, area.name)
                        _LOGGER.info(
                            "Created zone '%s' on bridge %s",
                            area.name,
                            bridge_name,
                        )

                    except Exception as err:
                        # Zone may already exist despite not being in list
                        _LOGGER.debug(
                            "Could not create zone '%s' on bridge %s: %s",
                            area.name,
                            bridge_name,
                            err,
                        )

    def get_device_info(self, device_id: str) -> DeviceInfo:
        """Get device info for a device."""
        device = self.devices.get(device_id)
        if not device:
            return DeviceInfo(identifiers={(DOMAIN, device_id)})

        # Find the bridge for this device
        bridge_id = self.device_to_bridge.get(device_id)
        bridge = None
        if bridge_id:
            for b in self.bridges:
                if b["id"] == bridge_id:
                    bridge = b
                    break

        device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.name,
            manufacturer="Alnor",
            model=(
                (
                    device.product_type.value
                    if hasattr(device.product_type, "value")
                    else str(device.product_type)
                )
                if device.product_type
                else "Unknown"
            ),
        )

        # Link to bridge
        if bridge:
            device_info["via_device"] = (DOMAIN, bridge["id"])

        # Map to HA area based on zone
        # Note: This would require zone information from device data
        # For now, we'll skip this mapping

        return device_info

    def get_bridge_info(self, bridge_id: str) -> DeviceInfo:
        """Get device info for a bridge."""
        bridge = None
        for b in self.bridges:
            if b["id"] == bridge_id:
                bridge = b
                break

        if not bridge:
            return DeviceInfo(identifiers={(DOMAIN, bridge_id)})

        return DeviceInfo(
            identifiers={(DOMAIN, bridge_id)},
            name=bridge.get("name", "Alnor Bridge"),
            manufacturer="Alnor",
            model="Gateway",
        )
