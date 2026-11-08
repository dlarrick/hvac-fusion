# HVAC Fusion

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
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
- **Flexible Native Schedule Integration**: Follows native Home Assistant `schedule` entities via customizable preset modes.
- **Monitoring / Shadow Mode**: Supports a `control_enabled: false` mode with diagnostic reporting services to validate behavior before commanding physical equipment.

## Concept

The basic principle of HVAC Fusion:
- You divide your home into **spaces** that you would like to control the temperature of, and HVAC Fusion provides a virtual thermostat for each.
- Each space has one or more **emitters** capable of heating or cooling that space via an existing physical climate entity.
- Each emitter is connected to a **producer** with an associated efficiency profile.
- Each producer is powered by an energy (fuel) source with an associated **tariff** cost per unit of energy.

HVAC Fusion then decides, moment to moment, which emitter is most cost-effectively capable of satisfying that demand.

## Installation

### Via HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in Home Assistant.
2. In HACS, add this repository as a **Custom Repository**:
   - URL: `https://github.com/dlarrick/hvac-fusion`
   - Category: `Integration`
3. Download and restart Home Assistant.

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

With this configuration HVAC Fusion provides two sensors:

- Economic crossover temperature -- if it's colder than this, it's cheaper to use your boiler
- Economic crossover COP -- another way of stating the same thing. Heat pumps become less efficient as temperatures get colder. This is the break-even Coefficient of Performance.

### Full Configuration

If you do have smart thermostats and connected mini-splits, HVAC Fusion can do much more. Use the Configuration to define your Spaces and Emitters as described above. HVAC Fusion will create a new virtual thermostat for each space. Use these in your dashboards instead of the underlying per-emitter thermostats.

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
   - Fuel and electricity tariffs (fixed rates or dynamic `sensor` / `input_number` entities for electric, natural gas, and propane)
   - Heat pump low ambient safety band
   - Enable physical control (toggle for dry-run mode)
   - Setpoint cycling hysteresis band
   - Evaluation interval

#### Examples

**Open Floorplan**
This space has one hydronic zone off a boiler, and two mini-split heads in different locations. Define this as one space, with all three emitters. The hydronic zone should be marked as "Independent" shared boiler role.

**Bedrooms**
This space has one hydronic zone for the whole floor, and each bedroom has its own mini-split head. Define this as one space per room, with its own mini-split and the boiler zone in each. Whichever space has the primary thermostat for the boiler zone should be marked "Primary" and the others marked "Secondary".

### Dry Run Mode

Maybe you're not comfortable turning this all on at once. There is a dry-run mode (enabled by default) where HVAC Fusion doesn't actually control the individual emitter thermostats, but just shows what it would have done.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
