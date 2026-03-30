"""Default parameters, paths, and constants for the optimal execution platform."""

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class Config:
    """Global configuration — all values overridable via environment variables."""

    # Paths
    DATA_DIR: str = os.getenv("DATA_DIR", "./data/raw")
    CACHE_DIR: str = os.getenv("CACHE_DIR", "./data/cache")
    MODELS_DIR: str = os.getenv("MODELS_DIR", "./rl/models")
    CALIBRATION_FILE: str = os.getenv("CALIBRATION_FILE", "./calibration/params.json")

    # Default calibration params (AAPL typical values, used if LOBSTER absent)
    DEFAULT_ETA: float = 0.0023          # temporary impact coefficient
    DEFAULT_GAMMA: float = 0.0008        # permanent impact coefficient
    DEFAULT_RHO: float = 10.0            # OW resilience (mean-reversion speed, per minute)
    DEFAULT_SIGMA: float = 0.015         # daily volatility (annualised / sqrt(252))
    DEFAULT_SPREAD_MEAN: float = 0.02    # mean bid-ask spread as fraction of price
    DEFAULT_SPREAD_STD: float = 0.005    # std of bid-ask spread
    DEFAULT_DEPTH_MEAN: float = 5000     # mean top-of-book depth (shares)
    DEFAULT_OFI_AUTOCORR: float = 0.3    # OFI AR(1) autocorrelation

    # Execution defaults
    DEFAULT_X: float = 10000      # shares to liquidate
    DEFAULT_T: float = 30         # time horizon (minutes)
    DEFAULT_N: int = 30           # number of time steps
    DEFAULT_LAMBDA: float = 1e-6  # risk aversion
    DEFAULT_COST_BPS: float = 10  # fixed transaction cost in bps

    # RL training
    DEFAULT_PPO_TIMESTEPS: int = 1_000_000
    RAILWAY_PPO_TIMESTEPS: int = 500_000  # reduced for Railway free tier

    # Synthetic fallback
    SYNTHETIC_FALLBACK: bool = os.getenv("SYNTHETIC_FALLBACK", "true").lower() == "true"

    def ensure_dirs(self) -> None:
        """Create necessary directories if they don't exist."""
        for d in [self.DATA_DIR, self.CACHE_DIR, self.MODELS_DIR]:
            Path(d).mkdir(parents=True, exist_ok=True)
        Path(self.CALIBRATION_FILE).parent.mkdir(parents=True, exist_ok=True)


config = Config()
