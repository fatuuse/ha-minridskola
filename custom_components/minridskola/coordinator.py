"""Data coordinator."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MinRidskolaClient
from .const import (
    ACTIVE_INTERVAL_MINUTES,
    ACTIVE_LEAD_MINUTES,
    CONF_CHILD_ID,
    DOMAIN,
    IDLE_INTERVAL_HOURS,
    LOGGER,
)
from .errors import AuthError, ConnectError, ParseError
from homeassistant.util import dt as dt_util

from .summaries import Lesson, expand_weekly, next_update_delay


EXPAND_WEEKS = 8


class MinRidskolaCoordinator(DataUpdateCoordinator[list[Lesson]]):
    """Fetch lessons for one child."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: MinRidskolaClient
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(hours=IDLE_INTERVAL_HOURS),
        )
        self.client = client
        self.history: list = []  # HistoryEntry, newest first
        self._in_active_window = False
        self._child_id: str = entry.data[CONF_CHILD_ID]

    async def _async_update_data(self) -> list[Lesson]:
        try:
            weekly = await self.client.async_get_lessons(keep_session=self._in_active_window)
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ConnectError, ParseError) as err:
            # Retry sooner than the daily idle interval.
            self.update_interval = timedelta(minutes=ACTIVE_INTERVAL_MINUTES)
            # Never return [] on failure: empty data would drop entities.
            raise UpdateFailed(str(err)) from err
        self.history = sorted(
            (h for w in weekly for h in w.history), key=lambda h: (h.year, h.week), reverse=True
        )
        lessons = expand_weekly(weekly, dt_util.now(), EXPAND_WEEKS)
        LOGGER.debug("Fetched %s weekly lessons, expanded to %s", len(weekly), len(lessons))
        delay = next_update_delay(
            lessons,
            dt_util.now(),
            idle=timedelta(hours=IDLE_INTERVAL_HOURS),
            active=timedelta(minutes=ACTIVE_INTERVAL_MINUTES),
            lead=timedelta(minutes=ACTIVE_LEAD_MINUTES),
        )
        self._in_active_window = delay <= timedelta(minutes=ACTIVE_INTERVAL_MINUTES)
        self.update_interval = delay
        LOGGER.debug("Next update in %s (session kept: %s)", self.update_interval, self._in_active_window)
        return lessons
