"""
Test data generator for the budget assistant.
Generates realistic transaction sets for testing summaries and alerts.
Run from project root: python tests/test_generator.py
"""

import os
import random
import sys
from datetime import datetime, timedelta
from typing import List

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data import Transaction, save_transactions

DEFAULT_CATEGORIES = ["food", "transport", "subscriptions", "shopping", "other"]


def generate_transactions(
    num_days: int = 30,
    transactions_per_day: int = (2, 5),
    categories: List[str] = None,
    include_uncategorized: bool = False,
    seed: int = None,
) -> List[Transaction]:
    """
    Generate realistic test transactions.
    - num_days: span of dates
    - transactions_per_day: (min, max) range
    - categories: list of categories; defaults to DEFAULT_CATEGORIES
    - include_uncategorized: add some 'other' or empty category
    - seed: for reproducible output
    """
    if seed is not None:
        random.seed(seed)
    categories = categories or DEFAULT_CATEGORIES

    # Rough amount ranges per category (HKD)
    amounts = {
        "food": (20, 80),
        "transport": (5, 20),
        "subscriptions": (10, 150),
        "shopping": (15, 200),
        "other": (10, 100),
    }

    transactions = []
    base = datetime.now().date() - timedelta(days=num_days)

    for d in range(num_days):
        date = base + timedelta(days=d)
        date_str = date.strftime("%Y-%m-%d")
        n = random.randint(transactions_per_day[0], transactions_per_day[1])

        for _ in range(n):
            cat = random.choice(categories)
            if include_uncategorized and random.random() < 0.2:
                cat = "other"
            lo, hi = amounts.get(cat, (10, 50))
            amt = -round(random.uniform(lo, hi), 2)
            desc = f"Test {cat} {random.randint(1, 99)}"
            transactions.append(Transaction(date=date_str, amount=amt, category=cat, description=desc))

    return transactions


def generate_zero_spending(num_days: int = 7) -> List[Transaction]:
    """Edge case: no expenses (empty or minimal)."""
    return []


def generate_all_uncategorized(num_days: int = 5, seed: int = 42) -> List[Transaction]:
    """Edge case: all transactions in 'other'."""
    return generate_transactions(
        num_days=num_days,
        transactions_per_day=(1, 3),
        categories=["other"],
        include_uncategorized=False,
        seed=seed,
    )


if __name__ == "__main__":
    # Generate and save sample test data
    out_dir = os.path.join(os.path.dirname(__file__), "test_data")
    os.makedirs(out_dir, exist_ok=True)

    # Case 1: Normal 30-day data
    t1 = generate_transactions(num_days=30, seed=123)
    save_transactions(t1, os.path.join(out_dir, "case1_normal.csv"))
    print(f"Saved case1_normal.csv: {len(t1)} transactions")

    # Case 2: Zero spending
    save_transactions(generate_zero_spending(), os.path.join(out_dir, "case2_zero.csv"))
    print("Saved case2_zero.csv: 0 transactions")

    # Case 3: All uncategorized
    t3 = generate_all_uncategorized(seed=456)
    save_transactions(t3, os.path.join(out_dir, "case3_uncategorized.csv"))
    print(f"Saved case3_uncategorized.csv: {len(t3)} transactions")

    # Case 4: Heavy food spending (for daily cap alerts)
    t4 = generate_transactions(num_days=7, transactions_per_day=(3, 6),
                               categories=["food"] * 5 + ["transport"], seed=789)
    save_transactions(t4, os.path.join(out_dir, "case4_heavy_food.csv"))
    print(f"Saved case4_heavy_food.csv: {len(t4)} transactions")
