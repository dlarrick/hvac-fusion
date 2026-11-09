import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { DAY_LABELS, InternalBlock, ScheduleDay } from '../types';
import { formatTimeDisplay } from '../utils/time';
import { getCoolColor, getCoolTextColor, getHeatColor, getHeatTextColor } from '../utils/colors';

export class PresetDialog extends LitElement {
  @property({ type: Object }) block!: InternalBlock;
  @property({ type: String }) temperatureUnit: '°F' | '°C' = '°F';
  @property({ type: Number }) minDeadband = 2;
  @property({ type: Number }) minTemp = 45;
  @property({ type: Number }) maxTemp = 85;

  @state() private currentMode: 'heat_cool' | 'heat' | 'cool' | 'off' = 'heat_cool';
  @state() private heatTo = 68;
  @state() private coolTo = 74;
  @state() private splitMinute = 720;

  static styles = css`
    :host {
      display: block;
    }

    .modal-backdrop {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.65);
      backdrop-filter: blur(4px);
      z-index: 999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      box-sizing: border-box;
    }

    .dialog-card {
      background: var(--card-background-color, #1f2937);
      color: var(--primary-text-color, #f3f4f6);
      border-radius: 16px;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      width: 100%;
      max-width: 440px;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
      overflow: hidden;
      animation: popIn 0.18s ease-out;
    }

    @keyframes popIn {
      from {
        opacity: 0;
        transform: scale(0.95);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }

    .dialog-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .dialog-title {
      font-size: 1.15rem;
      font-weight: 600;
      margin: 0;
    }

    .dialog-subtitle {
      font-size: 0.85rem;
      color: var(--secondary-text-color, #9ca3af);
      margin-top: 2px;
    }

    .close-btn {
      background: transparent;
      border: none;
      color: var(--secondary-text-color, #9ca3af);
      font-size: 1.5rem;
      cursor: pointer;
      line-height: 1;
      padding: 4px;
      border-radius: 6px;
    }
    .close-btn:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.08);
    }

    .dialog-body {
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Mode selector */
    .mode-selector {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      background: rgba(0, 0, 0, 0.25);
      padding: 4px;
      border-radius: 10px;
    }

    .mode-btn {
      padding: 8px 6px;
      font-size: 0.82rem;
      font-weight: 500;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      background: transparent;
      color: var(--secondary-text-color, #9ca3af);
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
    }

    .mode-btn:hover {
      color: #fff;
    }

    .mode-btn.active {
      background: var(--primary-color, #3b82f6);
      color: #ffffff;
      font-weight: 600;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    /* Temperature controls */
    .setpoint-section {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .stepper-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .stepper-label {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .stepper-name {
      font-size: 0.9rem;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .stepper-badge {
      font-size: 1.3rem;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 8px;
      min-width: 55px;
      text-align: center;
    }

    .stepper-controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .step-btn {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
      font-size: 1.2rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.15s;
    }
    .step-btn:hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.2);
    }
    .step-btn:disabled {
      opacity: 0.3;
      cursor: not-allowed;
    }

    /* Split block section */
    .split-section {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 12px 14px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px dashed rgba(255, 255, 255, 0.12);
    }

    .split-header {
      font-size: 0.82rem;
      font-weight: 500;
      color: var(--secondary-text-color, #9ca3af);
    }

    .split-controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .split-badge {
      font-size: 0.95rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      color: #fff;
    }

    .split-action-btn {
      margin-left: auto;
      padding: 6px 12px;
      font-size: 0.8rem;
      font-weight: 600;
      border-radius: 6px;
      border: 1px solid var(--primary-color, #38bdf8);
      background: rgba(56, 189, 248, 0.15);
      color: var(--primary-color, #38bdf8);
      cursor: pointer;
      transition: all 0.15s;
    }
    .split-action-btn:hover {
      background: var(--primary-color, #38bdf8);
      color: #fff;
    }

    /* Copy shortcuts */
    .shortcuts-section {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .shortcut-btn {
      flex: 1;
      min-width: 100px;
      padding: 7px 10px;
      font-size: 0.78rem;
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--secondary-text-color, #9ca3af);
      cursor: pointer;
      text-align: center;
      transition: background 0.15s;
    }
    .shortcut-btn:hover {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }

    /* Dialog footer */
    .dialog-footer {
      padding: 16px 20px;
      border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(0, 0, 0, 0.15);
    }

    .delete-btn {
      background: transparent;
      border: 1px solid #ef4444;
      color: #ef4444;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s;
    }
    .delete-btn:hover {
      background: #ef4444;
      color: #fff;
    }

    .save-btn {
      background: var(--primary-color, #3b82f6);
      border: none;
      color: #fff;
      padding: 9px 20px;
      border-radius: 8px;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.15s;
    }
    .save-btn:hover {
      opacity: 0.9;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    if (this.block) {
      this.currentMode = this.block.hvac_mode || 'heat_cool';
      this.heatTo = this.block.heat_to ?? 68;
      this.coolTo = this.block.cool_to ?? 74;
      const dur = this.block.endMinutes - this.block.startMinutes;
      this.splitMinute = Math.min(
        this.block.endMinutes - 15,
        Math.max(this.block.startMinutes + 15, Math.round((this.block.startMinutes + dur / 2) / 15) * 15)
      );
    }
  }

  private stepSplit(deltaMinutes: number) {
    const next = this.splitMinute + deltaMinutes;
    if (next <= this.block.startMinutes || next >= this.block.endMinutes) return;
    this.splitMinute = next;
  }

  private handleSplit() {
    this.dispatchEvent(
      new CustomEvent('split-block', {
        detail: {
          blockId: this.block.id,
          day: this.block.day,
          splitMinute: this.splitMinute
        },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleSetMode(mode: 'heat_cool' | 'heat' | 'cool' | 'off') {
    this.currentMode = mode;
  }

  private stepHeat(delta: number) {
    const next = this.heatTo + delta;
    if (next < this.minTemp) return;
    if (this.currentMode === 'heat_cool' && next > this.coolTo - this.minDeadband) {
      return;
    }
    this.heatTo = next;
  }

  private stepCool(delta: number) {
    const next = this.coolTo + delta;
    if (next > this.maxTemp) return;
    if (this.currentMode === 'heat_cool' && next < this.heatTo + this.minDeadband) {
      return;
    }
    this.coolTo = next;
  }

  private handleSave() {
    this.dispatchEvent(
      new CustomEvent('save-block', {
        detail: {
          block: {
            ...this.block,
            hvac_mode: this.currentMode,
            heat_to: this.heatTo,
            cool_to: this.coolTo
          }
        },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleDelete() {
    this.dispatchEvent(
      new CustomEvent('delete-block', {
        detail: { blockId: this.block.id, day: this.block.day },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleCopyTo(target: 'weekdays' | 'weekend' | 'all') {
    this.dispatchEvent(
      new CustomEvent('copy-block-to', {
        detail: {
          block: {
            ...this.block,
            hvac_mode: this.currentMode,
            heat_to: this.heatTo,
            cool_to: this.coolTo
          },
          target
        },
        bubbles: true,
        composed: true
      })
    );
  }

  private handleClose() {
    this.dispatchEvent(new CustomEvent('close-dialog', { bubbles: true, composed: true }));
  }

  render() {
    if (!this.block) return html``;

    const dayName = DAY_LABELS[this.block.day]?.full || this.block.day;
    const timeRange = `${formatTimeDisplay(this.block.startMinutes)} – ${formatTimeDisplay(this.block.endMinutes)}`;

    const heatColor = getHeatColor(this.heatTo, this.temperatureUnit);
    const heatText = getHeatTextColor(this.heatTo, this.temperatureUnit);
    const coolColor = getCoolColor(this.coolTo, this.temperatureUnit);
    const coolText = getCoolTextColor(this.coolTo, this.temperatureUnit);

    return html`
      <div class="modal-backdrop" @click=${(e: Event) => e.target === e.currentTarget && this.handleClose()}>
        <div class="dialog-card">
          <div class="dialog-header">
            <div>
              <h3 class="dialog-title">${dayName} Preset</h3>
              <div class="dialog-subtitle">${timeRange}</div>
            </div>
            <button class="close-btn" @click=${this.handleClose}>&times;</button>
          </div>

          <div class="dialog-body">
            <!-- Mode Selector -->
            <div class="mode-selector">
              <button
                class="mode-btn ${this.currentMode === 'heat_cool' ? 'active' : ''}"
                @click=${() => this.handleSetMode('heat_cool')}
              >
                <span>Dual</span>
                <span>Auto</span>
              </button>
              <button
                class="mode-btn ${this.currentMode === 'heat' ? 'active' : ''}"
                @click=${() => this.handleSetMode('heat')}
              >
                <span>🔥</span>
                <span>Heat</span>
              </button>
              <button
                class="mode-btn ${this.currentMode === 'cool' ? 'active' : ''}"
                @click=${() => this.handleSetMode('cool')}
              >
                <span>❄️</span>
                <span>Cool</span>
              </button>
              <button
                class="mode-btn ${this.currentMode === 'off' ? 'active' : ''}"
                @click=${() => this.handleSetMode('off')}
              >
                <span>⭕</span>
                <span>Off</span>
              </button>
            </div>

            <!-- Setpoint Steppers -->
            <div class="setpoint-section">
              ${this.currentMode === 'heat_cool' || this.currentMode === 'cool'
                ? html`
                    <div class="stepper-row">
                      <div class="stepper-label">
                        <div class="stepper-name">
                          <span>❄️</span> Cool To
                        </div>
                      </div>
                      <div class="stepper-controls">
                        <button
                          class="step-btn"
                          @click=${() => this.stepCool(-1)}
                          ?disabled=${this.coolTo <= (this.currentMode === 'heat_cool' ? this.heatTo + this.minDeadband : this.minTemp)}
                        >-</button>
                        <div
                          class="stepper-badge"
                          style="background-color: ${coolColor}; color: ${coolText};"
                        >
                          ${this.coolTo}°
                        </div>
                        <button
                          class="step-btn"
                          @click=${() => this.stepCool(1)}
                          ?disabled=${this.coolTo >= this.maxTemp}
                        >+</button>
                      </div>
                    </div>
                  `
                : ''}

              ${this.currentMode === 'heat_cool' || this.currentMode === 'heat'
                ? html`
                    <div class="stepper-row">
                      <div class="stepper-label">
                        <div class="stepper-name">
                          <span>🔥</span> Heat To
                        </div>
                      </div>
                      <div class="stepper-controls">
                        <button
                          class="step-btn"
                          @click=${() => this.stepHeat(-1)}
                          ?disabled=${this.heatTo <= this.minTemp}
                        >-</button>
                        <div
                          class="stepper-badge"
                          style="background-color: ${heatColor}; color: ${heatText};"
                        >
                          ${this.heatTo}°
                        </div>
                        <button
                          class="step-btn"
                          @click=${() => this.stepHeat(1)}
                          ?disabled=${this.heatTo >= (this.currentMode === 'heat_cool' ? this.coolTo - this.minDeadband : this.maxTemp)}
                        >+</button>
                      </div>
                    </div>
                  `
                : ''}

              ${this.currentMode === 'off'
                ? html`
                    <div style="text-align: center; color: var(--secondary-text-color, #9ca3af); font-size: 0.9rem; padding: 12px;">
                      Zone will be turned OFF during this time interval.
                    </div>
                  `
                : ''}
            </div>

            <!-- Split Section -->
            ${this.block.endMinutes - this.block.startMinutes >= 30
              ? html`
                  <div class="split-section">
                    <div class="split-header">✂️ Split Block at Time</div>
                    <div class="split-controls">
                      <button
                        class="step-btn"
                        style="width: 32px; height: 32px; font-size: 1rem;"
                        @click=${() => this.stepSplit(-15)}
                        ?disabled=${this.splitMinute <= this.block.startMinutes + 15}
                      >-</button>
                      <div class="split-badge">${formatTimeDisplay(this.splitMinute)}</div>
                      <button
                        class="step-btn"
                        style="width: 32px; height: 32px; font-size: 1rem;"
                        @click=${() => this.stepSplit(15)}
                        ?disabled=${this.splitMinute >= this.block.endMinutes - 15}
                      >+</button>
                      <button class="split-action-btn" @click=${this.handleSplit}>
                        Split into Two
                      </button>
                    </div>
                  </div>
                `
              : ''}

            <!-- Quick Copy Shortcuts -->
            <div style="font-size: 0.8rem; font-weight: 500; color: var(--secondary-text-color, #9ca3af);">
              Quick Copy:
            </div>
            <div class="shortcuts-section">
              <button class="shortcut-btn" @click=${() => this.handleCopyTo('weekdays')}>
                Copy to Weekdays
              </button>
              <button class="shortcut-btn" @click=${() => this.handleCopyTo('weekend')}>
                Copy to Weekend
              </button>
              <button class="shortcut-btn" @click=${() => this.handleCopyTo('all')}>
                Copy to All 7 Days
              </button>
            </div>
          </div>

          <div class="dialog-footer">
            <button class="delete-btn" @click=${this.handleDelete}>Delete Block</button>
            <button class="save-btn" @click=${this.handleSave}>Apply</button>
          </div>
        </div>
      </div>
    `;
  }
}

if (!customElements.get('preset-dialog')) {
  customElements.define('preset-dialog', PresetDialog);
}
