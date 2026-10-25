"""Foundational integration tests for HVAC Fusion."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import HVACAction
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME, CONF_ID

from custom_components.hvac_fusion import HvacFusionManager
from custom_components.hvac_fusion.const import (
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_TARIFFS,
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_GAS_COST_PER_THERM,
    CONF_PRODUCERS,
    CONF_SPACES,
    CONF_EMITTERS,
    CONF_TYPE,
    CONF_PRODUCER,
    CONF_NOMINAL_BTU,
)
from custom_components.hvac_fusion.climate import HvacFusionSpaceClimate
from hvac_crossover import (
    SpaceDirective,
    HvacMode as LibHvacMode,
    HvacAction as LibHvacAction,
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
