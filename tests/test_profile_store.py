"""Tests for remote profile index, ETag caching, and hourly revalidation."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
from custom_components.hvac_fusion import HvacFusionManager
from custom_components.hvac_fusion.config_flow import (
    async_get_available_producer_profiles,
)
from custom_components.hvac_fusion.const import (
    CONF_EMITTERS,
    CONF_OUTDOOR_TEMPERATURE_ENTITY,
    CONF_PRODUCERS,
    CONF_PROFILE,
    CONF_SPACES,
    CONF_TARIFFS,
    CONF_TYPE,
    DEFAULT_PROFILES_BASE_URL,
)
from custom_components.hvac_fusion.profile_store import (
    async_ensure_profiles,
    async_fetch_remote_index,
    resolve_profile_path,
)
from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.core import HomeAssistant

SAMPLE_INDEX = {
    "version": 1,
    "generated_at": "2026-11-15T15:07:02Z",
    "url_template": "producers/{id}.json",
    "fields": ["id", "make", "series", "model", "type", "fuel"],
    "rows": [
        [
            "mitsubishi/mxz_xcxxnahz2",
            "Mitsubishi Electric",
            "Multi-Zone Hyper-Heating (H2i)",
            "MXZ-xCxxNAHZ2",
            "inverter_heat_pump",
            "electric",
        ],
        [
            "burnham/alta",
            "Burnham",
            "Alta",
            "Alta",
            "modulating_boiler",
            "gas",
        ],
    ],
}

SAMPLE_HP_PROFILE = {
    "make": "Mitsubishi Electric",
    "series": "Multi-Zone Hyper-Heating (H2i)",
    "model": "MXZ-xCxxNAHZ2",
    "producer_type": "inverter_heat_pump",
    "min_operational_temp_f": -13.0,
    "heating_performance": {
        "full_load_cop": {"47": 3.3, "17": 2.0, "5": 1.95, "-13": 1.75},
        "part_load_cop": {"47": 4.0, "17": 2.65, "5": 2.3},
        "capacity_percentage": {"47": 100.0, "17": 100.0, "5": 100.0, "-13": 74.8},
    },
}


class _FakeResponse:
    def __init__(
        self, status: int, text: str = "", headers: dict[str, str] | None = None
    ) -> None:
        self.status = status
        self._text = text
        self.headers = headers or {}

    async def text(self) -> str:
        return self._text

    async def __aenter__(self) -> _FakeResponse:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None


class _FakeSession:
    def __init__(self, handler: Any) -> None:
        self._handler = handler
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(
        self, url: str, headers: dict[str, str] | None = None, **kwargs: Any
    ) -> _FakeResponse:
        hdrs = dict(headers or {})
        self.calls.append((url, hdrs))
        return self._handler(url, hdrs)


@pytest.mark.asyncio
async def test_fetch_remote_index_etag_and_offline_fallback(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    """Index is cached with ETag, sends If-None-Match, and falls back offline."""
    hass.config.config_dir = str(tmp_path)

    responses = [
        _FakeResponse(200, json.dumps(SAMPLE_INDEX), {"ETag": '"idx-etag-1"'}),
        _FakeResponse(304, "", {"ETag": '"idx-etag-1"'}),
    ]
    session = _FakeSession(lambda _url, _hdrs: responses.pop(0))

    with patch(
        "custom_components.hvac_fusion.profile_store.async_get_clientsession",
        return_value=session,
    ):
        entries = await async_fetch_remote_index(hass)
        assert len(entries) == 2
        assert entries[0]["value"] == "mitsubishi/mxz_xcxxnahz2.json"
        assert entries[0]["label"] == "Mitsubishi Electric MXZ-xCxxNAHZ2"
        assert entries[0]["category"] == "heat_pump"
        assert entries[1]["label"] == "Burnham Alta (Gas)"
        assert entries[1]["category"] == "modulating_boiler"

        # Second fetch sends If-None-Match and handles 304
        entries2 = await async_fetch_remote_index(hass)
        assert len(entries2) == 2
        assert session.calls[1][1].get("If-None-Match") == '"idx-etag-1"'

    # Offline fallback returns cached index
    def _raise_err(_url: str, _hdrs: dict[str, str]) -> _FakeResponse:
        raise aiohttp.ClientError("offline")

    offline_session = _FakeSession(_raise_err)
    with patch(
        "custom_components.hvac_fusion.profile_store.async_get_clientsession",
        return_value=offline_session,
    ):
        entries3 = await async_fetch_remote_index(hass)
        assert len(entries3) == 2


@pytest.mark.asyncio
async def test_config_flow_merges_generic_and_remote_profiles(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    """Options Flow merges bundled generic profiles with remote index."""
    hass.config.config_dir = str(tmp_path)
    session = _FakeSession(
        lambda _url, _hdrs: _FakeResponse(
            200, json.dumps(SAMPLE_INDEX), {"ETag": '"idx-1"'}
        )
    )
    with patch(
        "custom_components.hvac_fusion.profile_store.async_get_clientsession",
        return_value=session,
    ):
        hp_choices = await async_get_available_producer_profiles(hass, "heat_pump")

    values = [c["value"] for c in hp_choices]
    assert "generic/cold_climate_heat_pump.json" in values
    assert "mitsubishi/mxz_xcxxnahz2.json" in values


@pytest.mark.asyncio
async def test_ensure_profiles_downloads_and_revalidates(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    """Selected remote profiles download, cache, revalidate via ETag, and update."""
    hass.config.config_dir = str(tmp_path)

    updated_hp = dict(SAMPLE_HP_PROFILE)
    updated_hp["min_operational_temp_f"] = -15.0

    responses = [
        _FakeResponse(200, json.dumps(SAMPLE_HP_PROFILE), {"ETag": '"hp-etag-1"'}),
        _FakeResponse(304, "", {"ETag": '"hp-etag-1"'}),
        _FakeResponse(200, json.dumps(updated_hp), {"ETag": '"hp-etag-2"'}),
    ]
    session = _FakeSession(lambda _url, _hdrs: responses.pop(0))

    with patch(
        "custom_components.hvac_fusion.profile_store.async_get_clientsession",
        return_value=session,
    ):
        # 1. Initial download
        changed = await async_ensure_profiles(
            hass,
            ["mitsubishi/mxz_xcxxnahz2.json", "generic/cold_climate_heat_pump.json"],
        )
        assert changed is True
        # Only remote profile was fetched (generic/ is bundled)
        assert len(session.calls) == 1
        assert session.calls[0][0] == (
            f"{DEFAULT_PROFILES_BASE_URL}producers/mitsubishi/mxz_xcxxnahz2.json"
        )

        resolved = resolve_profile_path("mitsubishi/mxz_xcxxnahz2.json", hass)
        assert Path(resolved).is_file()

        # 2. Revalidate -> 304 Not Modified
        changed2 = await async_ensure_profiles(hass, ["mitsubishi/mxz_xcxxnahz2.json"])
        assert changed2 is False
        assert session.calls[1][1].get("If-None-Match") == '"hp-etag-1"'

        # 3. Revalidate -> 200 Updated
        changed3 = await async_ensure_profiles(hass, ["mitsubishi/mxz_xcxxnahz2.json"])
        assert changed3 is True
        assert session.calls[2][1].get("If-None-Match") == '"hp-etag-1"'
        saved = json.loads(Path(resolved).read_text(encoding="utf-8"))
        assert saved["min_operational_temp_f"] == -15.0


@pytest.mark.asyncio
async def test_manager_hourly_revalidation_rebuilds_topology(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    """HvacFusionManager downloads on init and rebuilds topology on hourly 200 update."""
    hass.config.config_dir = str(tmp_path)
    hass.states.async_set("sensor.outdoor_temp", "35.0")

    updated_hp = dict(SAMPLE_HP_PROFILE)
    updated_hp["min_operational_temp_f"] = -20.0

    responses = [
        _FakeResponse(200, json.dumps(SAMPLE_HP_PROFILE), {"ETag": '"hp-1"'}),
        _FakeResponse(200, json.dumps(updated_hp), {"ETag": '"hp-2"'}),
    ]
    session = _FakeSession(lambda _url, _hdrs: responses.pop(0))

    conf = {
        CONF_NAME: "Test",
        CONF_OUTDOOR_TEMPERATURE_ENTITY: "sensor.outdoor_temp",
        CONF_TARIFFS: {},
        CONF_PRODUCERS: {
            "hp": {
                CONF_TYPE: "inverter_heat_pump",
                CONF_PROFILE: "mitsubishi/mxz_xcxxnahz2.json",
            }
        },
        CONF_SPACES: [{CONF_ID: "lr", CONF_NAME: "Living Room", CONF_EMITTERS: []}],
    }

    with patch(
        "custom_components.hvac_fusion.profile_store.async_get_clientsession",
        return_value=session,
    ):
        manager = HvacFusionManager(hass, conf, entry_id="test_entry")
        await manager.async_init()
        assert manager.topology is not None
        assert manager.topology.producers[0].min_operational_temp_f == -13.0

        # Immediate evaluate should NOT re-fetch (< 1 hour)
        await manager.async_evaluate()
        assert len(session.calls) == 1

        # Simulate > 1 hour elapsed -> hourly revalidation triggers & updates topology
        manager._last_profile_check = datetime.now(UTC) - timedelta(hours=2)
        await manager.async_evaluate()
        assert len(session.calls) == 2
        assert manager.topology.producers[0].min_operational_temp_f == -20.0
