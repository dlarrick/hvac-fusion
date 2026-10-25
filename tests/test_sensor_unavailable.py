"""Regression test: async_evaluate must not crash when a space temperature sensor
is unavailable (returns None) at startup or during a transient sensor dropout.

Before the fix, SpaceCondition(current_temp=None) was passed to the coordinator,
which then crashed with:
    TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'
inside RecoveryEngine.is_space_in_recovery -> ComfortRange.heat_deficit.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.hvac_fusion import HvacFusionManager
from custom_components.hvac_fusion.const import (
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
)


def _make_conf():
    return {
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
                CONF_TEMP_SENSOR: "sensor.living_room_temp",
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


def _make_manager(mock_hass):
    from hvac_crossover import CoordinatorConfig, DualFuelCoordinator, TariffSchedule

    manager = HvacFusionManager(mock_hass, _make_conf())
    manager.topology = manager._build_topology()
    manager.tariffs = TariffSchedule(
        gas_cost_per_therm=1.50, propane_cost_per_gal=0.0, elec_cost_per_kwh=0.25
    )
    manager.coordinator = DualFuelCoordinator(manager.topology, CoordinatorConfig())
    return manager


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.mark.asyncio
async def test_evaluate_does_not_crash_when_temp_sensor_unavailable(mock_hass) -> None:
    """Regression: async_evaluate must skip spaces whose temp sensor is unavailable."""
    manager = _make_manager(mock_hass)

    def mock_states_get(entity_id):
        if entity_id == "sensor.outdoor_temp":
            s = MagicMock()
            s.state = "35.0"
            s.attributes = {}
            return s
        s = MagicMock()
        s.state = "unavailable"
        s.attributes = {}
        return s

    mock_hass.states.get = mock_states_get

    # Must not raise
    await manager.async_evaluate()

    assert manager.last_plan is not None


@pytest.mark.asyncio
async def test_evaluate_includes_space_when_temp_available(mock_hass) -> None:
    """When temp sensor is available, the space should be included in evaluation."""
    manager = _make_manager(mock_hass)

    def mock_states_get(entity_id):
        s = MagicMock()
        if entity_id == "sensor.outdoor_temp":
            s.state = "25.0"
            s.attributes = {}
        elif entity_id == "sensor.living_room_temp":
            s.state = "62.0"
            s.attributes = {}
        else:
            s.state = "unavailable"
            s.attributes = {}
        return s

    mock_hass.states.get = mock_states_get

    await manager.async_evaluate()

    assert manager.last_plan is not None
    assert "living_room" in manager.last_plan.space_directives
