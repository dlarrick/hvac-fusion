# HVAC Fusion

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

HVAC Fusion is a Home Assistant custom integration for intelligent management of complex dual-fuel and multi-source HVAC systems (e.g., heat pumps / mini-splits paired with hydronic boilers or furnaces).

It acts as a coordinator layer, creating virtual climate entities for living spaces while dynamically optimizing fuel switchover, avoiding multi-split refrigerant conflicts, and orchestrating underlying physical thermostats.

HVAC Fusion uses the core physics and arbitration engine from [`hvac-crossover`](https://github.com/dlarrick/hvac-crossover).

## Features

- **Economic Optimization**: Real-time COP vs. fuel tariff calculations to choose the most cost-effective heat source at current outdoor temperatures.
- **Arbitration**: Manages multi-split outdoor units (ODUs) to prevent conflicting simultaneous heating/cooling demands across indoor units (IDUs).
- **Recovery Acceleration**: Detects large temperature differentials or recovery calls to enlist high-capacity auxiliary heat (such as condensing or standard boilers).
- **Virtual Space Climate Entities**: Exposes unified climate entities to Home Assistant for intuitive schedule and thermostat card control (`heat_cool`, `heat`, `cool`, `off`).
- **Flexible Native Schedule Integration**: Follows native Home Assistant `schedule` entities via customizable preset modes.
- **Monitoring / Shadow Mode**: Supports a `control_enabled: false` mode with diagnostic reporting services to validate behavior before commanding physical equipment.

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

HVAC Fusion is currently configured via YAML. See [`custom_components/hvac_fusion/configuration.yaml.example`](custom_components/hvac_fusion/configuration.yaml.example) for a comprehensive annotated configuration example.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
