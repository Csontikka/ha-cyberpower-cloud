"""Tests for CyberPower Cloud diagnostics."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock

from custom_components.cyberpower_cloud.diagnostics import (
    async_get_config_entry_diagnostics,
)


def _mock_coordinator(
    sn: str = "SN000000123456",
    name: str = "Test UPS",
    model: str = "OLS2000",
    data: dict | None = None,
    interval_seconds: float | None = 300.0,
):
    coord = MagicMock()
    coord.device_sn = sn
    coord.device_name = name
    coord.device_model = model
    coord.data = data
    coord.update_interval = (
        timedelta(seconds=interval_seconds) if interval_seconds is not None else None
    )
    return coord


def test_diagnostics_happy_path():
    """Diagnostics returns redacted account and per-device data."""

    async def _run():
        coord = _mock_coordinator(data={"BatCap": 100, "BatSta": 0})
        entry = MagicMock()
        entry.runtime_data = [coord]
        return await async_get_config_entry_diagnostics(MagicMock(), entry)

    result = asyncio.run(_run())
    assert result["account"] == "**redacted**"
    assert result["device_count"] == 1
    device = result["devices"][0]
    assert device["device_name"] == "Test UPS"
    assert device["device_model"] == "OLS2000"
    assert device["device_sn"] == "SN0000***"  # first 6 + ***
    assert device["update_interval"] == 300.0
    assert device["last_data"] == {"BatCap": 100, "BatSta": 0}


def test_diagnostics_no_data():
    """Diagnostics handles coordinator with no data."""

    async def _run():
        coord = _mock_coordinator(data=None)
        entry = MagicMock()
        entry.runtime_data = [coord]
        return await async_get_config_entry_diagnostics(MagicMock(), entry)

    result = asyncio.run(_run())
    assert result["devices"][0]["last_data"] == {}


def test_diagnostics_no_interval():
    """Diagnostics handles coordinator with stopped update_interval."""

    async def _run():
        coord = _mock_coordinator(interval_seconds=None)
        entry = MagicMock()
        entry.runtime_data = [coord]
        return await async_get_config_entry_diagnostics(MagicMock(), entry)

    result = asyncio.run(_run())
    assert result["devices"][0]["update_interval"] is None


def test_diagnostics_multiple_devices():
    """Diagnostics aggregates across multiple coordinators."""

    async def _run():
        entry = MagicMock()
        entry.runtime_data = [
            _mock_coordinator(sn="SN_AAAAAA1", name="UPS A"),
            _mock_coordinator(sn="SN_BBBBBB2", name="UPS B"),
        ]
        return await async_get_config_entry_diagnostics(MagicMock(), entry)

    result = asyncio.run(_run())
    assert result["device_count"] == 2
    assert {d["device_name"] for d in result["devices"]} == {"UPS A", "UPS B"}
