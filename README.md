# UniFi VPN Client for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/dula34/Unifi-vpn-client/actions/workflows/validate.yml/badge.svg)](https://github.com/dula34/Unifi-vpn-client/actions/workflows/validate.yml)

A Home Assistant custom integration that turns every **VPN client** network on a UniFi OS gateway
(UDM, UDM Pro, UDR, UCG, UXG, Cloud Key with Network, …) into a **switch**. Turn the switch on or off to
enable or disable that VPN client connection, from the UI or from automations.

## Features

- One switch entity per VPN client network (`purpose: vpn-client`) on the selected site
- New VPN clients that you add on the gateway show up automatically
- Local polling every 60 seconds, with no cloud account needed
- Logs in again automatically when the session expires, and starts a reauth flow if the password changes
- UI configuration (config flow), with English and Slovak translations

Each switch exposes these attributes:

| Attribute    | Description                                  |
| ------------ | -------------------------------------------- |
| `network_id` | UniFi network `_id` of the VPN client        |
| `vpn_type`   | VPN type reported by UniFi (e.g. `wireguard-client`, `openvpn-client`) |

## Requirements

- Home Assistant **2024.11** or newer
- A UniFi OS gateway running the UniFi Network application
- A **local** UniFi OS account **without MFA** that is allowed to change network settings
  (create it under *UniFi OS → Admins & Users*, and select *Restrict to local access only*)

## Installation

### HACS (recommended)

This repository is not in the default HACS store yet, so add it as a custom repository:

1. Make sure [HACS](https://hacs.xyz/docs/use/) is installed.
2. In Home Assistant, open **HACS**.
3. Click the **⋮** menu in the top right corner and select **Custom repositories**.
4. Fill in:
   - **Repository:** `https://github.com/dula34/Unifi-vpn-client`
   - **Type:** `Integration`
5. Click **Add** and close the dialog.
6. Search HACS for **UniFi VPN Client**, open it and click **Download**.
7. **Restart Home Assistant.**

Or use this button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dula34&repository=Unifi-vpn-client&category=integration)

HACS tells you when new releases are available, and you can update from the HACS UI.

### Manual

1. Download the latest release, or clone this repository.
2. Copy `custom_components/unifi_vpn_client` into the `custom_components` directory of your
   Home Assistant configuration. The result should be `<config>/custom_components/unifi_vpn_client/manifest.json`.
3. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **UniFi VPN Client**.
3. Fill in the form:

| Field                  | Description                                                                 |
| ---------------------- | --------------------------------------------------------------------------- |
| Gateway address        | IP address or hostname of the gateway, e.g. `192.168.1.1`. `https://` is added automatically. |
| Username / Password    | Local UniFi OS account (no MFA)                                             |
| Site                   | UniFi Network site name. Default: `default`                                 |
| Verify SSL certificate | Turn this off (the default) for the gateway's self-signed certificate       |

The integration checks the credentials and stops with an error if the site has no VPN client networks.
You can add each gateway/site combination once.

[![Open your Home Assistant instance and start setting up the integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=unifi_vpn_client)

## Example automation

```yaml
automation:
  - alias: "Enable VPN at night"
    triggers:
      - trigger: time
        at: "22:00:00"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.unifi_vpn_clients_my_vpn
```

## How it works

The integration uses the same local API as the UniFi Network web UI:

- `POST /api/auth/login`: logs in (session cookie and CSRF token)
- `GET /proxy/network/api/s/<site>/rest/networkconf`: lists networks, filtered to `purpose == "vpn-client"`
- `PUT /proxy/network/api/s/<site>/rest/networkconf/<id>`: sends the network object back with `enabled` toggled

## Troubleshooting

- **Invalid username or password**: use a local account, not a UI.com cloud account, and make sure MFA is off.
- **Cannot connect**: check that Home Assistant can reach the gateway over HTTPS. If you turned on SSL verification, check that the certificate is valid.
- **No VPN clients found**: create the VPN client first under *Settings → VPN → VPN Client* in UniFi Network, and check the site name.

To turn on debug logging:

```yaml
logger:
  logs:
    custom_components.unifi_vpn_client: debug
```

## Publishing a new version (maintainers)

1. Bump `version` in `custom_components/unifi_vpn_client/manifest.json`.
2. Commit, push, and wait for the **Validate** workflow (HACS + Hassfest) to pass.
3. Create a **GitHub release** (a full release, not just a tag), e.g. `v1.0.1`. HACS uses releases for its version list.

To add this integration to the default HACS store, follow
[Include default repositories](https://hacs.xyz/docs/publish/include). The repository needs a description
and topics on GitHub, both validation actions must pass, and it needs at least one release. Then open a PR
against [hacs/default](https://github.com/hacs/default).

## License

[Apache License 2.0](LICENSE)
