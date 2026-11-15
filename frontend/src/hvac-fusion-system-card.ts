import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { DEFAULT_SYSTEM_DIAGNOSTICS, HomeAssistant, SystemCardConfig } from './types';
import './components/system-editor';

@customElement('hvac-fusion-system-card')
export class HvacFusionSystemCard extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ attribute: false }) public config!: SystemCardConfig;

  @state() private diagnosticsExpanded = false;

  static getConfigElement() {
    return document.createElement('hvac-fusion-system-card-editor');
  }

  static getStubConfig() {
    return {
      type: 'custom:hvac-fusion-system-card',
      entity: 'sensor.hvac_fusion_economic_crossover_temperature',
      show_costs: true,
      show_producers: true,
      show_diagnostics: true,
      diagnostics_expanded_by_default: false,
      diagnostic_attributes: [...DEFAULT_SYSTEM_DIAGNOSTICS]
    };
  }

  public setConfig(config: SystemCardConfig) {
    if (!config.entity) {
      throw new Error('Please specify the primary economic crossover sensor entity');
    }
    this.config = {
      show_costs: true,
      show_producers: true,
      show_diagnostics: true,
      ...config
    };
    this.diagnosticsExpanded = Boolean(config.diagnostics_expanded_by_default);
  }

  public getCardSize(): number {
    let size = 2;
    if (this.config?.show_costs !== false) size += 2;
    if (this.config?.show_producers !== false) size += 1;
    if (this.config?.show_diagnostics !== false && this.diagnosticsExpanded) size += 2;
    return size;
  }

  private resolvePrimaryEntity(): string {
    const configured = this.config?.entity || '';
    const states = this.hass?.states || {};
    if (configured && states[configured]) {
      return configured;
    }
    const discovered = Object.keys(states).find((id) => {
      if (!id.startsWith('sensor.')) return false;
      return (
        states[id]?.attributes?.break_even_cop !== undefined ||
        id.endsWith('_economic_crossover_temperature')
      );
    });
    return discovered || configured;
  }

  private getCoordPrefix(): string {
    const entity = this.resolvePrimaryEntity();
    const suffix = '_economic_crossover_temperature';
    if (entity.endsWith(suffix)) {
      return entity.slice(0, -suffix.length);
    }
    const lastUnderscore = entity.lastIndexOf('_');
    return lastUnderscore > 0 ? entity.slice(0, lastUnderscore) : entity;
  }

  private getCostRateState(): any | null {
    const states = this.hass?.states || {};
    if (this.config?.cost_rate_entity && states[this.config.cost_rate_entity]) {
      return states[this.config.cost_rate_entity];
    }
    const byPrefix = `${this.getCoordPrefix()}_estimated_heating_cost_rate`;
    if (states[byPrefix]) {
      return states[byPrefix];
    }
    const fallback = Object.keys(states).find(
      (id) => id.startsWith('sensor.') && id.endsWith('_estimated_heating_cost_rate')
    );
    return fallback ? states[fallback] : null;
  }

  private getSavingsState(): any | null {
    const states = this.hass?.states || {};
    if (this.config?.savings_entity && states[this.config.savings_entity]) {
      return states[this.config.savings_entity];
    }
    const byPrefix = `${this.getCoordPrefix()}_estimated_savings_vs_fossil_fuel`;
    if (states[byPrefix]) {
      return states[byPrefix];
    }
    const fallback = Object.keys(states).find(
      (id) => id.startsWith('sensor.') && id.endsWith('_estimated_savings_vs_fossil_fuel')
    );
    return fallback ? states[fallback] : null;
  }

  private getProducerStates(): Array<{ entityId: string; stateObj: any }> {
    const explicit = this.config?.producer_entities;
    if (Array.isArray(explicit) && explicit.length > 0) {
      return explicit
        .map((entityId) => ({ entityId, stateObj: this.hass?.states?.[entityId] }))
        .filter((item) => Boolean(item.stateObj));
    }

    const prefix = `${this.getCoordPrefix()}_`;
    const states = this.hass?.states || {};
    const results: Array<{ entityId: string; stateObj: any }> = [];
    for (const [entityId, stateObj] of Object.entries(states)) {
      if (!entityId.startsWith(prefix)) continue;
      const attrs = stateObj?.attributes || {};
      const isProducer =
        attrs.current_cop !== undefined ||
        attrs.fuel_type !== undefined ||
        attrs.nominal_capacity_btu !== undefined;
      if (isProducer) {
        results.push({ entityId, stateObj });
      }
    }
    return results;
  }

  private formatCurrency(val: any, decimals = 2): string {
    const num = Number(val);
    if (val === null || val === undefined || Number.isNaN(num)) {
      return '—';
    }
    const abs = Math.abs(num).toFixed(decimals);
    return num < 0 ? `-$${abs}` : `$${abs}`;
  }

  private formatRate(val: any): string {
    const formatted = this.formatCurrency(val, 2);
    return formatted === '—' ? '—' : `${formatted}/h`;
  }

  private shouldShowAttribute(attrKey: string): boolean {
    const list = this.config.diagnostic_attributes || DEFAULT_SYSTEM_DIAGNOSTICS;
    return list.includes(attrKey);
  }

  static styles = css`
    :host {
      display: block;
    }

    ha-card {
      padding: 16px;
      border-radius: var(--ha-card-border-radius, 12px);
      background: var(--ha-card-background, var(--card-background-color, #1e293b));
      color: var(--primary-text-color, #f8fafc);
      font-family: var(--paper-font-body1_-_font-family, system-ui, -apple-system, sans-serif);
    }

    /* Header */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .card-title {
      font-size: 1.05rem;
      font-weight: 700;
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .header-pills {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 6px;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 0.74rem;
      font-weight: 600;
      white-space: nowrap;
    }

    .badge-auto {
      background: rgba(52, 211, 153, 0.14);
      color: #34d399;
      border: 1px solid rgba(52, 211, 153, 0.35);
    }

    .badge-dry {
      background: rgba(251, 191, 36, 0.14);
      color: #fbbf24;
      border: 1px solid rgba(251, 191, 36, 0.35);
    }

    .badge-advisory {
      background: rgba(129, 140, 248, 0.14);
      color: #a5b4fc;
      border: 1px solid rgba(129, 140, 248, 0.35);
    }

    .badge-xover {
      background: rgba(56, 189, 248, 0.14);
      color: #7dd3fc;
      border: 1px solid rgba(56, 189, 248, 0.32);
    }

    .badge-load {
      background: rgba(255, 255, 255, 0.06);
      color: var(--primary-text-color, #e2e8f0);
      border: 1px solid rgba(255, 255, 255, 0.12);
    }

    /* Section Containers */
    .section-box {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--divider-color, rgba(255, 255, 255, 0.08));
      border-radius: 10px;
      padding: 10px 12px;
      margin-bottom: 12px;
    }

    .section-heading {
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--secondary-text-color, #94a3b8);
      margin-bottom: 8px;
    }

    /* Section 1: Costs & Savings */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 8px;
    }

    @media (max-width: 520px) {
      .kpi-grid {
        grid-template-columns: 1fr;
      }
    }

    .kpi-tile {
      display: grid;
      grid-template-rows: 1fr auto auto;
      align-items: center;
      background: rgba(15, 23, 42, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 8px;
      padding: 8px 10px;
      text-align: center;
    }

    .kpi-label {
      font-size: 0.7rem;
      font-weight: 600;
      color: var(--secondary-text-color, #94a3b8);
      margin-bottom: 2px;
    }

    .kpi-value {
      font-size: 1.25rem;
      font-weight: 700;
      line-height: 1.2;
      color: var(--primary-text-color, #f8fafc);
    }

    .kpi-value.positive {
      color: #34d399;
    }

    .kpi-value.negative {
      color: #f87171;
    }

    .kpi-sub {
      font-size: 0.7rem;
      color: var(--secondary-text-color, #94a3b8);
      margin-top: 2px;
    }

    /* Section 2: Producers (3-across 2-line pills) */
    .producer-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 8px;
    }

    .producer-pill {
      background: rgba(15, 23, 42, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: 8px;
      padding: 6px 10px;
      min-width: 0;
    }

    .producer-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
      font-size: 0.78rem;
      font-weight: 600;
      margin-bottom: 2px;
    }

    .producer-name {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .producer-state {
      font-size: 0.72rem;
      font-weight: 700;
      white-space: nowrap;
    }

    .state-heating {
      color: #fb923c;
    }

    .state-cooling {
      color: #38bdf8;
    }

    .state-idle {
      color: #94a3b8;
    }

    .state-locked {
      color: #f87171;
    }

    .producer-sub {
      font-size: 0.7rem;
      color: var(--secondary-text-color, #94a3b8);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Section 3: Diagnostics Pills */
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
      padding-top: 8px;
      animation: fadeIn 0.15s ease-in-out;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .diag-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .diag-pill {
      display: inline-flex;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 4px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 6px;
      padding: 4px 9px;
      font-size: 0.76rem;
      line-height: 1.3;
      max-width: 100%;
      box-sizing: border-box;
    }

    .diag-label {
      color: var(--secondary-text-color, #94a3b8);
      font-weight: 500;
    }

    .diag-value {
      font-weight: 600;
      color: var(--primary-text-color, #f1f5f9);
      word-break: break-word;
    }
  `;

  private renderProducerCard(entityId: string, stateObj: any) {
    const attrs = stateObj.attributes || {};
    const rawName = attrs.friendly_name || entityId.split('.').pop() || entityId;
    const stateStr = String(stateObj.state || 'unknown').toLowerCase();
    const stateLabel = stateStr.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

    let stateClass = 'state-idle';
    let icon = '⏸️';
    if (stateStr === 'heating') {
      stateClass = 'state-heating';
      icon = '🔥';
    } else if (stateStr === 'cooling') {
      stateClass = 'state-cooling';
      icon = '❄️';
    } else if (stateStr === 'locked_out') {
      stateClass = 'state-locked';
      icon = '🔒';
    }

    const parts: string[] = [];
    if (attrs.current_cop !== undefined && attrs.current_cop !== null) {
      parts.push(`COP ${Number(attrs.current_cop).toFixed(2)}`);
      if (attrs.mode_lock) {
        parts.push(`Mode: ${attrs.mode_lock}`);
      }
    } else {
      if (attrs.estimated_return_temp_f !== undefined && attrs.estimated_return_temp_f !== null) {
        parts.push(`Return ${attrs.estimated_return_temp_f}°F`);
      }
      if (attrs.estimated_efficiency !== undefined && attrs.estimated_efficiency !== null) {
        parts.push(`${Math.round(Number(attrs.estimated_efficiency) * 100)}%`);
      } else if (attrs.rated_afue !== undefined && attrs.rated_afue !== null) {
        parts.push(`AFUE ${Math.round(Number(attrs.rated_afue) * 100)}%`);
      }
      if (attrs.condensing_state) {
        parts.push(String(attrs.condensing_state).replace(/_/g, ' '));
      }
    }

    const subText = parts.length > 0 ? parts.join(' • ') : 'Standby';

    return html`
      <div class="producer-pill" title="${rawName}: ${stateLabel} (${subText})">
        <div class="producer-top">
          <span class="producer-name">${icon} ${rawName}</span>
          <span class="producer-state ${stateClass}">${stateLabel}</span>
        </div>
        <div class="producer-sub">${subText}</div>
      </div>
    `;
  }

  private renderDiagnosticPills(xoverAttrs: Record<string, any>, rateAttrs: Record<string, any>, savingsAttrs: Record<string, any>) {
    const pills = [];
    const pill = (label: string, value: string, color?: string) => html`
      <div class="diag-pill" title="${label}: ${value}">
        <span class="diag-label">${label}:</span>
        <span class="diag-value" style="${color ? `color: ${color};` : ''}">${value}</span>
      </div>
    `;

    if (this.shouldShowAttribute('system_phase')) {
      const rawPhase = xoverAttrs.system_phase || 'unknown';
      const label = String(rawPhase).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
      pills.push(pill('System Phase', label));
    }

    if (this.shouldShowAttribute('break_even_cop')) {
      const cop = xoverAttrs.break_even_cop;
      pills.push(
        pill('Break-Even COP', typeof cop === 'number' ? cop.toFixed(2) : 'N/A')
      );
    }

    if (this.shouldShowAttribute('control_enabled')) {
      const ctrl = xoverAttrs.control_enabled;
      const advisoryOnly = xoverAttrs.advisory_only === true;
      const label =
        ctrl === false
          ? 'Dry Run'
          : advisoryOnly
            ? 'Advisory'
            : ctrl === true
              ? 'Enabled'
              : 'Unknown';
      const color =
        ctrl === false
          ? '#fbbf24'
          : advisoryOnly
            ? '#a5b4fc'
            : ctrl === true
              ? '#34d399'
              : '#94a3b8';
      pills.push(pill('Control', label, color));
    }

    if (this.shouldShowAttribute('heat_pump') && xoverAttrs.heat_pump) {
      pills.push(pill('Heat Pump', String(xoverAttrs.heat_pump)));
    }

    if (this.shouldShowAttribute('auxiliary_producer') && xoverAttrs.auxiliary_producer) {
      pills.push(pill('Auxiliary', String(xoverAttrs.auxiliary_producer)));
    }

    if (this.shouldShowAttribute('cumulative_estimated_cost')) {
      const cum = savingsAttrs.cumulative_estimated_cost ?? rateAttrs.cumulative_estimated_cost;
      if (cum !== undefined && cum !== null) {
        pills.push(pill('Cumulative Cost', this.formatCurrency(cum, 2)));
      }
    }

    return pills;
  }

  render() {
    if (!this.config?.entity || !this.hass) {
      return html`
        <ha-card>
          <div style="padding: 16px; color: #f87171;">
            Please configure an HVAC Fusion economic crossover sensor entity.
          </div>
        </ha-card>
      `;
    }

    const primaryEntityId = this.resolvePrimaryEntity();
    const xoverState = this.hass.states[primaryEntityId];
    const xoverAttrs = xoverState?.attributes || {};
    const title = this.config.title || 'HVAC Fusion';
    const advisoryOnly = xoverAttrs.advisory_only === true;
    const ctrl = xoverAttrs.control_enabled;
    const controlBadgeText = advisoryOnly
      ? 'Advisory'
      : ctrl === true
        ? 'Autonomous'
        : ctrl === false
          ? 'Dry Run'
          : 'Unknown';
    const controlBadgeClass = advisoryOnly
      ? 'badge-advisory'
      : ctrl === true
        ? 'badge-auto'
        : ctrl === false
          ? 'badge-dry'
          : 'badge-load';

    const xoverTemp = Number(xoverState?.state);
    const xoverText =
      xoverState && !Number.isNaN(xoverTemp) ? `${xoverTemp.toFixed(1)} °F` : 'N/A';
    const copStar =
      typeof xoverAttrs.break_even_cop === 'number'
        ? ` (COP* ${xoverAttrs.break_even_cop.toFixed(2)})`
        : '';

    const rateState = this.getCostRateState();
    const rateAttrs = rateState?.attributes || {};
    const savingsState = this.getSavingsState();
    const savingsAttrs = savingsState?.attributes || {};

    const hasCostData = Boolean(rateState || savingsState);
    const heatLossBtu = rateAttrs.total_heat_loss_btu_per_hr;
    const producers = this.config.show_producers !== false ? this.getProducerStates() : [];

    const fossilSavedTotal = savingsAttrs.savings_vs_fossil_fuel_total ?? savingsState?.state;
    const hpSavedTotal = savingsAttrs.savings_vs_heat_pump_total;
    const fossilSavedHr = rateAttrs.savings_vs_fossil_fuel_per_hr ?? savingsAttrs.savings_vs_fossil_fuel_per_hr;
    const hpSavedHr = rateAttrs.savings_vs_heat_pump_per_hr ?? savingsAttrs.savings_vs_heat_pump_per_hr;

    const fossilNum = Number(fossilSavedHr);
    const hpNum = Number(hpSavedHr);

    const formatSavingsPct = (savedVal: any, baselineVal: any): string => {
      const saved = Number(savedVal);
      const base = Number(baselineVal);
      if (
        savedVal === undefined ||
        savedVal === null ||
        baselineVal === undefined ||
        baselineVal === null ||
        Number.isNaN(saved) ||
        Number.isNaN(base) ||
        base <= 0
      ) {
        return '—';
      }
      const pct = (saved / base) * 100;
      if (Math.abs(pct) < 0.5) return 'Even';
      return pct > 0 ? `${Math.round(pct)}% cheaper` : `${Math.round(Math.abs(pct))}% more`;
    };

    return html`
      <ha-card>
        <!-- Header -->
        <div class="header">
          <div class="title-group">
            <h2 class="card-title">${title}</h2>
            <span class="status-badge ${controlBadgeClass}">
              ${controlBadgeText}
            </span>
          </div>

          <div class="header-pills">
            <span class="status-badge badge-xover" title="Economic Crossover Temperature & Break-Even COP">
              ⚖️ Crossover: ${xoverText}${copStar}
            </span>
            ${typeof heatLossBtu === 'number'
              ? html`
                  <span class="status-badge badge-load" title="Estimated Space Envelope Heat Loss">
                    🔥 Load: ${Math.round(heatLossBtu).toLocaleString()} BTU/h
                  </span>
                `
              : ''}
          </div>
        </div>

        <!-- Section 1: Costs & Savings -->
        ${this.config.show_costs !== false && hasCostData
          ? html`
              <div class="section-box">
                <div class="section-heading">Costs & Savings</div>
                <div class="kpi-grid">
                  <div class="kpi-tile">
                    <div class="kpi-label">Current Rate</div>
                    <div class="kpi-value">${this.formatRate(rateState?.state)}</div>
                    <div class="kpi-sub">Optimized</div>
                  </div>
                  <div class="kpi-tile">
                    <div class="kpi-label">Saving vs Fossil Fuel</div>
                    <div class="kpi-value ${!Number.isNaN(fossilNum) ? (fossilNum > 0 ? 'positive' : fossilNum < 0 ? 'negative' : '') : ''}">
                      ${this.formatRate(fossilSavedHr)}
                    </div>
                    <div class="kpi-sub">${formatSavingsPct(fossilSavedHr, rateAttrs.fossil_fuel_baseline_cost_per_hr)}</div>
                  </div>
                  <div class="kpi-tile">
                    <div class="kpi-label">Saving vs Heat Pump</div>
                    <div class="kpi-value ${!Number.isNaN(hpNum) ? (hpNum > 0 ? 'positive' : hpNum < 0 ? 'negative' : '') : ''}">
                      ${this.formatRate(hpSavedHr)}
                    </div>
                    <div class="kpi-sub">${formatSavingsPct(hpSavedHr, rateAttrs.heat_pump_baseline_cost_per_hr)}</div>
                  </div>
                </div>
                <div class="diag-pills">
                  <div class="diag-pill">
                    <span class="diag-label">Optimized:</span>
                    <span class="diag-value">${this.formatRate(rateState?.state)}</span>
                  </div>
                  <div class="diag-pill">
                    <span class="diag-label">Fossil Fuel:</span>
                    <span class="diag-value">${this.formatRate(rateAttrs.fossil_fuel_baseline_cost_per_hr)}</span>
                  </div>
                  <div class="diag-pill">
                    <span class="diag-label">Heat Pump:</span>
                    <span class="diag-value">${this.formatRate(rateAttrs.heat_pump_baseline_cost_per_hr)}</span>
                  </div>
                </div>
              </div>
            `
          : ''}

        <!-- Section 2: Producers -->
        ${this.config.show_producers !== false && producers.length > 0
          ? html`
              <div class="section-box">
                <div class="section-heading">Producers</div>
                <div class="producer-grid">
                  ${producers.map((p) => this.renderProducerCard(p.entityId, p.stateObj))}
                </div>
              </div>
            `
          : ''}

        <!-- Section 3: Expandable System Details & Diagnostics -->
        ${this.config.show_diagnostics !== false
          ? html`
              <div class="diagnostics-section">
                <button
                  class="diagnostics-toggle-btn"
                  @click=${() => (this.diagnosticsExpanded = !this.diagnosticsExpanded)}
                >
                  <span>ℹ️ System Details & Diagnostics</span>
                  <span>${this.diagnosticsExpanded ? '▲ Hide' : '▼ Show'}</span>
                </button>

                ${this.diagnosticsExpanded
                  ? html`
                      <div class="diagnostics-drawer">
                        <div class="diag-pills">
                          ${this.renderDiagnosticPills(xoverAttrs, rateAttrs, savingsAttrs)}
                        </div>
                      </div>
                    `
                  : ''}
              </div>
            `
          : ''}
      </ha-card>
    `;
  }
}

if (!customElements.get('hvac-fusion-system-card')) {
  customElements.define('hvac-fusion-system-card', HvacFusionSystemCard);
}
