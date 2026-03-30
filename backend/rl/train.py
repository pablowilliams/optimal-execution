"""PPO training loop using stable-baselines3."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback

from config import config
from simulation.execution_env import ExecutionEnv

logger = logging.getLogger(__name__)


class LogCallback(BaseCallback):
    """Custom callback to log mean episode reward every 10k steps."""

    def __init__(self) -> None:
        super().__init__()
        self.rewards_log: list[dict] = []

    def _on_rollout_end(self) -> None:
        if len(self.model.ep_info_buffer) > 0:
            mean_r = np.mean([ep["r"] for ep in self.model.ep_info_buffer])
            self.rewards_log.append(
                {
                    "timestep": self.num_timesteps,
                    "mean_reward": float(mean_r),
                }
            )

    def _on_step(self) -> bool:
        return True


def train_ppo(
    params: dict,
    total_timesteps: int = 1_000_000,
    X: float = 10000,
    T: float = 30,
    N: int = 30,
    lambda_risk: float = 1e-6,
    save_path: str = "./rl/models/ppo_execution",
) -> str:
    """Train PPO agent on ExecutionEnv.

    Args:
        params: Calibrated parameters dict.
        total_timesteps: Total training timesteps.
        X: Shares to liquidate.
        T: Time horizon in minutes.
        N: Number of steps.
        lambda_risk: Risk aversion.
        save_path: Where to save the model.

    Returns:
        Path to saved model zip file.
    """
    env = ExecutionEnv(params, X=X, T_minutes=T, N=N, lambda_risk=lambda_risk)
    eval_env = ExecutionEnv(params, X=X, T_minutes=T, N=N, lambda_risk=lambda_risk)

    log_cb = LogCallback()

    model = PPO(
        "MlpPolicy",
        env,
        verbose=0,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        policy_kwargs={"net_arch": [128, 128, 64]},
    )

    model.learn(total_timesteps=total_timesteps, callback=log_cb)

    # Save model
    save_dir = Path(save_path)
    save_dir.parent.mkdir(parents=True, exist_ok=True)
    model.save(save_path)

    # Save training log
    log_dir = Path("./rl/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    with open(log_dir / "training_log.json", "w") as f:
        json.dump(log_cb.rewards_log, f)

    logger.info(f"PPO training complete. Model saved to {save_path}.zip")
    return save_path + ".zip"


def run_ppo_inference(
    params: dict,
    X: float = 10000,
    T: float = 30,
    N: int = 30,
    lambda_risk: float = 1e-6,
    model_path: str = "./rl/models/ppo_execution",
) -> dict:
    """Load trained PPO model and run one episode deterministically.

    Args:
        params: Calibrated parameters.
        X: Shares to liquidate.
        T: Time horizon.
        N: Time steps.
        lambda_risk: Risk aversion.
        model_path: Path to saved model.

    Returns:
        Dict with inventory, trades, IS_bps_realised matching AC/OW format.
    """
    env = ExecutionEnv(params, X=X, T_minutes=T, N=N, lambda_risk=lambda_risk)
    model = PPO.load(model_path)

    obs, _ = env.reset(seed=42)
    inventory = [X]
    trades = []

    for _ in range(N):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        trades.append(float(env.trajectory[-1]["v_k"]))
        inventory.append(float(env.x_remaining))
        if terminated:
            break

    IS_bps = info.get("IS_bps", 0.0)

    return {
        "inventory": inventory,
        "trades": trades,
        "IS_bps_realised": float(IS_bps),
    }
