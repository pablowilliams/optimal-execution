import React from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { STRATEGY_NAMES } from '../utils/formatters';

export default function CostBreakdown({ results, params }) {
  if (!results) {
    return (
      <div className="bg-bg-card border border-border rounded-xl p-5">
        <h3 className="text-sm font-medium text-text-secondary mb-4">Cost Breakdown</h3>
        <div className="h-64 flex items-center justify-center text-text-secondary text-sm">
          Run a strategy to see cost breakdown
        </div>
      </div>
    );
  }

  const chartData = Object.entries(results).map(([strat, data]) => {
    const metrics = data?.simulated_metrics?.metrics || {};
    return {
      name: STRATEGY_NAMES[strat] || strat.toUpperCase(),
      'Perm Impact': Math.abs(metrics.perm_impact_bps || 0),
      'Temp Impact': Math.abs(metrics.temp_impact_bps || 0),
      'Timing Risk': Math.abs((metrics.IS_bps || 0) - (metrics.perm_impact_bps || 0) - (metrics.temp_impact_bps || 0)),
    };
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-card border border-border rounded-xl p-5"
    >
      <h3 className="text-sm font-medium text-text-secondary mb-4">
        Cost Breakdown (bps)
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="horizontal">
            <CartesianGrid strokeDasharray="3 3" stroke="#1A2535" />
            <XAxis dataKey="name" stroke="#8B9CB6" fontSize={10} />
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
            <Bar dataKey="Perm Impact" stackId="a" fill="#C9A84C" />
            <Bar dataKey="Temp Impact" stackId="a" fill="#4C7AE0" />
            <Bar dataKey="Timing Risk" stackId="a" fill="#4CAF8C" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
