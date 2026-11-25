"""Sensor platform."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import MinRidskolaCoordinator
from .entity import MinRidskolaEntity
from .summaries import next_lesson, upcoming


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: MinRidskolaCoordinator = entry.runtime_data
    async_add_entities(
        [NextLessonSensor(coordinator), UpcomingCountSensor(coordinator), LastHorseSensor(coordinator)]
    )


class NextLessonSensor(MinRidskolaEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: MinRidskolaCoordinator) -> None:
        super().__init__(coordinator, "next_lesson")

    @property
    def native_value(self) -> datetime | None:
        lesson = next_lesson(self.coordinator.data or [], dt_util.now())
        return lesson.start if lesson else None

    @property
    def extra_state_attributes(self) -> dict | None:
        lesson = next_lesson(self.coordinator.data or [], dt_util.now())
        if not lesson:
            return None
        return {
            "title": lesson.title,
            "end": lesson.end.isoformat(),
            "instructor": lesson.instructor,
            "horse": lesson.horse,
            "location": lesson.location,
            "message": lesson.note,
        }


class UpcomingCountSensor(MinRidskolaEntity, SensorEntity):
    _attr_native_unit_of_measurement = "lessons"

    def __init__(self, coordinator: MinRidskolaCoordinator) -> None:
        super().__init__(coordinator, "upcoming_count")

    @property
    def native_value(self) -> int:
        return len(upcoming(self.coordinator.data or [], dt_util.now()))


class LastHorseSensor(MinRidskolaEntity, SensorEntity):
    """Horse from the most recent attended (non-theory) week."""

    def __init__(self, coordinator: MinRidskolaCoordinator) -> None:
        super().__init__(coordinator, "last_horse")

    @property
    def _latest(self):
        return next((h for h in self.coordinator.history if h.horse), None)

    @property
    def native_value(self) -> str | None:
        latest = self._latest
        return latest.horse if latest else None

    @property
    def extra_state_attributes(self) -> dict | None:
        latest = self._latest
        if not latest:
            return None

        def fmt(h) -> str:
            what = h.kind or " - ".join(x for x in (h.horse, h.level) if x)
            return f"{h.year}-{h.week:02d}: {what}"

        return {
            "week": f"{latest.year}-{latest.week:02d}",
            "level": latest.level,
            "history": [fmt(h) for h in self.coordinator.history[:10]],
        }
