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
from datetime import date, datetime, timedelta
from typing import List, Optional, Sequence, Tuple

from data import BudgetRule, Transaction
from stats import by_period, by_category, total_spending

# Prefix → kind id (used by GUI banners). Longer prefixes must come first.
ALERT_PREFIX_KIND: List[Tuple[str, str]] = [
    ("[BUDGET % CRITICAL]", "budget_pct_critical"),
    ("[BUDGET % WARN]", "budget_pct_warn"),
    ("[OVERSPEND]", "overspend"),
    ("[BUDGET %]", "budget_pct"),
    ("[STREAK]", "streak"),
    ("[UNCATEGORIZED]", "uncategorized"),
    ("[SUBSCRIPTION CREEP]", "subscription_creep"),
]


def split_alert_message(msg: str) -> Tuple[str, str]:
    """
    Return (kind, body) where kind is a short id for styling, body is text without the tag prefix.
    Unknown / legacy messages use kind 'general'.
    """
    s = (msg or "").strip()
    for prefix, kind in ALERT_PREFIX_KIND:
        if s.startswith(prefix):
            return kind, s[len(prefix) :].strip()
    return "general", s


def normalize_pct_rules_rows(
    pct_rules: Optional[Sequence] = None,
) -> List[Tuple[str, float, float]]:
    """
    Each row is (category, warning_pct, critical_pct). Critical 0 = only warning tier.
    2-element rows (CLI / legacy) become (c, w, 0).
    """
    out: List[Tuple[str, float, float]] = []
    for r in pct_rules or []:
        if not isinstance(r, (list, tuple)) or len(r) < 2:
            continue
        try:
            cat = str(r[0]).strip().lower()
            w = float(r[1])
            c = float(r[2]) if len(r) >= 3 else 0.0
        except (TypeError, ValueError, IndexError):
            continue
        if not cat:
            continue
        if not (0 < w <= 100):
            continue
        c = max(0.0, min(100.0, c))
        if 0 < c <= w:
            continue
        out.append((cat, w, c))
    return out



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
        if not cat_txns:
            continue
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
    pct_rules: List[Tuple[str, float, float]],
) -> List[str]:
    """
    Two tiers per category: warning when share > warning_pct; critical when > critical_pct
    (if critical_pct > 0 and critical_pct > warning_pct). If critical_pct is 0, only warnings.
    """
    alerts = []
    total = total_spending(transactions)
    if total == 0:
        return alerts

    cat_totals = by_category(transactions)
    for category, warn_pct, crit_pct in pct_rules:
        cat_spent = cat_totals.get(category, 0.0)
        actual_pct = (cat_spent / total) * 100
        if crit_pct > 0 and actual_pct > crit_pct:
            alerts.append(
                f"[BUDGET % CRITICAL] {category.upper()} is {actual_pct:.1f}% of total spending "
                f"(critical if above {crit_pct:.0f}%; warning from {warn_pct:.0f}%)"
            )
        elif actual_pct > warn_pct:
            extra = (
                f" Critical threshold {crit_pct:.0f}%."
                if crit_pct > 0
                else " (single warning tier only)."
            )
            alerts.append(
                f"[BUDGET % WARN] {category.upper()} is {actual_pct:.1f}% of total spending "
                f"(warning if above {warn_pct:.0f}% of total).{extra}"
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

        # Calendar-consecutive overspend days only (not just consecutive rows in
        # sorted_dates — gaps with zero category spend must break the run).
        sorted_dates = sorted(daily_totals.keys())
        streak = 0
        max_streak = 0
        last_overspend_day: Optional[date] = None

        for date_str in sorted_dates:
            spent = daily_totals[date_str]
          if isinstance(date_str, date):
            day = date_str
        else:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if spent > rule.threshold:
                if last_overspend_day is not None and day == last_overspend_day + timedelta(days=1):
                    streak += 1
                else:
                    streak = 1
                last_overspend_day = day
                max_streak = max(max_streak, streak)
            else:
                streak = 0
                last_overspend_day = None

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


def check_subscription_creep(transactions: List[Transaction], threshold_pct: float = 20.0) -> List[str]:
    """
    Compare subscription spending across the two most recent calendar months.
    If spending increased by more than threshold_pct%, fire a subscription creep alert.
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
    if change_pct > threshold_pct:
        alerts.append(
            f"[SUBSCRIPTION CREEP] Subscription spending rose {change_pct:.1f}% "
            f"from {prev_month} (HK$ {prev_amt:.2f}) to {curr_month} (HK$ {curr_amt:.2f}) "
            f"(alert threshold: {threshold_pct:.0f}% increase). "
            f"Review your active subscriptions."
        )

    return alerts


# Master runner


def run_all_alerts(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    pct_rules: Optional[Sequence] = None,
    consecutive_days: int = 3,
    subscription_creep_threshold_pct: float = 20.0,
) -> List[str]:
    """
    Run all alert checks and return a combined list of alert messages.
    pct_rules may be 2-tuples (legacy) or 3-tuples (category, warn_pct, critical_pct).

    """
    pct_norm = normalize_pct_rules_rows(pct_rules)

    all_alerts: List[str] = []
    all_alerts += check_category_caps(transactions, rules)
    all_alerts += check_percentage_thresholds(transactions, pct_norm)
    all_alerts += check_consecutive_overspend(transactions, rules, streak_threshold=consecutive_days)
    all_alerts += check_uncategorized(transactions)
    all_alerts += check_subscription_creep(transactions, threshold_pct=subscription_creep_threshold_pct)

    return all_alerts
