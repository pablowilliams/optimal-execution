"""Obizhaeva-Wang (2013) resilient order book model with front-loaded strategy."""

from __future__ import annotations

import numpy as np

from config import config


def compute_ow_trajectory(
    X: float,
    T_min: float,
    N: int,
    lambda_risk: float,
    sigma: float,
    rho_per_min: float,
    depth_D: float,
    S0: float = 100.0,
) -> dict:
    """Compute front-loaded OW trajectory.

    OW replaces linear temporary impact with a resilient block-shaped order book.
    The book has depth D (shares per unit price), recovers exponentially at rate rho.

    Args:
        X: Total shares to liquidate.
        T_min: Time horizon in minutes.
        N: Number of time steps.
        lambda_risk: Risk aversion parameter.
        sigma: Volatility (annualised).
        rho_per_min: Resilience parameter (mean-reversion speed, per minute).
        depth_D: Order book depth (shares per price level).
        S0: Initial stock price.

    Returns:
        Dictionary with inventory, trades, v0, u_rate, IS_bps_analytical.
    """
    dt = T_min / N
    rho = rho_per_min  # resilience per minute

    # Front block (OW 2013, no risk aversion limit):
    # v_0 = X * rho / (rho + 2/T_min)
    v0 = X * rho / (rho + 2 / T_min)

    # Remaining: X_rem = X - v0
    X_rem = X - v0

    # Continuous rate: u = X_rem / T_min (shares per minute)
    u_rate = X_rem / T_min

    # Discrete: v[k] = u * dt for k=2..N
    # v[1] = v0 + u*dt (first step = front block + first continuous chunk)
    trades = np.zeros(N)
    trades[0] = v0 + u_rate * dt  # front block + first continuous
    for k in range(1, N):
        trades[k] = u_rate * dt

    # Build inventory from trades
    inventory = np.zeros(N + 1)
    inventory[0] = X
    for k in range(N):
        inventory[k + 1] = max(inventory[k] - trades[k], 0.0)

    # Force terminal to zero
    if inventory[N] > 0:
        trades[N - 1] += inventory[N]
        inventory[N] = 0.0

    # With risk aversion (Lorenz-Schied 2013 extension):
    sigma_per_min = sigma / np.sqrt(252 * 390)
    kappa_ow = np.sqrt(2 * lambda_risk * sigma_per_min**2 * depth_D)

    # Adjust v[k] using exponential profile matching kappa_ow
    if kappa_ow > 1e-10:
        # Exponential liquidation rate
        times = np.arange(N) * dt
        exp_weights = np.exp(-kappa_ow * times)
        exp_weights = exp_weights / exp_weights.sum()
        trades_ra = X * exp_weights

        # Blend: higher lambda -> more front-loaded
        blend = min(kappa_ow * T_min, 1.0)
        trades = (1 - blend) * trades + blend * trades_ra

        # Rebuild inventory
        inventory[0] = X
        for k in range(N):
            inventory[k + 1] = max(inventory[k] - trades[k], 0.0)
        if inventory[N] > 0:
            trades[N - 1] += inventory[N]
            inventory[N] = 0.0

    # Analytical IS (OW Proposition 2):
    # IS_OW = v0^2 / (2*D) + u^2*T/(2*rho) + cross terms
    if depth_D > 0:
        IS_OW = v0**2 / (2 * depth_D) + u_rate**2 * T_min / (2 * rho) if rho > 0 else v0**2 / (2 * depth_D)
    else:
        IS_OW = 0.0

    IS_bps = IS_OW / (X * S0) * 10000

    return {
        "inventory": inventory.tolist(),
        "trades": trades.tolist(),
        "v0": float(v0),
        "u_rate": float(u_rate),
        "IS_bps_analytical": float(IS_bps),
    }
