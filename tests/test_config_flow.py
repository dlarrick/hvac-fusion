"""Tests for HVAC Fusion config flow and options flow."""

from unittest.mock import patch

import pytest
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
    CONF_GAS_RATE_SENSOR,
    CONF_HEAT_PUMP_SAFETY_BAND_F,
    CONF_NOMINAL_BTU,
    CONF_OFFSET,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRESETS,
    CONF_PRIORITY,
    CONF_PRODUCER,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_PROPANE_COST_PER_GAL,
    CONF_PROPANE_RATE_SENSOR,
    CONF_SHARED_BOILER_ROLE,
    CONF_SOLAR_EXPORT_ENTITY,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TEMP_SENSOR,
    CONF_TYPE,
    CONF_WINDOW_SENSOR,
    CONF_ZONE_ID,
    DOMAIN,
)
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from pytest_homeassistant.common import MockConfigEntry


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
                CONF_SOLAR_EXPORT_ENTITY: "sensor.solar_export_power",
                CONF_CONTROL_ENABLED: False,
            },
        )

        assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
        assert result["title"] == "My HVAC Coordinator"
        assert (
            result["data"][CONF_OUTDOOR_TEMPERATURE_ENTITY]
            == "sensor.outdoor_temperature"
        )
        assert result["data"][CONF_SOLAR_EXPORT_ENTITY] == "sensor.solar_export_power"
        assert result["data"][CONF_CONTROL_ENABLED] is False
        assert result["data"][CONF_TARIFFS] == {}
        assert result["data"][CONF_PRODUCERS] == {}
        assert result["data"][CONF_SPACES] == []

        await hass.async_block_till_done()
        mock_setup_entry.assert_called_once()


@pytest.mark.asyncio
async def test_flow_user_single_instance_abort(hass: HomeAssistant) -> None:
    """Test that starting config flow aborts if an instance is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {},
            CONF_PRODUCERS: {},
            CONF_SPACES: [],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


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
    """Test updating environmental sensors in options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_CONTROL_ENABLED: False,
            CONF_TARIFFS: {
                CONF_ELECTRIC_COST_PER_KWH: 0.25,
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
        },
    )
    # Submission returns to main menu
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"

    # Finish flow and verify saved options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    saved = result["data"]
    assert saved[CONF_OUTDOOR_TEMPERATURE_ENTITY] == "sensor.weather_outdoor_temp"
    assert saved[CONF_SOLAR_EXPORT_ENTITY] == "sensor.solar_export_power"


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
            "policies_section": {
                CONF_CONTROL_ENABLED: True,
                CONF_CYCLING_BAND: 3.0,
                CONF_EVALUATION_INTERVAL_MINUTES: 10,
            },
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CONTROL_ENABLED] is True
    assert result["data"][CONF_CYCLING_BAND] == 3.0
    assert result["data"][CONF_EVALUATION_INTERVAL_MINUTES] == 10


@pytest.mark.asyncio
async def test_options_flow_policies_menu_conditional_sections(
    hass: HomeAssistant,
) -> None:
    """Test that policies menu dynamically includes sections based on producers."""
    # 1. With HP and Propane boiler: electricity, propane, limits, and policies sections should be present
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_PRODUCERS: {
                "hp1": {
                    CONF_NAME: "Heat Pump",
                    CONF_TYPE: "inverter_heat_pump",
                },
                "boiler1": {
                    CONF_NAME: "Propane Boiler",
                    CONF_TYPE: "modulating_boiler",
                    CONF_FUEL_TYPE: "propane",
                },
            },
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

    schema_keys = [str(k) for k in result["data_schema"].schema]
    assert any("electricity_section" in k for k in schema_keys)
    assert any("propane_section" in k for k in schema_keys)
    assert any("limits_section" in k for k in schema_keys)
    assert any("policies_section" in k for k in schema_keys)
    assert not any("gas_section" in k for k in schema_keys)

    # Verify tariffs default to blank (suggested_value is None, no prefilled static constant)
    elec_section_val = next(
        val
        for key, val in result["data_schema"].schema.items()
        if "electricity_section" in str(key)
    )
    elec_cost_key = next(
        k
        for k in elec_section_val.schema.schema
        if str(k) == CONF_ELECTRIC_COST_PER_KWH
    )
    assert elec_cost_key.description.get("suggested_value") is None

    # Configure tariffs and limits with fractional-cent rates
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "electricity_section": {
                CONF_ELECTRIC_COST_PER_KWH: 0.25077,
                CONF_ELECTRIC_RATE_SENSOR: "sensor.live_electric_rate",
            },
            "propane_section": {
                CONF_PROPANE_COST_PER_GAL: 3.8542,
                CONF_PROPANE_RATE_SENSOR: "sensor.propane_sensor",
            },
            "limits_section": {
                CONF_HEAT_PUMP_SAFETY_BAND_F: 5.5,
            },
            "policies_section": {
                CONF_CONTROL_ENABLED: True,
                CONF_CYCLING_BAND: 2.5,
                CONF_EVALUATION_INTERVAL_MINUTES: 15,
            },
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    saved = result["data"]
    assert saved[CONF_TARIFFS][CONF_ELECTRIC_COST_PER_KWH] == 0.25077
    assert saved[CONF_TARIFFS][CONF_ELECTRIC_RATE_SENSOR] == "sensor.live_electric_rate"
    assert saved[CONF_TARIFFS][CONF_PROPANE_COST_PER_GAL] == 3.8542
    assert saved[CONF_TARIFFS][CONF_PROPANE_RATE_SENSOR] == "sensor.propane_sensor"
    assert saved[CONF_HEAT_PUMP_SAFETY_BAND_F] == 5.5
    assert saved[CONF_CONTROL_ENABLED] is True
    assert saved[CONF_CYCLING_BAND] == 2.5
    assert saved[CONF_EVALUATION_INTERVAL_MINUTES] == 15

    # 2. Gas boiler only: gas and policies sections present, electricity/propane/limits absent
    entry_gas = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion Gas",
        data={
            CONF_NAME: "HVAC Fusion Gas",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_PRODUCERS: {
                "boiler_gas": {
                    CONF_NAME: "Gas Boiler",
                    CONF_TYPE: "modulating_boiler",
                    CONF_FUEL_TYPE: "natural_gas",
                },
            },
            CONF_TARIFFS: {},
        },
    )
    entry_gas.add_to_hass(hass)

    result2 = await hass.config_entries.options.async_init(entry_gas.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {"next_step_id": "policies_menu"}
    )
    assert result2["type"] is data_entry_flow.FlowResultType.FORM
    assert result2["step_id"] == "policies_menu"

    schema_keys_gas = [str(k) for k in result2["data_schema"].schema]
    assert any("gas_section" in k for k in schema_keys_gas)
    assert any("policies_section" in k for k in schema_keys_gas)
    assert not any("electricity_section" in k for k in schema_keys_gas)
    assert not any("propane_section" in k for k in schema_keys_gas)
    assert not any("limits_section" in k for k in schema_keys_gas)

    result2 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        {
            "gas_section": {
                CONF_GAS_COST_PER_THERM: 1.85,
                CONF_GAS_RATE_SENSOR: "sensor.gas_rate",
            },
            "policies_section": {
                CONF_CONTROL_ENABLED: False,
            },
        },
    )
    assert result2["type"] is data_entry_flow.FlowResultType.MENU
    result2 = await hass.config_entries.options.async_configure(
        result2["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()
    assert result2["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    saved_gas = result2["data"]
    assert saved_gas[CONF_TARIFFS][CONF_GAS_COST_PER_THERM] == 1.85
    assert saved_gas[CONF_TARIFFS][CONF_GAS_RATE_SENSOR] == "sensor.gas_rate"
    assert saved_gas[CONF_CONTROL_ENABLED] is False


@pytest.mark.asyncio
async def test_options_flow_producers_crud(hass: HomeAssistant) -> None:
    """Test adding, editing, and deleting a producer."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {
                CONF_ELECTRIC_COST_PER_KWH: 0.25,
                CONF_GAS_COST_PER_THERM: 1.50,
            },
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
            CONF_TYPE: "heat_pump",
            "heat_pump_profile": "mitsubishi/mxz_xcxxnahz2.json",
            CONF_NOMINAL_BTU: 36000.0,
        },
    )
    assert result["step_id"] == "producers_menu"

    # Select the new producer to manage -> goes directly to producer_edit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "hp_test"}
    )
    assert result["step_id"] == "producer_edit"
    nom_field = next(
        k
        for k in result["data_schema"].schema
        if getattr(k, "schema", None) == CONF_NOMINAL_BTU
    )
    assert nom_field.default() == 36000.0

    # Update name
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Updated Heat Pump",
            CONF_TYPE: "heat_pump",
            "heat_pump_profile": "mitsubishi/mxz_xcxxnahz2.json",
        },
    )
    assert result["step_id"] == "producers_menu"

    # Select to delete via delete_producer toggle
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "hp_test"}
    )
    assert result["step_id"] == "producer_edit"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Updated Heat Pump",
            CONF_TYPE: "heat_pump",
            "heat_pump_profile": "mitsubishi/mxz_xcxxnahz2.json",
            "delete_producer": True,
        },
    )
    assert result["step_id"] == "producers_menu"

    # Save and verify empty producers
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()
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
                    CONF_PROFILE: "mitsubishi/mxz_xcxxnahz2.json",
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
            "hp_emitter_producer": "hp1",
            CONF_ENTITY_ID: "climate.lr_ac",
            CONF_OFFSET: 1.5,
            CONF_NOMINAL_BTU: 12000.0,
        },
    )
    assert result["step_id"] == "emitters_menu"

    # Edit the emitter directly from emitters_menu
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "0"}
    )
    assert result["step_id"] == "emitter_edit"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TYPE: "mini_split",
            "hp_emitter_producer": "hp1",
            CONF_ENTITY_ID: "climate.lr_ac",
            CONF_OFFSET: 2.0,
            CONF_NOMINAL_BTU: 12000.0,
        },
    )
    assert result["step_id"] == "emitters_menu"

    # Add a second emitter, then delete it via delete_emitter toggle
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TYPE: "mini_split",
            "hp_emitter_producer": "hp1",
            CONF_ENTITY_ID: "climate.spare_ac",
            CONF_OFFSET: 0.0,
            CONF_NOMINAL_BTU: 9000.0,
        },
    )
    assert result["step_id"] == "emitters_menu"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "1"}
    )
    assert result["step_id"] == "emitter_edit"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TYPE: "mini_split",
            "hp_emitter_producer": "hp1",
            CONF_ENTITY_ID: "climate.spare_ac",
            "delete_emitter": True,
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
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    spaces = result["data"][CONF_SPACES]
    assert len(spaces) == 1
    assert spaces[0][CONF_ID] == "living_room"
    assert spaces[0][CONF_NAME] == "Living Room"
    assert spaces[0]["envelope_score"] == 5
    assert spaces[0]["thermal_mass"] == 3
    assert len(spaces[0][CONF_EMITTERS]) == 1
    assert spaces[0][CONF_EMITTERS][0][CONF_ENTITY_ID] == "climate.lr_ac"
    assert spaces[0][CONF_EMITTERS][0][CONF_OFFSET] == 2.0


@pytest.mark.asyncio
async def test_options_flow_space_schedule_presets(hass: HomeAssistant) -> None:
    """Test adding, editing, and deleting schedule presets on a space."""
    hass.states.async_set(
        "schedule.lr_day",
        "on",
        {"friendly_name": "Daytime Schedule"},
    )
    hass.states.async_set(
        "schedule.lr_night",
        "off",
        {},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {},
            CONF_PRODUCERS: {},
            CONF_SPACES: [
                {
                    CONF_ID: "living_room",
                    CONF_NAME: "Living Room",
                    CONF_TEMP_SENSOR: "sensor.living_room_temp",
                    CONF_PRESETS: {},
                    CONF_EMITTERS: [],
                }
            ],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "spaces_menu"}
    )
    assert result["step_id"] == "spaces_menu"

    # Select living_room space
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "living_room"}
    )
    assert result["step_id"] == "space_manage"

    # Select manage presets
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "presets"}
    )
    assert result["step_id"] == "presets_menu"

    # Add a preset without custom name (should derive from friendly_name)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"preset_action": "add"}
    )
    assert result["step_id"] == "preset_add"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"schedule_entity": "schedule.lr_day"},
    )
    assert result["step_id"] == "presets_menu"

    # Add a second preset with custom name
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"preset_action": "add"}
    )
    assert result["step_id"] == "preset_add"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "schedule_entity": "schedule.lr_night",
            "custom_name_toggle": True,
            "preset_name": "Night Mode",
        },
    )
    assert result["step_id"] == "presets_menu"

    # Select Daytime Schedule and delete it via delete_preset toggle
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"preset_action": "Daytime Schedule"}
    )
    assert result["step_id"] == "preset_edit"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"schedule_entity": "schedule.lr_day", "delete_preset": True},
    )
    assert result["step_id"] == "presets_menu"

    # Exit back to spaces_menu -> init -> finish
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"preset_action": "back"}
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
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    spaces = result["data"][CONF_SPACES]
    assert len(spaces) == 1
    assert CONF_PRESETS in spaces[0]
    assert "Night Mode" in spaces[0][CONF_PRESETS]
    assert spaces[0][CONF_PRESETS]["Night Mode"] == "schedule.lr_night"
    assert "Daytime Schedule" not in spaces[0][CONF_PRESETS]


@pytest.mark.asyncio
async def test_options_flow_inline_primary_emitter(hass: HomeAssistant) -> None:
    """Test creating a space with inline primary emitter configured in one step."""
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
                    CONF_PROFILE: None,
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

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "add"}
    )
    assert result["step_id"] == "space_add"

    # Add space and primary emitter in one step (omitting CONF_ID to test auto-slugging)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Master Bedroom",
            CONF_TEMP_SENSOR: "sensor.bedroom_temp",
            "configure_primary_emitter": True,
            "emitter_type": "mini_split",
            "hp_emitter_producer": "hp1",
            "emitter_entity_id": "climate.bedroom_ac",
            "emitter_nominal_btu": 9000.0,
        },
    )
    assert result["step_id"] == "space_manage"

    # Finish and verify
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
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    spaces = result["data"][CONF_SPACES]
    assert len(spaces) == 1
    assert spaces[0][CONF_ID] == "master_bedroom"
    assert spaces[0][CONF_NAME] == "Master Bedroom"
    assert len(spaces[0][CONF_EMITTERS]) == 1
    emitter = spaces[0][CONF_EMITTERS][0]
    assert emitter[CONF_TYPE] == "mini_split"
    assert emitter[CONF_PRODUCER] == "hp1"
    assert emitter[CONF_ENTITY_ID] == "climate.bedroom_ac"
    assert emitter[CONF_NOMINAL_BTU] == 9000.0


@pytest.mark.asyncio
async def test_options_flow_space_auto_slug_and_hydronic_primary_emitter(
    hass: HomeAssistant,
) -> None:
    """Test space ID auto-slug collision handling and hydronic primary emitter configuration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {},
            CONF_PRODUCERS: {
                "boiler1": {
                    CONF_NAME: "Main Boiler",
                    CONF_TYPE: "boiler",
                    CONF_PROFILE: "burnham/alpine.json",
                }
            },
            CONF_SPACES: [
                {
                    CONF_ID: "living_room",
                    CONF_NAME: "Living Room",
                    CONF_TEMP_SENSOR: "sensor.existing_lr",
                    CONF_PRESETS: {},
                    CONF_EMITTERS: [],
                }
            ],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "spaces_menu"}
    )
    assert result["step_id"] == "spaces_menu"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "add"}
    )
    assert result["step_id"] == "space_add"

    # Add second space named "Living Room" (should disambiguate to living_room_2) with hydronic emitter
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room",
            CONF_TEMP_SENSOR: "sensor.new_lr_temp",
            "configure_primary_emitter": True,
            "emitter_type": "hydronic",
            "boiler_emitter_producer": "boiler1",
            "emitter_entity_id": "switch.lr_radiator_valve",
            "emitter_zone_id": "z2",
        },
    )
    assert result["step_id"] == "space_manage"

    # Finish and verify
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    spaces = result["data"][CONF_SPACES]
    assert len(spaces) == 2
    assert spaces[0][CONF_ID] == "living_room"
    assert spaces[1][CONF_ID] == "living_room_2"
    assert spaces[1][CONF_NAME] == "Living Room"
    assert len(spaces[1][CONF_EMITTERS]) == 1
    emitter = spaces[1][CONF_EMITTERS][0]
    assert emitter[CONF_TYPE] == "hydronic"
    assert emitter[CONF_PRODUCER] == "boiler1"
    assert emitter[CONF_ENTITY_ID] == "switch.lr_radiator_valve"
    assert emitter[CONF_ZONE_ID] == "z2"


@pytest.mark.asyncio
async def test_options_flow_conditional_producer_and_emitter_fields(
    hass: HomeAssistant,
) -> None:
    """Test conditional field visibility and value stripping for producers and emitters."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {},
            CONF_PRODUCERS: {},
            CONF_SPACES: [
                {
                    CONF_ID: "den",
                    CONF_NAME: "Den",
                    CONF_TEMP_SENSOR: "sensor.den_temp",
                    CONF_PRESETS: {},
                    CONF_EMITTERS: [],
                }
            ],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    # Add boiler producer with propane fuel type
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "producers_menu"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    assert result["step_id"] == "producer_add"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ID: "boiler1",
            CONF_NAME: "Main Boiler",
            CONF_TYPE: "modulating_boiler",
            "modulating_boiler_profile": "none",
            CONF_FUEL_TYPE: "propane",
        },
    )
    assert result["step_id"] == "producers_menu"

    # Add heat pump producer (fuel_type hidden, should not persist fuel_type)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    assert result["step_id"] == "producer_add"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ID: "hp1",
            CONF_NAME: "Heat Pump 1",
            CONF_TYPE: "heat_pump",
            "heat_pump_profile": "none",
        },
    )
    assert result["step_id"] == "producers_menu"

    # Go back to init -> spaces_menu -> den -> emitters
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "spaces_menu"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "den"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "emitters"}
    )

    # Add hydronic emitter: zone_id specified, nominal_btu should be stripped
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "add"}
    )
    assert result["step_id"] == "emitter_add"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TYPE: "hydronic",
            "boiler_emitter_producer": "boiler1",
            CONF_ENTITY_ID: "switch.den_zone_valve",
            CONF_ZONE_ID: "z_den",
        },
    )
    assert result["step_id"] == "emitters_menu"

    # Add mini-split emitter: nominal_btu specified, zone_id should be stripped
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "add"}
    )
    assert result["step_id"] == "emitter_add"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TYPE: "mini_split",
            "hp_emitter_producer": "hp1",
            CONF_ENTITY_ID: "climate.den_ac",
            CONF_NOMINAL_BTU: 18000.0,
        },
    )
    assert result["step_id"] == "emitters_menu"

    # Save and exit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    producers = result["data"][CONF_PRODUCERS]
    assert producers["boiler1"][CONF_FUEL_TYPE] == "propane"
    assert CONF_FUEL_TYPE not in producers["hp1"]

    den_emitters = result["data"][CONF_SPACES][0][CONF_EMITTERS]
    assert len(den_emitters) == 2
    # Hydronic emitter
    assert den_emitters[0][CONF_TYPE] == "hydronic"
    assert den_emitters[0][CONF_ZONE_ID] == "z_den"
    assert CONF_NOMINAL_BTU not in den_emitters[0]
    # Mini-split emitter
    assert den_emitters[1][CONF_TYPE] == "mini_split"
    assert den_emitters[1][CONF_NOMINAL_BTU] == 18000.0
    assert CONF_ZONE_ID not in den_emitters[1]


async def test_options_flow_producer_add_auto_slug_and_profile_lists(
    hass: HomeAssistant,
) -> None:
    """Test Add Producer with auto-generated ID slug, disambiguation, and profile filtering."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HVAC Fusion",
        data={
            CONF_NAME: "HVAC Fusion",
            CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
            CONF_TARIFFS: {
                CONF_ELECTRIC_COST_PER_KWH: 0.25,
                CONF_GAS_COST_PER_THERM: 1.50,
            },
            CONF_PRODUCERS: {},
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "producers_menu"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    assert result["step_id"] == "producer_add"

    schema = result["data_schema"].schema
    schema_keys = [str(k) for k in schema]

    # Verify field order / presence
    assert schema_keys[0] == CONF_NAME
    assert schema_keys[1] == CONF_ID
    assert schema_keys[2] == CONF_TYPE

    # Check heat pump profile visibility and default
    hp_profile_key = next(k for k in schema if str(k) == "heat_pump_profile")
    assert hp_profile_key.visible == {
        "field": CONF_TYPE,
        "value": "heat_pump",
    }
    assert hp_profile_key.default() == "generic/cold_climate_heat_pump.json"

    # Check boiler profile visibility and default
    boiler_profile_key = next(
        k for k in schema if str(k) == "modulating_boiler_profile"
    )
    assert boiler_profile_key.visible == {
        "field": CONF_TYPE,
        "value": "modulating_boiler",
    }
    assert boiler_profile_key.default() == "generic/modulating_condensing_boiler.json"

    # 1. Add Heat Pump omitting CONF_ID -> should auto-slug to 'living_room_heat_pump'
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room Heat Pump",
            CONF_TYPE: "heat_pump",
            "heat_pump_profile": "generic/cold_climate_heat_pump.json",
        },
    )
    assert result["step_id"] == "producers_menu"

    # 2. Add another Heat Pump with the SAME name and NO ID -> should disambiguate to 'living_room_heat_pump_2'
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Living Room Heat Pump",
            CONF_TYPE: "heat_pump",
            "heat_pump_profile": "generic/standard_heat_pump.json",
        },
    )
    assert result["step_id"] == "producers_menu"

    # 3. Add Boiler with explicit ID
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_ID: "custom_boiler",
            CONF_NAME: "Basement Boiler",
            CONF_TYPE: "modulating_boiler",
            "modulating_boiler_profile": "generic/modulating_condensing_boiler.json",
            CONF_FUEL_TYPE: "natural_gas",
        },
    )
    assert result["step_id"] == "producers_menu"

    # Finish flow and verify saved producers
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()

    producers = result["data"][CONF_PRODUCERS]
    assert "living_room_heat_pump" in producers
    assert (
        producers["living_room_heat_pump"][CONF_PROFILE]
        == "generic/cold_climate_heat_pump.json"
    )
    assert producers["living_room_heat_pump"][CONF_TYPE] == "heat_pump"

    assert "living_room_heat_pump_2" in producers
    assert (
        producers["living_room_heat_pump_2"][CONF_PROFILE]
        == "generic/standard_heat_pump.json"
    )

    assert "custom_boiler" in producers
    assert producers["custom_boiler"][CONF_FUEL_TYPE] == "natural_gas"
    assert (
        producers["custom_boiler"][CONF_PROFILE]
        == "generic/modulating_condensing_boiler.json"
    )


@pytest.mark.asyncio
async def test_options_flow_cancel_in_all_add_steps(hass: HomeAssistant) -> None:
    """Test cancelling out of all 'Add xxx' steps without saving or losing options."""
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
                    CONF_TYPE: "heat_pump",
                    CONF_PROFILE: None,
                }
            },
            CONF_SPACES: [
                {
                    CONF_ID: "den",
                    CONF_NAME: "Den",
                    CONF_TEMP_SENSOR: "sensor.den_temp",
                    CONF_PRESETS: {},
                    CONF_EMITTERS: [],
                }
            ],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    # 1. Test producer_add cancellation & validation
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "producers_menu"}
    )
    assert result["step_id"] == "producers_menu"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "add"}
    )
    assert result["step_id"] == "producer_add"

    # Submitting empty without cancel triggers name_required error
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: ""}
    )
    assert result["step_id"] == "producer_add"
    assert result["errors"][CONF_NAME] == "name_required"

    # Submitting with cancel=True returns cleanly to producers_menu
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"cancel": True}
    )
    assert result["step_id"] == "producers_menu"

    # 2. Test space_add cancellation & validation
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"producer_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "spaces_menu"}
    )
    assert result["step_id"] == "spaces_menu"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "add"}
    )
    assert result["step_id"] == "space_add"

    # Submitting empty without cancel triggers validation errors
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_NAME: ""}
    )
    assert result["step_id"] == "space_add"
    assert result["errors"][CONF_NAME] == "name_required"
    assert result["errors"][CONF_TEMP_SENSOR] == "temp_sensor_required"

    # Submitting with cancel=True returns cleanly to spaces_menu
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"cancel": True}
    )
    assert result["step_id"] == "spaces_menu"

    # 3. Enter Den -> Schedule Presets -> preset_add cancellation & validation
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "den"}
    )
    assert result["step_id"] == "space_manage"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "presets"}
    )
    assert result["step_id"] == "presets_menu"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"preset_action": "add"}
    )
    assert result["step_id"] == "preset_add"

    # Submitting empty without cancel triggers schedule_required error
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    assert result["step_id"] == "preset_add"
    assert result["errors"]["schedule_entity"] == "schedule_required"

    # Submitting with cancel=True returns cleanly to presets_menu
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"cancel": True}
    )
    assert result["step_id"] == "presets_menu"

    # 4. Return to Den manage -> Emitters -> emitter_add cancellation & validation
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"preset_action": "back"}
    )
    assert result["step_id"] == "space_manage"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "emitters"}
    )
    assert result["step_id"] == "emitters_menu"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "add"}
    )
    assert result["step_id"] == "emitter_add"

    # Submitting without entity_id triggers entity_required error
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TYPE: "mini_split", "hp_emitter_producer": "hp1"}
    )
    assert result["step_id"] == "emitter_add"
    assert result["errors"][CONF_ENTITY_ID] == "entity_required"

    # Submitting with cancel=True returns cleanly to emitters_menu
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"cancel": True}
    )
    assert result["step_id"] == "emitters_menu"

    # Finish and verify no rogue entities were created
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"emitter_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"space_action": "back"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "finish"}
    )
    await hass.async_block_till_done()
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY

    saved_data = result["data"]
    assert len(saved_data[CONF_PRODUCERS]) == 1
    assert "hp1" in saved_data[CONF_PRODUCERS]
    assert len(saved_data[CONF_SPACES]) == 1
    assert saved_data[CONF_SPACES][0][CONF_ID] == "den"
    assert len(saved_data[CONF_SPACES][0][CONF_EMITTERS]) == 0
    assert len(saved_data[CONF_SPACES][0][CONF_PRESETS]) == 0
