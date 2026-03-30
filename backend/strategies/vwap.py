"""VWAP baseline: volume-weighted trading schedule (uniform as proxy)."""

from __future__ import annotations

import numpy as np


def compute_vwap_trajectory(X: float, N: int) -> dict:
    """Compute VWAP trajectory.

    Without intraday volume profile data, VWAP defaults to TWAP-like uniform
    but with slight U-shape to mimic typical intraday volume (higher at open/close).

    Args:
        X: Total shares to liquidate.
        N: Number of time steps.

    Returns:
        Dictionary with inventory and trades lists.
    """
    # U-shaped volume profile: higher at start and end
    t = np.linspace(0, 1, N)
    volume_profile = 1.0 + 0.5 * (np.exp(-5 * t) + np.exp(-5 * (1 - t)))
    volume_profile = volume_profile / volume_profile.sum()

    trades = (X * volume_profile).tolist()

    inventory = [X]
    for k in range(N):
        inventory.append(max(inventory[-1] - trades[k], 0.0))

    # Ensure terminal is zero
    inventory[-1] = 0.0

    return {
        "inventory": inventory,
        "trades": trades,
    }
