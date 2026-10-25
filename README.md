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

HVAC Fusion is configured via the Home Assistant UI (ConfigFlow). Add the integration and provide some basic inputs, then use Configure to establish:
1. Global Sensors and Tariffs:
   - Outdoor temperature sensor
   - Utility rates, fixed or via sensor entities
   - Solar export settings
   - Safety band for heat pump operation
2. Producers
   - Choose your exact model if available, or a generic producer
   - Boilers
   - Heat pump outdoor units
3. Spaces and Emitters
   - Define the topology of the whole home
   - Define spaces and their attributes
   - Define emitters and what space(s) they affect
4. Policies
   - Dry-run mode
   - Evaluation interval
   - Extended setpoint range cycling

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
