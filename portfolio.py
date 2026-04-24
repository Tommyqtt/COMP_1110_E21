"""
MockWealth - portfolio allocation and Monte Carlo simulation.
Educational simulator only; not real investment advice.

"""

import csv
import random
import statistics
from pathlib import Path
from typing import Dict, List, Optional

ASSETS_FILE = "assets.csv"

# Rule-based allocation: risk_level -> {asset_class: weight}. Weights sum to 1.0.
RISK_ALLOCATION: Dict[int, Dict[str, float]] = {
    1: {"cash": 0.20, "bonds": 0.70, "balanced": 0.10, "equity": 0.00, "high_risk": 0.00},
    2: {"cash": 0.15, "bonds": 0.55, "balanced": 0.20, "equity": 0.10, "high_risk": 0.00},
    3: {"cash": 0.10, "bonds": 0.40, "balanced": 0.20, "equity": 0.30, "high_risk": 0.00},
    4: {"cash": 0.05, "bonds": 0.25, "balanced": 0.20, "equity": 0.45, "high_risk": 0.05},
    5: {"cash": 0.05, "bonds": 0.10, "balanced": 0.15, "equity": 0.55, "high_risk": 0.15},
}


def load_assets(path: str) -> List[Dict]:
    """Load the mock asset universe from CSV; fall back to defaults."""
    p = Path(path)
    if not p.exists():
        return _default_assets()
    assets: List[Dict] = []
    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                assets.append({
                    "asset_id": row.get("asset_id", ""),
                    "asset_class": row.get("asset_class", "").lower(),
                    "risk_level": int(row.get("risk_level", 1)),
                    "mu_monthly": float(row.get("mu_monthly", 0)),
                    "sigma_monthly": float(row.get("sigma_monthly", 0)),
                    "fee_rate": float(row.get("fee_rate", 0)),
                })
            except (ValueError, KeyError):
                continue
    return assets if assets else _default_assets()


def _default_assets() -> List[Dict]:
    """Built-in mock assets used when assets.csv is missing or empty."""
    return [
        {"asset_id": "CASH", "asset_class": "cash", "risk_level": 1,
         "mu_monthly": 0.001, "sigma_monthly": 0.001, "fee_rate": 0},
        {"asset_id": "BOND_GOVT", "asset_class": "bonds", "risk_level": 1,
         "mu_monthly": 0.003, "sigma_monthly": 0.01, "fee_rate": 0.0002},
        {"asset_id": "BALANCED", "asset_class": "balanced", "risk_level": 3,
         "mu_monthly": 0.005, "sigma_monthly": 0.02, "fee_rate": 0.0005},
        {"asset_id": "EQUITY", "asset_class": "equity", "risk_level": 4,
         "mu_monthly": 0.008, "sigma_monthly": 0.05, "fee_rate": 0.001},
        {"asset_id": "HIGH_RISK", "asset_class": "high_risk", "risk_level": 5,
         "mu_monthly": 0.012, "sigma_monthly": 0.08, "fee_rate": 0.002},
    ]


def get_allocation(risk_level: int) -> Dict[str, float]:
    """Return the canned allocation for risk level 1-5 (clamped)."""
    level = max(1, min(5, int(risk_level)))
    return dict(RISK_ALLOCATION[level])


def normalize_allocation(allocation: Dict[str, float]) -> Dict[str, float]:
    """Rescale user-supplied weights to sum to 1.0; drops negatives."""
    cleaned = {k: max(0.0, float(v)) for k, v in allocation.items()}
    total = sum(cleaned.values())
    if total <= 0:
        return {"cash": 1.0}
    return {k: v / total for k, v in cleaned.items()}


def _percentile(sorted_vals: List[float], pct: float) -> float:
    """Plain percentile on a sorted list (0 <= pct <= 100)."""
    if not sorted_vals:
        return 0.0
    k = int(pct / 100 * (len(sorted_vals) - 1))
    k = max(0, min(k, len(sorted_vals) - 1))
    return sorted_vals[k]


def simulate(
    initial: float,
    monthly_contribution: float,
    months: int,
    allocation: Dict[str, float],
    assets: List[Dict],
    num_paths: int = 1000,
    seed: Optional[int] = None,
) -> Dict[str, float]:
    """
    Monte Carlo simulation over num_paths trajectories.
    Pass seed for deterministic, reproducible runs.
    """
    rng = random.Random(seed) if seed is not None else random

    alloc = normalize_allocation(allocation)
    asset_by_class = {a["asset_class"]: a for a in assets}

    final_values: List[float] = []
    max_drawdowns: List[float] = []

    for _ in range(num_paths):
        value = initial
        peak = value
        max_dd = 0.0
        for _m in range(months):
            monthly_return = 0.0
            for ac, weight in alloc.items():
                if weight <= 0:
                    continue
                a = asset_by_class.get(ac)
                if not a:
                    continue
                ret = rng.gauss(a["mu_monthly"], a["sigma_monthly"])
                ret -= a["fee_rate"]
                monthly_return += weight * ret
            value = value * (1 + monthly_return) + monthly_contribution
            if value > peak:
                peak = value
            if peak > 0:
                dd = (peak - value) / peak
                if dd > max_dd:
                    max_dd = dd
        final_values.append(value)
        max_drawdowns.append(max_dd)

    final_values.sort()
    n = len(final_values)
    if n == 0:
        return {
            "p10": 0.0, "p50": 0.0, "p90": 0.0, "loss_prob": 0.0,
            "var_5pct": 0.0, "max_drawdown_avg": 0.0,
            "volatility": 0.0, "sharpe_like": 0.0, "annualized_return": 0.0,
        }

    p10 = _percentile(final_values, 10)
    p50 = _percentile(final_values, 50)
    p90 = _percentile(final_values, 90)
    p5 = _percentile(final_values, 5)

    total_in = initial + monthly_contribution * months
    loss_prob = sum(1 for v in final_values if v < total_in) / n
    var_5pct = max(0.0, total_in - p5)

    vol = statistics.pstdev(final_values) if n >= 2 else 0.0
    sharpe_like = (p50 - total_in) / vol if vol > 0 else 0.0
    max_dd_avg = sum(max_drawdowns) / len(max_drawdowns) if max_drawdowns else 0.0

    annualized = 0.0
    if months > 0 and p50 > 0:
        if initial > 0 and monthly_contribution == 0:
            annualized = (p50 / initial) ** (12.0 / months) - 1
        elif total_in > 0:
            annualized = (p50 / total_in) ** (12.0 / months) - 1

    return {
        "p10": p10,
        "p50": p50,
        "p90": p90,
        "loss_prob": loss_prob,
        "var_5pct": var_5pct,
        "max_drawdown_avg": max_dd_avg,
        "volatility": vol,
        "sharpe_like": sharpe_like,
        "annualized_return": annualized,
    }


def run_portfolio_menu() -> None:
    """Interactive CLI portfolio simulation with full risk metric output."""
    assets = load_assets(ASSETS_FILE)
    print("\n--- MockWealth Portfolio Simulator ---")
    print("(Educational only - not investment advice)")
    try:
        initial = float(input("Initial deposit (HKD): ").strip())
        monthly = float(input("Monthly contribution (HKD): ").strip())
        months = int(input("Time horizon (months): ").strip())
        risk = int(input("Risk tolerance 1-5 (1=conservative, 5=aggressive): ").strip())
    except ValueError:
        print("  Invalid input.")
        return
    if initial < 0 or monthly < 0 or months <= 0 or risk < 1 or risk > 5:
        print("  Invalid values.")
        return

    seed_raw = input("Random seed (blank for random): ").strip()
    seed: Optional[int] = None
    if seed_raw:
        try:
            seed = int(seed_raw)
        except ValueError:
            print("  Invalid seed; using random.")

    alloc = get_allocation(risk)
    print("\n  Allocation:")
    for ac, w in alloc.items():
        if w > 0:
            print(f"    {ac}: {w * 100:.0f}%")

    result = simulate(initial, monthly, months, alloc, assets, seed=seed)
    total_in = initial + monthly * months

    print("\n  Simulated outcomes (1000 paths):")
    print(f"    P10 (pessimistic):    HK$ {result['p10']:,.2f}")
    print(f"    P50 (typical):        HK$ {result['p50']:,.2f}")
    print(f"    P90 (optimistic):     HK$ {result['p90']:,.2f}")
    print(f"    Total contributed:    HK$ {total_in:,.2f}")
    print("\n  Risk metrics:")
    print(f"    Loss probability:     {result['loss_prob'] * 100:.1f}%")
    print(f"    5% VaR (loss):        HK$ {result['var_5pct']:,.2f}")
    print(f"    Avg max drawdown:     {result['max_drawdown_avg'] * 100:.1f}%")
    print(f"    Volatility (stdev):   HK$ {result['volatility']:,.2f}")
    print(f"    Sharpe-like ratio:    {result['sharpe_like']:.3f}")
    print(f"    Annualized (median):  {result['annualized_return'] * 100:.2f}%")
