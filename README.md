# Optimal Execution Research Platform

Live demo: [ExecLab Dashboard](https://execlab.vercel.app)

```
optimal-execution/
  backend/             FastAPI + simulation engine + RL trainer
    main.py            REST + WebSocket endpoints
    config.py          Default params & paths
    data/              LOBSTER parser + synthetic fallback
    calibration/       4-regression calibration pipeline
    simulation/        Gymnasium ExecutionEnv
    strategies/        AC, OW, TWAP, VWAP implementations
    rl/                PPO training + inference
    evaluation/        Multi-episode comparison engine
    report/            PDF research note generator
    cli.py             Typer CLI entry point
  frontend/            React 18 + Vite + TailwindCSS + Recharts
    src/components/    11 dashboard components
    src/hooks/         WebSocket + react-query hooks
```

## Quick Start

```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm install && VITE_API_URL=http://localhost:8000 VITE_WS_URL=ws://localhost:8000 npm run dev

# CLI
cd backend && python -m cli calibrate && python -m cli run --strategy all
```

## LOBSTER Data Setup

1. Register at [lobsterdata.com](https://lobsterdata.com) (free account)
2. Download AAPL 2012-06-21 files: `AAPL_2012-06-21_34200000_57600000_message_10.csv` and `AAPL_2012-06-21_34200000_57600000_orderbook_10.csv`
3. Place in `backend/data/raw/`
4. The platform works immediately with synthetic data; LOBSTER files enable real calibration

## Key Results

| Strategy | IS (bps) | Sharpe-of-IS |
|----------|----------|-------------|
| AC       | ~8-12    | ~-0.8       |
| OW       | ~6-10    | ~-0.7       |
| PPO      | ~5-9     | ~-0.9       |
| TWAP     | ~10-15   | ~-0.6       |

*Results depend on calibration parameters and market conditions.*

## Mathematical Background

**Almgren-Chriss (2001):** Closed-form mean-variance optimal execution minimising E[IS] + lambda * Var[IS] under linear temporary and permanent impact. Optimal trajectory: x(t) = X * sinh(kappa*(T-t)) / sinh(kappa*T).

**Obizhaeva-Wang (2013):** Resilient block-shaped order book with depth D, recovering at rate rho. Optimal strategy: front-load discrete block v0, then trade continuously at constant rate.

**PPO Deep RL:** Proximal Policy Optimisation agent with 5D state (inventory fraction, time fraction, normalised spread, OFI, last impact) trained on calibrated simulation. Tests whether RL adapts to microstructure violations that analytical models assume away.
