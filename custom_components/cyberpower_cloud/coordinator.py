"""DataUpdateCoordinator for CyberPower Cloud."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AuthError, CyberPowerCloudAPI
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_POWER_OUTAGE_ENDED,
    EVENT_POWER_OUTAGE_STARTED,
)

_LOGGER = logging.getLogger(__name__)

MAX_CONSECUTIVE_ERRORS = 3


class CyberPowerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls CyberPower Cloud API every 5 minutes."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: CyberPowerCloudAPI,
        device_sn: str,
        device_dcode: int,
        device_name: str,
        device_model: str,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        ups_rated_power: int = 2000,
        sw_version: str | None = None,
        fw_version: str | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{device_sn}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.device_sn = device_sn
        self.device_dcode = device_dcode
        self.device_name = device_name
        self.device_model = device_model
        self.ups_rated_power = ups_rated_power
        self.sw_version = sw_version
        self.fw_version = fw_version
        self._consecutive_errors = 0
        self._previous_on_battery: bool | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status = await self.api.get_device_status(self.device_sn)
            log_entry = await self.api.get_status_log(self.device_dcode)
            merged = {**log_entry, **status}
            if self._consecutive_errors > 0:
                _LOGGER.info(
                    "CyberPower %s recovered after %d error(s)",
                    self.device_sn, self._consecutive_errors,
                )
            self._consecutive_errors = 0

            # Detect power outage state changes and fire events
            bat_sta = merged.get("BatSta")
            if bat_sta is not None:
                on_battery = bat_sta != 0
                if self._previous_on_battery is not None and on_battery != self._previous_on_battery:
                    event_data = {
                        "device_sn": self.device_sn,
                        "device_name": self.device_name,
                        "device_model": self.device_model,
                    }
                    if on_battery:
                        _LOGGER.warning(
                            "CyberPower %s: power outage detected!", self.device_sn,
                        )
                        self.hass.bus.async_fire(EVENT_POWER_OUTAGE_STARTED, event_data)
                    else:
                        _LOGGER.info(
                            "CyberPower %s: power restored", self.device_sn,
                        )
                        self.hass.bus.async_fire(EVENT_POWER_OUTAGE_ENDED, event_data)
                self._previous_on_battery = on_battery

            _LOGGER.debug(
                "CyberPower %s update OK: battery=%s%%, load=%s%%, status=%s",
                self.device_sn,
                merged.get("BatCap"),
                merged.get("Load", merged.get("DevLoad")),
                merged.get("device_status"),
            )
            return merged
        except AuthError as err:
            _LOGGER.error("CyberPower %s auth failed, stopping polling: %s", self.device_sn, err)
            self.update_interval = None  # stop polling
            async_create_issue(
                self.hass,
                DOMAIN,
                f"auth_failed_{self.device_sn}",
                is_fixable=False,
                severity=IssueSeverity.ERROR,
                translation_key="auth_failed",
                translation_placeholders={"device": self.device_name},
            )
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiError as err:
            self._consecutive_errors += 1
            _LOGGER.warning(
                "CyberPower %s API error (%d/%d): %s",
                self.device_sn, self._consecutive_errors, MAX_CONSECUTIVE_ERRORS, err,
            )
            if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                _LOGGER.error(
                    "CyberPower API failed %d times in a row, stopping polling: %s",
                    self._consecutive_errors, err,
                )
                self.update_interval = None  # stop polling
                async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"api_error_{self.device_sn}",
                    is_fixable=False,
                    severity=IssueSeverity.WARNING,
                    translation_key="api_error",
                    translation_placeholders={"device": self.device_name},
                )
            raise UpdateFailed(str(err)) from err
