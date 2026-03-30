import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { useSimulation } from '../hooks/useSimulation';
import { STRATEGY_COLORS, formatBps, formatShares } from '../utils/formatters';

const SPEEDS = [0.5, 1, 2, 5];

export default function SimulationPlayer({ params, calibration }) {
  const { trajectoryData, isPlaying, play, pause, reset, currentStep } = useSimulation();
  const [selectedStrategies, setSelectedStrategies] = useState(['ac']);
  const [speed, setSpeed] = useState(1);
  const [multiStratData, setMultiStratData] = useState({});

  const handlePlay = () => {
    const strat = selectedStrategies[0] || 'ac';
    play({
      strategy: strat,
      X: params.X,
      T: params.T,
      N: params.N,
      lambda_risk: params.lambda_risk,
    });
  };

  // Build chart data from trajectory
  const chartData = trajectoryData.map((d) => ({
    step: d.step,
    x_remaining: d.x_remaining,
    mid: d.mid,
    IS_cum: d.IS_cum,
  }));

  const latestStep = trajectoryData[trajectoryData.length - 1];

  return (
    <div className="bg-bg-card border border-border rounded-xl p-5 space-y-4">
      {/* Controls bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Strategy tabs */}
          {['ac', 'ow', 'ppo', 'twap'].map((s) => (
            <button
              key={s}
              onClick={() => setSelectedStrategies([s])}
              className={`px-3 py-1 text-xs rounded-md transition ${
                selectedStrategies.includes(s)
                  ? 'bg-accent-gold/20 text-accent-gold border border-accent-gold'
                  : 'text-text-secondary border border-border hover:border-text-secondary'
              }`}
            >
              {s.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {/* Speed selector */}
          <div className="flex items-center gap-1 text-xs text-text-secondary">
            {SPEEDS.map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`px-2 py-0.5 rounded ${
                  speed === s ? 'bg-accent-gold/20 text-accent-gold' : 'hover:text-text-primary'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
          {/* Play / Pause */}
          <button
            onClick={isPlaying ? pause : handlePlay}
            className="px-4 py-1.5 bg-accent-gold text-bg-root text-sm font-medium rounded-md hover:bg-accent-gold/90 transition"
          >
            {isPlaying ? 'Pause' : 'Play'}
          </button>
          <button
            onClick={reset}
            className="px-3 py-1.5 border border-border text-text-secondary text-sm rounded-md hover:border-text-secondary transition"
          >
            Reset
          </button>
        </div>
      </div>

      {/* Main chart */}
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1A2535" />
            <XAxis
              dataKey="step"
              stroke="#8B9CB6"
              fontSize={11}
              label={{ value: 'Time Step', position: 'insideBottom', offset: -5, fill: '#8B9CB6' }}
            />
            <YAxis
              stroke="#8B9CB6"
              fontSize={11}
              label={{ value: 'Shares Remaining', angle: -90, position: 'insideLeft', fill: '#8B9CB6' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0D1320',
                border: '1px solid #1A2535',
                borderRadius: '8px',
                color: '#E8ECF0',
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="x_remaining"
              stroke={STRATEGY_COLORS[selectedStrategies[0]] || '#C9A84C'}
              strokeWidth={2}
              dot={false}
              animationDuration={100}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Live metrics */}
      <AnimatePresence>
        {latestStep && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-4 gap-4"
          >
            <div className="bg-bg-root rounded-lg p-3 text-center">
              <div className="text-xs text-text-secondary">Shares Remaining</div>
              <div className="text-lg font-mono text-text-primary">
                {formatShares(latestStep.x_remaining)}
              </div>
            </div>
            <div className="bg-bg-root rounded-lg p-3 text-center">
              <div className="text-xs text-text-secondary">Cumulative IS</div>
              <div className="text-lg font-mono text-text-primary">
                {formatBps(latestStep.IS_cum / (params.X * (latestStep.mid || 100)) * 10000)}
              </div>
            </div>
            <div className="bg-bg-root rounded-lg p-3 text-center">
              <div className="text-xs text-text-secondary">Current Step</div>
              <div className="text-lg font-mono text-text-primary">{currentStep}</div>
            </div>
            <div className="bg-bg-root rounded-lg p-3 text-center">
              <div className="text-xs text-text-secondary">% Complete</div>
              <div className="text-lg font-mono text-accent-gold">
                {((currentStep / params.N) * 100).toFixed(0)}%
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
