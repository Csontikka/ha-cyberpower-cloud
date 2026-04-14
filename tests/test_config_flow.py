"""Tests for the CyberPower Cloud config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.cyberpower_cloud.api import AuthError
from custom_components.cyberpower_cloud.const import DOMAIN

from .conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_DEVICE, MOCK_EMAIL, MOCK_LOGIN_RESPONSE


async def test_user_flow_success(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """Test successful user config flow."""
    with patch(
        "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG_ENTRY_DATA
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "CyberPower (Test UPS)"
        assert result["data"] == MOCK_CONFIG_ENTRY_DATA


async def test_user_flow_invalid_auth(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """Test config flow with invalid credentials."""
    mock_api.login = AsyncMock(side_effect=AuthError("Invalid credentials"))

    with patch(
        "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG_ENTRY_DATA
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """Test config flow with connection error."""
    mock_api.login = AsyncMock(side_effect=aiohttp.ClientError())

    with patch(
        "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG_ENTRY_DATA
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_no_devices(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    """Test config flow when no devices found."""
    mock_api.devices = []

    with patch(
        "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG_ENTRY_DATA
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "no_devices"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_api: AsyncMock, mock_config_entry
) -> None:
    """Test config flow when already configured."""
    with patch(
        "custom_components.cyberpower_cloud.config_flow.CyberPowerCloudAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], MOCK_CONFIG_ENTRY_DATA
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"
