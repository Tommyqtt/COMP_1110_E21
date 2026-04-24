"""
Rule-based alerts 

Alert kinds:
  1. Daily / weekly / monthly category cap overspend
  2. Category share of total spending (warning + optional critical tier)
  3. Consecutive overspend days on a daily cap
  4. Uncategorized transactions warning
  5. Subscription creep (month-over-month growth)
  6. Period-end forecast (current pace projected to end of period)
  7. Daily spending anomaly (unusual spike vs typical day)
  8. Recurring non-subscription payments (likely mis-categorized)
  9. Overall budget health score summary
"""
from data import CATEGORIES
from stats import get_category_totals

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from data import BudgetRule, Transaction
from stats import (
    by_category,
    by_period,
    daily_std,
    forecast_period_total,
    median_daily_spending,
    total_spending,
)

# Map alert tag prefixes to short kind ids used by GUI banner styling.
# Longer prefixes must come first so match order is unambiguous.
ALERT_PREFIX_KIND: List[Tuple[str, str]] = [
    ("[BUDGET % CRITICAL]", "budget_pct_critical"),
    ("[BUDGET % WARN]", "budget_pct_warn"),
    ("[OVERSPEND]", "overspend"),
    ("[BUDGET %]", "budget_pct"),
    ("[STREAK]", "streak"),
    ("[UNCATEGORIZED]", "uncategorized"),
    ("[SUBSCRIPTION CREEP]", "subscription_creep"),
    ("[FORECAST]", "forecast"),
    ("[ANOMALY]", "anomaly"),
    ("[RECURRING]", "recurring"),
    ("[HEALTH]", "health"),
]


def split_alert_message(msg: str) -> Tuple[str, str]:
    """Return (kind, body). Unknown tags use kind 'general'."""
    s = (msg or "").strip()
    for prefix, kind in ALERT_PREFIX_KIND:
        if s.startswith(prefix):
            return kind, s[len(prefix):].strip()
    return "general", s


def normalize_pct_rules_rows(
    pct_rules: Optional[Sequence] = None,
) -> List[Tuple[str, float, float]]:
    """
    Normalize pct-rule rows to (category, warning_pct, critical_pct) tuples.
    Critical 0 means warning tier only. 2-element rows become (c, w, 0).
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
        if not cat or not (0 < w <= 100):
            continue
        c = max(0.0, min(100.0, c))
        if 0 < c <= w:
            continue
        out.append((cat, w, c))
    return out


def check_category_caps(
    transactions: List[Transaction],
    rules: List[BudgetRule],
) -> List[str]:
    """Fire an alert for every rule whose most recent period has exceeded the cap."""
    alerts: List[str] = []
    for rule in rules:
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
                f"spent HK$ {spent:.2f} (+HK$ {overage:.2f} over)"
            )
    return alerts


def check_percentage_thresholds(
    transactions: List[Transaction],
    pct_rules: List[Tuple[str, float, float]],
) -> List[str]:
    """Two tiers per category: warning fires first, critical fires if higher tier is crossed."""
    alerts: List[str] = []
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
            extra = f" Critical threshold {crit_pct:.0f}%." if crit_pct > 0 else " (single warning tier only)."
            alerts.append(
                f"[BUDGET % WARN] {category.upper()} is {actual_pct:.1f}% of total spending "
                f"(warning if above {warn_pct:.0f}% of total).{extra}"
            )
    return alerts


def check_consecutive_overspend(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    streak_threshold: int = 3,
) -> List[str]:
    """Detect calendar-consecutive days that exceed a daily category cap."""
    alerts: List[str] = []
    for rule in (r for r in rules if r.period == "daily"):
        cat_txns = [t for t in transactions if t.category == rule.category and t.amount < 0]
        if not cat_txns:
            continue
        daily_totals: Dict[str, float] = defaultdict(float)
        for t in cat_txns:
            daily_totals[t.date] += abs(t.amount)
        sorted_dates = sorted(daily_totals.keys())
        streak = 0
        max_streak = 0
        last_day: Optional[date] = None
        for date_str in sorted_dates:
            try:
                day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if daily_totals[date_str] > rule.threshold:
                if last_day is not None and day == last_day + timedelta(days=1):
                    streak += 1
                else:
                    streak = 1
                last_day = day
                max_streak = max(max_streak, streak)
            else:
                streak = 0
                last_day = None
        if max_streak >= streak_threshold:
            alerts.append(
                f"[STREAK] {rule.category.upper()} exceeded daily cap (HK$ {rule.threshold:.2f}) "
                f"for {max_streak} consecutive day(s). "
                f"Consider reviewing your {rule.category} habits."
            )
    return alerts


def check_uncategorized(transactions: List[Transaction]) -> List[str]:
    """Warn when transactions remain in the 'other' category."""
    uncategorized = [t for t in transactions if t.category == "other"]
    if not uncategorized:
        return []
    return [
        f"[UNCATEGORIZED] {len(uncategorized)} transaction(s) are in the 'other' category. "
        f"Consider recategorizing them for more accurate summaries."
    ]


def check_subscription_creep(
    transactions: List[Transaction],
    threshold_pct: float = 20.0,
) -> List[str]:
    """Compare the two most recent calendar months of 'subscriptions' spend."""
    sub_txns = [t for t in transactions if t.category == "subscriptions"]
    monthly = by_period(sub_txns, "monthly")
    if len(monthly) < 2:
        return []
    sorted_months = sorted(monthly.keys())
    prev_month, curr_month = sorted_months[-2], sorted_months[-1]
    prev_amt, curr_amt = monthly[prev_month], monthly[curr_month]
    if prev_amt <= 0:
        return []
    change_pct = ((curr_amt - prev_amt) / prev_amt) * 100
    if change_pct <= threshold_pct:
        return []
    return [
        f"[SUBSCRIPTION CREEP] Subscription spending rose {change_pct:.1f}% "
        f"from {prev_month} (HK$ {prev_amt:.2f}) to {curr_month} (HK$ {curr_amt:.2f}) "
        f"(alert threshold: {threshold_pct:.0f}% increase). Review your active subscriptions."
    ]


def check_forecasts(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    forecast_pct_trigger: float = 110.0,
) -> List[str]:
    """
    Project end-of-period spend from the current pace inside the active period.
    Fires when the projection crosses the trigger (default 110% of cap) but
    the cap has not yet been breached — avoids duplicating OVERSPEND alerts.
    """
    alerts: List[str] = []
    for rule in rules:
        f = forecast_period_total(transactions, rule)
        if f["spent"] >= f["threshold"] or f["threshold"] <= 0:
            continue
        if f["forecast_pct"] >= forecast_pct_trigger:
            alerts.append(
                f"[FORECAST] {rule.category.upper()} on pace for HK$ {f['forecast']:.2f} "
                f"by end of {rule.period} (cap HK$ {f['threshold']:.2f}; "
                f"{f['days_elapsed']}/{f['days_total']} days elapsed, "
                f"projected {f['forecast_pct']:.0f}% of cap). Slow spending to stay under."
            )
    return alerts


def check_anomalies(
    transactions: List[Transaction],
    multiplier: float = 2.5,
    min_baseline: float = 30.0,
    top_n: int = 3,
) -> List[str]:
    """
    Flag days where total spending exceeds multiplier * max(median, min_baseline).
    Using median keeps the detector from being dragged up by its own spikes.
    """
    daily: Dict[str, float] = defaultdict(float)
    for t in transactions:
        if t.amount < 0:
            daily[t.date] += abs(t.amount)
    if len(daily) < 3:
        return []
    med = median_daily_spending(transactions)
    std = daily_std(transactions)
    baseline = max(med, min_baseline)
    threshold = baseline * multiplier
    flagged = [(d, v) for d, v in daily.items() if v > threshold]
    if not flagged:
        return []
    flagged.sort(key=lambda x: x[1], reverse=True)
    parts = [f"{d}: HK$ {v:.2f} ({(v / baseline):.1f}x baseline)" for d, v in flagged[:top_n]]
    extra = f" (+{len(flagged) - top_n} more)" if len(flagged) > top_n else ""
    return [
        f"[ANOMALY] Unusually high daily spending detected. "
        f"Median / stdev per active day: HK$ {med:.2f} / HK$ {std:.2f}. "
        f"Top days: {'; '.join(parts)}{extra}."
    ]


def check_recurring_nonsubscription(
    transactions: List[Transaction],
    min_hits: int = 2,
    amount_tolerance_pct: float = 5.0,
) -> List[str]:
    """
    Group non-subscription expenses by (category, description, amount-bucket).
    Flag groups that repeat across distinct months at very similar amounts:
    likely recurring payments worth relabelling as 'subscriptions'.
    """
    groups: Dict[Tuple[str, str, int], List[Transaction]] = defaultdict(list)
    for t in transactions:
        if t.amount >= 0 or t.category == "subscriptions":
            continue
        desc = (t.description or "").strip().lower()
        if not desc:
            continue
        key = (t.category, desc, int(round(abs(t.amount) / max(1.0, amount_tolerance_pct))))
        groups[key].append(t)

    alerts: List[str] = []
    for (cat, desc, _), items in groups.items():
        if len(items) < min_hits:
            continue
        months = set()
        for t in items:
            try:
                dt = datetime.strptime(t.date, "%Y-%m-%d")
                months.add((dt.year, dt.month))
            except ValueError:
                continue
        if len(months) < min_hits:
            continue
        amounts = [abs(t.amount) for t in items]
        avg_amt = sum(amounts) / len(amounts)
        spread = (max(amounts) - min(amounts)) / max(1.0, avg_amt) * 100
        if spread > amount_tolerance_pct * 4:
            continue
        alerts.append(
            f"[RECURRING] '{desc}' in '{cat}' repeats {len(items)} times across "
            f"{len(months)} month(s) at ~HK$ {avg_amt:.2f}. "
            f"Consider moving to 'subscriptions' for creep tracking."
        )
    return alerts


def compute_health_score(
    transactions: List[Transaction],
    rules: List[BudgetRule],
) -> Dict[str, Any]:
    """
    0-100 health score combining three signals:
      - utilization: highest current-period cap utilization
      - forecast:    highest projected end-of-period utilization
      - categorization: share of transactions not in 'other'
    """
    if not transactions:
        return {"score": 100.0, "grade": "A", "max_util": 0.0,
                "max_forecast": 0.0, "categorized_pct": 100.0}

    max_util = 0.0
    max_fc = 0.0
    for rule in rules:
        f = forecast_period_total(transactions, rule)
        if f["threshold"] > 0:
            util_pct = (f["spent"] / f["threshold"]) * 100
            max_util = max(max_util, util_pct)
            max_fc = max(max_fc, f["forecast_pct"])

    categorized = sum(1 for t in transactions if t.category != "other")
    cat_pct = (categorized / len(transactions)) * 100

    util_pen = min(60.0, max(0.0, max_util - 50.0) * 0.8)
    fc_pen = min(30.0, max(0.0, max_fc - 90.0) * 0.6)
    cat_pen = min(20.0, (100 - cat_pct) * 0.4)

    score = max(0.0, 100.0 - util_pen - fc_pen - cat_pen)
    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": round(score, 1),
        "grade": grade,
        "max_util": round(max_util, 1),
        "max_forecast": round(max_fc, 1),
        "categorized_pct": round(cat_pct, 1),
    }


def check_health_summary(
    transactions: List[Transaction],
    rules: List[BudgetRule],
) -> List[str]:
    """Single [HEALTH] message summarizing the dashboard score."""
    if not transactions:
        return []
    h = compute_health_score(transactions, rules)
    return [
        f"[HEALTH] Budget health: {h['score']:.0f}/100 (grade {h['grade']}). "
        f"Highest cap utilisation {h['max_util']:.0f}%, "
        f"projected end-of-period {h['max_forecast']:.0f}%, "
        f"transactions categorised {h['categorized_pct']:.0f}%."
    ]


def run_all_alerts(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    pct_rules: Optional[Sequence] = None,
    consecutive_days: int = 3,
    subscription_creep_threshold_pct: float = 20.0,
    anomaly_multiplier: float = 2.5,
    forecast_pct_trigger: float = 110.0,
    include_health: bool = True,
) -> List[str]:
    """Run every alert check and return the combined message list."""
    pct_norm = normalize_pct_rules_rows(pct_rules)
    out: List[str] = []
    out += check_category_caps(transactions, rules)
    out += check_forecasts(transactions, rules, forecast_pct_trigger=forecast_pct_trigger)
    out += check_percentage_thresholds(transactions, pct_norm)
    out += check_consecutive_overspend(transactions, rules, streak_threshold=consecutive_days)
    out += check_anomalies(transactions, multiplier=anomaly_multiplier)
    out += check_recurring_nonsubscription(transactions)
    out += check_uncategorized(transactions)
    out += check_subscription_creep(transactions, threshold_pct=subscription_creep_threshold_pct)
    if include_health:
        out += check_health_summary(transactions, rules)
    return out

# Assume you store budget limits in a dictionary or load them from budgets.csv
budget_caps = {
    "food": 2000,
    "transport": 500
}

def check_category_alerts(transactions: list):
    totals = get_category_totals(transactions) # using the updated stats function
    
    for cat in CATEGORIES:
        # If a new category exists but has no cap set yet, skip it or give it a default
        cap = budget_caps.get(cat, None) 
        if cap is not None and totals.get(cat, 0) > cap:
            print(f"⚠️ ALERT: You have exceeded your budget for '{cat}'! (Spent: {totals[cat]}, Cap: {cap})")