"""Minimal async client for the UniFi OS Network API (VPN client networks)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import REQUEST_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class UniFiVpnApiError(Exception):
    """Generic API / connection error."""


class UniFiVpnAuthError(UniFiVpnApiError):
    """Authentication failed."""


def normalize_host(host: str) -> str:
    """Return host as https base URL without trailing slash."""
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    return host


class UniFiVpnApi:
    """UniFi OS gateway API wrapper."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str,
        password: str,
        site: str,
    ) -> None:
        self._session = session
        self._host = normalize_host(host)
        self._username = username
        self._password = password
        self._base = f"/proxy/network/api/s/{site}/rest/networkconf"
        self._csrf: str | None = None
        self._logged_in = False
        self._login_lock = asyncio.Lock()

    async def async_close(self) -> None:
        """Log out and close the HTTP session."""
        if self._logged_in:
            try:
                await self._raw("POST", "/api/auth/logout", {})
            except UniFiVpnApiError:
                pass
        await self._session.close()

    async def login(self) -> None:
        """Authenticate against UniFi OS."""
        async with self._login_lock:
            try:
                async with asyncio.timeout(REQUEST_TIMEOUT):
                    async with self._session.post(
                        f"{self._host}/api/auth/login",
                        json={
                            "username": self._username,
                            "password": self._password,
                            "remember": True,
                        },
                    ) as resp:
                        if resp.status in (400, 401, 403):
                            raise UniFiVpnAuthError(
                                f"Login rejected (HTTP {resp.status})"
                            )
                        if resp.status != 200:
                            raise UniFiVpnApiError(
                                f"Login failed (HTTP {resp.status})"
                            )
                        self._csrf = resp.headers.get("X-CSRF-Token")
                        self._logged_in = True
            except (aiohttp.ClientError, TimeoutError) as err:
                raise UniFiVpnApiError(f"Cannot connect: {err}") from err

    async def _raw(
        self, method: str, path: str, payload: Any = None
    ) -> tuple[int, Any]:
        headers = {"X-CSRF-Token": self._csrf} if self._csrf else {}
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.request(
                    method, f"{self._host}{path}", json=payload, headers=headers
                ) as resp:
                    if new_token := resp.headers.get("X-Updated-CSRF-Token"):
                        self._csrf = new_token
                    if resp.status == 401:
                        return resp.status, None
                    if resp.status >= 400:
                        body = await resp.text()
                        raise UniFiVpnApiError(
                            f"{method} {path} -> HTTP {resp.status}: {body[:200]}"
                        )
                    return resp.status, await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UniFiVpnApiError(f"Request failed: {err}") from err

    async def _request(self, method: str, path: str, payload: Any = None) -> Any:
        if not self._logged_in:
            await self.login()
        status, data = await self._raw(method, path, payload)
        if status == 401:
            _LOGGER.debug("Session expired, re-authenticating")
            self._logged_in = False
            await self.login()
            status, data = await self._raw(method, path, payload)
            if status == 401:
                raise UniFiVpnAuthError("Unauthorized after re-login")
        return (data or {}).get("data", [])

    async def get_vpn_clients(self) -> dict[str, dict[str, Any]]:
        """Return VPN client networks keyed by network _id."""
        networks = await self._request("GET", self._base)
        return {
            net["_id"]: net
            for net in networks
            if net.get("purpose") == "vpn-client" and "_id" in net
        }

    async def set_enabled(self, network: dict[str, Any], enabled: bool) -> None:
        """Enable or disable a VPN client network."""
        payload = {**network, "enabled": enabled}
        await self._request("PUT", f"{self._base}/{network['_id']}", payload)
