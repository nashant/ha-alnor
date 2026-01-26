"""Base entity for Alnor integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_CONNECTION_MODE, DOMAIN
from .coordinator import AlnorDataUpdateCoordinator


class AlnorEntity(CoordinatorEntity[AlnorDataUpdateCoordinator]):
    """Base class for Alnor entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlnorDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.device_id = device_id
        self._attr_device_info = coordinator.get_device_info(device_id)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.device_id in self.coordinator.data
        )

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return additional state attributes."""
        # Add connection mode to attributes
        connection_mode = self.coordinator.connection_modes.get(self.device_id)
        if connection_mode:
            return {ATTR_CONNECTION_MODE: connection_mode}
        return None
