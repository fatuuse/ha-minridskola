"""Pure helpers and data models. No Home Assistant imports (testable)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass(frozen=True)
class School:
    school_id: str
    name: str


@dataclass(frozen=True)
class Child:
    child_id: str
    name: str


@dataclass(frozen=True)
class Lesson:
    lesson_id: str
    start: datetime
    end: datetime
    title: str
    instructor: str | None = None
    horse: str | None = None
    location: str | None = None
    cancelled: bool = False
    note: str | None = None  # message from the instructor


@dataclass(frozen=True)
class HistoryEntry:
    """One attended week from 'Narvarohistorik'."""

    year: int
    week: int  # ISO week
    horse: str | None = None
    level: str | None = None
    kind: str | None = None  # e.g. TEORI


@dataclass(frozen=True)
class WeeklyLesson:
    """A recurring booked lesson (the site lists weekday + time, not dates)."""

    lesson_id: str
    weekday: int  # Monday = 0
    start_time: time
    end_time: time
    place: str | None = None
    instructor: str | None = None
    horse: str | None = None
    kind: str | None = None  # e.g. TEORI
    note: str | None = None
    key: str = ""  # raw id for the detail page URL (contains padding spaces)
    period_start: date | None = None
    period_end: date | None = None
    message: str | None = None  # message from the instructor
    history: tuple[HistoryEntry, ...] = ()


def expand_weekly(weekly: list[WeeklyLesson], now: datetime, weeks: int = 8) -> list[Lesson]:
    """Expand weekly lessons into dated lessons from today and `weeks` weeks ahead.

    Occurrences are limited to the lesson period (from the detail page) when known.
    Per-date cancellations and breaks are not handled yet.
    """
    today = now.date()
    result: list[Lesson] = []
    for offset in range(weeks * 7):
        day = today + timedelta(days=offset)
        for w in weekly:
            if w.weekday != day.weekday():
                continue
            if (w.period_start and day < w.period_start) or (w.period_end and day > w.period_end):
                continue
            result.append(
                Lesson(
                    lesson_id=f"{w.lesson_id}_{day.isoformat()}",
                    start=datetime.combine(day, w.start_time, tzinfo=now.tzinfo),
                    end=datetime.combine(day, w.end_time, tzinfo=now.tzinfo),
                    title="Ridlektion" + (f" ({w.kind})" if w.kind else ""),
                    instructor=w.instructor,
                    horse=w.horse,
                    location=w.place,
                    note=w.message,
                )
            )
    return sorted(result, key=lambda l: l.start)


def upcoming(lessons: list[Lesson], now: datetime, days: int | None = None) -> list[Lesson]:
    """Return non-cancelled lessons that have not ended, sorted by start."""
    result = [l for l in lessons if not l.cancelled and l.end > now]
    if days is not None:
        limit = now + timedelta(days=days)
        result = [l for l in result if l.start <= limit]
    return sorted(result, key=lambda l: l.start)


def next_lesson(lessons: list[Lesson], now: datetime) -> Lesson | None:
    """Return the next (or ongoing) lesson."""
    items = upcoming(lessons, now)
    return items[0] if items else None


def next_update_delay(
    lessons: list[Lesson],
    now: datetime,
    idle: timedelta = timedelta(hours=24),
    active: timedelta = timedelta(minutes=15),
    lead: timedelta = timedelta(hours=1),
) -> timedelta:
    """Delay until the next refresh.

    `active` while now is between (start - lead) and end of a lesson, otherwise
    `idle`, shortened so the refresh happens when the next active window opens.
    """
    for lesson in upcoming(lessons, now):  # sorted by start, not ended
        opens = lesson.start - lead
        if opens <= now:
            return active
        return max(min(idle, opens - now), timedelta(minutes=1))
    return idle
