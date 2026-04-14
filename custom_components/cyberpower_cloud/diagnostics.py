"""Diagnostics support for CyberPower Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import CyberPowerCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinators: list[CyberPowerCoordinator] = hass.data[DOMAIN][entry.entry_id]

    devices = []
    for coordinator in coordinators:
        device_data = dict(coordinator.data) if coordinator.data else {}
        # Remove nothing sensitive in coordinator data, but redact account info
        devices.append(
            {
                "device_name": coordinator.device_name,
                "device_model": coordinator.device_model,
                "device_sn": coordinator.device_sn[:6] + "***",
                "update_interval": coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None,
                "last_data": device_data,
            }
        )

    return {
        "account": "**redacted**",
        "device_count": len(coordinators),
        "devices": devices,
    }
