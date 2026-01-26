"""Constants for the Alnor integration."""
from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

# Integration domain
DOMAIN: Final = "alnor"

# Platforms
PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.BUTTON,
]

# Configuration keys
CONF_SYNC_ZONES: Final = "sync_zones"
CONF_LOCAL_IPS: Final = "local_ips"
CONF_CONNECTION_MODE: Final = "connection_mode"

# Connection modes
CONNECTION_MODE_AUTO: Final = "auto"
CONNECTION_MODE_CLOUD: Final = "cloud"
CONNECTION_MODE_LOCAL: Final = "local"

# Update intervals
UPDATE_INTERVAL_LOCAL: Final = timedelta(seconds=30)
UPDATE_INTERVAL_CLOUD: Final = timedelta(seconds=60)
UPDATE_INTERVAL_DEFAULT: Final = UPDATE_INTERVAL_CLOUD

# Device attributes
ATTR_CONNECTION_MODE: Final = "connection_mode"
ATTR_FAULT_CODE: Final = "fault_code"

# Default values
DEFAULT_SYNC_ZONES: Final = True
DEFAULT_CONNECTION_MODE: Final = CONNECTION_MODE_AUTO

# Modbus TCP
MODBUS_PORT: Final = 502
MODBUS_TIMEOUT: Final = 10
