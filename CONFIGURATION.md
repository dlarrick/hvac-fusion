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

A Space represents an independently monitored room or physical zone. Each configured space generates a unified Home Assistant virtual climate entity (`climate.<space_id>_fusion`).

### Space Configuration Fields

| Field | Description | Type / Unit | Default |
| :--- | :--- | :--- | :--- |
| **Space ID** | Unique slug for entity generation (e.g. `living_room` yields `climate.living_room_fusion`). | String | Auto-slugged |
| **Display Name** | Friendly name (e.g. `Living Room`, `Primary Bedroom`). | String | Required |
| **Temperature Sensor** | Current space temperature sensor (from a dedicated room sensor or a climate entity). | `climate.*` or `sensor.*` | Required |
| **Floor Area** | Floor surface area in square feet. | Sq. Ft. | `300.0` |
| **Ceiling Height** | Average ceiling height in feet. Room volume ($A \times h$) models thermal heat loss. | Feet | `8.0` |
| **Arbitration Priority** | Weight from `1` (lowest) to `10` (highest). Resolves heating vs. cooling mode conflicts when multiple spaces share an outdoor heat pump. | Integer (1–10) | `5` |
| **Window / Door Sensor** *(Optional)* | Contact sensor. Opening the window immediately switches the space to `off` to prevent energy waste. | `binary_sensor.*` | Optional |
| **Shared Boiler Role** | How hydronic heating in this room interacts with shared zone valves: | Selector | `independent` |
| | • `independent`: Space has a dedicated zone valve or circulator. | | |
| | • `primary`: Space controls the physical thermostat driving a shared hydronic zone loop. | | |
| | • `secondary`: Space shares a hydronic zone loop controlled by a primary room; accepts heat opportunistically when the primary calls, but cannot independently fire the zone. | | |
| **Schedule Presets** *(Optional)* | Maps preset names (`occupied`, `away`, `sleep`, etc.) to Home Assistant `schedule` entities. | Entity map | Optional |

---

## 5. Emitters (Delivery Units)

Emitters are the physical heating and cooling terminal units installed inside a space. A space can contain multiple emitters connected to different producers (e.g. a ductless mini-split head and a hydronic baseboard loop).

### Emitter Types & Properties

#### A. Mini-Split Indoor Head (`mini_split`)
* **Producer**: Select the connected heat pump outdoor condenser (`heat_pump`).
* **Entity ID**: The physical Home Assistant thermostat entity (`climate.*`) controlling this indoor head.
* **Nominal BTU**: Rated capacity of the indoor head (e.g., `6000`, `9000`, `12000`, `18000` BTU/h).
* **Setpoint Offset (°F)**: Calibration adjustment added to target setpoints commanded to physical hardware (e.g., `+2.0` to compensate for a high-mounted sensor reading warmer than room level).

#### B. Hydronic Loop Emitter (`hydronic`)
* **Producer**: Select the connected boiler (`modulating_boiler`, `atmospheric_boiler`, `steam_boiler`).
* **Entity ID**: Switch or climate entity controlling the zone valve or circulator (`switch.*` or `climate.*`).
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
* **Entity ID**: Climate or switch entity controlling the damper or furnace call.
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

Once configured, place the virtual `climate.<space_id>_fusion` thermostats on your Home Assistant dashboards:

* Set your desired space heating/cooling targets on the virtual thermostat.
* HVAC Fusion continually computes real-time delivered $/MMBtu costs for all available emitters, checks equipment operational envelopes, executes dual-fuel crossover dispatch, and commands the underlying physical hardware.
* Monitor entities provided for spaces and producers:
  * `sensor.hvac_fusion_economic_crossover_temperature`: Central coordinator break-even switchover temperature (with `break_even_cop`, `heat_pump`, `auxiliary_producer`, `system_phase`, and `control_enabled` attributes).
  * `sensor.hvac_fusion_<producer_id>`: Dedicated status sensor for each energy producer reporting operational state (`idle`, `heating`, `cooling`, `locked_out`) with producer-specific metrics (current COP, capacity derate, mode lock, estimated return temp, AFUE/efficiency, condensing state, and active spaces).
  * `climate.<space_id>_fusion`: Space virtual thermostat with room-specific state (`active_producer`, `active_delivery_units`, `cycling_emitters`, `phase`, `in_recovery`, `window_open`, and dispatch `explanation`).
