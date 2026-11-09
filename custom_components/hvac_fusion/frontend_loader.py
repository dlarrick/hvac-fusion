"""Serve the dashboard card suite through an uncached, content-versioned loader."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from aiohttp import web
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http.server import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.http import HomeAssistantView
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN

BUNDLE_NAME = "hvac-fusion-cards.js"
BUNDLE_DIRECTORY = Path(__file__).parent / "frontend"
STATIC_URL = f"/{DOMAIN}/static"
API_LOADER_URL = f"/api/{DOMAIN}/frontend/{BUNDLE_NAME}"
_REGISTERED: HassKey[bool] = HassKey(f"{DOMAIN}.frontend_loader_registered")


def bundle_fingerprint(path: Path = BUNDLE_DIRECTORY / BUNDLE_NAME) -> str:
    """Return a short content hash so browsers fetch updated bundles on change."""
    if not path.is_file():
        return "notfound"
    return sha256(path.read_bytes()).hexdigest()[:16]


def loader_source(fingerprint: str) -> str:
    """Import the bundle at a URL that changes whenever its content changes."""
    return f'import "{STATIC_URL}/{BUNDLE_NAME}?v={fingerprint}";\n'


class HvacFusionLoaderView(HomeAssistantView):
    """Tiny module that browsers revalidate on dashboard load to bust cache on updates."""

    url = API_LOADER_URL
    name = f"{DOMAIN}:frontend_loader"
    requires_auth = False

    def __init__(self) -> None:
        self._cache: tuple[tuple[int, int], str] | None = None

    def _fingerprint(self) -> str:
        path = BUNDLE_DIRECTORY / BUNDLE_NAME
        if not path.is_file():
            return "notfound"
        stat = path.stat()
        key = (stat.st_mtime_ns, stat.st_size)
        if self._cache is None or self._cache[0] != key:
            self._cache = (key, bundle_fingerprint(path))
        return self._cache[1]

    async def get(self, request: web.Request) -> web.Response:
        """Return the loader module with no-store cache headers."""
        hass: HomeAssistant = request.app["hass"]
        fingerprint = await hass.async_add_executor_job(self._fingerprint)
        return web.Response(
            text=loader_source(fingerprint),
            content_type="application/javascript",
            headers={"Cache-Control": "no-store"},
        )


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register routes once per HA process and auto-load the card bundle."""
    if hass.http is None or hass.data.get(_REGISTERED):
        return

    hass.http.register_view(HvacFusionLoaderView())

    if BUNDLE_DIRECTORY.is_dir():
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(BUNDLE_DIRECTORY), cache_headers=True)]
        )

    if "frontend" in hass.config.components:
        add_extra_js_url(hass, API_LOADER_URL)

    hass.data[_REGISTERED] = True
