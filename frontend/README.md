# Climate Preset Schedule Card (`schedule-preset-card`)

A Home Assistant Lovelace custom card for visually viewing and editing climate preset schedules backed by native **`schedule.*`** helper entities.

Designed specifically to partner with multi-emitter climate coordinators like **`hvac-fusion`**, which expect active time blocks to carry target HVAC modes and dual setpoint ranges (`heat_to`, `cool_to`) inside their `data` dictionary.

---

## Features

* **Native HA WebSocket Backend**: Reads and updates native `schedule.*` entities directly using Home Assistant's Core `schedule/list` and `schedule/update` WebSocket APIs—no custom daemons or non-standard storage engines required.
* **Dual Setpoint Visualization**:
  * **Cooling Scale (Blue)**: Colder targets are deeper azure/navy; warmer targets are soft ice blue.
  * **Heating Scale (Red/Warm)**: Warmer targets are deep rich crimson; cooler targets are soft peach/cream.
  * **Unconfigured Gaps**: Rendered in dark neutral gray (handled by `hvac-fusion` as system `off`).
* **Aspect-Ratio-Aware Block Rotation**:
  * **Normal/Long duration blocks**: Vertical split (Top half cooling blue, bottom half heating red).
  * **Short duration blocks (< 45 min)**: Division rotates by 90° into a side-by-side format (Left heating, right cooling) so temperature values and color bands remain legible.
* **Interactive Editing**:
  * Drag top and bottom edges to resize start/end times with 15-minute snapping.
  * Click anywhere on an empty track to create a new block.
  * Click any block to open the preset modal dialog:
    * Mode selector: `heat_cool`, `heat`, `cool`, `off`.
    * Dual setpoint steppers with minimum deadband enforcement.
    * Quick copy shortcuts: "Copy to Weekdays", "Copy to Weekend", "Copy to All 7 Days".
    * Delete block button.
* **Read-Only Detection**: Displays a badge if a schedule was defined in YAML, preventing accidental desync.

---

## Installation & Configuration

### Lovelace Dashboard Resource

Add the compiled bundle to your Home Assistant dashboard resources:
```yaml
url: /local/schedule-preset-card/schedule-preset-card.js
type: module
```

### Card Configuration Example

```yaml
type: custom:schedule-preset-card
title: "1st Floor Climate Schedule"
entity: schedule.first_floor_occupied
temperature_unit: "°F"     # Optional: "°F" or "°C" (default: "°F")
step_size: 15              # Snapping interval in minutes (default: 15)
min_deadband: 2            # Minimum degrees between heat and cool (default: 2)
```

---

## Development & Local Preview

To test or develop locally without requiring a live Home Assistant server:

```bash
cd schedule-preset-card
npm install
npm run dev
```

Open `http://localhost:5173` to interact with the mock schedule preview.

To build the production bundle:
```bash
npm run build
```
Outputs to `dist/schedule-preset-card.js`.
