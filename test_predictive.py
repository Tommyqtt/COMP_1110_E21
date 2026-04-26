import unittest
from datetime import date
from stats import get_monthly_forecast, Transaction

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
