"""
Implements 5 alert types:
  1. Daily category cap overspend
  2. Weekly category cap overspend
  3. Monthly category cap overspend
  4. Percentage threshold (e.g. transport > 30% of total)
  5. Consecutive overspend days (e.g. food over daily cap 3 days in a row)
  6. Uncategorized (category == 'other') transaction warning
  7. Subscription creep detection (subscriptions rising month-over-month)
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Tuple

from data import BudgetRule, Transaction
from stats import by_period, by_category, total_spending



# 1-3. Category cap alerts (daily / weekly / monthly)


def check_category_caps(
    transactions: List[Transaction],
    rules: List[BudgetRule],
) -> List[str]:
    """
    For every budget rule, compute the total spent in the most recent period
    and fire an alert if it exceeds the threshold.

    Returns a list of alert message strings.
    """
    alerts = []

    for rule in rules:
        period_totals = by_period(transactions, rule.period)
        if not period_totals:
            continue

        # Only look at transactions matching this category
        cat_txns = [t for t in transactions if t.category == rule.category]
        cat_period_totals = by_period(cat_txns, rule.period)

        if not cat_period_totals:
            continue

        latest_key = sorted(cat_period_totals.keys())[-1]
        spent = cat_period_totals[latest_key]

        if spent > rule.threshold:
            overage = spent - rule.threshold
            alerts.append(
                f"[OVERSPEND] {rule.category.upper()} exceeded {rule.period} cap "
                f"(HK$ {rule.threshold:.2f}) in {latest_key}: "
                f"spent HK$ {spent:.2f}  (+HK$ {overage:.2f} over)"
            )

    return alerts



# 4. Percentage threshold alerts


def check_percentage_thresholds(
    transactions: List[Transaction],
    pct_rules: List[Tuple[str, float]],
) -> List[str]:
    """
    Fire an alert when a category exceeds a given percentage of total spending.

    """
    alerts = []
    total = total_spending(transactions)
    if total == 0:
        return alerts

    cat_totals = by_category(transactions)
    for category, max_pct in pct_rules:
        cat_spent = cat_totals.get(category, 0.0)
        actual_pct = (cat_spent / total) * 100
        if actual_pct > max_pct:
            alerts.append(
                f"[BUDGET %] {category.upper()} is {actual_pct:.1f}% of total spending "
                f"(limit: {max_pct:.0f}%)"
            )

    return alerts


# 5. Consecutive overspend days


def check_consecutive_overspend(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    streak_threshold: int = 3,
) -> List[str]:
    """
    Detect when a category has exceeded its daily cap for `streak_threshold`
    or more consecutive days.
    """
    alerts = []
    daily_rules = [r for r in rules if r.period == "daily"]

    for rule in daily_rules:
        # Build a dict of date -> total spending for this category
        cat_txns = [t for t in transactions if t.category == rule.category and t.amount < 0]
        daily_totals: dict = defaultdict(float)
        for t in cat_txns:
            daily_totals[t.date] += abs(t.amount)

        if not daily_totals:
            continue

        # Walk through dates in order and count consecutive overspend days
        sorted_dates = sorted(daily_totals.keys())
        streak = 0
        max_streak = 0
        streak_start = None

        for i, date_str in enumerate(sorted_dates):
            if daily_totals[date_str] > rule.threshold:
                if streak == 0:
                    streak_start = date_str
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

        if max_streak >= streak_threshold:
            alerts.append(
                f"[STREAK] {rule.category.upper()} exceeded daily cap (HK$ {rule.threshold:.2f}) "
                f"for {max_streak} consecutive day(s). "
                f"Consider reviewing your {rule.category} habits."
            )

    return alerts


# 6. Uncategorized transaction warning


def check_uncategorized(transactions: List[Transaction]) -> List[str]:
    """
    Warn if any transactions are in the 'other' category, suggesting
    the user should review and properly categorize them.
    """
    uncategorized = [t for t in transactions if t.category == "other"]
    if not uncategorized:
        return []

    return [
        f"[UNCATEGORIZED] {len(uncategorized)} transaction(s) are in the 'other' category. "
        f"Consider recategorizing them for more accurate summaries."
    ]



# 7. Subscription creep detection


def check_subscription_creep(transactions: List[Transaction]) -> List[str]:
    """
    Compare subscription spending across the two most recent calendar months.
    If spending increased by more than 20%, fire a subscription creep alert.
    """
    alerts = []
    sub_txns = [t for t in transactions if t.category == "subscriptions"]
    monthly = by_period(sub_txns, "monthly")

    if len(monthly) < 2:
        return alerts

    sorted_months = sorted(monthly.keys())
    prev_month = sorted_months[-2]
    curr_month = sorted_months[-1]
    prev_amt = monthly[prev_month]
    curr_amt = monthly[curr_month]

    if prev_amt == 0:
        return alerts

    change_pct = ((curr_amt - prev_amt) / prev_amt) * 100
    if change_pct > 20:
        alerts.append(
            f"[SUBSCRIPTION CREEP] Subscription spending rose {change_pct:.1f}% "
            f"from {prev_month} (HK$ {prev_amt:.2f}) to {curr_month} (HK$ {curr_amt:.2f}). "
            f"Review your active subscriptions."
        )

    return alerts


# Master runner


def run_all_alerts(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    pct_rules: List[Tuple[str, float]] = None,
    consecutive_days: int = 3,
) -> List[str]:
    """
    Run all alert checks and return a combined list of alert messages.

    """
    if pct_rules is None:
        pct_rules = []

    all_alerts: List[str] = []
    all_alerts += check_category_caps(transactions, rules)
    all_alerts += check_percentage_thresholds(transactions, pct_rules)
    all_alerts += check_consecutive_overspend(transactions, rules, streak_threshold=consecutive_days)
    all_alerts += check_uncategorized(transactions)
    all_alerts += check_subscription_creep(transactions)

    return all_alerts
