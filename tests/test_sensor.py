"""Tests for HVAC Fusion diagnostic sensors."""

import pytest
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
    HvacFusionEconomicCrossoverTemperatureSensor,
    HvacFusionProducerSensor,
)
from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant.common import MockConfigEntry


@pytest.mark.asyncio
async def test_sensors_without_producers(hass: HomeAssistant) -> None:
    """Test sensors report None when no producers are configured."""
    conf = {
        CONF_NAME: "HVAC Fusion Coordinator",
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temperature",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.25,
            CONF_GAS_COST_PER_THERM: 1.80,
        },
    }
    manager = HvacFusionManager(hass, conf, entry_id="test_coordinator")
    await manager.async_init()

    xover_sensor = HvacFusionEconomicCrossoverTemperatureSensor(manager)

    assert xover_sensor.native_value is None
    assert xover_sensor.extra_state_attributes["heat_pump"] is None
    assert xover_sensor.extra_state_attributes["auxiliary_producer"] is None
    assert xover_sensor.extra_state_attributes["break_even_cop"] is None


@pytest.mark.asyncio
async def test_sensors_with_gas_boiler_and_heat_pump(hass: HomeAssistant) -> None:
    """Test crossover temperature, break-even COP attribute, and producer status sensors."""
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
                CONF_PROFILE: "mitsubishi/mxz_xcxxnahz2",
            },
        },
    }
    manager = HvacFusionManager(hass, conf, entry_id="test_coordinator")
    await manager.async_init()

    xover_sensor = HvacFusionEconomicCrossoverTemperatureSensor(manager)
    producers_by_id = {p.id: p for p in manager.topology.producers}
    hp_sensor = HvacFusionProducerSensor(manager, producers_by_id["hp"])
    boiler_sensor = HvacFusionProducerSensor(manager, producers_by_id["boiler"])

    xover = xover_sensor.native_value
    assert xover is not None
    assert isinstance(xover, float)
    assert 20.0 < xover < 60.0

    cop = xover_sensor.extra_state_attributes["break_even_cop"]
    assert cop is not None
    assert isinstance(cop, float)
    assert 2.0 < cop < 5.0
    assert xover_sensor.extra_state_attributes["heat_pump"] == "hp"
    assert xover_sensor.extra_state_attributes["auxiliary_producer"] == "boiler"

    # Producer status sensors
    assert hp_sensor.native_value == "idle"
    assert hp_sensor.extra_state_attributes["producer_type"] == "inverter_heat_pump"
    assert hp_sensor.extra_state_attributes["nominal_capacity_btu"] == 24000.0

    assert boiler_sensor.native_value == "idle"
    assert boiler_sensor.extra_state_attributes["producer_type"] == "modulating_boiler"
    assert boiler_sensor.extra_state_attributes["fuel_type"] == "natural_gas"
    assert boiler_sensor.extra_state_attributes["nominal_capacity_btu"] == 150000.0


@pytest.mark.asyncio
async def test_sensors_with_propane_boiler(hass: HomeAssistant) -> None:
    """Test break-even COP attribute calculation and producer sensor with propane tariff."""
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
                CONF_PROFILE: "mitsubishi/mxz_xcxxnahz2",
            },
        },
    }
    manager = HvacFusionManager(hass, conf, entry_id="test_propane")
    await manager.async_init()

    xover_sensor = HvacFusionEconomicCrossoverTemperatureSensor(manager)
    cop = xover_sensor.extra_state_attributes["break_even_cop"]
    assert cop is not None
    assert 1.5 < cop < 4.0

    producers_by_id = {p.id: p for p in manager.topology.producers}
    boiler_sensor = HvacFusionProducerSensor(manager, producers_by_id["boiler"])
    assert boiler_sensor.extra_state_attributes["fuel_type"] == "propane"


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
    assert xover_state is not None
    assert xover_state.state == "unknown"  # No producers configured yet

    # Unload entry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Check manager popped
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


@pytest.mark.asyncio
async def test_sensor_immediate_update_on_options_flow_reload(
    hass: HomeAssistant,
) -> None:
    """Test that sensors update immediately after options flow adds producers and tariffs."""
    hass.states.async_set("sensor.outdoor_temp", "35.0")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {},
            CONF_PRODUCERS: {},
        },
        options={},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Initially unknown because no producers or tariffs configured
    xover_state = hass.states.get("sensor.hvac_fusion_economic_crossover_temperature")
    assert xover_state is not None
    assert xover_state.state == "unknown"

    # Start options flow and add Heat Pump
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "producers_menu"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room Mini-Split",
            CONF_TYPE: "heat_pump",
            "heat_pump_profile": "generic/cold_climate_heat_pump.json",
        },
    )

    # Add Boiler
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Basement Boiler",
            CONF_TYPE: "modulating_boiler",
            "modulating_boiler_profile": "generic/modulating_condensing_boiler.json",
            CONF_FUEL_TYPE: "natural_gas",
        },
    )

    # Return to menu and go to Policies/Tariffs
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "policies_menu"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "electricity_section": {
                CONF_ELECTRIC_COST_PER_KWH: 0.25077,
            },
            "gas_section": {
                CONF_GAS_COST_PER_THERM: 1.50,
            },
            "limits_section": {
                "heat_pump_safety_band_f": 5.0,
            },
            "policies_section": {
                "control_enabled": False,
                "cycling_band_deg": 2.0,
                "evaluation_interval_minutes": 15,
            },
        },
    )

    # Finish options flow
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()

    # Verify sensors updated IMMEDIATELY without waiting for periodic timer
    xover_state = hass.states.get("sensor.hvac_fusion_economic_crossover_temperature")
    assert xover_state is not None
    assert xover_state.state != "unknown"
    xover_val = float(xover_state.state)
    assert 10.0 <= xover_val <= 60.0

    cop_val = float(xover_state.attributes["break_even_cop"])
    assert 1.0 <= cop_val <= 10.0
    assert xover_state.attributes["system_phase"] in (
        "away_coast",
        "plateau_maintenance",
        "setback_recovery",
        "passive_ventilation",
    )

    # Verify producer status sensors exist and are tracked
    hp_state = hass.states.get("sensor.hvac_fusion_living_room_mini_split")
    boiler_state = hass.states.get("sensor.hvac_fusion_basement_boiler")
    assert hp_state is not None
    assert boiler_state is not None
    assert hp_state.state in ("idle", "heating", "cooling", "locked_out")
    assert boiler_state.state in ("idle", "heating")


@pytest.mark.asyncio
async def test_producer_sensor_active_delivery_units_no_cross_contamination(
    hass: HomeAssistant,
) -> None:
    """Test that producer status sensors strictly isolate their own delivery units across multiple producer types."""
    from unittest.mock import MagicMock
    from custom_components.hvac_fusion.const import (
        CONF_EMITTERS,
        CONF_PRODUCER,
        CONF_SPACES,
        CONF_TEMP_SENSOR,
        CONF_ZONE_ID,
    )
    from homeassistant.const import CONF_ENTITY_ID, CONF_ID

    conf = {
        CONF_NAME: "Multi-Producer Multi-Emitter System",
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.25,
            CONF_GAS_COST_PER_THERM: 1.50,
        },
        CONF_PRODUCERS: {
            "hp1": {
                CONF_TYPE: "inverter_heat_pump",
                CONF_PROFILE: "mitsubishi/mxz_xcxxnahz2",
            },
            "hp2": {
                CONF_TYPE: "inverter_heat_pump",
                CONF_PROFILE: "generic/cold_climate_heat_pump.json",
            },
            "boiler": {
                CONF_TYPE: "modulating_boiler",
                CONF_NOMINAL_BTU: 100000.0,
                CONF_FUEL_TYPE: "natural_gas",
            },
        },
        CONF_SPACES: [
            {
                CONF_ID: "great_room",
                CONF_NAME: "Great Room",
                CONF_TEMP_SENSOR: "sensor.great_room_temp",
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "hp1",
                        CONF_ENTITY_ID: "climate.great_room_hp1_a",
                        CONF_NOMINAL_BTU: 12000.0,
                    },
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "hp1",
                        CONF_ENTITY_ID: "climate.great_room_hp1_b",
                        CONF_NOMINAL_BTU: 9000.0,
                    },
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "hp2",
                        CONF_ENTITY_ID: "climate.great_room_hp2_a",
                        CONF_NOMINAL_BTU: 12000.0,
                    },
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "hp2",
                        CONF_ENTITY_ID: "climate.great_room_hp2_b",
                        CONF_NOMINAL_BTU: 9000.0,
                    },
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "boiler",
                        CONF_ENTITY_ID: "climate.great_room_rad_a",
                        CONF_ZONE_ID: "z1",
                    },
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "boiler",
                        CONF_ENTITY_ID: "climate.great_room_rad_b",
                        CONF_ZONE_ID: "z2",
                    },
                ],
            },
            {
                CONF_ID: "bedroom",
                CONF_NAME: "Bedroom",
                CONF_TEMP_SENSOR: "sensor.bedroom_temp",
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "hp1",
                        CONF_ENTITY_ID: "climate.bedroom_hp1",
                        CONF_NOMINAL_BTU: 9000.0,
                    },
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "boiler",
                        CONF_ENTITY_ID: "climate.bedroom_rad",
                        CONF_ZONE_ID: "z3",
                    },
                ],
            },
        ],
    }

    manager = HvacFusionManager(hass, conf, entry_id="test_multi_prod")
    await manager.async_init()

    producers_by_id = {p.id: p for p in manager.topology.producers}
    hp1_sensor = HvacFusionProducerSensor(manager, producers_by_id["hp1"])
    hp2_sensor = HvacFusionProducerSensor(manager, producers_by_id["hp2"])
    boiler_sensor = HvacFusionProducerSensor(manager, producers_by_id["boiler"])

    # Mock a dispatch plan where great_room calls hp1, but has foreign emitters in active_delivery_unit_ids
    # and bedroom calls boiler, but also has foreign emitters in active_delivery_unit_ids
    great_room_dir = MagicMock()
    great_room_dir.active_producer_id = "hp1"
    great_room_dir.active_delivery_unit_ids = [
        "great_room_hp1_0",
        "great_room_hp1_1",
        "great_room_hp2_2",
        "great_room_boiler_4",
    ]

    bedroom_dir = MagicMock()
    bedroom_dir.active_producer_id = "boiler"
    bedroom_dir.active_delivery_unit_ids = [
        "bedroom_hp1_0",
        "bedroom_boiler_1",
    ]

    mock_plan = MagicMock()
    mock_plan.producer_directives = {}
    mock_plan.space_directives = {
        "great_room": great_room_dir,
        "bedroom": bedroom_dir,
    }

    manager.last_plan = mock_plan

    # Verify hp1 attributes
    hp1_attrs = hp1_sensor.extra_state_attributes
    assert hp1_attrs["active_spaces"] == ["great_room"]
    assert hp1_attrs["active_delivery_units"] == [
        "great_room_hp1_0",
        "great_room_hp1_1",
    ]

    # Verify hp2 attributes (not called by any space)
    hp2_attrs = hp2_sensor.extra_state_attributes
    assert hp2_attrs["active_spaces"] == []
    assert hp2_attrs["active_delivery_units"] == []

    # Verify boiler attributes
    boiler_attrs = boiler_sensor.extra_state_attributes
    assert boiler_attrs["active_spaces"] == ["bedroom"]
    assert boiler_attrs["active_delivery_units"] == ["bedroom_boiler_1"]
