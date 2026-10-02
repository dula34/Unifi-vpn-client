"""Config flow for UniFi VPN Client."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant

from . import create_api
from .api import UniFiVpnApiError, UniFiVpnAuthError, normalize_host
from .const import CONF_SITE, DEFAULT_SITE, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SITE, default=DEFAULT_SITE): str,
        vol.Optional(CONF_VERIFY_SSL, default=False): bool,
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): str})


async def _validate(hass: HomeAssistant, data: dict[str, Any]) -> int:
    """Log in and return number of VPN clients found."""
    api = create_api(hass, data)
    try:
        return len(await api.get_vpn_clients())
    finally:
        await api.async_close()


class UniFiVpnConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step where the user enters gateway credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_HOST] = normalize_host(user_input[CONF_HOST])
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}|{user_input[CONF_SITE]}"
            )
            self._abort_if_unique_id_configured()
            try:
                count = await _validate(self.hass, user_input)
            except UniFiVpnAuthError:
                errors["base"] = "invalid_auth"
            except UniFiVpnApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown"
            else:
                if count == 0:
                    errors["base"] = "no_vpn_clients"
                else:
                    return self.async_create_entry(
                        title=f"UniFi VPN ({user_input[CONF_HOST].split('//')[-1]})",
                        data=user_input,
                    )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after the stored credentials stopped working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new password and validate it before updating the entry."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            try:
                await _validate(self.hass, data)
            except UniFiVpnAuthError:
                errors["base"] = "invalid_auth"
            except UniFiVpnApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=REAUTH_SCHEMA, errors=errors
        )
