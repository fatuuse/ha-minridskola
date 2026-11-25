"""Parsers for minridskola pages. Pure functions, no HA imports.

All parsers are STUBS until real HTML/JSON samples are available.
They raise ParseError so a missing implementation never looks like "no data".
"""
from __future__ import annotations

import html as htmllib
import re

from .errors import ParseError
from datetime import date, time

from .summaries import HistoryEntry, School, WeeklyLesson


def parse_schools(html: str) -> list[School]:
    """Parse school list from Init_Ridskolor.aspx.

    Each connected school has:
      onclick="SaveLicNr('XXXX-XXXX-XXXX')"
      <span class="Xe-Fet">School Name</span>, CITY

    Schools with onclick="OpenEjAnsluten()" are not connected – skip them.
    The test school (w3-text-grey) is included; callers may filter it.
    """
    # Match only entries with a real LicNr
    # Pattern: SaveLicNr('6334-2705-0934')">...<span class="Xe-Fet">Name</span>, CITY
    pattern = re.compile(
        r"SaveLicNr\('([0-9\-]+)'\)[^>]*>"
        r"\s*<span[^>]*>([^<]+)</span>,\s*([A-ZÅÄÖ/ \-]+)",
        re.IGNORECASE,
    )
    schools: list[School] = []
    seen: set[str] = set()
    for m in pattern.finditer(html):
        lic_nr = m.group(1).strip()
        name = htmllib.unescape(m.group(2).strip())
        city = m.group(3).strip().title()
        if lic_nr in seen:
            continue  # deduplication (the page renders each school twice)
        seen.add(lic_nr)
        schools.append(School(school_id=lic_nr, name=f"{name}, {city}"))
    if not schools:
        raise ParseError("parse_schools: no schools found – page structure may have changed")
    return schools


def parse_login_result(html: str) -> bool:
    """Signed in = the start page with the welcome label is shown."""
    return "ContentPlaceHolder1_labWelcomeBig" in html or "ContentPlaceHolder1_labWelcomeSmall" in html


_WELCOME_RE = re.compile(
    r'id="ContentPlaceHolder1_labWelcomeBig"[^>]*>.*?<b>(.*?)</b>', re.S | re.I
)


def parse_welcome_name(html: str) -> str:
    """Name from 'Valkommen <b>Name!</b>' (the logged-in person; one account per child)."""
    m = _WELCOME_RE.search(html)
    if not m:
        raise ParseError("Welcome name not found on start page")
    return htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip().rstrip("!").strip()


_FORM_ACTION_RE = re.compile(r'<form\b[^>]*\baction="([^"]*)"', re.I)


def parse_autosubmit_form(html: str) -> tuple[str, dict[str, str]] | None:
    """Return (action, hidden fields) for a page that auto-submits a form via JS."""
    m = _FORM_ACTION_RE.search(html)
    if not m or ".submit()" not in html:
        return None
    return htmllib.unescape(m.group(1)), _hidden_inputs(html)


_WEEKDAYS = {"mån": 0, "tis": 1, "ons": 2, "tor": 3, "fre": 4, "lör": 5, "sön": 6}
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")
_ID_SPLIT = "GoToLektion('"


def _text(cell: str) -> str:
    cell = re.sub(r"<br\s*/?>", "\n", cell, flags=re.I)
    cell = htmllib.unescape(re.sub(r"<[^>]+>", "", cell))
    return cell.replace("\u2011", "").replace("\xa0", " ").strip()


def _panel(html: str, panel_id: str) -> str:
    start = html.find(f'id="ContentPlaceHolder1_{panel_id}"')
    if start < 0:
        return ""
    end = html.find('id="ContentPlaceHolder1_', start + 10)
    return html[start : end if end > 0 else len(html)]


def _segments(panel: str) -> list[tuple[str, list[str]]]:
    """Return (lesson id, cells of the inner row) per lesson in a panel."""
    result = []
    for seg in panel.split(_ID_SPLIT)[1:]:
        lesson_id = seg.split("'", 1)[0]  # raw, keeps padding spaces
        m = re.search(r'<tr class="w3-white[^>]*>(.*?)</tr>', seg, re.S)
        if m:
            result.append((lesson_id, [_text(c) for c in _CELL_RE.findall(m.group(1))]))
    return result


def parse_lessons(html: str) -> list[WeeklyLesson]:
    """Parse 'Mina bokade lektioner' (recurring weekly lessons)."""
    if "Mina bokade lektioner" not in html:
        raise ParseError("'Mina bokade lektioner' not found on lesson page")
    big = _segments(_panel(html, "panStorSkarm"))
    kinds = {}
    for lesson_id, cells in _segments(_panel(html, "panLitenSkarm")):
        # kind is shown as "(TEORI)" in the 3rd cell on small screens
        if len(cells) >= 3 and cells[2].startswith("(") and cells[2].endswith(")"):
            kinds[lesson_id] = cells[2][1:-1].strip() or None
    lessons: list[WeeklyLesson] = []
    for lesson_id, cells in big:
        if len(cells) < 6:
            raise ParseError(f"Unexpected lesson row layout ({len(cells)} cells)")
        day_time, place_range, extra, instructor, horse, note = cells[:6]
        wd = _WEEKDAYS.get(day_time.split("\n")[0].strip()[:3].lower())
        rng = _RANGE_RE.search(place_range)
        if wd is None or not rng:
            raise ParseError(f"Cannot read weekday/time from row: {day_time!r} {place_range!r}")
        h1, m1, h2, m2 = (int(x) for x in rng.groups())
        place = place_range.split("\n")[0].strip() or None
        lessons.append(
            WeeklyLesson(
                lesson_id=" ".join(lesson_id.split()),
                key=lesson_id,
                weekday=wd,
                start_time=time(h1, m1),
                end_time=time(h2, m2),
                place=place,
                instructor=instructor or None,
                horse=horse or None,
                kind=kinds.get(lesson_id) or extra.strip("() ") or None,
                note=note or None,
            )
        )
    return lessons


_INPUT_RE = re.compile(r"<input\b[^>]*>", re.I)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def _hidden_inputs(html: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for tag in _INPUT_RE.findall(html):
        attrs = {k.lower(): v for k, v in _ATTR_RE.findall(tag)}
        if attrs.get("type", "").lower() == "hidden" and "name" in attrs:
            fields[attrs["name"]] = attrs.get("value", "")
    return fields


def parse_hidden_fields(html: str) -> dict[str, str]:
    """Return ASP.NET hidden inputs (__VIEWSTATE, __EVENTVALIDATION, ...)."""
    fields = _hidden_inputs(html)
    if "__VIEWSTATE" not in fields:
        raise ParseError("No __VIEWSTATE on login page")
    return fields


_PERIOD_RE = re.compile(
    r"Lektionsperiod\s*</td>\s*<td[^>]*>\s*(\d{4})-(\d{2})-(\d{2})\s*-\s*(\d{4})-(\d{2})-(\d{2})", re.S
)
_MESSAGE_RE = re.compile(
    r"Meddelande från ridläraren.*?<span class=\"w3-text-indigo[^\"]*\"[^>]*>(.*?)</span>", re.S
)


def parse_lesson_detail(html: str) -> dict:
    """Parse Lekt_VisaLektion0: lesson period and message from the instructor."""
    if "Lektionsuppgifter" not in html:
        raise ParseError("'Lektionsuppgifter' not found on lesson detail page")
    result: dict = {"period_start": None, "period_end": None, "message": None}
    m = _PERIOD_RE.search(html)
    if m:
        y1, m1, d1, y2, m2, d2 = (int(x) for x in m.groups())
        result["period_start"] = date(y1, m1, d1)
        result["period_end"] = date(y2, m2, d2)
    m = _MESSAGE_RE.search(html)
    if m:
        text = _text(m.group(1))
        result["message"] = re.sub(r"\n{3,}", "\n\n", text) or None
    return result


_HISTORY_RE = re.compile(
    r'Vecka\s*<span[^>]*>(\d{4})(?:&#x2011;|\u2011|-)(\d{1,2})</span></td>\s*<td[^>]*>(.*?)</td>', re.S
)


def parse_history(html: str) -> list[HistoryEntry]:
    """Parse Lekt_VisaLektion3 ('Narvarohistorik'): '<horse> - <level>' or TEORI per ISO week."""
    if "ContentPlaceHolder1_labRubrikStor" not in html:
        raise ParseError("Not a lesson history page")
    entries: list[HistoryEntry] = []
    for year, week, cell in _HISTORY_RE.findall(html):
        text = _text(cell)
        if not text:
            continue
        if " - " in text:
            horse, level = (x.strip() or None for x in text.rsplit(" - ", 1))
            entries.append(HistoryEntry(int(year), int(week), horse, level))
        elif text.isupper():
            entries.append(HistoryEntry(int(year), int(week), kind=text))
        else:
            entries.append(HistoryEntry(int(year), int(week), horse=text))
    return entries
