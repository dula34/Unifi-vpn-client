"""Switch entities for UniFi VPN client networks."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import UniFiVpnConfigEntry
from .api import UniFiVpnApiError
from .const import DOMAIN
from .coordinator import UniFiVpnCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: UniFiVpnConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a switch per VPN client; add new ones as they appear."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = [
            UniFiVpnClientSwitch(coordinator, net_id)
            for net_id in coordinator.data
            if net_id not in known
        ]
        if new:
            known.update(ent.network_id for ent in new)
            async_add_entities(new)

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class UniFiVpnClientSwitch(CoordinatorEntity[UniFiVpnCoordinator], SwitchEntity):
    """Enable/disable a UniFi VPN client network."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:vpn"

    def __init__(self, coordinator: UniFiVpnCoordinator, network_id: str) -> None:
        """Initialize the switch for the given VPN client network id."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self.network_id = network_id
        self._attr_unique_id = f"{entry.unique_id}|{network_id}"
        self._fallback_name = coordinator.data[network_id].get("name", network_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="UniFi VPN Clients",
            manufacturer="Ubiquiti",
            model="UniFi Gateway",
            configuration_url=entry.data["host"],
        )

    @property
    def _network(self) -> dict[str, Any] | None:
        """Return the current network object, or None if it was removed."""
        return self.coordinator.data.get(self.network_id)

    @property
    def available(self) -> bool:
        """Return True if the coordinator is healthy and the network still exists."""
        return super().available and self._network is not None

    @property
    def name(self) -> str:
        """Return the VPN client name as configured on the gateway."""
        net = self._network
        return net.get("name", self._fallback_name) if net else self._fallback_name

    @property
    def is_on(self) -> bool | None:
        """Return True if the VPN client network is enabled."""
        net = self._network
        return net.get("enabled", True) if net else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the UniFi network id and VPN type."""
        net = self._network or {}
        return {"network_id": self.network_id, "vpn_type": net.get("vpn_type")}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the VPN client network."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the VPN client network."""
        await self._async_set(False)

    async def _async_set(self, enabled: bool) -> None:
        """Push the new state to the gateway, update optimistically, then refresh."""
        net = self._network
        if net is None:
            raise HomeAssistantError(f"VPN client {self.name} not found on gateway")
        try:
            await self.coordinator.api.set_enabled(net, enabled)
        except UniFiVpnApiError as err:
            raise HomeAssistantError(
                f"Failed to {'enable' if enabled else 'disable'} {self.name}: {err}"
            ) from err
        net["enabled"] = enabled
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
