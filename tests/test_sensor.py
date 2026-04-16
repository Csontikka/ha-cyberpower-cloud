"""Tests for CyberPower Cloud sensor platform."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.cyberpower_cloud.sensor import (
    DEVICE_STATUS_MAP,
    SENSOR_DESCRIPTIONS,
    CyberPowerSensor,
    async_setup_entry,
)


def _mock_coordinator(data=None, rated_power: int = 2000, sn: str = "SN001"):
    coord = MagicMock()
    coord.data = data
    coord.device_sn = sn
    coord.device_name = "Test UPS"
    coord.device_model = "OLS2000"
    coord.ups_rated_power = rated_power
    coord.sw_version = None
    coord.fw_version = None
    return coord


def _get_desc(key: str):
    return next(d for d in SENSOR_DESCRIPTIONS if d.key == key)


def _make_sensor(coord, key: str):
    with patch.object(CoordinatorEntity, "__init__", return_value=None):
        sensor = CyberPowerSensor(coord, _get_desc(key))
    sensor.coordinator = coord
    return sensor


def test_sensor_descriptions_count():
    """Sensor catalog is non-empty and keys are unique."""
    assert len(SENSOR_DESCRIPTIONS) >= 13
    keys = [d.key for d in SENSOR_DESCRIPTIONS]
    assert len(keys) == len(set(keys))


def test_async_setup_entry_adds_all_sensors():
    """Setup adds one CyberPowerSensor per description per coordinator."""

    async def _run():
        entry = MagicMock()
        entry.runtime_data = [_mock_coordinator(sn="A"), _mock_coordinator(sn="B")]
        added = []

        def _add(entities):
            added.extend(entities)

        with patch.object(CoordinatorEntity, "__init__", return_value=None):
            await async_setup_entry(MagicMock(), entry, _add)
        return added

    entities = asyncio.run(_run())
    assert len(entities) == 2 * len(SENSOR_DESCRIPTIONS)


def test_native_value_none_without_data():
    """native_value is None when coordinator data is None."""
    sensor = _make_sensor(_mock_coordinator(data=None), "input_voltage")
    assert sensor.native_value is None


def test_native_value_none_when_key_missing():
    """native_value is None when the specific key is absent."""
    sensor = _make_sensor(_mock_coordinator(data={}), "input_voltage")
    assert sensor.native_value is None


def test_input_voltage_raw_passthrough():
    """Plain numeric sensors pass the raw value through."""
    sensor = _make_sensor(_mock_coordinator(data={"InVolt": 230.5}), "input_voltage")
    assert sensor.native_value == 230.5


def test_battery_capacity_passthrough():
    sensor = _make_sensor(_mock_coordinator(data={"BatCap": 95}), "battery_capacity")
    assert sensor.native_value == 95


def test_device_status_maps_known_values():
    """device_status maps 0..3 through DEVICE_STATUS_MAP."""
    for code, expected in DEVICE_STATUS_MAP.items():
        sensor = _make_sensor(
            _mock_coordinator(data={"device_status": code}), "device_status"
        )
        assert sensor.native_value == expected


def test_device_status_unknown_code():
    """Unknown device_status code returns 'Unknown (N)'."""
    sensor = _make_sensor(
        _mock_coordinator(data={"device_status": 99}), "device_status"
    )
    assert sensor.native_value == "Unknown (99)"


def test_load_percentage_with_rated_power():
    """load returns percentage of ups_rated_power."""
    sensor = _make_sensor(
        _mock_coordinator(data={"DevLoad": 500}, rated_power=2000), "load"
    )
    assert sensor.native_value == 25.0


def test_load_returns_none_when_rated_power_is_zero():
    """load returns None while rated_power unconfigured (=0)."""
    sensor = _make_sensor(
        _mock_coordinator(data={"DevLoad": 500}, rated_power=0), "load"
    )
    assert sensor.native_value is None


def test_power_consumption_passthrough():
    """power_consumption returns raw DevLoad watt value."""
    sensor = _make_sensor(
        _mock_coordinator(data={"DevLoad": 500}, rated_power=2000), "power_consumption"
    )
    assert sensor.native_value == 500


def test_last_update_parses_timestamp():
    """last_update converts 'YYYY-MM-DD HH:MM:SS' to timezone-aware datetime."""
    sensor = _make_sensor(
        _mock_coordinator(data={"timestamp": "2026-04-14 12:30:45"}), "last_update"
    )
    dt = sensor.native_value
    assert dt is not None
    assert dt.year == 2026 and dt.month == 4 and dt.day == 14
    assert dt.hour == 12 and dt.minute == 30 and dt.second == 45


def test_unique_id_includes_sn_and_key():
    """Unique ID combines SN and description key."""
    sensor = _make_sensor(_mock_coordinator(sn="Z9"), "battery_capacity")
    assert sensor._attr_unique_id == "Z9_battery_capacity"
