"""
Personal Budget and Spending Assistant - Main CLI
COMP1110 E21 - Topic A
"""

import sys
from typing import List

from data import (
    BudgetRule,
    DEFAULT_CATEGORIES,
    Transaction,
    load_budget_rules,
    load_transactions,
    save_budget_rules,
    save_transactions,
    validate_amount,
    validate_category,
    validate_date,
)
from stats import format_summary, by_category, by_period
from alerts import run_all_alerts

# Default file paths
TRANSACTIONS_FILE = "transactions.csv"
BUDGETS_FILE = "budgets.csv"


def add_transaction_interactive(transactions: List[Transaction]) -> None:
    """Prompt user to add a transaction."""
    print("\n--- Add Transaction ---")
    while True:
        date_str = input("Date (YYYY-MM-DD): ").strip()
        if not date_str:
            return
        if not validate_date(date_str):
            print("  Invalid date. Use YYYY-MM-DD.")
            continue
        break

    while True:
        amount_str = input("Amount (HKD): ").strip()
        if not amount_str:
            return
        amt = validate_amount(amount_str)
        if amt is None:
            print("  Invalid amount. Enter a positive number.")
            continue
        break

    print(f"  Categories: {', '.join(DEFAULT_CATEGORIES)}")
    while True:
        category = input("Category: ").strip().lower()
        if not category:
            return
        if not validate_category(category):
            print("  Invalid category. Use one from the list or a valid word.")
            continue
        break

    description = input("Description (optional): ").strip()
    transactions.append(Transaction(
        date=date_str,
        amount=-amt,
        category=category,
        description=description or ""
    ))
    print("  Transaction added.")


def view_transactions(transactions: List[Transaction], filter_date: str = None, filter_category: str = None) -> None:
    """Display transactions, optionally filtered."""
    filtered = transactions
    if filter_date:
        filtered = [t for t in filtered if t.date == filter_date]
    if filter_category:
        filtered = [t for t in filtered if t.category == filter_category.lower()]

    if not filtered:
        print("  No transactions match.")
        return
    print(f"\n  Found {len(filtered)} transaction(s):")
    for t in sorted(filtered, key=lambda x: (x.date, x.amount)):
        print(f"    {t.date} | HK$ {abs(t.amount):.2f} | {t.category} | {t.description}")


def show_summaries(transactions: List[Transaction]) -> None:
    """Display summary statistics."""
    print("\n--- Summary ---")
    print(format_summary(transactions))


def show_alerts(transactions: List[Transaction], rules: List[BudgetRule]) -> None:
    """Display alerts."""
    print("\n--- Alerts ---")
    pct_rules = [("transport", 30)]  # Example: transport > 30% of total
    messages = run_all_alerts(transactions, rules, pct_rules=pct_rules)
    if not messages:
        print("  No alerts.")
    else:
        for m in messages:
            print("  " + m)


def configure_budgets(rules: List[BudgetRule]) -> None:
    """Add a budget rule interactively."""
    print("\n--- Configure Budget Rule ---")
    print("Categories:", ", ".join(DEFAULT_CATEGORIES))
    category = input("Category: ").strip().lower()
    if not category:
        return
    period = input("Period (daily/weekly/monthly): ").strip().lower()
    if period not in ("daily", "weekly", "monthly"):
        print("  Invalid period.")
        return
    try:
        threshold = float(input("Threshold (HKD): ").strip())
        if threshold <= 0:
            print("  Invalid threshold.")
            return
    except ValueError:
        print("  Invalid number.")
        return
    rules.append(BudgetRule(category=category, period=period, threshold=threshold, alert_type="overspend"))
    print("  Budget rule added.")


def menu() -> None:
    """Main menu loop."""
    transactions = load_transactions(TRANSACTIONS_FILE)
    rules = load_budget_rules(BUDGETS_FILE)

    try:
        import portfolio
        has_portfolio = True
    except ImportError:
        has_portfolio = False

    while True:
        print("\n" + "=" * 40)
        print("  Personal Budget Assistant")
        print("=" * 40)
        print("  1. Add transaction")
        print("  2. View all transactions")
        print("  3. View by date")
        print("  4. View by category")
        print("  5. Summaries")
        print("  6. Alerts")
        print("  7. Configure budget rule")
        print("  8. Load data")
        print("  9. Save data")
        if has_portfolio:
            print("  p. Portfolio (MockWealth)")
        print("  q. Quit")
        print("=" * 40)

        choice = input("Choice: ").strip().lower()
        if not choice:
            continue

        if choice == "1":
            add_transaction_interactive(transactions)
        elif choice == "2":
            view_transactions(transactions)
        elif choice == "3":
            d = input("Date (YYYY-MM-DD): ").strip()
            if validate_date(d):
                view_transactions(transactions, filter_date=d)
            else:
                print("  Invalid date.")
        elif choice == "4":
            c = input("Category: ").strip()
            if c:
                view_transactions(transactions, filter_category=c)
        elif choice == "5":
            show_summaries(transactions)
        elif choice == "6":
            show_alerts(transactions, rules)
        elif choice == "7":
            configure_budgets(rules)
        elif choice == "8":
            transactions = load_transactions(TRANSACTIONS_FILE)
            rules = load_budget_rules(BUDGETS_FILE)
            print("  Data loaded.")
        elif choice == "9":
            save_transactions(transactions, TRANSACTIONS_FILE)
            save_budget_rules(rules, BUDGETS_FILE)
            print("  Data saved.")
        elif has_portfolio and choice == "p":
            portfolio.run_portfolio_menu()
        elif choice in ("q", "quit"):
            save = input("Save before quit? (y/n): ").strip().lower()
            if save == "y":
                save_transactions(transactions, TRANSACTIONS_FILE)
                save_budget_rules(rules, BUDGETS_FILE)
                print("  Saved.")
            print("Goodbye.")
            break
        else:
            print("  Unknown option.")


if __name__ == "__main__":
    if "--gui" in sys.argv or "-g" in sys.argv:
        from ui import run_gui
        run_gui()
    else:
        menu()
