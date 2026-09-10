"""ARPAT Toscana integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ArpatApi
from .config_flow import get_enabled_data_types
from .const import (
    CONF_DATA_TYPES,
    CONF_STATION,
    CONF_STATION_DATA,
    DOMAIN,
    LEGACY_DEFAULT_DATA_TYPES,
)
from .coordinator import ArpatDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up ARPAT Toscana from a config entry."""
    station = entry.data[CONF_STATION]
    station_data = dict(entry.data.get(CONF_STATION_DATA, {}))

    api = ArpatApi(async_get_clientsession(hass))
    coordinator = ArpatDataUpdateCoordinator(
        hass,
        api,
        station,
        station_data,
        get_enabled_data_types(entry),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Migrate configuration entries created by ARPAT Toscana 0.1.x."""
    if entry.version == 1:
        data = dict(entry.data)
        data.setdefault(
            CONF_DATA_TYPES,
            list(LEGACY_DEFAULT_DATA_TYPES),
        )

        hass.config_entries.async_update_entry(
            entry,
            data=data,
            version=2,
        )

    return True
