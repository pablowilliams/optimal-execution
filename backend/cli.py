"""Typer CLI entry point for the Optimal Execution Research Platform."""

from __future__ import annotations

import json
import logging
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from config import config

app = typer.Typer(name="exec-research", help="Optimal Trade Execution Research Platform")
console = Console()
logging.basicConfig(level=logging.INFO)


@app.command()
def calibrate() -> None:
    """Run calibration from LOBSTER data (or synthetic fallback), print params."""
    from calibration.calibrate import load_or_calibrate

    with console.status("[bold gold1]Calibrating from market data..."):
        params = load_or_calibrate()

    table = Table(title="Calibrated Parameters", style="bold")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")

    for key, val in params.items():
        table.add_row(key, f"{val:.6f}" if isinstance(val, float) else str(val))

    console.print(table)


@app.command()
def run(
    strategy: str = typer.Option("ac", help="Strategy: ac|ow|ppo|twap|vwap|all"),
    X: int = typer.Option(10000, help="Shares to liquidate"),
    T: int = typer.Option(30, help="Time horizon (minutes)"),
    N: int = typer.Option(30, help="Number of time steps"),
    lambda_risk: float = typer.Option(1e-6, "--lambda", help="Risk aversion"),
) -> None:
    """Run a strategy and print results."""
    from calibration.calibrate import load_or_calibrate

    params = load_or_calibrate()

    eta = params.get("eta", config.DEFAULT_ETA)
    gamma = params.get("gamma", config.DEFAULT_GAMMA)
    sigma = params.get("sigma", config.DEFAULT_SIGMA)
    rho = params.get("rho", config.DEFAULT_RHO)
    depth_D = params.get("depth_mean", config.DEFAULT_DEPTH_MEAN)

    results = {}

    if strategy in ("ac", "all"):
        from strategies.almgren_chriss import compute_ac_trajectory
        traj = compute_ac_trajectory(X, T, N, lambda_risk, eta, gamma, sigma)
        results["AC"] = traj
        console.print(f"[gold1]AC[/] E[IS]={traj['E_IS_bps']:.2f} bps, kappa={traj['kappa']:.6f}")

    if strategy in ("ow", "all"):
        from strategies.obizhaeva_wang import compute_ow_trajectory
        traj = compute_ow_trajectory(X, T, N, lambda_risk, sigma, rho, depth_D)
        results["OW"] = traj
        console.print(f"[gold1]OW[/] IS_analytical={traj['IS_bps_analytical']:.2f} bps, v0={traj['v0']:.0f}")

    if strategy in ("ppo", "all"):
        from rl.evaluate import evaluate_ppo
        try:
            traj = evaluate_ppo(params, X, T, N, lambda_risk)
            results["PPO"] = traj
            console.print(f"[gold1]PPO[/] IS_realised={traj['IS_bps_realised']:.2f} bps")
        except FileNotFoundError as e:
            console.print(f"[red]PPO model not found.[/] Train first with: exec-research train")

    if strategy in ("twap", "all"):
        from strategies.twap import compute_twap_trajectory
        traj = compute_twap_trajectory(X, N)
        results["TWAP"] = traj
        console.print("[gold1]TWAP[/] uniform schedule computed")

    if strategy in ("vwap", "all"):
        from strategies.vwap import compute_vwap_trajectory
        traj = compute_vwap_trajectory(X, N)
        results["VWAP"] = traj
        console.print("[gold1]VWAP[/] volume-weighted schedule computed")


@app.command()
def compare(
    n_episodes: int = typer.Option(500, help="Number of episodes"),
) -> None:
    """Run full comparison across all strategies, print rich table."""
    from calibration.calibrate import load_or_calibrate
    from evaluation.compare import compare_strategies

    params = load_or_calibrate()

    with console.status(f"[bold gold1]Running {n_episodes}-episode comparison..."):
        result = compare_strategies(params, n_episodes=n_episodes)

    table = Table(title="Strategy Comparison", style="bold")
    table.add_column("Strategy", style="cyan")
    table.add_column("E[IS] (bps)", style="green")
    table.add_column("Std[IS]", style="yellow")
    table.add_column("Sharpe-of-IS", style="magenta")
    table.add_column("VWAP Slip", style="blue")
    table.add_column("vs TWAP %", style="red")

    strats = result.get("strategies", {})
    twap_is = strats.get("twap", {}).get("mean_IS", 1)

    for name in ["ac", "ow", "ppo", "twap", "vwap"]:
        if name in strats:
            s = strats[name]
            improvement = (twap_is - s["mean_IS"]) / abs(twap_is) * 100 if twap_is != 0 else 0
            table.add_row(
                name.upper(),
                f"{s['mean_IS']:.2f}",
                f"{s['std_IS']:.2f}",
                f"{s['sharpe_IS']:.3f}",
                f"{s['VWAP_slippage_bps']:.2f}",
                f"{improvement:+.1f}%",
            )

    console.print(table)


@app.command()
def train(
    timesteps: int = typer.Option(1_000_000, help="Total training timesteps"),
) -> None:
    """Train PPO agent with rich progress bar."""
    from calibration.calibrate import load_or_calibrate
    from rl.train import train_ppo

    params = load_or_calibrate()

    console.print(f"[bold gold1]Training PPO for {timesteps:,} timesteps...[/]")
    model_path = train_ppo(params, total_timesteps=timesteps)
    console.print(f"[green]Model saved to {model_path}[/]")


@app.command()
def serve(
    port: int = typer.Option(8000, help="Server port"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
) -> None:
    """Start uvicorn server."""
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)


if __name__ == "__main__":
    app()
