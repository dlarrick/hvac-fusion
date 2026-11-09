/**
 * Temperature color scales and cell layout adaptation
 */

function clamp(val: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, val));
}

function interpolateHsl(
  h1: number, s1: number, l1: number,
  h2: number, s2: number, l2: number,
  t: number
): string {
  const h = h1 + (h2 - h1) * t;
  const s = s1 + (s2 - s1) * t;
  const l = l1 + (l2 - l1) * t;
  return `hsl(${Math.round(h)}, ${Math.round(s)}%, ${Math.round(l)}%)`;
}

/**
 * Heating color scale:
 * Warmer -> deeper red/coral (#dc2626, hsl(0, 80%, 48%))
 * Cooler -> paler warm peach/cream (#fed7aa, hsl(32, 90%, 86%))
 */
export function getHeatColor(temp: number, unit: '°F' | '°C' = '°F'): string {
  const minTemp = unit === '°C' ? 10 : 50;
  const maxTemp = unit === '°C' ? 24 : 75;
  const t = clamp((temp - minTemp) / (maxTemp - minTemp), 0, 1);

  // From pale peach (h: 34, s: 90%, l: 86%) to deep rich crimson (h: 0, s: 82%, l: 48%)
  return interpolateHsl(34, 90, 86, 0, 82, 48, t);
}

/**
 * Cooling color scale:
 * Cooler -> deeper blue/azure (#0369a1, hsl(202, 90%, 38%))
 * Warmer -> paler ice blue/white (#e0f2fe, hsl(204, 85%, 90%))
 */
export function getCoolColor(temp: number, unit: '°F' | '°C' = '°F'): string {
  const minTemp = unit === '°C' ? 18 : 65;
  const maxTemp = unit === '°C' ? 28 : 82;
  // Note: cooler temperature has higher intensity (t=1 at minTemp, t=0 at maxTemp)
  const t = clamp((maxTemp - temp) / (maxTemp - minTemp), 0, 1);

  // From pale ice blue (h: 204, s: 85%, l: 90%) to deep rich azure (h: 202, s: 92%, l: 38%)
  return interpolateHsl(204, 85, 90, 202, 92, 38, t);
}

/**
 * Returns optimal text color for contrast against a given temperature
 */
export function getHeatTextColor(temp: number, unit: '°F' | '°C' = '°F'): string {
  const threshold = unit === '°C' ? 18 : 64;
  return temp >= threshold ? '#ffffff' : '#431407';
}

export function getCoolTextColor(temp: number, unit: '°F' | '°C' = '°F'): string {
  const threshold = unit === '°C' ? 22 : 72;
  return temp <= threshold ? '#ffffff' : '#082f49';
}

/**
 * In a vertical-time grid (00:00 - 24:00 down):
 * - Normal duration (height >= width): vertical split (Top Cool, Bottom Heat)
 * - Short duration (width > height): horizontal split rotated 90° (Left Heat, Right Cool)
 */
export function getSplitOrientation(width: number, height: number): 'stacked' | 'side-by-side' {
  // If height is less than width or less than ~38px, side-by-side gives far better legibility
  if (height < 38 || width > height) {
    return 'side-by-side';
  }
  return 'stacked';
}
