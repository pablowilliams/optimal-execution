"""Load PPO model, run inference, return trajectory."""

from __future__ import annotations

import logging
from pathlib import Path

from config import config
from rl.train import run_ppo_inference

logger = logging.getLogger(__name__)


def evaluate_ppo(
    params: dict,
    X: float = 10000,
    T: float = 30,
    N: int = 30,
    lambda_risk: float = 1e-6,
    model_path: str = "./rl/models/ppo_execution",
) -> dict:
    """Evaluate PPO agent on a single episode.

    Args:
        params: Calibrated parameters.
        X: Shares.
        T: Time horizon.
        N: Steps.
        lambda_risk: Risk aversion.
        model_path: Path to model.

    Returns:
        Trajectory dict.
    """
    model_file = Path(model_path + ".zip")
    if not model_file.exists():
        raise FileNotFoundError(
            f"PPO model not found at {model_file}. Train first with /train-rl."
        )

    return run_ppo_inference(params, X, T, N, lambda_risk, model_path)
