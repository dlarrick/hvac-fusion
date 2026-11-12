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

    from . import HvacFusionManager

    manager = next(
        (
            v
            for v in hass.data.get(DOMAIN, {}).values()
            if isinstance(v, HvacFusionManager)
        ),
        None,
    )
    if not manager:
        return

    entities: list[SensorEntity] = [
        HvacFusionEconomicCrossoverTemperatureSensor(manager),
    ]
    if manager.topology and manager.topology.producers:
        for producer in manager.topology.producers:
            entities.append(HvacFusionProducerSensor(manager, producer))
    async_add_entities(entities)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HVAC Fusion sensors from a config entry."""
    manager = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        HvacFusionEconomicCrossoverTemperatureSensor(manager),
    ]
    if manager.topology and manager.topology.producers:
        for producer in manager.topology.producers:
            entities.append(HvacFusionProducerSensor(manager, producer))
    async_add_entities(entities)


class HvacFusionSensorBase(SensorEntity):
    """Base class for HVAC Fusion diagnostic sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: Any) -> None:
        """Initialize the sensor."""
        self.manager = manager
        coord_id = getattr(manager, "entry_id", None) or manager.conf.get(
            CONF_ID, DOMAIN
        )
        coord_name = manager.conf.get(CONF_NAME, "HVAC Fusion")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coord_id)},
            name=coord_name,
            manufacturer="HVAC Fusion",
            model="Dual Fuel Coordinator",
        )

    async def async_added_to_hass(self) -> None:
        """Register with coordinator manager when added."""
        self.manager.register_sensor_entity(self)
        if self.hass is not None:
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from coordinator manager when removed."""
        self.manager.unregister_sensor_entity(self)


class HvacFusionEconomicCrossoverTemperatureSensor(HvacFusionSensorBase):
    """Sensor reporting the economic crossover temperature between heat pump and boiler."""

    _attr_translation_key = "economic_crossover_temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, manager: Any) -> None:
        """Initialize sensor."""
        super().__init__(manager)
        coord_id = getattr(manager, "entry_id", None) or manager.conf.get(
            CONF_ID, DOMAIN
        )
        self._attr_unique_id = f"{coord_id}_economic_crossover_temperature"
        self._attr_name = "Economic crossover temperature"

    @property
    def native_value(self) -> float | None:
        """Return the economic crossover temperature."""
        return self.manager.economic_crossover_temperature

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return central plant economic and coordination attributes."""
        attrs: dict[str, Any] = {}
        hp = self.manager.primary_heat_pump
        boiler = self.manager.primary_boiler
        attrs["heat_pump"] = hp.id if hp else None
        attrs["auxiliary_producer"] = boiler.id if boiler else None
        attrs["break_even_cop"] = self.manager.break_even_cop
        attrs["system_phase"] = self.manager.system_phase
        attrs["control_enabled"] = self.manager.control_enabled
        return attrs


class HvacFusionProducerSensor(HvacFusionSensorBase):
    """Sensor reporting operational state and attributes for an energy producer."""

    def __init__(self, manager: Any, producer: Any) -> None:
        """Initialize producer sensor."""
        super().__init__(manager)
        self.producer = producer
        coord_id = getattr(manager, "entry_id", None) or manager.conf.get(
            CONF_ID, DOMAIN
        )
        self._attr_unique_id = f"{coord_id}_{producer.id}"
        self._attr_name = producer.name if producer.name else producer.id
        self._setup_icon()

    def _setup_icon(self) -> None:
        from hvac_crossover import ProducerType

        p_type = getattr(self.producer, "producer_type", None)
        if p_type == ProducerType.INVERTER_HEAT_PUMP:
            self._attr_icon = "mdi:heat-pump"
        elif p_type == ProducerType.FURNACE:
            self._attr_icon = "mdi:fire"
        else:
            self._attr_icon = "mdi:water-boiler"

    @property
    def native_value(self) -> str:
        """Return operational state: idle, heating, cooling, or locked_out."""
        from hvac_crossover import HvacMode, ProducerType

        outdoor_temp = self.manager.get_outdoor_temp()
        p_type = getattr(self.producer, "producer_type", None)

        if p_type == ProducerType.INVERTER_HEAT_PUMP and outdoor_temp is not None:
            min_temp = getattr(self.producer, "min_operating_temp_f", -15.0)
            safety = 5.0
            if self.manager.coordinator and hasattr(self.manager.coordinator, "config"):
                safety = getattr(
                    self.manager.coordinator.config, "heat_pump_safety_band_f", 5.0
                )
            if outdoor_temp < (min_temp + safety):
                return "locked_out"

        if self.manager.last_plan:
            p_dir = self.manager.last_plan.producer_directives.get(self.producer.id)
            if p_dir and p_dir.is_active:
                if p_dir.operational_mode == HvacMode.HEAT:
                    return "heating"
                if p_dir.operational_mode == HvacMode.COOL:
                    return "cooling"
                return "active"

        return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return producer operational and thermodynamic attributes."""
        from hvac_crossover import ProducerType

        attrs: dict[str, Any] = {
            "producer_id": self.producer.id,
            "producer_type": (
                self.producer.producer_type.value
                if hasattr(self.producer.producer_type, "value")
                else str(self.producer.producer_type)
            ),
            "nominal_capacity_btu": self.producer.nominal_btu,
        }

        # Determine active spaces and delivery units from last plan
        active_spaces: list[str] = []
        active_delivery_units: list[str] = []

        producer_delivery_unit_ids: set[str] = set()
        if self.manager.topology:
            for space in self.manager.topology.spaces:
                for emitter in space.emitters:
                    if getattr(emitter, "producer_id", None) == self.producer.id:
                        producer_delivery_unit_ids.add(emitter.id)

        p_dir = None
        if self.manager.last_plan:
            p_dir = self.manager.last_plan.producer_directives.get(self.producer.id)
            if p_dir and p_dir.active_zones:
                active_spaces = list(p_dir.active_zones)
            for s_id, s_dir in self.manager.last_plan.space_directives.items():
                if s_dir.active_producer_id == self.producer.id:
                    if s_id not in active_spaces:
                        active_spaces.append(s_id)
                    for u_id in s_dir.active_delivery_unit_ids:
                        if u_id in producer_delivery_unit_ids:
                            active_delivery_units.append(u_id)

        attrs["active_spaces"] = sorted(active_spaces)
        attrs["active_delivery_units"] = sorted(set(active_delivery_units))

        outdoor_temp = self.manager.get_outdoor_temp()
        p_type = getattr(self.producer, "producer_type", None)

        if p_type == ProducerType.INVERTER_HEAT_PUMP:
            min_temp = getattr(self.producer, "min_operating_temp_f", -15.0)
            safety = 5.0
            if self.manager.coordinator and hasattr(self.manager.coordinator, "config"):
                safety = getattr(
                    self.manager.coordinator.config, "heat_pump_safety_band_f", 5.0
                )
            attrs["safety_lockout"] = bool(
                outdoor_temp is not None and outdoor_temp < (min_temp + safety)
            )

            if outdoor_temp is not None:
                try:
                    cop = self.producer.cop_at(outdoor_temp)
                    attrs["current_cop"] = round(float(cop), 2)
                except Exception:
                    attrs["current_cop"] = None
                try:
                    derate = self.producer.derate_at(outdoor_temp)
                    attrs["capacity_derate_pct"] = round(float(derate) * 100.0, 1)
                except Exception:
                    attrs["capacity_derate_pct"] = None
            else:
                attrs["current_cop"] = None
                attrs["capacity_derate_pct"] = None

            mode_lock = None
            if self.manager.last_plan and self.manager.last_plan.diagnostics:
                mode_lock = self.manager.last_plan.diagnostics.odu_modes.get(
                    self.producer.id
                )
            attrs["mode_lock"] = mode_lock

        else:
            fuel_type = getattr(self.producer, "fuel_type", None)
            attrs["fuel_type"] = (
                fuel_type.value if hasattr(fuel_type, "value") else str(fuel_type)
            )

            rated_afue = getattr(self.producer, "rated_afue", None)
            if rated_afue is not None:
                attrs["rated_afue"] = rated_afue

            if p_type == ProducerType.MODULATING_BOILER:
                attrs["has_outdoor_reset"] = getattr(
                    self.producer, "has_outdoor_reset", False
                )
                attrs["estimated_return_temp_f"] = (
                    p_dir.estimated_return_temp_f if p_dir else None
                )
                attrs["estimated_efficiency"] = (
                    p_dir.estimated_efficiency if p_dir else None
                )
                attrs["condensing_state"] = p_dir.condensing_state if p_dir else None

        return attrs
