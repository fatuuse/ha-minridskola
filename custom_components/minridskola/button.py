"""Button platform: refresh data now."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import LOGGER
from .coordinator import MinRidskolaCoordinator
from .entity import MinRidskolaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([RefreshButton(entry.runtime_data)])


class RefreshButton(MinRidskolaEntity, ButtonEntity):
    def __init__(self, coordinator: MinRidskolaCoordinator) -> None:
        super().__init__(coordinator, "refresh")

    @property
    def available(self) -> bool:
        # Stay pressable after a failed update so the user can retry.
        return True

    async def async_press(self) -> None:
        LOGGER.debug("Manual refresh requested")
        await self.coordinator.async_refresh()
