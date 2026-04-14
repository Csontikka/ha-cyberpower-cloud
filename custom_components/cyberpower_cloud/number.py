"""Number platform for CyberPower Cloud."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CyberPowerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CyberPower number entities from config entry."""
    coordinators: list[CyberPowerCoordinator] = hass.data[DOMAIN][entry.entry_id]

    entities: list[NumberEntity] = []
    for coordinator in coordinators:
        entities.append(CyberPowerRatedPowerNumber(coordinator))
    async_add_entities(entities)


class CyberPowerRatedPowerNumber(
    CoordinatorEntity[CyberPowerCoordinator], NumberEntity, RestoreEntity
):
    """Number entity to configure UPS rated power per device."""

    _attr_has_entity_name = True
    _attr_translation_key = "ups_rated_power"
    _attr_native_min_value = 100
    _attr_native_max_value = 20000
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: CyberPowerCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_sn}_rated_power"
        self._attr_native_value = coordinator.ups_rated_power

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

    async def async_added_to_hass(self) -> None:
        """Restore previous value on startup."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                self._attr_native_value = int(float(last_state.state))
                self.coordinator.ups_rated_power = self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the rated power value and refresh dependent sensors."""
        self._attr_native_value = int(value)
        self.coordinator.ups_rated_power = int(value)
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
