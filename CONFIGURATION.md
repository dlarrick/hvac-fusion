# HVAC Fusion Configuration Reference

HVAC Fusion is configured exclusively through the Home Assistant user interface via **Config Flow** (during initial setup) and **Options Flow** (via **Settings → Devices & Services → HVAC Fusion → Configure**).

YAML configuration (`configuration.yaml`) is **not supported**. All settings, equipment definitions, room topologies, and tariff rules are stored within Home Assistant's configuration entries and can be modified live without restarting Home Assistant.

---

## 1. Initial Setup (Config Flow)

When first adding the integration from **Settings → Devices & Services → Add Integration → HVAC Fusion**, you will configure the fundamental environmental and economic baseline:

| Field | Description | Type / Format | Example / Default |
| :--- | :--- | :--- | :--- |
| **Integration Title** | Friendly name for this system instance. | String | `HVAC Fusion` |
| **Outdoor Temperature Sensor** | Entity reporting outdoor ambient air temperature. Used for thermodynamic efficiency (COP) and crossover calculations. | `weather.*` or `sensor.*` | `sensor.outdoor_temperature` |
| **Solar Export Sensor** *(Optional)* | Entity reporting instantaneous grid solar export in Watts. When positive, electric cost calculations shift to net export credit tariffs. | `sensor.*` | `sensor.envoy_solar_export_watts` |
| **Control Enabled** | When checked, HVAC Fusion actively actuates physical climate and switch entities. When unchecked (Dry Run mode), it simulates decisions and updates diagnostic sensors without touching hardware. | Boolean | `false` (Dry Run enabled by default) |
| **Electric Cost per kWh** | Static base electric energy rate in $/kWh. Can be overridden with dynamic sensors in the Options Flow. | Float ($/kWh) | `0.25` |
| **Gas Cost per Therm** | Static natural gas rate in $/therm. | Float ($/therm) | `1.88` |
| **Propane Cost per Gallon** | Static propane (LP) rate in $/gal. | Float ($/gal) | `3.20` |
| **Oil Cost per Gallon** | Static fuel oil (#2) rate in $/gal. | Float ($/gal) | `3.85` |

---

## 2. Options Flow Navigation Hub

Once installed, click **Configure** on the HVAC Fusion integration card to access the navigation hub:

* **Manage Producers**: Add, edit, or remove heating and cooling equipment (heat pump outdoor condensers, boilers, furnaces).
* **Manage Spaces**: Add, edit, or remove thermal zones/rooms, attach delivery emitters, and link schedule presets.
* **Policies & Tariffs**: Update fuel/electric rates, configure dynamic rate sensors, adjust cycling deadbands, and toggle Dry Run mode.
* **Environmental Sensors**: Update outdoor temperature or solar export sensor entity IDs.

---

## 3. Producers (Equipment)

Producers represent primary energy conversion equipment. HVAC Fusion supports inverter heat pumps, modulating condensing boilers, standard atmospheric boilers, steam boilers, and warm-air furnaces.

### Supported Equipment Types

1. **Inverter Heat Pump (`heat_pump`)**
   * Multi-split or central inverter outdoor condenser unit (ODU).
   * Models temperature-dependent COP and capacity derating curves down to rated low-ambient cutoff limits (e.g. -4°F, -13°F).
   * Enforces single-refrigerant mode locking across connected indoor heads.
2. **Modulating Condensing Boiler (`modulating_boiler`)**
   * High-efficiency gas or propane hydronic boiler (e.g., Burnham Alta, Bradford White Brute FT).
   * Models physics-based return water dew-point condensing efficiency, turndown limits, and hydraulic separator mixing.
3. **Standard Atmospheric Boiler (`atmospheric_boiler`)**
   * Cast-iron non-condensing hydronic boiler with fixed AFUE (e.g. 80%–83%).
4. **Steam Boiler (`steam_boiler`)**
   * Low-pressure residential steam heating boiler.
5. **Warm-Air Furnace (`furnace`)**
   * Central ducted gas or oil furnace (standard or condensing).

### Producer Configuration Fields

| Setting | Applies To | Description |
| :--- | :--- | :--- |
| **Display Name** | All | Human-readable name (e.g., `Mitsubishi 3-Zone ODU`, `Alta 150 Boiler`). |
| **Producer ID** | All | Slug identifier (e.g., `odu1`, `boiler1`). Auto-generated from name if left blank. |
| **Producer Type** | All | Selects equipment physics model (`heat_pump`, `modulating_boiler`, etc.). |
| **Equipment Profile** | All | Select a pre-calibrated manufacturer or generic performance profile from the dropdown (see below), or select `None` for generic defaults. |
| **Nominal Heating Capacity (BTU)** | All | Equipment nameplate rated heating capacity in BTU/h (e.g., `24000` or `36000` for a 2-ton or 3-ton heat pump; `100000` or `150000` for a boiler). |
| **Fuel Type** | Boilers & Furnaces | Select fuel source: `Natural Gas`, `Propane`, or `Heating Oil (#2)`. |
| **Outdoor Reset Sensor Connected** | Modulating Boiler | Check if equipped with an outdoor reset water temperature sensor. When active, adjusts primary supply temperature along the outdoor reset curve. |

### Available Pre-Calibrated Profiles

Profiles provide manufacturer-tested full-load and part-load COP curves, turndown ratios, and derating percentages:

* **Heat Pumps**:
  * `generic/cold_climate_heat_pump.json`: Conservative baseline for cold-climate heat pumps rated to -4°F.
  * `generic/standard_heat_pump.json`: Baseline for standard mini-splits rated to 5°F.
  * `mitsubishi/mxz_xcxxnahz2.json`: Mitsubishi Multi-Zone Hyper-Heating (H2i) C-generation series (100% capacity to 5°F, operating to -13°F).
  * `mitsubishi/mxz_xdxxnlhz.json`: Mitsubishi Multi-Zone Hyper-Heating (H2i) D-generation R-454B series.
  * `haier/xuxxms2vhb.json`: Haier FlexFit Multi-Zone series (operating to -4°F).
* **Boilers & Furnaces**:
  * `generic/modulating_condensing_boiler.json`: Generic 95% AFUE modulating boiler with 5:1 turndown.
  * `burnham/alta.json`: Burnham Alta modulating condensing series (7.5:1 turndown).
  * `bradford_white/bmfthw.json`: Bradford White Brute FT series (10:1 turndown).
  * `generic/atmospheric_cast_iron_boiler_gas.json` / `_oil.json`: Standard 83% AFUE atmospheric boilers.
  * `generic/steam_boiler_gas.json` / `_oil.json`: Standard 81% AFUE steam boilers.
  * `generic/furnace_gas_standard.json`, `generic/furnace_gas_condensing.json`, `generic/furnace_oil.json`: Ducted warm-air furnaces.

---

## 4. Spaces (Thermal Zones)

A Space represents an independently monitored room or physical zone. Each configured space generates a unified Home Assistant virtual climate entity (`climate.<space_id>_space`).

### Space Configuration Fields

| Field | Description | Type / Unit | Default |
| :--- | :--- | :--- | :--- |
| **Space ID** | Unique slug for entity generation (e.g. `living_room` yields `climate.living_room_space`). | String | Auto-slugged |
| **Display Name** | Friendly name (e.g. `Living Room`, `Primary Bedroom`). | String | Required |
| **Temperature Sensor** | Current space temperature sensor (from a dedicated room sensor or a climate entity). | `climate.*` or `sensor.*` | Required |
| **Floor Area** | Floor surface area in square feet. | Sq. Ft. | `300.0` |
| **Ceiling Height** | Average ceiling height in feet. Space volume ($A \times h$) models thermal capacitance. | Feet | `8.0` |
| **Insulation & Air Sealing** | Space envelope heat-retention score from `1` (uninsulated & drafty) to `10` (airtight Passive House). See reference table below. | Integer (1–10) | `5` |
| **Thermal Mass** | How much heat the space's walls and floors absorb and release during setback recovery, from `1` (lightweight & fast-changing) to `5` (heavy masonry/slab). | Integer (1–5) | `3` |
| **Arbitration Priority** | Weight from `1` (lowest) to `10` (highest). Resolves heating vs. cooling mode conflicts when multiple spaces share an outdoor heat pump. | Integer (1–10) | `5` |
| **Window / Door Sensor** *(Optional)* | Contact sensor. Opening the window immediately switches the space to `off` to prevent energy waste. | `binary_sensor.*` | Optional |
| **Shared Boiler Role** | How hydronic heating in this room interacts with shared zone valves: | Selector | `independent` |
| | • `independent`: Space has a dedicated zone valve or circulator. | | |
| | • `primary`: Space controls the physical thermostat driving a shared hydronic zone loop. | | |
| | • `secondary`: Space shares a hydronic zone loop controlled by a primary room; accepts heat opportunistically when the primary calls, but cannot independently fire the zone. | | |
| **Schedule Presets** *(Optional)* | Maps preset names (`occupied`, `away`, `sleep`, etc.) to Home Assistant `schedule` entities. | Entity map | Optional |

#### Insulation & Air Sealing Reference (`1–10`)

| Score | Typical Construction / Performance | Gross UA / sq ft |
| :---: | :--- | :---: |
| **1** | Uninsulated & very drafty (empty wall cavities, single-pane windows, ~18 ACH50) | `0.70` |
| **3** | Older / minimal wall insulation, single-pane with storms (~12 ACH50) | `0.42` |
| **5** | Average existing home (modest wall/attic insulation, older double-pane, ~7 ACH50) | `0.26` |
| **7** | Modern code-built / well-insulated & air-sealed (R-20 walls, low-E windows, ~3 ACH50) | `0.16` |
| **9** | High-performance / net-zero ready (~1.5 ACH50) | `0.09` |
| **10** | Airtight Passive House (PHIUS/PHI, triple-pane, 0.6 ACH50 + ERV) | `0.06` |

*Tip:* Interior or middle-floor spaces sandwiched between conditioned zones lose less heat per sq ft than corner rooms or sloped-roof attics — nudge those spaces up or down by 1–2 points as needed.

#### Thermal Mass Reference (`1–5`)

* **1 — Lightweight & fast-changing:** Drywall, carpet over plywood, minimal interior mass.
* **3 — Average:** Drywall or plaster, wood floors, typical furniture.
* **5 — Heavy thermal mass:** Exposed concrete slab, masonry, stone, or adobe.

#### Tuning Scores from Actual Daily Consumption

If you have real energy metering in Home Assistant (circuit-level heat pump monitors, smart gas/electric meters, or utility daily usage), you can dial in your `Insulation & Air Sealing` scores in a few minutes:

1. **Pick 1–3 cloudy, cold days** (average outdoor temp below ~45°F with minimal sun). Avoid tuning from a bright sunny day, where passive solar gain through windows naturally lowers actual heating below the model's baseline.
2. **Record HVAC Fusion's 24-hour estimate:** Enable the opt-in **Estimated heating cost** sensor (or sum 24 hourly bars in a Statistics Graph card) for the same 24-hour window.
3. **Calculate your actual 24-hour space-heating cost:**
   * **Sub-metered heat pumps:** `(total ODU kWh) × ($/kWh)`.
   * **Fossil fuel (gas / propane / oil):** Subtract a mild-weather non-heating baseline day (domestic hot water, cooking, dryer) from the day's fuel usage, then multiply by your fuel tariff.
   * **Whole-house electric (no sub-meter):** Subtract a mild-weather non-HVAC electric day, then multiply by `$/kWh`.
4. **Adjust `Insulation & Air Sealing` proportionally:** On the non-linear `1–10` curve, each **+1 point** reduces modeled heat loss by roughly **15–20%**, and each **−1 point** increases it by roughly **20–25%**:
   * Estimate is **~20% too high** → raise scores by **+1** (e.g., `5 → 6`).
   * Estimate is **~40% too high** → raise scores by **+2** (e.g., `5 → 7`).
   * Estimate is **~25% too low** → lower scores by **−1** (e.g., `5 → 4`).
5. **Refine per space (optional):** Once the whole-house daily total tracks within ~10–15% across a couple of cloudy days, you can nudge individual spaces up or down by 1 point based on exposure (higher for interior/middle floors, lower for corner rooms or sloped-roof attics).

#### Tuning Thermal Mass from Observed Recovery

`Thermal Mass` (`1–5`) governs the extra energy absorbed by walls, floors, and furnishings when warming a space back up from a setback. Once your `Insulation & Air Sealing` score is dialed in:

1. **Pick a clean setback recovery window** (e.g., a 1–2 hour morning warm-up where the space rises by at least `3–6°F` with minimal sun).
2. **Estimate delivered BTUs during recovery:**
   * **Heat pump:** `(ODU kWh during recovery) × 3,412 × (current COP)`.
   * **Gas / propane / oil boiler or furnace:** `(fuel used during recovery) × (BTU per unit) × (AFUE / efficiency)` (e.g., `100,000 BTU/therm` for natural gas, `91,500 BTU/gal` for propane, `138,500 BTU/gal` for #2 oil).
3. **Subtract steady-state envelope loss** during the same window (`total_heat_loss_btu_per_hr × hours` just before or after recovery). The remainder is the **thermal-mass soak** (BTUs absorbed by the space's structure).
4. **Divide by temperature rise and floor area:**
   $$\text{Effective Capacitance} = \frac{\text{Mass Soak BTUs}}{\Delta T_{\text{rise}} \times \text{Floor Area (sq ft)}}$$
   Match the result to the `1–5` scale (for ~8–9 ft ceilings):
   * **1 (Very Low):** `~0.8–1.2 BTU/(°F·sq ft)`
   * **2 (Low):** `~1.3–1.8 BTU/(°F·sq ft)`
   * **3 (Medium):** `~1.9–2.5 BTU/(°F·sq ft)`
   * **4 (High):** `~2.6–3.2 BTU/(°F·sq ft)`
   * **5 (Very High):** `~3.3–4.5+ BTU/(°F·sq ft)`
5. **Quick visual check (no math required):** Compare the morning recovery bar on HVAC Fusion's hourly cost chart against your actual metered morning spike — if the modeled recovery bump is noticeably smaller than reality, step `Thermal Mass` up by **+1**; if larger, step down by **−1**.

---

## 5. Emitters (Delivery Units)

Emitters are the physical heating and cooling terminal units installed inside a space. A space can contain multiple emitters connected to different producers (e.g. a ductless mini-split head and a hydronic baseboard loop).

> **Advisory-Only / Dumb Equipment:** The **Physical Actuation Entity** (`entity_id`) is **optional** on all emitter types. If you have a non-connected mini-split or a boiler on a dumb wall thermostat, leave the actuation entity blank—HVAC Fusion will still use the emitter's physical properties (nominal BTU, hydronic type, return-water temp) to compute a rigorous space-aware economic crossover temperature without attempting to control hardware. Even in Advisory or Dry Run mode, keep each virtual Space climate entity (`climate.<space_id>_space`) in `heat` or `heat_cool` mode (not `off`, and not in an `off` schedule gap) so heat load and `$/hr` cost/savings estimates can be modeled against your target setpoint.

### Emitter Types & Properties

#### A. Mini-Split Indoor Head (`mini_split`)
* **Producer**: Select the connected heat pump outdoor condenser (`heat_pump`).
* **Entity ID (Optional)**: The physical Home Assistant thermostat entity (`climate.*`) controlling this indoor head. Leave blank for advisory-only modeling.
* **Nominal BTU**: Rated capacity of the indoor head (e.g., `6000`, `9000`, `12000`, `18000` BTU/h).
* **Setpoint Offset (°F)**: Calibration adjustment added to target setpoints commanded to physical hardware (e.g., `+2.0` to compensate for a high-mounted sensor reading warmer than room level).

#### B. Hydronic Loop Emitter (`hydronic`)
* **Producer**: Select the connected boiler (`modulating_boiler`, `atmospheric_boiler`, `steam_boiler`).
* **Entity ID (Optional)**: Switch or climate entity controlling the zone valve or circulator (`switch.*` or `climate.*`). Leave blank for dumb-thermostat / advisory-only modeling.
* **Zone ID**: Identifier of the physical plumbing zone (e.g., `z1`, `z2`). Emitters sharing the same `zone_id` across rooms will be coordinated together.
* **Hydronic Type**: Select emitter plumbing style to model water temperature and flow rate:
  * `fin_tube_baseboard`: Design water temp 160°F, $\Delta T$ 20°F, 3.5 GPM.
  * `cast_iron_radiator`: Design water temp 150°F, $\Delta T$ 20°F, 3.5 GPM.
  * `in_floor_radiant`: Design water temp 110°F, $\Delta T$ 10°F, 4.5 GPM.
  * `kickspace`: Design water temp 140°F, $\Delta T$ 15°F, 3.0 GPM.
  * `hydro_air`: Design water temp 130°F, $\Delta T$ 25°F, 4.0 GPM.
* **Setpoint Offset (°F)**: Optional calibration offset.

#### C. Warm-Air Furnace Register (`furnace`)
* **Producer**: Select the central furnace.
* **Entity ID (Optional)**: Climate or switch entity controlling the damper or furnace call. Leave blank for advisory-only modeling.
* **Setpoint Offset (°F)**: Optional calibration offset.

---

## 6. Policies & Operational Tariffs

Accessible under **Options Flow → Policies & Tariffs**:

| Setting | Description | Default |
| :--- | :--- | :--- |
| **Control Enabled** | Master switch. When checked, sends commands to physical equipment. When unchecked, runs safely in simulation (Dry Run) mode. | `false` |
| **Cycling Deadband (°F)** | Hysteresis deadband around target setpoints to prevent rapid on/off cycling of equipment. | `2.0°F` |
| **Evaluation Interval** | Frequency in minutes at which thermodynamic state and economic dispatch are re-evaluated. | `5 min` |
| **Heat Pump Safety Band (°F)** | Safety margin added to heat pump low-ambient cutoff. For example, with a -4°F minimum envelope and a 5°F safety band, the heat pump is locked out below +1°F. | `5.0°F` |
| **Dynamic Rate Sensors** | Optional Home Assistant sensor entities reporting real-time electricity, gas, propane, or oil rates (e.g., `sensor.amber_general_usage_price`). When populated, dynamic sensor readings override static rate values. | None |

---

## 7. Using HVAC Fusion in Dashboards

Once configured, place the virtual `climate.<space_id>_space` thermostats on your Home Assistant dashboards:

* Set your desired space heating/cooling targets on the virtual thermostat.
* HVAC Fusion continually computes real-time delivered $/MMBtu costs for all available emitters, checks equipment operational envelopes, executes dual-fuel crossover dispatch, and commands the underlying physical hardware.
* Monitor entities provided for spaces and producers:
  * `sensor.hvac_fusion_economic_crossover_temperature`: Central coordinator break-even switchover temperature (with `break_even_cop`, `heat_pump`, `auxiliary_producer`, `system_phase`, and `control_enabled` attributes).
  * `sensor.hvac_fusion_<producer_id>`: Dedicated status sensor for each energy producer reporting operational state (`idle`, `heating`, `cooling`, `locked_out`) with producer-specific metrics (current COP, capacity derate, mode lock, estimated return temp, AFUE/efficiency, condensing state, and active spaces).
  * `climate.<space_id>_space`: Space virtual thermostat with room-specific state (`active_producer`, `active_delivery_units`, `cycling_emitters`, `phase`, `in_recovery`, `window_open`, and dispatch `explanation`).
