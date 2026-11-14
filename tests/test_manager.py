"""Foundational integration tests for HVAC Fusion."""

from unittest.mock import MagicMock, patch

import pytest
from custom_components.hvac_fusion import HvacFusionManager
from custom_components.hvac_fusion.climate import HvacFusionSpaceClimate
from custom_components.hvac_fusion.const import (
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_EMITTERS,
    CONF_GAS_COST_PER_THERM,
    CONF_NOMINAL_BTU,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRESETS,
    CONF_PRODUCER,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_SHARED_BOILER_ROLE,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TYPE,
)
from homeassistant.components.climate import HVACAction
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant

from hvac_crossover import (
    HvacAction as LibHvacAction,
)
from hvac_crossover import (
    HvacMode as LibHvacMode,
)
from hvac_crossover import (
    SharedBoilerRole,
    SpaceDirective,
)


def test_manager_build_topology():
    """Verify HvacFusionManager builds topology and tariffs from config."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    conf = {
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.25,
            CONF_GAS_COST_PER_THERM: 1.50,
        },
        CONF_PRODUCERS: {
            "boiler": {
                CONF_TYPE: "modulating_boiler",
                CONF_NOMINAL_BTU: 100000.0,
            }
        },
        CONF_SPACES: [
            {
                CONF_ID: "living_room",
                CONF_NAME: "Living Room",
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "boiler",
                        CONF_ENTITY_ID: "climate.lr_unit",
                        CONF_NOMINAL_BTU: 12000.0,
                    }
                ],
            }
        ],
    }
    manager = HvacFusionManager(hass, conf)
    topology = manager._build_topology()

    assert len(topology.producers) == 1
    assert topology.producers[0].id == "boiler"
    assert len(topology.spaces) == 1
    assert topology.spaces[0].id == "living_room"
    assert "living_room_boiler_0" in manager.emitter_entity_map


def test_space_climate_entity_action_mapping():
    """Verify that HvacFusionSpaceClimate maps underlying emitter actions and shows cycling attrs."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    manager = MagicMock()
    manager.hass = hass
    manager.emitter_entity_map = {"living_room_hp_0": "climate.lr_mini"}
    manager._cycling_state = {"living_room_hp_0": True}
    manager.get_space_window_open.return_value = False

    space_conf = {
        CONF_ID: "living_room",
        CONF_NAME: "Living Room",
        CONF_EMITTERS: [],
    }

    entity = HvacFusionSpaceClimate(manager, space_conf)
    s_dir = SpaceDirective(
        space_id="living_room",
        action=LibHvacAction.HEATING,
        hvac_mode=LibHvacMode.HEAT,
        target_temp=68.0,
        active_delivery_unit_ids=["living_room_hp_0"],
    )
    entity.update_from_directive(s_dir, None)

    # Underlying physical climate is currently heating
    mock_state = MagicMock()
    mock_state.attributes = {"hvac_action": "heating"}
    hass.states.get.return_value = mock_state

    assert entity.hvac_action == HVACAction.HEATING
    assert "living_room_hp_0" in entity.extra_state_attributes["cycling_emitters"]
    assert entity.extra_state_attributes["phase"] == "plateau_maintenance"
    assert entity.extra_state_attributes["in_recovery"] is False


@pytest.mark.asyncio
async def test_space_climate_state_restoration():
    """Verify that HvacFusionSpaceClimate restores active preset and setpoints on restart."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    manager = MagicMock()
    manager.hass = hass

    space_conf = {
        CONF_ID: "living_room",
        CONF_NAME: "Living Room",
        CONF_PRESETS: {
            "home": "schedule.lr_home",
            "away": "schedule.lr_away",
        },
        CONF_EMITTERS: [],
    }

    # Case 1: Restoring 'away' preset instead of defaulting to first preset ('home')
    entity = HvacFusionSpaceClimate(manager, space_conf)
    assert entity.preset_mode == "home"  # Initial before restore

    mock_last_state = MagicMock()
    mock_last_state.state = "heat_cool"
    mock_last_state.attributes = {
        "preset_mode": "away",
        "target_temp_low": 62.0,
        "target_temp_high": 78.0,
    }
    with (
        patch.object(entity, "async_get_last_state", return_value=mock_last_state),
        patch.object(entity, "async_update_from_schedule") as mock_update_sched,
    ):
        await entity.async_added_to_hass()
        assert entity.preset_mode == "away"
        assert entity.hvac_mode == "heat_cool"
        assert entity.native_target_temperature_low == 62.0
        assert entity.native_target_temperature_high == 78.0
        assert entity.native_target_temperature is None
        mock_update_sched.assert_called_once()

    # Case 2: Restoring 'manual' mode preserves custom setpoints without schedule override
    entity_manual = HvacFusionSpaceClimate(manager, space_conf)
    mock_last_manual = MagicMock()
    mock_last_manual.state = "heat"
    mock_last_manual.attributes = {
        "preset_mode": "manual",
        "target_temp_low": 65.0,
        "target_temp_high": 75.0,
        "temperature": 65.0,
    }
    with (
        patch.object(
            entity_manual, "async_get_last_state", return_value=mock_last_manual
        ),
        patch.object(
            entity_manual, "async_update_from_schedule"
        ) as mock_update_sched_manual,
    ):
        await entity_manual.async_added_to_hass()
        assert entity_manual.preset_mode == "manual"
        assert entity_manual.hvac_mode == "heat"
        assert entity_manual.native_target_temperature == 65.0
        assert entity_manual.native_target_temperature_low is None
        assert entity_manual.native_target_temperature_high is None
        # Schedule update should NOT be called for manual preset
        mock_update_sched_manual.assert_not_called()


def test_tariffs_sensor_with_static_fallback():
    """Verify that dynamic rate entity takes precedence, falling back to static rate if unavailable."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    conf = {
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {
            CONF_ELECTRIC_COST_PER_KWH: 0.25,
            "electric_rate_sensor": "sensor.electric_rate",
            CONF_GAS_COST_PER_THERM: 1.50,
            "gas_rate_sensor": "input_number.gas_rate",
        },
        CONF_PRODUCERS: {},
        CONF_SPACES: [],
    }
    manager = HvacFusionManager(hass, conf)

    # 1. When sensors are available and numeric
    def mock_states_online(entity_id):
        s = MagicMock()
        if entity_id == "sensor.electric_rate":
            s.state = "0.38"
            return s
        if entity_id == "input_number.gas_rate":
            s.state = "1.95"
            return s
        return None

    hass.states.get = mock_states_online
    tariffs = manager.get_current_tariffs()
    assert tariffs.elec_cost_per_kwh == 0.38
    assert tariffs.gas_cost_per_therm == 1.95

    # 2. When electric sensor is unavailable and input_number is unknown -> fall back to static
    def mock_states_offline(entity_id):
        s = MagicMock()
        if entity_id == "sensor.electric_rate":
            s.state = "unavailable"
            return s
        if entity_id == "input_number.gas_rate":
            s.state = "unknown"
            return s
        return None

    hass.states.get = mock_states_offline
    tariffs_fallback = manager.get_current_tariffs()
    assert tariffs_fallback.elec_cost_per_kwh == 0.25
    assert tariffs_fallback.gas_cost_per_therm == 1.50

    # 3. When sensor returns None (not found) -> fall back to static
    hass.states.get = lambda _: None
    tariffs_missing = manager.get_current_tariffs()
    assert tariffs_missing.elec_cost_per_kwh == 0.25
    assert tariffs_missing.gas_cost_per_therm == 1.50


def test_manager_build_topology_shared_boiler_roles():
    """Verify primary and secondary shared boiler roles are parsed correctly."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    conf = {
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {CONF_ELECTRIC_COST_PER_KWH: 0.25, CONF_GAS_COST_PER_THERM: 1.50},
        CONF_PRODUCERS: {
            "alta": {CONF_TYPE: "modulating_boiler", CONF_NOMINAL_BTU: 100000.0}
        },
        CONF_SPACES: [
            {
                CONF_ID: "primary_br",
                CONF_NAME: "Primary Bedroom",
                CONF_SHARED_BOILER_ROLE: "primary",
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "alta",
                        CONF_ENTITY_ID: "climate.second_floor",
                        "zone_id": "z2",
                    }
                ],
            },
            {
                CONF_ID: "guest_room",
                CONF_NAME: "Guest Room",
                CONF_SHARED_BOILER_ROLE: "secondary",
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "alta",
                        CONF_ENTITY_ID: "climate.second_floor",
                        "zone_id": "z2",
                    }
                ],
            },
        ],
    }
    manager = HvacFusionManager(hass, conf)
    topology = manager._build_topology()

    spaces = {s.id: s for s in topology.spaces}
    assert spaces["primary_br"].shared_boiler_role == SharedBoilerRole.PRIMARY
    assert spaces["guest_room"].shared_boiler_role == SharedBoilerRole.SECONDARY


def test_space_climate_naming():
    """Verify that climate entities are named with 'Space' suffix without duplication."""
    hass = MagicMock(spec=HomeAssistant)
    manager = MagicMock()
    manager.hass = hass

    # 1. Standard name gets 'Space' appended
    entity1 = HvacFusionSpaceClimate(
        manager,
        {CONF_ID: "living_room", CONF_NAME: "Living Room", CONF_EMITTERS: []},
    )
    assert entity1.name == "Living Room Space"
    assert entity1.unique_id == "hvac_fusion_living_room_space"

    # 2. Name already ending with 'space' does not get duplicate suffix
    entity2 = HvacFusionSpaceClimate(
        manager,
        {CONF_ID: "office_space", CONF_NAME: "Office Space", CONF_EMITTERS: []},
    )
    assert entity2.name == "Office Space"
    assert entity2.unique_id == "hvac_fusion_office_space_space"


def test_boiler_capacity_and_min_fire():
    """Verify boiler turndown ratio computes min_fire_btu from boiler nominal_btu."""
    from hvac_crossover.models.producers import ModulatingBoilerProducer

    hass = MagicMock(spec=HomeAssistant)
    conf = {
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {CONF_GAS_COST_PER_THERM: 1.50},
        CONF_PRODUCERS: {
            "boiler1": {
                CONF_TYPE: "modulating_boiler",
                CONF_PROFILE: "generic/modulating_condensing_boiler.json",
                CONF_NOMINAL_BTU: 120000.0,
            }
        },
        CONF_SPACES: [
            {
                CONF_ID: "living_room",
                CONF_NAME: "Living Room",
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "boiler1",
                        CONF_ENTITY_ID: "switch.lr_valve",
                    }
                ],
            },
        ],
    }
    manager = HvacFusionManager(hass, conf)
    topology = manager._build_topology()
    boiler = topology.producers[0]
    assert isinstance(boiler, ModulatingBoilerProducer)
    assert boiler.nominal_btu == 120000.0
    assert boiler.turndown_ratio == 4.0
    # Boiler physical min fire: 120,000 / 4.0 = 30,000 BTU
    assert boiler.min_fire_btu == 30000.0
    # Hydronic emitter does not have nominal_btu
    emitter = topology.spaces[0].emitters[0]
    assert not hasattr(emitter, "nominal_btu")


def test_heat_pump_capacity_and_derating():
    """Verify heat pump outdoor unit nominal_btu config and derate curve scaling."""
    from hvac_crossover.models.producers import InverterHeatPumpProducer

    hass = MagicMock(spec=HomeAssistant)
    conf = {
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {CONF_ELECTRIC_COST_PER_KWH: 0.25},
        CONF_PRODUCERS: {
            "hp1": {
                CONF_TYPE: "heat_pump",
                CONF_PROFILE: "generic/cold_climate_heat_pump.json",
                CONF_NOMINAL_BTU: 36000.0,
            }
        },
        CONF_SPACES: [
            {
                CONF_ID: "living_room",
                CONF_NAME: "Living Room",
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "hp1",
                        CONF_ENTITY_ID: "climate.lr_minisplit",
                        CONF_NOMINAL_BTU: 18000.0,
                    }
                ],
            },
        ],
    }
    manager = HvacFusionManager(hass, conf)
    topology = manager._build_topology()
    hp = topology.producers[0]
    assert isinstance(hp, InverterHeatPumpProducer)
    assert hp.nominal_btu == 36000.0
    assert hp.max_capacity_at(47.0) == 36000.0
    assert hp.max_capacity_at(17.0) == 27000.0  # 75% derate at 17°F
    assert hp.max_capacity_at(-4.0) == 18000.0  # 50% derate at -4°F
    assert hp.max_capacity_at(-10.0) == 0.0  # Below min operational temp
    # Mini-split head emitter retains its own head rating
    emitter = topology.spaces[0].emitters[0]
    assert emitter.nominal_btu == 18000.0


def test_space_climate_hvac_action_deadband_buffer_fallback():
    """Verify fallback hvac_action applies 0.5°F maintenance buffer when physical entity cannot report action."""
    from homeassistant.components.climate import HVACMode

    hass = MagicMock()
    manager = MagicMock(spec=HvacFusionManager)
    manager.hass = hass
    manager.emitter_entity_map = {"emitter1": "climate.kumo_unit"}

    # Mock underlying state: state exists, but has NO hvac_action attribute (like hass-kumo)
    underlying_state = MagicMock()
    underlying_state.attributes = {}  # No hvac_action!
    hass.states.get.return_value = underlying_state

    space_conf = {CONF_ID: "living_room", CONF_NAME: "Living Room"}
    entity = HvacFusionSpaceClimate(manager, space_conf)
    entity._active_delivery_units = ["emitter1"]

    # 1. Heating mode with heat_to = 66.0
    entity._attr_hvac_mode = HVACMode.HEAT
    entity.get_comfort_bounds = MagicMock(return_value=(66.0, None))

    # At 66.2°F (< 66.0 + 0.5): plateau maintenance -> HEATING
    manager.get_space_current_temp.return_value = 66.2
    assert entity.hvac_action == HVACAction.HEATING

    # At 66.5°F (>= 66.0 + 0.5): satisfied inside deadband -> IDLE
    manager.get_space_current_temp.return_value = 66.5
    assert entity.hvac_action == HVACAction.IDLE

    # 2. Cooling mode with cool_to = 77.0
    entity._attr_hvac_mode = HVACMode.COOL
    entity.get_comfort_bounds = MagicMock(return_value=(None, 77.0))

    # At 76.8°F (> 77.0 - 0.5): plateau maintenance -> COOLING
    manager.get_space_current_temp.return_value = 76.8
    assert entity.hvac_action == HVACAction.COOLING

    # At 76.5°F (<= 77.0 - 0.5): satisfied inside deadband -> IDLE
    manager.get_space_current_temp.return_value = 76.5
    assert entity.hvac_action == HVACAction.IDLE


def test_space_climate_economic_crossover_temp_attribute():
    """Verify HvacFusionSpaceClimate exposes per-space economic_crossover_temp from diagnostics."""
    hass = MagicMock(spec=HomeAssistant)
    manager = MagicMock(spec=HvacFusionManager)
    manager.hass = hass
    manager.coordinator = None
    manager.get_space_current_temp.return_value = 68.0
    manager.get_space_window_open.return_value = False
    manager.is_schedule_locked.return_value = False

    plan = MagicMock()
    plan.diagnostics = MagicMock()
    plan.diagnostics.space_crossover_temps = {"living_room": 32.3}
    manager.last_plan = plan

    space_conf = {CONF_ID: "living_room", CONF_NAME: "Living Room"}
    entity = HvacFusionSpaceClimate(manager, space_conf)
    assert entity.extra_state_attributes["economic_crossover_temp"] == 32.3

    # Space without dual-fuel crossover returns None
    other_entity = HvacFusionSpaceClimate(
        manager, {CONF_ID: "guest_room", CONF_NAME: "Guest Room"}
    )
    assert other_entity.extra_state_attributes["economic_crossover_temp"] is None


def test_build_topology_envelope_score_and_thermal_mass():
    """Verify _build_topology propagates envelope_score and thermal_mass into Space."""
    hass = MagicMock(spec=HomeAssistant)
    conf = {
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {},
        CONF_PRODUCERS: {},
        CONF_SPACES: [
            {
                CONF_ID: "passive_room",
                CONF_NAME: "Passive Room",
                "floor_area_sqft": 100.0,
                "ceiling_height_ft": 10.0,
                "envelope_score": 10,
                "thermal_mass": 5,
                CONF_EMITTERS: [],
            },
        ],
    }
    manager = HvacFusionManager(hass, conf)
    topology = manager._build_topology()
    space = topology.spaces[0]
    assert space.envelope_score == 10.0
    assert space.thermal_mass == 5
    assert abs(space.ua_factor - 15.0) < 0.01
    assert abs(space.thermal_capacitance_btu_per_f - (1000.0 * 0.018 * 24.0)) < 0.01
