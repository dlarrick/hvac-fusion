"""Tests for HVAC Fusion config flow and options flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hvac_fusion.const import (
    CONF_CEILING_HEIGHT,
    CONF_CONTROL_ENABLED,
    CONF_CYCLING_BAND,
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_ELECTRIC_RATE_SENSOR,
    CONF_EMITTERS,
    CONF_EVALUATION_INTERVAL_MINUTES,
    CONF_FLOOR_AREA,
    CONF_FUEL_TYPE,
    CONF_GAS_COST_PER_THERM,
    CONF_HEAT_PUMP_SAFETY_BAND_F,
    CONF_NOMINAL_BTU,
    CONF_OFFSET,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRIORITY,
    CONF_PRODUCER,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_PROPANE_COST_PER_GAL,
    CONF_SHARED_BOILER_ROLE,
    CONF_SOLAR_EXPORT_ENTITY,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TEMP_SENSOR,
    CONF_TYPE,
    CONF_WINDOW_SENSOR,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_flow_user_init(hass: HomeAssistant) -> None:
    """Test that the user step displays form schema."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_flow_user_creates_entry(hass: HomeAssistant) -> None:
    """Test that submitting valid data creates the config entry."""
    with patch(
        "custom_components.hvac_fusion.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data={
                "name": "My HVAC Coordinator",
                CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temperature",
                CONF_ELECTRIC_COST_PER_KWH: 0.28,
                CONF_GAS_COST_PER_THERM: 1.75,
                CONF_PROPANE_COST_PER_GAL: 3.50,
                CONF_CONTROL_ENABLED: False,
            },
        )

        assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "My HVAC Coordinator"
        assert (
            result["data"][CONF_OUTDOOR_TEMPERATURE_ENTITY]
            == "sensor.outdoor_temperature"
        )
        assert result["data"][CONF_CONTROL_ENABLED] is False
        assert result["data"][CONF_TARIFFS][CONF_ELECTRIC_COST_PER_KWH] == 0.28
        assert result["data"][CONF_TARIFFS][CONF_GAS_COST_PER_THERM] == 1.75
        assert result["data"][CONF_TARIFFS][CONF_PROPANE_COST_PER_GAL] == 3.50

        await hass.async_block_till_done()
        mock_setup_entry.assert_called_once()


@pytest.mark.asyncio
async def test_options_flow_init_menu(hass: HomeAssistant) -> None:
    """Test that options flow initializes with the main menu."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_CONTROL_ENABLED: False,
            CONF_TARIFFS: {
                CONF_ELECTRIC_COST_PER_KWH: 0.25,
                CONF_GAS_COST_PER_THERM: 1.50,
                CONF_PROPANE_COST_PER_GAL: 3.00,
            },
            CONF_PRODUCERS: {},
            CONF_SPACES: [],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_global_settings(hass: HomeAssistant) -> None:
    """Test updating global sensors, tariffs and safety band in options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_CONTROL_ENABLED: False,
            CONF_TARIFFS: {
                CONF_ELECTRIC_COST_PER_KWH: 0.25,
                CONF_GAS_COST_PER_THERM: 1.50,
                CONF_PROPANE_COST_PER_GAL: 3.00,
            },
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "global_settings"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "global_settings"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.weather_outdoor_temp",
            CONF_SOLAR_EXPORT_ENTITY: "sensor.solar_export_power",
            CONF_ELECTRIC_COST_PER_KWH: 0.32,
            CONF_ELECTRIC_RATE_SENSOR: "sensor.live_electric_rate",
            CONF_GAS_COST_PER_THERM: 2.10,
            CONF_PROPANE_COST_PER_GAL: 3.80,
            CONF_HEAT_PUMP_SAFETY_BAND_F: 6.0,
        },
    )
    # Submission returns to main menu
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"

    # Finish flow and verify saved options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    saved = result["data"]
    assert saved[CONF_OUTDOOR_TEMPERATURE_ENTITY] == "sensor.weather_outdoor_temp"
    assert saved[CONF_SOLAR_EXPORT_ENTITY] == "sensor.solar_export_power"
    assert saved[CONF_HEAT_PUMP_SAFETY_BAND_F] == 6.0
    assert saved[CONF_TARIFFS][CONF_ELECTRIC_COST_PER_KWH] == 0.32
    assert saved[CONF_TARIFFS][CONF_ELECTRIC_RATE_SENSOR] == "sensor.live_electric_rate"
    assert saved[CONF_TARIFFS][CONF_GAS_COST_PER_THERM] == 2.10
    assert saved[CONF_TARIFFS][CONF_PROPANE_COST_PER_GAL] == 3.80


@pytest.mark.asyncio
async def test_options_flow_policies_menu(hass: HomeAssistant) -> None:
    """Test updating operational policies in options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_CONTROL_ENABLED: False,
            CONF_TARIFFS: {},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "policies_menu"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "policies_menu"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_CONTROL_ENABLED: True,
            CONF_CYCLING_BAND: 3.0,
            CONF_EVALUATION_INTERVAL_MINUTES: 10,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CONTROL_ENABLED] is True
    assert result["data"][CONF_CYCLING_BAND] == 3.0
    assert result["data"][CONF_EVALUATION_INTERVAL_MINUTES] == 10


@pytest.mark.asyncio
async def test_options_flow_producers_crud(hass: HomeAssistant) -> None:
    """Test adding, editing, and deleting a producer."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {},
            CONF_PRODUCERS: {},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "producers_menu"}
    )
    assert result["step_id"] == "producers_menu"

    # Select add
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    assert result["step_id"] == "producer_add"

    # Add producer
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ID: "hp_test",
            CONF_NAME: "Test Heat Pump",
            CONF_TYPE: "inverter_heat_pump",
            CONF_PROFILE: "mitsubishi/mxz_3c30nahz2.json",
            CONF_FUEL_TYPE: "natural_gas",
        },
    )
    assert result["step_id"] == "producers_menu"

    # Select the new producer to manage
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "hp_test"}
    )
    assert result["step_id"] == "producer_manage"

    # Choose edit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "edit"}
    )
    assert result["step_id"] == "producer_edit"

    # Update name
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Updated Heat Pump",
            CONF_TYPE: "inverter_heat_pump",
            CONF_PROFILE: "mitsubishi/mxz_3c30nahz2.json",
            CONF_FUEL_TYPE: "natural_gas",
        },
    )
    assert result["step_id"] == "producers_menu"

    # Select to delete
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "hp_test"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "delete"}
    )
    assert result["step_id"] == "producer_delete"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"confirm": True}
    )
    assert result["step_id"] == "producers_menu"

    # Save and verify empty producers
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert "hp_test" not in result["data"][CONF_PRODUCERS]


@pytest.mark.asyncio
async def test_options_flow_spaces_and_emitters(hass: HomeAssistant) -> None:
    """Test full space and emitter configuration workflow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {},
            CONF_PRODUCERS: {
                "hp1": {
                    CONF_NAME: "Heat Pump 1",
                    CONF_TYPE: "inverter_heat_pump",
                    CONF_PROFILE: "mitsubishi/mxz_3c30nahz2.json",
                }
            },
            CONF_SPACES: [],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "spaces_menu"}
    )
    assert result["step_id"] == "spaces_menu"

    # Select add space
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "add"}
    )
    assert result["step_id"] == "space_add"

    # Add space
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ID: "living_room",
            CONF_NAME: "Living Room",
            CONF_TEMP_SENSOR: "sensor.living_room_temp",
            CONF_WINDOW_SENSOR: "binary_sensor.lr_window",
            CONF_FLOOR_AREA: 450.0,
            CONF_CEILING_HEIGHT: 9.0,
            CONF_PRIORITY: 8,
            CONF_SHARED_BOILER_ROLE: "independent",
        },
    )
    assert result["step_id"] == "space_manage"

    # Navigate to emitters
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "emitters"}
    )
    assert result["step_id"] == "emitters_menu"

    # Add emitter
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "add"}
    )
    assert result["step_id"] == "emitter_add"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TYPE: "mini_split",
            CONF_PRODUCER: "hp1",
            CONF_ENTITY_ID: "climate.lr_ac",
            CONF_OFFSET: 1.5,
            CONF_NOMINAL_BTU: 12000.0,
        },
    )
    assert result["step_id"] == "emitters_menu"

    # Back to space manage -> back to spaces menu -> finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "back"}
    )
    assert result["step_id"] == "space_manage"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "back"}
    )
    assert result["step_id"] == "spaces_menu"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "back"}
    )
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    spaces = result["data"][CONF_SPACES]
    assert len(spaces) == 1
    assert spaces[0][CONF_ID] == "living_room"
    assert spaces[0][CONF_NAME] == "Living Room"
    assert len(spaces[0][CONF_EMITTERS]) == 1
    assert spaces[0][CONF_EMITTERS][0][CONF_ENTITY_ID] == "climate.lr_ac"
    assert spaces[0][CONF_EMITTERS][0][CONF_OFFSET] == 1.5
