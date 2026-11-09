import {
  DAYS_OF_WEEK,
  HAScheduleBlock,
  HAScheduleItem,
  HomeAssistant,
  InternalBlock,
  ScheduleDay
} from '../types';
import { minutesToTimeString, timeStringToMinutes } from '../utils/time';

// Global broadcast channel & window event bus for synchronizing schedule cards
let syncChannel: BroadcastChannel | null = null;
try {
  if (typeof BroadcastChannel !== 'undefined') {
    syncChannel = new BroadcastChannel('ha-schedule-sync-bus');
  }
} catch {
  // BroadcastChannel unavailable in older environments
}

let activeSubscribers = 0;
let pollTimer: ReturnType<typeof setInterval> | null = null;
const lastKnownHashes = new Map<string, string>();
let latestHass: HomeAssistant | null = null;

export async function checkSchedulesForChanges(): Promise<void> {
  if (!latestHass) return;
  if (typeof document !== 'undefined' && document.hidden) return;

  try {
    const list = await latestHass.callWS<HAScheduleItem[]>({ type: 'schedule/list' });
    if (!list) return;

    for (const item of list) {
      const currentHash = JSON.stringify(item);
      const prevHash = lastKnownHashes.get(item.id);
      if (prevHash && prevHash !== currentHash) {
        lastKnownHashes.set(item.id, currentHash);
        notifyScheduleUpdated(item.id);
      } else {
        lastKnownHashes.set(item.id, currentHash);
      }
    }
  } catch {
    // Ignore WebSocket error during background poll
  }
}

function startPolling(): void {
  if (pollTimer) return;
  pollTimer = setInterval(checkSchedulesForChanges, 15000);
}

function stopPolling(): void {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && activeSubscribers > 0) {
      checkSchedulesForChanges();
    }
  });
}

export function notifyScheduleUpdated(scheduleId: string): void {
  // 1. Dispatch custom DOM event on window for components in current document
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('ha-schedule-updated', {
        detail: { scheduleId }
      })
    );
  }
  // 2. Broadcast across tabs/windows
  if (syncChannel) {
    try {
      syncChannel.postMessage({ type: 'schedule-updated', scheduleId });
    } catch {
      // Ignore
    }
  }
}

export function subscribeScheduleUpdates(callback: (scheduleId?: string) => void): () => void {
  activeSubscribers++;
  startPolling();

  const windowHandler = (e: Event) => {
    const detail = (e as CustomEvent).detail;
    callback(detail?.scheduleId);
  };

  const channelHandler = (e: MessageEvent) => {
    if (e.data?.type === 'schedule-updated') {
      callback(e.data?.scheduleId);
    }
  };

  if (typeof window !== 'undefined') {
    window.addEventListener('ha-schedule-updated', windowHandler);
  }
  if (syncChannel) {
    syncChannel.addEventListener('message', channelHandler);
  }

  return () => {
    activeSubscribers = Math.max(0, activeSubscribers - 1);
    if (activeSubscribers === 0) {
      stopPolling();
    }
    if (typeof window !== 'undefined') {
      window.removeEventListener('ha-schedule-updated', windowHandler);
    }
    if (syncChannel) {
      syncChannel.removeEventListener('message', channelHandler);
    }
  };
}

export async function fetchScheduleList(hass: HomeAssistant): Promise<HAScheduleItem[]> {
  latestHass = hass;
  try {
    const list = await hass.callWS<HAScheduleItem[]>({ type: 'schedule/list' });
    if (list) {
      for (const item of list) {
        lastKnownHashes.set(item.id, JSON.stringify(item));
      }
    }
    return list || [];
  } catch (err) {
    console.warn('[schedule-preset-card] Failed to fetch schedule list via WebSocket:', err);
    return [];
  }
}

export async function updateHASchedule(
  hass: HomeAssistant,
  scheduleId: string,
  name: string,
  days: Record<ScheduleDay, HAScheduleBlock[]>,
  icon?: string
): Promise<void> {
  latestHass = hass;
  const payload: { type: string; [key: string]: any } = {
    type: 'schedule/update',
    schedule_id: scheduleId,
    name,
    ...days
  };
  if (icon) {
    payload.icon = icon;
  }
  await hass.callWS(payload);
  const simulated = { id: scheduleId, name, icon, ...days };
  lastKnownHashes.set(scheduleId, JSON.stringify(simulated));
  notifyScheduleUpdated(scheduleId);
}

export function convertToInternalBlocks(
  scheduleItem: HAScheduleItem | undefined
): Record<ScheduleDay, InternalBlock[]> {
  const result: Record<ScheduleDay, InternalBlock[]> = {
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
    saturday: [],
    sunday: []
  };

  if (!scheduleItem) return result;

  for (const day of DAYS_OF_WEEK) {
    const rawBlocks = scheduleItem[day] || [];
    result[day] = rawBlocks.map((b, index) => {
      const data = b.data || {};
      const mode = (data.hvac_mode || data.mode || 'heat_cool').toLowerCase() as
        | 'heat_cool'
        | 'heat'
        | 'cool'
        | 'off';

      const heat =
        data.heat_to ??
        data.target_temp_low ??
        data.temperature ??
        68;
      const cool =
        data.cool_to ??
        data.target_temp_high ??
        74;

      return {
        id: `${day}_block_${index}_${Date.now()}`,
        day,
        startMinutes: timeStringToMinutes(b.from),
        endMinutes: timeStringToMinutes(b.to),
        hvac_mode: ['heat_cool', 'heat', 'cool', 'off'].includes(mode) ? mode : 'heat_cool',
        heat_to: Number(heat),
        cool_to: Number(cool),
        originalData: data
      };
    });
  }

  return result;
}

export function convertToHABlocks(
  blocksByDay: Record<ScheduleDay, InternalBlock[]>
): Record<ScheduleDay, HAScheduleBlock[]> {
  const result: Record<ScheduleDay, HAScheduleBlock[]> = {
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
    saturday: [],
    sunday: []
  };

  for (const day of DAYS_OF_WEEK) {
    // 1. Only keep valid blocks with duration >= 1 minute
    const valid = blocksByDay[day].filter((b) => b.endMinutes > b.startMinutes);
    // 2. Sort strictly by startMinutes
    valid.sort((a, b) => a.startMinutes - b.startMinutes);

    // 3. Guarantee strictly non-overlapping intervals
    const sanitized: InternalBlock[] = [];
    for (const b of valid) {
      if (sanitized.length > 0) {
        const prev = sanitized[sanitized.length - 1];
        if (prev.endMinutes > b.startMinutes) {
          prev.endMinutes = b.startMinutes;
          if (prev.endMinutes <= prev.startMinutes) {
            sanitized.pop();
          }
        }
      }
      if (b.endMinutes > b.startMinutes) {
        sanitized.push({ ...b });
      }
    }

    result[day] = sanitized.map((block) => {
      const dataPayload: Record<string, any> = {
        ...(block.originalData || {}),
        hvac_mode: block.hvac_mode
      };

      if (block.hvac_mode === 'heat_cool') {
        dataPayload.heat_to = block.heat_to;
        dataPayload.cool_to = block.cool_to;
      } else if (block.hvac_mode === 'heat') {
        dataPayload.heat_to = block.heat_to;
        delete dataPayload.cool_to;
      } else if (block.hvac_mode === 'cool') {
        dataPayload.cool_to = block.cool_to;
        delete dataPayload.heat_to;
      } else if (block.hvac_mode === 'off') {
        delete dataPayload.heat_to;
        delete dataPayload.cool_to;
      }

      return {
        from: minutesToTimeString(block.startMinutes),
        to: minutesToTimeString(block.endMinutes),
        data: dataPayload
      };
    });
  }

  return result;
}
