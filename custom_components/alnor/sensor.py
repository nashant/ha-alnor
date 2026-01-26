"""Sensor platform for Alnor integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from alnor_sdk.models import DeviceState, ProductType
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AlnorDataUpdateCoordinator
from .entity import AlnorEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlnorSensorEntityDescription(SensorEntityDescription):
    """Describes Alnor sensor entity."""

    value_fn: Callable[[DeviceState], float | int | None] = lambda state: None
    product_types: list[ProductType] | None = None


# Heat Recovery Unit sensors
HRU_SENSORS: tuple[AlnorSensorEntityDescription, ...] = (
    AlnorSensorEntityDescription(
        key="indoor_temperature",
        name="Indoor temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.indoor_temperature,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
    AlnorSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.outdoor_temperature,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
    AlnorSensorEntityDescription(
        key="exhaust_temperature",
        name="Exhaust temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.exhaust_temperature,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
    AlnorSensorEntityDescription(
        key="supply_temperature",
        name="Supply temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.supply_temperature,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
    AlnorSensorEntityDescription(
        key="exhaust_fan_speed",
        name="Exhaust fan speed",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda state: state.exhaust_fan_speed,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
    AlnorSensorEntityDescription(
        key="supply_fan_speed",
        name="Supply fan speed",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda state: state.supply_fan_speed,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
    AlnorSensorEntityDescription(
        key="filter_days_remaining",
        name="Filter days remaining",
        native_unit_of_measurement="days",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=lambda state: state.filter_days_remaining,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
    AlnorSensorEntityDescription(
        key="bypass_position",
        name="Bypass position",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:valve",
        value_fn=lambda state: state.bypass_position,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
    AlnorSensorEntityDescription(
        key="preheater_demand",
        name="Preheater demand",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:radiator",
        value_fn=lambda state: state.preheater_demand,
        product_types=[ProductType.HRU_PREMAIR_450, ProductType.HRU_PREMAIR_500],
    ),
)

# Exhaust fan sensors
EXHAUST_FAN_SENSORS: tuple[AlnorSensorEntityDescription, ...] = (
    AlnorSensorEntityDescription(
        key="fan_speed",
        name="Fan speed",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        value_fn=lambda state: state.speed,
        product_types=[ProductType.VMC_02VJ04, ProductType.VMC_EXHAUST_FAN],
    ),
)

# CO2 sensor sensors
CO2_SENSORS: tuple[AlnorSensorEntityDescription, ...] = (
    AlnorSensorEntityDescription(
        key="co2_level",
        name="CO2 level",
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.co2_level,
        product_types=[ProductType.VMS_02C05, ProductType.SENSOR_CO2],
    ),
)

# Humidity sensor sensors
HUMIDITY_SENSORS: tuple[AlnorSensorEntityDescription, ...] = (
    AlnorSensorEntityDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.temperature,
        product_types=[ProductType.VMI_02MC02, ProductType.SENSOR_HUMIDITY],
    ),
    AlnorSensorEntityDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.humidity,
        product_types=[ProductType.VMI_02MC02, ProductType.SENSOR_HUMIDITY],
    ),
)

# All sensors combined
ALL_SENSORS = (
    *HRU_SENSORS,
    *EXHAUST_FAN_SENSORS,
    *CO2_SENSORS,
    *HUMIDITY_SENSORS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alnor sensor platform."""
    coordinator: AlnorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Add sensors for each device based on product type
    for device_id, device in coordinator.devices.items():
        for description in ALL_SENSORS:
            # Check if sensor applies to this device type
            if description.product_types and device.product_type in description.product_types:
                entities.append(AlnorSensor(coordinator, device_id, description))
                _LOGGER.debug(
                    "Added %s sensor for device %s",
                    description.key,
                    device.name,
                )

    async_add_entities(entities)


class AlnorSensor(AlnorEntity, SensorEntity):
    """Representation of an Alnor sensor."""

    entity_description: AlnorSensorEntityDescription

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
        description: AlnorSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{device_id}_{description.key}"

    @property
    def native_value(self) -> float | int | None:
        """Return the state of the sensor."""
        state = self.coordinator.data.get(self.device_id)
        if not state:
            return None

        try:
            return self.entity_description.value_fn(state)
        except AttributeError:
            # State attribute doesn't exist for this device
            return None
