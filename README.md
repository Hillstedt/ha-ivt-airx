# IVT AirX Home Assistant Integration

A read-only Home Assistant custom integration for the **IVT AirX 407** (and other Bosch Thermotechnology heat pumps using the K30 WiFi module) via the Bosch PoinTT cloud API.

## What it does

Polls your heat pump every 2 minutes and exposes sensors in Home Assistant:

| Sensor | Description |
|---|---|
| Outdoor Temperature | Outside air temperature |
| Supply Temperature | Flow temperature from the heat pump |
| Return Temperature | Return temperature to the heat pump |
| Hot Water Temperature | Domestic hot water (DHW) tank temperature |
| Compressor Modulation | Compressor load (%) |
| Compressor Status | off / heating / cooling / dhw / defrost / alarm |
| Central Heating Status | Whether CH circuit is active |

> **Note:** This is Phase 1 — read-only sensors only. Climate control and write entities are planned for a later release.

## Requirements

- IVT AirX 407 (or compatible Bosch/Buderus heat pump with K30 WiFi module)
- A **SingleKey ID** account linked to your heat pump (the same account you use in the IVT/Bosch app)
- Home Assistant with a terminal or SSH access for installation

## Installation

SSH into your Home Assistant and run:

```bash
git clone https://github.com/Hillstedt/ha-ivt-airx /config/custom_components/ivt_airx
```

Then restart Home Assistant.

To update later:
```bash
cd /config/custom_components/ivt_airx && git pull
```

## Setup

Go to **Settings → Devices & Services → Add Integration** and search for **IVT AirX**.

The integration uses OAuth2 with SingleKey ID. Your credentials are entered directly on Bosch's login page — they are never seen by Home Assistant or this integration.

### Getting the authorization code (Chrome)

Chrome cannot open the `com.bosch.tt.dashtt.pointt://` app link that Bosch uses as the OAuth redirect, so you need to capture the code manually via DevTools. **The code expires in ~60 seconds, so do this quickly.**

1. In HA, start the **Add Integration** flow — it shows an authorization URL.
2. Open a new Chrome tab, press **F12** to open DevTools, click the **Network** tab, and tick **Preserve log**.
3. Paste the authorization URL into the address bar and press Enter.
4. Log in with your SingleKey ID credentials.
5. After login, find the request in the Network tab that starts with `com.bosch.tt.dashtt.pointt://` — it will have a red ✗ (failed) icon.
6. Click it, then copy the full **Request URL** from the Headers panel.
7. Switch back to HA and paste the full URL into the field, then submit.

If HA shows "authentication failed", the code expired — just start the flow again from step 1.

### Getting the authorization code (Firefox)

Firefox handles the custom scheme more visibly:

1. Start the flow in HA and open the authorization URL in Firefox.
2. Log in with your SingleKey ID credentials.
3. Firefox will show a dialog saying it can't open the link — the `com.bosch.tt.dashtt.pointt://...` URL will be visible in the address bar.
4. Copy that full URL and paste it into HA.

## Token refresh

The login is a one-time setup. The integration automatically refreshes its access token in the background (access tokens last ~1 hour; refresh tokens last months). Refreshed tokens are persisted back into the HA config entry, so they survive restarts.

You would only need to re-authenticate if you revoke access in your SingleKey ID account, or after a very long period of inactivity.

## Compatibility

This integration targets the IVT AirX 407 but should work with any Bosch Thermotechnology product that:
- Uses the K30 WiFi module
- Connects to the Bosch PoinTT cloud API (`pointt-api.bosch-thermotechnology.com`)
- Is managed via the SingleKey ID account system

This includes some **Buderus** and **Bosch** branded heat pumps sold in other markets.

## Credits

Reverse-engineered with reference to:
- [fuatsengul/ivt-heatpump-ha](https://github.com/fuatsengul/ivt-heatpump-ha)
- [BassXT/buderus](https://github.com/BassXT/buderus)
