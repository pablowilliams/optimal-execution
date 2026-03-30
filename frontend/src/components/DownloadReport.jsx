import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { formatBps } from '../utils/formatters';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function DownloadReport({ params, calibration, comparisonData }) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [pdfUrl, setPdfUrl] = useState(null);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const response = await fetch(
        `${API_URL}/research-note?strategy=all&X=${params.X}&T=${params.T}`
      );
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);

      // Trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = 'research_note.pdf';
      a.click();
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setIsDownloading(false);
    }
  };

  const strats = comparisonData?.strategies || {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Metrics summary cards */}
      <div className="grid grid-cols-4 gap-4">
        {['ac', 'ow', 'ppo', 'twap'].map((s) => {
          const data = strats[s];
          return (
            <div key={s} className="bg-bg-card border border-border rounded-xl p-5 text-center">
              <div className="text-xs text-text-secondary mb-1">{s.toUpperCase()} IS</div>
              <div className="text-2xl font-bold text-accent-gold font-mono">
                {data ? `${data.mean_IS.toFixed(2)}` : '—'}
              </div>
              <div className="text-xs text-text-secondary">bps</div>
            </div>
          );
        })}
      </div>

      {/* Research narrative */}
      <div className="bg-bg-card border border-border rounded-xl p-6 space-y-4">
        <h3 className="text-lg font-semibold text-accent-gold">Research Narrative</h3>

        {calibration && (
          <div className="text-sm text-text-secondary leading-relaxed space-y-3">
            <p>
              <strong className="text-text-primary">Calibration:</strong> The model was calibrated
              with parameters eta={calibration.eta?.toFixed(4)}, gamma={calibration.gamma?.toFixed(4)},
              rho={calibration.rho?.toFixed(1)}, sigma={calibration.sigma?.toFixed(4)}.
              {calibration.spread_mean && ` Mean bid-ask spread: ${(calibration.spread_mean * 100).toFixed(2)}%.`}
            </p>

            {strats.ac && strats.ppo && (
              <p>
                <strong className="text-text-primary">Key Finding:</strong> The PPO agent
                achieved {strats.ppo.mean_IS.toFixed(2)} bps mean IS compared to
                Almgren-Chriss at {strats.ac.mean_IS.toFixed(2)} bps.
                {strats.ppo.mean_IS < strats.ac.mean_IS
                  ? ' The RL agent outperforms the analytical solution, suggesting it learns to exploit microstructure patterns not captured by the AC model assumptions.'
                  : ' The analytical AC solution outperforms the RL agent, which may indicate that the simulation environment closely matches AC assumptions, leaving little room for RL improvement.'}
              </p>
            )}

            {strats.ow && (
              <p>
                <strong className="text-text-primary">OW Comparison:</strong> The
                Obizhaeva-Wang model achieved {strats.ow.mean_IS.toFixed(2)} bps, reflecting
                the front-loaded strategy's interaction with order book resilience dynamics.
              </p>
            )}

            <p>
              <strong className="text-text-primary">Research Question:</strong> When real
              microstructure violates model assumptions (non-linear impact, stochastic spread,
              correlated order flow), does a PPO agent trained on a calibrated simulation
              produce lower implementation shortfall?
            </p>
          </div>
        )}

        {!calibration && (
          <p className="text-sm text-text-secondary">
            Run calibration and comparison first to generate the research narrative.
          </p>
        )}
      </div>

      {/* Download section */}
      <div className="bg-bg-card border border-border rounded-xl p-6 text-center space-y-4">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleDownload}
          disabled={isDownloading}
          className="px-8 py-3 bg-accent-gold text-bg-root font-semibold rounded-lg hover:bg-accent-gold/90 transition disabled:opacity-50"
        >
          {isDownloading ? 'Generating PDF...' : 'Download Research Note PDF'}
        </motion.button>

        {pdfUrl && (
          <div className="mt-4">
            <iframe
              src={pdfUrl}
              className="w-full h-96 rounded-lg border border-border"
              title="Research Note Preview"
            />
          </div>
        )}
      </div>
    </motion.div>
  );
}
