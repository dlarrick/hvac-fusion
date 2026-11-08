# HVAC Fusion - Project Structure & Architecture

`hvac-fusion` is a Home Assistant custom component integration (designed for HACS) that acts as the high-level brain for multi-source heating and cooling systems. It orchestrates physical mini-split and hydronic entities using the underlying calculation and arbitration engine from [`hvac-crossover`](file:///home/doug/Projects/hvac-crossover).

---

## 1. Directory Structure

```text
hvac-fusion/
├── custom_components/
│   └── hvac_fusion/                # Main Home Assistant integration package
│       ├── brand/                  # Brand assets (icon.png, logo.png, @2x versions)
│       ├── __init__.py             # HvacFusionManager, entity setup, dispatching & cycling
│       ├── climate.py              # HvacFusionSpaceClimate: virtual space climate entities
│       ├── config_flow.py          # UI Setup & Options Flow (4-menu configuration hub)
│       ├── const.py                # Configuration constants, domain, and defaults
│       ├── icons.json              # Custom icon translations
│       ├── manifest.json           # Home Assistant manifest & dependency pins
│       ├── sensor.py               # Diagnostic sensors (crossover temperature, COP*)
│       ├── services.yaml           # Service definitions
│       ├── strings.json            # UI translation source
│       ├── configuration.yaml.example # Reference YAML configuration
│       └── translations/
│           └── en.json             # English UI translation strings (mirrors strings.json)
├── tests/                          # Integration test suite (pytest-homeassistant-custom-component)
│   ├── conftest.py                 # Pytest fixtures and environment setup
│   ├── test_config_flow.py         # Form navigation, validation, CRUD for producers/spaces/tariffs
│   ├── test_cycling.py             # Setpoint clamping detection & hysteresis cycling
│   ├── test_manager.py             # Manager lifecycle, topology generation, tariff sensors
│   ├── test_sensor.py              # Diagnostic sensor state and attribute updates
│   └── test_sensor_unavailable.py  # Graceful fallback on unavailable/unknown entity sensors
├── hacs.json                       # HACS integration metadata
├── pytest.ini                      # Pytest runner configuration
└── requirements-test.txt           # Test runner dependencies
```

---

## 2. Core Integration Architecture

### A. HvacFusionManager (`__init__.py`)
The central coordinator running inside Home Assistant:
* **Topology Construction:** Translates Home Assistant configuration entries into `hvac-crossover`'s `SystemTopology` (producers, delivery units, spaces).
* **State Gathering:** Collects real-time state from physical sensors and helpers (outdoor temperature, space temperatures, window binary sensors, solar export, and live electric/gas/propane tariff sensors or input_number entities).
* **Evaluation Loop:** Periodically runs `DualFuelCoordinator.evaluate_conditions()` to generate a `DispatchPlan`.
* **Subsidiary Command Dispatching:** Translates plan directives into physical Home Assistant service calls (`climate.set_hvac_mode`, `climate.set_temperature`), with support for shared boiler secondary space fallback.
* **Setpoint-Limit Cycling:** Detects when requested setpoints are clamped by a physical thermostat's `min_temp` or `max_temp` limits and runs cycling band hysteresis to maintain comfort without overheating.

### B. Virtual Space Climate Entity (`climate.py`)
Each living space configured in HVAC Fusion is exposed as a virtual `climate` entity:
* Supports `HEAT_COOL`, `HEAT`, `COOL`, and `OFF`.
* Maps preset modes to Home Assistant `schedule` entities or manual overrides.
* Restores active preset modes and target temperature setpoints across Home Assistant restarts (`RestoreEntity`).
* Exposes rich diagnostic state attributes (`active_producer`, `active_delivery_units`, `cycling_emitters`, `economic_crossover_temp`, `system_phase`, `explanation`).

### C. Options Flow & UI Configuration (`config_flow.py`)
Allows full UI-based setup and ongoing reconfiguration via Home Assistant Settings:
* **Initial Setup (Config Flow):** Captures coordinator name, outdoor temperature sensor, optional solar export sensor, and physical control toggle (dry-run mode).
* **Options Flow (4-Menu Configuration Hub):**
  1. **Environmental Sensors:** Outdoor temperature sensor entity and optional solar export sensor entity.
  2. **Producers Hub:** Add, edit, or delete heating/cooling equipment (heat pumps and boilers). Profiles are scanned dynamically with make/model metadata, and forms take advantage of HA 2026.11 conditional visibility to tailor fields by equipment type.
  3. **Spaces & Emitters Hub:** Add, edit, or delete living spaces with room temperature sensors, floor area, ceiling height, arbitration priority (1–10), window/door binary sensors, and shared boiler roles (`independent`, `primary`, `secondary`). Includes nested sub-flows for:
     * **Emitters:** Attach mini-split heads or hydronic zones to producers and physical actuation entities (`climate` or `switch`), with setpoint offsets and capacity/zone IDs.
     * **Schedule Presets:** Add or edit space preset modes linked directly to Home Assistant `schedule` entities.
  4. **Tariffs, Safety Limits & Operational Policies:** Grouped into visual sections for electric, gas, and propane tariffs (with live sensor/helper support and static fallbacks), heat pump low-ambient safety band, physical control toggle (dry-run mode), setpoint cycling band, and evaluation interval.

---

## 3. Developer Quick Reference

### Virtual Environment & Testing
All development and testing must use the project's dedicated virtual environment:
```bash
# Activate environment
source /home/doug/Projects/hvac-fusion/venv/bin/activate

# Run test suite with PYTHONPATH set
cd /home/doug/Projects/hvac-fusion
PYTHONPATH=. pytest

# Run hvac-crossover tests from the same environment
cd /home/doug/Projects/hvac-crossover
python3 -m unittest discover -s tests
```

### Dependency on `hvac-crossover`
* `hvac-crossover` is installed in editable mode (`pip install -e /home/doug/Projects/hvac-crossover`) inside `./venv`.
* Changes made in `/home/doug/Projects/hvac-crossover` take effect immediately in `hvac-fusion` tests.
* When updating versions, bump `pyproject.toml` in `hvac-crossover` and update `"requirements": ["hvac-crossover==x.y.z"]` in `custom_components/hvac_fusion/manifest.json`.
