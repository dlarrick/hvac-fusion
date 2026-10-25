"""Tests for HVAC Fusion diagnostic sensors."""

import pytest
from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hvac_fusion import (
    DOMAIN,
    HvacFusionManager,
)
from custom_components.hvac_fusion.const import (
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_FUEL_TYPE,
    CONF_GAS_COST_PER_THERM,
    CONF_NOMINAL_BTU,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_PROPANE_COST_PER_GAL,
    CONF_TARIFFS,
    CONF_TYPE,
)
from custom_components.hvac_fusion.sensor import (
    HvacFusionBreakEvenCopSensor,
    HvacFusionEconomicCrossoverTemperatureSensor,
)


@pytest.mark.asyncio
async def test_sensors_without_producers(hass: HomeAssistant) -> None:
    """Test sensors report None when no producers are configured."""
    conf = {
        CONF_NAME: "HVAC Fusion Hub",
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temperature",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.25,
            CONF_GAS_COST_PER_THERM: 1.80,
        },
    }
    manager = HvacFusionManager(hass, conf, entry_id="test_hub")
    await manager.async_init()

    xover_sensor = HvacFusionEconomicCrossoverTemperatureSensor(manager)
    cop_sensor = HvacFusionBreakEvenCopSensor(manager)

    assert xover_sensor.native_value is None
    assert cop_sensor.native_value is None
    assert xover_sensor.extra_state_attributes["primary_heat_pump"] is None
    assert xover_sensor.extra_state_attributes["primary_boiler"] is None


@pytest.mark.asyncio
async def test_sensors_with_gas_boiler_and_heat_pump(hass: HomeAssistant) -> None:
    """Test crossover temperature and break-even COP with gas boiler and mini-split."""
    conf = {
        CONF_NAME: "Victorian Coordinator",
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.25,
            CONF_GAS_COST_PER_THERM: 1.88,
        },
        CONF_PRODUCERS: {
            "boiler": {
                CONF_TYPE: "modulating_boiler",
                CONF_NOMINAL_BTU: 150000.0,
                CONF_FUEL_TYPE: "natural_gas",
            },
            "hp": {
                CONF_TYPE: "inverter_heat_pump",
                CONF_PROFILE: "mitsubishi/mxz_3c30nahz2",
            },
        },
    }
    manager = HvacFusionManager(hass, conf, entry_id="test_hub")
    await manager.async_init()

    xover_sensor = HvacFusionEconomicCrossoverTemperatureSensor(manager)
    cop_sensor = HvacFusionBreakEvenCopSensor(manager)

    cop = cop_sensor.native_value
    assert cop is not None
    assert isinstance(cop, float)
    assert 2.0 < cop < 5.0

    xover = xover_sensor.native_value
    assert xover is not None
    assert isinstance(xover, float)
    assert 20.0 < xover < 60.0

    assert cop_sensor.extra_state_attributes["primary_boiler"] == "boiler"
    assert cop_sensor.extra_state_attributes["fuel_type"] == "natural_gas"
    assert xover_sensor.extra_state_attributes["primary_heat_pump"] == "hp"


@pytest.mark.asyncio
async def test_sensors_with_propane_boiler(hass: HomeAssistant) -> None:
    """Test break-even COP calculation with propane tariff."""
    conf = {
        CONF_NAME: "Propane Home",
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.28,
            CONF_PROPANE_COST_PER_GAL: 3.60,
        },
        CONF_PRODUCERS: {
            "boiler": {
                CONF_TYPE: "modulating_boiler",
                CONF_NOMINAL_BTU: 140000.0,
                CONF_FUEL_TYPE: "propane",
            },
            "hp": {
                CONF_TYPE: "inverter_heat_pump",
                CONF_PROFILE: "mitsubishi/mxz_3c30nahz2",
            },
        },
    }
    manager = HvacFusionManager(hass, conf, entry_id="test_propane")
    await manager.async_init()

    cop_sensor = HvacFusionBreakEvenCopSensor(manager)
    cop = cop_sensor.native_value
    assert cop is not None
    assert 1.5 < cop < 4.0
    assert cop_sensor.extra_state_attributes["fuel_type"] == "propane"


@pytest.mark.asyncio
async def test_sensor_setup_entry_and_unload(hass: HomeAssistant) -> None:
    """Test async_setup_entry loads sensor entities and unloads cleanly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="My Coordinator",
        data={
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {
                CONF_ELECTRIC_COST_PER_KWH: 0.25,
                CONF_GAS_COST_PER_THERM: 1.88,
            },
        },
        options={},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Check entities registered in HA state machine
    xover_state = hass.states.get("sensor.hvac_fusion_economic_crossover_temperature")
    cop_state = hass.states.get("sensor.hvac_fusion_break_even_cop")

    assert xover_state is not None
    assert cop_state is not None
    assert xover_state.state == "unknown"  # No producers configured yet
    assert cop_state.state == "unknown"

    # Unload entry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Check manager popped
    assert entry.entry_id not in hass.data.get(DOMAIN, {})
