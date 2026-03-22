"""
MockWealth - Simple portfolio allocation and Monte Carlo simulation.
Educational simulator only; not real investment advice.
"""

import csv
import random
from pathlib import Path
from typing import Dict, List, Optional

ASSETS_FILE = "assets.csv"

# Rule-based allocation: risk_level -> {asset_class: weight}
# risk 1=conservative, 5=aggressive
RISK_ALLOCATION = {
    1: {"cash": 0.20, "bonds": 0.70, "balanced": 0.10, "equity": 0.00, "high_risk": 0.00},
    2: {"cash": 0.15, "bonds": 0.55, "balanced": 0.20, "equity": 0.10, "high_risk": 0.00},
    3: {"cash": 0.10, "bonds": 0.40, "balanced": 0.20, "equity": 0.30, "high_risk": 0.00},
    4: {"cash": 0.05, "bonds": 0.25, "balanced": 0.20, "equity": 0.45, "high_risk": 0.05},
    5: {"cash": 0.05, "bonds": 0.10, "balanced": 0.15, "equity": 0.55, "high_risk": 0.15},
}


def load_assets(path: str) -> List[Dict]:
    """Load mock asset universe from CSV."""
    p = Path(path)
    if not p.exists():
        return _default_assets()
    assets = []
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
    """Return built-in mock assets if CSV missing."""
    return [
        {"asset_id": "CASH", "asset_class": "cash", "risk_level": 1, "mu_monthly": 0.001, "sigma_monthly": 0.001, "fee_rate": 0},
        {"asset_id": "BOND_GOVT", "asset_class": "bonds", "risk_level": 1, "mu_monthly": 0.003, "sigma_monthly": 0.01, "fee_rate": 0.0002},
        {"asset_id": "BALANCED", "asset_class": "balanced", "risk_level": 3, "mu_monthly": 0.005, "sigma_monthly": 0.02, "fee_rate": 0.0005},
        {"asset_id": "EQUITY", "asset_class": "equity", "risk_level": 4, "mu_monthly": 0.008, "sigma_monthly": 0.05, "fee_rate": 0.001},
        {"asset_id": "HIGH_RISK", "asset_class": "high_risk", "risk_level": 5, "mu_monthly": 0.012, "sigma_monthly": 0.08, "fee_rate": 0.002},
    ]


def get_allocation(risk_level: int) -> Dict[str, float]:
    """Get allocation weights for risk level 1-5."""
    level = max(1, min(5, int(risk_level)))
    return dict(RISK_ALLOCATION[level])


def simulate(
    initial: float,
    monthly_contribution: float,
    months: int,
    allocation: Dict[str, float],
    assets: List[Dict],
    num_paths: int = 1000,
) -> Dict:
    """
    Monte Carlo simulation. Returns P10, P50, P90, loss_prob.
    """
    # Map allocation to assets by class
    asset_by_class = {a["asset_class"]: a for a in assets}
    final_values = []

    for _ in range(num_paths):
        value = initial
        for m in range(months):
            monthly_return = 0.0
            for ac, weight in allocation.items():
                if weight <= 0:
                    continue
                a = asset_by_class.get(ac)
                if not a:
                    continue
                ret = random.gauss(a["mu_monthly"], a["sigma_monthly"])
                ret -= a["fee_rate"]
                monthly_return += weight * ret
            value = value * (1 + monthly_return) + monthly_contribution
        final_values.append(value)

    final_values.sort()
    n = len(final_values)
    p10 = final_values[int(0.1 * n)] if n > 0 else 0
    p50 = final_values[int(0.5 * n)] if n > 0 else 0
    p90 = final_values[int(0.9 * n)] if n > 0 else 0
    loss_prob = sum(1 for v in final_values if v < initial + monthly_contribution * months) / n

    return {"p10": p10, "p50": p50, "p90": p90, "loss_prob": loss_prob}


def run_portfolio_menu() -> None:
    """Interactive portfolio simulation."""
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

    alloc = get_allocation(risk)
    print("\n  Allocation:")
    for ac, w in alloc.items():
        if w > 0:
            print(f"    {ac}: {w*100:.0f}%")

    result = simulate(initial, monthly, months, alloc, assets)
    print("\n  Simulated outcomes (1000 paths):")
    print(f"    P10 (pessimistic): HK$ {result['p10']:,.2f}")
    print(f"    P50 (typical):     HK$ {result['p50']:,.2f}")
    print(f"    P90 (optimistic):  HK$ {result['p90']:,.2f}")
    print(f"    Loss probability:  {result['loss_prob']*100:.1f}%")
