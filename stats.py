"""
Summary statistics
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


def average_daily_spending(transactions: List[Transaction]) -> float:
    """Average spending per active day (days that have at least one expense)."""
    daily = by_period(transactions, "daily")
    if not daily:
        return 0.0
    return sum(daily.values()) / len(daily)


def format_summary(transactions: List[Transaction]) -> str:
    """
    Format a comprehensive summary for CLI display.

    """
    if not transactions:
        return "  No transactions loaded."

    lines = []
    sep = "  " + "-" * 36

    # Overall total
    total = total_spending(transactions)
    lines.append(f"  Total spending:      HK$ {total:>10.2f}")
    lines.append(f"  Avg per active day:  HK$ {average_daily_spending(transactions):>10.2f}")
    lines.append(sep)

    # By category
    cat_totals = by_category(transactions)
    if cat_totals:
        lines.append("  By category:")
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (amt / total * 100) if total else 0
            lines.append(f"    {cat:<18} HK$ {amt:>8.2f}  ({pct:.1f}%)")
    lines.append(sep)

    # Top 3 categories
    top = top_categories(transactions)
    if top:
        lines.append("  Top 3 categories:")
        for i, (cat, amt) in enumerate(top, 1):
            lines.append(f"    {i}. {cat:<16} HK$ {amt:>8.2f}")
    lines.append(sep)

    # Monthly breakdown (most recent 3 months)
    monthly = by_period(transactions, "monthly")
    if monthly:
        lines.append("  Monthly breakdown (recent 3 months):")
        for key in sorted(monthly.keys())[-3:]:
            lines.append(f"    {key}    HK$ {monthly[key]:>10.2f}")
    lines.append(sep)

    # Weekly breakdown (most recent 4 weeks)
    weekly = by_period(transactions, "weekly")
    if weekly:
        lines.append("  Weekly breakdown (recent 4 weeks):")
        for key in sorted(weekly.keys())[-4:]:
            lines.append(f"    {key}   HK$ {weekly[key]:>10.2f}")
    lines.append(sep)

    # Trend windows 
    t7 = trend_last_n_days(transactions, 7)
    t30 = trend_last_n_days(transactions, 30)
    lines.append(f"  Last  7 days:        HK$ {t7:>10.2f}")
    lines.append(f"  Last 30 days:        HK$ {t30:>10.2f}")

    return "\n".join(lines)
