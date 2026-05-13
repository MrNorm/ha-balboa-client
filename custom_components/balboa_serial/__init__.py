"""The Balboa Spa (Serial-to-IP) integration."""

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import CONF_SYNC_TIME, DEFAULT_PORT, DEFAULT_SYNC_TIME
from .pybalboa import SpaClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.EVENT,
    Platform.FAN,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TIME,
]

SYNC_TIME_INTERVAL = timedelta(hours=1)

type BalboaConfigEntry = ConfigEntry[SpaClient]


async def async_setup_entry(hass: HomeAssistant, entry: BalboaConfigEntry) -> bool:
    """Set up Balboa Spa from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)

    _LOGGER.debug("Attempting to connect to %s:%s", host, port)
    spa = SpaClient(host, port)
    if not await spa.connect():
        raise ConfigEntryNotReady(f"Unable to connect to {host}:{port}")
    if not await spa.async_configuration_loaded():
        await spa.disconnect()
        raise ConfigEntryNotReady(f"Unable to load spa configuration from {host}:{port}")

    entry.runtime_data = spa

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await _async_setup_time_sync(hass, entry)
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    entry.async_on_unload(spa.disconnect)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BalboaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _update_listener(hass: HomeAssistant, entry: BalboaConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_setup_time_sync(hass: HomeAssistant, entry: BalboaConfigEntry) -> None:
    """Set up the time sync."""
    if not entry.options.get(CONF_SYNC_TIME, DEFAULT_SYNC_TIME):
        return

    spa = entry.runtime_data

    async def sync_time(now: datetime) -> None:
        now = dt_util.as_local(now)
        if (now.hour, now.minute) != (spa.time_hour, spa.time_minute):
            await spa.set_time(now.hour, now.minute)

    await sync_time(dt_util.utcnow())
    entry.async_on_unload(
        async_track_time_interval(hass, sync_time, SYNC_TIME_INTERVAL)
    )
