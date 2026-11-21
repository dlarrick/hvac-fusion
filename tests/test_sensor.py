"""Tests for HVAC Fusion diagnostic sensors."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from custom_components.hvac_fusion import (
    DOMAIN,
    HvacFusionManager,
)
from custom_components.hvac_fusion.const import (
    CONF_CONTROL_ENABLED,
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_EMITTERS,
    CONF_FUEL_TYPE,
    CONF_GAS_COST_PER_THERM,
    CONF_NOMINAL_BTU,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRODUCER,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_PROPANE_COST_PER_GAL,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TEMP_SENSOR,
    CONF_TYPE,
)
from custom_components.hvac_fusion.sensor import (
    HvacFusionEconomicCrossoverTemperatureSensor,
    HvacFusionEstimatedCostRateSensor,
    HvacFusionEstimatedSavingsSensor,
    HvacFusionProducerSensor,
    _build_cost_sensors,
)
from homeassistant.const import (
    CONF_ID,
    CONF_NAME,
)
from homeassistant.core import HomeAssistant, State
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
                CONF_PROFILE: "generic/cold_climate_heat_pump.json",
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
                CONF_PROFILE: "generic/cold_climate_heat_pump.json",
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

    manager = hass.data[DOMAIN][entry.entry_id]
    await manager.async_evaluate()
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
                CONF_PROFILE: "generic/cold_climate_heat_pump.json",
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


@pytest.mark.asyncio
async def test_cost_matrix_estimates_and_sensors(hass: HomeAssistant) -> None:
    """Test hourly cost/savings matrix, HP lockout resistive fallback, and sensor defaults."""
    hass.states.async_set("sensor.outdoor_temp", "45.0")
    hass.states.async_set("sensor.room_temp", "67.0")

    conf = {
        CONF_NAME: "HVAC Fusion",
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.20,
            CONF_GAS_COST_PER_THERM: 2.00,
        },
        CONF_PRODUCERS: {
            "hp": {
                CONF_NAME: "Heat Pump",
                CONF_TYPE: "heat_pump",
                CONF_PROFILE: "generic/cold_climate_heat_pump.json",
            },
            "boiler": {
                CONF_NAME: "Boiler",
                CONF_TYPE: "boiler",
                CONF_FUEL_TYPE: "natural_gas",
                CONF_PROFILE: "generic/modulating_condensing_boiler.json",
            },
        },
        CONF_SPACES: [
            {
                CONF_ID: "living_room",
                CONF_NAME: "Living Room",
                CONF_TEMP_SENSOR: "sensor.room_temp",
                "floor_area_sqft": 400.0,
                "ceiling_height_ft": 8.0,
                "envelope_score": 5,
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "hp",
                        CONF_NOMINAL_BTU: 12000.0,
                    },
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "boiler",
                    },
                ],
            }
        ],
    }

    manager = HvacFusionManager(hass, conf, entry_id="test_entry")
    await manager.async_init()

    # Build cost sensors and verify enabled-by-default vs opt-in matrix
    sensors = _build_cost_sensors(manager)
    assert len(sensors) == 8
    enabled_default = [s for s in sensors if s.entity_registry_enabled_default]
    disabled_default = [s for s in sensors if not s.entity_registry_enabled_default]
    assert len(enabled_default) == 2
    assert len(disabled_default) == 6

    # Evaluate at mild temp (45°F): HP should be cheaper than gas boiler
    await manager.async_evaluate()
    est = manager.cost_estimates
    assert est["chosen_cost_per_hr"] is not None
    assert est["fossil_fuel_baseline_cost_per_hr"] is not None
    assert est["heat_pump_baseline_cost_per_hr"] is not None
    assert est["savings_vs_fossil_fuel_per_hr"] > 0.0
    assert est["total_heat_loss_btu_per_hr"] > 0.0

    # Simulate 30 minutes elapsed and evaluate at extreme cold (-30°F) where HP locks out
    manager._last_cost_eval_utc = datetime.now(timezone.utc) - timedelta(minutes=30)
    hass.states.async_set("sensor.outdoor_temp", "-30.0")
    await manager.async_evaluate()

    est_cold = manager.cost_estimates
    # At -30°F HP locks out: chosen uses boiler, HP baseline falls back to COP=1 resistive
    assert est_cold["heat_pump_baseline_cost_per_hr"] is not None
    assert est_cold["heat_pump_baseline_cost_per_hr"] > est_cold["chosen_cost_per_hr"]
    assert est_cold["savings_vs_heat_pump_per_hr"] > 0.0
    assert manager.cumulative_estimated_cost > 0.0
    assert manager.cumulative_heat_pump_baseline_cost > 0.0

    rate_sensor = next(
        s for s in sensors if isinstance(s, HvacFusionEstimatedCostRateSensor)
    )
    assert rate_sensor.native_value == est_cold["chosen_cost_per_hr"]
    assert (
        rate_sensor.extra_state_attributes["heat_pump_baseline_cost_per_hr"]
        == est_cold["heat_pump_baseline_cost_per_hr"]
    )


@pytest.mark.asyncio
async def test_estimated_savings_sensor_restore(hass: HomeAssistant) -> None:
    """Test HvacFusionEstimatedSavingsSensor restores cumulative totals on startup."""
    manager = MagicMock(spec=HvacFusionManager)
    manager.entry_id = "test_entry"
    manager.conf = {CONF_NAME: "HVAC Fusion"}
    manager.cost_estimates = {
        "savings_vs_fossil_fuel_per_hr": 0.15,
        "savings_vs_heat_pump_per_hr": 0.0,
    }
    manager.cumulative_savings_vs_fossil_fuel = 0.0
    manager.cumulative_savings_vs_heat_pump = 0.0
    manager.cumulative_estimated_cost = 0.0
    manager.cumulative_fossil_fuel_baseline_cost = 0.0
    manager.cumulative_heat_pump_baseline_cost = 0.0
    manager.register_sensor_entity = MagicMock()

    sensor = HvacFusionEstimatedSavingsSensor(manager)
    sensor.hass = hass
    sensor.async_write_ha_state = MagicMock()

    last_state = State(
        "sensor.hvac_fusion_estimated_savings_vs_fossil_fuel",
        "12.34",
        attributes={
            "savings_vs_heat_pump_total": 5.67,
            "cumulative_estimated_cost": 45.67,
            "cumulative_fossil_fuel_baseline_cost": 58.01,
            "cumulative_heat_pump_baseline_cost": 51.34,
        },
    )
    sensor.async_get_last_state = AsyncMock(return_value=last_state)

    await sensor.async_added_to_hass()

    assert manager.cumulative_savings_vs_fossil_fuel == 12.34
    assert manager.cumulative_savings_vs_heat_pump == 5.67
    assert manager.cumulative_estimated_cost == 45.67
    assert manager.cumulative_fossil_fuel_baseline_cost == 58.01
    assert manager.cumulative_heat_pump_baseline_cost == 51.34
    assert sensor.native_value == 12.34


@pytest.mark.asyncio
async def test_advisory_only_dry_run_all_sensors_populated(hass: HomeAssistant) -> None:
    """Test no-entity (advisory-only) dry-run setup populates crossover, cost, savings, and producer sensors."""
    hass.states.async_set("sensor.outdoor_temp", "32.0")
    hass.states.async_set("sensor.living_room_temp", "68.0")

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Dry Run Coordinator",
        data={
            CONF_CONTROL_ENABLED: False,
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {
                CONF_ELECTRIC_COST_PER_KWH: 0.25,
                CONF_GAS_COST_PER_THERM: 1.88,
            },
            CONF_PRODUCERS: {
                "hp": {
                    CONF_NAME: "Heat Pump",
                    CONF_TYPE: "heat_pump",
                    CONF_PROFILE: "generic/cold_climate_heat_pump.json",
                },
                "boiler": {
                    CONF_NAME: "Boiler",
                    CONF_TYPE: "boiler",
                    CONF_FUEL_TYPE: "natural_gas",
                    CONF_PROFILE: "generic/modulating_condensing_boiler.json",
                },
            },
            CONF_SPACES: [
                {
                    CONF_ID: "living_room",
                    CONF_NAME: "Living Room",
                    CONF_TEMP_SENSOR: "sensor.living_room_temp",
                    "floor_area_sqft": 400.0,
                    "ceiling_height_ft": 8.0,
                    "envelope_score": 5,
                    CONF_EMITTERS: [
                        {
                            CONF_ID: "lr_hp",
                            CONF_NAME: "LR Mini Split",
                            CONF_TYPE: "mini_split",
                            CONF_PRODUCER: "hp",
                            CONF_NOMINAL_BTU: 18000,
                        },
                        {
                            CONF_ID: "lr_rad",
                            CONF_NAME: "LR Radiator",
                            CONF_TYPE: "hydronic",
                            CONF_PRODUCER: "boiler",
                            CONF_NOMINAL_BTU: 15000,
                        },
                    ],
                }
            ],
        },
        options={},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    manager = hass.data[DOMAIN][entry.entry_id]
    await manager.async_evaluate()
    await hass.async_block_till_done()

    xover_state = hass.states.get("sensor.hvac_fusion_economic_crossover_temperature")
    assert xover_state is not None
    assert xover_state.state not in ("unknown", "unavailable")
    assert xover_state.attributes["control_enabled"] is False
    assert xover_state.attributes["advisory_only"] is True
    assert xover_state.attributes["break_even_cop"] is not None

    cost_state = hass.states.get("sensor.hvac_fusion_estimated_heating_cost_rate")
    assert cost_state is not None
    assert cost_state.state not in ("unknown", "unavailable")
    assert float(cost_state.state) > 0
    assert cost_state.attributes["total_heat_loss_btu_per_hr"] > 0
    assert cost_state.attributes["fossil_fuel_baseline_cost_per_hr"] is not None
    assert cost_state.attributes["heat_pump_baseline_cost_per_hr"] is not None

    savings_state = hass.states.get(
        "sensor.hvac_fusion_estimated_savings_vs_fossil_fuel"
    )
    assert savings_state is not None
    assert savings_state.state not in ("unknown", "unavailable")

    assert hass.states.get("sensor.hvac_fusion_heat_pump") is not None
    assert hass.states.get("sensor.hvac_fusion_boiler") is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_controllable_emitter_sets_advisory_only_false(
    hass: HomeAssistant,
) -> None:
    """Test crossover sensor reports advisory_only=False when an emitter has an entity_id."""
    hass.states.async_set("sensor.outdoor_temp", "32.0")
    hass.states.async_set("sensor.living_room_temp", "68.0")
    hass.states.async_set(
        "climate.lr_mini_split", "heat", {"current_temperature": 68.0}
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Autonomous Coordinator",
        data={
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {
                CONF_ELECTRIC_COST_PER_KWH: 0.25,
                CONF_GAS_COST_PER_THERM: 1.88,
            },
            CONF_PRODUCERS: {
                "hp": {
                    CONF_NAME: "Heat Pump",
                    CONF_TYPE: "heat_pump",
                    CONF_PROFILE: "generic/cold_climate_heat_pump.json",
                },
            },
            CONF_SPACES: [
                {
                    CONF_ID: "living_room",
                    CONF_NAME: "Living Room",
                    CONF_TEMP_SENSOR: "sensor.living_room_temp",
                    CONF_EMITTERS: [
                        {
                            CONF_ID: "lr_hp",
                            CONF_NAME: "LR Mini Split",
                            CONF_TYPE: "mini_split",
                            CONF_PRODUCER: "hp",
                            "entity_id": "climate.lr_mini_split",
                            CONF_NOMINAL_BTU: 18000,
                        },
                    ],
                }
            ],
        },
        options={},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    xover_state = hass.states.get("sensor.hvac_fusion_economic_crossover_temperature")
    assert xover_state is not None
    assert xover_state.attributes["advisory_only"] is False

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_cost_estimates_not_calling_overshoot_and_thermal_mass_pullup(
    hass: HomeAssistant,
) -> None:
    """Verify +2°F overshoot zeroes load, balance point zeroes load, and recovery pull-up adds mass load."""
    hass.states.async_set("sensor.outdoor_temp", "40.0")
    hass.states.async_set("sensor.room_temp", "64.0")

    conf = {
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.25,
            CONF_GAS_COST_PER_THERM: 1.88,
        },
        CONF_PRODUCERS: {
            "hp": {
                CONF_NAME: "Heat Pump",
                CONF_TYPE: "heat_pump",
                CONF_PROFILE: "generic/cold_climate_heat_pump.json",
            },
            "boiler": {
                CONF_NAME: "Boiler",
                CONF_TYPE: "boiler",
                CONF_FUEL_TYPE: "natural_gas",
                CONF_PROFILE: "generic/modulating_condensing_boiler.json",
            },
        },
        CONF_SPACES: [
            {
                CONF_ID: "loft",
                CONF_NAME: "Loft",
                CONF_TEMP_SENSOR: "sensor.room_temp",
                "floor_area_sqft": 500.0,
                "ceiling_height_ft": 8.0,
                "envelope_score": 5,
                "thermal_mass": 3,
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "hp",
                        CONF_NOMINAL_BTU: 12000.0,
                    },
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "boiler",
                    },
                ],
            }
        ],
    }

    manager = HvacFusionManager(hass, conf, entry_id="test_mass_entry")
    await manager.async_init()

    # 1. Baseline steady-state evaluation at 64°F (DEFAULT_HEAT_TO = 68°F, outdoor = 40°F)
    await manager.async_evaluate()
    base_btu = manager.cost_estimates["total_heat_loss_btu_per_hr"]
    base_cost = manager.cost_estimates["chosen_cost_per_hr"]
    # UA = 500 * 0.26 = 130, ΔT = 28°F -> gross 3640 - 500 internal gains = 3140 BTU/hr
    assert abs(base_btu - 3140.0) < 1.0
    assert base_cost > 0.0

    # 2. Simulate 15 minutes elapsed with room warming 64°F -> 66°F (active recovery pull-up)
    manager._last_cost_eval_utc = datetime.now(timezone.utc) - timedelta(minutes=15)
    hass.states.async_set("sensor.room_temp", "66.0")
    await manager.async_evaluate()
    pullup_btu = manager.cost_estimates["total_heat_loss_btu_per_hr"]
    pullup_cost = manager.cost_estimates["chosen_cost_per_hr"]
    assert pullup_btu > base_btu
    assert pullup_cost > base_cost

    # 3. Room exceeds heat_to (68°F) by >= 2.0°F (70°F, e.g. solar/stairwell heat) -> $0.00/hr
    manager._last_cost_eval_utc = datetime.now(timezone.utc) - timedelta(minutes=15)
    hass.states.async_set("sensor.room_temp", "70.0")
    await manager.async_evaluate()
    assert manager.cost_estimates["total_heat_loss_btu_per_hr"] == 0.0
    assert manager.cost_estimates["chosen_cost_per_hr"] == 0.0
    assert manager.cost_estimates["fossil_fuel_baseline_cost_per_hr"] == 0.0
    assert manager.cost_estimates["heat_pump_baseline_cost_per_hr"] == 0.0

    # 4. Mild outdoor temp above balance point (66°F outdoor vs 68°F setpoint) -> $0.00/hr
    manager._last_cost_eval_utc = datetime.now(timezone.utc) - timedelta(minutes=15)
    hass.states.async_set("sensor.room_temp", "68.0")
    hass.states.async_set("sensor.outdoor_temp", "66.0")
    await manager.async_evaluate()
    assert manager.cost_estimates["total_heat_loss_btu_per_hr"] == 0.0
    assert manager.cost_estimates["chosen_cost_per_hr"] == 0.0
