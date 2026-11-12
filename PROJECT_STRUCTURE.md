# HVAC Fusion - Project Structure & Architecture

**hvac-fusion** is a Home Assistant custom component integration (designed for HACS) that acts as the high-level brain for multi-source heating and cooling systems. It orchestrates physical mini-split and hydronic entities using the underlying calculation and arbitration engine from **hvac-crossover**.

---

## 1. Directory Structure

Every tracked file in the repository is organized as follows:

```text
hvac-fusion/
├── .github/
│   └── workflows/
│       └── test.yml                  # GitHub Actions CI (pytest, frontend typecheck, bundle drift check)
├── .gitignore                        # Git ignore patterns
├── .pre-commit-config.yaml           # Pre-commit hook definitions (ruff formatting and linting)
├── CONFIGURATION.md                  # Full UI Configuration Reference (Config Flow & Options Flow)
├── LICENSE                           # Project license (MIT)
├── PROJECT_STRUCTURE.md              # Permanent architecture, layout, and onboarding map (updated every session)
├── README.md                         # Main repository documentation, feature overview, and setup guide
├── custom_components/
│   └── hvac_fusion/                  # Main Home Assistant integration package
│       ├── brand/                    # Brand assets (icon.png, logo.png, @2x versions)
│       │   ├── icon.png
│       │   ├── icon@2x.png
│       │   ├── logo.png
│       │   └── logo@2x.png
│       ├── frontend/                 # Compiled frontend distribution bundle
│       │   └── hvac-fusion-cards.js  # Production build of custom Lovelace cards
│       ├── translations/
│       │   └── en.json               # English UI translation strings (mirrors strings.json)
│       ├── __init__.py               # HvacFusionManager: entity setup, state gathering, plan dispatching & cycling
│       ├── climate.py                # HvacFusionSpaceClimate: virtual space climate entities (Tier 2/3)
│       ├── config_flow.py            # UI Setup & Options Flow (4-menu configuration hub)
│       ├── const.py                  # Domain constants, configuration keys, and defaults
│       ├── frontend_loader.py        # Uncached, version-fingerprinted Lovelace resource auto-loader
│       ├── icons.json                # Custom icon mapping definitions
│       ├── manifest.json             # Home Assistant integration manifest & dependency pins
│       ├── sensor.py                 # Diagnostic & advisory sensors (crossover temp, COP, producer states)
│       ├── services.yaml             # Service call schemas
│       └── strings.json              # Source UI translation strings
├── docs/
│   └── images/                       # Documentation screenshots and visual assets
│       ├── climate_preset_timeline.png
│       └── schedule_preset_card.png
├── frontend/                         # Lovelace custom dashboard card suite (TypeScript + Lit + Vite)
│   ├── .gitignore                    # Frontend build and dependency ignore patterns
│   ├── README.md                     # Frontend development, testing, and card configuration docs
│   ├── index.html                    # Vite local development dev harness
│   ├── package-lock.json             # NPM lockfile
│   ├── package.json                  # NPM dependencies and build scripts
│   ├── tsconfig.json                 # TypeScript compiler configuration
│   ├── vite.config.ts                # Vite build configuration (single IIFE bundle)
│   └── src/
│       ├── index.ts                  # Bundle entry point & Lovelace custom card registration
│       ├── types.ts                  # TypeScript interfaces (HA entities, schedules, cards, presets)
│       ├── schedule-preset-card.ts   # custom:schedule-preset-card (7-day schedule grid editor)
│       ├── hvac-fusion-status-card.ts# custom:hvac-fusion-status-card (24h schedule, comfort bump, diagnostics)
│       ├── components/
│       │   ├── card-editor.ts        # Visual card editor for custom:schedule-preset-card
│       │   ├── preset-dialog.ts      # Modal dialog for editing schedule timeblocks and setpoints
│       │   └── status-editor.ts      # Visual card editor for custom:hvac-fusion-status-card
│       ├── services/
│       │   └── ha-schedule.ts        # WebSocket service abstraction for Home Assistant schedule entities
│       └── utils/
│           ├── colors.ts             # Preset mode color scheme mapping
│           └── time.ts               # Time conversion, quantization, and formatting helpers
├── hacs.json                         # HACS integration metadata
├── plans/                            # Planning, session handover, and design documents (see plans/INDEX.md)
│   ├── INDEX.md                      # Index of all planning, architecture, and session continuity files
│   ├── HANDOVER.md                   # Transient handover notes and immediate context (updated every session)
│   ├── history.md                    # Chronological development log & historical notes (updated every session)
│   ├── roadmap_and_backlog.md        # Prioritized bug tracker and feature backlog (updated every session)
│   ├── agentic_climate_supervisor.md # Tier 3 LLM/agent supervisor architectural vision
│   ├── condensing_boiler_modeling_plan.md # Modulating-condensing return water estimation plan
│   ├── ha_gui_config_design.md       # Home Assistant GUI config design & 3-tier confidence ladder
│   └── profiles_re_work.md           # Producer profile generalization design
├── pytest.ini                        # Pytest runner configuration
├── requirements-test.txt             # Test runner dependencies (pytest, pytest-homeassistant-custom-component)
└── tests/                            # Integration test suite
    ├── conftest.py                   # Pytest fixtures and environment setup
    ├── test_comfort_boost.py         # Space comfort boost, stacking, linear decay, and restart survival
    ├── test_config_flow.py           # Form navigation, validation, CRUD for producers/spaces/tariffs
    ├── test_cycling.py               # Setpoint clamping detection & hysteresis cycling
    ├── test_manager.py               # Manager lifecycle, topology generation, tariff sensors
    ├── test_sensor.py                # Diagnostic sensor state and attribute updates
    └── test_sensor_unavailable.py    # Graceful fallback on unavailable/unknown entity sensors
```

---

## 2. Core Integration Architecture

### A. Coordinator & Manager ([`custom_components/hvac_fusion/__init__.py`](custom_components/hvac_fusion/__init__.py))
[`HvacFusionManager`](custom_components/hvac_fusion/__init__.py) is the central coordinator running inside Home Assistant:
* **Topology Construction:** Translates Home Assistant configuration entries into `hvac-crossover`'s `SystemTopology` (producers, delivery units, spaces):
  * **Emitter Identification & Topology Mapping:** Emitters are assigned deterministic IDs formatted as `{space_id}_{producer_id}_{idx}`.
  * Each emitter model (`MiniSplitHead`, `HydronicEmitter`, `FurnaceRegister`) explicitly holds its parent `producer_id`.
  * `HvacFusionManager` maintains runtime maps for actuation (`emitter_entity_map`, `emitter_types`, `emitter_zones`, `emitter_offsets`), while equipment association is queried through `Space.emitters`.
* **State Gathering:** Collects real-time state from physical sensors and helpers (outdoor temperature, space temperatures, window binary sensors, solar export, and live electric/gas/propane/oil tariff sensors or input numbers).
* **Evaluation Loop:** Periodically runs `DualFuelCoordinator.evaluate_conditions()` to generate a `DispatchPlan`.
* **Subsidiary Command Dispatching:** Translates plan directives into physical Home Assistant service calls (`climate.set_hvac_mode`, `climate.set_temperature`), with support for shared boiler secondary space fallback.
* **Setpoint-Limit Cycling:** Detects when requested setpoints are clamped by a physical thermostat's `min_temp` or `max_temp` limits and runs cycling band hysteresis to maintain comfort without overheating.

### B. Virtual Space Climate Entity ([`custom_components/hvac_fusion/climate.py`](custom_components/hvac_fusion/climate.py))
Each living space configured in HVAC Fusion is exposed as a virtual `climate` entity ([`HvacFusionSpaceClimate`](custom_components/hvac_fusion/climate.py)):
* Supports `HEAT_COOL`, `HEAT`, `COOL`, and `OFF`.
* Maps preset modes to Home Assistant `schedule` entities or manual overrides.
* Restores active preset modes and target temperature setpoints across Home Assistant restarts via `RestoreEntity` (`async_get_last_state`).
* Exposes clean room-level state attributes (`space_id`, `preset_mode`, `active_producer`, `active_delivery_units`, `cycling_emitters`, `phase`, `in_recovery`, `window_open`, `explanation`).
* **Service Interactions & Hold Modes:** Supports custom integration services (e.g. `acquire_schedule_lock`, `release_schedule_lock`, and `comfort_boost`). State attributes reflect active overrides (e.g., `schedule_editing: true/false`, `current_boost: float`).
* **Polling Invariant:** Must strictly enforce `_attr_should_poll = False` to prevent unwanted 30-second background polling timers.

### C. Advisory & Producer Entities ([`custom_components/hvac_fusion/sensor.py`](custom_components/hvac_fusion/sensor.py))
* **Economic Crossover Temperature Sensor:** System-level break-even temperature between heat pump and auxiliary heating, with `break_even_cop`, `heat_pump`, `auxiliary_producer`, `system_phase`, and `control_enabled` attributes.
* **Producer Status Sensors ([`HvacFusionProducerSensor`](custom_components/hvac_fusion/sensor.py)):** Dedicated operational state sensor (`idle`, `heating`, `cooling`, `locked_out`) for every energy producer:
  * Heat Pumps: Real-time `current_cop`, `capacity_derate_pct`, `mode_lock`, `nominal_capacity_btu`, `active_spaces`, and `safety_lockout`.
  * Boilers & Furnaces: `fuel_type`, `nominal_capacity_btu`, `rated_afue`, `estimated_return_temp_f`, `estimated_efficiency`, `condensing_state`, and `active_spaces`.

### D. Options Flow & UI Configuration ([`custom_components/hvac_fusion/config_flow.py`](custom_components/hvac_fusion/config_flow.py))
Allows full UI-based setup and ongoing reconfiguration via Home Assistant Settings:
* **Initial Setup (Config Flow):** Captures coordinator name, outdoor temperature sensor, optional solar export sensor, and physical control toggle (dry-run mode).
* **Options Flow (4-Menu Configuration Hub):**
  1. **Environmental Sensors:** Outdoor temperature sensor entity and optional solar export sensor entity.
  2. **Producers Hub:** Add, edit, or delete heating/cooling equipment (heat pumps, modulating boilers, atmospheric boilers, steam boilers, furnaces). Configures equipment nominal capacity (BTU), selects generalized profiles (or manual), and applies conditional visibility for fuel types and ODR settings.
  3. **Spaces & Emitters Hub:** Add, edit, or delete living spaces with room temperature sensors, floor area, ceiling height, arbitration priority (1–10), window/door binary sensors, and shared boiler roles (`independent`, `primary`, `secondary`). Includes nested sub-flows for:
     * **Emitters:** Attach mini-split heads, hydronic loops, or furnace registers to producers and physical actuation entities (`climate` or `switch`), with setpoint offsets, hydronic emitter characteristics, and mini-split head ratings.
     * **Schedule Presets:** Add or edit space preset modes linked directly to Home Assistant `schedule` entities.
  4. **Tariffs, Safety Limits & Operational Policies:** Grouped into visual sections for electric, gas, propane, and oil tariffs (with live sensor/helper support and static fallbacks), heat pump low-ambient safety band, physical control toggle (dry-run mode), setpoint cycling band, and evaluation interval.

### E. Frontend Dashboard Card Suite ([`frontend/`](frontend/) & [`custom_components/hvac_fusion/frontend_loader.py`](custom_components/hvac_fusion/frontend_loader.py))
* **[`custom:schedule-preset-card`](frontend/src/schedule-preset-card.ts):** A 7-day schedule grid editor displaying visual preset blocks, enabling direct schedule editing, temperature target adjustments, and block additions/deletions.
* **[`custom:hvac-fusion-status-card`](frontend/src/hvac-fusion-status-card.ts):** A unified space status card for living space dashboards featuring a 24-hour preset schedule track with live NOW progress needle, temporary comfort bump toolbar (`Warmer` / `Cooler` / `Cancel`), and expandable room diagnostics (aliases legacy `custom:climate-preset-timeline`).
* **Auto-Registration & Cache Busting:** [`frontend_loader.py`](custom_components/hvac_fusion/frontend_loader.py) registers an uncached, content-versioned resource endpoint (`/api/hvac_fusion/frontend/hvac-fusion-cards.js`) on integration setup, automatically injecting the cards into Lovelace without requiring manual dashboard resource configuration.
* **Progressive Enhancement:** Both cards function standalone with native Home Assistant `schedule` and `climate` entities even if the backend `hvac_fusion` custom component is not loaded.

---

## 3. Developer Quick Reference

### Virtual Environment & Backend Testing
All Python development and testing must use the project's dedicated virtual environment:
```bash
# Activate environment
source ./venv/bin/activate

# Run backend test suite with PYTHONPATH set
PYTHONPATH=. pytest

# Run hvac-crossover tests from sibling repository
cd ../hvac-crossover
python3 -m unittest discover -s tests
```

### Frontend Building & CI Drift Prevention
Whenever any file in `frontend/src/` is modified:
```bash
# 1. Typecheck frontend code (must pass with 0 errors)
npm --prefix frontend run typecheck

# 2. Build production bundle (updates custom_components/hvac_fusion/frontend/hvac-fusion-cards.js)
npm --prefix frontend run build
```
> [!IMPORTANT]
> CI strictly verifies frontend bundle drift with `git diff --exit-code custom_components/hvac_fusion/frontend/hvac-fusion-cards.js`. Unbuilt frontend edits will fail pipeline verification.

### Code Style & Pre-commit
```bash
# Run ruff lint and format checks
pre-commit run --all-files
```

### Dependency on `hvac-crossover`
* `hvac-crossover` is installed in editable mode (`pip install -e ../hvac-crossover`) inside `./venv`.
* Changes made in `hvac-crossover` take effect immediately in `hvac-fusion` tests.
* When updating versions, bump `pyproject.toml` and `hvac_crossover/__init__.py` in `hvac-crossover`, and update `"requirements": ["hvac-crossover==x.y.z"]` in `custom_components/hvac_fusion/manifest.json`.

---

## 4. Session Continuity & Documentation Lifecycle

Every AI session must maintain and update four core files:

| File | Type | Lifecycle & Purpose |
| :--- | :--- | :--- |
| [`plans/HANDOVER.md`](plans/HANDOVER.md) | Transient | **Immediate session handover:** Current state, recent changes, in-flight work, active gotchas, and environment notes. A new session reads this first. |
| [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) | Permanent | **Permanent architecture & layout:** Comprehensive map of repository files, component responsibilities, and dev workflows. Enables sessions to hit the ground running without excessive exploration. |
| [`plans/history.md`](plans/history.md) | Permanent | **Chronological history:** Record of work done, architectural decisions, discussions, and historical context across development sessions. |
| [`plans/roadmap_and_backlog.md`](plans/roadmap_and_backlog.md) | Living Backlog | **Poor-man's ticketing system:** Prioritized bugs (Priority 1), near-term features (Priority 2), and future backlog items. |

For a complete index of all architectural proposals, design specifications, and implementation references, see [`plans/INDEX.md`](plans/INDEX.md).
