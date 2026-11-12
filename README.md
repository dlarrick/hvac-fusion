# HVAC Fusion

[![CI](https://github.com/dlarrick/hvac-fusion/actions/workflows/test.yml/badge.svg)](https://github.com/dlarrick/hvac-fusion/actions/workflows/test.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/dlarrick/hvac-fusion)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

HVAC Fusion is a Home Assistant custom integration for intelligent management of complex dual-fuel and multi-source HVAC systems (e.g., heat pumps / mini-splits paired with hydronic boilers or furnaces).

Those mini-splits you added to your old house sure are nice in the summer. But do you know how to use them effectively in heating season? Is it cold enough out that your boiler is a better choice? And if you do switch back & forth, does everybody in the house understand which thermostat to use? HVAC Fusion was designed to solve these problems!

It acts as a coordinator layer, creating virtual climate entities for living spaces while dynamically optimizing fuel switchover, avoiding multi-split refrigerant conflicts, and orchestrating underlying physical thermostats.

HVAC Fusion uses the core physics and arbitration engine from [`hvac-crossover`](https://github.com/dlarrick/hvac-crossover).

## Features

- **Economic Optimization**: Real-time COP vs. fuel tariff calculations to choose the most cost-effective heat source at current outdoor temperatures.
- **Arbitration**: Manages multi-split outdoor units (ODUs) to prevent conflicting simultaneous heating/cooling demands across indoor units (IDUs).
- **Recovery Acceleration**: Detects large temperature differentials or recovery calls to enlist high-capacity auxiliary heat (such as condensing or standard boilers).
- **Virtual Space Climate Entities**: Exposes unified climate entities to Home Assistant, controlling multiple underlying climate entities per space, for intuitive schedule and thermostat card control (`heat_cool`, `heat`, `cool`, `off`).
- **Custom Lovelace Schedule & Status Cards**: Ships with built-in dashboard cards (`schedule-preset-card` and `hvac-fusion-status-card`) for visual 7-day schedule creation and editing, real-time 24-hour preset timeline tracking, temporary comfort bump adjustments, and expandable room diagnostics.
- **Flexible Native Schedule Integration**: Follows native Home Assistant `schedule` entities via customizable preset modes.
- **Monitoring / Shadow Mode**: Supports a `control_enabled: false` mode with diagnostic reporting services to validate behavior before commanding physical equipment.

## Concept

The basic principle of HVAC Fusion:
- You divide your home into **spaces** that you would like to control the temperature of, and HVAC Fusion provides a virtual thermostat for each.
- Each space has one or more **emitters** capable of heating or cooling that space via an existing physical climate entity.
- Each emitter is connected to a **producer** with an associated efficiency profile.
- Each producer is powered by an energy (fuel) source with an associated **tariff** cost per unit of energy.

HVAC Fusion then decides, moment to moment, which emitter is most cost-effectively capable of satisfying that demand.

## Frontend Dashboard Cards

HVAC Fusion automatically bundles and serves two companion Lovelace cards for visualizing and editing climate schedules directly on your dashboards. No separate HACS install or manual resource entry is required—the integration's built-in loader serves and content-versions the bundle automatically.

```yaml
# Example Lovelace dashboard configuration
type: vertical-stack
cards:
  # Native Thermostat Card for space temperature & mode control
  - type: thermostat
    entity: climate.first_floor_space

  # Unified space status card: 24h schedule timeline, comfort bump, & diagnostics
  - type: custom:hvac-fusion-status-card
    entity: climate.first_floor_space

  # 7-day interactive weekly schedule calendar
  - type: custom:schedule-preset-card
    title: Heating & Cooling Schedules
    default_schedule: schedule.first_floor_occupied
```

### 1. `schedule-preset-card` (7-Day Schedule Calendar)
An interactive 7-day vertical timeline calendar designed to visualize and edit native Home Assistant `schedule.*` entities with multi-mode preset payloads (`hvac_mode`, `heat_to`, `cool_to`).

<img src="docs/images/schedule_preset_card.png" alt="7-Day Schedule Calendar Card" width="430">

* **Visual Editing**: Drag to create new blocks, drag block bodies to shift times, and drag top/bottom edge handles to adjust start and end times in 15-minute increments.
* **Block Actions**: Click any block to edit temperatures and HVAC mode, split a block into two, or copy blocks across weekdays, weekends, or all days.
* **Schedule Switcher**: A dropdown menu lets you quickly switch between different configured schedules on the fly.
* **Compact & Full Views**: Toggle between a compact `280px` overview (4-hour time marks) and a full `580px` detailed editor (2-hour time marks).
* **Live Synchronization**: Real-time cross-card bus and background WebSocket polling ensure edits made anywhere—in another card, another browser tab, or via external automations and services—are reflected without needing a page refresh.

### 2. `hvac-fusion-status-card` (Unified Space Status & Comfort Bump Card)
A comprehensive companion card for living space dashboards bringing together 24-hour schedule awareness, intuitive temporary temperature adjustments, and live operational diagnostics.

<img src="docs/images/hvac_fusion_status_card.png" alt="HVAC Fusion Status Card with Companion Thermostat" width="430">

* **24-Hour Preset Timeline**: Displays today's scheduled comfort bounds and active preset mode with a live high-contrast "NOW" progress needle updating every 30 seconds.
* **Temporary Comfort Bump**: Provides one-tap `🔥 Warmer (+2°)` and `❄️ Cooler (-2°)` adjustments that stack up to ±5°F and decay linearly back to the active schedule over 2 hours without mutating underlying schedule definitions.
* **Space Details & Diagnostics**: An expandable accordion displaying real-time system phase (e.g. *Plateau Maintenance*, *Setback Recovery*), active producer, window interlock state, cycling emitter status, and coordinator explanation strings.
* **Day Navigation**: Flip between days (`‹ Today ›`) to inspect upcoming schedule routines.
* **Backwards Compatibility**: Seamlessly aliases the legacy `custom:climate-preset-timeline` card type.

### Schedule Edit Mutual Exclusion Locks
When editing schedules in `schedule-preset-card`, clicking `[ ✎ Edit ]` invokes the `hvac_fusion.acquire_schedule_lock` service (setting a 300s TTL lock and exposing `schedule_editing: true` on the space's climate entity). This signals to external automations and tools that consult this lock to pause automated schedule adjustments while a human is actively making edits. When finished, clicking `[ ✓ Done ]` releases the lock. Both cards use progressive enhancement—if used standalone without HVAC Fusion, the cards operate cleanly without errors.

## Installation

### Via HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dlarrick&repository=hvac-fusion&category=integration)

Or manually add as a Custom Repository in HACS:
1. Ensure [HACS](https://hacs.xyz/) is installed in Home Assistant.
2. In HACS, navigate to **Integrations** > **Custom repositories** (or open the top-right menu).
3. Add `https://github.com/dlarrick/hvac-fusion` with category **Integration**.
4. Download and restart Home Assistant.

### Manual Installation

Copy the `custom_components/hvac_fusion` directory into your Home Assistant `<config_dir>/custom_components/` directory and restart Home Assistant.

## Configuration

HVAC Fusion is configured via the Home Assistant UI (ConfigFlow). Add the integration and provide some basic inputs, then use Configure to finish describing your HVAC system.

### Basic
Even if your HVAC system is not integrated with Home Assistant, there's still value in knowing your economic crossover point.

Configure the following:

- Outside temperature sensor. This sensor can be (and often is) from a weather forecast entity.
- Producers. Your boiler(s), heat pump(s), and (soon) furnaces. Use a generic model, or look up & contribute a profile for your actual model.
- Fuel tariffs. The price per unit for each of your fuel sources. This can be a fixed number, a sensor, or an input number.

With this configuration HVAC Fusion provides advisory and equipment entities:

- **Economic crossover temperature** -- outdoor break-even temperature where heat pump and boiler match costs (with `break_even_cop` as an attribute).
- **Producer status sensors** -- operational state (`idle`, `heating`, `cooling`, `locked_out`) and telemetry (current COP, derate, fuel rate, boiler return temp, efficiency, condensing state) for each configured unit.

### Full Configuration

If you do have smart thermostats and connected mini-splits, HVAC Fusion can do much more. Use the Configuration to define your Spaces and Emitters as described above. HVAC Fusion will create a new virtual thermostat for each space. Use these in your dashboards instead of the underlying per-emitter thermostats.

For complete field descriptions and setup details, see the [Configuration Reference](CONFIGURATION.md).

1. Environmental Sensors:
   - Outdoor temperature sensor
   - Solar export sensor (optional)
2. Manage Producers:
   - Boilers (natural gas or propane, with manufacturer profiles or generic/custom)
   - Heat pump outdoor units (with manufacturer profiles or generic/custom)
3. Manage Spaces:
   - Define spaces (rooms or zones), temperature sensors, and room dimensions
   - Arbitration priority (resolves heat/cool mode conflicts across multi-split heads sharing an outdoor unit)
   - Window / door sensors (pauses HVAC in the space when open)
   - Shared boiler roles (`independent`, `primary`, `secondary` for multi-space hydronic loops)
   - **Emitters**: Attach heating/cooling delivery units to each space, along with the controlling climate entity
   - **Schedule Presets**: Link space presets directly to Home Assistant `schedule` entities defining time-of-day operating mode & setpoints
4. Tariffs, Safety Limits & Operational Policies:
   - Fuel and electricity tariffs (fixed rates or dynamic `sensor` / `input_number` entities for electric, natural gas, propane, and heating oil)
   - Heat pump low ambient safety band
   - Enable physical control (toggle for dry-run mode)
   - Setpoint cycling hysteresis band
   - Evaluation interval

#### Fuel Tariffs

When configuring energy rates for economic crossover calculations, consider how each fuel is billed:

* **Utility-Metered Energy (Electricity & Natural Gas):** Metered and billed on-demand per unit consumed (kWh, therm, or CCF). Enter your effective marginal utility rate (including volumetric delivery and supply charges, but excluding fixed monthly meter charges). You can also link dynamic `sensor` entities for time-of-use (TOU) or real-time tariffs.
* **Bulk-Delivered Fuels (Heating Oil & Propane):** Delivered and paid for in bulk to on-site storage tanks. When deciding what rate to enter:
  * **Marginal Replacement Cost (Recommended):** In most cases, the economically optimal rate to configure is the **expected cost to replace consumed fuel** (the current market spot price or anticipated next delivery price), rather than the historical price paid on the previous delivery ticket. Treating fuel already sitting in your tank as a sunk cost ensures HVAC Fusion does not burn through cheap off-season fuel prematurely if replacing it mid-winter will be significantly more expensive.
  * **Pre-Buy Contracts or Sufficient Seasonal Reserve (Exception):** If you locked in a fixed pre-buy contract for the winter, or your tank volume is large enough to comfortably carry you through the entire heating season without needing a refill, the contracted rate (or paid price) represents your true marginal replacement cost.

You can enter a static rate per gallon in the Policies & Tariffs hub or provide an `input_number` / template `sensor` to track changing market or supplier rates dynamically.

#### Examples

**Open Floorplan**
This space has one hydronic zone off a boiler, and two mini-split heads in different locations. Define this as one space, with all three emitters. The hydronic zone should be marked as "Independent" shared boiler role.

**Bedrooms**
This space has one hydronic zone for the whole floor, and each bedroom has its own mini-split head. Define this as one space per room, with its own mini-split and the boiler zone in each. Whichever space has the primary thermostat for the boiler zone should be marked "Primary" and the others marked "Secondary".

### Dry Run Mode

Maybe you're not comfortable turning this all on at once. There is a dry-run mode (enabled by default) where HVAC Fusion doesn't actually control the individual emitter thermostats, but just shows what it would have done (indicated by `control_enabled: false` on the crossover sensor).

## Entities & Attributes

HVAC Fusion creates entities for your spaces, central plant advisory, and equipment producers:

### Virtual Space Climate Entities (`climate.<space_id>_fusion`)
A virtual thermostat is created for each configured living space to manage target setpoints, presets, and schedules on your dashboards:
* **State / Modes:** `heat_cool`, `heat`, `cool`, `off`
* **HVAC Action:** `heating`, `cooling`, `idle`, `off`
* **Target Setpoints:** Single target temperature or dual heating/cooling setpoints (`target_temp_low`, `target_temp_high`)
* **State Attributes:**
  * `space_id`: Identifier for the thermal zone.
  * `preset_mode`: Currently active preset mode (`manual` or user-defined preset).
  * `active_schedule`: Entity ID of the Home Assistant `schedule` entity currently driving this preset (if linked).
  * `active_producer`: ID of the producer currently supplying heating or cooling to this space (`None` when idle).
  * `active_delivery_units`: List of emitter delivery unit IDs currently commanded active.
  * `cycling_emitters`: List of emitter IDs currently held by setpoint limit cycling hysteresis.
  * `window_open`: `true` if an associated window or door contact sensor is currently open (pausing conditioning).
  * `phase`: Operational phase for this living space (`plateau_maintenance`, `setback_recovery`, or `passive_ventilation`).
  * `in_recovery`: `true` if the room has an active thermal deficit meeting or exceeding the setback recovery threshold.
  * `explanation`: Human-readable summary of the coordinator's dispatch reasoning for this space.

### Economic Crossover Temperature Sensor (`sensor.<coordinator_id>_economic_crossover_temperature`)
Central plant advisory sensor indicating the outdoor temperature break-even point between heat pump heating and auxiliary fuel:
* **State:** Outdoor crossover temperature in `°F` (`device_class: temperature`). If the outdoor temperature is below this threshold, auxiliary heat is more cost-effective than running the heat pump.
* **State Attributes:**
  * `break_even_cop`: The coefficient of performance the heat pump must achieve to match auxiliary fuel cost at current tariffs.
  * `heat_pump`: Equipment ID of the heat pump evaluated in the crossover calculation.
  * `auxiliary_producer`: Equipment ID of the auxiliary boiler or furnace compared against the heat pump.
  * `system_phase`: Macro-system operational phase (`plateau_maintenance`, `setback_recovery`, `passive_ventilation`, `away_coast`).
  * `control_enabled`: `true` when physical thermostat actuation is enabled; `false` in simulation (dry-run) mode.

### Producer Status Sensors (`sensor.<coordinator_id>_<producer_id>`)
A dedicated status sensor is created for each piece of heating or cooling equipment (heat pump outdoor unit, boiler, or furnace):
* **State:** Operational status (`idle`, `heating`, `cooling`, `locked_out`).
* **Common Attributes:**
  * `producer_id`: Equipment identifier.
  * `producer_type`: Equipment archetype (`inverter_heat_pump`, `modulating_boiler`, `atmospheric_boiler`, `steam_boiler`, `furnace`).
  * `nominal_capacity_btu`: Configured nominal rated capacity in BTU/h.
  * `active_spaces`: List of living space IDs currently calling this producer.
  * `active_delivery_units`: List of emitter delivery unit IDs currently commanded on.
* **Heat Pump Specific Attributes:**
  * `current_cop`: Real-time estimated COP at current outdoor temperature.
  * `capacity_derate_pct`: Percentage of nominal heating capacity available at current outdoor temperature.
  * `mode_lock`: Multi-split refrigerant cycle mode lock enforced across indoor heads (`heat`, `cool`, or `None`).
  * `safety_lockout`: `true` if outdoor temperature is below the low-ambient envelope plus safety margin.
* **Boiler & Furnace Specific Attributes:**
  * `fuel_type`: Energy source (`natural_gas`, `oil`, `propane`).
  * `rated_afue`: Rated combustion efficiency.
  * `has_outdoor_reset`: `true` if modulating boiler outdoor reset curve is enabled.
  * `estimated_return_temp_f`: Estimated return water temperature (for modulating condensing boilers).
  * `estimated_efficiency`: Current estimated operating combustion efficiency based on load and return water temperature.
  * `condensing_state`: Flue gas condensing state (`condensing` vs. `dry`).

## Acknowledgments & Attribution

The visual presentation, dual-setpoint interaction, and weekly calendar layout in `schedule-preset-card` are adapted from and inspired by the excellent work of **[arozoire](https://github.com/arozoire)** in [`schedule_creator`](https://github.com/arozoire/schedule_creator) and `weekly-schedule-card` (MIT Licensed), re-engineered here to operate natively with Home Assistant's built-in `schedule.*` helper entities and Core WebSocket APIs.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
