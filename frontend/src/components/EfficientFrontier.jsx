import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceDot,
} from 'recharts';
import { useEfficientFrontier } from '../hooks/useStrategyData';
import { formatLambda } from '../utils/formatters';

export default function EfficientFrontier({ params, setParams, calibration }) {
  const frontierMutation = useEfficientFrontier();
  const [frontierData, setFrontierData] = useState([]);

  useEffect(() => {
    if (calibration) {
      frontierMutation.mutate(
        { X: params.X, T: params.T, N: params.N, n_points: 50 },
        {
          onSuccess: (data) => {
            if (data.frontier) {
              setFrontierData(
                data.frontier.map((p) => ({
                  x: p.Std_IS_bps,
                  y: p.E_IS_bps,
                  lambda: p.lambda,
                }))
              );
            }
          },
        }
      );
    }
  }, [calibration, params.X, params.T, params.N]);

  // Find current lambda position on curve
  const currentPoint = frontierData.reduce(
    (closest, point) =>
      Math.abs(Math.log10(point.lambda) - Math.log10(params.lambda_risk)) <
      Math.abs(Math.log10(closest.lambda) - Math.log10(params.lambda_risk))
        ? point
        : closest,
    frontierData[0] || { x: 0, y: 0, lambda: 1e-6 }
  );

  const handleClick = (data) => {
    if (data && data.activePayload && data.activePayload[0]) {
      const point = data.activePayload[0].payload;
      setParams({ ...params, lambda_risk: point.lambda });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-card border border-border rounded-xl p-5 h-full"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-text-secondary">
          AC Efficient Frontier (E[IS] vs Std[IS])
        </h3>
        {currentPoint && (
          <span className="text-xs text-accent-gold font-mono">
            lambda = {formatLambda(currentPoint.lambda)}
          </span>
        )}
      </div>

      <div className="h-96">
        {frontierData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart onClick={handleClick}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A2535" />
              <XAxis
                dataKey="x"
                type="number"
                stroke="#8B9CB6"
                fontSize={11}
                name="Std[IS] (bps)"
                label={{ value: 'Std[IS] (bps)', position: 'insideBottom', offset: -5, fill: '#8B9CB6' }}
              />
              <YAxis
                dataKey="y"
                type="number"
                stroke="#8B9CB6"
                fontSize={11}
                name="E[IS] (bps)"
                label={{ value: 'E[IS] (bps)', angle: -90, position: 'insideLeft', fill: '#8B9CB6' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0D1320',
                  border: '1px solid #1A2535',
                  borderRadius: '8px',
                  color: '#E8ECF0',
                  fontSize: 12,
                }}
                formatter={(value, name) => [
                  typeof value === 'number' ? value.toFixed(2) : value,
                  name,
                ]}
              />
              <Scatter
                data={frontierData}
                fill="#C9A84C"
                fillOpacity={0.6}
                r={3}
                cursor="pointer"
              />
              {currentPoint && (
                <ReferenceDot
                  x={currentPoint.x}
                  y={currentPoint.y}
                  r={8}
                  fill="#C9A84C"
                  stroke="#E8ECF0"
                  strokeWidth={2}
                />
              )}
            </ScatterChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-text-secondary text-sm">
            {frontierMutation.isPending ? (
              <div className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4 text-accent-gold" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Computing frontier...
              </div>
            ) : (
              'Calibrate first to see the efficient frontier'
            )}
          </div>
        )}
      </div>

      <div className="flex justify-between text-xs text-text-secondary mt-2">
        <span>Low Risk (high cost)</span>
        <span>High Risk (low cost)</span>
      </div>
    </motion.div>
  );
}
