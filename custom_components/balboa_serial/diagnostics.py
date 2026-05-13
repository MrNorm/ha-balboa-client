"""Diagnostics support for Balboa Spa (Serial-to-IP)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from . import BalboaConfigEntry

REDACT = {CONF_HOST, "mac_address", "idigi_device_id", "configuration_signature"}


def _control_summary(control: Any) -> dict[str, Any]:
    try:
        state = control.state.name if hasattr(control.state, "name") else str(control.state)
    except Exception as err:  # noqa: BLE001
        state = f"<err: {err}>"
    return {
        "name": control.name,
        "type": control.control_type.value,
        "index": control.index,
        "state": state,
        "options": [getattr(o, "name", str(o)) for o in control.options],
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BalboaConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    spa = entry.runtime_data

    state = spa.state
    spa_data: dict[str, Any] = {
        "model": spa.model,
        "software_version": spa.software_version,
        "heater_type": spa.heater_type,
        "voltage": spa.voltage,
        "mac_address": spa.mac_address,
        "configuration_signature": spa.configuration_signature,
        "dip_switch": spa.dip_switch,
        "state": state.name if state is not None else None,
        "temperature_unit": spa.temperature_unit.name,
        "temperature": spa.temperature,
        "target_temperature": spa.target_temperature,
        "is_24_hour": spa.is_24_hour,
        "pump_count": spa.pump_count,
        "filter_cycle_1_running": spa.filter_cycle_1_running,
        "filter_cycle_2_running": spa.filter_cycle_2_running,
        "filter_cycle_2_enabled": spa.filter_cycle_2_enabled,
        "available": spa.available,
        "connected": spa.connected,
        "controls": [_control_summary(c) for c in spa.controls],
        "last_status_raw": (
            spa._previous_status.hex() if spa._previous_status else None  # noqa: SLF001
        ),
    }

    return {
        "entry": async_redact_data(
            {"data": dict(entry.data), "options": dict(entry.options)}, REDACT
        ),
        "spa": async_redact_data(spa_data, REDACT),
    }
