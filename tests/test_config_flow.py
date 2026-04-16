"""Tests for the CyberPower Cloud config flow."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from custom_components.cyberpower_cloud.api import AuthError

from .conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_DEVICE


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

        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow, "async_set_unique_id", new_callable=AsyncMock, return_value=None
            ),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kwargs: {
                    "type": "form",
                    "step_id": kwargs.get("step_id"),
                },
            ),
        ):
            return await flow.async_step_user(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["type"] == "form"
    assert result["step_id"] == "rated_power_reminder"


def test_config_flow_reminder_creates_entry():
    """Reminder step creates the entry with exact title + user credentials.

    Verifies the full entry payload — title uses device names, data carries the
    email/password unchanged — not just that *some* create_entry call happened.
    """

    async def _run():
        flow = _make_flow()
        flow._pending_user_input = MOCK_CONFIG_ENTRY_DATA
        flow._pending_device_names = "Test UPS"

        with patch.object(
            flow,
            "async_create_entry",
            side_effect=lambda **kw: {
                "type": "create_entry",
                "title": kw["title"],
                "data": kw["data"],
            },
        ) as mock_create:
            result = await flow.async_step_rated_power_reminder({})
        return result, mock_create

    result, mock_create = asyncio.run(_run())
    assert result["type"] == "create_entry"
    assert result["title"] == "CyberPower (Test UPS)"
    mock_create.assert_called_once_with(
        title="CyberPower (Test UPS)",
        data=MOCK_CONFIG_ENTRY_DATA,
    )


def test_config_flow_invalid_auth():
    """Test config flow with invalid credentials."""

    async def _run():
        flow = _make_flow()
        api = _mock_api(auth_error=True)

        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kwargs: {
                    "type": "form",
                    "errors": kwargs.get("errors", {}),
                },
            ),
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

        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kwargs: {
                    "type": "form",
                    "errors": kwargs.get("errors", {}),
                },
            ),
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

        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kwargs: {
                    "type": "form",
                    "errors": kwargs.get("errors", {}),
                },
            ),
        ):
            return await flow.async_step_user(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["type"] == "form"
    assert result["errors"] == {"base": "no_devices"}


def test_config_flow_timeout_error():
    """TimeoutError during login yields cannot_connect."""

    async def _run():
        flow = _make_flow()
        api = MagicMock()
        api.login = AsyncMock(side_effect=TimeoutError())

        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kwargs: {
                    "type": "form",
                    "errors": kwargs.get("errors", {}),
                },
            ),
        ):
            return await flow.async_step_user(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["errors"] == {"base": "cannot_connect"}


def test_config_flow_device_name_fallback_to_model():
    """Device without DeviceName uses Model in the title."""

    async def _run():
        flow = _make_flow()
        api = MagicMock()
        api.login = AsyncMock(return_value={"Flag": True})
        api.devices = [{"Model": "CP1350", "DeviceSN": "SN2"}]

        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow, "async_set_unique_id", new_callable=AsyncMock, return_value=None
            ),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kwargs: {
                    "type": "form",
                    "step_id": kwargs.get("step_id"),
                },
            ),
        ):
            await flow.async_step_user(MOCK_CONFIG_ENTRY_DATA)
            return flow._pending_device_names

    name = asyncio.run(_run())
    assert name == "CP1350"


# ---------------------------------------------------------------------------
# Reauth flow
# ---------------------------------------------------------------------------


def _reauth_flow(entry_data=None):
    from custom_components.cyberpower_cloud.config_flow import CyberPowerCloudConfigFlow

    flow = CyberPowerCloudConfigFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries = MagicMock()
    flow.hass.config_entries.async_reload = AsyncMock()

    entry = MagicMock()
    entry.data = entry_data or dict(MOCK_CONFIG_ENTRY_DATA)
    entry.entry_id = "entry1"
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=entry)
    flow.context = {"entry_id": "entry1"}
    return flow, entry


def test_reauth_redirects_to_confirm_form():
    """async_step_reauth shows the confirmation form."""

    async def _run():
        flow, _ = _reauth_flow()
        with patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kw: {"type": "form", "step_id": kw["step_id"]},
        ):
            return await flow.async_step_reauth(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["step_id"] == "reauth_confirm"


def test_reauth_confirm_success_updates_entry_and_aborts():
    """Successful reauth writes the NEW password into entry.data, preserves email, aborts.

    Verifies the update_entry call carries the new password (not the old one)
    and that async_reload is kicked off so HA re-runs setup with fresh creds.
    """

    async def _run():
        flow, entry = _reauth_flow()
        flow.hass.config_entries.async_update_entry = MagicMock()

        api = _mock_api()
        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_abort",
                side_effect=lambda **kw: {"type": "abort", "reason": kw["reason"]},
            ),
        ):
            result = await flow.async_step_reauth_confirm({"password": "newpw"})
        return result, flow, entry

    result, flow, entry = asyncio.run(_run())
    assert result["reason"] == "reauth_successful"

    # Update was called once, carried the new password, preserved the email.
    flow.hass.config_entries.async_update_entry.assert_called_once()
    call_entry, call_data = (
        flow.hass.config_entries.async_update_entry.call_args.args[0],
        flow.hass.config_entries.async_update_entry.call_args.kwargs["data"],
    )
    assert call_entry is entry
    assert call_data["password"] == "newpw"
    assert call_data["email"] == MOCK_CONFIG_ENTRY_DATA["email"]
    # Reload triggered so HA picks up the new credentials immediately.
    flow.hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)


def test_reauth_confirm_invalid_auth_shows_form():
    """AuthError during reauth shows the form with invalid_auth error."""

    async def _run():
        flow, _ = _reauth_flow()
        api = _mock_api(auth_error=True)
        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kw: {
                    "type": "form",
                    "errors": kw.get("errors", {}),
                },
            ),
        ):
            return await flow.async_step_reauth_confirm({"password": "bad"})

    result = asyncio.run(_run())
    assert result["errors"] == {"base": "invalid_auth"}


def test_reauth_confirm_connect_error_shows_form():
    """ClientError during reauth shows the form with cannot_connect."""

    async def _run():
        flow, _ = _reauth_flow()
        api = _mock_api(connect_error=True)
        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kw: {
                    "type": "form",
                    "errors": kw.get("errors", {}),
                },
            ),
        ):
            return await flow.async_step_reauth_confirm({"password": "pw"})

    result = asyncio.run(_run())
    assert result["errors"] == {"base": "cannot_connect"}


def test_reauth_confirm_shows_empty_form_without_input():
    """Calling reauth_confirm with no input returns the password form."""

    async def _run():
        flow, _ = _reauth_flow()
        with patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kw: {"type": "form", "step_id": kw["step_id"]},
        ):
            return await flow.async_step_reauth_confirm(None)

    result = asyncio.run(_run())
    assert result["step_id"] == "reauth_confirm"


# ---------------------------------------------------------------------------
# Reconfigure flow
# ---------------------------------------------------------------------------


def test_reconfigure_success_shows_reminder():
    """Successful reconfigure goes to the reconfigure_reminder step."""

    async def _run():
        flow, _ = _reauth_flow()
        api = _mock_api()
        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kw: {"type": "form", "step_id": kw["step_id"]},
            ),
        ):
            return await flow.async_step_reconfigure(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["step_id"] == "reconfigure_reminder"


def test_reconfigure_invalid_auth():
    async def _run():
        flow, _ = _reauth_flow()
        api = _mock_api(auth_error=True)
        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kw: {
                    "type": "form",
                    "errors": kw.get("errors", {}),
                },
            ),
        ):
            return await flow.async_step_reconfigure(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["errors"] == {"base": "invalid_auth"}


def test_reconfigure_cannot_connect():
    async def _run():
        flow, _ = _reauth_flow()
        api = _mock_api(connect_error=True)
        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kw: {
                    "type": "form",
                    "errors": kw.get("errors", {}),
                },
            ),
        ):
            return await flow.async_step_reconfigure(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["errors"] == {"base": "cannot_connect"}


def test_reconfigure_no_devices():
    async def _run():
        flow, _ = _reauth_flow()
        api = _mock_api(no_devices=True)
        with (
            patch(
                "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
                return_value=api,
            ),
            patch(
                "custom_components.cyberpower_cloud.config_flow.async_get_clientsession",
                return_value=MagicMock(),
            ),
            patch.object(
                flow,
                "async_show_form",
                side_effect=lambda **kw: {
                    "type": "form",
                    "errors": kw.get("errors", {}),
                },
            ),
        ):
            return await flow.async_step_reconfigure(MOCK_CONFIG_ENTRY_DATA)

    result = asyncio.run(_run())
    assert result["errors"] == {"base": "no_devices"}


def test_reconfigure_shows_form_without_input():
    async def _run():
        flow, _ = _reauth_flow()
        with patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kw: {"type": "form", "step_id": kw["step_id"]},
        ):
            return await flow.async_step_reconfigure(None)

    result = asyncio.run(_run())
    assert result["step_id"] == "reconfigure"


def test_reconfigure_reminder_submission_updates_entry():
    """Reconfigure-reminder submission writes the new user input into entry.data and reloads."""

    async def _run():
        flow, entry = _reauth_flow()
        flow._pending_user_input = MOCK_CONFIG_ENTRY_DATA
        flow._pending_device_names = "UPS A"
        flow.hass.config_entries.async_update_entry = MagicMock()
        with patch.object(
            flow,
            "async_abort",
            side_effect=lambda **kw: {"type": "abort", "reason": kw["reason"]},
        ):
            result = await flow.async_step_reconfigure_reminder({})
        return result, flow, entry

    result, flow, entry = asyncio.run(_run())
    assert result["reason"] == "reconfigure_successful"
    flow.hass.config_entries.async_update_entry.assert_called_once_with(
        entry, data=MOCK_CONFIG_ENTRY_DATA
    )
    flow.hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)


def test_reconfigure_reminder_shows_form_without_input():
    async def _run():
        flow, _ = _reauth_flow()
        flow._pending_device_names = "UPS A"
        with patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kw: {"type": "form", "step_id": kw["step_id"]},
        ):
            return await flow.async_step_reconfigure_reminder(None)

    result = asyncio.run(_run())
    assert result["step_id"] == "reconfigure_reminder"


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


def _make_options_flow(options=None):
    from custom_components.cyberpower_cloud.config_flow import (
        CyberPowerCloudConfigFlow,
        CyberPowerOptionsFlow,
    )

    entry = MagicMock()
    entry.options = options or {}
    flow = CyberPowerOptionsFlow(entry)
    flow.hass = MagicMock()
    return flow, CyberPowerCloudConfigFlow


def test_options_flow_registered_via_async_get_options_flow():
    """Static helper returns an OptionsFlow instance."""
    from custom_components.cyberpower_cloud.config_flow import (
        CyberPowerCloudConfigFlow,
        CyberPowerOptionsFlow,
    )

    entry = MagicMock()
    entry.options = {}
    flow = CyberPowerCloudConfigFlow.async_get_options_flow(entry)
    assert isinstance(flow, CyberPowerOptionsFlow)


def test_options_flow_shows_form_with_current_interval():
    """Options flow shows the current scan_interval as default."""

    async def _run():
        flow, _ = _make_options_flow(options={"scan_interval": 600})
        with patch.object(
            flow,
            "async_show_form",
            side_effect=lambda **kw: {"type": "form", "step_id": kw["step_id"]},
        ):
            return await flow.async_step_init(None)

    result = asyncio.run(_run())
    assert result["step_id"] == "init"


def test_options_flow_creates_entry_with_new_interval():
    """Submitting the form creates an options entry with the new interval."""

    async def _run():
        flow, _ = _make_options_flow()
        with patch.object(
            flow,
            "async_create_entry",
            side_effect=lambda **kw: {"type": "create_entry", "data": kw["data"]},
        ):
            return await flow.async_step_init({"scan_interval": 1200})

    result = asyncio.run(_run())
    assert result["data"] == {"scan_interval": 1200}
