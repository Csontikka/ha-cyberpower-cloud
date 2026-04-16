"""Tests for CyberPower Cloud base entity."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.cyberpower_cloud.const import DOMAIN
from custom_components.cyberpower_cloud.entity import CyberPowerEntity


def _mock_coordinator(
    sn: str = "SN001",
    name: str = "Test UPS",
    model: str = "OLS2000",
    sw_version: str | None = None,
    fw_version: str | None = None,
):
    coord = MagicMock()
    coord.device_sn = sn
    coord.device_name = name
    coord.device_model = model
    coord.sw_version = sw_version
    coord.fw_version = fw_version
    return coord


def _make_entity(coord):
    """Instantiate CyberPowerEntity bypassing CoordinatorEntity wiring."""
    with patch.object(CoordinatorEntity, "__init__", return_value=None):
        entity = CyberPowerEntity(coord)
    entity.coordinator = coord
    return entity


def test_device_info_minimal():
    """device_info returns required fields without sw/fw when absent."""
    coord = _mock_coordinator()
    entity = _make_entity(coord)

    info = entity.device_info
    assert (DOMAIN, "SN001") in info["identifiers"]
    assert info["name"] == "Test UPS"
    assert info["manufacturer"] == "CyberPower"
    assert info["model"] == "OLS2000"
    assert info["serial_number"] == "SN001"
    assert "sw_version" not in info
    assert "hw_version" not in info


def test_device_info_with_versions():
    """device_info exposes sw_version and hw_version when set."""
    coord = _mock_coordinator(sw_version="1.2.3", fw_version="FW-9")
    entity = _make_entity(coord)

    info = entity.device_info
    assert info["sw_version"] == "1.2.3"
    assert info["hw_version"] == "FW-9"


def test_has_entity_name_is_true():
    """Base entity enables _attr_has_entity_name."""
    entity = _make_entity(_mock_coordinator())
    assert entity._attr_has_entity_name is True
