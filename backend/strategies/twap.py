"""TWAP baseline: uniform (equal-sized) trading schedule."""

from __future__ import annotations

import numpy as np


def compute_twap_trajectory(X: float, N: int) -> dict:
    """Compute TWAP trajectory — trade X/N each step.

    Args:
        X: Total shares to liquidate.
        N: Number of time steps.

    Returns:
        Dictionary with inventory and trades lists.
    """
    v = X / N  # equal trade each step
    trades = [v] * N

    inventory = [X]
    for k in range(N):
        inventory.append(inventory[-1] - trades[k])

    # Ensure terminal is zero
    inventory[-1] = 0.0

    return {
        "inventory": inventory,
        "trades": trades,
    }
