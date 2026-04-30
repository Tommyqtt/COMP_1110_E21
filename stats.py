"""
Summary statistics for transactions. 
"""

import calendar
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from data import BudgetRule, Transaction
from data import CATEGORIES


def total_spending(transactions: List[Transaction]) -> float:
    """Sum of absolute amounts for expenses only."""
    return sum(abs(t.amount) for t in transactions if t.amount < 0)


def by_category(transactions: List[Transaction]) -> Dict[str, float]:
    """Spending totals keyed by category."""
    totals: Dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.amount < 0:
            totals[t.category] += abs(t.amount)
    return dict(totals)


def by_period(transactions: List[Transaction], period: str) -> Dict[str, float]:
    """Spending totals keyed by period. Period is 'daily', 'weekly' or 'monthly'."""
    totals: Dict[str, float] = defaultdict(float)
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
        else:
            key = f"{dt.year}-{dt.month:02d}"
        totals[key] += abs(t.amount)
    return dict(totals)


def top_categories(transactions: List[Transaction], n: int = 3) -> List[Tuple[str, float]]:
    """Top n categories by spending; list of (category, amount)."""
    cat_totals = by_category(transactions)
    return sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:n]


def _parsed_date(t: Transaction) -> Optional[date]:
    """Parse a transaction's date or return None if malformed."""
    try:
        return datetime.strptime(t.date, "%Y-%m-%d").date()
    except ValueError:
        return None


def trend_last_n_days(transactions: List[Transaction], n: int) -> float:
    """Total expense spending in the last n days, counted from the latest date."""
    if not transactions:
        return 0.0
    dates = [d for d in (_parsed_date(t) for t in transactions) if d is not None]
    if not dates:
        return 0.0
    cutoff = max(dates) - timedelta(days=n)
    total = 0.0
    for t in transactions:
        d = _parsed_date(t)
        if d is not None and d >= cutoff and t.amount < 0:
            total += abs(t.amount)
    return total


def recommend_budget_caps(
    transactions: List[Transaction],
    period: str = "monthly",
    safety_factor: float = 1.2,
) -> Dict[str, float]:
    """Recommend budget caps based on category spending history.

    Uses historical average spending for each category over the chosen
    period, then applies a safety factor to suggest a practical threshold.
    """
    if not transactions:
        return {}

    recommendations: Dict[str, float] = {}
    categories = {
        t.category for t in transactions if t.amount < 0 and t.category
    }
    for category in categories:
        cat_txns = [t for t in transactions if t.category == category and t.amount < 0]
        totals = by_period(cat_txns, period)
        if not totals:
            continue
        avg_spend = sum(totals.values()) / len(totals)
        recommendations[category] = round(avg_spend * safety_factor, 2)

    return recommendations


def average_daily_spending(transactions: List[Transaction]) -> float:
    """Mean daily spend across active days (days with at least one expense)."""
    daily: Dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.amount < 0:
            daily[t.date] += abs(t.amount)
    if not daily:
        return 0.0
    return sum(daily.values()) / len(daily)


def median_daily_spending(transactions: List[Transaction]) -> float:
    """Median daily spend across active days."""
    daily: Dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.amount < 0:
            daily[t.date] += abs(t.amount)
    vals = sorted(daily.values())
    if not vals:
        return 0.0
    mid = len(vals) // 2
    if len(vals) % 2 == 1:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2


def daily_std(transactions: List[Transaction]) -> float:
    """Population standard deviation of daily spend across active days."""
    daily: Dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.amount < 0:
            daily[t.date] += abs(t.amount)
    vals = list(daily.values())
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(var)


def moving_average(transactions: List[Transaction], window_days: int) -> Dict[str, float]:
    """Rolling daily-average spending across the window ending on each day."""
    daily: Dict[date, float] = defaultdict(float)
    for t in transactions:
        d = _parsed_date(t)
        if d is not None and t.amount < 0:
            daily[d] += abs(t.amount)
    if not daily:
        return {}
    start, end = min(daily.keys()), max(daily.keys())
    out: Dict[str, float] = {}
    cur = start
    while cur <= end:
        window_start = cur - timedelta(days=window_days - 1)
        tot = sum(v for d, v in daily.items() if window_start <= d <= cur)
        out[cur.strftime("%Y-%m-%d")] = tot / window_days
        cur += timedelta(days=1)
    return out


def period_boundaries(period: str, ref_day: date) -> Tuple[date, date]:
    """Return (start, end) dates of the period that contains ref_day."""
    if period == "daily":
        return ref_day, ref_day
    if period == "weekly":
        start = ref_day - timedelta(days=ref_day.weekday())
        return start, start + timedelta(days=6)
    start = ref_day.replace(day=1)
    last_day = calendar.monthrange(ref_day.year, ref_day.month)[1]
    return start, ref_day.replace(day=last_day)


def budget_utilization(
    transactions: List[Transaction],
    rule: BudgetRule,
    ref_day: Optional[date] = None,
) -> Dict[str, float]:
    """
    Current-period utilization for a single rule.

    """
    if ref_day is None:
        latest = None
        for t in transactions:
            d = _parsed_date(t)
            if d is not None and (latest is None or d > latest):
                latest = d
        ref_day = latest or date.today()
    start, end = period_boundaries(rule.period, ref_day)
    spent = 0.0
    for t in transactions:
        d = _parsed_date(t)
        if d is None or t.amount >= 0 or t.category != rule.category:
            continue
        if start <= d <= end:
            spent += abs(t.amount)
    total_days = (end - start).days + 1
    elapsed = (ref_day - start).days + 1
    pct = (spent / rule.threshold * 100) if rule.threshold > 0 else 0.0
    return {
        "spent": spent,
        "threshold": rule.threshold,
        "pct": pct,
        "remaining": max(0.0, rule.threshold - spent),
        "days_elapsed": elapsed,
        "days_total": total_days,
    }


def forecast_period_total(
    transactions: List[Transaction],
    rule: BudgetRule,
    ref_day: Optional[date] = None,
) -> Dict[str, float]:
    """
    Linear pace forecast to end of the active period.
        """
    util = budget_utilization(transactions, rule, ref_day)
    days_elapsed = max(1, int(util["days_elapsed"]))
    days_total = max(1, int(util["days_total"]))
    pace = util["spent"] / days_elapsed
    forecast = pace * days_total
    pct = (forecast / rule.threshold * 100) if rule.threshold > 0 else 0.0
    return {
        "spent": util["spent"],
        "forecast": forecast,
        "threshold": rule.threshold,
        "forecast_pct": pct,
        "days_elapsed": days_elapsed,
        "days_total": days_total,
    }


def format_summary(transactions: List[Transaction]) -> str:
    """Human-readable summary used by the CLI menu."""
    if not transactions:
        return "  No transactions."

    lines: List[str] = []
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
    avg = average_daily_spending(transactions)
    med = median_daily_spending(transactions)
    lines.append(f"  Avg / Median per active day: HK$ {avg:.2f} / HK$ {med:.2f}")
    t7 = trend_last_n_days(transactions, 7)
    t30 = trend_last_n_days(transactions, 30)
    lines.append(f"  Last 7 days:  HK$ {t7:.2f}")
    lines.append(f"  Last 30 days: HK$ {t30:.2f}")
    return "\n".join(lines)

def get_category_totals(transactions: list) -> dict:
    """Dynamically calculates totals for all available categories."""
    totals = {cat: 0.0 for cat in CATEGORIES}

    for t in transactions:
        cat = getattr(t, "category", "others") or "others"
        amount = float(getattr(t, "amount", 0.0))

        if cat not in totals:
            totals[cat] = 0.0

        totals[cat] += amount

    return totals

def get_monthly_forecast(transactions: List[Transaction]) -> dict:
    """
    Calculates the daily burn rate and predicts total spending for the month.
    Handles edge cases where no transactions exist or it is the start of the month.
    
    Args:
        transactions (List[Transaction]): List of transaction objects to analyze.
        
    Returns:
        dict: A dictionary containing 'burn_rate' and 'forecasted_total'.
    """
    # EDGE CASE HANDLING: If no transactions, return zeroed data
    if not transactions:
        return {"burn_rate": 0.0, "forecasted_total": 0.0}

    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    
    # Calculate days passed (min 1 to avoid division by zero)
    days_passed = max(1, today.day)
    
    # Only sum negative amounts (spending) for the current month
    current_month_spending = sum(abs(t.amount) for t in transactions 
                                if t.amount < 0 and _parsed_date(t) 
                                and _parsed_date(t).month == today.month 
                                and _parsed_date(t).year == today.year)
    
    burn_rate = current_month_spending / days_passed
    forecasted_total = burn_rate * days_in_month
    
    return {
        "burn_rate": burn_rate,
        "forecasted_total": forecasted_total
    }

def detect_subscription_creep(transactions: List[Transaction], threshold: float = 0.20) -> dict:
    """
    Detects month-over-month increases in subscription spending (Case Study 3).
    
    Args:
        transactions (List[Transaction]): List of transaction objects.
        threshold (float): The percentage increase (0.20 = 20%) to trigger an alert.
        
    Returns:
        dict: Results including detection status and percentage change.
    """
    if not transactions:
        return {"detected": False, "pct": 0, "current": 0}
