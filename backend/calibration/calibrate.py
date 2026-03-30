"""Run four regressions on LOBSTER data to estimate model parameters."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import linregress

from config import config

logger = logging.getLogger(__name__)


def calibrate_from_lobster(lob_data: dict) -> dict:
    """Run four regressions to estimate model parameters.

    Args:
        lob_data: Dictionary from parse_lobster or generate_synthetic_lob.

    Returns:
        Dict with keys: eta, gamma, rho, sigma, spread_mean, spread_std,
        depth_mean, ofi_autocorr.
    """
    mid_prices = lob_data["mid_prices"]
    spreads = lob_data["spreads"]
    ofi = lob_data["ofi"]
    exec_times = lob_data["exec_times"]
    exec_sizes = lob_data["exec_sizes"]
    exec_prices = lob_data["exec_prices"]
    n_seconds = lob_data["n_seconds"]

    # 1. Temporary impact eta (regression on 5-min buckets)
    bucket_size = 300  # 5 minutes in seconds
    n_buckets = n_seconds // bucket_size
    eta = config.DEFAULT_ETA

    if len(exec_times) > 0 and n_buckets > 2:
        bucket_volumes = np.zeros(n_buckets)
        bucket_price_changes = np.zeros(n_buckets)

        for i in range(n_buckets):
            t_start = i * bucket_size
            t_end = (i + 1) * bucket_size
            mask = (exec_times >= t_start) & (exec_times < t_end)
            bucket_volumes[i] = np.sum(exec_sizes[mask])  # signed volume

            idx_start = min(t_start, len(mid_prices) - 1)
            idx_end = min(t_end, len(mid_prices) - 1)
            bucket_price_changes[i] = mid_prices[idx_end] - mid_prices[idx_start]

        # Regress: delta_mid ~ beta * sign(volume) * |volume|^alpha
        signed_vol = np.sign(bucket_volumes) * np.abs(bucket_volumes)
        valid = np.abs(signed_vol) > 0
        if np.sum(valid) > 5:
            slope, intercept, r_value, p_value, std_err = linregress(
                signed_vol[valid], bucket_price_changes[valid]
            )
            # eta = beta * sigma_daily / sqrt(252)
            sigma_daily = np.std(bucket_price_changes[bucket_price_changes != 0]) * np.sqrt(
                252 * n_buckets / (n_seconds / 23400)
            ) if np.any(bucket_price_changes != 0) else config.DEFAULT_SIGMA
            eta = abs(slope) * sigma_daily / np.sqrt(252) if abs(slope) > 0 else config.DEFAULT_ETA

    # 2. Permanent impact gamma
    gamma = config.DEFAULT_GAMMA

    if len(exec_times) > 10:
        # For each trade execution, track price 15 minutes (900s) later
        perm_impacts = []
        trade_abs_sizes = []

        for i in range(len(exec_times)):
            t_trade = exec_times[i]
            t_later = t_trade + 900  # 15 minutes later
            idx_trade = min(int(t_trade), len(mid_prices) - 1)
            idx_later = min(int(t_later), len(mid_prices) - 1)

            if idx_later < len(mid_prices) - 1:
                permanent_impact = (mid_prices[idx_later] - mid_prices[idx_trade]) * np.sign(
                    exec_sizes[i]
                )
                perm_impacts.append(permanent_impact)
                trade_abs_sizes.append(abs(exec_sizes[i]))

        if len(perm_impacts) > 10:
            perm_impacts = np.array(perm_impacts)
            trade_abs_sizes = np.array(trade_abs_sizes)
            slope, _, _, _, _ = linregress(trade_abs_sizes, perm_impacts)
            S0 = mid_prices[0]
            gamma = abs(slope) / S0 if abs(slope) > 0 else config.DEFAULT_GAMMA

    # 3. OW resilience rho
    rho = config.DEFAULT_RHO

    if len(exec_times) > 50:
        # After each large trade (>10x median), fit spread recovery
        median_size = np.median(np.abs(exec_sizes))
        large_mask = np.abs(exec_sizes) > 10 * median_size
        large_indices = np.where(large_mask)[0]

        taus = [1, 2, 5, 10, 30, 60]
        recovery_data = []

        for idx in large_indices[:50]:  # limit for performance
            t_trade = exec_times[idx]
            idx_trade = min(int(t_trade), len(spreads) - 1)
            spread_0 = spreads[idx_trade]

            for tau in taus:
                idx_tau = min(idx_trade + tau, len(spreads) - 1)
                if idx_tau < len(spreads):
                    recovery_data.append((tau, spreads[idx_tau], spread_0))

        if len(recovery_data) > 10:
            recovery_arr = np.array(recovery_data)
            tau_vals = recovery_arr[:, 0]
            spread_tau = recovery_arr[:, 1]
            spread_0_vals = recovery_arr[:, 2]
            spread_inf = np.mean(spreads)

            def exp_recovery(tau: np.ndarray, rho_fit: float) -> np.ndarray:
                return spread_inf + (spread_0_vals - spread_inf) * np.exp(-rho_fit * tau)

            try:
                popt, _ = curve_fit(exp_recovery, tau_vals, spread_tau, p0=[0.1], maxfev=5000)
                rho = max(abs(popt[0]) * 60, 0.1)  # convert per-second to per-minute
            except (RuntimeError, ValueError):
                pass

    # 4. Volatility sigma
    # Compute log returns of mid_price at 5-min intervals
    bucket_prices = mid_prices[::bucket_size]
    if len(bucket_prices) > 2:
        log_returns = np.diff(np.log(bucket_prices))
        sigma = np.std(log_returns) * np.sqrt(252 * 78)  # 78 = 5-min bars per 6.5hr day
    else:
        sigma = config.DEFAULT_SIGMA

    # Spread statistics
    spread_mean = float(np.mean(spreads))
    spread_std = float(np.std(spreads))

    # Depth mean — approximate from trade sizes
    depth_mean = float(np.mean(np.abs(exec_sizes)) * 10) if len(exec_sizes) > 0 else config.DEFAULT_DEPTH_MEAN

    # OFI autocorrelation
    if len(ofi) > 2:
        ofi_autocorr = float(np.corrcoef(ofi[:-1], ofi[1:])[0, 1])
    else:
        ofi_autocorr = config.DEFAULT_OFI_AUTOCORR

    result = {
        "eta": float(eta),
        "gamma": float(gamma),
        "rho": float(rho),
        "sigma": float(sigma),
        "spread_mean": float(spread_mean),
        "spread_std": float(spread_std),
        "depth_mean": float(depth_mean),
        "ofi_autocorr": float(ofi_autocorr),
    }

    # Save to calibration file
    cal_path = Path(config.CALIBRATION_FILE)
    cal_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cal_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Calibration complete: {result}")
    return result


def load_or_calibrate() -> dict:
    """Load params.json if fresh (<7 days), otherwise run calibration.

    Returns:
        Calibrated parameters dictionary.
    """
    import time

    cal_path = Path(config.CALIBRATION_FILE)

    if cal_path.exists():
        age_days = (time.time() - cal_path.stat().st_mtime) / 86400
        if age_days < 7:
            with open(cal_path) as f:
                params = json.load(f)
            logger.info(f"Loaded cached calibration (age={age_days:.1f} days)")
            return params

    # Run calibration
    from data.lobster_parser import parse_lobster_safe
    lob_data = parse_lobster_safe(config.DATA_DIR)
    return calibrate_from_lobster(lob_data)
