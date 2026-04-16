"""Tests for CyberPower Cloud integration setup."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from custom_components.cyberpower_cloud import (
    _async_update_options,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.cyberpower_cloud.api import AuthError


def _make_entry(devices=None, options=None):
    entry = MagicMock()
    entry.data = {"email": "test@example.com", "password": "pw"}
    entry.options = options or {}
    entry.entry_id = "abc123"
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock(return_value=MagicMock())
    return entry


def _patch_api(devices, login_side_effect=None):
    """Return a patch context manager providing a mock CyberPowerCloudAPI."""
    api = MagicMock()
    if login_side_effect is not None:
        api.login = AsyncMock(side_effect=login_side_effect)
    else:
        api.login = AsyncMock(return_value={"Flag": True})
    api.devices = devices

    return patch(
        "custom_components.cyberpower_cloud.CyberPowerCloudAPI",
        return_value=api,
    )


def _patch_coordinator():
    """Patch the CyberPowerCoordinator so first-refresh is a no-op."""
    coord = MagicMock()
    coord.async_config_entry_first_refresh = AsyncMock()
    return patch(
        "custom_components.cyberpower_cloud.CyberPowerCoordinator",
        return_value=coord,
    )


def test_setup_entry_happy_path():
    """Successful setup stores coordinators in runtime_data and forwards platforms."""

    async def _run():
        entry = _make_entry()
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        with (
            _patch_api(
                devices=[
                    {
                        "DeviceSN": "SN1",
                        "Id": 1,
                        "DeviceName": "UPS A",
                        "Model": "OLS2000",
                        "RP": 1500,
                    }
                ]
            ),
            _patch_coordinator(),
            patch(
                "custom_components.cyberpower_cloud.async_get_clientsession",
                return_value=MagicMock(),
            ),
        ):
            result = await async_setup_entry(hass, entry)
        return result, entry, hass

    result, entry, hass = asyncio.run(_run())
    assert result is True
    assert isinstance(entry.runtime_data, list)
    assert len(entry.runtime_data) == 1
    hass.config_entries.async_forward_entry_setups.assert_awaited_once()
    entry.async_on_unload.assert_called_once()


def test_setup_entry_auth_error_raises_config_entry_auth_failed():
    """AuthError during login is translated to ConfigEntryAuthFailed."""

    async def _run():
        entry = _make_entry()
        hass = MagicMock()
        with (
            _patch_api(devices=[], login_side_effect=AuthError("bad pass")),
            patch(
                "custom_components.cyberpower_cloud.async_get_clientsession",
                return_value=MagicMock(),
            ),
        ):
            with pytest.raises(ConfigEntryAuthFailed):
                await async_setup_entry(hass, entry)

    asyncio.run(_run())


def test_setup_entry_client_error_raises_config_entry_not_ready():
    """aiohttp.ClientError during login is translated to ConfigEntryNotReady."""

    async def _run():
        entry = _make_entry()
        hass = MagicMock()
        with (
            _patch_api(devices=[], login_side_effect=aiohttp.ClientError("boom")),
            patch(
                "custom_components.cyberpower_cloud.async_get_clientsession",
                return_value=MagicMock(),
            ),
        ):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, entry)

    asyncio.run(_run())


def test_setup_entry_timeout_error_raises_config_entry_not_ready():
    """TimeoutError during login is translated to ConfigEntryNotReady."""

    async def _run():
        entry = _make_entry()
        hass = MagicMock()
        with (
            _patch_api(devices=[], login_side_effect=TimeoutError()),
            patch(
                "custom_components.cyberpower_cloud.async_get_clientsession",
                return_value=MagicMock(),
            ),
        ):
            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(hass, entry)

    asyncio.run(_run())


def test_setup_entry_uses_rva_when_rp_missing():
    """RVA is used when RP field is missing."""

    async def _run():
        entry = _make_entry()
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        with (
            _patch_api(
                devices=[
                    {
                        "DeviceSN": "SN1",
                        "Id": 1,
                        "DeviceName": "UPS A",
                        "Model": "OLS2000",
                        "RVA": 800,
                    }
                ]
            ) as _api,
            patch(
                "custom_components.cyberpower_cloud.CyberPowerCoordinator"
            ) as coord_cls,
            patch(
                "custom_components.cyberpower_cloud.async_get_clientsession",
                return_value=MagicMock(),
            ),
        ):
            coord_cls.return_value.async_config_entry_first_refresh = AsyncMock()
            await async_setup_entry(hass, entry)
            return coord_cls

    coord_cls = asyncio.run(_run())
    kwargs = coord_cls.call_args.kwargs
    assert kwargs["ups_rated_power"] == 800


def test_setup_entry_falls_back_to_default_rated_power():
    """Neither RP nor RVA present means default rated power."""

    async def _run():
        entry = _make_entry()
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        with (
            _patch_api(devices=[{"DeviceSN": "SN1", "Id": 1, "Model": "OLS2000"}]),
            patch(
                "custom_components.cyberpower_cloud.CyberPowerCoordinator"
            ) as coord_cls,
            patch(
                "custom_components.cyberpower_cloud.async_get_clientsession",
                return_value=MagicMock(),
            ),
        ):
            coord_cls.return_value.async_config_entry_first_refresh = AsyncMock()
            await async_setup_entry(hass, entry)
            return coord_cls

    coord_cls = asyncio.run(_run())
    kwargs = coord_cls.call_args.kwargs
    assert kwargs["ups_rated_power"] == 0  # DEFAULT_UPS_RATED_POWER


def test_unload_entry_forwards_to_platforms():
    """async_unload_entry delegates to config_entries.async_unload_platforms."""

    async def _run():
        entry = _make_entry()
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        return await async_unload_entry(hass, entry), hass

    result, hass = asyncio.run(_run())
    assert result is True
    hass.config_entries.async_unload_platforms.assert_awaited_once()


def test_update_options_reloads_entry():
    """_async_update_options triggers a reload of the config entry."""

    async def _run():
        entry = _make_entry()
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_reload = AsyncMock()
        await _async_update_options(hass, entry)
        return hass, entry

    hass, entry = asyncio.run(_run())
    hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)


def test_setup_entry_honors_custom_scan_interval():
    """Options scan_interval flows into coordinator constructor."""

    async def _run():
        entry = _make_entry(options={"scan_interval": 900})
        hass = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()

        with (
            _patch_api(devices=[{"DeviceSN": "SN1", "Id": 1, "Model": "OLS2000"}]),
            patch(
                "custom_components.cyberpower_cloud.CyberPowerCoordinator"
            ) as coord_cls,
            patch(
                "custom_components.cyberpower_cloud.async_get_clientsession",
                return_value=MagicMock(),
            ),
        ):
            coord_cls.return_value.async_config_entry_first_refresh = AsyncMock()
            await async_setup_entry(hass, entry)
            return coord_cls

    coord_cls = asyncio.run(_run())
    kwargs = coord_cls.call_args.kwargs
    assert kwargs["scan_interval"] == 900
