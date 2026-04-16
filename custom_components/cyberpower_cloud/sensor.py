"""Sensor platform for CyberPower Cloud."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.util.dt import parse_datetime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CyberPowerCoordinator
from .entity import CyberPowerEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class CyberPowerSensorDescription(SensorEntityDescription):
    """Sensor entity description with data key."""

    value_fn: str  # key in coordinator.data


SENSOR_DESCRIPTIONS: tuple[CyberPowerSensorDescription, ...] = (
    CyberPowerSensorDescription(
        key="input_voltage",
        translation_key="input_voltage",
        value_fn="InVolt",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="output_voltage",
        translation_key="output_voltage",
        value_fn="OutVolt",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="input_frequency",
        translation_key="input_frequency",
        value_fn="InFreq",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="output_frequency",
        translation_key="output_frequency",
        value_fn="OutFreq",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="battery_capacity",
        translation_key="battery_capacity",
        value_fn="BatCap",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="battery_runtime",
        translation_key="battery_runtime",
        value_fn="BatRun",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="load",
        translation_key="load",
        value_fn="DevLoad",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="battery_health",
        translation_key="battery_health",
        value_fn="BHI",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="ups_temperature",
        translation_key="ups_temperature",
        value_fn="SysTemp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="environment_temperature",
        translation_key="environment_temperature",
        value_fn="EnvTemp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="environment_humidity",
        translation_key="environment_humidity",
        value_fn="EnvHumi",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="device_status",
        translation_key="device_status",
        value_fn="device_status",
    ),
    CyberPowerSensorDescription(
        key="power_consumption",
        translation_key="power_consumption",
        value_fn="DevLoad",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    CyberPowerSensorDescription(
        key="last_update",
        translation_key="last_update",
        value_fn="timestamp",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)

DEVICE_STATUS_MAP = {
    0: "Normal",
    1: "Warning",
    2: "Critical",
    3: "Offline",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CyberPower sensors from config entry."""
    coordinators: list[CyberPowerCoordinator] = entry.runtime_data

    entities: list[CyberPowerSensor] = []
    for coordinator in coordinators:
        for description in SENSOR_DESCRIPTIONS:
            entities.append(CyberPowerSensor(coordinator, description))

    async_add_entities(entities)


class CyberPowerSensor(CyberPowerEntity, SensorEntity):
    """Sensor entity for CyberPower UPS data."""

    entity_description: CyberPowerSensorDescription

    def __init__(
        self,
        coordinator: CyberPowerCoordinator,
        description: CyberPowerSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_sn}_{description.key}"

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self.entity_description.value_fn)
        if value is None:
            return None
        if self.entity_description.key == "device_status":
            return DEVICE_STATUS_MAP.get(value, f"Unknown ({value})")
        if self.entity_description.key == "load":
            rated = self.coordinator.ups_rated_power
            if rated == 0:
                return None  # rated power not configured yet
            return round(value / rated * 100, 1)
        if self.entity_description.key == "last_update":
            return parse_datetime(str(value).replace(" ", "T") + "+00:00")
        return value
