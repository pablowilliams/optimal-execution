"""FastAPI app with WebSocket, all REST endpoints for optimal execution platform."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Literal, Optional

import numpy as np
from fastapi import BackgroundTasks, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Optimal Execution Research Platform", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
_params: Optional[dict] = None
_ppo_model_trained: bool = False
_training_jobs: dict = {}


# Pydantic models
class StrategyRequest(BaseModel):
    """Request to run a strategy."""
    strategy: Literal["ac", "ow", "ppo", "twap", "vwap", "all"]
    X: float = 10000
    T: int = 30
    N: int = 30
    lambda_risk: float = 1e-6
    cost_bps: float = 10


class FrontierRequest(BaseModel):
    """Request for efficient frontier."""
    X: float = 10000
    T: int = 30
    N: int = 30
    lambda_min: float = 1e-8
    lambda_max: float = 1e-4
    n_points: int = 50


class SensitivityRequest(BaseModel):
    """Request for sensitivity heatmap."""
    X: float = 10000
    N: int = 30
    lambda_risk: float = 1e-6
    T_values: list[int] = [5, 10, 15, 20, 30, 45, 60]
    lambda_values: list[float] = [1e-8, 1e-7, 1e-6, 1e-5, 1e-4]


class TrainRequest(BaseModel):
    """Request to train PPO."""
    total_timesteps: int = 500000
    X: float = 10000
    T: int = 30
    N: int = 30
    lambda_risk: float = 1e-6


class CalibrateRequest(BaseModel):
    """Calibration request."""
    use_synthetic: bool = True


class CompareRequest(BaseModel):
    """Comparison request."""
    X: float = 10000
    T: int = 30
    N: int = 30
    lambda_risk: float = 1e-6
    n_episodes: int = 500


# Startup
@app.on_event("startup")
async def startup_event() -> None:
    """Load calibration on startup, check for PPO model."""
    global _params, _ppo_model_trained

    config.ensure_dirs()

    from calibration.calibrate import load_or_calibrate
    _params = load_or_calibrate()
    logger.info(f"Calibrated params loaded: {_params}")

    _ppo_model_trained = Path("./rl/models/ppo_execution.zip").exists()
    logger.info(f"PPO model available: {_ppo_model_trained}")


# Endpoints
@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "calibrated": _params is not None,
        "model_trained": _ppo_model_trained,
    }


@app.post("/calibrate")
async def calibrate(req: CalibrateRequest) -> dict:
    """Run calibration and return parameters."""
    global _params

    if req.use_synthetic:
        from data.synthetic_generator import generate_synthetic_lob
        from calibration.calibrate import calibrate_from_lobster
        lob_data = generate_synthetic_lob()
        _params = calibrate_from_lobster(lob_data)
    else:
        from calibration.calibrate import load_or_calibrate
        _params = load_or_calibrate()

    return _params


@app.post("/run-strategy")
async def run_strategy(req: StrategyRequest) -> dict:
    """Run requested strategy/strategies, return trajectory + metrics."""
    global _params, _ppo_model_trained

    if _params is None:
        from calibration.calibrate import load_or_calibrate
        _params = load_or_calibrate()

    eta = _params.get("eta", config.DEFAULT_ETA)
    gamma = _params.get("gamma", config.DEFAULT_GAMMA)
    sigma = _params.get("sigma", config.DEFAULT_SIGMA)
    rho = _params.get("rho", config.DEFAULT_RHO)
    depth_D = _params.get("depth_mean", config.DEFAULT_DEPTH_MEAN)

    results = {}

    strategies_to_run = (
        ["ac", "ow", "ppo", "twap", "vwap"] if req.strategy == "all"
        else [req.strategy]
    )

    for strat in strategies_to_run:
        if strat == "ac":
            from strategies.almgren_chriss import compute_ac_trajectory
            traj = compute_ac_trajectory(req.X, req.T, req.N, req.lambda_risk, eta, gamma, sigma)
            # Run through simulation for IS metrics
            sim_traj = _simulate_trajectory(traj["trades"], req)
            traj["simulated_metrics"] = sim_traj
            results["ac"] = traj

        elif strat == "ow":
            from strategies.obizhaeva_wang import compute_ow_trajectory
            traj = compute_ow_trajectory(req.X, req.T, req.N, req.lambda_risk, sigma, rho, depth_D)
            sim_traj = _simulate_trajectory(traj["trades"], req)
            traj["simulated_metrics"] = sim_traj
            results["ow"] = traj

        elif strat == "ppo":
            if not _ppo_model_trained and not Path("./rl/models/ppo_execution.zip").exists():
                # Auto-train with reduced timesteps
                logger.info("PPO model not found. Auto-training...")
                from rl.train import train_ppo
                train_ppo(_params, total_timesteps=config.RAILWAY_PPO_TIMESTEPS,
                         X=req.X, T=req.T, N=req.N, lambda_risk=req.lambda_risk)
                _ppo_model_trained = True

            from rl.evaluate import evaluate_ppo
            traj = evaluate_ppo(_params, req.X, req.T, req.N, req.lambda_risk)
            results["ppo"] = traj

        elif strat == "twap":
            from strategies.twap import compute_twap_trajectory
            traj = compute_twap_trajectory(req.X, req.N)
            sim_traj = _simulate_trajectory(traj["trades"], req)
            traj["simulated_metrics"] = sim_traj
            results["twap"] = traj

        elif strat == "vwap":
            from strategies.vwap import compute_vwap_trajectory
            traj = compute_vwap_trajectory(req.X, req.N)
            sim_traj = _simulate_trajectory(traj["trades"], req)
            traj["simulated_metrics"] = sim_traj
            results["vwap"] = traj

    return results


def _simulate_trajectory(trades: list[float], req: StrategyRequest) -> dict:
    """Run a trade schedule through the simulation environment."""
    from simulation.execution_env import ExecutionEnv
    from evaluation.metrics import compute_metrics

    env = ExecutionEnv(_params, X=req.X, T_minutes=req.T, N=req.N, lambda_risk=req.lambda_risk)
    obs, _ = env.reset(seed=42)

    for k in range(min(len(trades), req.N)):
        if env.x_remaining > 0:
            action_frac = min(trades[k] / env.x_remaining, 1.0)
        else:
            action_frac = 0.0
        action = np.array([action_frac], dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated:
            break

    S0 = env.trajectory[0]["mid"] if env.trajectory else 100.0
    metrics = compute_metrics(env.trajectory, req.X, S0, _params)

    return {
        "trajectory": env.trajectory,
        "metrics": metrics,
    }


@app.post("/efficient-frontier")
async def efficient_frontier(req: FrontierRequest) -> dict:
    """Return AC efficient frontier points."""
    if _params is None:
        return {"error": "Not calibrated"}

    from strategies.almgren_chriss import compute_efficient_frontier

    eta = _params.get("eta", config.DEFAULT_ETA)
    gamma = _params.get("gamma", config.DEFAULT_GAMMA)
    sigma = _params.get("sigma", config.DEFAULT_SIGMA)

    frontier = compute_efficient_frontier(
        req.X, req.T, req.N, eta, gamma, sigma, req.n_points
    )
    return {"frontier": frontier}


@app.post("/sensitivity")
async def sensitivity(req: SensitivityRequest) -> dict:
    """Return 2D heatmap of IS_bps indexed by T and lambda."""
    if _params is None:
        return {"error": "Not calibrated"}

    from strategies.almgren_chriss import compute_ac_trajectory

    eta = _params.get("eta", config.DEFAULT_ETA)
    gamma = _params.get("gamma", config.DEFAULT_GAMMA)
    sigma = _params.get("sigma", config.DEFAULT_SIGMA)

    heatmap = {}
    for T_val in req.T_values:
        heatmap[str(T_val)] = {}
        for lam in req.lambda_values:
            traj = compute_ac_trajectory(req.X, T_val, req.N, lam, eta, gamma, sigma)
            heatmap[str(T_val)][str(lam)] = round(traj["E_IS_bps"], 2)

    return {"heatmap": heatmap, "T_values": req.T_values, "lambda_values": req.lambda_values}


@app.post("/train-rl")
async def train_rl(req: TrainRequest, background_tasks: BackgroundTasks) -> dict:
    """Start PPO training as BackgroundTask, return job_id."""
    job_id = str(uuid.uuid4())[:8]

    _training_jobs[job_id] = {
        "status": "running",
        "progress_pct": 0,
        "current_timestep": 0,
        "total_timesteps": req.total_timesteps,
    }

    def _train_task() -> None:
        global _ppo_model_trained
        try:
            from rl.train import train_ppo
            train_ppo(
                _params,
                total_timesteps=req.total_timesteps,
                X=req.X,
                T=req.T,
                N=req.N,
                lambda_risk=req.lambda_risk,
            )
            _training_jobs[job_id]["status"] = "complete"
            _training_jobs[job_id]["progress_pct"] = 100
            _ppo_model_trained = True
        except Exception as e:
            _training_jobs[job_id]["status"] = f"failed: {str(e)}"

    background_tasks.add_task(_train_task)
    return {"job_id": job_id, "status": "started"}


@app.get("/train-status/{job_id}")
async def train_status(job_id: str) -> dict:
    """Check training job status."""
    if job_id in _training_jobs:
        return _training_jobs[job_id]
    return {"status": "not_found"}


@app.get("/training-curve")
async def training_curve() -> dict:
    """Load training log and return curve data."""
    log_path = Path("./rl/logs/training_log.json")
    if log_path.exists():
        with open(log_path) as f:
            curve = json.load(f)
        return {"curve": curve}
    return {"curve": []}


@app.post("/compare")
async def compare(req: CompareRequest) -> dict:
    """Run full comparison across all strategies."""
    if _params is None:
        return {"error": "Not calibrated"}

    from evaluation.compare import compare_strategies
    return compare_strategies(
        _params, req.X, req.T, req.N, req.lambda_risk, req.n_episodes
    )


@app.websocket("/ws/simulate")
async def ws_simulate(websocket: WebSocket) -> None:
    """WebSocket: stream simulation steps in real-time as JSON."""
    await websocket.accept()

    try:
        # Receive initial parameters
        data = await websocket.receive_json()
        strategy = data.get("strategy", "ac")
        X = data.get("X", 10000)
        T = data.get("T", 30)
        N = data.get("N", 30)
        lambda_risk = data.get("lambda_risk", 1e-6)

        if _params is None:
            await websocket.send_json({"error": "Not calibrated"})
            await websocket.close()
            return

        eta = _params.get("eta", config.DEFAULT_ETA)
        gamma = _params.get("gamma", config.DEFAULT_GAMMA)
        sigma = _params.get("sigma", config.DEFAULT_SIGMA)
        rho = _params.get("rho", config.DEFAULT_RHO)
        depth_D = _params.get("depth_mean", config.DEFAULT_DEPTH_MEAN)

        # Compute trades for the strategy
        if strategy == "ac":
            from strategies.almgren_chriss import compute_ac_trajectory
            traj = compute_ac_trajectory(X, T, N, lambda_risk, eta, gamma, sigma)
            trades = traj["trades"]
        elif strategy == "ow":
            from strategies.obizhaeva_wang import compute_ow_trajectory
            traj = compute_ow_trajectory(X, T, N, lambda_risk, sigma, rho, depth_D)
            trades = traj["trades"]
        elif strategy == "twap":
            from strategies.twap import compute_twap_trajectory
            traj = compute_twap_trajectory(X, N)
            trades = traj["trades"]
        elif strategy == "vwap":
            from strategies.vwap import compute_vwap_trajectory
            traj = compute_vwap_trajectory(X, N)
            trades = traj["trades"]
        elif strategy == "ppo":
            # PPO runs step by step
            trades = None
        else:
            await websocket.send_json({"error": f"Unknown strategy: {strategy}"})
            await websocket.close()
            return

        # Run simulation step by step
        from simulation.execution_env import ExecutionEnv
        env = ExecutionEnv(_params, X=X, T_minutes=T, N=N, lambda_risk=lambda_risk)
        obs, _ = env.reset(seed=42)

        if strategy == "ppo" and Path("./rl/models/ppo_execution.zip").exists():
            from stable_baselines3 import PPO as PPOModel
            model = PPOModel.load("./rl/models/ppo_execution")
        else:
            model = None

        for step in range(N):
            if strategy == "ppo" and model is not None:
                action, _ = model.predict(obs, deterministic=True)
            elif trades is not None and step < len(trades):
                if env.x_remaining > 0:
                    frac = min(trades[step] / env.x_remaining, 1.0)
                else:
                    frac = 0.0
                action = np.array([frac], dtype=np.float32)
            else:
                action = np.array([0.0], dtype=np.float32)

            obs, reward, terminated, truncated, info = env.step(action)

            step_data = env.trajectory[-1]
            await websocket.send_json({
                "step": step_data["step"],
                "x_remaining": float(step_data["x_remaining"]),
                "v_k": float(step_data["v_k"]),
                "mid": float(step_data["mid"]),
                "S_exec": float(step_data["S_exec"]),
                "IS_step": float(step_data["IS_step"]),
                "IS_cum": float(step_data["IS_cum"]),
                "spread": float(step_data["spread"]),
            })

            await asyncio.sleep(0.03)  # ~30ms per step for smooth animation

            if terminated:
                break

        # Send completion
        await websocket.send_json({"done": True, "IS_bps": info.get("IS_bps", 0)})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass


@app.get("/research-note")
async def research_note(
    strategy: str = "all",
    X: float = 10000,
    T: float = 30,
) -> StreamingResponse:
    """Generate and stream 4-page PDF research note."""
    global _params
    if _params is None:
        from calibration.calibrate import load_or_calibrate
        _params = load_or_calibrate()

    # Load or generate comparison data
    results_path = Path("./evaluation/results.json")
    if results_path.exists():
        with open(results_path) as f:
            comparison = json.load(f)
    else:
        from evaluation.compare import compare_strategies
        comparison = compare_strategies(_params, X=X, T=T, n_episodes=100)

    from report.research_note import generate_research_note
    pdf_bytes = generate_research_note(_params, comparison, strategy, X, T)

    return StreamingResponse(
        content=iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=research_note.pdf"},
    )
