"""UniFi VPN Client integration."""

from __future__ import annotations

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import UniFiVpnApi
from .const import CONF_SITE, DEFAULT_SITE
from .coordinator import UniFiVpnCoordinator

PLATFORMS: list[Platform] = [Platform.SWITCH]

type UniFiVpnConfigEntry = ConfigEntry[UniFiVpnCoordinator]


def create_api(hass: HomeAssistant, data: dict) -> UniFiVpnApi:
    """Create an API client with its own cookie jar (IP hosts need unsafe=True)."""
    session = async_create_clientsession(
        hass,
        verify_ssl=data.get(CONF_VERIFY_SSL, False),
        auto_cleanup=False,
        cookie_jar=aiohttp.CookieJar(unsafe=True),
    )
    return UniFiVpnApi(
        session,
        data[CONF_HOST],
        data[CONF_USERNAME],
        data[CONF_PASSWORD],
        data.get(CONF_SITE, DEFAULT_SITE),
    )


async def async_setup_entry(hass: HomeAssistant, entry: UniFiVpnConfigEntry) -> bool:
    """Set up from a config entry."""
    api = create_api(hass, dict(entry.data))
    coordinator = UniFiVpnCoordinator(hass, entry, api)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await api.async_close()
        raise
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: UniFiVpnConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.api.async_close()
    return unload_ok
