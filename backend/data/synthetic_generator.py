"""Generate realistic synthetic LOB data matching the parse_lobster dict format."""

from __future__ import annotations

import numpy as np

from config import config


def generate_synthetic_lob(
    n_seconds: int = 23400,  # 6.5 hours of trading
    eta: float = config.DEFAULT_ETA,
    gamma: float = config.DEFAULT_GAMMA,
    rho: float = config.DEFAULT_RHO,
    sigma: float = config.DEFAULT_SIGMA,
    spread_mean: float = config.DEFAULT_SPREAD_MEAN,
    spread_std: float = config.DEFAULT_SPREAD_STD,
    depth_mean: float = config.DEFAULT_DEPTH_MEAN,
    seed: int = 42,
) -> dict:
    """Generate realistic synthetic LOB data.

    Simulates:
      - mid_price: geometric Brownian motion with sigma=DEFAULT_SIGMA/sqrt(252*23400)
      - spreads: truncated normal with spread_mean, spread_std, min=0.0001
      - OFI: AR(1) process with autocorr=0.3, N(0,1) innovations
      - Executions: Poisson process with rate=3 trades/second
        - sizes: log-normal with mean=200 shares, std=500 shares
        - direction: 60% correlated with OFI (sign of OFI -> direction with probability 0.6)

    Args:
        n_seconds: Number of seconds to simulate.
        eta: Temporary impact coefficient.
        gamma: Permanent impact coefficient.
        rho: OW resilience parameter.
        sigma: Daily volatility.
        spread_mean: Mean spread as fraction of price.
        spread_std: Std of spread.
        depth_mean: Mean order book depth.
        seed: Random seed.

    Returns:
        Dictionary matching parse_lobster output format.
    """
    rng = np.random.default_rng(seed)

    # Mid-price: GBM
    S0 = 100.0
    sigma_per_sec = sigma / np.sqrt(252 * 23400)
    log_returns = rng.normal(0, sigma_per_sec, n_seconds)
    mid_prices = S0 * np.exp(np.cumsum(log_returns))

    # Spreads: truncated normal
    spreads = np.clip(
        rng.normal(spread_mean, spread_std, n_seconds),
        0.0001,
        None,
    )

    # OFI: AR(1) process
    ofi_autocorr = 0.3
    ofi = np.zeros(n_seconds)
    for t in range(1, n_seconds):
        ofi[t] = ofi_autocorr * ofi[t - 1] + np.sqrt(1 - ofi_autocorr**2) * rng.normal(0, 1)

    # Executions: Poisson arrivals, ~3 per second
    n_trades = rng.poisson(3, n_seconds)
    exec_times_list = []
    exec_sizes_list = []
    exec_prices_list = []

    for t in range(n_seconds):
        n = n_trades[t]
        if n == 0:
            continue
        times = t + rng.uniform(0, 1, n)
        sizes = np.clip(rng.lognormal(np.log(200), np.log(2.5), n), 1, 10000).astype(int)

        # Direction: 60% correlated with OFI sign
        ofi_sign = np.sign(ofi[t]) if ofi[t] != 0 else 1
        directions = np.where(
            rng.random(n) < 0.6,
            ofi_sign,
            np.where(rng.random(n) < 0.5, 1, -1),
        )
        signed_sizes = sizes * directions

        # Execution prices: mid +/- half spread
        prices = mid_prices[t] + directions * spreads[t] * mid_prices[t] / 2

        exec_times_list.append(times)
        exec_sizes_list.append(signed_sizes)
        exec_prices_list.append(prices)

    exec_times = np.concatenate(exec_times_list) if exec_times_list else np.array([])
    exec_sizes = np.concatenate(exec_sizes_list) if exec_sizes_list else np.array([])
    exec_prices = np.concatenate(exec_prices_list) if exec_prices_list else np.array([])

    # Sort by time
    sort_idx = np.argsort(exec_times)
    exec_times = exec_times[sort_idx]
    exec_sizes = exec_sizes[sort_idx]
    exec_prices = exec_prices[sort_idx]

    return {
        "mid_prices": mid_prices.astype(np.float64),
        "spreads": spreads.astype(np.float64),
        "ofi": ofi.astype(np.float64),
        "exec_times": exec_times.astype(np.float64),
        "exec_sizes": exec_sizes.astype(np.float64),
        "exec_prices": exec_prices.astype(np.float64),
        "n_seconds": n_seconds,
    }
