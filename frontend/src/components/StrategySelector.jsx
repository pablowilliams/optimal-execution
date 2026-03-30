import React from 'react';
import { STRATEGY_COLORS, STRATEGY_NAMES } from '../utils/formatters';

const STRATEGIES = ['ac', 'ow', 'ppo', 'twap'];

export default function StrategySelector({ selected, onChange }) {
  const toggle = (strat) => {
    if (selected.includes(strat)) {
      if (selected.length > 1) {
        onChange(selected.filter((s) => s !== strat));
      }
    } else {
      onChange([...selected, strat]);
    }
  };

  return (
    <div className="space-y-2">
      <span className="text-sm text-text-secondary">Strategy Selection</span>
      <div className="flex flex-wrap gap-2">
        {STRATEGIES.map((strat) => (
          <button
            key={strat}
            onClick={() => toggle(strat)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-all ${
              selected.includes(strat)
                ? 'border-accent-gold bg-accent-gold/10 text-accent-gold'
                : 'border-border bg-bg-root text-text-secondary hover:border-text-secondary'
            }`}
          >
            <span
              className="inline-block w-2 h-2 rounded-full mr-1.5"
              style={{ backgroundColor: STRATEGY_COLORS[strat] }}
            />
            {strat.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}
