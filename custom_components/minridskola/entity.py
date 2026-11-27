"""Base entity."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CHILD_ID,
    CONF_CHILD_NAME,
    CONF_SCHOOL_ID,
    CONF_SCHOOL_NAME,
    DOMAIN,
)
from .coordinator import MinRidskolaCoordinator


class MinRidskolaEntity(CoordinatorEntity[MinRidskolaCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: MinRidskolaCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_unique_id = (
            f"{entry.data[CONF_SCHOOL_ID]}_{entry.data[CONF_CHILD_ID]}_{key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.data[CONF_SCHOOL_ID]}_{entry.data[CONF_CHILD_ID]}")},
            name=entry.data[CONF_CHILD_NAME],
            manufacturer=entry.data[CONF_SCHOOL_NAME],
            model="Min Ridskola",
        )
