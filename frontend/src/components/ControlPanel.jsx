import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useCalibrate, useRunStrategy, useTrainRL } from '../hooks/useStrategyData';
import { formatScientific, formatLambda } from '../utils/formatters';
import StrategySelector from './StrategySelector';

export default function ControlPanel({ params, setParams, calibration, setCalibration, onResults, health }) {
  const calibrateMutation = useCalibrate();
  const runMutation = useRunStrategy();
  const trainMutation = useTrainRL();
  const [trainingJobId, setTrainingJobId] = useState(null);

  const handleCalibrate = async () => {
    const result = await calibrateMutation.mutateAsync(true);
    setCalibration(result);
  };

  const handleRun = async () => {
    const result = await runMutation.mutateAsync({
      strategy: params.strategies.length === 1 ? params.strategies[0] : 'all',
      X: params.X,
      T: params.T,
      N: params.N,
      lambda_risk: params.lambda_risk,
      cost_bps: params.cost_bps,
    });
    onResults(result);
  };

  const handleTrain = async () => {
    const result = await trainMutation.mutateAsync({
      total_timesteps: 500000,
      X: params.X,
      T: params.T,
      N: params.N,
      lambda_risk: params.lambda_risk,
    });
    setTrainingJobId(result.job_id);
  };

  const lambdaLog = Math.log10(params.lambda_risk);

  return (
    <div className="bg-bg-card border border-border rounded-xl p-5 space-y-5 h-fit">
      <h2 className="text-lg font-semibold text-accent-gold">Parameters</h2>

      {/* Inventory X */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Inventory X (shares)</span>
          <span className="text-text-primary font-mono">{params.X.toLocaleString()}</span>
        </div>
        <input
          type="range"
          min={1000}
          max={1000000}
          step={1000}
          value={params.X}
          onChange={(e) => setParams({ ...params, X: Number(e.target.value) })}
          className="w-full"
        />
      </div>

      {/* Time horizon T */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Time horizon T (min)</span>
          <span className="text-text-primary font-mono">{params.T}</span>
        </div>
        <input
          type="range"
          min={1}
          max={390}
          step={1}
          value={params.T}
          onChange={(e) => setParams({ ...params, T: Number(e.target.value) })}
          className="w-full"
        />
      </div>

      {/* Time steps N */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Time steps N</span>
          <span className="text-text-primary font-mono">{params.N}</span>
        </div>
        <input
          type="range"
          min={5}
          max={100}
          step={1}
          value={params.N}
          onChange={(e) => setParams({ ...params, N: Number(e.target.value) })}
          className="w-full"
        />
      </div>

      {/* Risk aversion lambda */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Risk aversion lambda</span>
          <span className="text-text-primary font-mono">{formatLambda(params.lambda_risk)}</span>
        </div>
        <input
          type="range"
          min={-8}
          max={-4}
          step={0.1}
          value={lambdaLog}
          onChange={(e) =>
            setParams({ ...params, lambda_risk: Math.pow(10, Number(e.target.value)) })
          }
          className="w-full"
        />
      </div>

      {/* Transaction cost */}
      <div className="space-y-1">
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Cost (bps)</span>
          <span className="text-text-primary font-mono">{params.cost_bps}</span>
        </div>
        <input
          type="number"
          min={0}
          max={50}
          value={params.cost_bps}
          onChange={(e) => setParams({ ...params, cost_bps: Number(e.target.value) })}
          className="w-full bg-bg-input border border-border rounded px-3 py-1.5 text-sm text-text-primary"
        />
      </div>

      {/* Strategy selection */}
      <StrategySelector
        selected={params.strategies}
        onChange={(strategies) => setParams({ ...params, strategies })}
      />

      {/* Calibration status */}
      <div className="bg-bg-root rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">Calibration</span>
          <button
            onClick={handleCalibrate}
            disabled={calibrateMutation.isPending}
            className="text-xs text-accent-gold hover:text-accent-gold/80 transition"
          >
            {calibrateMutation.isPending ? 'Running...' : 'Re-Calibrate'}
          </button>
        </div>
        {calibration && (
          <div className="grid grid-cols-2 gap-1 text-xs font-mono">
            <span className="text-text-secondary">eta</span>
            <span>{calibration.eta?.toFixed(4)}</span>
            <span className="text-text-secondary">gamma</span>
            <span>{calibration.gamma?.toFixed(4)}</span>
            <span className="text-text-secondary">rho</span>
            <span>{calibration.rho?.toFixed(1)}</span>
            <span className="text-text-secondary">sigma</span>
            <span>{calibration.sigma?.toFixed(4)}</span>
          </div>
        )}
      </div>

      {/* PPO Status */}
      <div className="bg-bg-root rounded-lg p-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">RL Training</span>
          {health?.model_trained ? (
            <span className="text-xs px-2 py-0.5 rounded-full bg-accent-success/20 text-accent-success">
              Model Ready
            </span>
          ) : (
            <span className="text-xs px-2 py-0.5 rounded-full bg-accent-error/20 text-accent-error">
              Not Trained
            </span>
          )}
        </div>
        {!health?.model_trained && (
          <button
            onClick={handleTrain}
            disabled={trainMutation.isPending}
            className="w-full py-1.5 text-xs bg-accent-gold/20 text-accent-gold rounded hover:bg-accent-gold/30 transition"
          >
            {trainMutation.isPending ? 'Starting...' : 'Train PPO Agent'}
          </button>
        )}
      </div>

      {/* Run button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={handleRun}
        disabled={runMutation.isPending}
        className="w-full py-3 bg-accent-gold text-bg-root font-semibold rounded-lg hover:bg-accent-gold/90 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {runMutation.isPending ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Running...
          </span>
        ) : (
          'Run Analysis'
        )}
      </motion.button>
    </div>
  );
}
