export function timeStringToMinutes(timeStr: string): number {
  if (!timeStr) return 0;
  const parts = timeStr.split(':').map((p) => parseInt(p, 10));
  const hours = parts[0] || 0;
  const minutes = parts[1] || 0;
  // HA allows 24:00:00 as end of day
  return Math.min(1440, Math.max(0, hours * 60 + minutes));
}

export function minutesToTimeString(minutes: number): string {
  const clamped = Math.min(1440, Math.max(0, Math.round(minutes)));
  const hours = Math.floor(clamped / 60);
  const mins = clamped % 60;
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:00`;
}

export function formatTimeDisplay(minutes: number, use24Hour = true): string {
  const clamped = Math.min(1440, Math.max(0, Math.round(minutes)));
  const hours = Math.floor(clamped / 60);
  const mins = clamped % 60;

  if (use24Hour) {
    return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
  }

  const period = hours >= 12 && hours < 24 ? 'PM' : 'AM';
  const displayHours = hours % 12 === 0 ? 12 : hours % 12;
  return `${displayHours}:${String(mins).padStart(2, '0')} ${period}`;
}

export function snapMinutes(minutes: number, stepSize = 15): number {
  const rounded = Math.round(minutes / stepSize) * stepSize;
  return Math.min(1440, Math.max(0, rounded));
}
