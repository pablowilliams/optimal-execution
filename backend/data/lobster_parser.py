"""Parse LOBSTER message + orderbook CSVs into structured DataFrames."""

from __future__ import annotations

import glob
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from config import config

logger = logging.getLogger(__name__)


def parse_lobster(data_dir: str) -> dict:
    """Load AAPL LOBSTER message + orderbook CSVs and return structured arrays.

    Args:
        data_dir: Directory containing the LOBSTER CSV files.

    Returns:
        Dictionary with keys: mid_prices, spreads, ofi, exec_times,
        exec_sizes, exec_prices, n_seconds.
    """
    msg_files = sorted(glob.glob(str(Path(data_dir) / "AAPL_*_message_*.csv")))
    ob_files = sorted(glob.glob(str(Path(data_dir) / "AAPL_*_orderbook_*.csv")))

    if not msg_files or not ob_files:
        raise FileNotFoundError(f"No LOBSTER files found in {data_dir}")

    # Message file columns (no header):
    # Time(ns), EventType, OrderID, Size, Price, Direction
    msg = pd.read_csv(
        msg_files[0],
        header=None,
        names=["Time", "EventType", "OrderID", "Size", "Price", "Direction"],
    )

    # Orderbook file columns (no header): 20 cols
    # AskPrice1, AskSize1, BidPrice1, BidSize1, ..., AskPrice10, AskSize10, BidPrice10, BidSize10
    ob_cols = []
    for i in range(1, 11):
        ob_cols.extend([f"AskPrice{i}", f"AskSize{i}", f"BidPrice{i}", f"BidSize{i}"])
    ob = pd.read_csv(ob_files[0], header=None, names=ob_cols)

    # All prices in integer cents (divide by 10000)
    msg["Price"] = msg["Price"] / 10000.0
    for col in ob.columns:
        if "Price" in col:
            ob[col] = ob[col] / 10000.0

    # Convert time from nanoseconds since midnight to seconds
    msg["Time"] = msg["Time"] / 1e9

    # Compute mid-price
    ob["mid_price"] = (ob["BidPrice1"] + ob["AskPrice1"]) / 2.0

    # Compute spread (in cents, convert to fraction)
    ob["spread"] = (ob["AskPrice1"] - ob["BidPrice1"])

    # Compute OFI = (BidSize1 - AskSize1) / (BidSize1 + AskSize1)
    total = ob["BidSize1"] + ob["AskSize1"]
    ob["ofi"] = np.where(total > 0, (ob["BidSize1"] - ob["AskSize1"]) / total, 0.0)

    # Attach time to orderbook
    ob["Time"] = msg["Time"].values

    # Resample to 1-second intervals (forward fill)
    ob["time_sec"] = ob["Time"].astype(int)
    resampled = ob.groupby("time_sec").last().reset_index()

    n_seconds = int(resampled["time_sec"].max() - resampled["time_sec"].min()) + 1
    full_range = pd.DataFrame({"time_sec": range(int(resampled["time_sec"].min()),
                                                  int(resampled["time_sec"].min()) + n_seconds)})
    resampled = full_range.merge(resampled, on="time_sec", how="left").ffill().bfill()

    mid_prices = resampled["mid_price"].values
    spreads = resampled["spread"].values / mid_prices  # as fraction of mid
    ofi = resampled["ofi"].values

    # Isolate execution events (EventType 4 or 5): actual trades
    executions = msg[msg["EventType"].isin([4, 5])].copy()
    exec_times = executions["Time"].values
    exec_sizes = executions["Size"].values * np.where(executions["Direction"] == 1, 1, -1)
    exec_prices = executions["Price"].values

    return {
        "mid_prices": mid_prices.astype(np.float64),
        "spreads": spreads.astype(np.float64),
        "ofi": ofi.astype(np.float64),
        "exec_times": exec_times.astype(np.float64),
        "exec_sizes": exec_sizes.astype(np.float64),
        "exec_prices": exec_prices.astype(np.float64),
        "n_seconds": n_seconds,
    }


def parse_lobster_safe(data_dir: str) -> dict:
    """Wrap parse_lobster in try/except. Falls back to synthetic if parsing fails.

    Args:
        data_dir: Directory containing the LOBSTER CSV files.

    Returns:
        Parsed LOBSTER data dict, or synthetic data if files missing / parse error.
    """
    try:
        return parse_lobster(data_dir)
    except (FileNotFoundError, Exception) as e:
        logger.warning(f"LOBSTER parsing failed: {e}. Falling back to synthetic data.")
        from data.synthetic_generator import generate_synthetic_lob
        return generate_synthetic_lob()
