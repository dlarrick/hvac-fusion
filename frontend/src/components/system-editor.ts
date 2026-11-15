import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { DEFAULT_SYSTEM_DIAGNOSTICS, HomeAssistant, SystemCardConfig } from '../types';

const AVAILABLE_SYSTEM_DIAGNOSTICS = [
  { key: 'system_phase', label: 'System Phase' },
  { key: 'break_even_cop', label: 'Break-Even COP' },
  { key: 'control_enabled', label: 'Control Mode (Autonomous / Dry Run)' },
  { key: 'heat_pump', label: 'Primary Heat Pump ID' },
  { key: 'auxiliary_producer', label: 'Auxiliary Producer ID' },
  { key: 'cumulative_estimated_cost', label: 'Cumulative Estimated Cost' }
];

@customElement('hvac-fusion-system-card-editor')
export class HvacFusionSystemEditor extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @state() private config!: SystemCardConfig;

  public setConfig(config: SystemCardConfig) {
    this.config = { ...config };
  }

  private getSensorEntities(filter?: string): string[] {
    if (!this.hass?.states) return [];
    return Object.keys(this.hass.states)
      .filter((id) => id.startsWith('sensor.') && (!filter || id.includes(filter)))
      .sort();
  }

  private updateConfig(updates: Partial<SystemCardConfig>) {
    const newConfig = { ...this.config, ...updates };
    this.config = newConfig;
    this.dispatchEvent(
      new CustomEvent('config-changed', {
        detail: { config: newConfig },
        bubbles: true,
        composed: true
      })
    );
  }

  private toggleDiagnosticAttr(key: string, checked: boolean) {
    const current = this.config.diagnostic_attributes || DEFAULT_SYSTEM_DIAGNOSTICS;
    const next = checked
      ? Array.from(new Set([...current, key]))
      : current.filter((k) => k !== key);
    this.updateConfig({ diagnostic_attributes: next });
  }

  static styles = css`
    .editor-container {
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 8px 0;
      color: var(--primary-text-color, #ffffff);
      font-family: inherit;
    }

    .field-group {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .field-label {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--secondary-text-color, #94a3b8);
    }

    .form-input,
    .form-select {
      width: 100%;
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.2));
      background: var(--card-background-color, #1e293b);
      color: var(--primary-text-color, #f8fafc);
      font-size: 0.9rem;
      box-sizing: border-box;
      color-scheme: dark;
    }

    .form-select option {
      background: var(--card-background-color, #1e293b);
      color: var(--primary-text-color, #f8fafc);
    }

    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.88rem;
      cursor: pointer;
    }

    .section-title {
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--secondary-text-color, #94a3b8);
      border-bottom: 1px solid var(--divider-color, rgba(255, 255, 255, 0.1));
      padding-bottom: 4px;
      margin-top: 4px;
    }

    .attrs-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 8px;
      padding-top: 4px;
    }

    .helper-text {
      font-size: 0.76rem;
      color: var(--secondary-text-color, #94a3b8);
    }
  `;

  render() {
    if (!this.config) return html``;

    const allSensors = this.getSensorEntities();
    const xoverSensors = this.getSensorEntities('economic_crossover_temperature');
    const primarySensors = xoverSensors.length > 0 ? xoverSensors : allSensors;
    const selectedAttrs = this.config.diagnostic_attributes || DEFAULT_SYSTEM_DIAGNOSTICS;

    return html`
      <div class="editor-container">
        <div class="field-group">
          <label class="field-label">Economic Crossover Sensor (Required)</label>
          <select
            class="form-select"
            .value=${this.config.entity || ''}
            @change=${(e: any) => this.updateConfig({ entity: e.target.value })}
          >
            <option value="">-- Select Crossover Sensor --</option>
            ${primarySensors.map(
              (eid) => html`
                <option value=${eid} ?selected=${this.config.entity === eid}>
                  ${this.hass.states[eid]?.attributes?.friendly_name || eid} (${eid})
                </option>
              `
            )}
          </select>
          <span class="helper-text">
            Sibling cost, savings, and producer sensors are auto-discovered from this entity.
          </span>
        </div>

        <div class="field-group">
          <label class="field-label">Card Title (Optional)</label>
          <input
            type="text"
            class="form-input"
            .value=${this.config.title || ''}
            placeholder="HVAC Fusion"
            @input=${(e: any) => this.updateConfig({ title: e.target.value })}
          />
        </div>

        <div class="section-title">Visible Sections</div>

        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.config.show_costs !== false}
            @change=${(e: any) => this.updateConfig({ show_costs: e.target.checked })}
          />
          <span>Show Costs & Baseline Savings</span>
        </label>

        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.config.show_producers !== false}
            @change=${(e: any) => this.updateConfig({ show_producers: e.target.checked })}
          />
          <span>Show Producers</span>
        </label>

        <label class="checkbox-row">
          <input
            type="checkbox"
            .checked=${this.config.show_diagnostics !== false}
            @change=${(e: any) => this.updateConfig({ show_diagnostics: e.target.checked })}
          />
          <span>Show Expandable System Diagnostics Drawer</span>
        </label>

        ${this.config.show_diagnostics !== false
          ? html`
              <label class="checkbox-row" style="margin-left: 20px;">
                <input
                  type="checkbox"
                  .checked=${Boolean(this.config.diagnostics_expanded_by_default)}
                  @change=${(e: any) =>
                    this.updateConfig({ diagnostics_expanded_by_default: e.target.checked })}
                />
                <span>Expanded by default</span>
              </label>

              <div class="section-title">System Diagnostic Attributes</div>
              <div class="attrs-grid">
                ${AVAILABLE_SYSTEM_DIAGNOSTICS.map(
                  (attr) => html`
                    <label class="checkbox-row">
                      <input
                        type="checkbox"
                        .checked=${selectedAttrs.includes(attr.key)}
                        @change=${(e: any) =>
                          this.toggleDiagnosticAttr(attr.key, e.target.checked)}
                      />
                      <span>${attr.label}</span>
                    </label>
                  `
                )}
              </div>
            `
          : ''}
      </div>
    `;
  }
}

if (!customElements.get('hvac-fusion-system-card-editor')) {
  customElements.define('hvac-fusion-system-card-editor', HvacFusionSystemEditor);
}
