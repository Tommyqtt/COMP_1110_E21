"""
Data models and file I/O for the Personal Budget and Spending Assistant.
Handles transactions and budget rules in CSV format.
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pathlib import Path

# Default categories
DEFAULT_CATEGORIES = ["food", "transport", "subscriptions", "shopping", "other"]


@dataclass
class Transaction:
    """A single spending transaction."""
    date: str       # YYYY-MM-DD
    amount: float   # Negative for expenses
    category: str
    description: str

    def __post_init__(self):
        if self.amount > 0:
            self.amount = -abs(self.amount)  # Expenses are negative


@dataclass
class BudgetRule:
    """A budget rule for alerts."""
    category: str
    period: str     # daily, weekly, monthly
    threshold: float
    alert_type: str


def load_transactions(path: str) -> List[Transaction]:
    """Load transactions from CSV. Returns empty list if file missing or empty."""
    p = Path(path)
    if not p.exists():
        print(f"  [Info] Transactions file not found. Using empty list.")
        return []
    if p.stat().st_size == 0:
        return []

    transactions = []
    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and "date" not in (reader.fieldnames or []):
            print(f"  [Warn] Invalid CSV header in {path}. Expected: date,amount,category,description")
            return []
        for i, row in enumerate(reader):
            try:
                date_str = row.get("date", "").strip()
                amount = float(row.get("amount", 0))
                category = (row.get("category") or "").strip().lower() or "other"
                description = (row.get("description") or "").strip()
                _validate_date(date_str)
                transactions.append(Transaction(date=date_str, amount=amount, category=category, description=description))
            except (ValueError, KeyError) as e:
                print(f"  [Warn] Skipping malformed row {i + 2}: {e}")
    return transactions


def save_transactions(transactions: List[Transaction], path: str) -> None:
    """Save transactions to CSV."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "amount", "category", "description"])
        writer.writeheader()
        for t in transactions:
            writer.writerow({"date": t.date, "amount": t.amount, "category": t.category, "description": t.description})


def load_budget_rules(path: str) -> List[BudgetRule]:
    """Load budget rules from CSV. Returns empty list if file missing or empty."""
    p = Path(path)
    if not p.exists():
        print(f"  [Info] Budget rules file not found. Using empty list.")
        return []
    if p.stat().st_size == 0:
        return []

    rules = []
    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                category = (row.get("category") or "").strip().lower()
                period = (row.get("period") or "").strip().lower()
                threshold = float(row.get("threshold", 0))
                alert_type = (row.get("alert_type") or "overspend").strip()
                if not category or period not in ("daily", "weekly", "monthly"):
                    continue
                rules.append(BudgetRule(category=category, period=period, threshold=threshold, alert_type=alert_type))
            except (ValueError, KeyError) as e:
                print(f"  [Warn] Skipping malformed budget row {i + 2}: {e}")
    return rules


def save_budget_rules(rules: List[BudgetRule], path: str) -> None:
    """Save budget rules to CSV."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "period", "threshold", "alert_type"])
        writer.writeheader()
        for r in rules:
            writer.writerow({"category": r.category, "period": r.period, "threshold": r.threshold, "alert_type": r.alert_type})


def _validate_date(date_str: str) -> None:
    """Raise ValueError if date is invalid."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")


def validate_date(date_str: str) -> bool:
    """Return True if date is valid YYYY-MM-DD."""
    try:
        _validate_date(date_str)
        return True
    except ValueError:
        return False


def validate_amount(value: str) -> Optional[float]:
    """Parse and validate positive amount. Returns float or None if invalid."""
    try:
        v = float(value)
        if v <= 0:
            return None
        return v
    except ValueError:
        return None


def validate_category(category: str) -> bool:
    """Return True if category is valid (in default list or non-empty)."""
    c = (category or "").strip().lower()
    return c in DEFAULT_CATEGORIES or (len(c) > 0 and c.isalnum())
