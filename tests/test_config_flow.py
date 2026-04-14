"""Tests for the CyberPower Cloud config flow."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from custom_components.cyberpower_cloud.api import AuthError
from custom_components.cyberpower_cloud.const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

from .conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_DEVICE, MOCK_EMAIL


def _mock_api(auth_error=False, connect_error=False, no_devices=False):
    """Create a mock API client."""
    api = MagicMock()
    if auth_error:
        api.login = AsyncMock(side_effect=AuthError("Invalid credentials"))
    elif connect_error:
        api.login = AsyncMock(side_effect=aiohttp.ClientError())
    else:
        api.login = AsyncMock(return_value={"Flag": True})

    api.devices = [] if no_devices else [MOCK_DEVICE]
    return api


def _make_flow():
    """Create a config flow instance with mocked hass."""
    from custom_components.cyberpower_cloud.config_flow import CyberPowerCloudConfigFlow

    flow = CyberPowerCloudConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries = MagicMock()
    flow.hass.config_entries.async_entries = MagicMock(return_value=[])
    return flow


def test_config_flow_shows_form_on_empty():
    """Test that the form is shown when no input is provided."""

    async def _run():
        flow = _make_flow()
        with patch.object(
            flow,
            "async_show_form",
            return_value={"type": "form", "step_id": "user", "errors": {}},
        ):
            return await flow.async_step_user(None)

    result = asyncio.run(_run())
    assert result["type"] == "form"
    assert result["step_id"] == "user"


def test_config_flow_success_shows_reminder():
    """Successful login forwards to the rated power reminder step."""

    async def _run():
        flow = _make_flow()
        api = _mock_api()

        with patch(
            "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
            return_value=api,
        ), patch(
            "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ), patch.object(
            flow, "async_set_unique_id", new_callable=AsyncMock, return_value=None
        ), patch.object(
            flow, "_abort_if_unique_id_configured"
        ), patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kwargs: {"type": "form", "step_id": kwargs.get("step_id")},
        ):
            return await flow.async_step_user(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["type"] == "form"
    assert result["step_id"] == "rated_power_reminder"


def test_config_flow_reminder_creates_entry():
    """Submitting the reminder step creates the config entry."""

    async def _run():
        flow = _make_flow()
        flow._pending_user_input = MOCK_CONFIG_ENTRY_DATA
        flow._pending_device_names = "Test UPS"

        with patch.object(
            flow,
            "async_create_entry",
            return_value={"type": "create_entry", "title": "CyberPower (Test UPS)"},
        ):
            return await flow.async_step_rated_power_reminder({})

    result = asyncio.run(_run())
    assert result["type"] == "create_entry"
    assert result["title"] == "CyberPower (Test UPS)"


def test_config_flow_invalid_auth():
    """Test config flow with invalid credentials."""

    async def _run():
        flow = _make_flow()
        api = _mock_api(auth_error=True)

        with patch(
            "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
            return_value=api,
        ), patch(
            "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ), patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kwargs: {"type": "form", "errors": kwargs.get("errors", {})},
        ):
            return await flow.async_step_user(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["type"] == "form"
    assert result["errors"] == {"base": "invalid_auth"}


def test_config_flow_cannot_connect():
    """Test config flow with connection error."""

    async def _run():
        flow = _make_flow()
        api = _mock_api(connect_error=True)

        with patch(
            "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
            return_value=api,
        ), patch(
            "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ), patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kwargs: {"type": "form", "errors": kwargs.get("errors", {})},
        ):
            return await flow.async_step_user(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


def test_config_flow_no_devices():
    """Test config flow when no devices found."""

    async def _run():
        flow = _make_flow()
        api = _mock_api(no_devices=True)

        with patch(
            "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
            return_value=api,
        ), patch(
            "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ), patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kwargs: {"type": "form", "errors": kwargs.get("errors", {})},
        ):
            return await flow.async_step_user(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["type"] == "form"
    assert result["errors"] == {"base": "no_devices"}
