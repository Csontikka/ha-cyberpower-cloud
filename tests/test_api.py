"""Tests for the CyberPower Cloud API client."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
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
