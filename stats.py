"""
Summary statistics for transactions.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List

from data import Transaction


def total_spending(transactions: List[Transaction]) -> float:
    """Total spending (sum of absolute amounts for expenses)."""
    return sum(abs(t.amount) for t in transactions if t.amount < 0)


def by_category(transactions: List[Transaction]) -> dict:
    """Spending totals per category."""
    totals = defaultdict(float)
    for t in transactions:
        if t.amount < 0:
            totals[t.category] += abs(t.amount)
    return dict(totals)


def by_period(transactions: List[Transaction], period: str) -> dict:
    """
    Spending totals by time period.
    period: 'daily', 'weekly', or 'monthly'
    Returns dict mapping period key (e.g. '2026-03') to total.
    """
    totals = defaultdict(float)
    for t in transactions:
        if t.amount >= 0:
            continue
        try:
            dt = datetime.strptime(t.date, "%Y-%m-%d")
        except ValueError:
            continue
        if period == "daily":
            key = t.date
        elif period == "weekly":
            # ISO week
            key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
        else:  # monthly
            key = f"{dt.year}-{dt.month:02d}"
        totals[key] += abs(t.amount)
    return dict(totals)


def top_categories(transactions: List[Transaction], n: int = 3) -> List[tuple]:
    """Top n categories by spending. Returns list of (category, amount)."""
    cat_totals = by_category(transactions)
    sorted_items = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    return sorted_items[:n]


def trend_last_n_days(transactions: List[Transaction], n: int) -> float:
    """Total spending in the last n days (from most recent transaction date)."""
    if not transactions:
        return 0.0
    dates = []
    for t in transactions:
        try:
            dates.append(datetime.strptime(t.date, "%Y-%m-%d"))
        except ValueError:
            continue
    if not dates:
        return 0.0
    cutoff = max(dates).date() - timedelta(days=n)
    total = 0.0
    for t in transactions:
        try:
            dt = datetime.strptime(t.date, "%Y-%m-%d").date()
            if dt >= cutoff:
                total += abs(t.amount) if t.amount < 0 else 0
        except ValueError:
            continue
    return total


def format_summary(transactions: List[Transaction]) -> str:
    """Format a summary for display."""
    lines = []
    total = total_spending(transactions)
    lines.append(f"  Total spending: HK$ {total:.2f}")

    cat_totals = by_category(transactions)
    if cat_totals:
        lines.append("  By category:")
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"    {cat}: HK$ {amt:.2f}")

    top = top_categories(transactions)
    if top:
        lines.append("  Top 3 categories:")
        for cat, amt in top:
            lines.append(f"    {cat}: HK$ {amt:.2f}")

    t7 = trend_last_n_days(transactions, 7)
    t30 = trend_last_n_days(transactions, 30)
    lines.append(f"  Last 7 days: HK$ {t7:.2f}")
    lines.append(f"  Last 30 days: HK$ {t30:.2f}")

    return "\n".join(lines) if lines else "  No transactions."
