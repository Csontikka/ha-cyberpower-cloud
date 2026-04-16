"""Tests for CyberPower Cloud coordinator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.cyberpower_cloud.api import ApiError, AuthError
from custom_components.cyberpower_cloud.const import (
    EVENT_POWER_OUTAGE_ENDED,
    EVENT_POWER_OUTAGE_STARTED,
)
from custom_components.cyberpower_cloud.coordinator import (
    MAX_CONSECUTIVE_ERRORS,
    CyberPowerCoordinator,
)


def _make_coordinator(api):
    """Instantiate a coordinator without the real DataUpdateCoordinator init."""
    with patch.object(DataUpdateCoordinator, "__init__", return_value=None):
        coord = CyberPowerCoordinator(
            hass=MagicMock(),
            api=api,
            device_sn="SN001",
            device_dcode=123,
            device_name="Test UPS",
            device_model="OLS2000",
            scan_interval=300,
            ups_rated_power=2000,
            sw_version="1.0",
            fw_version="2.0",
        )
    coord.hass = MagicMock()
    coord.hass.bus = MagicMock()
    coord.hass.bus.async_fire = MagicMock()
    coord.update_interval = MagicMock()
    return coord


def test_update_merges_status_and_log():
    """Successful update merges status + log entries; status wins on collision."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(
            return_value={"BatCap": 100, "BatSta": 0, "DevLoad": 150}
        )
        api.get_status_log = AsyncMock(
            return_value={"InVolt": 230.0, "OutVolt": 230.0, "DevLoad": 999}
        )

        coord = _make_coordinator(api)
        data = await coord._async_update_data()
        return data

    data = asyncio.run(_run())
    assert data["BatCap"] == 100
    assert data["InVolt"] == 230.0
    # status value should override log value on key collision
    assert data["DevLoad"] == 150


def test_update_resets_consecutive_errors_on_success():
    """Successful update clears consecutive error count."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(return_value={"BatSta": 0})
        api.get_status_log = AsyncMock(return_value={})

        coord = _make_coordinator(api)
        coord._consecutive_errors = 2
        await coord._async_update_data()
        return coord

    coord = asyncio.run(_run())
    assert coord._consecutive_errors == 0


def test_power_outage_started_event_fires():
    """Transition from grid to battery fires outage_started event."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(return_value={"BatSta": 1})
        api.get_status_log = AsyncMock(return_value={})

        coord = _make_coordinator(api)
        coord._previous_on_battery = False  # was on grid
        await coord._async_update_data()
        return coord

    coord = asyncio.run(_run())
    coord.hass.bus.async_fire.assert_called_once()
    args, _ = coord.hass.bus.async_fire.call_args
    assert args[0] == EVENT_POWER_OUTAGE_STARTED
    assert args[1]["device_sn"] == "SN001"
    assert coord._previous_on_battery is True


def test_power_outage_ended_event_fires():
    """Transition from battery to grid fires outage_ended event."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(return_value={"BatSta": 0})
        api.get_status_log = AsyncMock(return_value={})

        coord = _make_coordinator(api)
        coord._previous_on_battery = True  # was on battery
        await coord._async_update_data()
        return coord

    coord = asyncio.run(_run())
    coord.hass.bus.async_fire.assert_called_once()
    args, _ = coord.hass.bus.async_fire.call_args
    assert args[0] == EVENT_POWER_OUTAGE_ENDED


def test_no_event_on_first_update():
    """First update with BatSta only seeds _previous_on_battery, no event."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(return_value={"BatSta": 1})
        api.get_status_log = AsyncMock(return_value={})

        coord = _make_coordinator(api)
        assert coord._previous_on_battery is None
        await coord._async_update_data()
        return coord

    coord = asyncio.run(_run())
    coord.hass.bus.async_fire.assert_not_called()
    assert coord._previous_on_battery is True


def test_no_event_when_state_unchanged():
    """No event fires when BatSta stays the same across updates."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(return_value={"BatSta": 0})
        api.get_status_log = AsyncMock(return_value={})

        coord = _make_coordinator(api)
        coord._previous_on_battery = False
        await coord._async_update_data()
        return coord

    coord = asyncio.run(_run())
    coord.hass.bus.async_fire.assert_not_called()


def test_batsta_missing_skips_event_tracking():
    """If BatSta missing from payload, leave tracking state untouched."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(return_value={"BatCap": 100})
        api.get_status_log = AsyncMock(return_value={})

        coord = _make_coordinator(api)
        coord._previous_on_battery = True
        await coord._async_update_data()
        return coord

    coord = asyncio.run(_run())
    coord.hass.bus.async_fire.assert_not_called()
    # previous state kept
    assert coord._previous_on_battery is True


def test_auth_error_raises_config_entry_auth_failed():
    """AuthError stops polling, creates repair issue, bubbles up as ConfigEntryAuthFailed."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(side_effect=AuthError("bad token"))

        coord = _make_coordinator(api)
        with patch(
            "custom_components.cyberpower_cloud.coordinator.async_create_issue"
        ) as mock_issue:
            with pytest.raises(ConfigEntryAuthFailed):
                await coord._async_update_data()
        return coord, mock_issue

    coord, mock_issue = asyncio.run(_run())
    assert coord.update_interval is None
    mock_issue.assert_called_once()
    # translation_key should be auth_failed
    kwargs = mock_issue.call_args.kwargs
    assert kwargs["translation_key"] == "auth_failed"


def test_api_error_under_threshold_raises_update_failed():
    """Single ApiError increments counter, raises UpdateFailed, keeps polling."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(side_effect=ApiError("boom"))

        coord = _make_coordinator(api)
        with patch(
            "custom_components.cyberpower_cloud.coordinator.async_create_issue"
        ) as mock_issue:
            with pytest.raises(UpdateFailed):
                await coord._async_update_data()
        return coord, mock_issue

    coord, mock_issue = asyncio.run(_run())
    assert coord._consecutive_errors == 1
    mock_issue.assert_not_called()


def test_api_error_three_strike_stops_polling_and_creates_issue():
    """Reaching MAX_CONSECUTIVE_ERRORS stops polling and opens repair issue."""

    async def _run():
        api = MagicMock()
        api.get_device_status = AsyncMock(side_effect=ApiError("boom"))

        coord = _make_coordinator(api)
        coord._consecutive_errors = MAX_CONSECUTIVE_ERRORS - 1
        with patch(
            "custom_components.cyberpower_cloud.coordinator.async_create_issue"
        ) as mock_issue:
            with pytest.raises(UpdateFailed):
                await coord._async_update_data()
        return coord, mock_issue

    coord, mock_issue = asyncio.run(_run())
    assert coord._consecutive_errors == MAX_CONSECUTIVE_ERRORS
    assert coord.update_interval is None
    mock_issue.assert_called_once()
    kwargs = mock_issue.call_args.kwargs
    assert kwargs["translation_key"] == "api_error"
