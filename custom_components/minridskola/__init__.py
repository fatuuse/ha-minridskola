"""Min Ridskola integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import MinRidskolaClient
from .const import (
    CONF_DEBUG,
    CONF_PASSWORD,
    CONF_SCHOOL_ID,
    CONF_USERNAME,
    LOGGER,
)
from .coordinator import MinRidskolaCoordinator

PLATFORMS = [Platform.BUTTON, Platform.CALENDAR, Platform.SENSOR]

type MinRidskolaConfigEntry = ConfigEntry[MinRidskolaCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MinRidskolaConfigEntry) -> bool:
    # Own session = own cookie jar per entry.
    session = async_create_clientsession(hass)
    client = MinRidskolaClient(
        session,
        school_id=entry.data[CONF_SCHOOL_ID],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        debug=entry.options.get(CONF_DEBUG, False),
    )
    coordinator = MinRidskolaCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    LOGGER.debug("Entry set up")
    return True


async def _async_update_listener(hass: HomeAssistant, entry: MinRidskolaConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: MinRidskolaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
