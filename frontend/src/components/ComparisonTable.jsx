import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useCompare } from '../hooks/useStrategyData';
import { formatBps, formatPercent, STRATEGY_NAMES } from '../utils/formatters';

const COLUMNS = [
  { key: 'name', label: 'Strategy' },
  { key: 'mean_IS', label: 'E[IS] (bps)' },
  { key: 'std_IS', label: 'Std[IS] (bps)' },
  { key: 'sharpe_IS', label: 'Sharpe-of-IS' },
  { key: 'VWAP_slippage_bps', label: 'VWAP Slippage' },
  { key: 'x_remaining_pct', label: 'Max Inv Risk' },
  { key: 'vs_twap', label: '% vs TWAP' },
];

export default function ComparisonTable({ params, comparisonData, setComparisonData }) {
  const compareMutation = useCompare();
  const [nEpisodes, setNEpisodes] = useState(500);

  const handleCompare = async () => {
    const result = await compareMutation.mutateAsync({
      X: params.X,
      T: params.T,
      N: params.N,
      lambda_risk: params.lambda_risk,
      n_episodes: nEpisodes,
    });
    setComparisonData(result);
  };

  const strats = comparisonData?.strategies || {};
  const twapIS = strats.twap?.mean_IS || 1;

  const rows = ['ac', 'ow', 'ppo', 'twap', 'vwap']
    .filter((s) => s in strats)
    .map((s) => ({
      name: s.toUpperCase(),
      ...strats[s],
      vs_twap: ((twapIS - strats[s].mean_IS) / Math.abs(twapIS)) * 100,
    }));

  // Find best/worst per column for colouring
  const getBestWorst = (key) => {
    if (rows.length === 0) return { best: null, worst: null };
    const sorted = [...rows].sort((a, b) => a[key] - b[key]);
    return {
      best: key === 'sharpe_IS' || key === 'vs_twap'
        ? sorted[sorted.length - 1]?.name
        : sorted[0]?.name,
      worst: key === 'sharpe_IS' || key === 'vs_twap'
        ? sorted[0]?.name
        : sorted[sorted.length - 1]?.name,
    };
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-card border border-border rounded-xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-text-secondary">Strategy Comparison</h3>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <span>Episodes:</span>
            <input
              type="number"
              min={10}
              max={1000}
              value={nEpisodes}
              onChange={(e) => setNEpisodes(Number(e.target.value))}
              className="w-16 bg-bg-input border border-border rounded px-2 py-1 text-text-primary"
            />
          </div>
          <button
            onClick={handleCompare}
            disabled={compareMutation.isPending}
            className="px-4 py-1.5 bg-accent-gold text-bg-root text-sm font-medium rounded-md hover:bg-accent-gold/90 transition disabled:opacity-50"
          >
            {compareMutation.isPending ? 'Running...' : 'Compare All'}
          </button>
        </div>
      </div>

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className="py-2 px-3 text-left text-xs font-medium text-text-secondary"
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                return (
                  <tr key={row.name} className="border-b border-border/50 hover:bg-bg-root/50 transition">
                    <td className="py-2.5 px-3 font-medium text-accent-gold">{row.name}</td>
                    {['mean_IS', 'std_IS', 'sharpe_IS', 'VWAP_slippage_bps', 'x_remaining_pct', 'vs_twap'].map((key) => {
                      const { best, worst } = getBestWorst(key);
                      const isBest = row.name === best;
                      const isWorst = row.name === worst;
                      const val = row[key];
                      return (
                        <td
                          key={key}
                          className={`py-2.5 px-3 font-mono text-xs ${
                            isBest ? 'text-accent-success bg-accent-success/5' :
                            isWorst ? 'text-accent-error bg-accent-error/5' :
                            'text-text-primary'
                          }`}
                        >
                          {key === 'vs_twap'
                            ? `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`
                            : key === 'sharpe_IS'
                            ? val.toFixed(3)
                            : key === 'x_remaining_pct'
                            ? `${val.toFixed(1)}%`
                            : val.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-40 flex items-center justify-center text-text-secondary text-sm">
          {compareMutation.isPending ? (
            <div className="flex flex-col items-center gap-3">
              <svg className="animate-spin h-6 w-6 text-accent-gold" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span>Running {nEpisodes}-episode comparison...</span>
              <div className="w-48 h-2 bg-bg-root rounded-full overflow-hidden">
                <div className="h-full bg-accent-gold rounded-full animate-pulse" style={{ width: '60%' }} />
              </div>
            </div>
          ) : (
            'Click "Compare All" to run a full multi-episode comparison'
          )}
        </div>
      )}
    </motion.div>
  );
}
