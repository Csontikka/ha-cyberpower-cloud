"""Tests for the CyberPower Cloud API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.cyberpower_cloud.api import (
    ApiError,
    AuthError,
    CyberPowerCloudAPI,
)

from .conftest import MOCK_EMAIL, MOCK_LOGIN_RESPONSE, MOCK_PASSWORD


def _make_response(data: dict, status: int = 200) -> AsyncMock:
    """Create a mock aiohttp response context manager."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


class TestPasswordEncryption:
    """Test password encryption logic."""

    def test_encrypt_password_format(self) -> None:
        """Test that encrypted password has correct format (MD5 + HMAC-SHA512)."""
        session = MagicMock()
        api = CyberPowerCloudAPI(session, "test@test.com", "test")
        result = api._encrypt_password("test")

        # MD5 hex = 32 chars, SHA512 hex = 128 chars -> total 160
        assert len(result) == 160
        # All uppercase hex
        assert result == result.upper()

    def test_encrypt_password_deterministic(self) -> None:
        """Test that same password always produces same result."""
        session = MagicMock()
        api = CyberPowerCloudAPI(session, "test@test.com", "test")
        result1 = api._encrypt_password("password123")
        result2 = api._encrypt_password("password123")
        assert result1 == result2

    def test_encrypt_password_different_inputs(self) -> None:
        """Test that different passwords produce different results."""
        session = MagicMock()
        api = CyberPowerCloudAPI(session, "test@test.com", "test")
        result1 = api._encrypt_password("password1")
        result2 = api._encrypt_password("password2")
        assert result1 != result2


class TestLogin:
    """Test login functionality."""

    async def test_login_success(self) -> None:
        """Test successful login."""
        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))

        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        result = await api.login()

        assert result["Flag"] is True
        assert api.devices == MOCK_LOGIN_RESPONSE["DevicesInfor"]

    async def test_login_failure(self) -> None:
        """Test failed login raises AuthError."""
        session = MagicMock()
        session.post = MagicMock(
            return_value=_make_response({"Flag": False, "Message": "Wrong password"})
        )

        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        with pytest.raises(AuthError, match="Wrong password"):
            await api.login()


class TestDeviceStatus:
    """Test device status retrieval."""

    async def test_get_device_status_success(self) -> None:
        """Test successful device status retrieval."""
        status_data = {"BatCap": 100, "BatSta": 0, "BHI": 90, "DevLoad": 150}
        response_data = {
            "result": True,
            "msg": {"device_status": [status_data]},
        }

        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))

        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        session.post = MagicMock(return_value=_make_response(response_data))
        result = await api.get_device_status("TEST_SN")
        assert result == status_data

    async def test_get_device_status_empty(self) -> None:
        """Test device status with empty response raises ApiError."""
        response_data = {"result": True, "msg": {"device_status": []}}

        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))

        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        session.post = MagicMock(return_value=_make_response(response_data))
        with pytest.raises(ApiError, match="No device status"):
            await api.get_device_status("TEST_SN")


class TestStatusLog:
    """Test status log retrieval."""

    async def test_get_status_log_success(self) -> None:
        """Returns most recent entry from body list."""
        log_data = {"InVol": 230.5, "OutVol": 230.2, "BatCap": 100}
        response_data = {"result": True, "msg": {"body": [log_data]}}

        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))
        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        session.post = MagicMock(return_value=_make_response(response_data))
        result = await api.get_status_log(12345)
        assert result == log_data

    async def test_get_status_log_empty_returns_empty_dict(self) -> None:
        """Empty log body returns empty dict rather than raising."""
        response_data = {"result": True, "msg": {"body": []}}

        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))
        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        session.post = MagicMock(return_value=_make_response(response_data))
        assert await api.get_status_log(12345) == {}


class TestPostErrorPaths:
    """Test the shared _post() helper error handling."""

    async def test_post_api_error_dict_errmsg(self) -> None:
        """Structured errmsg dict surfaces the body field."""
        response_data = {"result": False, "errmsg": {"body": "Device offline"}}

        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))
        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        session.post = MagicMock(return_value=_make_response(response_data))
        with pytest.raises(ApiError, match="Device offline"):
            await api.get_device_status("SN")

    async def test_post_api_error_plain_errmsg(self) -> None:
        """Plain-string errmsg surfaces directly."""
        response_data = {"result": False, "errmsg": "Something broke"}

        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))
        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        session.post = MagicMock(return_value=_make_response(response_data))
        with pytest.raises(ApiError, match="Something broke"):
            await api.get_device_status("SN")

    async def test_post_401_triggers_relogin(self) -> None:
        """A 401 on first attempt re-logs in and retries successfully."""
        login_resp = _make_response(MOCK_LOGIN_RESPONSE)
        expired_resp = _make_response({"result": False}, status=401)
        success_resp = _make_response(
            {"result": True, "msg": {"device_status": [{"BatCap": 95}]}}
        )

        session = MagicMock()
        # sequence: initial login, expired request, re-login, successful retry
        session.post = MagicMock(
            side_effect=[login_resp, expired_resp, login_resp, success_resp]
        )
        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        result = await api.get_device_status("SN")
        assert result == {"BatCap": 95}

    async def test_post_relogin_failure_raises_auth_error(self) -> None:
        """401 persisting across the retry surfaces as AuthError."""
        login_resp = _make_response(MOCK_LOGIN_RESPONSE)
        expired_resp = _make_response({"result": False}, status=401)

        session = MagicMock()
        # Always returns 401 for requests; logins succeed.
        responses = iter(
            [login_resp, expired_resp, login_resp, expired_resp, login_resp]
        )
        session.post = MagicMock(side_effect=lambda *a, **kw: next(responses))
        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        from custom_components.cyberpower_cloud.api import AuthError

        with pytest.raises(AuthError, match="Re-login failed"):
            await api.get_device_status("SN")

    async def test_post_expired_errmsg_triggers_relogin(self) -> None:
        """'expired' in errmsg triggers re-login path even without 401."""
        login_resp = _make_response(MOCK_LOGIN_RESPONSE)
        expired_resp = _make_response(
            {"result": False, "errmsg": "token expired"}, status=200
        )
        success_resp = _make_response(
            {"result": True, "msg": {"device_status": [{"BatCap": 80}]}}
        )

        session = MagicMock()
        session.post = MagicMock(
            side_effect=[login_resp, expired_resp, login_resp, success_resp]
        )
        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        result = await api.get_device_status("SN")
        assert result == {"BatCap": 80}
