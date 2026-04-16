"""Tests for CyberPower Cloud number platform."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.cyberpower_cloud.number import (
    CyberPowerRatedPowerNumber,
    async_setup_entry,
)


def _mock_coordinator(rated_power: int = 2000, sn: str = "SN001"):
    coord = MagicMock()
    coord.device_sn = sn
    coord.device_name = "Test UPS"
    coord.device_model = "OLS2000"
    coord.ups_rated_power = rated_power
    coord.sw_version = None
    coord.fw_version = None
    coord.async_request_refresh = AsyncMock()
    return coord


def _make_number(coord):
    with patch.object(CoordinatorEntity, "__init__", return_value=None):
        entity = CyberPowerRatedPowerNumber(coord)
    entity.coordinator = coord
    return entity


def test_async_setup_entry_adds_one_per_coordinator():
    """Setup adds one number entity per coordinator."""

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
    assert len(entities) == 2
    assert all(isinstance(e, CyberPowerRatedPowerNumber) for e in entities)


def test_init_seeds_value_from_coordinator():
    """Initial native value mirrors coordinator's rated power."""
    num = _make_number(_mock_coordinator(rated_power=1500))
    assert num._attr_native_value == 1500


def test_unique_id_includes_sn():
    """Unique ID encodes serial number."""
    num = _make_number(_mock_coordinator(sn="SN_XYZ"))
    assert num._attr_unique_id == "SN_XYZ_rated_power"


def test_async_set_native_value_updates_coordinator():
    """Setting the value mirrors into coordinator and triggers refresh."""

    async def _run():
        coord = _mock_coordinator(rated_power=2000)
        num = _make_number(coord)
        num.async_write_ha_state = MagicMock()
        await num.async_set_native_value(1234.7)
        return coord, num

    coord, num = asyncio.run(_run())
    assert num._attr_native_value == 1234
    assert coord.ups_rated_power == 1234
    coord.async_request_refresh.assert_awaited_once()
    num.async_write_ha_state.assert_called_once()


def _restore_state(state_value: str | None):
    """Build a fake last_state with the given string state."""
    st = MagicMock()
    st.state = state_value
    return st


def test_async_added_to_hass_restores_previous_value():
    """RestoreEntity restores the last known value on startup."""

    async def _run():
        coord = _mock_coordinator(rated_power=2000)
        num = _make_number(coord)
        num.async_get_last_state = AsyncMock(return_value=_restore_state("1800"))
        with patch(
            "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ):
            await num.async_added_to_hass()
        return coord, num

    coord, num = asyncio.run(_run())
    assert num._attr_native_value == 1800
    assert coord.ups_rated_power == 1800


def test_async_added_to_hass_ignores_unknown_state():
    """Unknown/unavailable last state does not overwrite the init value."""

    async def _run():
        coord = _mock_coordinator(rated_power=2000)
        num = _make_number(coord)
        num.async_get_last_state = AsyncMock(return_value=_restore_state("unknown"))
        with patch(
            "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ):
            await num.async_added_to_hass()
        return num

    num = asyncio.run(_run())
    assert num._attr_native_value == 2000


def test_async_added_to_hass_handles_missing_last_state():
    """No previous state means we keep the init value."""

    async def _run():
        coord = _mock_coordinator(rated_power=2000)
        num = _make_number(coord)
        num.async_get_last_state = AsyncMock(return_value=None)
        with patch(
            "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ):
            await num.async_added_to_hass()
        return num

    num = asyncio.run(_run())
    assert num._attr_native_value == 2000
