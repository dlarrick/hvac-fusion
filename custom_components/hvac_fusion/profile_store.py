"""Remote profile index, ETag caching, and local resolution for HVAC Fusion."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_PROFILES_BASE_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=10)
_DEFAULT_URL_TEMPLATE = "producers/{id}.json"


def normalize_profile_id(profile_str: str) -> str:
    """Normalize a profile identifier to '<make>/<model>' without .json suffix."""
    cleaned = profile_str.strip().strip("/")
    if cleaned.startswith("producers/"):
        cleaned = cleaned[len("producers/") :]
    if cleaned.endswith(".json"):
        cleaned = cleaned[:-5]
    return cleaned


def is_bundled_generic_profile(profile_str: str) -> bool:
    """Return True if the profile refers to a built-in generic/ fallback."""
    return normalize_profile_id(profile_str).startswith("generic/")


def get_profile_cache_dir(hass: HomeAssistant | None) -> Path | None:
    """Return the local .storage cache directory for downloaded profiles."""
    if hass is None:
        return None
    config = getattr(hass, "config", None)
    path_fn = getattr(config, "path", None)
    if not callable(path_fn):
        return None
    try:
        candidate = path_fn(".storage", DOMAIN, "profiles")
    except Exception:
        return None
    if isinstance(candidate, (str, os.PathLike)):
        return Path(candidate)
    return None


def resolve_profile_path(profile_str: str, hass: HomeAssistant | None = None) -> str:
    """Find profile JSON in bundled hvac_crossover, local cache, or user path."""
    if os.path.isabs(profile_str) and os.path.exists(profile_str):
        return profile_str

    try:
        import hvac_crossover

        pkg_dir = os.path.dirname(hvac_crossover.__file__)
        pkg_profiles_dir = os.path.join(pkg_dir, "profiles", "producers")
        candidate = os.path.join(pkg_profiles_dir, profile_str)
        if not candidate.endswith(".json"):
            candidate += ".json"
        if os.path.exists(candidate):
            return candidate
    except ImportError:
        pass

    cache_dir = get_profile_cache_dir(hass)
    if cache_dir is not None:
        profile_id = normalize_profile_id(profile_str)
        cached_path = cache_dir / "producers" / f"{profile_id}.json"
        if cached_path.exists():
            return str(cached_path)

    if os.path.exists(profile_str):
        return profile_str
    if os.path.exists(profile_str + ".json"):
        return profile_str + ".json"

    return profile_str


def _load_json_file(path: Path) -> Any:
    """Synchronously read and parse a JSON file, returning None on missing/invalid."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        _LOGGER.debug("Failed reading cached JSON %s: %s", path, err)
        return None


def _write_json_file(path: Path, data: Any) -> None:
    """Synchronously write JSON data to disk, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")


def _write_text_file(path: Path, text: str) -> None:
    """Synchronously write text to disk, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _get_clientsession_safe(
    hass: HomeAssistant | None,
) -> aiohttp.ClientSession | None:
    """Safely obtain HA's aiohttp ClientSession (returns None for mock hass)."""
    if hass is None:
        return None
    try:
        session = async_get_clientsession(hass)
    except Exception:
        return None
    if not hasattr(session, "get") or type(session).__name__ == "MagicMock":
        return None
    return session


async def _fetch_with_etag(
    session: aiohttp.ClientSession,
    url: str,
    etag: str | None,
) -> tuple[int, str | None, str | None]:
    """Fetch URL with optional If-None-Match. Returns (status, text, new_etag)."""
    headers: dict[str, str] = {}
    if etag:
        headers["If-None-Match"] = etag
    async with session.get(url, headers=headers, timeout=_HTTP_TIMEOUT) as resp:
        new_etag = resp.headers.get("ETag")
        if resp.status == 304:
            return 304, None, new_etag or etag
        if resp.status == 200:
            return 200, await resp.text(), new_etag
        return resp.status, None, None


def _map_producer_category(raw_type: str) -> str:
    """Map raw producer_type string to Config Flow filter category."""
    if "heat_pump" in raw_type:
        return "heat_pump"
    if raw_type in (
        "modulating_boiler",
        "atmospheric_boiler",
        "steam_boiler",
        "furnace",
    ):
        return raw_type
    return "boiler"


def parse_index_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse table JSON index.json into profile metadata entries."""
    fields = payload.get("fields")
    rows = payload.get("rows")
    if not isinstance(fields, list) or not isinstance(rows, list):
        return []

    idx = {name: i for i, name in enumerate(fields)}
    if "id" not in idx:
        return []

    entries: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) <= idx["id"]:
            continue
        profile_id = str(row[idx["id"]])
        make = str(row[idx["make"]]) if "make" in idx and idx["make"] < len(row) else ""
        series = (
            str(row[idx["series"]])
            if "series" in idx and idx["series"] < len(row)
            else ""
        )
        model = (
            str(row[idx["model"]]) if "model" in idx and idx["model"] < len(row) else ""
        )
        raw_type = (
            str(row[idx["type"]]) if "type" in idx and idx["type"] < len(row) else ""
        )
        fuel = str(row[idx["fuel"]]) if "fuel" in idx and idx["fuel"] < len(row) else ""

        parts = [p for p in (make, model or series) if p]
        label = " ".join(parts) if parts else profile_id
        if fuel and fuel != "electric":
            label += f" ({fuel.replace('_', ' ').title()})"

        entries.append(
            {
                "value": f"{profile_id}.json",
                "label": label,
                "category": _map_producer_category(raw_type),
                "make": make,
                "series": series,
                "model": model,
                "fuel": fuel,
            }
        )
    return entries


async def async_fetch_remote_index(
    hass: HomeAssistant,
    base_url: str = DEFAULT_PROFILES_BASE_URL,
) -> list[dict[str, Any]]:
    """Fetch remote index.json using ETag caching, falling back to cached copy."""
    cache_dir = get_profile_cache_dir(hass)
    index_path = cache_dir / "index.json" if cache_dir else None
    etags_path = cache_dir / "etags.json" if cache_dir else None

    etags: dict[str, Any] = {}
    if etags_path is not None:
        loaded_etags = await hass.async_add_executor_job(_load_json_file, etags_path)
        if isinstance(loaded_etags, dict):
            etags = loaded_etags

    cached_index = (
        await hass.async_add_executor_job(_load_json_file, index_path)
        if index_path is not None
        else None
    )

    session = _get_clientsession_safe(hass)
    if session is not None:
        normalized_base = base_url if base_url.endswith("/") else f"{base_url}/"
        index_url = urljoin(normalized_base, "index.json")
        cached_etag = etags.get("index.json") if cached_index is not None else None
        try:
            status, body, new_etag = await _fetch_with_etag(
                session, index_url, cached_etag
            )
            if status == 200 and body is not None:
                parsed = json.loads(body)
                if isinstance(parsed, dict) and "rows" in parsed:
                    cached_index = parsed
                    if index_path is not None:
                        await hass.async_add_executor_job(
                            _write_text_file, index_path, body
                        )
                    if etags_path is not None and new_etag:
                        etags["index.json"] = new_etag
                        await hass.async_add_executor_job(
                            _write_json_file, etags_path, etags
                        )
            elif status not in (200, 304):
                _LOGGER.warning(
                    "Unexpected HTTP %s fetching profile index %s", status, index_url
                )
        except Exception as err:  # noqa: BLE001 - network/DNS errors must fall back cleanly
            _LOGGER.warning(
                "Could not refresh remote profile index (%s); using cached index if available",
                err,
            )

    if isinstance(cached_index, dict):
        return parse_index_payload(cached_index)
    return []


async def async_ensure_profiles(
    hass: HomeAssistant,
    profile_names: list[str],
    base_url: str = DEFAULT_PROFILES_BASE_URL,
    revalidate: bool = True,
) -> bool:
    """Ensure selected non-generic profiles are cached locally and up to date.

    Returns True if any cached profile file was created or updated on disk.
    """
    remote_ids = sorted(
        {
            normalize_profile_id(p)
            for p in profile_names
            if p
            and p != "none"
            and not os.path.isabs(p)
            and not is_bundled_generic_profile(p)
        }
    )
    if not remote_ids:
        return False

    cache_dir = get_profile_cache_dir(hass)
    if cache_dir is None:
        return False

    session = _get_clientsession_safe(hass)
    if session is None:
        return False

    etags_path = cache_dir / "etags.json"
    etags: dict[str, Any] = {}
    loaded_etags = await hass.async_add_executor_job(_load_json_file, etags_path)
    if isinstance(loaded_etags, dict):
        etags = loaded_etags

    # Determine URL template from cached index if available
    url_template = _DEFAULT_URL_TEMPLATE
    cached_index = await hass.async_add_executor_job(
        _load_json_file, cache_dir / "index.json"
    )
    if isinstance(cached_index, dict) and isinstance(
        cached_index.get("url_template"), str
    ):
        url_template = cached_index["url_template"]

    normalized_base = base_url if base_url.endswith("/") else f"{base_url}/"
    changed = False
    etags_dirty = False
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    for profile_id in remote_ids:
        local_path = cache_dir / "producers" / f"{profile_id}.json"
        file_exists = await hass.async_add_executor_job(local_path.exists)
        if file_exists and not revalidate:
            continue

        rel_url = url_template.format(id=profile_id)
        profile_url = urljoin(normalized_base, rel_url)
        cached_etag = etags.get(profile_id) if file_exists else None

        try:
            status, body, new_etag = await _fetch_with_etag(
                session, profile_url, cached_etag
            )
            if status == 200 and body is not None:
                # Validate JSON before persisting
                json.loads(body)
                await hass.async_add_executor_job(_write_text_file, local_path, body)
                if new_etag:
                    etags[profile_id] = new_etag
                    etags_dirty = True
                changed = True
                _LOGGER.info("Downloaded updated producer profile: %s", profile_id)
            elif status == 304:
                _LOGGER.debug("Producer profile %s unchanged (304)", profile_id)
                if new_etag and etags.get(profile_id) != new_etag:
                    etags[profile_id] = new_etag
                    etags_dirty = True
            else:
                _LOGGER.warning(
                    "HTTP %s fetching producer profile %s from %s",
                    status,
                    profile_id,
                    profile_url,
                )
        except Exception as err:  # noqa: BLE001 - network/DNS errors must fall back cleanly
            if file_exists:
                _LOGGER.warning(
                    "Failed to revalidate profile %s (%s); keeping cached version",
                    profile_id,
                    err,
                )
            else:
                _LOGGER.error(
                    "Failed to download profile %s (%s) and no local cache exists",
                    profile_id,
                    err,
                )

    if etags_dirty:
        etags["_last_checked_at"] = now_iso
        await hass.async_add_executor_job(_write_json_file, etags_path, etags)

    return changed
