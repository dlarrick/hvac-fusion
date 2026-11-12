"""Tests for HVAC Fusion space comfort boost service and decay dynamics."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from custom_components.hvac_fusion import DOMAIN, HvacFusionManager
from custom_components.hvac_fusion.climate import HvacFusionSpaceClimate
from custom_components.hvac_fusion.const import (
    CONF_TEMP_SENSOR,
    DEFAULT_COOL_TO,
    DEFAULT_HEAT_TO,
)
from homeassistant.components.climate import HVACMode
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant, State


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.states = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


@pytest.fixture
def mock_manager(mock_hass):
    """Create a mock manager for climate entities."""
    manager = MagicMock(spec=HvacFusionManager)
    manager.hass = mock_hass
    manager.async_evaluate = AsyncMock()
    manager.get_space_current_temp.return_value = 68.0
    manager.get_space_window_open.return_value = False
    manager.is_schedule_locked.return_value = False
    manager.emitter_entity_map = {}
    return manager


@pytest.fixture
def space_climate(mock_manager):
    """Create a space climate entity with standard defaults."""
    space_conf = {
        CONF_ID: "living_room",
        CONF_NAME: "Living Room",
        CONF_TEMP_SENSOR: "sensor.living_room_temp",
    }
    entity = HvacFusionSpaceClimate(mock_manager, space_conf)
    entity.hass = mock_manager.hass
    entity.async_write_ha_state = MagicMock()
    return entity


@pytest.mark.asyncio
async def test_comfort_boost_basic(space_climate):
    """Test applying a basic too_cold comfort boost."""
    now = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)
    with patch("homeassistant.util.dt.utcnow", return_value=now):
        await space_climate.async_comfort_boost(
            feeling="too_cold", delta_f=2.0, duration_minutes=120, decay=True
        )

        assert space_climate.boost_active is True
        assert space_climate.boost_feeling == "too_cold"
        assert space_climate.boost_remaining_minutes == 120
        assert space_climate.boost_current_offset == 2.0
        assert space_climate.current_boost == 2.0

        # Setpoints shift up by 2.0°F
        assert space_climate.native_target_temperature_low == DEFAULT_HEAT_TO + 2.0
        assert space_climate.native_target_temperature_high == DEFAULT_COOL_TO + 2.0

        bounds = space_climate.get_comfort_bounds()
        assert bounds == (DEFAULT_HEAT_TO + 2.0, DEFAULT_COOL_TO + 2.0)

        # Only clean 'current_boost' is exposed in public attributes
        attrs = space_climate.extra_state_attributes
        assert attrs["current_boost"] == 2.0
        assert "boost_active" not in attrs
        assert "boost_start_time" not in attrs
        assert "boost_end_time" not in attrs

        # Detailed state is preserved in private extra_restore_state_data
        extra_data = space_climate.extra_restore_state_data
        assert extra_data is not None
        assert extra_data.delta_f == 2.0
        assert extra_data.start_time == now.isoformat()
        assert extra_data.end_time == (now + timedelta(minutes=120)).isoformat()


@pytest.mark.asyncio
async def test_comfort_boost_linear_decay(space_climate):
    """Test linear decay of comfort boost over time."""
    start_time = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)

    with patch("homeassistant.util.dt.utcnow", return_value=start_time):
        await space_climate.async_comfort_boost(
            feeling="too_cold", delta_f=2.0, duration_minutes=120, decay=True
        )

    # At t=30 min (25% elapsed, 75% remaining) -> 2.0 * 0.75 = 1.5°F
    t30 = start_time + timedelta(minutes=30)
    with patch("homeassistant.util.dt.utcnow", return_value=t30):
        assert space_climate.boost_active is True
        assert space_climate.boost_remaining_minutes == 90
        assert space_climate.boost_current_offset == 1.5

    # At t=60 min (50% elapsed, 50% remaining) -> 2.0 * 0.5 = 1.0°F
    t60 = start_time + timedelta(minutes=60)
    with patch("homeassistant.util.dt.utcnow", return_value=t60):
        assert space_climate.boost_active is True
        assert space_climate.boost_remaining_minutes == 60
        assert space_climate.boost_current_offset == 1.0

    # At t=120 min (100% elapsed) -> 0.0°F / expired
    t120 = start_time + timedelta(minutes=120)
    with patch("homeassistant.util.dt.utcnow", return_value=t120):
        assert space_climate.boost_active is False
        assert space_climate.boost_current_offset == 0.0
        assert space_climate.boost_remaining_minutes == 0

    # At t=130 min -> still expired
    t130 = start_time + timedelta(minutes=130)
    with patch("homeassistant.util.dt.utcnow", return_value=t130):
        assert space_climate.boost_active is False
        assert space_climate.boost_current_offset == 0.0


@pytest.mark.asyncio
async def test_comfort_boost_no_decay(space_climate):
    """Test step hold when decay=False."""
    start_time = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)

    with patch("homeassistant.util.dt.utcnow", return_value=start_time):
        await space_climate.async_comfort_boost(
            feeling="too_hot", delta_f=2.0, duration_minutes=60, decay=False
        )

    # Halfway through: still full -2.0°F
    t30 = start_time + timedelta(minutes=30)
    with patch("homeassistant.util.dt.utcnow", return_value=t30):
        assert space_climate.boost_active is True
        assert space_climate.boost_current_offset == -2.0
        assert space_climate.boost_remaining_minutes == 30

    # Expired: reverts to 0.0
    t70 = start_time + timedelta(minutes=70)
    with patch("homeassistant.util.dt.utcnow", return_value=t70):
        assert space_climate.boost_active is False
        assert space_climate.boost_current_offset == 0.0


@pytest.mark.asyncio
async def test_comfort_boost_stacking_and_cap(space_climate):
    """Test Option B repeated presses pile up with a ±5.0°F hard cap."""
    now = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)

    with patch("homeassistant.util.dt.utcnow", return_value=now):
        # 1st press: +2.0°F
        await space_climate.async_comfort_boost(feeling="too_cold", delta_f=2.0)
        assert space_climate.boost_current_offset == 2.0

        # 2nd press: +2.0°F -> 4.0°F
        await space_climate.async_comfort_boost(feeling="too_cold", delta_f=2.0)
        assert space_climate.boost_current_offset == 4.0

        # 3rd press: +2.0°F -> 6.0°F clamped to 5.0°F max cap!
        await space_climate.async_comfort_boost(feeling="too_cold", delta_f=2.0)
        assert space_climate.boost_current_offset == 5.0

        # Counter press: -2.0°F ("too_hot") -> 3.0°F
        await space_climate.async_comfort_boost(feeling="too_hot", delta_f=2.0)
        assert space_climate.boost_current_offset == 3.0

        # Counter press: -3.0°F -> 0.0°F -> clears boost!
        await space_climate.async_comfort_boost(feeling="too_hot", delta_f=3.0)
        assert space_climate.boost_active is False
        assert space_climate.boost_current_offset == 0.0


@pytest.mark.asyncio
async def test_clear_comfort_boost(space_climate):
    """Test explicitly clearing an active comfort boost."""
    now = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)

    with patch("homeassistant.util.dt.utcnow", return_value=now):
        await space_climate.async_comfort_boost(feeling="too_cold", delta_f=2.0)
        assert space_climate.boost_active is True

        await space_climate.async_clear_comfort_boost()
        assert space_climate.boost_active is False
        assert space_climate.boost_current_offset == 0.0
        assert space_climate.extra_state_attributes["current_boost"] == 0.0
        assert space_climate.extra_restore_state_data is None


@pytest.mark.asyncio
async def test_comfort_boost_preserved_across_preset_transition(space_climate):
    """Test that comfort boost stays active and offsets new baseline when presets change."""
    now = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)

    with patch("homeassistant.util.dt.utcnow", return_value=now):
        await space_climate.async_comfort_boost(feeling="too_cold", delta_f=2.0)

        # Baseline targets are changed (e.g. from schedule transition)
        space_climate._target_temp_low = 62.0
        space_climate._target_temp_high = 66.0

        # Target temperatures include the +2.0°F boost on top of new 62/66 baseline
        assert space_climate.native_target_temperature_low == 64.0
        assert space_climate.native_target_temperature_high == 68.0
        assert space_climate.get_comfort_bounds() == (64.0, 68.0)


@pytest.mark.asyncio
async def test_comfort_boost_survives_ha_restart_active(mock_manager):
    """Test that an active comfort boost successfully resumes at the decayed point across a restart."""
    from custom_components.hvac_fusion.climate import ComfortBoostExtraStoredData

    start_time = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=120)

    extra_data = ComfortBoostExtraStoredData(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        delta_f=2.0,
        duration_minutes=120,
        decay=True,
    )

    saved_state = State(
        entity_id="climate.living_room_space",
        state=HVACMode.HEAT_COOL,
        attributes={},
    )

    space_conf = {
        CONF_ID: "living_room",
        CONF_NAME: "Living Room",
        CONF_TEMP_SENSOR: "sensor.living_room_temp",
    }
    entity = HvacFusionSpaceClimate(mock_manager, space_conf)
    entity.hass = mock_manager.hass
    entity.async_write_ha_state = MagicMock()
    entity.async_get_last_extra_data = AsyncMock(return_value=extra_data)
    entity.async_get_last_state = AsyncMock(return_value=saved_state)

    # Restart happens at t=30 min (30 min after start, 90 min remaining)
    restart_time = start_time + timedelta(minutes=30)
    with patch("homeassistant.util.dt.utcnow", return_value=restart_time):
        await entity.async_added_to_hass()

        assert entity.boost_active is True
        assert entity.boost_remaining_minutes == 90
        # (90 / 120) * 2.0 = 1.5°F
        assert entity.boost_current_offset == 1.5
        assert entity.current_boost == 1.5
        assert entity.extra_state_attributes["current_boost"] == 1.5
        assert entity.native_target_temperature_low == DEFAULT_HEAT_TO + 1.5


@pytest.mark.asyncio
async def test_comfort_boost_survives_ha_restart_expired(mock_manager):
    """Test that an expired boost from a previous run cleanly initializes to inactive."""
    from custom_components.hvac_fusion.climate import ComfortBoostExtraStoredData

    start_time = datetime(2026, 11, 10, 20, 0, 0, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=120)

    extra_data = ComfortBoostExtraStoredData(
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        delta_f=2.0,
        duration_minutes=120,
        decay=True,
    )

    saved_state = State(
        entity_id="climate.living_room_space",
        state=HVACMode.HEAT_COOL,
        attributes={},
    )

    space_conf = {
        CONF_ID: "living_room",
        CONF_NAME: "Living Room",
        CONF_TEMP_SENSOR: "sensor.living_room_temp",
    }
    entity = HvacFusionSpaceClimate(mock_manager, space_conf)
    entity.hass = mock_manager.hass
    entity.async_write_ha_state = MagicMock()
    entity.async_get_last_extra_data = AsyncMock(return_value=extra_data)
    entity.async_get_last_state = AsyncMock(return_value=saved_state)

    # Restart happens at t=150 min (after boost expired)
    restart_time = start_time + timedelta(minutes=150)
    with patch("homeassistant.util.dt.utcnow", return_value=restart_time):
        await entity.async_added_to_hass()

        assert entity.boost_active is False
        assert entity.boost_current_offset == 0.0
        assert entity.current_boost == 0.0
        assert entity.extra_state_attributes["current_boost"] == 0.0
        assert entity.native_target_temperature_low == DEFAULT_HEAT_TO


@pytest.mark.asyncio
async def test_services_comfort_boost_routing(hass: HomeAssistant):
    """Test service registration and routing for comfort_boost and clear_comfort_boost."""
    from custom_components.hvac_fusion import async_register_services

    space_mock = MagicMock()
    space_mock.entity_id = "climate.living_room_space"
    space_mock.async_comfort_boost = AsyncMock()
    space_mock.async_clear_comfort_boost = AsyncMock()

    manager = MagicMock(spec=HvacFusionManager)
    manager.space_entities = {"living_room": space_mock}

    hass.data[DOMAIN] = {"test_entry": manager, "legacy_ref": manager}
    async_register_services(hass)

    # Call comfort_boost service
    await hass.services.async_call(
        DOMAIN,
        "comfort_boost",
        {
            "entity_id": "climate.living_room_space",
            "feeling": "too_cold",
            "delta_f": 2.5,
            "duration_minutes": 90,
            "decay": False,
        },
        blocking=True,
    )

    space_mock.async_comfort_boost.assert_awaited_once_with(
        feeling="too_cold",
        delta_f=2.5,
        duration_minutes=90,
        decay=False,
    )

    # Call clear_comfort_boost service
    await hass.services.async_call(
        DOMAIN,
        "clear_comfort_boost",
        {"entity_id": "climate.living_room_space"},
        blocking=True,
    )

    space_mock.async_clear_comfort_boost.assert_awaited_once()
