"""Binary sensor platform for CyberPower Cloud."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CyberPowerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CyberPower binary sensors from config entry."""
    coordinators: list[CyberPowerCoordinator] = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    for coordinator in coordinators:
        entities.append(CyberPowerOnBatterySensor(coordinator))
    async_add_entities(entities)


class CyberPowerOnBatterySensor(
    CoordinatorEntity[CyberPowerCoordinator], BinarySensorEntity
):
    """Binary sensor that indicates if UPS is running on battery."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_translation_key = "on_battery"

    def __init__(self, coordinator: CyberPowerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_sn}_on_battery"

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

    @property
    def is_on(self) -> bool | None:
        """Return True if UPS is on battery (power outage)."""
        if self.coordinator.data is None:
            return None
        bat_sta = self.coordinator.data.get("BatSta")
        if bat_sta is None:
            return None
        return bat_sta != 0
