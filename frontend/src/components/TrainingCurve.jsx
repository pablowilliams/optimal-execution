import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { useTrainingCurve } from '../hooks/useStrategyData';

export default function TrainingCurve({ health }) {
  const { data, refetch, isLoading } = useTrainingCurve();
  const [loaded, setLoaded] = useState(false);

  const handleLoad = () => {
    refetch().then(() => setLoaded(true));
  };

  const curveData = data?.curve || [];

  // Format timesteps as "100k", "500k"
  const formatTimestep = (value) => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(0)}k`;
    return value;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-card border border-border rounded-xl p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-text-secondary">PPO Training Curve</h3>
        {health?.model_trained && (
          <button
            onClick={handleLoad}
            className="text-xs text-accent-gold hover:text-accent-gold/80 transition"
          >
            {isLoading ? 'Loading...' : 'Load Curve'}
          </button>
        )}
      </div>

      <div className="h-64">
        {curveData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={curveData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A2535" />
              <XAxis
                dataKey="timestep"
                stroke="#8B9CB6"
                fontSize={11}
                tickFormatter={formatTimestep}
              />
              <YAxis stroke="#8B9CB6" fontSize={11} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0D1320',
                  border: '1px solid #1A2535',
                  borderRadius: '8px',
                  color: '#E8ECF0',
                  fontSize: 12,
                }}
                labelFormatter={formatTimestep}
              />
              <Line
                type="monotone"
                dataKey="mean_reward"
                stroke="#C9A84C"
                strokeWidth={2}
                dot={false}
                fill="#C9A84C"
                fillOpacity={0.1}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-text-secondary text-sm">
            {health?.model_trained
              ? 'Click "Load Curve" to view training history'
              : 'Train a PPO agent first to see the learning curve'}
          </div>
        )}
      </div>

      {curveData.length > 0 && (
        <div className="text-xs text-text-secondary mt-2 text-right">
          Total: {formatTimestep(curveData[curveData.length - 1]?.timestep || 0)} timesteps
        </div>
      )}
    </motion.div>
  );
}
