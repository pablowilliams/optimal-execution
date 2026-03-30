"""Run all strategies on the SAME environment seed, compute comparison metrics."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from config import config
from evaluation.metrics import compute_metrics
from simulation.execution_env import ExecutionEnv
from strategies.almgren_chriss import compute_ac_trajectory
from strategies.obizhaeva_wang import compute_ow_trajectory
from strategies.twap import compute_twap_trajectory
from strategies.vwap import compute_vwap_trajectory

logger = logging.getLogger(__name__)


def _run_trajectory_in_env(
    trades: list[float],
    params: dict,
    X: float,
    T: float,
    N: int,
    lambda_risk: float,
    seed: int,
) -> tuple[list[dict], dict]:
    """Execute a pre-computed trade schedule in the simulation environment.

    Args:
        trades: List of trade sizes for each step.
        params: Calibrated parameters.
        X: Total shares.
        T: Time horizon.
        N: Time steps.
        lambda_risk: Risk aversion.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (trajectory, info_dict).
    """
    env = ExecutionEnv(params, X=X, T_minutes=T, N=N, lambda_risk=lambda_risk)
    obs, _ = env.reset(seed=seed)

    for k in range(min(len(trades), N)):
        # Convert trade size to fraction of remaining
        if env.x_remaining > 0:
            action_frac = min(trades[k] / env.x_remaining, 1.0)
        else:
            action_frac = 0.0
        action = np.array([action_frac], dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated:
            break

    return env.trajectory, info


def _run_ppo_in_env(
    params: dict,
    X: float,
    T: float,
    N: int,
    lambda_risk: float,
    seed: int,
) -> tuple[list[dict], dict]:
    """Run PPO agent in the simulation environment.

    Args:
        params: Calibrated parameters.
        X: Total shares.
        T: Time horizon.
        N: Time steps.
        lambda_risk: Risk aversion.
        seed: Random seed.

    Returns:
        Tuple of (trajectory, info_dict).
    """
    from stable_baselines3 import PPO as PPOModel

    model_path = Path("./rl/models/ppo_execution.zip")
    if not model_path.exists():
        raise FileNotFoundError("PPO model not found. Train first.")

    model = PPOModel.load("./rl/models/ppo_execution")
    env = ExecutionEnv(params, X=X, T_minutes=T, N=N, lambda_risk=lambda_risk)
    obs, _ = env.reset(seed=seed)

    for _ in range(N):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated:
            break

    return env.trajectory, info


def compare_strategies(
    params: dict,
    X: float = 10000,
    T: float = 30,
    N: int = 30,
    lambda_risk: float = 1e-6,
    n_episodes: int = 500,
) -> dict:
    """Run all strategies for n_episodes and compute comparison statistics.

    Args:
        params: Calibrated parameters.
        X: Total shares.
        T: Time horizon.
        N: Time steps.
        lambda_risk: Risk aversion.
        n_episodes: Number of simulation episodes.

    Returns:
        Dict with per-strategy metrics and episode-level IS lists.
    """
    eta = params.get("eta", config.DEFAULT_ETA)
    gamma = params.get("gamma", config.DEFAULT_GAMMA)
    sigma = params.get("sigma", config.DEFAULT_SIGMA)
    rho = params.get("rho", config.DEFAULT_RHO)
    depth_D = params.get("depth_mean", config.DEFAULT_DEPTH_MEAN)

    # Pre-compute analytical trajectories
    ac_traj = compute_ac_trajectory(X, T, N, lambda_risk, eta, gamma, sigma)
    ow_traj = compute_ow_trajectory(X, T, N, lambda_risk, sigma, rho, depth_D)
    twap_traj = compute_twap_trajectory(X, N)
    vwap_traj = compute_vwap_trajectory(X, N)

    # Check if PPO is available
    ppo_available = Path("./rl/models/ppo_execution.zip").exists()

    strategies = {
        "ac": ac_traj["trades"],
        "ow": ow_traj["trades"],
        "twap": twap_traj["trades"],
        "vwap": vwap_traj["trades"],
    }

    results = {name: [] for name in strategies}
    if ppo_available:
        results["ppo"] = []

    episode_IS = {name: [] for name in results}

    for ep in range(n_episodes):
        seed = ep * 17 + 42  # deterministic but varied seeds

        for name, trades in strategies.items():
            traj, info = _run_trajectory_in_env(
                trades, params, X, T, N, lambda_risk, seed
            )
            S0 = traj[0]["mid"] if traj else 100.0
            metrics = compute_metrics(traj, X, S0, params)
            results[name].append(metrics)
            episode_IS[name].append(metrics["IS_bps"])

        if ppo_available:
            try:
                traj, info = _run_ppo_in_env(params, X, T, N, lambda_risk, seed)
                S0 = traj[0]["mid"] if traj else 100.0
                metrics = compute_metrics(traj, X, S0, params)
                results["ppo"].append(metrics)
                episode_IS["ppo"].append(metrics["IS_bps"])
            except Exception as e:
                logger.warning(f"PPO episode {ep} failed: {e}")

    # Aggregate statistics
    summary = {}
    for name, episodes in results.items():
        if not episodes:
            continue
        IS_arr = np.array([e["IS_bps"] for e in episodes])
        summary[name] = {
            "mean_IS": float(np.mean(IS_arr)),
            "std_IS": float(np.std(IS_arr)),
            "sharpe_IS": float(-np.mean(IS_arr) / max(np.std(IS_arr), 1e-10)),
            "p5_IS": float(np.percentile(IS_arr, 5)),
            "p95_IS": float(np.percentile(IS_arr, 95)),
            "VWAP_slippage_bps": float(
                np.mean([e["VWAP_slippage_bps"] for e in episodes])
            ),
            "perm_impact_bps": float(
                np.mean([e["perm_impact_bps"] for e in episodes])
            ),
            "temp_impact_bps": float(
                np.mean([e["temp_impact_bps"] for e in episodes])
            ),
            "x_remaining_pct": float(
                np.mean([e["x_remaining_pct"] for e in episodes])
            ),
        }

    output = {
        "strategies": summary,
        "episode_IS": {k: v for k, v in episode_IS.items() if v},
    }

    # Cache results
    cache_path = Path("./evaluation/results.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(output, f, indent=2)

    return output
