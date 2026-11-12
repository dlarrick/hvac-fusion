export type ScheduleDay =
  | 'monday'
  | 'tuesday'
  | 'wednesday'
  | 'thursday'
  | 'friday'
  | 'saturday'
  | 'sunday';

export const DAYS_OF_WEEK: ScheduleDay[] = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday'
];

export const DAY_LABELS: Record<ScheduleDay, { short: string; full: string }> = {
  monday: { short: 'Mon', full: 'Monday' },
  tuesday: { short: 'Tue', full: 'Tuesday' },
  wednesday: { short: 'Wed', full: 'Wednesday' },
  thursday: { short: 'Thu', full: 'Thursday' },
  friday: { short: 'Fri', full: 'Friday' },
  saturday: { short: 'Sat', full: 'Saturday' },
  sunday: { short: 'Sun', full: 'Sunday' }
};

export interface ScheduleBlockData {
  hvac_mode?: 'heat_cool' | 'heat' | 'cool' | 'off' | string;
  mode?: string;
  heat_to?: number;
  cool_to?: number;
  target_temp_low?: number;
  target_temp_high?: number;
  temperature?: number;
  [key: string]: any;
}

export interface HAScheduleBlock {
  from: string; // "HH:MM:SS" or "HH:MM"
  to: string;   // "HH:MM:SS" or "HH:MM"
  data?: ScheduleBlockData;
}

export interface HAScheduleItem {
  id: string;
  name: string;
  icon?: string;
  monday?: HAScheduleBlock[];
  tuesday?: HAScheduleBlock[];
  wednesday?: HAScheduleBlock[];
  thursday?: HAScheduleBlock[];
  friday?: HAScheduleBlock[];
  saturday?: HAScheduleBlock[];
  sunday?: HAScheduleBlock[];
}

export interface CardConfig {
  type: string;
  entity?: string;
  title?: string;
  step_size?: number; // snapping in minutes, default 15
  temperature_unit?: '°F' | '°C';
  min_deadband?: number; // default 2°F / 1°C
  min_temp?: number;
  max_temp?: number;
  compact?: boolean;
}

export interface StatusCardConfig extends CardConfig {
  show_schedule?: boolean;
  show_boost?: boolean;
  show_diagnostics?: boolean;
  diagnostics_expanded_by_default?: boolean;
  diagnostic_attributes?: string[];
}

export interface InternalBlock {
  id: string;
  day: ScheduleDay;
  startMinutes: number; // 0 to 1440
  endMinutes: number;   // 0 to 1440
  hvac_mode: 'heat_cool' | 'heat' | 'cool' | 'off';
  heat_to: number;
  cool_to: number;
  isGeneric?: boolean;
  originalData?: Record<string, any>;
}

export interface HomeAssistant {
  states: Record<string, any>;
  services?: Record<string, any>;
  config: {
    unit_system?: {
      temperature?: string;
    };
    [key: string]: any;
  };
  callWS<T = any>(params: { type: string; [key: string]: any }): Promise<T>;
  callService(domain: string, service: string, serviceData?: Record<string, any>): Promise<any>;
}
