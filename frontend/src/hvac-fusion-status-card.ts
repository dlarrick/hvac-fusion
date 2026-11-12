import { LitElement, html, css, PropertyValues } from 'lit';
import { property, state } from 'lit/decorators.js';
import {
  DAYS_OF_WEEK,
  DAY_LABELS,
  HAScheduleItem,
  HomeAssistant,
  InternalBlock,
  ScheduleDay,
  StatusCardConfig
} from './types';
import {
  convertToInternalBlocks,
  fetchScheduleList,
  findScheduleInList,
  isForeignSchedule,
  subscribeScheduleUpdates
} from './services/ha-schedule';
import { formatTimeDisplay } from './utils/time';
import {
  getCoolColor,
  getCoolTextColor,
  getHeatColor,
  getHeatTextColor
} from './utils/colors';
import './components/status-editor';

export class HvacFusionStatusCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private config!: StatusCardConfig;

  @state() private schedules: HAScheduleItem[] = [];
  @state() private activeScheduleId = '';
  @state() private currentPresetMode = '';
  @state() private isManual = false;
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
  @state() private diagnosticsExpanded = false;

  private _timer?: ReturnType<typeof setInterval>;
  private _unsubscribeSync?: () => void;

  public static async getConfigElement(): Promise<HTMLElement> {
    return document.createElement('hvac-fusion-status-editor');
  }

  public static getStubConfig(): Record<string, any> {
    return {
      type: 'custom:hvac-fusion-status-card',
      title: '',
      entity: '',
      show_schedule: true,
      show_boost: true,
      show_diagnostics: true,
      diagnostics_expanded_by_default: false,
      diagnostic_attributes: ['phase', 'active_producer', 'explanation', 'window_open']
    };
  }

  connectedCallback() {
    super.connectedCallback();
    // Update 'NOW' needle position every 30 seconds
    this._timer = setInterval(() => this.requestUpdate(), 30000);

    // Subscribe to cross-card schedule updates
    this._unsubscribeSync = subscribeScheduleUpdates(() => {
      this.refreshSchedules(true);
    });

    if (this.config?.diagnostics_expanded_by_default) {
      this.diagnosticsExpanded = true;
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._timer) clearInterval(this._timer);
    if (this._unsubscribeSync) this._unsubscribeSync();
  }

  public setConfig(config: StatusCardConfig) {
    if (!config) throw new Error('Invalid configuration');
    this.config = {
      show_schedule: true,
      show_boost: true,
      show_diagnostics: true,
      diagnostics_expanded_by_default: false,
      diagnostic_attributes: ['phase', 'active_producer', 'explanation', 'window_open'],
      ...config
    };
    if (this.config.diagnostics_expanded_by_default) {
      this.diagnosticsExpanded = true;
    }
  }

  protected willUpdate(changedProps: PropertyValues) {
    if (changedProps.has('hass') && this.hass) {
      this.syncWithClimateEntity();
    }
  }

  private async syncWithClimateEntity() {
    if (!this.hass || !this.config?.entity) return;

    const stateObj = this.hass.states[this.config.entity];
    if (!stateObj) return;

    const preset = stateObj.attributes.preset_mode || 'manual';
    this.currentPresetMode = preset;
    this.isManual = preset === 'manual';

    const activeSchedule = stateObj.attributes.active_schedule;
    let targetScheduleId = activeSchedule;

    if (!targetScheduleId && stateObj.attributes.presets) {
      targetScheduleId = stateObj.attributes.presets[preset];
    }

    if (targetScheduleId && targetScheduleId !== this.activeScheduleId) {
      this.activeScheduleId = targetScheduleId;
      await this.refreshSchedules(false);
    }
  }

  private async refreshSchedules(forceRefresh = false) {
    if (!this.hass) return;
    try {
      this.schedules = await fetchScheduleList(this.hass);
      this.loadActiveSchedule(forceRefresh);
    } catch (e) {
      console.error('[HvacFusionStatusCard] Failed to fetch schedules:', e);
    }
  }

  private async loadActiveSchedule(force = false) {
    if (!this.activeScheduleId || !this.hass) {
      this.scheduleNotFound = true;
      return;
    }

    const schedule = await findScheduleInList(this.schedules, this.activeScheduleId, this.hass);
    if (!schedule) {
      this.scheduleNotFound = true;
      return;
    }

    this.scheduleNotFound = false;
    this.isYamlSchedule = schedule.id.startsWith('yaml_');
    this.isForeign = isForeignSchedule(schedule);

    const scheduleHash = JSON.stringify(schedule);
    if (!force && scheduleHash === this._lastLoadedScheduleHash) {
      return;
    }
    this._lastLoadedScheduleHash = scheduleHash;

    this.blocksByDay = convertToInternalBlocks(schedule);
  }

  private changeDay(offset: number) {
    this.selectedDayIndex = (this.selectedDayIndex + offset + 7) % 7;
  }

  private async triggerComfortBoost(feeling: 'too_cold' | 'too_hot') {
    if (!this.hass || !this.config?.entity) return;
    try {
      await this.hass.callService('hvac_fusion', 'comfort_boost', {
        entity_id: this.config.entity,
        feeling: feeling,
        delta_f: 2.0,
        duration_minutes: 120,
        decay: true
      });
    } catch (err) {
      console.error('[HvacFusionStatusCard] Failed to trigger comfort boost:', err);
    }
  }

  private async clearComfortBoost() {
    if (!this.hass || !this.config?.entity) return;
    try {
      await this.hass.callService('hvac_fusion', 'clear_comfort_boost', {
        entity_id: this.config.entity
      });
    } catch (err) {
      console.error('[HvacFusionStatusCard] Failed to clear comfort boost:', err);
    }
  }

  static styles = css`
    :host {
      display: block;
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--primary-text-color, #e1e7ec);
    }

    ha-card {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      border-radius: var(--ha-card-border-radius, 12px);
      box-shadow: var(--ha-card-box-shadow, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
      padding: 16px;
      overflow: hidden;
      box-sizing: border-box;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
    }

    /* Primary Header */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      gap: 12px;
      flex-wrap: nowrap;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
      flex: 1 1 auto;
      overflow: hidden;
    }

    .card-title {
      font-size: 1.05rem;
      font-weight: 600;
      color: var(--primary-text-color, #ffffff);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .preset-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 8px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      background: rgba(56, 189, 248, 0.15);
      color: #38bdf8;
      border: 1px solid rgba(56, 189, 248, 0.3);
      white-space: nowrap;
      flex-shrink: 0;
    }

    .preset-chip.manual {
      background: rgba(245, 158, 11, 0.15);
      color: #f59e0b;
      border-color: rgba(245, 158, 11, 0.3);
    }

    .day-nav {
      display: flex;
      align-items: center;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      overflow: hidden;
      flex-shrink: 0;
    }

    .nav-btn {
      background: none;
      border: none;
      color: var(--secondary-text-color, #9ca3af);
      font-size: 1rem;
      padding: 4px 8px;
      cursor: pointer;
      line-height: 1;
      transition: background 0.15s;
    }

    .nav-btn:hover {
      background: rgba(255, 255, 255, 0.1);
      color: var(--primary-text-color, #ffffff);
    }

    .day-label {
      font-size: 0.8rem;
      font-weight: 600;
      padding: 0 4px;
      min-width: 60px;
      text-align: center;
      color: var(--primary-text-color, #ffffff);
    }

    /* Section 1: Timeline Track */
    .timeline-section {
      margin-bottom: 14px;
    }

    .timeline-track-wrap {
      position: relative;
      height: 38px;
      background: rgba(15, 23, 42, 0.6);
      border-radius: 8px;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      overflow: hidden;
      box-sizing: border-box;
    }

    .timeline-block {
      position: absolute;
      top: 0;
      bottom: 0;
      border-radius: 4px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 0 4px;
      box-sizing: border-box;
      pointer-events: none;
    }

    .dual-band {
      display: flex;
      flex-direction: column;
      height: 100%;
      width: 100%;
    }

    .band-half {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.7rem;
      font-weight: 700;
      line-height: 1;
    }

    .band-single {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 700;
    }

    .now-needle {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 2px;
      background: #ffffff;
      box-shadow: 0 0 6px rgba(255, 255, 255, 0.8), -1px 0 0 rgba(0, 0, 0, 0.8), 1px 0 0 rgba(0, 0, 0, 0.8);
      z-index: 10;
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
    }

    .time-ticks {
      display: flex;
      justify-content: space-between;
      margin-top: 4px;
      font-size: 0.68rem;
      color: var(--secondary-text-color, #9ca3af);
      padding: 0 2px;
    }

    .overlay-msg {
      position: absolute;
      inset: 0;
      background: rgba(15, 23, 42, 0.85);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--secondary-text-color, #cbd5e1);
      z-index: 5;
    }

    /* Section 2: Comfort Boost Toolbar */
    .boost-section {
      background: rgba(255, 255, 255, 0.02);
      border-radius: 8px;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.06));
      padding: 10px 12px;
      margin-bottom: 12px;
    }

    .boost-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 8px;
    }

    .boost-title {
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--secondary-text-color, #94a3b8);
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .boost-subtitle {
      font-size: 0.72rem;
      color: var(--secondary-text-color, #64748b);
    }

    .boost-controls {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: nowrap;
      width: 100%;
    }

    .boost-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      padding: 6px 8px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease-in-out;
      white-space: nowrap;
      flex: 1 1 auto;
      min-width: 0;
    }

    .boost-btn-warm {
      background: rgba(239, 68, 68, 0.12);
      color: #f87171;
      border-color: rgba(239, 68, 68, 0.25);
    }

    .boost-btn-warm:hover {
      background: rgba(239, 68, 68, 0.2);
      border-color: #ef4444;
      color: #ffffff;
    }

    .boost-btn-cool {
      background: rgba(56, 189, 248, 0.12);
      color: #38bdf8;
      border-color: rgba(56, 189, 248, 0.25);
    }

    .boost-btn-cool:hover {
      background: rgba(56, 189, 248, 0.2);
      border-color: #38bdf8;
      color: #ffffff;
    }

    .boost-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      white-space: nowrap;
      flex-shrink: 0;
      margin-left: auto;
    }

    .boost-pill.warm {
      background: rgba(239, 68, 68, 0.2);
      color: #fca5a5;
      border: 1px solid rgba(239, 68, 68, 0.4);
    }

    .boost-pill.cool {
      background: rgba(56, 189, 248, 0.2);
      color: #7dd3fc;
      border: 1px solid rgba(56, 189, 248, 0.4);
    }

    .boost-cancel-btn {
      background: none;
      border: none;
      color: inherit;
      cursor: pointer;
      font-weight: 700;
      font-size: 0.8rem;
      padding: 0 0 0 2px;
      line-height: 1;
      opacity: 0.8;
      transition: opacity 0.15s;
    }

    .boost-cancel-btn:hover {
      opacity: 1;
    }

    /* Section 3: Expandable Diagnostics */
    .diagnostics-section {
      border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      padding-top: 8px;
    }

    .diagnostics-toggle-btn {
      width: 100%;
      background: none;
      border: none;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 4px 2px;
      font-size: 0.78rem;
      font-weight: 600;
      color: var(--secondary-text-color, #94a3b8);
      cursor: pointer;
      text-align: left;
    }

    .diagnostics-toggle-btn:hover {
      color: var(--primary-text-color, #ffffff);
    }

    .diagnostics-drawer {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-top: 8px;
      animation: fadeIn 0.15s ease-in-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .diag-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 8px;
    }

    .diag-card {
      background: rgba(255, 255, 255, 0.03);
      border-radius: 6px;
      padding: 6px 8px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .diag-label {
      font-size: 0.7rem;
      font-weight: 600;
      color: var(--secondary-text-color, #94a3b8);
      margin-bottom: 2px;
    }

    .diag-value {
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--primary-text-color, #f1f5f9);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .diag-explanation {
      font-size: 0.75rem;
      font-style: italic;
      color: var(--secondary-text-color, #cbd5e1);
      background: rgba(255, 255, 255, 0.02);
      border-left: 2px solid var(--primary-color, #38bdf8);
      padding: 6px 10px;
      border-radius: 0 4px 4px 0;
      line-height: 1.35;
    }
  `;

  render() {
    if (!this.config?.entity) {
      return html`
        <ha-card>
          <div style="padding: 16px; text-align: center; color: var(--secondary-text-color);">
            Please configure a target space climate entity.
          </div>
        </ha-card>
      `;
    }

    const stateObj = this.hass?.states[this.config.entity];
    const friendlyName =
      this.config.title ||
      stateObj?.attributes?.friendly_name ||
      this.config.entity.replace('climate.', '').replace(/_/g, ' ');

    const currentBoost = Number(stateObj?.attributes?.current_boost || 0.0);
    const hasBoost = Math.abs(currentBoost) >= 0.1;

    const selectedDay = DAYS_OF_WEEK[this.selectedDayIndex];
    const dayLabel = DAY_LABELS[selectedDay];
    const todayIndex = (new Date().getDay() + 6) % 7;
    const isViewingToday = this.selectedDayIndex === todayIndex;
    const dayBlocks = this.blocksByDay[selectedDay] || [];

    // NOW needle calculation
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const nowPct = Math.min(100, Math.max(0, (nowMinutes / 1440) * 100));

    return html`
      <ha-card>
        <!-- Card Header -->
        <div class="header">
          <div class="header-left">
            <span class="card-title" title="${friendlyName}">${friendlyName}</span>
            <span
              class="preset-chip ${this.isManual ? 'manual' : ''}"
              title="${this.isManual ? 'Manual Hold Mode' : this.currentPresetMode}"
            >
              ${this.isManual ? '⚠️ Manual Hold' : `🎯 ${this.currentPresetMode}`}
            </span>
          </div>

          <!-- Day Navigation -->
          <div class="day-nav">
            <button class="nav-btn" @click=${() => this.changeDay(-1)} title="Previous Day">‹</button>
            <span class="day-label">${isViewingToday ? `Today (${dayLabel.short})` : dayLabel.short}</span>
            <button class="nav-btn" @click=${() => this.changeDay(1)} title="Next Day">›</button>
          </div>
        </div>

        <!-- Section 1: 24h Schedule Timeline -->
        ${this.config.show_schedule !== false
          ? html`
              <div class="timeline-section">
                <div class="timeline-track-wrap">
                  <!-- Status Overlays -->
                  ${this.isManual
                    ? html`<div class="overlay-msg"><span>⏸️ Manual Hold Active — No schedule running</span></div>`
                    : this.isYamlSchedule
                    ? html`<div class="overlay-msg"><span>📄 YAML Schedule Active — Read-only</span></div>`
                    : this.isForeign
                    ? html`<div class="overlay-msg"><span>⚠️ Non-HVAC Schedule Active — Read-only</span></div>`
                    : this.scheduleNotFound
                    ? html`<div class="overlay-msg"><span>Schedule not found for preset "${this.currentPresetMode}"</span></div>`
                    : ''}

                  <!-- Timeline Blocks -->
                  ${dayBlocks.map((block) => {
                    const left = (block.startMinutes / 1440) * 100;
                    const width = ((block.endMinutes - block.startMinutes) / 1440) * 100;

                    if (block.hvac_mode === 'heat_cool') {
                      return html`
                        <div class="timeline-block" style="left: ${left}%; width: ${width}%;">
                          <div class="dual-band">
                            <div class="band-half" style="background: ${getCoolColor(block.cool_to)}; color: ${getCoolTextColor(block.cool_to)};">
                              ${block.cool_to}°
                            </div>
                            <div class="band-half" style="background: ${getHeatColor(block.heat_to)}; color: ${getHeatTextColor(block.heat_to)};">
                              ${block.heat_to}°
                            </div>
                          </div>
                        </div>
                      `;
                    } else if (block.hvac_mode === 'heat') {
                      return html`
                        <div class="timeline-block" style="left: ${left}%; width: ${width}%;">
                          <div class="band-single" style="background: ${getHeatColor(block.heat_to)}; color: ${getHeatTextColor(block.heat_to)};">
                            ${block.heat_to}°
                          </div>
                        </div>
                      `;
                    } else if (block.hvac_mode === 'cool') {
                      return html`
                        <div class="timeline-block" style="left: ${left}%; width: ${width}%;">
                          <div class="band-single" style="background: ${getCoolColor(block.cool_to)}; color: ${getCoolTextColor(block.cool_to)};">
                            ${block.cool_to}°
                          </div>
                        </div>
                      `;
                    } else {
                      return html`
                        <div class="timeline-block" style="left: ${left}%; width: ${width}%;">
                          <div class="band-single" style="background: #334155; color: #94a3b8;">
                            OFF
                          </div>
                        </div>
                      `;
                    }
                  })}

                  <!-- NOW Needle (shown only on today's view) -->
                  ${isViewingToday
                    ? html`<div class="now-needle" style="left: ${nowPct}%;" title="Current Time"></div>`
                    : ''}
                </div>

                <!-- Time Ticks -->
                <div class="time-ticks">
                  <span>12a</span>
                  <span>4a</span>
                  <span>8a</span>
                  <span>12p</span>
                  <span>4p</span>
                  <span>8p</span>
                  <span>12a</span>
                </div>
              </div>
            `
          : ''}

        <!-- Section 2: Comfort Boost Toolbar -->
        ${this.config.show_boost !== false
          ? html`
              <div class="boost-section">
                <div class="boost-header">
                  <span class="boost-title">🕒 Temporary Comfort Bump</span>
                  <span class="boost-subtitle">2-hour boost • Decays back to schedule</span>
                </div>
                <div class="boost-controls">
                  <button
                    class="boost-btn boost-btn-warm"
                    @click=${() => this.triggerComfortBoost('too_cold')}
                    title="Applies a temporary +2°F boost that automatically decays back to schedule"
                  >
                    🔥 Warmer (+2°)
                  </button>
                  <button
                    class="boost-btn boost-btn-cool"
                    @click=${() => this.triggerComfortBoost('too_hot')}
                    title="Applies a temporary -2°F cooling boost that automatically decays back to schedule"
                  >
                    ❄️ Cooler (-2°)
                  </button>

                  ${hasBoost
                    ? html`
                        <div class="boost-pill ${currentBoost > 0 ? 'warm' : 'cool'}">
                          <span>${currentBoost > 0 ? '🔥' : '❄️'} ${currentBoost > 0 ? `+${currentBoost}` : currentBoost}°</span>
                          <button
                            class="boost-cancel-btn"
                            @click=${this.clearComfortBoost}
                            title="Cancel temporary boost and return to schedule"
                          >
                            ✕ Cancel
                          </button>
                        </div>
                      `
                    : ''}
                </div>
              </div>
            `
          : ''}

        <!-- Section 3: Expandable Diagnostics & Attributes -->
        ${this.config.show_diagnostics !== false
          ? html`
              <div class="diagnostics-section">
                <button
                  class="diagnostics-toggle-btn"
                  @click=${() => (this.diagnosticsExpanded = !this.diagnosticsExpanded)}
                >
                  <span>ℹ️ Space Details & Diagnostics</span>
                  <span>${this.diagnosticsExpanded ? '▲ Hide' : '▼ Show'}</span>
                </button>

                ${this.diagnosticsExpanded
                  ? html`
                      <div class="diagnostics-drawer">
                        <div class="diag-grid">
                          ${this.renderDiagnosticAttributes(stateObj?.attributes || {})}
                        </div>
                        ${this.shouldShowAttribute('explanation') && stateObj?.attributes?.explanation
                          ? html`
                              <div class="diag-explanation">
                                "${stateObj.attributes.explanation}"
                              </div>
                            `
                          : ''}
                      </div>
                    `
                  : ''}
              </div>
            `
          : ''}
      </ha-card>
    `;
  }

  private shouldShowAttribute(attrKey: string): boolean {
    const list = this.config.diagnostic_attributes || [
      'phase',
      'active_producer',
      'explanation',
      'window_open'
    ];
    return list.includes(attrKey);
  }

  private renderDiagnosticAttributes(attrs: Record<string, any>) {
    const cards = [];

    if (this.shouldShowAttribute('phase')) {
      const rawPhase = attrs.phase || 'plateau_maintenance';
      const label = rawPhase.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
      cards.push(html`
        <div class="diag-card">
          <div class="diag-label">System Phase</div>
          <div class="diag-value" title="${label}">${label}</div>
        </div>
      `);
    }

    if (this.shouldShowAttribute('active_producer')) {
      const prod = attrs.active_producer || 'None (Idle)';
      cards.push(html`
        <div class="diag-card">
          <div class="diag-label">Active Producer</div>
          <div class="diag-value" title="${prod}">${prod}</div>
        </div>
      `);
    }

    if (this.shouldShowAttribute('window_open')) {
      const isOpen = Boolean(attrs.window_open);
      cards.push(html`
        <div class="diag-card">
          <div class="diag-label">Window Interlock</div>
          <div class="diag-value" style="color: ${isOpen ? '#f87171' : '#34d399'};">
            ${isOpen ? '⚠️ Open (Paused)' : 'Closed'}
          </div>
        </div>
      `);
    }

    if (this.shouldShowAttribute('active_delivery_units')) {
      const units = attrs.active_delivery_units || [];
      const label = units.length > 0 ? units.join(', ') : 'None';
      cards.push(html`
        <div class="diag-card">
          <div class="diag-label">Delivery Units</div>
          <div class="diag-value" title="${label}">${label}</div>
        </div>
      `);
    }

    if (this.shouldShowAttribute('cycling_emitters')) {
      const cycling = attrs.cycling_emitters || [];
      const label = cycling.length > 0 ? cycling.join(', ') : 'None';
      cards.push(html`
        <div class="diag-card">
          <div class="diag-label">Cycling Emitters</div>
          <div class="diag-value" title="${label}">${label}</div>
        </div>
      `);
    }

    if (this.shouldShowAttribute('in_recovery')) {
      const inRec = Boolean(attrs.in_recovery);
      cards.push(html`
        <div class="diag-card">
          <div class="diag-label">Recovery State</div>
          <div class="diag-value">${inRec ? 'In Recovery' : 'Normal'}</div>
        </div>
      `);
    }

    return cards;
  }
}

// Register both custom:hvac-fusion-status-card and legacy alias custom:climate-preset-timeline
if (!customElements.get('hvac-fusion-status-card')) {
  customElements.define('hvac-fusion-status-card', HvacFusionStatusCard);
}
if (!customElements.get('climate-preset-timeline')) {
  customElements.define(
    'climate-preset-timeline',
    class extends HvacFusionStatusCard {}
  );
}
