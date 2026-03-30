"""Exact metric definitions for strategy evaluation."""

from __future__ import annotations

import numpy as np


def compute_metrics(
    trajectory: list[dict],
    X: float,
    S0: float,
    params: dict,
) -> dict:
    """Compute all evaluation metrics from a trajectory.

    Args:
        trajectory: List of step dicts with keys: step, v_k, mid, S_exec,
                    IS_step, IS_cum, x_remaining, spread.
        X: Total shares to liquidate.
        S0: Arrival price.
        params: Calibrated parameters (gamma, eta).

    Returns:
        Dict with IS_bps, VWAP_slippage_bps, perm_impact_bps,
        temp_impact_bps, x_remaining_pct, n_steps_used.
    """
    if not trajectory:
        return {
            "IS_bps": 0.0,
            "VWAP_slippage_bps": 0.0,
            "perm_impact_bps": 0.0,
            "temp_impact_bps": 0.0,
            "x_remaining_pct": 100.0,
            "n_steps_used": 0,
        }

    # 1. Implementation Shortfall (IS)
    IS_total_dollars = trajectory[-1]["IS_cum"]
    IS_bps = IS_total_dollars / (X * S0) * 10000

    # 2. VWAP Slippage
    v_k_arr = np.array([t["v_k"] for t in trajectory])
    S_exec_arr = np.array([t["S_exec"] for t in trajectory])
    S_mid_arr = np.array([t["mid"] for t in trajectory])

    total_shares = np.sum(v_k_arr)
    if total_shares > 0:
        VWAP_exec = np.sum(v_k_arr * S_exec_arr) / total_shares
        VWAP_mid = np.sum(v_k_arr * S_mid_arr) / total_shares
    else:
        VWAP_exec = S0
        VWAP_mid = S0

    VWAP_slippage_bps = (VWAP_exec - VWAP_mid) / S0 * 10000  # negative = bad

    # 4. Permanent Impact Cost
    gamma = params.get("gamma", 0.0008)
    PIC = gamma * X * S0  # total permanent cost in dollars
    perm_impact_bps = PIC / (X * S0) * 10000

    # 5. Temporary Impact Cost (approximation)
    eta = params.get("eta", 0.0023)
    temp_impact_dollars = IS_total_dollars - PIC
    temp_impact_bps = temp_impact_dollars / (X * S0) * 10000

    # Remaining inventory
    x_remaining_pct = trajectory[-1]["x_remaining"] / X * 100

    return {
        "IS_bps": float(IS_bps),
        "VWAP_slippage_bps": float(VWAP_slippage_bps),
        "perm_impact_bps": float(perm_impact_bps),
        "temp_impact_bps": float(temp_impact_bps),
        "x_remaining_pct": float(x_remaining_pct),
        "n_steps_used": len(trajectory),
    }
