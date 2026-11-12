import { LitElement, html, css } from 'lit';
import { property, state } from 'lit/decorators.js';
import { HomeAssistant, StatusCardConfig } from '../types';

export class HvacFusionStatusEditor extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config!: StatusCardConfig;

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

    .checkbox-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      border-radius: 8px;
      padding: 12px;
    }

    .checkbox-item {
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
      font-size: 0.88rem;
      color: var(--primary-text-color, #f1f5f9);
    }

    .checkbox-item input[type='checkbox'] {
      width: 16px;
      height: 16px;
      cursor: pointer;
      accent-color: var(--primary-color, #38bdf8);
    }

    .section-title {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--primary-color, #38bdf8);
      margin-top: 4px;
    }
  `;

  public setConfig(config: StatusCardConfig) {
    this._config = {
      show_schedule: true,
      show_boost: true,
      show_diagnostics: true,
      diagnostics_expanded_by_default: false,
      diagnostic_attributes: ['phase', 'active_producer', 'explanation', 'window_open'],
      ...config,
      type: 'custom:hvac-fusion-status-card'
    };
  }

  private _valueChanged(key: keyof StatusCardConfig, value: any) {
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

  private _toggleDiagnosticAttribute(attrKey: string, checked: boolean) {
    const current = this._config.diagnostic_attributes || [
      'phase',
      'active_producer',
      'explanation',
      'window_open'
    ];
    let next: string[];
    if (checked) {
      next = current.includes(attrKey) ? current : [...current, attrKey];
    } else {
      next = current.filter((k) => k !== attrKey);
    }
    this._valueChanged('diagnostic_attributes', next);
  }

  render() {
    if (!this._config) return html``;

    // Discover climate entities
    const climateEntities = Object.keys(this.hass?.states || {})
      .filter((entityId) => entityId.startsWith('climate.'))
      .sort();

    const selectedAttrs = this._config.diagnostic_attributes || [
      'phase',
      'active_producer',
      'explanation',
      'window_open'
    ];

    return html`
      <div class="editor-container">
        <!-- Target Climate Entity -->
        <div class="form-row">
          <label class="form-label">Space Climate Entity (Required)</label>
          <select
            class="form-select"
            .value=${this._config.entity || ''}
            @change=${(e: Event) =>
              this._valueChanged('entity', (e.target as HTMLSelectElement).value)}
          >
            <option value="">(Select a climate entity...)</option>
            ${climateEntities.map((id) => {
              const stateObj = this.hass?.states[id];
              const friendlyName = stateObj?.attributes?.friendly_name || id;
              const isHvacFusion = stateObj?.attributes?.current_boost !== undefined;
              return html`
                <option value=${id} ?selected=${this._config.entity === id}>
                  ${friendlyName} (${id}) ${isHvacFusion ? '⚡' : ''}
                </option>
              `;
            })}
          </select>
          <span style="font-size: 0.75rem; color: var(--secondary-text-color, #9ca3af);">
            Bound space entity (e.g. climate.living_room_space).
          </span>
        </div>

        <!-- Custom Card Title -->
        <div class="form-row">
          <label class="form-label">Card Title (optional override)</label>
          <input
            type="text"
            class="form-input"
            placeholder="e.g. Living Room Space"
            .value=${this._config.title || ''}
            @input=${(e: Event) =>
              this._valueChanged('title', (e.target as HTMLInputElement).value)}
          />
        </div>

        <!-- Section 1 & 2 & 3 Visibility Toggles -->
        <div class="form-row">
          <span class="section-title">Card Sections</span>
          <div class="checkbox-group">
            <label class="checkbox-item">
              <input
                type="checkbox"
                ?checked=${this._config.show_schedule !== false}
                @change=${(e: Event) =>
                  this._valueChanged('show_schedule', (e.target as HTMLInputElement).checked)}
              />
              <span>Show 24-Hour Schedule Timeline</span>
            </label>

            <label class="checkbox-item">
              <input
                type="checkbox"
                ?checked=${this._config.show_boost !== false}
                @change=${(e: Event) =>
                  this._valueChanged('show_boost', (e.target as HTMLInputElement).checked)}
              />
              <span>Show Temporary Comfort Bump Toolbar</span>
            </label>

            <label class="checkbox-item">
              <input
                type="checkbox"
                ?checked=${this._config.show_diagnostics !== false}
                @change=${(e: Event) =>
                  this._valueChanged('show_diagnostics', (e.target as HTMLInputElement).checked)}
              />
              <span>Show Space Details & Diagnostics Accordion</span>
            </label>
          </div>
        </div>

        <!-- Space Diagnostics Attributes Checklist -->
        ${this._config.show_diagnostics !== false
          ? html`
              <div class="form-row">
                <span class="section-title">Space Diagnostic Attributes to Display</span>
                <div class="checkbox-group">
                  <label class="checkbox-item">
                    <input
                      type="checkbox"
                      ?checked=${selectedAttrs.includes('phase')}
                      @change=${(e: Event) =>
                        this._toggleDiagnosticAttribute(
                          'phase',
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span>System Phase (Plateau Maintenance / Recovery / Ventilation)</span>
                  </label>

                  <label class="checkbox-item">
                    <input
                      type="checkbox"
                      ?checked=${selectedAttrs.includes('active_producer')}
                      @change=${(e: Event) =>
                        this._toggleDiagnosticAttribute(
                          'active_producer',
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span>Active Producer (e.g. Heat Pump, Boiler)</span>
                  </label>

                  <label class="checkbox-item">
                    <input
                      type="checkbox"
                      ?checked=${selectedAttrs.includes('explanation')}
                      @change=${(e: Event) =>
                        this._toggleDiagnosticAttribute(
                          'explanation',
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span>Dispatch Explanation (Live explanation string from coordinator)</span>
                  </label>

                  <label class="checkbox-item">
                    <input
                      type="checkbox"
                      ?checked=${selectedAttrs.includes('window_open')}
                      @change=${(e: Event) =>
                        this._toggleDiagnosticAttribute(
                          'window_open',
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span>Window / Door Interlock (Open vs Closed)</span>
                  </label>

                  <label class="checkbox-item">
                    <input
                      type="checkbox"
                      ?checked=${selectedAttrs.includes('active_delivery_units')}
                      @change=${(e: Event) =>
                        this._toggleDiagnosticAttribute(
                          'active_delivery_units',
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span>Active Delivery Units (Indoor heads / hydronic loops)</span>
                  </label>

                  <label class="checkbox-item">
                    <input
                      type="checkbox"
                      ?checked=${selectedAttrs.includes('cycling_emitters')}
                      @change=${(e: Event) =>
                        this._toggleDiagnosticAttribute(
                          'cycling_emitters',
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span>Cycling Emitters (Emitters clamped by limit hysteresis)</span>
                  </label>

                  <label class="checkbox-item">
                    <input
                      type="checkbox"
                      ?checked=${selectedAttrs.includes('in_recovery')}
                      @change=${(e: Event) =>
                        this._toggleDiagnosticAttribute(
                          'in_recovery',
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span>Setback Recovery State</span>
                  </label>

                  <hr style="border: 0; border-top: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08)); margin: 4px 0;" />

                  <label class="checkbox-item">
                    <input
                      type="checkbox"
                      ?checked=${Boolean(this._config.diagnostics_expanded_by_default)}
                      @change=${(e: Event) =>
                        this._valueChanged(
                          'diagnostics_expanded_by_default',
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span style="font-weight: 500; color: var(--secondary-text-color, #9ca3af);">
                      Expand diagnostics by default (instead of collapsed)
                    </span>
                  </label>
                </div>
              </div>
            `
          : ''}
      </div>
    `;
  }
}

// Register both hvac-fusion-status-editor and legacy alias climate-preset-timeline-editor
if (!customElements.get('hvac-fusion-status-editor')) {
  customElements.define('hvac-fusion-status-editor', HvacFusionStatusEditor);
}
if (!customElements.get('climate-preset-timeline-editor')) {
  customElements.define(
    'climate-preset-timeline-editor',
    class extends HvacFusionStatusEditor {}
  );
}
