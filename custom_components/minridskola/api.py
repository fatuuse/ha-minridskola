"""HTTP client for minridskola."""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import replace
from urllib.parse import quote, urljoin
from collections import deque
from dataclasses import dataclass

import aiohttp

from .const import (
    BASE_URL,
    DEBUG_BUFFER_SIZE,
    LOGGER,
    LOGIN_FIELD_PASS,
    LOGIN_FIELD_USER,
    PATH_START,  # children list == start page (one account per child)
    PATH_HISTORY,
    PATH_LESSON_DETAIL,
    PATH_LESSONS,
    PATH_LOGOUT,
    LOGIN_FIELD_SUBMIT,
    PATH_LOGIN_PAGE,
    PATH_LOGIN_POST,
    PATH_SCHOOLS,
)
from .errors import AuthError, ConnectError, ParseError
from .parsers import (
    parse_autosubmit_form,
    parse_hidden_fields,
    parse_history,
    parse_lesson_detail,
    parse_lessons,
    parse_login_result,
    parse_schools,
    parse_welcome_name,
)
from .summaries import Child, School, WeeklyLesson

MAX_HOPS = 4
TIMEOUT = aiohttp.ClientTimeout(total=30)


@dataclass
class Capture:
    """One captured response (kept in memory only while debug is on)."""

    method: str
    url: str
    status: int
    elapsed_ms: int
    redirects: list[str]
    body: str


def redact(text: str, secrets: list[str]) -> str:
    """Remove secrets and obvious tokens from text."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    text = re.sub(r"(?i)(password|passwd|pwd)(\"?\s*[:=]\s*\"?)[^\"&\s<]+", r"\1\2***", text)
    return text


class MinRidskolaClient:
    """Client. Uses its own cookie session (pass aiohttp session with cookie jar)."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        school_id: str | None = None,
        username: str | None = None,
        password: str | None = None,
        debug: bool = False,
    ) -> None:
        self._session = session
        self.school_id = school_id
        self._username = username
        self._password = password
        self.debug = debug
        self.captures: deque[Capture] = deque(maxlen=DEBUG_BUFFER_SIZE)
        self._signed_in = False
        self._last_url = BASE_URL + "/"
        self._welcome_name: str | None = None

    @property
    def secrets(self) -> list[str]:
        return [s for s in (self._username, self._password) if s]

    async def _request(self, method: str, path: str, **kwargs) -> str:
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        start = time.monotonic()
        # Log form field NAMES only, never values.
        form = kwargs.get("data")
        LOGGER.debug(
            "%s %s (form fields: %s)",
            method,
            url,
            sorted(form) if isinstance(form, dict) else None,
        )
        try:
            async with self._session.request(
                method, url, timeout=TIMEOUT, allow_redirects=True, **kwargs
            ) as resp:
                body = await resp.text()
                self._last_url = str(resp.url)
                elapsed = int((time.monotonic() - start) * 1000)
                redirects = [str(r.url) for r in resp.history]
                LOGGER.debug(
                    "<- %s %s status=%s bytes=%s %sms redirects=%s final=%s",
                    method,
                    url,
                    resp.status,
                    len(body),
                    elapsed,
                    len(redirects),
                    resp.url,
                )
                if self.debug:
                    self.captures.append(
                        Capture(method, str(resp.url), resp.status, elapsed, redirects, body)
                    )
                if resp.status in (401, 403):
                    raise AuthError(f"HTTP {resp.status} from {resp.url}")
                if resp.status >= 400:
                    raise ConnectError(f"HTTP {resp.status} from {resp.url}")
                return body
        except (aiohttp.ClientError, TimeoutError) as err:
            LOGGER.debug("Request failed: %s %s: %r", method, url, err)
            raise ConnectError(str(err)) from err

    # --- public API -----------------------------------------------------

    async def async_get_schools(self) -> list[School]:
        return parse_schools(await self._request("GET", PATH_SCHOOLS))

    async def async_login(self) -> None:
        if not (self._username and self._password):
            raise AuthError("Missing credentials")
        # 1) GET the school's login page (LicNr selects the school), 2) POST the
        # ASP.NET form incl. __VIEWSTATE/__EVENTVALIDATION.
        page = await self._request("GET", PATH_LOGIN_PAGE, params={"LicNr": self.school_id})
        form = parse_hidden_fields(page)
        form.update(
            {
                LOGIN_FIELD_USER: self._username,
                LOGIN_FIELD_PASS: self._password,
                LOGIN_FIELD_SUBMIT: "Logga in",
            }
        )
        body = await self._request("POST", PATH_LOGIN_POST, data=form)
        # Login passes through auto-submitting pages (Init_LoggaIn_Save -> Main_Init -> Main_Start).
        for _ in range(MAX_HOPS):
            if parse_login_result(body):
                break
            hop = parse_autosubmit_form(body)
            if not hop:
                break
            action, fields = hop
            LOGGER.debug("Following auto-submit form -> %s", action)
            body = await self._request("POST", urljoin(self._last_url, action), data=fields)
        if not parse_login_result(body):
            raise AuthError("Sign-in rejected or unexpected page")
        self._welcome_name = parse_welcome_name(body)
        self._signed_in = True
        LOGGER.debug("Signed in")

    async def _ensure_login(self) -> None:
        if not self._signed_in:
            await self.async_login()

    async def async_get_children(self) -> list[Child]:
        """One account = one child (login uses the child's personal number)."""
        await self._ensure_login()
        if not self._welcome_name:
            self._welcome_name = parse_welcome_name(await self._request("GET", PATH_START))
        # Stable id without storing the personal number in unique ids.
        child_id = hashlib.sha256((self._username or "").encode()).hexdigest()[:12]
        return [Child(child_id, self._welcome_name)]

    async def async_logout(self) -> None:
        """Sign out (best effort, never raises) so no session lingers on the server."""
        if not self._signed_in:
            return
        self._signed_in = False
        try:
            await self._request("GET", PATH_LOGOUT)
            LOGGER.debug("Signed out")
        except (ConnectError, AuthError) as err:
            LOGGER.debug("Logout failed (ignored): %r", err)

    async def async_get_lessons(self, keep_session: bool = False) -> list[WeeklyLesson]:
        """Fetch lessons. Signs out afterwards unless keep_session=True."""
        try:
            return await self._get_lessons()
        finally:
            if not keep_session:
                await self.async_logout()

    async def _get_lessons(self) -> list[WeeklyLesson]:
        await self._ensure_login()
        try:
            body = await self._request("GET", PATH_LESSONS)
        except AuthError:
            # Session expired: one re-login, then retry once.
            self._signed_in = False
            await self.async_login()
            body = await self._request("GET", PATH_LESSONS)
        weekly = parse_lessons(body)
        # Enrich with period and instructor message from each lesson's detail page.
        enriched: list[WeeklyLesson] = []
        for w in weekly:
            try:
                detail = parse_lesson_detail(
                    await self._request("GET", f"{PATH_LESSON_DETAIL}?KNummerPlats={quote(w.key)}")
                )
            except ParseError as err:
                LOGGER.debug("Detail page not parsed for %s: %r", w.lesson_id, err)
                enriched.append(w)
            else:
                # History page is session-bound to the lesson opened just above.
                try:
                    history = tuple(parse_history(await self._request("GET", PATH_HISTORY)))
                except ParseError as err:
                    LOGGER.debug("History not parsed for %s: %r", w.lesson_id, err)
                    history = ()
                enriched.append(replace(w, history=history, **detail))
        return enriched
