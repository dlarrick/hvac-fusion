import { LitElement, html, css, PropertyValues } from 'lit';
import { property, state } from 'lit/decorators.js';
import {
  DAYS_OF_WEEK,
  DAY_LABELS,
  HAScheduleItem,
  HomeAssistant,
  InternalBlock,
  ScheduleDay
} from './types';
import {
  convertToHABlocks,
  convertToInternalBlocks,
  fetchScheduleList,
  findScheduleInList,
  isForeignSchedule,
  subscribeScheduleUpdates,
  updateHASchedule
} from './services/ha-schedule';
import { formatTimeDisplay, snapMinutes } from './utils/time';
import {
  getCoolColor,
  getCoolTextColor,
  getHeatColor,
  getHeatTextColor
} from './utils/colors';
import './components/preset-dialog';
import './components/timeline-editor';

export interface TimelineCardConfig {
  type: string;
  entity?: string;
  title?: string;
  temperature_unit?: '°F' | '°C';
  step_size?: number;
  min_deadband?: number;
}

export class ClimatePresetTimeline extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private config!: TimelineCardConfig;

  @state() private schedules: HAScheduleItem[] = [];
  @state() private activeScheduleId = '';
  @state() private currentPresetMode = '';
  @state() private isManual = false;
  @state() private isEditMode = false;
  @state() private isYamlSchedule = false;
  @state() private isForeign = false;
  @state() private scheduleNotFound = false;
  private _lastLoadedScheduleHash = '';

  @state() private blocksByDay: Record<ScheduleDay, InternalBlock[]> = {
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
    saturday: [],
    sunday: []
  };

  @state() private selectedDayIndex = (new Date().getDay() + 6) % 7; // Monday = 0
  @state() private activeEditingBlock: InternalBlock | null = null;
  @state() private isSaving = false;

  // Interaction tracking for horizontal dragging & resizing
  private dragAction: {
    type: 'resize-start' | 'resize-end' | 'create';
    blockId?: string;
    abuttingBlockId?: string;
    initialX: number;
    initialMinute: number;
    currentMinute?: number;
    initialStart?: number;
    initialEnd?: number;
    hasDragged: boolean;
  } | null = null;
  private lastDragEndTime = 0;
  private _timer?: ReturnType<typeof setInterval>;
  private _unsubscribeSync?: () => void;
  private _heartbeatTimer?: ReturnType<typeof setInterval>;

  public static async getConfigElement(): Promise<HTMLElement> {
    return document.createElement('climate-preset-timeline-editor');
  }

  public static getStubConfig(): Record<string, any> {
    return {
      type: 'custom:climate-preset-timeline',
      title: '',
      entity: '',
      temperature_unit: '°F',
      step_size: 15,
      min_deadband: 2
    };
  }

  connectedCallback() {
    super.connectedCallback();
    // Update red 'NOW' needle position every 30 seconds
    this._timer = setInterval(() => this.requestUpdate(), 30000);

    // Subscribe to cross-card schedule updates
    this._unsubscribeSync = subscribeScheduleUpdates(() => {
      this.syncFromHass(true);
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = undefined;
    }
    if (this._unsubscribeSync) {
      this._unsubscribeSync();
      this._unsubscribeSync = undefined;
    }
    if (this._heartbeatTimer) {
      clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = undefined;
    }
    if (this.isEditMode) {
      this.sendLockSignal(false);
    }
  }

  static styles = css`
    :host {
      display: block;
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--primary-text-color, #e1e7ec);
      user-select: none;
      -webkit-user-select: none;
    }

    ha-card {
      background: var(--ha-card-background, var(--card-background-color, #181c24));
      border-radius: var(--ha-card-border-radius, 16px);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      padding: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    /* Header */
    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: nowrap;
      gap: 8px;
      min-width: 0;
    }

    .title-box {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      flex: 1 1 auto;
      overflow: hidden;
    }

    .card-title {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--primary-text-color, #ffffff);
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
      flex-shrink: 1;
    }

    .preset-chip {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 3px 9px;
      border-radius: 12px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary-color, #38bdf8);
      border: 1px solid rgba(56, 189, 248, 0.3);
      text-transform: capitalize;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 160px;
      flex-shrink: 2;
    }
    .preset-chip.manual {
      background: rgba(234, 179, 8, 0.15);
      color: #eab308;
      border-color: rgba(234, 179, 8, 0.3);
    }
    .yaml-badge {
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(234, 179, 8, 0.15);
      color: #eab308;
      border: 1px solid rgba(234, 179, 8, 0.3);
      white-space: nowrap;
      flex-shrink: 0;
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }

    /* Day Navigation */
    .day-nav {
      display: flex;
      align-items: center;
      gap: 2px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      padding: 2px 4px;
      flex-shrink: 0;
    }

    .nav-btn {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #9ca3af);
      font-size: 1rem;
      cursor: pointer;
      padding: 2px 6px;
      border-radius: 4px;
      transition: all 0.15s;
    }
    .nav-btn:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }

    .day-label {
      font-size: 0.82rem;
      font-weight: 600;
      padding: 0 4px;
      min-width: 70px;
      text-align: center;
      white-space: nowrap;
    }

    .edit-toggle-btn {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--secondary-text-color, #9ca3af);
      font-size: 0.78rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s ease-in-out;
    }
    .edit-toggle-btn:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }
    .edit-toggle-btn.active {
      background: rgba(56, 189, 248, 0.18);
      border-color: #38bdf8;
      color: #38bdf8;
    }
    .edit-toggle-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    /* Horizontal Track Container */
    .timeline-track-wrap {
      position: relative;
      width: 100%;
      height: 64px;
      background: rgba(0, 0, 0, 0.3);
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      overflow: hidden;
      touch-action: none;
      cursor: default;
      transition: border-color 0.2s;
    }
    .timeline-track-wrap.editing {
      cursor: crosshair;
      border-color: rgba(56, 189, 248, 0.45);
    }
    .timeline-track-wrap.editing .timeline-block {
      cursor: pointer;
    }
    .timeline-track-wrap:not(.editing) .timeline-block {
      cursor: default;
    }
    .timeline-track-wrap:not(.editing) .h-resize-handle {
      display: none;
    }

    .manual-overlay {
      position: absolute;
      top: 0;
      bottom: 0;
      left: 0;
      right: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: rgba(24, 28, 36, 0.72);
      color: #eab308;
      font-size: 0.85rem;
      font-weight: 500;
      pointer-events: none;
      z-index: 15;
    }
    .manual-overlay.error {
      color: #f87171;
    }

    /* Horizontal Grid Ticks (every 4 hours) */
    .time-grid-line {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 1px;
      background: rgba(255, 255, 255, 0.05);
      pointer-events: none;
    }

    /* Blocks */
    .timeline-block {
      position: absolute;
      top: 2px;
      bottom: 2px;
      border-radius: 6px;
      overflow: hidden;
      cursor: pointer;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4);
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      transition: border-color 0.15s;
    }
    .timeline-block:hover {
      border-color: rgba(255, 255, 255, 0.5);
      z-index: 10;
    }

    .band-cool,
    .band-heat {
      flex: 1;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.72rem;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      min-height: 0;
    }

    .band-generic {
      flex: 1;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.70rem;
      font-weight: 600;
      color: #cbd5e1;
      background: rgba(100, 116, 139, 0.35);
      border: 1px dashed rgba(148, 163, 184, 0.7);
      text-transform: uppercase;
      letter-spacing: 0.03em;
      min-height: 0;
    }

    /* Horizontal Resize Handles (Left / Right edges) */
    .h-resize-handle {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 10px;
      z-index: 20;
      cursor: ew-resize;
    }
    .h-resize-handle.left {
      left: 0;
    }
    .h-resize-handle.right {
      right: 0;
    }
    .h-resize-handle:hover {
      background: rgba(255, 255, 255, 0.25);
    }

    /* NOW Needle */
    .now-needle {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 2px;
      background: #ffffff;
      box-shadow: 0 0 1px 1px rgba(0, 0, 0, 0.7), 0 0 6px 1px rgba(244, 63, 94, 0.85);
      z-index: 30;
      pointer-events: none;
    }
    .now-needle::after {
      content: '';
      position: absolute;
      top: 0;
      left: 50%;
      transform: translateX(-50%);
      width: 0;
      height: 0;
      border-left: 4px solid transparent;
      border-right: 4px solid transparent;
      border-top: 5px solid #ffffff;
      filter: drop-shadow(0 0 2px rgba(244, 63, 94, 0.9));
    }

    /* Time Axis Labels (Under track) */
    .time-axis-horizontal {
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      color: var(--secondary-text-color, #71717a);
      padding: 0 2px;
    }

    /* Carve preview overlay */
    .carve-overlay {
      position: absolute;
      top: 2px;
      bottom: 2px;
      border: 2px dashed var(--primary-color, #38bdf8);
      background: rgba(56, 189, 248, 0.28);
      border-radius: 6px;
      pointer-events: none;
      z-index: 25;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.72rem;
      font-weight: 700;
      color: #fff;
    }

    /* Floating drag time badge */
    .drag-h-indicator {
      position: absolute;
      top: -8px;
      bottom: -8px;
      width: 0;
      pointer-events: none;
      z-index: 50;
      display: flex;
      flex-direction: column;
      align-items: center;
      transform: translateX(-50%);
    }

    .drag-h-line {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 2px;
      background: var(--primary-color, #38bdf8);
      box-shadow: 0 0 8px rgba(56, 189, 248, 0.9);
    }

    .drag-h-pill {
      position: relative;
      top: -24px;
      background: #090d16;
      color: #38bdf8;
      border: 1.5px solid #38bdf8;
      padding: 2px 7px;
      border-radius: 6px;
      font-size: 0.74rem;
      font-weight: 700;
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.8);
      white-space: nowrap;
    }
  `;

  public setConfig(config: TimelineCardConfig) {
    if (!config) throw new Error('Invalid configuration');
    this.config = {
      temperature_unit: '°F',
      step_size: 15,
      min_deadband: 2,
      ...config
    };
  }

  public getCardSize(): number {
    return 3;
  }

  public willUpdate(changedProps: PropertyValues) {
    if (changedProps.has('hass') && this.hass) {
      this.syncFromHass();
    }
  }

  private async syncFromHass(forceReload = false) {
    if (!this.hass || this.isSaving || this.dragAction || this.activeEditingBlock) return;

    // Load storage schedules
    const list = await fetchScheduleList(this.hass);
    this.schedules = list;

    // Inspect the bound entity
    const targetEntityId = this.config.entity;
    let scheduleEntityId: string | null = null;

    if (targetEntityId) {
      const stateObj = this.hass.states[targetEntityId];

      if (targetEntityId.startsWith('climate.')) {
        // Space leader climate entity!
        const attrs = stateObj?.attributes || {};
        this.currentPresetMode = attrs.preset_mode || 'unknown';
        this.isManual = attrs.preset_mode === 'manual';

        if (!this.isManual) {
          // Check active_schedule attribute
          const activeSched = attrs.active_schedule;
          const presetsMap = attrs.presets || {};

          if (activeSched && typeof activeSched === 'string') {
            scheduleEntityId = activeSched;
          } else if (presetsMap[this.currentPresetMode]) {
            scheduleEntityId = String(presetsMap[this.currentPresetMode]);
          }
        }
      } else if (targetEntityId.startsWith('schedule.')) {
        scheduleEntityId = targetEntityId;
      }
    }

    if (this.isManual) {
      this.activeScheduleId = '';
      this._lastLoadedScheduleHash = '';
      this.isEditMode = false;
      this.isYamlSchedule = false;
      this.isForeign = false;
      this.scheduleNotFound = false;
      this.blocksByDay = {
        monday: [],
        tuesday: [],
        wednesday: [],
        thursday: [],
        friday: [],
        saturday: [],
        sunday: []
      };
      return;
    }

    // Look up schedule strictly by entity_id
    let item: HAScheduleItem | undefined;
    if (scheduleEntityId) {
      item = await findScheduleInList(list, scheduleEntityId, this.hass);
    } else if (list.length > 0) {
      item = list[0];
    }

    if (item && !this.isSaving && !this.dragAction && !this.activeEditingBlock) {
      this.isYamlSchedule = false;
      this.isForeign = isForeignSchedule(item);
      this.scheduleNotFound = false;

      if (this.isForeign && this.isEditMode) {
        this.isEditMode = false;
        this.sendLockSignal(false);
      }

      const itemHash = JSON.stringify(item);
      if (
        forceReload ||
        item.id !== this.activeScheduleId ||
        itemHash !== this._lastLoadedScheduleHash
      ) {
        this.activeScheduleId = item.id;
        this._lastLoadedScheduleHash = itemHash;
        this.blocksByDay = convertToInternalBlocks(item);
      }
    } else if (scheduleEntityId && !item) {
      // Check if entity exists in hass.states (e.g. YAML schedule)
      const fullEntityId = scheduleEntityId.startsWith('schedule.')
        ? scheduleEntityId
        : `schedule.${scheduleEntityId}`;
      const stateObj = this.hass.states[fullEntityId];
      if (stateObj) {
        this.isYamlSchedule = true;
        this.isForeign = false;
        this.scheduleNotFound = false;
      } else {
        this.isYamlSchedule = false;
        this.isForeign = false;
        this.scheduleNotFound = true;
      }
      this.activeScheduleId = '';
      this.isEditMode = false;
      this.blocksByDay = {
        monday: [],
        tuesday: [],
        wednesday: [],
        thursday: [],
        friday: [],
        saturday: [],
        sunday: []
      };
    }
  }

  private sendLockSignal(acquire: boolean) {
    if (!this.hass || !this.activeScheduleId) return;
    const action = acquire ? 'acquire_schedule_lock' : 'release_schedule_lock';
    // Progressive enhancement: only dispatch lock if hvac_fusion integration is installed
    if (!this.hass.services?.hvac_fusion?.[action]) return;

    this.hass.callService('hvac_fusion', action, {
      schedule_id: this.activeScheduleId,
      ...(acquire ? { duration: 300 } : {})
    });
  }

  private toggleEditMode() {
    if (this.isManual || this.isYamlSchedule || this.isForeign || this.scheduleNotFound) return;
    this.isEditMode = !this.isEditMode;

    if (this.isEditMode) {
      this.sendLockSignal(true);
      if (this._heartbeatTimer) clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = setInterval(() => {
        if (this.isEditMode) this.sendLockSignal(true);
      }, 60000);
    } else {
      if (this._heartbeatTimer) {
        clearInterval(this._heartbeatTimer);
        this._heartbeatTimer = undefined;
      }
      this.sendLockSignal(false);
    }
  }

  private get currentDayKey(): ScheduleDay {
    return DAYS_OF_WEEK[this.selectedDayIndex];
  }

  private changeDay(delta: number) {
    this.selectedDayIndex = (this.selectedDayIndex + delta + 7) % 7;
  }

  // --- Interaction: Dragging & Resizing Horizontally ---

  private handleTrackPointerDown(e: PointerEvent) {
    if (!this.isEditMode || this.isManual) return;
    const track = e.currentTarget as HTMLElement;
    const rect = track.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, clickX / rect.width));
    const stepSize = this.config.step_size || 15;
    const clickedMinute = snapMinutes(ratio * 1440, stepSize);

    track.setPointerCapture(e.pointerId);

    this.dragAction = {
      type: 'create',
      initialX: e.clientX,
      initialMinute: clickedMinute,
      currentMinute: clickedMinute,
      hasDragged: false
    };
  }

  private handleBlockClick(e: MouseEvent, block: InternalBlock) {
    e.stopPropagation();
    if (!this.isEditMode || this.isManual) return;
    if (Date.now() - this.lastDragEndTime < 350 || this.dragAction?.hasDragged) return;
    this.activeEditingBlock = block;
  }

  private handleResizePointerDown(
    e: PointerEvent,
    block: InternalBlock,
    type: 'resize-start' | 'resize-end'
  ) {
    e.stopPropagation();
    if (!this.isEditMode || this.isManual) return;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    const blockList = this.blocksByDay[this.currentDayKey];
    let abuttingBlockId: string | undefined;

    if (type === 'resize-end') {
      const neighbor = blockList.find((b) => b.id !== block.id && b.startMinutes === block.endMinutes);
      if (neighbor) abuttingBlockId = neighbor.id;
    } else if (type === 'resize-start') {
      const neighbor = blockList.find((b) => b.id !== block.id && b.endMinutes === block.startMinutes);
      if (neighbor) abuttingBlockId = neighbor.id;
    }

    this.dragAction = {
      type,
      blockId: block.id,
      abuttingBlockId,
      initialX: e.clientX,
      initialMinute: type === 'resize-start' ? block.startMinutes : block.endMinutes,
      currentMinute: type === 'resize-start' ? block.startMinutes : block.endMinutes,
      initialStart: block.startMinutes,
      initialEnd: block.endMinutes,
      hasDragged: false
    };
  }

  private handleTrackPointerMove(e: PointerEvent) {
    if (!this.dragAction) return;

    if (Math.abs(e.clientX - this.dragAction.initialX) > 5) {
      this.dragAction.hasDragged = true;
    }

    const track = e.currentTarget as HTMLElement;
    const rect = track.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, currentX / rect.width));
    const stepSize = this.config.step_size || 15;
    const currentMinute = snapMinutes(ratio * 1440, stepSize);

    const { type, blockId, abuttingBlockId, initialMinute } = this.dragAction;
    const day = this.currentDayKey;
    const blockList = this.blocksByDay[day];

    if (type === 'create') {
      if (!this.dragAction.hasDragged) return;
      this.dragAction.currentMinute = currentMinute;
      this.requestUpdate();
      return;
    }

    const currentBlock = blockList.find((b) => b.id === blockId);
    if (!currentBlock) return;

    if (type === 'resize-start') {
      const nextStart = Math.min(currentBlock.endMinutes - stepSize, Math.max(0, currentMinute));
      this.dragAction.currentMinute = nextStart;
      if (nextStart !== currentBlock.startMinutes) {
        currentBlock.startMinutes = nextStart;
        if (abuttingBlockId) {
          const neighbor = blockList.find((b) => b.id === abuttingBlockId);
          if (neighbor) neighbor.endMinutes = nextStart;
        }
      }
      this.requestUpdate();
    } else if (type === 'resize-end') {
      const nextEnd = Math.max(currentBlock.startMinutes + stepSize, Math.min(1440, currentMinute));
      this.dragAction.currentMinute = nextEnd;
      if (nextEnd !== currentBlock.endMinutes) {
        currentBlock.endMinutes = nextEnd;
        if (abuttingBlockId) {
          const neighbor = blockList.find((b) => b.id === abuttingBlockId);
          if (neighbor) neighbor.startMinutes = nextEnd;
        }
      }
      this.requestUpdate();
    }
  }

  private handleTrackPointerUp() {
    if (!this.dragAction) return;

    const { type, initialMinute, hasDragged } = this.dragAction;
    const day = this.currentDayKey;

    if (type === 'create') {
      if (!hasDragged) {
        const existing = this.blocksByDay[day].find(
          (b) => initialMinute >= b.startMinutes && initialMinute < b.endMinutes
        );
        if (existing) {
          this.activeEditingBlock = existing;
        } else {
          const stepSize = this.config.step_size || 15;
          const newBlock: InternalBlock = {
            id: `${day}_block_${Date.now()}`,
            day,
            startMinutes: initialMinute,
            endMinutes: Math.min(1440, initialMinute + 60),
            hvac_mode: 'heat_cool',
            heat_to: 68,
            cool_to: 74
          };
          this.blocksByDay = {
            ...this.blocksByDay,
            [day]: [...this.blocksByDay[day], newBlock].sort((a, b) => a.startMinutes - b.startMinutes)
          };
          this.activeEditingBlock = newBlock;
        }
      } else {
        const stepSize = this.config.step_size || 15;
        const cur = this.dragAction.currentMinute ?? initialMinute;
        const start = Math.min(initialMinute, cur);
        const end = Math.max(start + stepSize, Math.max(initialMinute, cur));
        this.carveAndInsertBlock(day, start, Math.min(1440, end));
      }
    }

    if (hasDragged) {
      this.lastDragEndTime = Date.now();
    }

    this.dragAction = null;
    this.saveCurrentSchedule();
  }

  private carveAndInsertBlock(day: ScheduleDay, carveStart: number, carveEnd: number) {
    const blockList = this.blocksByDay[day];
    const nextBlocks: InternalBlock[] = [];

    const intersected = blockList.find(
      (b) => b.startMinutes < carveEnd && b.endMinutes > carveStart
    );

    for (const b of blockList) {
      if (b.endMinutes <= carveStart || b.startMinutes >= carveEnd) {
        nextBlocks.push(b);
      } else if (b.startMinutes < carveStart && b.endMinutes > carveEnd) {
        nextBlocks.push({ ...b, id: `${b.day}_block_${Date.now()}_l`, endMinutes: carveStart });
        nextBlocks.push({ ...b, id: `${b.day}_block_${Date.now()}_r`, startMinutes: carveEnd });
      } else if (b.startMinutes < carveStart && b.endMinutes <= carveEnd) {
        nextBlocks.push({ ...b, endMinutes: carveStart });
      } else if (b.startMinutes >= carveStart && b.endMinutes > carveEnd) {
        nextBlocks.push({ ...b, startMinutes: carveEnd });
      }
    }

    const newBlock: InternalBlock = {
      id: `${day}_block_${Date.now()}`,
      day,
      startMinutes: carveStart,
      endMinutes: carveEnd,
      hvac_mode: intersected?.hvac_mode || 'heat_cool',
      heat_to: intersected?.heat_to ?? 68,
      cool_to: intersected?.cool_to ?? 74
    };
    nextBlocks.push(newBlock);
    nextBlocks.sort((a, b) => a.startMinutes - b.startMinutes);

    this.blocksByDay = { ...this.blocksByDay, [day]: nextBlocks };
  }

  private handleSaveBlock(e: CustomEvent<{ block: InternalBlock }>) {
    const updated = e.detail.block;
    const day = updated.day;
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: this.blocksByDay[day].map((b) => (b.id === updated.id ? updated : b))
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }

  private handleDeleteBlock(e: CustomEvent<{ blockId: string; day: ScheduleDay }>) {
    const { blockId, day } = e.detail;
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: this.blocksByDay[day].filter((b) => b.id !== blockId)
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }

  private handleSplitBlock(e: CustomEvent<{ blockId: string; day: ScheduleDay; splitMinute: number }>) {
    const { blockId, day, splitMinute } = e.detail;
    const list = this.blocksByDay[day];
    const idx = list.findIndex((b) => b.id === blockId);
    if (idx === -1) return;

    const original = list[idx];
    const originalEnd = original.endMinutes;
    original.endMinutes = splitMinute;

    const secondPiece: InternalBlock = {
      ...original,
      id: `${day}_block_${Date.now()}`,
      startMinutes: splitMinute,
      endMinutes: originalEnd
    };

    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: [...list, secondPiece].sort((a, b) => a.startMinutes - b.startMinutes)
    };
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }

  private handleCopyBlockTo(
    e: CustomEvent<{ block: InternalBlock; target: 'weekdays' | 'weekend' | 'all' }>
  ) {
    const { block, target } = e.detail;
    const targetDays: ScheduleDay[] =
      target === 'weekdays'
        ? ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        : target === 'weekend'
        ? ['saturday', 'sunday']
        : DAYS_OF_WEEK;

    const nextBlocks = { ...this.blocksByDay };

    for (const day of targetDays) {
      const copy: InternalBlock = {
        ...block,
        id: `${day}_block_${Date.now()}_${Math.random()}`,
        day
      };
      nextBlocks[day] = [
        ...nextBlocks[day].filter(
          (b) => !(b.startMinutes < copy.endMinutes && b.endMinutes > copy.startMinutes)
        ),
        copy
      ].sort((a, b) => a.startMinutes - b.startMinutes);
    }

    this.blocksByDay = nextBlocks;
    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }

  private async saveCurrentSchedule() {
    if (!this.hass || !this.activeScheduleId) return;
    this.isSaving = true;
    try {
      const schedule = this.schedules.find((s) => s.id === this.activeScheduleId);
      const name = schedule?.name || this.activeScheduleId;
      const icon = schedule?.icon;
      const haDays = convertToHABlocks(this.blocksByDay);
      await updateHASchedule(this.hass, this.activeScheduleId, name, haDays, icon);
      this._lastLoadedScheduleHash = JSON.stringify({ ...schedule, ...haDays, name, icon });
    } catch (err) {
      console.error('[climate-preset-timeline] Failed to save schedule update:', err);
    } finally {
      this.isSaving = false;
    }
  }

  render() {
    const climateState = this.config.entity ? this.hass?.states[this.config.entity] : undefined;
    const title =
      this.config.title ||
      climateState?.attributes?.friendly_name ||
      'Climate Preset 1-day Timeline';

    const dayName = DAY_LABELS[this.currentDayKey]?.full || this.currentDayKey;
    const todayIndex = (new Date().getDay() + 6) % 7;
    const isViewingToday = this.selectedDayIndex === todayIndex;

    const blocks = this.blocksByDay[this.currentDayKey] || [];
    const unit = this.config.temperature_unit || '°F';

    // Calculate current time needle position
    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    const nowPct = (currentMinutes / 1440) * 100;

    return html`
      <ha-card>
        <!-- Header -->
        <div class="header-row">
          <div class="title-box">
            <h3 class="card-title" title="${title}">${title}</h3>
            ${this.currentPresetMode
              ? html`
                  <span
                    class="preset-chip ${this.isManual ? 'manual' : ''}"
                    title="${this.isManual ? 'Manual Mode' : this.currentPresetMode}"
                  >
                    ${this.isManual ? '⚠️ Manual' : `🎯 ${this.currentPresetMode}`}
                  </span>
                `
              : ''}
            ${this.isYamlSchedule
              ? html`<span class="yaml-badge" title="Defined in YAML: edits must be made in configuration.yaml">YAML (Read Only)</span>`
              : this.isForeign
              ? html`<span class="yaml-badge" title="Non-HVAC schedule data payloads cannot be edited in this card">Non-HVAC (Read Only)</span>`
              : ''}
          </div>

          <!-- Controls: Day Navigation + Edit Toggle -->
          <div class="header-controls">
            <!-- Day navigation -->
            <div class="day-nav">
              <button class="nav-btn" @click=${() => this.changeDay(-1)} title="Previous Day">‹</button>
              <span class="day-label">${isViewingToday ? `Today (${dayName.slice(0, 3)})` : dayName}</span>
              <button class="nav-btn" @click=${() => this.changeDay(1)} title="Next Day">›</button>
            </div>

            <!-- Edit mode toggle -->
            <button
              class="edit-toggle-btn ${this.isEditMode ? 'active' : ''}"
              @click=${this.toggleEditMode}
              ?disabled=${this.isManual || this.isYamlSchedule || this.isForeign || this.scheduleNotFound}
              title=${this.isManual
                ? 'Manual mode active (no schedule to edit)'
                : this.isYamlSchedule
                ? 'YAML schedules are read-only'
                : this.isForeign
                ? 'Non-HVAC schedules are read-only'
                : this.scheduleNotFound
                ? 'Schedule entity not found'
                : this.isEditMode
                ? 'Finish editing'
                : 'Enable editing'}
            >
              ${this.isEditMode ? '✓ Done' : '✎ Edit'}
            </button>
          </div>
        </div>

        <!-- Horizontal Timeline Track -->
        <div
          class="timeline-track-wrap ${this.isEditMode ? 'editing' : ''}"
          @pointerdown=${this.handleTrackPointerDown}
          @pointermove=${this.handleTrackPointerMove}
          @pointerup=${this.handleTrackPointerUp}
        >
          <!-- Status Overlays -->
          ${this.isManual
            ? html`
                <div class="manual-overlay">
                  <span>⏸️ Manual Hold Active — No schedule running</span>
                </div>
              `
            : this.isYamlSchedule
            ? html`
                <div class="manual-overlay">
                  <span>📄 YAML Schedule Active — Read-only</span>
                </div>
              `
            : this.isForeign
            ? html`
                <div class="manual-overlay">
                  <span>⚠️ Non-HVAC Schedule Active — Read-only</span>
                </div>
              `
            : this.scheduleNotFound
            ? html`
                <div class="manual-overlay error">
                  <span>⚠️ Schedule entity not found</span>
                </div>
              `
            : ''}
          <!-- Grid tick lines every 4 hours -->
          ${[4, 8, 12, 16, 20].map((hour) => {
            const leftPct = (hour / 24) * 100;
            return html`<div class="time-grid-line" style="left: ${leftPct}%;"></div>`;
          })}

          <!-- Scheduled Blocks -->
          ${blocks.map((block) => {
            const leftPct = (block.startMinutes / 1440) * 100;
            const duration = block.endMinutes - block.startMinutes;
            const widthPct = (duration / 1440) * 100;

            const heatColor = getHeatColor(block.heat_to, unit);
            const heatText = getHeatTextColor(block.heat_to, unit);
            const coolColor = getCoolColor(block.cool_to, unit);
            const coolText = getCoolTextColor(block.cool_to, unit);

            const tooltip =
              block.isGeneric
                ? `Non-Climate Block: No HVAC targets (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`
                : block.hvac_mode === 'heat_cool'
                ? `Dual: Heat ${block.heat_to}°, Cool ${block.cool_to}° (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`
                : `${block.hvac_mode} (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`;

            return html`
              <div
                class="timeline-block"
                style="left: ${leftPct}%; width: ${widthPct}%;"
                title=${tooltip}
                @click=${(e: MouseEvent) => this.handleBlockClick(e, block)}
              >
                ${block.isGeneric
                  ? html`
                      <div class="band-generic">
                        ${widthPct > 8 ? 'No HVAC' : ''}
                      </div>
                    `
                  : block.hvac_mode === 'heat_cool'
                  ? html`
                      <div class="band-cool" style="background-color: ${coolColor}; color: ${coolText};">
                        ${widthPct > 5 ? `${block.cool_to}°` : ''}
                      </div>
                      <div class="band-heat" style="background-color: ${heatColor}; color: ${heatText};">
                        ${widthPct > 5 ? `${block.heat_to}°` : ''}
                      </div>
                    `
                  : block.hvac_mode === 'heat'
                  ? html`
                      <div class="band-heat" style="background-color: ${heatColor}; color: ${heatText}; flex: 1;">
                        ${block.heat_to}°
                      </div>
                    `
                  : block.hvac_mode === 'cool'
                  ? html`
                      <div class="band-cool" style="background-color: ${coolColor}; color: ${coolText}; flex: 1;">
                        ${block.cool_to}°
                      </div>
                    `
                  : html`<div style="flex: 1; background: #27272a;"></div>`}

                <!-- Resize handles -->
                <div
                  class="h-resize-handle left"
                  @click=${(e: MouseEvent) => e.stopPropagation()}
                  @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-start')}
                ></div>
                <div
                  class="h-resize-handle right"
                  @click=${(e: MouseEvent) => e.stopPropagation()}
                  @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-end')}
                ></div>
              </div>
            `;
          })}

          <!-- Carve preview overlay -->
          ${this.dragAction && this.dragAction.type === 'create' && this.dragAction.hasDragged
            ? (() => {
                const step = this.config.step_size || 15;
                const cur = this.dragAction.currentMinute ?? this.dragAction.initialMinute;
                const start = Math.min(this.dragAction.initialMinute, cur);
                const end = Math.min(1440, Math.max(start + step, Math.max(this.dragAction.initialMinute, cur)));
                const leftPct = (start / 1440) * 100;
                const widthPct = ((end - start) / 1440) * 100;
                return html`
                  <div class="carve-overlay" style="left: ${leftPct}%; width: ${widthPct}%;">
                    ${formatTimeDisplay(start)} – ${formatTimeDisplay(end)}
                  </div>
                `;
              })()
            : ''}

          <!-- Floating drag resize guide -->
          ${this.dragAction && (this.dragAction.type === 'resize-start' || this.dragAction.type === 'resize-end') && this.dragAction.currentMinute !== undefined
            ? (() => {
                const leftPct = (this.dragAction.currentMinute / 1440) * 100;
                return html`
                  <div class="drag-h-indicator" style="left: ${leftPct}%;">
                    <div class="drag-h-line"></div>
                    <div class="drag-h-pill">${formatTimeDisplay(this.dragAction.currentMinute)}</div>
                  </div>
                `;
              })()
            : ''}

          <!-- Red "NOW" needle if viewing today -->
          ${isViewingToday
            ? html`<div class="now-needle" style="left: ${nowPct}%;" title="Current Time"></div>`
            : ''}
        </div>

        <!-- Horizontal Time Axis Labels -->
        <div class="time-axis-horizontal">
          <span>00:00</span>
          <span>04:00</span>
          <span>08:00</span>
          <span>12:00</span>
          <span>16:00</span>
          <span>20:00</span>
          <span>24:00</span>
        </div>

        <!-- Edit Dialog -->
        ${this.activeEditingBlock
          ? html`
              <preset-dialog
                .block=${this.activeEditingBlock}
                .temperatureUnit=${this.config.temperature_unit || '°F'}
                .minDeadband=${this.config.min_deadband || 2}
                .minTemp=${45}
                .maxTemp=${85}
                @save-block=${this.handleSaveBlock}
                @delete-block=${this.handleDeleteBlock}
                @split-block=${this.handleSplitBlock}
                @copy-block-to=${this.handleCopyBlockTo}
                @close-dialog=${() => (this.activeEditingBlock = null)}
              ></preset-dialog>
            `
          : ''}
      </ha-card>
    `;
  }
}

if (!customElements.get('climate-preset-timeline')) {
  customElements.define('climate-preset-timeline', ClimatePresetTimeline);
}

declare global {
  interface HTMLElementTagNameMap {
    'climate-preset-timeline': ClimatePresetTimeline;
  }
}

(window as any).customCards = (window as any).customCards || [];
(window as any).customCards.push({
  type: 'climate-preset-timeline',
  name: 'Climate Preset 1-day Timeline',
  description: 'Single-day horizontal timeline tracker bound to a space climate preset schedule.',
  preview: true
});
