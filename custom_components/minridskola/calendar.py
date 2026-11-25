"""Calendar platform: all lessons for the child."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import MinRidskolaCoordinator
from .entity import MinRidskolaEntity
from .summaries import Lesson, next_lesson


def _to_event(lesson: Lesson) -> CalendarEvent:
    parts = [p for p in (lesson.instructor, lesson.horse) if p]
    return CalendarEvent(
        start=lesson.start,
        end=lesson.end,
        summary=lesson.title,
        description="\n".join(x for x in (", ".join(parts), lesson.note) if x) or None,
        location=lesson.location,
        uid=lesson.lesson_id,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([LessonCalendar(entry.runtime_data)])


class LessonCalendar(MinRidskolaEntity, CalendarEntity):
    def __init__(self, coordinator: MinRidskolaCoordinator) -> None:
        super().__init__(coordinator, "lessons")

    @property
    def event(self) -> CalendarEvent | None:
        lesson = next_lesson(self.coordinator.data or [], dt_util.now())
        return _to_event(lesson) if lesson else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            _to_event(l)
            for l in (self.coordinator.data or [])
            if l.start < end_date and l.end > start_date
        ]
