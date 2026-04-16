"""CyberPower Cloud integration for Home Assistant."""

from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuthError, CyberPowerCloudAPI
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UPS_RATED_POWER,
)
from .coordinator import CyberPowerCoordinator

_LOGGER = logging.getLogger(__name__)


PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SENSOR]

type CyberPowerConfigEntry = ConfigEntry[list[CyberPowerCoordinator]]


async def async_setup_entry(hass: HomeAssistant, entry: CyberPowerConfigEntry) -> bool:
    """Set up CyberPower Cloud from a config entry."""
    session = async_get_clientsession(hass)
    api = CyberPowerCloudAPI(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])

    _LOGGER.debug("Setting up CyberPower Cloud for %s", entry.data[CONF_EMAIL])

    try:
        await api.login()
    except AuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except (aiohttp.ClientError, TimeoutError) as err:
        raise ConfigEntryNotReady(f"Cannot connect to CyberPower Cloud: {err}") from err

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    _LOGGER.debug(
        "CyberPower Cloud: %d device(s), scan interval %ds",
        len(api.devices),
        scan_interval,
    )

    coordinators: list[CyberPowerCoordinator] = []
    for device in api.devices:
        # Use API-reported rated power if available, otherwise default
        api_rated_power = device.get("RP") or device.get("RVA")
        effective_rated_power = (
            int(api_rated_power) if api_rated_power else DEFAULT_UPS_RATED_POWER
        )

        coordinator = CyberPowerCoordinator(
            hass,
            api,
            device_sn=device["DeviceSN"],
            device_dcode=device["Id"],
            device_name=device.get("DeviceName", "CyberPower UPS"),
            device_model=device.get("Model", "Unknown"),
            scan_interval=scan_interval,
            ups_rated_power=effective_rated_power,
            sw_version=device.get("FirmwareVersion"),
            fw_version=device.get("FirmwareVersion"),
        )
        await coordinator.async_config_entry_first_refresh()
        coordinators.append(coordinator)

    entry.runtime_data = coordinators
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_options(
    hass: HomeAssistant, entry: CyberPowerConfigEntry
) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: CyberPowerConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
