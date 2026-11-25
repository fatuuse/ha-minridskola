"""Diagnostics (credentials, names and ids redacted; no response bodies)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHILD_ID,
    CONF_CHILD_NAME,
    CONF_PASSWORD,
    CONF_SCHOOL_ID,
    CONF_SCHOOL_NAME,
    CONF_USERNAME,
)

TO_REDACT = {
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCHOOL_ID,
    CONF_SCHOOL_NAME,
    CONF_CHILD_ID,
    CONF_CHILD_NAME,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "last_update_success": coordinator.last_update_success,
        "lesson_count": len(coordinator.data or []),
        "captures": [
            {"method": c.method, "status": c.status, "bytes": len(c.body), "ms": c.elapsed_ms}
            for c in coordinator.client.captures
        ],
    }
