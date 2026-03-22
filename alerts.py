"""
Rule-based alerts for budget and spending.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List

from data import BudgetRule, Transaction
from stats import by_category, total_spending


def _parse_date(date_str: str):
    """Parse date or return None."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def check_daily_category_cap(
    transactions: List[Transaction],
    rules: List[BudgetRule]
) -> List[str]:
    """Check daily category caps."""
    messages = []
    daily_by_cat = defaultdict(lambda: defaultdict(float))
    for t in transactions:
        if t.amount >= 0:
            continue
        dt = _parse_date(t.date)
        if dt:
            daily_by_cat[t.category][t.date] += abs(t.amount)

    for r in rules:
        if r.period != "daily":
            continue
        for date_key, total in daily_by_cat.get(r.category, {}).items():
            if total > r.threshold:
                messages.append(
                    f"[Alert] {r.category} exceeded daily cap (HK$ {r.threshold:.0f}) "
                    f"on {date_key}: spent HK$ {total:.2f}"
                )
    return messages


def check_weekly_category_cap(
    transactions: List[Transaction],
    rules: List[BudgetRule]
) -> List[str]:
    """Check weekly category caps."""
    messages = []
    weekly_by_cat = defaultdict(lambda: defaultdict(float))
    for t in transactions:
        if t.amount >= 0:
            continue
        dt = _parse_date(t.date)
        if dt:
            week_key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
            weekly_by_cat[t.category][week_key] += abs(t.amount)

    for r in rules:
        if r.period != "weekly":
            continue
        for week_key, total in weekly_by_cat.get(r.category, {}).items():
            if total > r.threshold:
                messages.append(
                    f"[Alert] {r.category} exceeded weekly cap (HK$ {r.threshold:.0f}) "
                    f"in {week_key}: spent HK$ {total:.2f}"
                )
    return messages


def check_monthly_category_cap(
    transactions: List[Transaction],
    rules: List[BudgetRule]
) -> List[str]:
    """Check monthly category caps."""
    messages = []
    monthly_by_cat = defaultdict(lambda: defaultdict(float))
    for t in transactions:
        if t.amount >= 0:
            continue
        dt = _parse_date(t.date)
        if dt:
            month_key = f"{dt.year}-{dt.month:02d}"
            monthly_by_cat[t.category][month_key] += abs(t.amount)

    for r in rules:
        if r.period != "monthly":
            continue
        for month_key, total in monthly_by_cat.get(r.category, {}).items():
            if total > r.threshold:
                messages.append(
                    f"[Alert] {r.category} exceeded monthly cap (HK$ {r.threshold:.0f}) "
                    f"in {month_key}: spent HK$ {total:.2f}"
                )
    return messages


def check_percentage_threshold(
    transactions: List[Transaction],
    category: str,
    pct_threshold: float
) -> List[str]:
    """Alert if a category exceeds pct_threshold of total spending."""
    total = total_spending(transactions)
    if total <= 0:
        return []
    cat_totals = by_category(transactions)
    cat_spend = cat_totals.get(category, 0)
    pct = 100 * cat_spend / total
    if pct > pct_threshold:
        return [
            f"[Alert] {category} is {pct:.1f}% of total spending "
            f"(threshold {pct_threshold:.0f}%)"
        ]
    return []


def check_uncategorized(transactions: List[Transaction]) -> List[str]:
    """Warn about uncategorized or 'other' transactions."""
    uncategorized = [t for t in transactions if not t.category or t.category == "other"]
    if len(uncategorized) > 5:
        return [
            f"[Alert] {len(uncategorized)} transactions are uncategorized or in 'other'. "
            "Consider reviewing for better tracking."
        ]
    return []


def run_all_alerts(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    pct_rules: List[tuple] = None
) -> List[str]:
    """
    Run all alert rules. pct_rules: list of (category, threshold) e.g. [("transport", 30)].
    """
    messages = []
    messages.extend(check_daily_category_cap(transactions, rules))
    messages.extend(check_weekly_category_cap(transactions, rules))
    messages.extend(check_monthly_category_cap(transactions, rules))
    if pct_rules:
        for cat, thresh in pct_rules:
            messages.extend(check_percentage_threshold(transactions, cat, thresh))
    messages.extend(check_uncategorized(transactions))
    return messages
