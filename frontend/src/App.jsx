import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useHealth } from './hooks/useStrategyData';
import ControlPanel from './components/ControlPanel';
import StrategySelector from './components/StrategySelector';
import SimulationPlayer from './components/SimulationPlayer';
import InventoryChart from './components/InventoryChart';
import TradeRateChart from './components/TradeRateChart';
import CostBreakdown from './components/CostBreakdown';
import EfficientFrontier from './components/EfficientFrontier';
import ComparisonTable from './components/ComparisonTable';
import OrderBookViz from './components/OrderBookViz';
import SensitivityHeatmap from './components/SensitivityHeatmap';
import TrainingCurve from './components/TrainingCurve';
import DownloadReport from './components/DownloadReport';

const TABS = ['Configure', 'Simulate', 'Compare', 'Research'];

export default function App() {
  const [activeTab, setActiveTab] = useState('Configure');
  const [params, setParams] = useState({
    X: 10000,
    T: 30,
    N: 30,
    lambda_risk: 1e-6,
    cost_bps: 10,
    strategies: ['ac'],
  });
  const [calibration, setCalibration] = useState(null);
  const [strategyResults, setStrategyResults] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);

  const { data: health } = useHealth();
  const isOnline = health?.status === 'ok';

  return (
    <div className="min-h-screen bg-bg-root">
      {/* Header */}
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-accent-gold">ExecLab</h1>
          <span className="text-text-secondary text-sm">Optimal Trade Execution Research</span>
        </div>
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 text-sm ${isOnline ? 'text-accent-success' : 'text-accent-error'}`}>
            <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-accent-success' : 'bg-accent-error'} animate-pulse`} />
            {isOnline ? 'Online' : 'Offline'}
          </div>
          {/* Tab navigation */}
          <nav className="flex gap-1 bg-bg-card rounded-lg p-1">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all relative ${
                  activeTab === tab
                    ? 'text-accent-gold'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                {tab}
                {activeTab === tab && (
                  <motion.div
                    layoutId="tab-indicator"
                    className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-gold rounded-full"
                  />
                )}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="p-6">
        <AnimatePresence mode="wait">
          {activeTab === 'Configure' && (
            <motion.div
              key="configure"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex gap-6"
            >
              {/* Left: Control Panel */}
              <div className="w-80 flex-shrink-0">
                <ControlPanel
                  params={params}
                  setParams={setParams}
                  calibration={calibration}
                  setCalibration={setCalibration}
                  onResults={setStrategyResults}
                  health={health}
                />
              </div>
              {/* Right: Efficient Frontier */}
              <div className="flex-1">
                <EfficientFrontier
                  params={params}
                  setParams={setParams}
                  calibration={calibration}
                />
              </div>
            </motion.div>
          )}

          {activeTab === 'Simulate' && (
            <motion.div
              key="simulate"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <SimulationPlayer params={params} calibration={calibration} />
              <div className="grid grid-cols-2 gap-6">
                <InventoryChart results={strategyResults} params={params} />
                <TradeRateChart results={strategyResults} params={params} />
              </div>
              <div className="grid grid-cols-2 gap-6">
                <OrderBookViz params={params} />
                <CostBreakdown results={strategyResults} params={params} />
              </div>
            </motion.div>
          )}

          {activeTab === 'Compare' && (
            <motion.div
              key="compare"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <ComparisonTable
                params={params}
                comparisonData={comparisonData}
                setComparisonData={setComparisonData}
              />
              <div className="grid grid-cols-2 gap-6">
                <SensitivityHeatmap params={params} calibration={calibration} />
                <TrainingCurve health={health} />
              </div>
            </motion.div>
          )}

          {activeTab === 'Research' && (
            <motion.div
              key="research"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <DownloadReport
                params={params}
                calibration={calibration}
                comparisonData={comparisonData}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
