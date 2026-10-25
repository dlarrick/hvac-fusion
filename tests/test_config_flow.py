"""Tests for HVAC Fusion config flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.hvac_fusion.const import (
    CONF_CONTROL_ENABLED,
    CONF_ELECTRIC_COST_PER_KWH,
    CONF_GAS_COST_PER_THERM,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PROPANE_COST_PER_GAL,
    CONF_TARIFFS,
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
