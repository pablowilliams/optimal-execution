"""Almgren-Chriss (2001) closed-form optimal trading trajectory + efficient frontier."""

from __future__ import annotations

import numpy as np

from config import config


def compute_ac_trajectory(
    X: float,
    T_min: float,
    N: int,
    lambda_risk: float,
    eta: float,
    gamma: float,
    sigma: float,
) -> dict:
    """Compute the AC closed-form optimal inventory schedule.

    Args:
        X: Total shares to liquidate.
        T_min: Time horizon in minutes.
        N: Number of time steps.
        lambda_risk: Risk aversion parameter.
        eta: Temporary impact coefficient.
        gamma: Permanent impact coefficient.
        sigma: Volatility (annualised).

    Returns:
        Dictionary with inventory, trades, E_IS_bps, Var_IS_bps, kappa, eta_tilde.
    """
    dt = T_min / N  # minutes per step
    T = T_min  # total time in minutes

    # sigma per step (annualised -> per minute)
    sigma_per_step = sigma / np.sqrt(252 * 390)  # per-minute vol
    sigma_sq = sigma_per_step**2

    # Adjusted temporary impact
    eta_tilde = eta - 0.5 * gamma * dt

    # kappa
    kappa_sq = lambda_risk * sigma_sq / max(eta_tilde, 1e-10)
    kappa = np.sqrt(max(kappa_sq, 1e-10))

    # Optimal inventory schedule
    # x[k] = X * sinh(kappa * (T - k*dt)) / sinh(kappa * T)
    inventory = np.zeros(N + 1)
    inventory[0] = X

    kappa_T = kappa * T

    if kappa_T < 1e-6:
        # Linear schedule as limit
        for k in range(1, N + 1):
            inventory[k] = X * (1 - k / N)
    else:
        for k in range(1, N + 1):
            t_k = k * dt
            inventory[k] = X * np.sinh(kappa * (T - t_k)) / np.sinh(kappa_T)

    # Ensure terminal condition
    inventory[N] = 0.0

    # Trade sizes
    trades = np.diff(-inventory)  # v_k = x_{k-1} - x_k

    # Expected IS using S0=100 for normalisation
    S0 = 100.0

    # E[IS] = 0.5 * gamma * X^2 + eta_tilde * kappa * X^2 / tanh(kappa*T)
    if kappa_T < 1e-6:
        E_IS = 0.5 * gamma * X**2 * S0 + eta_tilde * X**2 * S0 / T
    else:
        E_IS = (
            0.5 * gamma * X**2 * S0
            + eta_tilde * X**2 * S0 * kappa / np.tanh(kappa_T)
            - 0.5 * gamma * X**2 * S0
        )
        E_IS = eta_tilde * X**2 * S0 * kappa / np.tanh(kappa_T)

    E_IS_bps = E_IS / (X * S0) * 10000

    # Var[IS] approximation
    # Var = sigma^2 * X^2 * S0^2 * T / (2 * N) * sum of inventory^2 terms
    inv_sq_sum = np.sum(inventory[:-1] ** 2) * dt
    Var_IS = sigma_sq * S0**2 * inv_sq_sum
    Var_IS_bps = Var_IS / (X * S0) ** 2 * 10000**2

    return {
        "inventory": inventory.tolist(),
        "trades": trades.tolist(),
        "E_IS_bps": float(E_IS_bps),
        "Var_IS_bps": float(Var_IS_bps),
        "kappa": float(kappa),
        "eta_tilde": float(eta_tilde),
    }


def compute_efficient_frontier(
    X: float,
    T_min: float,
    N: int,
    eta: float,
    gamma: float,
    sigma: float,
    n_points: int = 50,
) -> list[dict]:
    """Compute efficient frontier: 50 values of lambda from 1e-8 to 1e-4.

    Args:
        X: Total shares.
        T_min: Time horizon.
        N: Time steps.
        eta: Temporary impact.
        gamma: Permanent impact.
        sigma: Volatility.
        n_points: Number of frontier points.

    Returns:
        List of dicts with lambda, E_IS_bps, Var_IS_bps, Std_IS_bps.
    """
    lambdas = np.logspace(-8, -4, n_points)
    frontier = []

    for lam in lambdas:
        traj = compute_ac_trajectory(X, T_min, N, lam, eta, gamma, sigma)
        frontier.append(
            {
                "lambda": float(lam),
                "E_IS_bps": traj["E_IS_bps"],
                "Var_IS_bps": traj["Var_IS_bps"],
                "Std_IS_bps": float(np.sqrt(max(traj["Var_IS_bps"], 0))),
            }
        )

    return frontier
