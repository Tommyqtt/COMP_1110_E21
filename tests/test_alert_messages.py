"""split_alert_message pairs alert strings with GUI banner kinds."""

import unittest

from alerts import split_alert_message


class TestSplitAlertMessage(unittest.TestCase):
    def test_overspend(self) -> None:
        m = (
            "[OVERSPEND] FOOD exceeded daily cap (HK$ 50.00) in 2026-04-01: "
            "spent HK$ 70.00  (+HK$ 20.00 over)"
        )
        k, b = split_alert_message(m)
        self.assertEqual(k, "overspend")
        self.assertNotIn("[OVERSPEND]", b)
        self.assertIn("FOOD", b)

    def test_budget_pct_legacy(self) -> None:
        m = "[BUDGET %] TRANSPORT is 45.0% of total spending (limit: 30%)"
        k, b = split_alert_message(m)
        self.assertEqual(k, "budget_pct")
        self.assertIn("TRANSPORT", b)

    def test_budget_pct_warn(self) -> None:
        m = "[BUDGET % WARN] TRANSPORT is 35.0% of total spending (..."
        k, b = split_alert_message(m)
        self.assertEqual(k, "budget_pct_warn")
        self.assertIn("TRANSPORT", b)

    def test_budget_pct_critical(self) -> None:
        m = "[BUDGET % CRITICAL] FOOD is 55.0% of total spending " "(critical if above 50%; warning from 30%)"
        k, b = split_alert_message(m)
        self.assertEqual(k, "budget_pct_critical")
        self.assertIn("FOOD", b)

    def test_streak(self) -> None:
        m = "[STREAK] FOOD exceeded daily cap (HK$ 1.00) for 3 consecutive day(s). Consider reviewing your food habits."
        k, b = split_alert_message(m)
        self.assertEqual(k, "streak")
        self.assertNotIn("[STREAK]", b)

    def test_uncategorized(self) -> None:
        m = "[UNCATEGORIZED] 2 transaction(s) are in the 'other' category."
        k, b = split_alert_message(m)
        self.assertEqual(k, "uncategorized")
        self.assertIn("2 transaction", b)

    def test_subscription_creep(self) -> None:
        m = "[SUBSCRIPTION CREEP] Subscription spending rose 25.0% from 2026-03 (HK$ 100.00) to 2026-04 (HK$ 125.00)."
        k, b = split_alert_message(m)
        self.assertEqual(k, "subscription_creep")
        self.assertIn("25.0%", b)

    def test_general_untagged(self) -> None:
        k, b = split_alert_message("Something unexpected.")
        self.assertEqual(k, "general")
        self.assertEqual(b, "Something unexpected.")


if __name__ == "__main__":
    unittest.main()
