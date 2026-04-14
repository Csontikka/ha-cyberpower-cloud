# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-04-14

### Added
- Post-login **Rated Power reminder** step in the config flow — surfaces a clear reminder to set the per-device UPS Rated Power (watts), without which the Load % sensor cannot be calculated. Shown both on initial setup and on reconfigure.
- Translations for **29 additional languages** (30 total with English): bg, ca, cs, da, de, el, es, et, fi, fr, hr, hu, it, ja, ko, lt, nb, nl, pl, pt, pt-BR, ro, ru, sk, sv, tr, uk, vi, zh-Hans.
- README: **Troubleshooting** section with Diagnostics Export, Debug Logs, and Removal subsections.
- README: **Supported Languages** section listing all 30 locales.
- README: note on UPS → PowerPanel Cloud upload cadence (~60 s) to help users choose a sensible polling interval.
- README: 2FA-must-be-disabled prerequisite (the integration uses the mobile login flow which does not support 2FA).

### Changed
- README rendering in HACS: switched image and license links to absolute GitHub URLs so banners and badges render correctly inside the HACS viewer.
- Single consolidated **Support** section at the bottom of the README (previously duplicated at top and bottom).

### Fixed
- License badge no longer breaks in HACS when viewed outside GitHub.

## [0.1.0] - 2026-04-14

Initial public release.

### Added
- Config flow for PowerPanel Cloud account login (email + password)
- Automatic discovery of all UPS devices on the account (multi-UPS support)
- 12 sensor entities per device:
  - Battery (%), Battery Runtime (min), Battery Health/BHI (%)
  - Power Consumption (W, Energy Dashboard compatible), Load (%)
  - Input/Output Voltage (V), Input/Output Frequency (Hz)
  - UPS Temperature, Environment Temperature, Environment Humidity
  - Status, Last Update
- Binary sensor: On Battery (power outage indicator)
- Number entity: per-device UPS Rated Power (watts) for Load % calculation
- Home Assistant events on power state changes:
  - `cyberpower_cloud_power_outage_started`
  - `cyberpower_cloud_power_outage_ended`
- Options flow: configurable scan interval (60–3600 s, default 300 s)
- Reconfigure and reauth flows
- Diagnostics export with sensitive data redaction
- Error resilience: stops polling after 3 consecutive failures, creates repair issues
- Automatic token refresh on expiry
- HACS-compatible repository structure

[0.1.1]: https://github.com/Csontikka/ha-cyberpower-cloud/releases/tag/v0.1.1
[0.1.0]: https://github.com/Csontikka/ha-cyberpower-cloud/releases/tag/v0.1.0
