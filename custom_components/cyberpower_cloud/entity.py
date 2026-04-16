"""Base entity for CyberPower Cloud integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CyberPowerCoordinator


class CyberPowerEntity(CoordinatorEntity[CyberPowerCoordinator]):
    """Base class for all CyberPower Cloud entities."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device_sn)},
            name=self.coordinator.device_name,
            manufacturer="CyberPower",
            model=self.coordinator.device_model,
            serial_number=self.coordinator.device_sn,
        )
        if self.coordinator.sw_version:
            info["sw_version"] = self.coordinator.sw_version
        if self.coordinator.fw_version:
            info["hw_version"] = self.coordinator.fw_version
        return info
