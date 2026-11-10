import { LitElement, html, css } from 'lit';
import { property, state } from 'lit/decorators.js';
import { HomeAssistant } from '../types';
import { TimelineCardConfig } from '../climate-preset-timeline';

export class ClimatePresetTimelineEditor extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config!: TimelineCardConfig;

  static styles = css`
    :host {
      display: block;
      font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      color: var(--primary-text-color, #e1e7ec);
    }

    .editor-container {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 12px 4px;
    }

    .form-row {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-label {
      font-size: 0.88rem;
      font-weight: 500;
      color: var(--secondary-text-color, #9ca3af);
    }

    .form-input,
    .form-select {
      background: var(--input-idle-line-color, rgba(255, 255, 255, 0.08));
      color: var(--primary-text-color, #ffffff);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
      border-radius: 8px;
      padding: 10px 12px;
      font-size: 0.92rem;
      box-sizing: border-box;
      width: 100%;
      outline: none;
      transition: border-color 0.15s;
    }

    .form-input:focus,
    .form-select:focus {
      border-color: var(--primary-color, #38bdf8);
    }

    .form-select {
      color-scheme: dark;
    }
    .form-select optgroup {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      color: var(--secondary-text-color, #9ca3af);
    }
    .form-select option {
      background: var(--card-background-color, var(--ha-card-background, #1e293b));
      color: var(--primary-text-color, #ffffff);
    }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }

    .unit-selector {
      display: flex;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.15));
    }

    .unit-btn {
      flex: 1;
      padding: 8px 12px;
      background: rgba(255, 255, 255, 0.05);
      border: none;
      color: var(--secondary-text-color, #9ca3af);
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      transition: all 0.15s;
    }

    .unit-btn.active {
      background: var(--primary-color, #38bdf8);
      color: #0f172a;
    }
  `;

  public setConfig(config: TimelineCardConfig) {
    this._config = {
      step_size: 15,
      temperature_unit: '°F',
      min_deadband: 2,
      ...config,
      type: 'custom:climate-preset-timeline'
    };
  }

  private _valueChanged(key: keyof TimelineCardConfig, value: any) {
    if (!this._config) return;
    this._config = {
      ...this._config,
      [key]: value
    };

    this.dispatchEvent(
      new CustomEvent('config-changed', {
        detail: { config: this._config },
        bubbles: true,
        composed: true
      })
    );
  }

  render() {
    if (!this._config) return html``;

    // Discover all climate entities in Home Assistant
    const climateEntities = Object.keys(this.hass?.states || {})
      .filter((entityId) => entityId.startsWith('climate.'))
      .sort();

    return html`
      <div class="editor-container">
        <!-- Target Climate Entity -->
        <div class="form-row">
          <label class="form-label">Climate Space Leader Entity (Required)</label>
          <select
            class="form-select"
            .value=${this._config.entity || ''}
            @change=${(e: Event) => this._valueChanged('entity', (e.target as HTMLSelectElement).value)}
          >
            <option value="">(Select a climate entity...)</option>
            ${climateEntities.map((id) => {
              const stateObj = this.hass?.states[id];
              const friendlyName = stateObj?.attributes?.friendly_name || id;
              const hasPresets = stateObj?.attributes?.presets || stateObj?.attributes?.preset_modes;
              return html`
                <option value=${id} ?selected=${this._config.entity === id}>
                  ${friendlyName} (${id}) ${hasPresets ? '⭐' : ''}
                </option>
              `;
            })}
          </select>
          <span style="font-size: 0.75rem; color: var(--secondary-text-color, #9ca3af);">
            The card will automatically follow this climate entity's active preset mode and display its corresponding schedule.
          </span>
        </div>

        <!-- Card Title -->
        <div class="form-row">
          <label class="form-label">Card Title (optional)</label>
          <input
            type="text"
            class="form-input"
            placeholder="e.g. Climate Preset 1-day Timeline"
            .value=${this._config.title || ''}
            @input=${(e: Event) => this._valueChanged('title', (e.target as HTMLInputElement).value)}
          />
        </div>

        <!-- Settings Grid -->
        <div class="form-grid">
          <!-- Temperature Unit -->
          <div class="form-row">
            <label class="form-label">Temperature Unit</label>
            <div class="unit-selector">
              <button
                type="button"
                class="unit-btn ${this._config.temperature_unit !== '°C' ? 'active' : ''}"
                @click=${() => this._valueChanged('temperature_unit', '°F')}
              >°F</button>
              <button
                type="button"
                class="unit-btn ${this._config.temperature_unit === '°C' ? 'active' : ''}"
                @click=${() => this._valueChanged('temperature_unit', '°C')}
              >°C</button>
            </div>
          </div>

          <!-- Time Step Size -->
          <div class="form-row">
            <label class="form-label">Snapping Interval</label>
            <select
              class="form-select"
              .value=${String(this._config.step_size || 15)}
              @change=${(e: Event) => this._valueChanged('step_size', parseInt((e.target as HTMLSelectElement).value, 10))}
            >
              <option value="15" ?selected=${(this._config.step_size || 15) === 15}>15 Minutes</option>
              <option value="30" ?selected=${this._config.step_size === 30}>30 Minutes</option>
              <option value="60" ?selected=${this._config.step_size === 60}>60 Minutes</option>
            </select>
          </div>
        </div>

        <!-- Minimum Deadband -->
        <div class="form-row">
          <label class="form-label">Min Deadband Between Heat & Cool</label>
          <input
            type="number"
            class="form-input"
            min="0"
            max="15"
            step="1"
            .value=${String(this._config.min_deadband ?? 2)}
            @input=${(e: Event) => this._valueChanged('min_deadband', parseFloat((e.target as HTMLInputElement).value) || 0)}
          />
        </div>
      </div>
    `;
  }
}

if (!customElements.get('climate-preset-timeline-editor')) {
  customElements.define('climate-preset-timeline-editor', ClimatePresetTimelineEditor);
}
