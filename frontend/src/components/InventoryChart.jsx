import React from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { STRATEGY_COLORS, STRATEGY_NAMES } from '../utils/formatters';

export default function InventoryChart({ results, params }) {
  if (!results) {
    return (
      <div className="bg-bg-card border border-border rounded-xl p-5">
        <h3 className="text-sm font-medium text-text-secondary mb-4">Inventory Trajectory</h3>
        <div className="h-64 flex items-center justify-center text-text-secondary text-sm">
          Run a strategy to see inventory trajectories
        </div>
      </div>
    );
  }

  // Build combined chart data
  const strategies = Object.keys(results);
  const maxLen = Math.max(
    ...strategies.map((s) => (results[s]?.inventory?.length || 0))
  );

  const chartData = [];
  for (let i = 0; i < maxLen; i++) {
    const point = { step: i };
    for (const strat of strategies) {
      const inv = results[strat]?.inventory;
      if (inv && i < inv.length) {
        point[strat] = inv[i];
      }
    }
    chartData.push(point);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-card border border-border rounded-xl p-5"
    >
      <h3 className="text-sm font-medium text-text-secondary mb-4">Inventory Trajectory</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A2535" />
            <XAxis dataKey="step" stroke="#8B9CB6" fontSize={11} />
            <YAxis stroke="#8B9CB6" fontSize={11} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0D1320',
                border: '1px solid #1A2535',
                borderRadius: '8px',
                color: '#E8ECF0',
                fontSize: 12,
              }}
            />
            <Legend />
            {strategies.map((strat) => (
              <Line
                key={strat}
                type="monotone"
                dataKey={strat}
                name={STRATEGY_NAMES[strat] || strat.toUpperCase()}
                stroke={STRATEGY_COLORS[strat] || '#8B9CB6'}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
