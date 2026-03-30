import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useSensitivity } from '../hooks/useStrategyData';
import { formatLambda } from '../utils/formatters';

const T_VALUES = [5, 10, 15, 20, 30, 45, 60];
const LAMBDA_VALUES = [1e-8, 1e-7, 1e-6, 1e-5, 1e-4];

function getHeatColor(value, min, max) {
  if (min === max) return '#4CAF8C';
  const ratio = (value - min) / (max - min);
  // Green (low IS) to Red (high IS)
  const r = Math.round(76 + ratio * (224 - 76));
  const g = Math.round(175 - ratio * (175 - 92));
  const b = Math.round(140 - ratio * (140 - 92));
  return `rgb(${r}, ${g}, ${b})`;
}

export default function SensitivityHeatmap({ params, calibration }) {
  const sensitivityMutation = useSensitivity();
  const [heatmapData, setHeatmapData] = useState(null);

  useEffect(() => {
    if (calibration) {
      sensitivityMutation.mutate(
        {
          X: params.X,
          N: params.N,
          lambda_risk: params.lambda_risk,
          T_values: T_VALUES,
          lambda_values: LAMBDA_VALUES,
        },
        {
          onSuccess: (data) => setHeatmapData(data),
        }
      );
    }
  }, [calibration]);

  // Compute min/max for colour scaling
  let allValues = [];
  if (heatmapData?.heatmap) {
    Object.values(heatmapData.heatmap).forEach((row) => {
      Object.values(row).forEach((v) => allValues.push(v));
    });
  }
  const minVal = allValues.length > 0 ? Math.min(...allValues) : 0;
  const maxVal = allValues.length > 0 ? Math.max(...allValues) : 1;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-bg-card border border-border rounded-xl p-5"
    >
      <h3 className="text-sm font-medium text-text-secondary mb-4">
        Sensitivity Heatmap: IS (bps) by T and lambda
      </h3>

      {heatmapData?.heatmap ? (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="text-xs text-text-secondary p-1.5">T \ lambda</th>
                {LAMBDA_VALUES.map((lam) => (
                  <th key={lam} className="text-xs text-text-secondary p-1.5 font-mono">
                    {formatLambda(lam)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {T_VALUES.map((T) => (
                <tr key={T}>
                  <td className="text-xs text-text-secondary p-1.5 font-mono">{T} min</td>
                  {LAMBDA_VALUES.map((lam) => {
                    const val = heatmapData.heatmap[String(T)]?.[String(lam)] ?? 0;
                    return (
                      <td
                        key={lam}
                        className="p-1.5 text-center text-xs font-mono cursor-pointer hover:ring-1 hover:ring-accent-gold rounded transition"
                        style={{
                          backgroundColor: getHeatColor(val, minVal, maxVal) + '30',
                          color: getHeatColor(val, minVal, maxVal),
                        }}
                        title={`T=${T}, lambda=${formatLambda(lam)}: ${val.toFixed(2)} bps`}
                      >
                        {val.toFixed(1)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-48 flex items-center justify-center text-text-secondary text-sm">
          {sensitivityMutation.isPending ? 'Computing heatmap...' : 'Calibrate first to see sensitivity'}
        </div>
      )}
    </motion.div>
  );
}
