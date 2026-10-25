"""Foundational integration tests for HVAC Fusion."""

from unittest.mock import MagicMock, patch

import pytest

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
    SpaceDirective,
)

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
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TYPE,
)


def test_manager_build_topology():
    """Verify HvacFusionManager builds topology and tariffs from config."""
    hass = MagicMock(spec=HomeAssistant)
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
    hass = MagicMock()
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


@pytest.mark.asyncio
async def test_space_climate_state_restoration():
    """Verify that HvacFusionSpaceClimate restores active preset and setpoints on restart."""
    hass = MagicMock()
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
    with patch.object(
        entity, "async_get_last_state", return_value=mock_last_state
    ), patch.object(entity, "async_update_from_schedule") as mock_update_sched:
        await entity.async_added_to_hass()
        assert entity.preset_mode == "away"
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
    with patch.object(
        entity_manual, "async_get_last_state", return_value=mock_last_manual
    ), patch.object(
        entity_manual, "async_update_from_schedule"
    ) as mock_update_sched_manual:
        await entity_manual.async_added_to_hass()
        assert entity_manual.preset_mode == "manual"
        assert entity_manual.hvac_mode == "heat"
        assert entity_manual.target_temperature_low == 65.0
        # Schedule update should NOT be called for manual preset
        mock_update_sched_manual.assert_not_called()
