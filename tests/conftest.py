"""Fixtures for CyberPower Cloud tests."""
from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.cyberpower_cloud.const import DOMAIN

MOCK_EMAIL = "test@example.com"
MOCK_PASSWORD = "TestPass123"

MOCK_DEVICE = {
    "DeviceSN": "000000AA00000001",
    "Id": 123456,
    "DeviceName": "Test UPS",
    "Model": "OLS2000EA",
    "DeviceSubType": 0,
    "SourceType": 0,
    "FirmwareVersion": None,
    "RP": None,
    "RVA": None,
}

MOCK_DEVICE_STATUS = {
    "BatCap": 100,
    "BatSta": 0,
    "BHI": 90,
    "DevLoad": 150,
}

MOCK_STATUS_LOG = {
    "InVol": 230.5,
    "InFreq": 50.0,
    "OutVol": 230.2,
    "OutFreq": 50.0,
    "BatVol": 54.6,
    "DevLoad": 145,
    "BatCap": 100,
    "BatSta": 0,
    "BHI": 90,
    "IntTemp": 28.5,
    "UpdateTime": "2026-04-14 12:00:00",
}

MOCK_LOGIN_RESPONSE = {
    "Flag": True,
    "OtpKey": "mock-otp-key",
    "token": "mock-bearer-token",
    "DevicesInfor": [MOCK_DEVICE],
}

MOCK_CONFIG_ENTRY_DATA = {
    "email": MOCK_EMAIL,
    "password": MOCK_PASSWORD,
}


@pytest.fixture
def mock_api() -> Generator[AsyncMock]:
    """Mock the CyberPowerCloudAPI."""
    with patch(
        "custom_components.cyberpower_cloud.api.CyberPowerCloudAPI",
        autospec=True,
    ) as mock_cls:
        api = mock_cls.return_value
        api.login = AsyncMock(return_value=MOCK_LOGIN_RESPONSE)
        api.devices = [MOCK_DEVICE]
        api.get_device_status = AsyncMock(return_value=MOCK_DEVICE_STATUS)
        api.get_status_log = AsyncMock(return_value=MOCK_STATUS_LOG)
        yield api


@pytest.fixture
def mock_config_entry(hass: HomeAssistant):
    """Create a mock config entry."""
    from homeassistant.config_entries import ConfigEntry
    from unittest.mock import MagicMock

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="CyberPower (Test UPS)",
        data=MOCK_CONFIG_ENTRY_DATA,
        source="user",
        unique_id=MOCK_EMAIL,
        options={},
        discovery_keys=MagicMock(),
    )
    entry.add_to_hass(hass)
    return entry
