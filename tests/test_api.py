"""Tests for the CyberPower Cloud API client."""

from __future__ import annotations

import time
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

    def test_encrypt_password_golden_vector(self) -> None:
        """Lock MD5+HMAC-SHA512(cyberpower@TP08!) algorithm against a known-good output.

        Guards against accidental changes to hash order, case, or HMAC secret —
        the server rejects anything else silently as a password mismatch.
        """
        session = MagicMock()
        api = CyberPowerCloudAPI(session, "x@x", "x")
        expected = (
            "5D41402ABC4B2A76B9719D911017C592"  # MD5("hello"), upper
            "6DAD6D5FF5CF836C7BF1C731501CA8D3"
            "5CD54B68A89AF0C3B31742F94B7B4A18"
            "6FF01EBCC4E6129E0B73A485D9626E87"
            "B5FC2B69163D5D917127587E07EC13DE"
        )
        assert api._encrypt_password("hello") == expected


class TestLogin:
    """Test login functionality."""

    async def test_login_success(self) -> None:
        """Test successful login returns flag and caches devices."""
        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))

        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        result = await api.login()

        assert result["Flag"] is True
        assert api.devices == MOCK_LOGIN_RESPONSE["DevicesInfor"]

    async def test_login_sends_correct_payload(self) -> None:
        """Login POSTs {Account, Password (encrypted), LoginType: 10} to the login endpoint.

        These three fields are the entire auth contract with the server — if any
        name, case, or value drifts the server rejects with a generic error.
        """
        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))

        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        call = session.post.call_args
        url = call.args[0]
        assert url.endswith("/LoginAccountWithDeviceInfo")

        payload = call.kwargs["json"]
        assert payload["Account"] == MOCK_EMAIL
        assert payload["LoginType"] == 10
        # Password is MD5(32) + HMAC-SHA512(128) = 160 upper-case hex chars.
        assert len(payload["Password"]) == 160
        assert payload["Password"] == payload["Password"].upper()
        # Never transmit the plaintext password.
        assert MOCK_PASSWORD not in payload["Password"]

    async def test_login_caches_otp_and_token(self) -> None:
        """Login stores OtpKey + bearer token for subsequent authenticated calls."""
        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))

        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        assert api._otp_key == MOCK_LOGIN_RESPONSE["OtpKey"]
        assert api._bearer_token == MOCK_LOGIN_RESPONSE["token"]
        assert api._headers()["Authorization"] == f"Bearer {MOCK_LOGIN_RESPONSE['token']}"

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
        """Device status POSTs {otp, sn} to the status endpoint and unwraps msg.device_status[0]."""
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

        # Payload contract: URL path, OTP from login cache, and SN are all required.
        call = session.post.call_args
        assert call.args[0].endswith("/device/read/status")
        import json as _json

        body = _json.loads(call.kwargs["data"])
        assert body == {"otp": MOCK_LOGIN_RESPONSE["OtpKey"], "sn": "TEST_SN"}
        # Authenticated request must carry the bearer token.
        assert call.kwargs["headers"]["Authorization"] == (
            f"Bearer {MOCK_LOGIN_RESPONSE['token']}"
        )

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
        """Status log posts {otp, dcode, from, to} with a 15-minute window.

        Verifies endpoint URL, dcode is forwarded, and the [from, to] window is
        exactly 900 seconds wide and ends at ~now.
        """
        log_data = {"InVol": 230.5, "OutVol": 230.2, "BatCap": 100}
        response_data = {"result": True, "msg": {"body": [log_data]}}

        session = MagicMock()
        session.post = MagicMock(return_value=_make_response(MOCK_LOGIN_RESPONSE))
        api = CyberPowerCloudAPI(session, MOCK_EMAIL, MOCK_PASSWORD)
        await api.login()

        session.post = MagicMock(return_value=_make_response(response_data))
        before = int(time.time())
        result = await api.get_status_log(12345)
        after = int(time.time())
        assert result == log_data

        call = session.post.call_args
        assert call.args[0].endswith("/status/log")
        import json as _json

        body = _json.loads(call.kwargs["data"])
        assert body["otp"] == MOCK_LOGIN_RESPONSE["OtpKey"]
        assert body["dcode"] == 12345
        # Window end is "now", window is exactly 900s (15 min) wide.
        assert before <= body["to"] <= after
        assert body["to"] - body["from"] == 900

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
