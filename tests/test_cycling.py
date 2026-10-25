"""Tests for setpoint-limit cycling and subsidiary actuation in HVAC Fusion."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from hvac_crossover import (
    HvacAction as LibHvacAction,
)
from hvac_crossover import (
    HvacMode as LibHvacMode,
)
from hvac_crossover import (
    SpaceDirective,
)

from custom_components.hvac_fusion import HvacFusionManager
from custom_components.hvac_fusion.const import (
    CONF_CYCLING_BAND,
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_EMITTERS,
    CONF_GAS_COST_PER_THERM,
    CONF_NOMINAL_BTU,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRODUCER,
    CONF_PRODUCERS,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TEMP_SENSOR,
    CONF_TYPE,
    CONF_ZONE_ID,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def basic_config():
    """Return standard test configuration with one space and two emitters (mini_split + hydronic)."""
    return {
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_CYCLING_BAND: 2.0,
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
                CONF_TEMP_SENSOR: "sensor.lr_temp",
                CONF_EMITTERS: [
                    {
                        CONF_TYPE: "mini_split",
                        CONF_PRODUCER: "heatpump",
                        CONF_ENTITY_ID: "climate.lr_minisplit",
                        CONF_NOMINAL_BTU: 12000.0,
                    },
                    {
                        CONF_TYPE: "hydronic",
                        CONF_PRODUCER: "boiler",
                        CONF_ENTITY_ID: "climate.lr_hydronic",
                        CONF_ZONE_ID: "z1",
                    },
                ],
            }
        ],
    }


def make_state(state="heat", attributes=None):
    """Helper to create a mock HA state object."""
    mock = MagicMock()
    mock.state = state
    mock.attributes = attributes or {}
    return mock


@pytest.mark.asyncio
async def test_normal_unclamped_operation(mock_hass, basic_config):
    """When target temp is within emitter limits, setpoint is applied directly without cycling."""
    manager = HvacFusionManager(mock_hass, basic_config)
    # Emitter entity map & setup
    ms_e_id = "living_room_heatpump_0"
    manager.emitter_entity_map[ms_e_id] = "climate.lr_minisplit"
    manager.emitter_types[ms_e_id] = "mini_split"

    # Mini split limits: min=61, max=86. Target=68 -> within limits
    mock_hass.states.get.return_value = make_state(
        "heat", {"min_temp": 61.0, "max_temp": 86.0, "temperature": 65.0}
    )

    plan = MagicMock()
    plan.producer_directives = {}
    plan.space_directives = {
        "living_room": SpaceDirective(
            space_id="living_room",
            action=LibHvacAction.HEATING,
            hvac_mode=LibHvacMode.HEAT,
            target_temp=68.0,
            active_delivery_unit_ids=[ms_e_id],
        )
    }

    await manager._dispatch_subsidiary_commands(plan, dry_run=False)

    # Should not be in cycling state
    assert ms_e_id not in manager._cycling_state

    # Should call set_temperature with 68.0
    mock_hass.services.async_call.assert_any_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.lr_minisplit", "temperature": 68.0},
        blocking=True,
    )


@pytest.mark.asyncio
async def test_mini_split_heat_clamped_cycles_on_when_cold(mock_hass, basic_config):
    """When target (e.g. 58) is clamped to min_temp (61), turn ON when space temp < ideal - band."""
    manager = HvacFusionManager(mock_hass, basic_config)
    ms_e_id = "living_room_heatpump_0"
    manager.emitter_entity_map[ms_e_id] = "climate.lr_minisplit"
    manager.emitter_types[ms_e_id] = "mini_split"

    # Space temp = 55 (below ideal 58 - band 2 = 56)
    def states_get(entity_id):
        if entity_id == "sensor.lr_temp":
            return make_state("55.0", {"current_temperature": 55.0})
        if entity_id == "climate.lr_minisplit":
            return make_state(
                "off", {"min_temp": 61.0, "max_temp": 86.0, "temperature": 61.0}
            )
        return None

    mock_hass.states.get.side_effect = states_get

    plan = MagicMock()
    plan.producer_directives = {}
    plan.space_directives = {
        "living_room": SpaceDirective(
            space_id="living_room",
            action=LibHvacAction.HEATING,
            hvac_mode=LibHvacMode.HEAT,
            target_temp=58.0,  # Clamped because min is 61.0
            active_delivery_unit_ids=[ms_e_id],
        )
    }

    await manager._dispatch_subsidiary_commands(plan, dry_run=False)

    # Cycling state should now be True (ON)
    assert manager._cycling_state.get(ms_e_id) is True

    # off_threshold = 58 + 2 = 60. min_temp = 61. cycle_on_temp = max(60, 61) = 61.0
    mock_hass.services.async_call.assert_any_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.lr_minisplit", "hvac_mode": "heat"},
        blocking=True,
    )
    mock_hass.services.async_call.assert_any_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.lr_minisplit", "temperature": 61.0},
        blocking=True,
    )


@pytest.mark.asyncio
async def test_mini_split_heat_clamped_cycles_off_when_warm(mock_hass, basic_config):
    """When cycling is active and space warms above off_threshold (ideal + band), turn OFF."""
    manager = HvacFusionManager(mock_hass, basic_config)
    ms_e_id = "living_room_heatpump_0"
    manager.emitter_entity_map[ms_e_id] = "climate.lr_minisplit"
    manager.emitter_types[ms_e_id] = "mini_split"
    # Pre-condition: currently in ON phase of cycling
    manager._cycling_state[ms_e_id] = True

    # Space temp = 60.5 (above ideal 58 + band 2 = 60.0)
    def states_get(entity_id):
        if entity_id == "sensor.lr_temp":
            return make_state("60.5", {"current_temperature": 60.5})
        if entity_id == "climate.lr_minisplit":
            return make_state(
                "heat", {"min_temp": 61.0, "max_temp": 86.0, "temperature": 61.0}
            )
        return None

    mock_hass.states.get.side_effect = states_get

    plan = MagicMock()
    plan.producer_directives = {}
    plan.space_directives = {
        "living_room": SpaceDirective(
            space_id="living_room",
            action=LibHvacAction.HEATING,
            hvac_mode=LibHvacMode.HEAT,
            target_temp=58.0,
            active_delivery_unit_ids=[ms_e_id],
        )
    }

    await manager._dispatch_subsidiary_commands(plan, dry_run=False)

    # Cycling state should transition to False (OFF)
    assert manager._cycling_state.get(ms_e_id) is False

    # Commanded to off
    mock_hass.services.async_call.assert_any_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.lr_minisplit", "hvac_mode": "off"},
        blocking=True,
    )


@pytest.mark.asyncio
async def test_cooling_clamped_cycles_correctly(mock_hass, basic_config):
    """Test symmetric cooling hysteresis: turn ON above ideal+band, OFF below ideal-band."""
    manager = HvacFusionManager(mock_hass, basic_config)
    ms_e_id = "living_room_heatpump_0"
    manager.emitter_entity_map[ms_e_id] = "climate.lr_minisplit"
    manager.emitter_types[ms_e_id] = "mini_split"

    # Ideal = 88, max_temp = 86 -> clamped to 86
    # on_threshold = 88 + 2 = 90. Space temp = 91 -> should turn ON
    def states_get(entity_id):
        if entity_id == "sensor.lr_temp":
            return make_state("91.0", {"current_temperature": 91.0})
        if entity_id == "climate.lr_minisplit":
            return make_state(
                "off", {"min_temp": 61.0, "max_temp": 86.0, "temperature": 86.0}
            )
        return None

    mock_hass.states.get.side_effect = states_get

    plan = MagicMock()
    plan.producer_directives = {}
    plan.space_directives = {
        "living_room": SpaceDirective(
            space_id="living_room",
            action=LibHvacAction.COOLING,
            hvac_mode=LibHvacMode.COOL,
            target_temp=88.0,
            active_delivery_unit_ids=[ms_e_id],
        )
    }

    await manager._dispatch_subsidiary_commands(plan, dry_run=False)
    assert manager._cycling_state.get(ms_e_id) is True

    # Now space cools down to 85.0 (below off_threshold 88 - 2 = 86)
    def states_get_cooled(entity_id):
        if entity_id == "sensor.lr_temp":
            return make_state("85.0", {"current_temperature": 85.0})
        if entity_id == "climate.lr_minisplit":
            return make_state(
                "cool", {"min_temp": 61.0, "max_temp": 86.0, "temperature": 86.0}
            )
        return None

    mock_hass.states.get.side_effect = states_get_cooled
    await manager._dispatch_subsidiary_commands(plan, dry_run=False)
    assert manager._cycling_state.get(ms_e_id) is False


@pytest.mark.asyncio
async def test_sensor_unavailable_fallback(mock_hass, basic_config):
    """If space temp sensor is unavailable, fall back gracefully to clamped setpoint."""
    manager = HvacFusionManager(mock_hass, basic_config)
    ms_e_id = "living_room_heatpump_0"
    manager.emitter_entity_map[ms_e_id] = "climate.lr_minisplit"
    manager.emitter_types[ms_e_id] = "mini_split"

    # Sensor unavailable
    def states_get(entity_id):
        if entity_id == "sensor.lr_temp":
            return make_state("unavailable")
        if entity_id == "climate.lr_minisplit":
            return make_state(
                "off", {"min_temp": 61.0, "max_temp": 86.0, "temperature": 65.0}
            )
        return None

    mock_hass.states.get.side_effect = states_get

    plan = MagicMock()
    plan.producer_directives = {}
    plan.space_directives = {
        "living_room": SpaceDirective(
            space_id="living_room",
            action=LibHvacAction.HEATING,
            hvac_mode=LibHvacMode.HEAT,
            target_temp=58.0,
            active_delivery_unit_ids=[ms_e_id],
        )
    }

    await manager._dispatch_subsidiary_commands(plan, dry_run=False)

    # Should not stay in cycling state
    assert ms_e_id not in manager._cycling_state
    # Direct clamped fallback call: min_temp is 61.0
    mock_hass.services.async_call.assert_any_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.lr_minisplit", "temperature": 61.0},
        blocking=True,
    )


@pytest.mark.asyncio
async def test_clearing_cycling_when_unclamped_or_inactive(mock_hass, basic_config):
    """Cycling state is removed once the emitter is no longer clamped or is switched off."""
    manager = HvacFusionManager(mock_hass, basic_config)
    ms_e_id = "living_room_heatpump_0"
    manager.emitter_entity_map[ms_e_id] = "climate.lr_minisplit"
    manager.emitter_types[ms_e_id] = "mini_split"
    manager._cycling_state[ms_e_id] = True

    mock_hass.states.get.return_value = make_state(
        "off", {"min_temp": 61.0, "max_temp": 86.0}
    )

    # Plan sets space to OFF
    plan = MagicMock()
    plan.producer_directives = {}
    plan.space_directives = {
        "living_room": SpaceDirective(
            space_id="living_room",
            action=LibHvacAction.OFF,
            hvac_mode=LibHvacMode.OFF,
            target_temp=None,
            active_delivery_unit_ids=[],
        )
    }

    await manager._dispatch_subsidiary_commands(plan, dry_run=False)
    assert ms_e_id not in manager._cycling_state
