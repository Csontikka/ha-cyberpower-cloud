"""Tests for CyberPower Cloud binary_sensor platform."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.cyberpower_cloud.binary_sensor import (
    CyberPowerOnBatterySensor,
    async_setup_entry,
)


def _mock_coordinator(data=None, sn: str = "SN001"):
    coord = MagicMock()
    coord.data = data
    coord.device_sn = sn
    coord.device_name = "Test UPS"
    coord.device_model = "OLS2000"
    coord.sw_version = None
    coord.fw_version = None
    return coord


def _make_sensor(coord):
    with patch.object(CoordinatorEntity, "__init__", return_value=None):
        sensor = CyberPowerOnBatterySensor(coord)
    sensor.coordinator = coord
    return sensor


def test_async_setup_entry_adds_one_per_coordinator():
    """Setup should add one binary sensor per coordinator."""

    async def _run():
        coord_a = _mock_coordinator(sn="A")
        coord_b = _mock_coordinator(sn="B")
        entry = MagicMock()
        entry.runtime_data = [coord_a, coord_b]

        added = []

        def _add(entities):
            added.extend(entities)

        with patch.object(CoordinatorEntity, "__init__", return_value=None):
            await async_setup_entry(MagicMock(), entry, _add)
        return added

    entities = asyncio.run(_run())
    assert len(entities) == 2
    assert all(isinstance(e, CyberPowerOnBatterySensor) for e in entities)


def test_is_on_true_when_on_battery():
    """BatSta != 0 means running on battery."""
    sensor = _make_sensor(_mock_coordinator(data={"BatSta": 1}))
    assert sensor.is_on is True


def test_is_on_false_when_normal():
    """BatSta == 0 means grid power OK."""
    sensor = _make_sensor(_mock_coordinator(data={"BatSta": 0}))
    assert sensor.is_on is False


def test_is_on_none_when_no_data():
    """Returns None if coordinator has no data yet."""
    sensor = _make_sensor(_mock_coordinator(data=None))
    assert sensor.is_on is None


def test_is_on_none_when_batsta_missing():
    """Returns None if BatSta not in payload."""
    sensor = _make_sensor(_mock_coordinator(data={"BatCap": 100}))
    assert sensor.is_on is None


def test_unique_id_includes_sn():
    """Unique ID encodes serial number."""
    sensor = _make_sensor(_mock_coordinator(sn="ABC123"))
    assert sensor._attr_unique_id == "ABC123_on_battery"
