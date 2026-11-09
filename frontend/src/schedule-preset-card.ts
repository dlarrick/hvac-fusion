import { LitElement, html, css, PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import {
  CardConfig,
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
  subscribeScheduleUpdates,
  updateHASchedule
} from './services/ha-schedule';
import { formatTimeDisplay, snapMinutes } from './utils/time';
import {
  getCoolColor,
  getCoolTextColor,
  getHeatColor,
  getHeatTextColor,
  getSplitOrientation
} from './utils/colors';
import './components/preset-dialog';
import './components/card-editor';

export class SchedulePresetCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private config!: CardConfig;
  @state() private schedules: HAScheduleItem[] = [];
  @state() private selectedScheduleId = '';
  @state() private blocksByDay: Record<ScheduleDay, InternalBlock[]> = {
    monday: [],
    tuesday: [],
    wednesday: [],
    thursday: [],
    friday: [],
    saturday: [],
    sunday: []
  };

  @state() private activeEditingBlock: InternalBlock | null = null;
  @state() private isSaving = false;
  @state() private isYamlSchedule = false;
  @state() private isCompact = false;
  @state() private isEditMode = false;

  // Interaction tracking for dragging & resizing
  private dragAction: {
    type: 'move' | 'resize-start' | 'resize-end' | 'create';
    blockId?: string;
    abuttingBlockId?: string;
    day: ScheduleDay;
    initialY: number;
    initialMinute: number;
    currentMinute?: number;
    initialStart?: number;
    initialEnd?: number;
    hasDragged: boolean;
  } | null = null;
  private lastDragEndTime = 0;
  private _unsubscribeSync?: () => void;
  private _lastLoadedScheduleHash = '';
  private _heartbeatTimer?: ReturnType<typeof setInterval>;

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
      padding: 14px 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    /* Card Header */
    .card-header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: nowrap;
      gap: 10px;
      margin: 0;
      padding: 0;
      min-width: 0;
    }

    .title-row {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
      flex: 1 1 auto;
      overflow: hidden;
    }

    .card-title {
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--primary-text-color, #ffffff);
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      min-width: 0;
      flex-shrink: 1;
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

    .header-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }

    .schedule-select {
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 8px;
      padding: 6px 10px;
      font-size: 0.85rem;
      cursor: pointer;
      max-width: 200px;
    }
    .schedule-select:focus {
      outline: none;
      border-color: var(--primary-color, #3b82f6);
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

    /* Weekly Grid Layout */
    .timeline-container {
      display: flex;
      width: 100%;
      height: 580px;
      position: relative;
      background: rgba(0, 0, 0, 0.22);
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.06);
      overflow: hidden;
      transition: height 0.22s ease-in-out;
    }

    .timeline-container.editing {
      border-color: rgba(56, 189, 248, 0.45);
    }
    .timeline-container.editing .timeline-block {
      cursor: pointer;
    }
    .timeline-container:not(.editing) .timeline-block {
      cursor: default;
    }
    .timeline-container:not(.editing) .resize-handle {
      display: none;
    }

    .timeline-container.compact {
      height: 280px;
    }

    /* Y-Axis Time Labels */
    .time-axis {
      width: 50px;
      flex-shrink: 0;
      position: relative;
      height: 100%;
      border-right: 1px solid rgba(255, 255, 255, 0.08);
      padding-top: 32px; /* space for day header */
      box-sizing: border-box;
    }

    .time-tick {
      position: absolute;
      left: 6px;
      font-size: 0.72rem;
      color: var(--secondary-text-color, #8b949e);
      transform: translateY(-50%);
      pointer-events: none;
    }

    /* Day Columns Container */
    .days-container {
      flex: 1;
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      height: 100%;
      position: relative;
    }

    .day-column {
      display: flex;
      flex-direction: column;
      height: 100%;
      border-right: 1px solid rgba(255, 255, 255, 0.05);
      position: relative;
    }
    .day-column:last-child {
      border-right: none;
    }

    .day-header {
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--secondary-text-color, #a1a1aa);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.02);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .day-header.today {
      color: var(--primary-color, #38bdf8);
      font-weight: 700;
    }

    /* Day Track (00:00 to 24:00) */
    .day-track {
      flex: 1;
      position: relative;
      cursor: crosshair;
      touch-action: none;
    }

    /* Background 2-hour grid lines */
    .grid-line {
      position: absolute;
      left: 0;
      right: 0;
      height: 1px;
      background: rgba(255, 255, 255, 0.04);
      pointer-events: none;
    }

    /* Individual Block Cell */
    .schedule-cell {
      position: absolute;
      left: 3px;
      right: 3px;
      border-radius: 6px;
      overflow: hidden;
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.35);
      transition: box-shadow 0.15s, border-color 0.15s;
      border: 1px solid rgba(255, 255, 255, 0.15);
      box-sizing: border-box;
      display: flex;
    }

    .schedule-cell:hover {
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
      border-color: rgba(255, 255, 255, 0.4);
      z-index: 10;
    }

    /* Stacked (Normal / Tall duration) */
    .schedule-cell.stacked {
      flex-direction: column;
    }

    .schedule-cell.stacked .cool-band,
    .schedule-cell.stacked .heat-band {
      flex: 1;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.76rem;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* Side-by-side (Rotated for short / horizontal duration) */
    .schedule-cell.side-by-side {
      flex-direction: row;
    }

    .schedule-cell.side-by-side .heat-band,
    .schedule-cell.side-by-side .cool-band {
      flex: 1;
      height: 100%;
      min-height: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.65rem;
      font-weight: 700;
      line-height: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    /* Resize Handles */
    .resize-handle {
      position: absolute;
      left: 0;
      right: 0;
      height: 8px;
      z-index: 20;
      cursor: ns-resize;
    }
    .resize-handle.top {
      top: 0;
    }
    .resize-handle.bottom {
      bottom: 0;
    }
    .resize-handle:hover {
      background: rgba(255, 255, 255, 0.25);
    }

    /* Off / Neutral block */
    .cell-off {
      background: #27272a !important;
      color: #71717a !important;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 600;
    }

    /* Carve preview overlay */
    .carve-preview {
      position: absolute;
      left: 3px;
      right: 3px;
      border: 2px dashed var(--primary-color, #38bdf8);
      background: rgba(56, 189, 248, 0.28);
      border-radius: 6px;
      pointer-events: none;
      z-index: 25;
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .carve-preview-label {
      font-size: 0.72rem;
      font-weight: 700;
      color: #fff;
      background: rgba(0, 0, 0, 0.75);
      padding: 2px 6px;
      border-radius: 4px;
      white-space: nowrap;
    }

    /* Floating time indicator while dragging edges */
    .drag-time-indicator {
      position: absolute;
      left: -8px;
      right: -8px;
      height: 0;
      pointer-events: none;
      z-index: 50;
      display: flex;
      align-items: center;
      justify-content: center;
      transform: translateY(-50%);
    }

    .drag-time-line {
      position: absolute;
      left: 0;
      right: 0;
      height: 2px;
      background: var(--primary-color, #38bdf8);
      box-shadow: 0 0 8px rgba(56, 189, 248, 0.9);
    }

    .drag-time-pill {
      position: relative;
      background: #090d16;
      color: #38bdf8;
      border: 1.5px solid #38bdf8;
      padding: 3px 8px;
      border-radius: 8px;
      font-size: 0.76rem;
      font-weight: 700;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.85);
      white-space: nowrap;
      letter-spacing: 0.5px;
      transform: translateY(-20px); /* Floats above the cursor and guideline */
      transition: transform 0.1s ease;
    }

    .drag-time-pill::after {
      content: '';
      position: absolute;
      bottom: -5px;
      left: 50%;
      transform: translateX(-50%);
      width: 0;
      height: 0;
      border-left: 5px solid transparent;
      border-right: 5px solid transparent;
      border-top: 5px solid #38bdf8;
    }

    /* Flip downward when dragging near the top of the day */
    .drag-time-pill.flip-down {
      transform: translateY(20px);
    }

    .drag-time-pill.flip-down::after {
      bottom: auto;
      top: -5px;
      border-top: none;
      border-bottom: 5px solid #38bdf8;
    }

    /* Footer hints */
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.78rem;
      color: var(--secondary-text-color, #71717a);
      padding: 0 4px;
    }

    .legend {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .legend-swatch {
      width: 12px;
      height: 12px;
      border-radius: 3px;
    }

    .view-toggle-btn {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 10px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: var(--secondary-text-color, #9ca3af);
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
    }
    .view-toggle-btn:hover {
      background: rgba(255, 255, 255, 0.15);
      color: #fff;
    }
  `;

  public setConfig(config: CardConfig) {
    if (!config) {
      throw new Error('Invalid configuration');
    }
    this.config = {
      step_size: 15,
      temperature_unit: '°F',
      min_deadband: 2,
      min_temp: 45,
      max_temp: 85,
      ...config
    };
  }

  public getCardSize(): number {
    return 10;
  }

  public static async getConfigElement(): Promise<HTMLElement> {
    return document.createElement('schedule-preset-card-editor');
  }

  public static getStubConfig(): Record<string, any> {
    return {
      type: 'custom:schedule-preset-card',
      title: 'Climate Schedule',
      temperature_unit: '°F',
      step_size: 15,
      min_deadband: 2
    };
  }

  connectedCallback() {
    super.connectedCallback();
    try {
      const savedCompact = localStorage.getItem('schedule-preset-card-compact');
      if (savedCompact !== null) {
        this.isCompact = savedCompact === 'true';
      }
    } catch {
      // Ignore if localStorage unavailable
    }

    // Subscribe to cross-card schedule updates
    this._unsubscribeSync = subscribeScheduleUpdates((scheduleId) => {
      this.syncFromHass(true);
    });
  }

  disconnectedCallback() {
    super.disconnectedCallback();
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

  private sendLockSignal(acquire: boolean) {
    if (!this.hass || !this.selectedScheduleId) return;
    const action = acquire ? 'acquire_schedule_lock' : 'release_schedule_lock';
    // Progressive enhancement: only dispatch lock if hvac_fusion integration is installed
    if (!this.hass.services?.hvac_fusion?.[action]) return;

    this.hass.callService('hvac_fusion', action, {
      schedule_id: this.selectedScheduleId,
      ...(acquire ? { duration: 300 } : {})
    });
  }

  private toggleEditMode() {
    if (this.isYamlSchedule) return;
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

  private toggleCompact() {
    this.isCompact = !this.isCompact;
    try {
      localStorage.setItem('schedule-preset-card-compact', String(this.isCompact));
    } catch {
      // Ignore
    }
  }

  public willUpdate(changedProps: PropertyValues) {
    if (changedProps.has('hass') && this.hass) {
      this.syncFromHass();
    }
  }

  private async syncFromHass(forceReload = false) {
    if (!this.hass || this.isSaving || this.dragAction || this.activeEditingBlock) return;

    // Load available schedules list (only storage-backed editable schedules)
    const list = await fetchScheduleList(this.hass);
    this.schedules = list;

    // Check localStorage first, then config.entity, then first schedule
    let targetId: string | null = null;
    try {
      targetId = localStorage.getItem('schedule-preset-card-selected');
    } catch {
      // Ignore
    }

    if (!targetId || !list.some((s) => s.id === targetId)) {
      targetId = this.config.entity || null;
      if (targetId && targetId.startsWith('schedule.')) {
        targetId = targetId.replace('schedule.', '');
      }
    }

    if ((!targetId || !list.some((s) => s.id === targetId)) && list.length > 0) {
      targetId = list[0].id;
    }

    if (targetId) {
      const item = list.find((s) => s.id === targetId);
      const itemHash = item ? JSON.stringify(item) : '';
      if (
        forceReload ||
        targetId !== this.selectedScheduleId ||
        (itemHash && itemHash !== this._lastLoadedScheduleHash)
      ) {
        this.selectedScheduleId = targetId;
        this._lastLoadedScheduleHash = itemHash;
        this.loadScheduleBlocks(targetId);
      }
    }
  }

  private loadScheduleBlocks(scheduleId: string) {
    const item = this.schedules.find((s) => s.id === scheduleId);
    if (item) {
      this._lastLoadedScheduleHash = JSON.stringify(item);
      this.blocksByDay = convertToInternalBlocks(item);
      this.isYamlSchedule = false;
    } else {
      this.isYamlSchedule = true;
    }
  }

  private handleScheduleSelected(e: Event) {
    const select = e.target as HTMLSelectElement;
    if (this.isEditMode) {
      this.sendLockSignal(false);
    }
    this.selectedScheduleId = select.value;
    try {
      localStorage.setItem('schedule-preset-card-selected', select.value);
    } catch {
      // Ignore
    }
    if (this.isEditMode) {
      this.sendLockSignal(true);
    }
    this.loadScheduleBlocks(select.value);
  }

  // --- Interaction: Dragging, Resizing, and Creating Blocks ---

  private handleTrackPointerDown(e: PointerEvent, day: ScheduleDay) {
    if (this.isYamlSchedule || !this.isEditMode) return;

    const track = e.currentTarget as HTMLElement;
    const rect = track.getBoundingClientRect();
    const clickY = e.clientY - rect.top;
    const ratio = Math.max(0, Math.min(1, clickY / rect.height));
    const stepSize = this.config.step_size || 15;
    const clickedMinute = snapMinutes(ratio * 1440, stepSize);

    track.setPointerCapture(e.pointerId);

    // Prepare drag/carve action
    this.dragAction = {
      type: 'create',
      day,
      initialY: e.clientY,
      initialMinute: clickedMinute,
      currentMinute: clickedMinute,
      hasDragged: false
    };
  }

  private handleBlockClick(e: MouseEvent, block: InternalBlock) {
    e.stopPropagation();
    if (this.isYamlSchedule || !this.isEditMode) return;
    // Ignore click synthesized immediately following a drag/resize
    if (Date.now() - this.lastDragEndTime < 350 || this.dragAction?.hasDragged) return;
    this.activeEditingBlock = block;
  }

  private handleResizePointerDown(
    e: PointerEvent,
    block: InternalBlock,
    type: 'resize-start' | 'resize-end'
  ) {
    if (this.isYamlSchedule || !this.isEditMode) return;
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    // Find abutting block for lock-step shared boundary dragging
    const blockList = this.blocksByDay[block.day];
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
      day: block.day,
      initialY: e.clientY,
      initialMinute: type === 'resize-start' ? block.startMinutes : block.endMinutes,
      currentMinute: type === 'resize-start' ? block.startMinutes : block.endMinutes,
      initialStart: block.startMinutes,
      initialEnd: block.endMinutes,
      hasDragged: false
    };
  }

  private handleTrackPointerMove(e: PointerEvent, day: ScheduleDay) {
    if (!this.dragAction || this.dragAction.day !== day) return;

    if (Math.abs(e.clientY - this.dragAction.initialY) > 5) {
      this.dragAction.hasDragged = true;
    }

    const track = e.currentTarget as HTMLElement;
    const rect = track.getBoundingClientRect();
    const currentY = e.clientY - rect.top;
    const ratio = Math.max(0, Math.min(1, currentY / rect.height));
    const stepSize = this.config.step_size || 15;
    const currentMinute = snapMinutes(ratio * 1440, stepSize);

    const { type, blockId, abuttingBlockId, initialMinute } = this.dragAction;
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
        // Lock-step: adjust abutting predecessor's end time
        if (abuttingBlockId) {
          const neighbor = blockList.find((b) => b.id === abuttingBlockId);
          if (neighbor) {
            neighbor.endMinutes = nextStart;
          }
        }
      }
      this.requestUpdate();
    } else if (type === 'resize-end') {
      const nextEnd = Math.max(currentBlock.startMinutes + stepSize, Math.min(1440, currentMinute));
      this.dragAction.currentMinute = nextEnd;
      if (nextEnd !== currentBlock.endMinutes) {
        currentBlock.endMinutes = nextEnd;
        // Lock-step: adjust abutting successor's start time
        if (abuttingBlockId) {
          const neighbor = blockList.find((b) => b.id === abuttingBlockId);
          if (neighbor) {
            neighbor.startMinutes = nextEnd;
          }
        }
      }
      this.requestUpdate();
    }
  }

  private handleTrackPointerUp() {
    if (!this.dragAction) return;

    const { type, day, initialMinute, hasDragged } = this.dragAction;

    if (type === 'create') {
      if (!hasDragged) {
        // Pure click: check if clicked on an existing block
        const existing = this.blocksByDay[day].find(
          (b) => initialMinute >= b.startMinutes && initialMinute < b.endMinutes
        );

        if (existing) {
          this.activeEditingBlock = existing;
        } else {
          // Click on empty space: create default 1-hour block and open dialog
          const stepSize = this.config.step_size || 15;
          const newStart = initialMinute;
          const newEnd = Math.min(1440, newStart + 60);

          const newBlock: InternalBlock = {
            id: `${day}_block_${Date.now()}`,
            day,
            startMinutes: newStart,
            endMinutes: newEnd,
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
        // User dragged to carve a new slice!
        const stepSize = this.config.step_size || 15;
        const curMin = this.dragAction.currentMinute ?? initialMinute;
        const start = Math.min(initialMinute, curMin);
        const end = Math.max(start + stepSize, Math.max(initialMinute, curMin));
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

    // Find any existing block that is being carved into, to inherit its preset if available
    const intersected = blockList.find(
      (b) => b.startMinutes < carveEnd && b.endMinutes > carveStart
    );

    for (const b of blockList) {
      // 1. Outside the carved range
      if (b.endMinutes <= carveStart || b.startMinutes >= carveEnd) {
        nextBlocks.push(b);
      }
      // 2. Envelops the carved range -> split into left and right pieces
      else if (b.startMinutes < carveStart && b.endMinutes > carveEnd) {
        nextBlocks.push({
          ...b,
          id: `${b.day}_block_${Date.now()}_left`,
          endMinutes: carveStart
        });
        nextBlocks.push({
          ...b,
          id: `${b.day}_block_${Date.now()}_right`,
          startMinutes: carveEnd
        });
      }
      // 3. Overlaps carveStart on left -> truncate end
      else if (b.startMinutes < carveStart && b.endMinutes > carveStart && b.endMinutes <= carveEnd) {
        nextBlocks.push({
          ...b,
          endMinutes: carveStart
        });
      }
      // 4. Overlaps carveEnd on right -> truncate start
      else if (b.startMinutes >= carveStart && b.startMinutes < carveEnd && b.endMinutes > carveEnd) {
        nextBlocks.push({
          ...b,
          startMinutes: carveEnd
        });
      }
      // 5. Completely covered -> replaced by the new block
    }

    // Insert new carved block
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

    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: nextBlocks
    };
  }

  private handleSplitBlock(
    e: CustomEvent<{ blockId: string; day: ScheduleDay; splitMinute: number }>
  ) {
    const { blockId, day, splitMinute } = e.detail;
    const blockList = this.blocksByDay[day];
    const index = blockList.findIndex((b) => b.id === blockId);
    if (index === -1) return;

    const original = blockList[index];
    const originalEnd = original.endMinutes;

    // Truncate original to split time
    original.endMinutes = splitMinute;

    // Create second piece
    const secondPiece: InternalBlock = {
      ...original,
      id: `${day}_block_${Date.now()}`,
      startMinutes: splitMinute,
      endMinutes: originalEnd
    };

    const nextList = [...blockList, secondPiece].sort((a, b) => a.startMinutes - b.startMinutes);
    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: nextList
    };

    this.activeEditingBlock = null;
    this.saveCurrentSchedule();
  }

  // --- Block Dialog Event Handlers ---

  private handleSaveBlock(e: CustomEvent<{ block: InternalBlock }>) {
    const updated = e.detail.block;
    const day = updated.day;
    const list = this.blocksByDay[day].map((b) => (b.id === updated.id ? updated : b));

    this.blocksByDay = {
      ...this.blocksByDay,
      [day]: list
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
      // Overwrite/insert matching block in target days
      const copy: InternalBlock = {
        ...block,
        id: `${day}_block_${Date.now()}_${Math.random()}`,
        day
      };
      // For MVP, append or replace overlapping
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
    if (this.isYamlSchedule || !this.hass || !this.selectedScheduleId) return;

    this.isSaving = true;
    try {
      const schedule = this.schedules.find((s) => s.id === this.selectedScheduleId);
      const name = schedule?.name || this.selectedScheduleId;
      const icon = schedule?.icon;
      const haDays = convertToHABlocks(this.blocksByDay);
      await updateHASchedule(this.hass, this.selectedScheduleId, name, haDays, icon);
      this._lastLoadedScheduleHash = JSON.stringify({ ...schedule, ...haDays, name, icon });
    } catch (err) {
      console.error('[schedule-preset-card] Failed to save schedule update:', err);
    } finally {
      this.isSaving = false;
    }
  }

  // --- Rendering ---

  private renderGridLines() {
    const step = this.isCompact ? 4 : 2;
    const lines = [];
    for (let hour = step; hour < 24; hour += step) {
      const topPct = (hour / 24) * 100;
      lines.push(
        html`<div class="grid-line" style="top: ${topPct}%;"></div>`
      );
    }
    return lines;
  }

  private renderBlockCell(block: InternalBlock) {
    const trackHeightPx = this.isCompact ? 348 : 548;
    const startPct = (block.startMinutes / 1440) * 100;
    const duration = block.endMinutes - block.startMinutes;
    const heightPct = (duration / 1440) * 100;
    const heightPx = (duration / 1440) * trackHeightPx;

    const unit = this.config.temperature_unit || '°F';
    const heatColor = getHeatColor(block.heat_to, unit);
    const coolColor = getCoolColor(block.cool_to, unit);
    const heatText = getHeatTextColor(block.heat_to, unit);
    const coolText = getCoolTextColor(block.cool_to, unit);

    const tooltip =
      block.hvac_mode === 'heat_cool'
        ? `Dual: Heat ${block.heat_to}°, Cool ${block.cool_to}° (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`
        : block.hvac_mode === 'heat'
        ? `Heat: ${block.heat_to}° (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`
        : block.hvac_mode === 'cool'
        ? `Cool: ${block.cool_to}° (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`
        : `Off (${formatTimeDisplay(block.startMinutes)} – ${formatTimeDisplay(block.endMinutes)})`;

    // Determine layout: side-by-side (rotated for short duration) vs stacked
    const estimatedWidthPx = 60;
    const orientation = getSplitOrientation(estimatedWidthPx, heightPx);

    if (block.hvac_mode === 'off') {
      return html`
        <div
          class="schedule-cell cell-off"
          style="top: ${startPct}%; height: ${heightPct}%;"
          title=${tooltip}
          @click=${(e: MouseEvent) => this.handleBlockClick(e, block)}
        >
          ${heightPx >= 28 ? 'Off' : ''}
          <div
            class="resize-handle top"
            @click=${(e: MouseEvent) => e.stopPropagation()}
            @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-start')}
          ></div>
          <div
            class="resize-handle bottom"
            @click=${(e: MouseEvent) => e.stopPropagation()}
            @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-end')}
          ></div>
        </div>
      `;
    }

    if (block.hvac_mode === 'heat') {
      return html`
        <div
          class="schedule-cell"
          style="top: ${startPct}%; height: ${heightPct}%; background-color: ${heatColor}; color: ${heatText};"
          title=${tooltip}
          @click=${(e: MouseEvent) => this.handleBlockClick(e, block)}
        >
          <div style="flex: 1; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.78rem;">
            ${heightPx >= 20 ? `${block.heat_to}°` : ''}
          </div>
          <div
            class="resize-handle top"
            @click=${(e: MouseEvent) => e.stopPropagation()}
            @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-start')}
          ></div>
          <div
            class="resize-handle bottom"
            @click=${(e: MouseEvent) => e.stopPropagation()}
            @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-end')}
          ></div>
        </div>
      `;
    }

    if (block.hvac_mode === 'cool') {
      return html`
        <div
          class="schedule-cell"
          style="top: ${startPct}%; height: ${heightPct}%; background-color: ${coolColor}; color: ${coolText};"
          title=${tooltip}
          @click=${(e: MouseEvent) => this.handleBlockClick(e, block)}
        >
          <div style="flex: 1; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.78rem;">
            ${heightPx >= 20 ? `${block.cool_to}°` : ''}
          </div>
          <div
            class="resize-handle top"
            @click=${(e: MouseEvent) => e.stopPropagation()}
            @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-start')}
          ></div>
          <div
            class="resize-handle bottom"
            @click=${(e: MouseEvent) => e.stopPropagation()}
            @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-end')}
          ></div>
        </div>
      `;
    }

    // Default: heat_cool (dual setpoint)
    const isStacked = orientation === 'stacked';

    return html`
      <div
        class="schedule-cell ${isStacked ? 'stacked' : 'side-by-side'}"
        style="top: ${startPct}%; height: ${heightPct}%;"
        title=${tooltip}
        @click=${(e: MouseEvent) => this.handleBlockClick(e, block)}
      >
        ${isStacked
          ? html`
              <!-- Top band: Cooling -->
              <div class="cool-band" style="background-color: ${coolColor}; color: ${coolText};">
                ${heightPx >= 48 ? `${block.cool_to}°` : ''}
              </div>
              <!-- Bottom band: Heating -->
              <div class="heat-band" style="background-color: ${heatColor}; color: ${heatText};">
                ${heightPx >= 48 ? `${block.heat_to}°` : ''}
              </div>
            `
          : html`
              <!-- Rotated Side-by-side for short duration blocks -->
              <!-- Left band: Heating -->
              <div class="heat-band" style="background-color: ${heatColor}; color: ${heatText};">
                ${heightPx >= 16 ? `${block.heat_to}°` : ''}
              </div>
              <!-- Right band: Cooling -->
              <div class="cool-band" style="background-color: ${coolColor}; color: ${coolText};">
                ${heightPx >= 16 ? `${block.cool_to}°` : ''}
              </div>
            `}

        <div
          class="resize-handle top"
          @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-start')}
        ></div>
        <div
          class="resize-handle bottom"
          @pointerdown=${(e: PointerEvent) => this.handleResizePointerDown(e, block, 'resize-end')}
        ></div>
      </div>
    `;
  }

  render() {
    const title = this.config?.title || 'Climate Schedule';
    const currentScheduleName =
      this.schedules.find((s) => s.id === this.selectedScheduleId)?.name ||
      this.selectedScheduleId ||
      'Schedule';

    const todayIndex = (new Date().getDay() + 6) % 7; // Monday = 0
    const todayKey = DAYS_OF_WEEK[todayIndex];

    return html`
      <ha-card>
        <!-- Header -->
        <div class="card-header-row">
          <div class="title-row">
            <h2 class="card-title" title="${title}">${title}</h2>
            ${this.isYamlSchedule
              ? html`<span class="yaml-badge" title="Defined in YAML: edits must be made in configuration.yaml">YAML (Read Only)</span>`
              : ''}
          </div>

          <div class="header-actions">
            ${this.schedules.length > 0
              ? html`
                  <select class="schedule-select" @change=${this.handleScheduleSelected}>
                    ${this.schedules.map(
                      (s) => html`
                        <option value=${s.id} ?selected=${s.id === this.selectedScheduleId}>
                          ${s.name || s.id}
                        </option>
                      `
                    )}
                  </select>
                `
              : html`<span style="font-size: 0.85rem; color: var(--secondary-text-color, #a1a1aa);">${currentScheduleName}</span>`}

            <!-- Edit mode toggle -->
            <button
              class="edit-toggle-btn ${this.isEditMode ? 'active' : ''}"
              @click=${this.toggleEditMode}
              ?disabled=${this.isYamlSchedule}
              title=${this.isYamlSchedule ? 'YAML schedules are read-only' : this.isEditMode ? 'Finish editing' : 'Enable editing'}
            >
              ${this.isEditMode ? '✓ Done' : '✎ Edit'}
            </button>
          </div>
        </div>

        <!-- 7-Day Timeline Grid -->
        <div class="timeline-container ${this.isCompact ? 'compact' : ''} ${this.isEditMode ? 'editing' : ''}">
          <!-- Time Axis -->
          <div class="time-axis">
            ${(this.isCompact ? [0, 4, 8, 12, 16, 20, 24] : [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]).map((hour) => {
              const topPct = (hour / 24) * 100;
              return html`
                <div class="time-tick" style="top: calc(32px + (100% - 32px) * ${hour / 24});">
                  ${String(hour).padStart(2, '0')}:00
                </div>
              `;
            })}
          </div>

          <!-- Day Columns -->
          <div class="days-container">
            ${DAYS_OF_WEEK.map((day) => {
              const blocks = this.blocksByDay[day] || [];
              const isToday = day === todayKey;

              return html`
                <div class="day-column">
                  <div class="day-header ${isToday ? 'today' : ''}">
                    ${DAY_LABELS[day].short}
                  </div>

                  <div
                    class="day-track"
                    @pointerdown=${(e: PointerEvent) => this.handleTrackPointerDown(e, day)}
                    @pointermove=${(e: PointerEvent) => this.handleTrackPointerMove(e, day)}
                    @pointerup=${this.handleTrackPointerUp}
                  >
                    ${this.renderGridLines()}
                    ${blocks.map((block) => this.renderBlockCell(block))}
                    ${this.dragAction && this.dragAction.day === day && this.dragAction.type === 'create' && this.dragAction.hasDragged
                      ? (() => {
                          const step = this.config.step_size || 15;
                          const cur = this.dragAction.currentMinute ?? this.dragAction.initialMinute;
                          const start = Math.min(this.dragAction.initialMinute, cur);
                          const end = Math.min(1440, Math.max(start + step, Math.max(this.dragAction.initialMinute, cur)));
                          const topPct = (start / 1440) * 100;
                          const heightPct = ((end - start) / 1440) * 100;
                          return html`
                            <div class="carve-preview" style="top: ${topPct}%; height: ${heightPct}%;">
                              <span class="carve-preview-label">${formatTimeDisplay(start)} – ${formatTimeDisplay(end)}</span>
                            </div>
                          `;
                        })()
                      : ''}
                    ${this.dragAction && this.dragAction.day === day && (this.dragAction.type === 'resize-start' || this.dragAction.type === 'resize-end') && this.dragAction.currentMinute !== undefined
                      ? (() => {
                          const topPct = (this.dragAction.currentMinute / 1440) * 100;
                          return html`
                            <div class="drag-time-indicator" style="top: ${topPct}%;">
                              <div class="drag-time-line"></div>
                              <div class="drag-time-pill ${this.dragAction.currentMinute < 75 ? 'flip-down' : ''}">${formatTimeDisplay(this.dragAction.currentMinute)}</div>
                            </div>
                          `;
                        })()
                      : ''}
                  </div>
                </div>
              `;
            })}
          </div>
        </div>

        <!-- Footer / Legend -->
        <div class="card-footer">
          <div class="legend">
            <div class="legend-item">
              <div class="legend-swatch" style="background: ${getHeatColor(70, this.config.temperature_unit)};"></div>
              <span>Heat</span>
            </div>
            <div class="legend-item">
              <div class="legend-swatch" style="background: ${getCoolColor(72, this.config.temperature_unit)};"></div>
              <span>Cool</span>
            </div>
            <div class="legend-item">
              <div class="legend-swatch" style="background: #27272a; border: 1px solid #52525b;"></div>
              <span>Off (Gap)</span>
            </div>
          </div>

          <div style="display: flex; align-items: center; gap: 12px;">
            <button class="view-toggle-btn" @click=${this.toggleCompact} title="Toggle card height">
              <span>↕</span> ${this.isCompact ? 'Full View' : 'Compact View'}
            </button>
            <span>${this.isSaving ? 'Saving...' : this.isEditMode ? 'Editing • Drag to carve / click block to edit' : 'Locked • Click ✎ Edit to make changes'}</span>
          </div>
        </div>

        <!-- Active Preset Edit Dialog Modal -->
        ${this.activeEditingBlock
          ? html`
              <preset-dialog
                .block=${this.activeEditingBlock}
                .temperatureUnit=${this.config.temperature_unit || '°F'}
                .minDeadband=${this.config.min_deadband || 2}
                .minTemp=${this.config.min_temp || 45}
                .maxTemp=${this.config.max_temp || 85}
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

// Register custom element on window for Home Assistant Lovelace discovery
if (!customElements.get('schedule-preset-card')) {
  customElements.define('schedule-preset-card', SchedulePresetCard);
}

declare global {
  interface HTMLElementTagNameMap {
    'schedule-preset-card': SchedulePresetCard;
  }
}

// Announce card to Lovelace custom card picker
(window as any).customCards = (window as any).customCards || [];
(window as any).customCards.push({
  type: 'schedule-preset-card',
  name: 'Climate Preset Schedule Card',
  description: 'Visual 7-day schedule editor for climate dual-setpoints and native HA schedule entities.',
  preview: true
});
