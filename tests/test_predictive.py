import unittest
from datetime import date
from stats import get_monthly_forecast, predict_by_category, days_until_cap, Transaction

class TestPredictiveLogic(unittest.TestCase):
    def setUp(self):
        # Create a mock transaction for testing
        self.mock_transactions = [
            Transaction(date="2026-04-01", description="Test", category="Food", amount=-100.0)
        ]

    def test_forecast_calculation(self):
        """Test if the burn rate calculation returns the expected keys."""
        result = get_monthly_forecast(self.mock_transactions)
        self.assertIn("burn_rate", result)
        self.assertIn("forecasted_total", result)
        self.assertGreaterEqual(result["forecasted_total"], 100.0)

    def test_zero_days_passed(self):
        """Test that the function doesn't crash on the first day of the month."""
        # This tests the 'if days_passed <= 0' logic we wrote!
        result = get_monthly_forecast(self.mock_transactions)
        # It should return a valid dictionary even if days_passed is 0
        self.assertIsInstance(result, dict)

if __name__ == "__main__":
    unittest.main()

class TestPredictByCategory(unittest.TestCase):

    def _make_txn(self, date, amount, category):
        return Transaction(date=date, amount=amount, category=category, description="")

    def test_single_category_projects_correctly(self):
        txns = [self._make_txn("2026-03-01", -40.0, "food"),
                self._make_txn("2026-03-05", -60.0, "food")]
        result = predict_by_category(txns, year=2026, month=3)
        import calendar
        total_days = calendar.monthrange(2026, 3)[1]
        expected = round((100.0 / 5) * total_days, 2)
        self.assertAlmostEqual(result.get("food", 0), expected, places=1)

    def test_multiple_categories_returned(self):
        txns = [self._make_txn("2026-03-10", -50.0, "food"),
                self._make_txn("2026-03-10", -20.0, "transport"),
                self._make_txn("2026-03-10", -30.0, "subscriptions")]
        result = predict_by_category(txns, year=2026, month=3)
        self.assertIn("food", result)
        self.assertIn("transport", result)
        self.assertIn("subscriptions", result)

    def test_ignores_other_months(self):
        txns = [self._make_txn("2026-02-15", -500.0, "food"),
                self._make_txn("2026-03-05", -50.0, "food")]
        result = predict_by_category(txns, year=2026, month=3)
        import calendar
        total_days = calendar.monthrange(2026, 3)[1]
        expected = round((50.0 / 5) * total_days, 2)
        self.assertAlmostEqual(result.get("food", 0), expected, places=1)

    def test_empty_transactions_returns_empty_dict(self):
        result = predict_by_category([])
        self.assertEqual(result, {})

    def test_no_data_for_target_month_returns_empty(self):
        txns = [self._make_txn("2026-02-10", -100.0, "food")]
        result = predict_by_category(txns, year=2026, month=3)
        self.assertEqual(result, {})

    def test_malformed_dates_skipped_gracefully(self):
        txns = [Transaction(date="not-a-date", amount=-50.0, category="food", description=""),
                self._make_txn("2026-03-10", -80.0, "food")]
        result = predict_by_category(txns, year=2026, month=3)
        self.assertIn("food", result)

    def test_all_same_day_uses_that_day_as_elapsed(self):
        txns = [self._make_txn("2026-03-01", -30.0, "food"),
                self._make_txn("2026-03-01", -20.0, "food")]
        result = predict_by_category(txns, year=2026, month=3)
        import calendar
        total_days = calendar.monthrange(2026, 3)[1]
        expected = round((50.0 / 1) * total_days, 2)
        self.assertAlmostEqual(result.get("food", 0), expected, places=1)

class TestDaysUntilCap(unittest.TestCase):

    def _make_txn(self, date, amount, category):
        return Transaction(date=date, amount=amount, category=category, description="")

    def _make_rule(self, category, period, threshold):
        from data import BudgetRule
        return BudgetRule(category=category, period=period, threshold=threshold, alert_type="overspend")

    def test_returns_none_when_no_spending(self):
        rules = [self._make_rule("food", "daily", 50.0)]
        result = days_until_cap([], rules)
        self.assertEqual(len(result), 1)
        _, _, _, days = result[0]
        self.assertIsNone(days)

    def test_returns_zero_when_already_exceeded(self):
        txns = [self._make_txn(f"2026-03-{d:02d}", -200.0, "food") for d in range(1, 11)]
        rules = [self._make_rule("food", "daily", 50.0)]
        result = days_until_cap(txns, rules)
        _, _, _, days = result[0]
        self.assertEqual(days, 0)

    def test_positive_days_remaining_calculated(self):
        txns = [self._make_txn(f"2026-03-{d:02d}", -30.0, "food") for d in range(1, 6)]
        rules = [self._make_rule("food", "daily", 50.0)]
        result = days_until_cap(txns, rules)
        _, _, _, days = result[0]
        self.assertIsNotNone(days)
        self.assertGreater(days, 0)

    def test_only_daily_rules_processed(self):
        txns = [self._make_txn("2026-03-01", -100.0, "transport")]
        rules = [self._make_rule("transport", "weekly", 300.0),
                 self._make_rule("transport", "monthly", 1000.0)]
        result = days_until_cap(txns, rules)
        self.assertEqual(result, [])

    def test_empty_rules_returns_empty(self):
        txns = [self._make_txn("2026-03-01", -50.0, "food")]
        result = days_until_cap(txns, [])
        self.assertEqual(result, [])

    def test_multiple_rules_all_returned(self):
        txns = [self._make_txn("2026-03-01", -40.0, "food"),
                self._make_txn("2026-03-01", -15.0, "transport")]
        rules = [self._make_rule("food", "daily", 50.0),
                 self._make_rule("transport", "daily", 30.0)]
        result = days_until_cap(txns, rules)
        self.assertEqual(len(result), 2)
        categories = [r[0] for r in result]
        self.assertIn("food", categories)
        self.assertIn("transport", categories)
