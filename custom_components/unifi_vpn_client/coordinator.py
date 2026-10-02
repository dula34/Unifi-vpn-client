"""Data update coordinator for UniFi VPN Client."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import UniFiVpnApi, UniFiVpnApiError, UniFiVpnAuthError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class UniFiVpnCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls VPN client networks from the gateway."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: UniFiVpnApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            return await self.api.get_vpn_clients()
        except UniFiVpnAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except UniFiVpnApiError as err:
            raise UpdateFailed(str(err)) from err
