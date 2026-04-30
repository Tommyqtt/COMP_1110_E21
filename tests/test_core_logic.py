"""
Consolidated logic tests: alerts, stats, data validation, gui_settings, portfolio.
Edge cases: empty inputs, boundaries, malformed data, deduplication, clamps.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data import (  # noqa: E402
    BudgetRule,
    Transaction,
    validate_amount,
    validate_category,
    validate_date,
)
from alerts import (  # noqa: E402
    check_category_caps,
    check_consecutive_overspend,
    check_percentage_thresholds,
    check_subscription_creep,
    check_uncategorized,
    normalize_pct_rules_rows,
    run_all_alerts,
)
import gui_settings  # noqa: E402
from stats import (  # noqa: E402
    average_daily_spending,
    by_category,
    by_period,
    format_summary,
    recommend_budget_caps,
    total_spending,
    trend_last_n_days,
)
import portfolio  # noqa: E402


def T(date: str, amount: float, category: str, description: str = "") -> Transaction:
    return Transaction(date=date, amount=amount, category=category, description=description)


class TestNormalizePctRules(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(normalize_pct_rules_rows(None), [])
        self.assertEqual(normalize_pct_rules_rows([]), [])

    def test_legacy_two_tuple(self) -> None:
        self.assertEqual(
            normalize_pct_rules_rows([["transport", 30]]),
            [("transport", 30.0, 0.0)],
        )

    def test_rejects_invalid(self) -> None:
        self.assertEqual(normalize_pct_rules_rows([["", 50]]), [])
        self.assertEqual(normalize_pct_rules_rows([["food", "notnum", 0]]), [])
        self.assertEqual(normalize_pct_rules_rows([["food", 0]]), [])
        self.assertEqual(normalize_pct_rules_rows([["food", 101]]), [])
        self.assertEqual(normalize_pct_rules_rows([["food", 30, 20]]), [])  # crit <= warn

    def test_critical_above_warn(self) -> None:
        out = normalize_pct_rules_rows([["food", 30, 50]])
        self.assertEqual(out, [("food", 30.0, 50.0)])

    def test_crit_clamped(self) -> None:
        out = normalize_pct_rules_rows([["food", 30, 200]])
        self.assertEqual(out[0][2], 100.0)


class TestCategoryCaps(unittest.TestCase):
    def test_empty_transactions(self) -> None:
        rules = [BudgetRule("food", "daily", 50, "overspend")]
        self.assertEqual(check_category_caps([], rules), [])

    def test_under_cap(self) -> None:
        txs = [T("2026-04-01", -20, "food")]
        rules = [BudgetRule("food", "daily", 50, "overspend")]
        self.assertEqual(check_category_caps(txs, rules), [])

    def test_over_daily_latest_period(self) -> None:
        txs = [T("2026-04-10", -80, "food")]
        rules = [BudgetRule("food", "daily", 50, "overspend")]
        a = check_category_caps(txs, rules)
        self.assertEqual(len(a), 1)
        self.assertIn("[OVERSPEND]", a[0])
        self.assertIn("FOOD", a[0])
        self.assertIn("2026-04-10", a[0])

    def test_monthly_cap(self) -> None:
        txs = [
            T("2026-04-01", -200, "transport"),
            T("2026-04-02", -150, "transport"),
        ]
        rules = [BudgetRule("transport", "monthly", 300, "overspend")]
        a = check_category_caps(txs, rules)
        self.assertEqual(len(a), 1)
        self.assertIn("monthly", a[0].lower())

    def test_weekly_cap(self) -> None:
        txs = [
            T("2026-04-06", -40, "shopping"),
            T("2026-04-07", -40, "shopping"),
            T("2026-04-08", -40, "shopping"),
        ]
        rules = [BudgetRule("shopping", "weekly", 100, "overspend")]
        a = check_category_caps(txs, rules)
        self.assertEqual(len(a), 1)
        self.assertIn("weekly", a[0].lower())


class TestPercentageThresholds(unittest.TestCase):
    def test_zero_total_no_crash(self) -> None:
        self.assertEqual(check_percentage_thresholds([], [("food", 10.0, 0.0)]), [])

    def test_warn_only_tier(self) -> None:
        txs = [T("2026-01-01", -70, "food"), T("2026-01-01", -30, "transport")]
        a = check_percentage_thresholds(txs, [("food", 50.0, 0.0)])
        self.assertEqual(len(a), 1)
        self.assertIn("[BUDGET % WARN]", a[0])
        self.assertIn("single warning tier only", a[0])

    def test_critical_tier(self) -> None:
        txs = [T("2026-01-01", -85, "food"), T("2026-01-01", -15, "transport")]
        a = check_percentage_thresholds(txs, [("food", 40.0, 80.0)])
        self.assertTrue(any("[BUDGET % CRITICAL]" in x for x in a))

    def test_boundary_not_exceeded(self) -> None:
        txs = [T("2026-01-01", -50, "food"), T("2026-01-01", -50, "transport")]
        a = check_percentage_thresholds(txs, [("food", 50.0, 90.0)])
        self.assertEqual(a, [])

    def test_exact_warn_boundary_no_warn(self) -> None:
        txs = [T("2026-01-01", -30, "food"), T("2026-01-01", -70, "transport")]
        a = check_percentage_thresholds(txs, [("food", 30.0, 80.0)])
        self.assertEqual(a, [])


class TestConsecutiveOverspend(unittest.TestCase):
    def test_no_daily_rule(self) -> None:
        txs = [T("2026-04-01", -100, "food")]
        rules = [BudgetRule("food", "monthly", 50, "overspend")]
        self.assertEqual(check_consecutive_overspend(txs, rules, streak_threshold=3), [])

    def test_streak_after_reset(self) -> None:
        txs = [
            T("2026-04-01", -60, "food"),
            T("2026-04-02", -40, "food"),
            T("2026-04-03", -60, "food"),
            T("2026-04-04", -60, "food"),
            T("2026-04-05", -60, "food"),
        ]
        rules = [BudgetRule("food", "daily", 50, "overspend")]
        a = check_consecutive_overspend(txs, rules, streak_threshold=3)
        self.assertEqual(len(a), 1)
        self.assertIn("[STREAK]", a[0])
        self.assertIn("for 3 consecutive day(s)", a[0])

    def test_calendar_gap_breaks_streak(self) -> None:
        """Spending on day 1 and day 3 only (no day 2) is not a 2-day calendar streak."""
        txs = [
            T("2026-04-01", -60, "food"),
            T("2026-04-03", -60, "food"),
        ]
        rules = [BudgetRule("food", "daily", 50, "overspend")]
        self.assertEqual(check_consecutive_overspend(txs, rules, streak_threshold=2), [])


class TestUncategorizedAndCreep(unittest.TestCase):
    def test_no_other(self) -> None:
        self.assertEqual(check_uncategorized([T("2026-01-01", -5, "food")]), [])

    def test_other_triggers(self) -> None:
        a = check_uncategorized(
            [T("2026-01-01", -1, "other"), T("2026-01-01", -2, "other")]
        )
        self.assertEqual(len(a), 1)
        self.assertIn("2 transaction", a[0])

    def test_creep_one_month(self) -> None:
        txs = [T("2026-03-01", -50, "subscriptions")]
        self.assertEqual(check_subscription_creep(txs, 20), [])

    def test_creep_exact_threshold_no_alert(self) -> None:
        txs = [
            T("2026-03-01", -100, "subscriptions"),
            T("2026-04-01", -120, "subscriptions"),
        ]
        self.assertEqual(check_subscription_creep(txs, 20), [])

    def test_creep_over_threshold(self) -> None:
        txs = [
            T("2026-03-01", -100, "subscriptions"),
            T("2026-04-01", -121, "subscriptions"),
        ]
        a = check_subscription_creep(txs, 20)
        self.assertEqual(len(a), 1)
        self.assertIn("[SUBSCRIPTION CREEP]", a[0])


class TestRunAllAlerts(unittest.TestCase):
    def test_combined(self) -> None:
        txs = [
            T("2026-04-01", -60, "food"),
            T("2026-04-01", -350, "transport"),
            T("2026-04-01", -5, "other"),
        ]
        rules = [
            BudgetRule("food", "daily", 50, "overspend"),
            BudgetRule("transport", "monthly", 300, "overspend"),
        ]
        pct = [("food", 1.0, 0.0)]
        out = run_all_alerts(txs, rules, pct_rules=pct, consecutive_days=1, subscription_creep_threshold_pct=20.0)
        joined = " ".join(out)
        self.assertIn("[OVERSPEND]", joined)
        self.assertIn("[UNCATEGORIZED]", joined)


class TestStats(unittest.TestCase):
    def test_total_ignores_positive(self) -> None:
        txs = [T("2026-01-01", 100, "food")]  # normalized to -100
        self.assertEqual(total_spending(txs), 100.0)

    def test_by_period_skips_bad_date(self) -> None:
        txs = [T("not-a-date", -10, "food"), T("2026-06-15", -20, "food")]
        m = by_period(txs, "monthly")
        self.assertIn("2026-06", m)

    def test_trend_all_bad_dates(self) -> None:
        txs = [T("bad", -10, "food")]
        self.assertEqual(trend_last_n_days(txs, 7), 0.0)

    def test_average_daily_empty(self) -> None:
        self.assertEqual(average_daily_spending([]), 0.0)

    def test_format_summary_empty(self) -> None:
        self.assertIn("No transactions", format_summary([]))

    def test_recommend_budget_caps_empty(self) -> None:
        self.assertEqual(recommend_budget_caps([], "monthly"), {})

    def test_recommend_budget_caps_monthly(self) -> None:
        txs = [
            T("2026-01-01", -100, "food"),
            T("2026-01-15", -120, "food"),
            T("2026-01-10", -50, "transport"),
            T("2026-02-05", -80, "transport"),
        ]
        recs = recommend_budget_caps(txs, "monthly", safety_factor=1.0)
        self.assertEqual(recs["food"], 220.0)
        self.assertEqual(recs["transport"], 65.0)


class TestDataValidation(unittest.TestCase):
    def test_transaction_positive_normalized(self) -> None:
        t = T("2026-01-01", 42.5, "shopping")
        self.assertLess(t.amount, 0)

    def test_validate_date(self) -> None:
        self.assertFalse(validate_date("2026-13-01"))
        self.assertTrue(validate_date("2026-01-15"))

    def test_validate_amount(self) -> None:
        self.assertIsNone(validate_amount("0"))
        self.assertIsNone(validate_amount("-1"))
        self.assertEqual(validate_amount("12.5"), 12.5)

    def test_validate_category(self) -> None:
        self.assertTrue(validate_category("food"))
        self.assertTrue(validate_category("custom1"))


class TestGuiSettingsFile(unittest.TestCase):
    def setUp(self) -> None:
        import data as data_mod

        self._td = Path(tempfile.mkdtemp())
        self.tmp = self._td / "budgets.csv"
        self.patch = patch.object(data_mod, "BUDGETS_PATH", self.tmp)
        self.patch.start()

    def tearDown(self) -> None:
        self.patch.stop()
        if self._td.exists():
            try:
                for p in self._td.iterdir():
                    p.unlink()
                self._td.rmdir()
            except OSError:
                pass

    def test_roundtrip_and_dedup(self) -> None:
        data = {
            "pct_rules": [
                ["food", 25, 40],
                ["food", 99, 0],
            ],
            "consecutive_overspend_days": 999,
            "subscription_creep_threshold_pct": 999,
            "alert_strip_width": 12,
        }
        gui_settings.save_gui_settings(data)
        loaded = gui_settings.load_gui_settings()
        self.assertEqual(len(loaded["pct_rules"]), 1)
        self.assertEqual(loaded["consecutive_overspend_days"], 30)
        self.assertEqual(loaded["subscription_creep_threshold_pct"], 500.0)
        self.assertNotIn("alert_strip_width", loaded)

    def test_pct_rules_as_tuples(self) -> None:
        gui_settings.save_gui_settings({"pct_rules": [["transport", 30, 45]]})
        loaded = gui_settings.load_gui_settings()
        tups = gui_settings.pct_rules_as_tuples(loaded)
        self.assertEqual(tups, [("transport", 30.0, 45.0)])


class TestPortfolio(unittest.TestCase):
    def test_get_allocation_clamp(self) -> None:
        a0 = portfolio.get_allocation(0)
        a1 = portfolio.get_allocation(1)
        self.assertEqual(a0, a1)
        a6 = portfolio.get_allocation(99)
        a5 = portfolio.get_allocation(5)
        self.assertEqual(a6, a5)

    def test_simulate_shape(self) -> None:
        assets = portfolio.load_assets(str(ROOT / "assets.csv"))
        alloc = portfolio.get_allocation(3)
        r = portfolio.simulate(1000, 100, 6, alloc, assets, num_paths=50)
        for k in ("p10", "p50", "p90", "loss_prob"):
            self.assertIn(k, r)


if __name__ == "__main__":
    unittest.main()
