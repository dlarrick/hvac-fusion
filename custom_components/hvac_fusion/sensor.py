"""Sensor platform for HVAC Fusion advisory and diagnostic sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ID,
    CONF_NAME,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up HVAC Fusion sensors from YAML or discovery."""
    if DOMAIN not in hass.data:
        return

    manager = hass.data[DOMAIN].get("manager")
    if not manager:
        return

    entities = [
        HvacFusionEconomicCrossoverTemperatureSensor(manager),
        HvacFusionBreakEvenCopSensor(manager),
    ]
    async_add_entities(entities)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HVAC Fusion sensors from a config entry."""
    manager = hass.data[DOMAIN][entry.entry_id]
    entities = [
        HvacFusionEconomicCrossoverTemperatureSensor(manager),
        HvacFusionBreakEvenCopSensor(manager),
    ]
    async_add_entities(entities)


class HvacFusionSensorBase(SensorEntity):
    """Base class for HVAC Fusion diagnostic sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: Any) -> None:
        """Initialize the sensor."""
        self.manager = manager
        hub_id = getattr(manager, "entry_id", None) or manager.conf.get(CONF_ID, DOMAIN)
        hub_name = manager.conf.get(CONF_NAME, "HVAC Fusion")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hub_id)},
            name=hub_name,
            manufacturer="HVAC Fusion",
            model="Dual Fuel Coordinator",
        )

    async def async_added_to_hass(self) -> None:
        """Register with coordinator manager when added."""
        self.manager.register_sensor_entity(self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from coordinator manager when removed."""
        self.manager.unregister_sensor_entity(self)


class HvacFusionEconomicCrossoverTemperatureSensor(HvacFusionSensorBase):
    """Sensor reporting the economic crossover temperature between heat pump and boiler."""

    _attr_translation_key = "economic_crossover_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_icon = "mdi:thermometer-auto"

    def __init__(self, manager: Any) -> None:
        """Initialize sensor."""
        super().__init__(manager)
        hub_id = getattr(manager, "entry_id", None) or manager.conf.get(CONF_ID, DOMAIN)
        self._attr_unique_id = f"{hub_id}_economic_crossover_temperature"
        self._attr_name = "Economic crossover temperature"

    @property
    def native_value(self) -> float | None:
        """Return the economic crossover temperature."""
        return self.manager.economic_crossover_temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes."""
        attrs: dict[str, Any] = {}
        hp = self.manager.primary_heat_pump
        boiler = self.manager.primary_boiler
        attrs["primary_heat_pump"] = hp.id if hp else None
        attrs["primary_boiler"] = boiler.id if boiler else None
        attrs["break_even_cop"] = self.manager.break_even_cop
        return attrs


class HvacFusionBreakEvenCopSensor(HvacFusionSensorBase):
    """Sensor reporting the thermodynamic break-even COP."""

    _attr_translation_key = "break_even_cop"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:scale-balance"

    def __init__(self, manager: Any) -> None:
        """Initialize sensor."""
        super().__init__(manager)
        hub_id = getattr(manager, "entry_id", None) or manager.conf.get(CONF_ID, DOMAIN)
        self._attr_unique_id = f"{hub_id}_break_even_cop"
        self._attr_name = "Break-even COP"

    @property
    def native_value(self) -> float | None:
        """Return break-even COP."""
        return self.manager.break_even_cop

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes."""
        attrs: dict[str, Any] = {}
        boiler = self.manager.primary_boiler
        attrs["primary_boiler"] = boiler.id if boiler else None
        if self.manager.tariffs:
            attrs["marginal_electric_rate"] = self.manager.tariffs.elec_cost_per_kwh
            attrs["gas_cost_per_therm"] = self.manager.tariffs.gas_cost_per_therm
            attrs["propane_cost_per_gal"] = self.manager.tariffs.propane_cost_per_gal
        if boiler:
            fuel_type = getattr(boiler, "fuel_type", None)
            attrs["fuel_type"] = (
                fuel_type.value if hasattr(fuel_type, "value") else str(fuel_type)
            )
        return attrs
