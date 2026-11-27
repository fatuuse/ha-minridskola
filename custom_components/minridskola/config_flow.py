"""Config flow: school -> credentials -> child."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import MinRidskolaClient, redact
from .const import (
    CONF_CHILD_ID,
    CONF_CHILD_NAME,
    CONF_DEBUG,
    CONF_PASSWORD,
    CONF_SCHOOL_ID,
    CONF_SCHOOL_NAME,
    CONF_USERNAME,
    DEBUG_DIR,
    DOMAIN,
    LOGGER,
)
from .errors import AuthError, ConnectError, ParseError


def _select(options: list[tuple[str, str]]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[SelectOptionDict(value=v, label=l) for v, l in options],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class MinRidskolaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._school_id = ""
        self._school_name = ""
        self._username = ""
        self._password = ""
        self._schools: dict[str, str] = {}
        self._children: dict[str, str] = {}
        self._client: MinRidskolaClient | None = None

    def _new_client(self) -> MinRidskolaClient:
        return MinRidskolaClient(
            async_create_clientsession(self.hass),
            school_id=self._school_id,
            username=self._username,
            password=self._password,
        )

    # Step 1: school (list from site; manual entry if the list cannot be read)
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if not self._schools:
            try:
                schools = await self._new_client().async_get_schools()
                self._schools = {s.school_id: s.name for s in schools}
            except (ConnectError, ParseError) as err:
                LOGGER.debug("Could not list schools, using manual entry: %r", err)
                return await self.async_step_school_manual()
        if user_input is not None:
            self._school_id = user_input[CONF_SCHOOL_ID]
            self._school_name = self._schools.get(self._school_id, self._school_id)
            return await self.async_step_credentials()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_SCHOOL_ID): _select(list(self._schools.items()))}
            ),
            errors=errors,
        )

    async def async_step_school_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._school_id = user_input[CONF_SCHOOL_ID].strip()
            self._school_name = user_input[CONF_SCHOOL_NAME].strip() or self._school_id
            return await self.async_step_credentials()
        return self.async_show_form(
            step_id="school_manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCHOOL_ID): str,
                    vol.Optional(CONF_SCHOOL_NAME, default=""): str,
                }
            ),
        )

    # Step 2: credentials, validated by listing children
    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._client = self._new_client()
            try:
                children = await self._client.async_get_children()
                await self._client.async_logout()
            except AuthError:
                errors["base"] = "invalid_auth"
            except ConnectError:
                errors["base"] = "cannot_connect"
            except ParseError as err:
                LOGGER.debug("Parse error in credentials step: %r", err)
                errors["base"] = "parse_error"
            else:
                if not children:
                    errors["base"] = "no_children"
                else:
                    self._children = {c.child_id: c.name for c in children}
                    if len(self._children) == 1:
                        return await self._async_create(next(iter(self._children)))
                    return await self.async_step_child()
        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=self._username): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            description_placeholders={"school": self._school_name},
            errors=errors,
        )

    # Step 3: child
    async def _async_create(self, child_id: str) -> ConfigFlowResult:
        await self.async_set_unique_id(f"{self._school_id}_{child_id}")
        self._abort_if_unique_id_configured()
        child_name = self._children[child_id]
        return self.async_create_entry(
            title=f"{child_name} ({self._school_name})",
            data={
                CONF_SCHOOL_ID: self._school_id,
                CONF_SCHOOL_NAME: self._school_name,
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_CHILD_ID: child_id,
                CONF_CHILD_NAME: child_name,
            },
        )

    # Step 3: child (only shown if the account exposes several)
    async def async_step_child(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await self._async_create(user_input[CONF_CHILD_ID])
        return self.async_show_form(
            step_id="child",
            data_schema=vol.Schema(
                {vol.Required(CONF_CHILD_ID): _select(list(self._children.items()))}
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> MinRidskolaOptionsFlow:
        return MinRidskolaOptionsFlow()


class MinRidskolaOptionsFlow(OptionsFlow):
    """Menu: settings or debug dump."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["settings", "debug_dump"])

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEBUG, default=opts.get(CONF_DEBUG, False)): bool,
                }
            ),
        )

    async def async_step_debug_dump(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Fetch fresh data with capture on and write redacted raw responses to a file."""
        client: MinRidskolaClient = self.config_entry.runtime_data.client
        was_debug = client.debug
        client.debug = True
        client.captures.clear()
        error = ""
        try:
            await client.async_get_lessons()
        except (AuthError, ConnectError, ParseError) as err:
            # Expected while parsers are stubs: the raw responses are the point.
            error = f"{type(err).__name__}: {err}"
        finally:
            client.debug = was_debug

        secrets = client.secrets
        lines = [f"# minridskola debug dump {datetime.now().isoformat()}", f"# result: {error or 'ok'}"]
        for cap in client.captures:
            lines += [
                "",
                (
                    f"=== {cap.method} {cap.url} status={cap.status} {cap.elapsed_ms}ms "
                    f"redirects={cap.redirects}"
                ),
                redact(cap.body, secrets),
            ]
        out_dir = Path(self.hass.config.path(DEBUG_DIR))
        out_file = out_dir / f"dump_{datetime.now():%Y%m%d_%H%M%S}.txt"

        def _write() -> None:
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file.write_text("\n".join(lines), encoding="utf-8")

        await self.hass.async_add_executor_job(_write)
        LOGGER.debug("Debug dump written: %s", out_file)
        return self.async_abort(
            reason="debug_written", description_placeholders={"path": str(out_file)}
        )
