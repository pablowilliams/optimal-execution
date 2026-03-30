"""OpenAI Gymnasium-compatible ExecutionEnv class.

Simulated limit order book execution environment calibrated to LOBSTER tick data parameters.
"""

from __future__ import annotations

from typing import Any, Optional

import gymnasium
import numpy as np

from config import config


class ExecutionEnv(gymnasium.Env):
    """Simulated limit order book execution environment.

    Calibrated to LOBSTER tick data parameters.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        params: dict,
        X: float = 10000,
        T_minutes: int = 30,
        N: int = 30,
        lambda_risk: float = 1e-6,
        cost_per_share_bps: float = 10,
        S0: float = 100.0,
        seed: Optional[int] = None,
    ):
        """Initialize the execution environment.

        Args:
            params: Calibrated parameters dict with keys eta, gamma, rho, sigma, etc.
            X: Total shares to liquidate.
            T_minutes: Total time in minutes.
            N: Number of discrete time steps.
            lambda_risk: Risk aversion parameter.
            cost_per_share_bps: Fixed transaction cost in basis points.
            S0: Initial stock price.
            seed: Random seed.
        """
        super().__init__()
        self.params = params
        self.X = float(X)
        self.T = T_minutes
        self.N = N
        self.dt = T_minutes / N  # minutes per step
        self.dt_sec = self.dt * 60  # seconds per step
        self.lambda_risk = lambda_risk
        self.cost_bps = cost_per_share_bps / 10000
        self.S0_base = S0

        # Unpack calibrated params
        self.eta = params.get("eta", config.DEFAULT_ETA)
        self.gamma = params.get("gamma", config.DEFAULT_GAMMA)
        self.rho = params.get("rho", config.DEFAULT_RHO) / 60  # convert to per-second
        self.sigma_annual = params.get("sigma", config.DEFAULT_SIGMA)
        self.sigma_step = self.sigma_annual / np.sqrt(252 * 390 / self.dt)
        self.spread_mean = params.get("spread_mean", config.DEFAULT_SPREAD_MEAN)
        self.spread_std = params.get("spread_std", config.DEFAULT_SPREAD_STD)
        self.depth_mean = params.get("depth_mean", config.DEFAULT_DEPTH_MEAN)
        self.ofi_autocorr = params.get("ofi_autocorr", config.DEFAULT_OFI_AUTOCORR)

        # Spaces
        # Observation: [x_remaining/X, t/T, spread/S0, OFI, last_impact]
        self.observation_space = gymnasium.spaces.Box(
            low=np.array([0.0, 0.0, 0.0, -1.0, -1.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 0.05, 1.0, 0.0], dtype=np.float32),
        )
        # Action: fraction of remaining inventory to trade this step
        self.action_space = gymnasium.spaces.Box(
            low=np.array([0.0], dtype=np.float32),
            high=np.array([1.0], dtype=np.float32),
        )

        self._rng = np.random.default_rng(seed)

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[np.ndarray, dict]:
        """Reset state: full inventory, t=0, random S_0 ~ N(100, 1).

        Args:
            seed: Optional random seed.
            options: Optional reset options.

        Returns:
            Tuple of (observation, info_dict).
        """
        if seed is not None:
            self._rng = np.random.default_rng(seed)

        self.S0 = self.S0_base * (1 + self._rng.normal(0, 0.02))
        self.mid = self.S0
        self.x_remaining = self.X
        self.step_count = 0
        self.cumulative_IS = 0.0
        self.ofi = 0.0
        self.trajectory: list[dict] = []

        obs = self._get_obs(last_impact=0.0)
        return obs, {}

    def _get_obs(self, last_impact: float) -> np.ndarray:
        """Build the 5-dimensional observation vector.

        Args:
            last_impact: Last realised temporary impact.

        Returns:
            Observation array [x_rem/X, t/N, spread/S0, ofi, last_impact].
        """
        spread_t = np.clip(
            self._rng.normal(self.spread_mean, self.spread_std),
            0.0001,
            0.05,
        )
        return np.array(
            [
                self.x_remaining / self.X,
                self.step_count / self.N,
                spread_t / self.S0,
                self.ofi,
                np.clip(last_impact, -1.0, 0.0),
            ],
            dtype=np.float32,
        )

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict]:
        """Execute one trading step.

        Args:
            action: Array with single float in [0, 1], fraction of remaining inventory.

        Returns:
            Tuple of (obs, reward, terminated, truncated, info).
        """
        a = float(np.clip(action[0], 0.0, 1.0))
        v_k = a * self.x_remaining

        # Market state for this step
        spread_t = np.clip(
            self._rng.normal(self.spread_mean, self.spread_std),
            0.0001,
            0.05,
        )
        noise = self._rng.normal(0, self.sigma_step)

        # Impact components
        temp_impact = self.eta * (v_k / max(self.dt_sec, 1e-6))  # $/share
        perm_impact = self.gamma * v_k  # permanent price level shift

        # OFI-driven drift
        self.ofi = (
            self.ofi_autocorr * self.ofi
            + np.sqrt(1 - self.ofi_autocorr**2) * self._rng.normal(0, 1)
        )
        ofi_drift = 0.2 * self.sigma_step * self.ofi

        # Execution price (buy to liquidate = sell, so we lose spread + temp impact)
        S_exec = self.mid - spread_t * self.S0 / 2 - temp_impact

        # IS contribution for this step
        IS_step = v_k * (self.S0 - S_exec)  # cost in dollars

        # Update mid-price
        self.mid = self.mid - perm_impact + ofi_drift + noise * self.S0

        # Update state
        self.x_remaining = max(self.x_remaining - v_k, 0.0)
        self.cumulative_IS += IS_step
        self.step_count += 1

        # Record trajectory
        self.trajectory.append(
            {
                "step": self.step_count,
                "v_k": v_k,
                "mid": self.mid,
                "S_exec": S_exec,
                "IS_step": IS_step,
                "IS_cum": self.cumulative_IS,
                "x_remaining": self.x_remaining,
                "spread": spread_t,
            }
        )

        # Reward = negative IS step cost + transaction cost
        reward = -IS_step / (self.X * self.S0) * 10000 - self.cost_bps * v_k

        terminated = self.step_count >= self.N

        if terminated and self.x_remaining > 0:
            # Large penalty for not fully liquidating
            reward -= 500 * (self.x_remaining / self.X)

        obs = self._get_obs(last_impact=-temp_impact / self.S0)

        return (
            obs,
            reward,
            terminated,
            False,
            {
                "IS_bps": self.cumulative_IS / (self.X * self.S0) * 10000,
                "x_remaining": self.x_remaining,
            },
        )
