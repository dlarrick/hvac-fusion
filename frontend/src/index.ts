/**
 * HVAC Fusion Lovelace Card Suite
 *
 * Bundles:
 * 1. schedule-preset-card: 7-day interactive schedule calendar editor
 * 2. hvac-fusion-status-card: Unified space status card (24h schedule, comfort bump, diagnostics)
 *    (aliases legacy custom:climate-preset-timeline)
 */

import './schedule-preset-card';
import './hvac-fusion-status-card';

export * from './types';

// Custom card registrations and suggestions for Home Assistant card picker
(window as any).customCards = (window as any).customCards || [];

// 1. Standalone Status Card
(window as any).customCards.push({
  type: 'hvac-fusion-status-card',
  name: 'HVAC Fusion Status Card',
  description:
    'Unified space status card with 24-hour preset schedule, temporary comfort bump, and room diagnostics.',
  preview: true,
  getEntitySuggestion: (hass: any, entityId: string) => {
    const state = hass?.states?.[entityId];
    if (!entityId.startsWith('climate.') || state?.attributes?.current_boost === undefined) {
      return null;
    }
    return {
      config: {
        type: 'custom:hvac-fusion-status-card',
        entity: entityId
      }
    };
  }
});

// 2. 2-Card Stack Suggestion: Native Tile + HVAC Fusion Status Card
(window as any).customCards.push({
  type: 'hvac-fusion-space-stack',
  name: 'HVAC Fusion Space Stack (Tile + Status)',
  description:
    'Pre-configured 2-card vertical stack: Native Tile Card (thermostat & presets) + HVAC Fusion Status Card.',
  preview: true,
  getEntitySuggestion: (hass: any, entityId: string) => {
    const state = hass?.states?.[entityId];
    if (!entityId.startsWith('climate.') || state?.attributes?.current_boost === undefined) {
      return null;
    }
    return {
      config: {
        type: 'vertical-stack',
        cards: [
          {
            type: 'tile',
            entity: entityId,
            features: [
              {
                type: 'climate-preset-modes',
                style: 'dropdown'
              }
            ]
          },
          {
            type: 'custom:hvac-fusion-status-card',
            entity: entityId
          }
        ]
      }
    };
  }
});
