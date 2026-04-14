# CyberPower PowerPanel Cloud

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/github/license/Csontikka/ha-cyberpower-cloud?color=yellow)](https://github.com/Csontikka/ha-cyberpower-cloud/blob/master/LICENSE)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=Csontikka_ha-cyberpower-cloud&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=Csontikka_ha-cyberpower-cloud)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=Csontikka_ha-cyberpower-cloud&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=Csontikka_ha-cyberpower-cloud)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=Csontikka_ha-cyberpower-cloud&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=Csontikka_ha-cyberpower-cloud)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-donate-yellow.svg?style=plastic)](https://buymeacoffee.com/Csontikka)

> **Note:** For best viewing experience, read this documentation on [GitHub](https://github.com/Csontikka/ha-cyberpower-cloud).

![CyberPower PowerPanel Cloud Banner](https://raw.githubusercontent.com/Csontikka/ha-cyberpower-cloud/master/images/banner.png)

Home Assistant custom integration for **CyberPower UPS** devices connected via [PowerPanel Cloud](https://powerpanel.cyberpower.com).

Monitor battery status, power consumption, load, voltage, temperature and more — directly from your Home Assistant dashboard. Get instant notifications on power outages through dedicated events.

## Prerequisites

1. A CyberPower UPS registered in [PowerPanel Cloud](https://powerpanel.cyberpower.com)
2. **Two-factor authentication must be DISABLED** on the PowerPanel Cloud account:
   - Open the PowerPanel Cloud mobile app
   - Go to **Account** → **Security**
   - Turn off **Two-Factor Authentication**
   - The integration uses the mobile app's login flow, which does not support 2FA — login will fail otherwise
3. **Temperature unit must be set to Celsius** in the PowerPanel Cloud app:
   - Open the PowerPanel Cloud mobile app
   - Go to **Account** → **Settings**
   - Set **Temperature Unit** to **°C (Celsius)**
   - The API returns raw values without unit indicators — this integration assumes Celsius

## Supported devices

Works with any CyberPower UPS registered in PowerPanel Cloud, including models with:

- **RWCCARD100** cloud network card
- **RWCCARD200** cloud network card
- Built-in cloud connectivity

Tested with:

| Model | Cloud Card | Status |
|-------|-----------|--------|
| OLS2000EA | RWCCARD100 | Fully working |

> If you have a different model working, please open an issue so we can add it to the list.

## Features

### Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Battery | % | Battery charge level |
| Battery Runtime | min | Estimated remaining runtime on battery |
| Battery Health (BHI) | % | Battery health indicator |
| Power Consumption | W | Real-time power draw (Energy Dashboard compatible) |
| Load | % | Load percentage (calculated from watts / rated power) |
| Input Voltage | V | Utility input voltage |
| Output Voltage | V | UPS output voltage |
| Input Frequency | Hz | Utility input frequency |
| Output Frequency | Hz | UPS output frequency |
| UPS Temperature | °C | Internal UPS temperature |
| Environment Temperature | °C | External sensor temperature |
| Environment Humidity | % | External sensor humidity |
| Status | — | Device status (Normal / Warning / Critical / Offline) |
| Last Update | timestamp | Last successful API data update |

> Temperature and humidity sensors require a compatible environmental sensor connected to the UPS. They will show as "Unknown" if not available.

### Binary sensors

| Sensor | Description |
|--------|-------------|
| On Battery | `on` when UPS is running on battery (power outage) |

### Configuration entities

| Entity | Type | Description |
|--------|------|-------------|
| UPS Rated Power | number | Per-device rated power in watts — used to calculate Load % |

> Set the rated power to your UPS model's **watt** rating (not VA). For example, OLS2000EA = 1800W. If not configured, Load % will show as "Unknown" until you set it.

### Power outage events

The integration fires Home Assistant events when the power state changes — faster than polling the binary sensor:

| Event | Fired when |
|-------|------------|
| `cyberpower_cloud_power_outage_started` | UPS switches to battery (power outage detected) |
| `cyberpower_cloud_power_outage_ended` | UPS returns to mains power |

Event data:

```json
{
  "device_sn": "...",
  "device_name": "...",
  "device_model": "..."
}
```

### Other features

- **Multiple UPS support** — one account can monitor multiple devices
- **Energy Dashboard** — Power Consumption sensor is compatible with HA Energy Dashboard
- **Auto re-authentication** — automatic token refresh on expiry
- **Configurable polling** — update interval from 60 to 3600 seconds (default: 300)
- **Error resilience** — stops polling after 3 consecutive failures to avoid account lockout, creates repair issues
- **Diagnostics** — built-in diagnostics export for troubleshooting (sensitive data redacted)
- **Firmware version** — displayed in device info when reported by the API

## Installation

### HACS (recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations** > click the three-dot menu (top right) > **Custom repositories**
3. Add repository URL: `https://github.com/Csontikka/ha-cyberpower-cloud`
4. Select category: **Integration**
5. Click **Add**
6. Search for **"CyberPower PowerPanel Cloud"** and click **Download**
7. **Restart Home Assistant**

### Manual installation

1. Download the latest release from [GitHub](https://github.com/Csontikka/ha-cyberpower-cloud/releases)
2. Copy the `custom_components/cyberpower_cloud` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Setup

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **"CyberPower PowerPanel Cloud"**
3. Enter your PowerPanel Cloud email and password
4. The integration will discover all UPS devices on your account

<!-- [SCREENSHOT: config flow - login screen] -->

After setup:

1. Open the device page for your UPS
2. Set the **UPS Rated Power** (watts) in the Configuration section — this is required for the Load % sensor to work correctly

![Device page with sensors](https://raw.githubusercontent.com/Csontikka/ha-cyberpower-cloud/master/images/device_page.png)

## Configuration

### Options

Click **Configure** on the integration card to adjust:

| Option | Range | Default | Description |
|--------|-------|---------|-------------|
| Update interval | 60–3600 s | 300 s | How often to poll the CyberPower Cloud API |

> **How often does the UPS upload to the cloud?**
> The CyberPower cloud card (RWCCARD100/200) pushes data to the PowerPanel Cloud approximately **every 60 seconds** during normal operation. Polling the API more often than that is wasteful — you will just get the same values back. For most users, the default **300 s** is a good balance between freshness and API load. If you need near-real-time data (e.g. during a power event), the `cyberpower_cloud_power_outage_started` / `_ended` events fire on state changes regardless of the poll interval. You can verify actual data freshness via the **Last Update** sensor — it shows the timestamp reported by the API for each device.

### Per-device settings

Each UPS device has its own configurable **UPS Rated Power** (watts) on the device page. This value is used to calculate the Load % sensor.

Common rated power values:

| Model | VA | Watts |
|-------|-----|-------|
| OLS1000EA | 1000 | 900 |
| OLS1500EA | 1500 | 1350 |
| OLS2000EA | 2000 | 1800 |
| OLS3000EA | 3000 | 2700 |

> Check your UPS model's datasheet for the exact watt rating. VA and watts are **not** the same.

## Energy Dashboard

The **Power Consumption** sensor can be added to the Home Assistant Energy Dashboard:

1. Go to **Settings** > **Dashboards** > **Energy**
2. Under **Individual devices**, click **Add device**
3. Select your UPS Power Consumption sensor

<!-- [SCREENSHOT: Energy Dashboard with UPS power consumption] -->

## Automation examples

### Power outage notification

```yaml
automation:
  - alias: "Power outage alert"
    trigger:
      - platform: event
        event_type: cyberpower_cloud_power_outage_started
    action:
      - service: notify.mobile_app
        data:
          title: "Power Outage!"
          message: "UPS {{ trigger.event.data.device_name }} is running on battery"
```

### Power restored notification

```yaml
automation:
  - alias: "Power restored"
    trigger:
      - platform: event
        event_type: cyberpower_cloud_power_outage_ended
    action:
      - service: notify.mobile_app
        data:
          title: "Power Restored"
          message: "UPS {{ trigger.event.data.device_name }} is back on mains power"
```

### Low battery warning

```yaml
automation:
  - alias: "UPS low battery warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_ups_battery
        below: 30
    action:
      - service: notify.mobile_app
        data:
          title: "UPS Battery Low"
          message: "Battery at {{ states('sensor.my_ups_battery') }}% — {{ states('sensor.my_ups_battery_runtime') }} minutes remaining"
```

## Error handling

| Situation | Behavior |
|-----------|----------|
| No internet at startup | Integration retries automatically (ConfigEntryNotReady) |
| Invalid credentials | Stops polling, creates a repair issue, prompts for re-authentication |
| API errors (3 consecutive) | Stops polling, creates a repair issue |
| Token expiry | Automatic re-login and retry |

## Troubleshooting

### Diagnostics Export

Download the integration diagnostics file for bug reports — it includes the integration state and configuration (with sensitive data redacted).

1. Go to **Settings → Devices & Services**
2. Find **CyberPower PowerPanel Cloud** → click the integration
3. Click the three-dot menu → **Download diagnostics**
4. Attach the `.json` file to your GitHub issue

### Debug Logs

To see detailed logs in the HA log viewer, add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.cyberpower_cloud: debug
```

This enables per-request API traces, coordinator update summaries, login/token refresh events, and event-firing logs. After restarting Home Assistant, check **Settings → System → Logs**.

### Removal

1. Go to **Settings → Devices & Services → CyberPower PowerPanel Cloud**
2. Click the three-dot menu → **Delete**
3. Optionally remove `custom_components/cyberpower_cloud/` and restart Home Assistant

## How it works

This integration uses the internal CyberPower PowerPanel Cloud API (`iotapi.cyberpower.com`) — the same API used by the official PowerPanel Cloud mobile app. There is no official public API; this integration was built through reverse engineering.

Data is polled at a configurable interval (default: 5 minutes). Two API endpoints are used per update cycle:

- `/device/read/status` — battery status, load (watts), BHI
- `/status/log` — voltage, frequency, temperature readings

## Supported languages

Available in 30 languages:

<p>
<img src="https://flagcdn.com/20x15/gb.png" width="20" title="English" alt="English"> <img src="https://flagcdn.com/20x15/bg.png" width="20" title="Bulgarian" alt="Bulgarian"> <img src="https://flagcdn.com/20x15/es.png" width="20" title="Catalan" alt="Catalan"> <img src="https://flagcdn.com/20x15/cz.png" width="20" title="Czech" alt="Czech"> <img src="https://flagcdn.com/20x15/dk.png" width="20" title="Danish" alt="Danish"> <img src="https://flagcdn.com/20x15/de.png" width="20" title="German" alt="German"> <img src="https://flagcdn.com/20x15/gr.png" width="20" title="Greek" alt="Greek"> <img src="https://flagcdn.com/20x15/es.png" width="20" title="Spanish" alt="Spanish"> <img src="https://flagcdn.com/20x15/ee.png" width="20" title="Estonian" alt="Estonian"> <img src="https://flagcdn.com/20x15/fi.png" width="20" title="Finnish" alt="Finnish"> <img src="https://flagcdn.com/20x15/fr.png" width="20" title="French" alt="French"> <img src="https://flagcdn.com/20x15/hr.png" width="20" title="Croatian" alt="Croatian"> <img src="https://flagcdn.com/20x15/hu.png" width="20" title="Hungarian" alt="Hungarian"> <img src="https://flagcdn.com/20x15/it.png" width="20" title="Italian" alt="Italian"> <img src="https://flagcdn.com/20x15/jp.png" width="20" title="Japanese" alt="Japanese"> <img src="https://flagcdn.com/20x15/kr.png" width="20" title="Korean" alt="Korean"> <img src="https://flagcdn.com/20x15/lt.png" width="20" title="Lithuanian" alt="Lithuanian"> <img src="https://flagcdn.com/20x15/no.png" width="20" title="Norwegian" alt="Norwegian"> <img src="https://flagcdn.com/20x15/nl.png" width="20" title="Dutch" alt="Dutch"> <img src="https://flagcdn.com/20x15/pl.png" width="20" title="Polish" alt="Polish"> <img src="https://flagcdn.com/20x15/pt.png" width="20" title="Portuguese" alt="Portuguese"> <img src="https://flagcdn.com/20x15/br.png" width="20" title="Portuguese (BR)" alt="Portuguese (BR)"> <img src="https://flagcdn.com/20x15/ro.png" width="20" title="Romanian" alt="Romanian"> <img src="https://flagcdn.com/20x15/ru.png" width="20" title="Russian" alt="Russian"> <img src="https://flagcdn.com/20x15/sk.png" width="20" title="Slovak" alt="Slovak"> <img src="https://flagcdn.com/20x15/se.png" width="20" title="Swedish" alt="Swedish"> <img src="https://flagcdn.com/20x15/tr.png" width="20" title="Turkish" alt="Turkish"> <img src="https://flagcdn.com/20x15/ua.png" width="20" title="Ukrainian" alt="Ukrainian"> <img src="https://flagcdn.com/20x15/vn.png" width="20" title="Vietnamese" alt="Vietnamese"> <img src="https://flagcdn.com/20x15/cn.png" width="20" title="Chinese" alt="Chinese">
</p>

> Translations were machine-generated — if you spot any issues, please [open an issue](https://github.com/Csontikka/ha-cyberpower-cloud/issues) or submit a PR!

## Known limitations

- **Cloud-only** — requires an active internet connection; does not work with local/USB-connected UPS
- **Polling-based** — not real-time; the minimum interval is 60 seconds
- **No UPS control** — read-only monitoring; cannot shutdown, test, or configure the UPS
- **Temperature sensors** — only available with compatible environmental sensors (e.g., EMHD1)

## Support

Found a bug or have an idea? [Open an issue](https://github.com/Csontikka/ha-cyberpower-cloud/issues) — feedback and feature requests are welcome!

If you find this integration useful, consider [buying me a coffee](https://www.buymeacoffee.com/csontikka) ☕.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-donate-yellow?logo=buy-me-a-coffee&logoColor=white)](https://www.buymeacoffee.com/csontikka)

## License

[MIT](https://github.com/Csontikka/ha-cyberpower-cloud/blob/master/LICENSE)
