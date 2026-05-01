"""
Main CLI
"""

import argparse
import sys
from typing import List, Tuple

from data import (
    BUDGETS_PATH,
    BudgetRule,
    Transaction,
    load_budget_rules,
    load_budgets_bundle,
    load_transactions,
    save_budget_rules,
    save_budgets_bundle,
    save_transactions,
    validate_amount,
    validate_category,
    validate_date,
    validate_payment_method,
    load_categories,
    add_category,
    load_payment_methods,
    add_payment_method,
    CATEGORIES,
    PAYMENT_METHODS,
)
from stats import (
    budget_utilization,
    by_category,
    by_period,
    forecast_period_total,
    recommend_budget_caps,
    format_summary,
)
from alerts import run_all_alerts
from gui_settings import pct_rules_as_tuples

TRANSACTIONS_FILE = "transactions.csv"
BUDGETS_FILE = str(BUDGETS_PATH)


# Interactive helpers


def add_transaction_interactive(transactions: List[Transaction]) -> None:
    """Prompt the user to add a single transaction."""
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

    print(f"  Categories: {', '.join(CATEGORIES)}")
    while True:
        category = input("Category: ").strip().lower()
        if not category:
            return
        if not validate_category(category):
            print("  Invalid category. Use one from the list or add a new one with 'a'.")
            continue
        break

    description = input("Description (optional): ").strip()
    transactions.append(Transaction(
        date=date_str, amount=-amt,
        category=category, description=description or "",
    ))
    print("  Transaction added.")


def delete_transaction_interactive(transactions: List[Transaction]) -> None:
    """List transactions with index numbers and delete one by index."""
    if not transactions:
        print("  No transactions to delete.")
        return
    print("\n--- Delete Transaction ---")
    for i, t in enumerate(transactions):
        print(f"  [{i + 1}] {t.date} | HK$ {abs(t.amount):.2f} | {t.category} | {t.description}")

    raw = input("Enter index to delete (or press Enter to cancel): ").strip()
    if not raw:
        return
    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(transactions)):
            print("  Index out of range.")
            return
    except ValueError:
        print("  Invalid input.")
        return

    removed = transactions[idx]
    confirm = input(f"  Are you sure you want to delete this {removed.category} entry? (y/n): ").strip().lower()
    if confirm == 'y':
        transactions.pop(idx)
        print(f"  Confirmed. Deleted: {removed.date} | HK$ {abs(removed.amount):.2f}")
    else:
        print("  Deletion cancelled.")


def edit_transaction_interactive(transactions: List[Transaction]) -> None:
    """List transactions with index numbers and edit one by index."""
    if not transactions:
        print("  No transactions to edit.")
        return
    print("\n--- Edit Transaction ---")
    for i, t in enumerate(transactions):
        print(f"  [{i + 1}] {t.date} | HK$ {abs(t.amount):.2f} | {t.category} | {t.description}")

    raw = input("Enter index to edit (or press Enter to cancel): ").strip()
    if not raw:
        return
    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(transactions)):
            print("  Index out of range.")
            return
    except ValueError:
        print("  Invalid input.")
        return

    t = transactions[idx]

    while True:
        date_str = input(f"Date (YYYY-MM-DD) [current: {t.date}, Enter to keep]: ").strip()
        if not date_str:
            date_str = t.date
            break
        if validate_date(date_str):
            break
        print("  Invalid date. Use YYYY-MM-DD.")

    while True:
        amount_str = input(f"Amount (HKD) [current: {abs(t.amount):.2f}, Enter to keep]: ").strip()
        if not amount_str:
            amt = abs(t.amount)
            break
        parsed = validate_amount(amount_str)
        if parsed is not None:
            amt = parsed
            break
        print("  Invalid amount. Enter a positive number.")

    print(f"  Categories: {', '.join(CATEGORIES)}")
    while True:
        category = input(f"Category [current: {t.category}, Enter to keep]: ").strip().lower()
        if not category:
            category = t.category
            break
        if validate_category(category):
            break
        print("  Invalid category. Use one from the list or add a new one with 'a'.")

    desc = input(f"Description [current: {t.description}, Enter to keep]: ").strip()
    if not desc:
        desc = t.description

    while True:
        payment_method = input(f"Payment method [current: {t.payment_method}, cash/octopus/payme/credit_card, Enter to keep]: ").strip().lower()
        if not payment_method:
            payment_method = t.payment_method
            break
        if validate_payment_method(payment_method):
            break
        print("  Invalid payment method. Choose cash, octopus, payme, or credit_card.")

    transactions[idx] = Transaction(
        date=date_str,
        amount=-amt,
        category=category,
        description=desc,
        payment_method=payment_method,
    )
    print("  Transaction updated.")


def view_transactions(
    transactions: List[Transaction],
    filter_date: str = None,
    filter_category: str = None,
    filter_payment_method: str = None,
) -> None:
    """Display transactions, optionally filtered by date, category, or payment method."""
    filtered = transactions
    if filter_date:
        filtered = [t for t in filtered if t.date == filter_date]
    if filter_category:
        filtered = [t for t in filtered if t.category == filter_category.lower()]
    if filter_payment_method:
        filtered = [t for t in filtered if t.payment_method == filter_payment_method.lower()]

    if not filtered:
        print("  No transactions match.")
        return

    filtered_sorted = sorted(filtered, key=lambda x: (x.date, x.payment_method, x.amount))
    print(f"\n  Found {len(filtered_sorted)} transaction(s):")
    for t in filtered_sorted:
        print(f"  {t.date} | HK$ {abs(t.amount):.2f} | {t.category} | {t.payment_method} | {t.description}")


def show_summaries(transactions: List[Transaction]) -> None:
    """Print summary statistics."""
    print("\n--- Summary ---")
    print(format_summary(transactions))


def show_budget_recommendations(transactions: List[Transaction]) -> None:
    """Print recommended budget caps based on spending history."""
    print("\n--- Recommended Budget Caps ---")
    if not transactions:
        print("  No transactions recorded. Add expenses before requesting recommendations.")
        return

    recs = recommend_budget_caps(transactions, period="monthly", safety_factor=1.2)
    if not recs:
        print("  Not enough expense history to recommend budgets yet.")
        return

    sorted_recs = sorted(recs.items(), key=lambda x: x[1], reverse=True)
    for category, amount in sorted_recs:
        print(f"  {category}: HK$ {amount:.2f}")
    print("  Use these suggestions as a monthly budget guide.")


def _pct_rule_triplet(rule) -> Tuple[str, float, float]:
    """Coerce a 2- or 3-tuple into (category, warn%, critical%)."""
    t = tuple(rule)
    if len(t) == 2:
        return (str(t[0]).strip().lower(), float(t[1]), 0.0)
    return (str(t[0]).strip().lower(), float(t[1]), float(t[2]))


def show_alerts(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    settings: dict,
) -> None:
    """Print the combined alert feed using stored settings."""
    print("\n--- Alerts ---")
    messages = run_all_alerts(
        transactions,
        rules,
        pct_rules=pct_rules_as_tuples(settings),
        consecutive_days=int(settings.get("consecutive_overspend_days", 3)),
        subscription_creep_threshold_pct=float(settings.get("subscription_creep_threshold_pct", 20.0)),
    )
    if not messages:
        print("  No alerts. You are within all budget limits.")
    else:
        for m in messages:
            print("  " + m)


def show_forecasts(
    transactions: List[Transaction],
    rules: List[BudgetRule],
) -> None:
    """Print the projected end-of-period total for each budget rule."""
    print("\n--- Forecasts (current period) ---")
    if not rules:
        print("  No budget rules configured.")
        return
    for r in rules:
        u = budget_utilization(transactions, r)
        f = forecast_period_total(transactions, r)
        print(
            f"  {r.category} ({r.period}): "
            f"spent HK$ {u['spent']:.2f}/{r.threshold:.2f} "
            f"({u['pct']:.0f}%), "
            f"day {u['days_elapsed']}/{u['days_total']} -> "
            f"projected HK$ {f['forecast']:.2f} "
            f"({f['forecast_pct']:.0f}% of cap)"
        )


def configure_budgets(rules: List[BudgetRule]) -> None:
    """Add a budget rule interactively."""
    print("\n--- Configure Budget Rule ---")
    print("Categories:", ", ".join(CATEGORIES))

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

    rules.append(BudgetRule(
        category=category, period=period,
        threshold=threshold, alert_type="overspend",
    ))
    print("  Budget rule added.")


def configure_pct_rules(settings: dict) -> None:
    """
    Add or update a percentage threshold alert rule and persist it to settings.
    Fires when a category exceeds the chosen share of total spending.
    """
    print("\n--- Configure Percentage Alert ---")
    print("  This fires an alert when a category exceeds X% of total spending.")
    print("  Categories:", ", ".join(CATEGORIES))

    category = input("Category: ").strip().lower()
    if not category:
        return

    try:
        max_pct = float(input("Max % of total spending (e.g. 30): ").strip())
        if not (0 < max_pct <= 100):
            print("  Must be between 0 and 100.")
            return
    except ValueError:
        print("  Invalid number.")
        return

    raw = settings.setdefault("pct_rules", [])
    raw[:] = [r for r in raw if str(r[0]).strip().lower() != category]
    raw.append([category, max_pct, 0.0])
    print(f"  Alert set: {category} > {max_pct:.0f}% of total will trigger a warning.")
    print("  (Use 's' to save so it persists between runs.)")


def export_report(
    transactions: List[Transaction],
    rules: List[BudgetRule],
    settings: dict,
) -> None:
    """Write summaries, forecasts, and alerts to a plain-text file."""
    filename = input("  Output filename (e.g. report.txt): ").strip()
    if not filename:
        filename = "report.txt"

    lines: List[str] = []
    lines.append("=" * 50)
    lines.append("  Personal Budget Report")
    lines.append("=" * 50)
    lines.append("")
    lines.append(format_summary(transactions))
    lines.append("")

    lines.append("--- Forecasts ---")
    if not rules:
        lines.append("  No budget rules configured.")
    else:
        for r in rules:
            u = budget_utilization(transactions, r)
            f = forecast_period_total(transactions, r)
            lines.append(
                f"  {r.category} ({r.period}): spent HK$ {u['spent']:.2f}/"
                f"{r.threshold:.2f} ({u['pct']:.0f}%), day "
                f"{u['days_elapsed']}/{u['days_total']} -> projected HK$ "
                f"{f['forecast']:.2f} ({f['forecast_pct']:.0f}% of cap)"
            )
    lines.append("")

    lines.append("--- Alerts ---")
    alerts = run_all_alerts(
        transactions, rules,
        pct_rules=pct_rules_as_tuples(settings),
        consecutive_days=int(settings.get("consecutive_overspend_days", 3)),
        subscription_creep_threshold_pct=float(settings.get("subscription_creep_threshold_pct", 20.0)),
    )
    if alerts:
        for a in alerts:
            lines.append("  " + a)
    else:
        lines.append("  No alerts.")

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"  Report saved to {filename}")
    except OSError as e:
        print(f"  Could not save report: {e}")

def manage_categories() -> None:
    """Manage custom categories interactively."""
    while True:
        print("\n--- Manage Categories ---")
        print(f"Current categories ({len(CATEGORIES)}): {', '.join(CATEGORIES)}")
        print("\nOptions:")
        print("  1. Add a new category")
        print("  2. View all categories")
        print("  3. Back to menu")
        
        choice = input("Choice: ").strip().lower()
        
        if choice == "1":
            new_cat = input("  Enter new category name: ").strip().lower()
            if new_cat:
                if add_category(new_cat):
                    print(f"  ✓ Category '{new_cat}' added successfully.")
                else:
                    print(f"  ✗ Category '{new_cat}' already exists.")
            else:
                print("  ✗ Invalid category name.")
        elif choice == "2":
            print(f"\n  All categories ({len(CATEGORIES)}):")
            for i, cat in enumerate(CATEGORIES, 1):
                print(f"    {i}. {cat}")
        elif choice == "3":
            return
        else:
            print("  Unknown option. Please try again.")
        
        again = input("\n  Continue managing categories? (y/n): ").strip().lower()
        if again != "y":
            return


def manage_payment_methods() -> None:
    """Manage custom payment methods interactively."""
    while True:
        print("\n--- Manage Payment Methods ---")
        print(f"Current payment methods ({len(PAYMENT_METHODS)}): {', '.join(PAYMENT_METHODS)}")
        print("\nOptions:")
        print("  1. Add a new payment method")
        print("  2. View all payment methods")
        print("  3. Back to menu")
        
        choice = input("Choice: ").strip().lower()
        
        if choice == "1":
            new_method = input("  Enter new payment method name: ").strip().lower()
            if new_method:
                if add_payment_method(new_method):
                    print(f"  ✓ Payment method '{new_method}' added successfully.")
                else:
                    print(f"  ✗ Payment method '{new_method}' already exists.")
            else:
                print("  ✗ Invalid payment method name.")
        elif choice == "2":
            print(f"\n  All payment methods ({len(PAYMENT_METHODS)}):")
            for i, method in enumerate(PAYMENT_METHODS, 1):
                print(f"    {i}. {method}")
        elif choice == "3":
            return
        else:
            print("  Unknown option. Please try again.")
        
        again = input("\n  Continue managing payment methods? (y/n): ").strip().lower()
        if again != "y":
            return

# Main menu loop


def menu() -> None:
    """Main menu loop."""
    load_categories()  # Load custom categories at startup
    load_payment_methods()  # Load custom payment methods at startup
    transactions = load_transactions(TRANSACTIONS_FILE)
    rules, settings = load_budgets_bundle(BUDGETS_FILE)

    try:
        import portfolio
        has_portfolio = True
    except ImportError:
        has_portfolio = False

    while True:
        print("\n" + "=" * 44)
        print("   Personal Budget Assistant")
        print("=" * 44)
        print("  1. Add transaction")
        print("  2. View all transactions")
        print("  3. View by date")
        print("  4. View by category")
        print("  pm. View by payment method")
        print("  d. Delete a transaction")
        print("  m. Edit a transaction")
        print("  5. Summaries")
        print("  6. Alerts")
        print("  f. Forecasts (projected end-of-period)")
        print("  7. Configure budget rule (cap)")
        print("  8. Configure % threshold alert")
        print("  r. Recommend budget caps")
        print("  c. Manage categories")
        print("  y. Manage payment methods")
        print("  9. Load data")
        print("  s. Save data")
        print("  e. Export report to file")
        if has_portfolio:
            print("  p. Portfolio (MockWealth)")
        print("  q. Quit")
        print("=" * 44)

        choice = input("Choice: ").strip().lower()
        if not choice:
            continue

        if choice == "1":
            add_transaction_interactive(transactions)
        elif choice == "2":
            view_transactions(transactions)
        elif choice == "3":
            d = input("  Date (YYYY-MM-DD): ").strip()
            if validate_date(d):
                view_transactions(transactions, filter_date=d)
            else:
                print("  Invalid date.")
        elif choice == "4":
            c = input("  Category: ").strip()
            if c:
                view_transactions(transactions, filter_category=c)
        elif choice in ("pm", "payment", "method"):
            print(f"  Available payment methods: {', '.join(PAYMENT_METHODS)}")
            method = input("  Payment method: ").strip().lower()
            if not validate_payment_method(method):
                print("  Invalid payment method.")
            else:
                view_transactions(transactions, filter_payment_method=method)
        elif choice in ("d", "delete"):
            delete_transaction_interactive(transactions)
        elif choice in ("m", "edit"):
            edit_transaction_interactive(transactions)
        elif choice == "5":
            show_summaries(transactions)
        elif choice == "6":
            show_alerts(transactions, rules, settings)
        elif choice == "f":
            show_forecasts(transactions, rules)
        elif choice == "7":
            configure_budgets(rules)
        elif choice == "8":
            configure_pct_rules(settings)
        elif choice == "r":
            show_budget_recommendations(transactions)
        elif choice == "c":
            manage_categories()
        elif choice == "y":
            manage_payment_methods()
        elif choice == "9":
            transactions = load_transactions(TRANSACTIONS_FILE)
            rules, settings = load_budgets_bundle(BUDGETS_FILE)
            print("  Data loaded.")
        elif choice == "s":
            save_transactions(transactions, TRANSACTIONS_FILE)
            settings = save_budgets_bundle(rules, settings, BUDGETS_FILE)
            print("  Data saved.")
        elif choice == "e":
            export_report(transactions, rules, settings)
        elif has_portfolio and choice == "p":
            portfolio.run_portfolio_menu()
        elif choice in ("q", "quit"):
            save = input("Save before quit? (y/n): ").strip().lower()
            if save == "y":
                save_transactions(transactions, TRANSACTIONS_FILE)
                save_budgets_bundle(rules, settings, BUDGETS_FILE)
                print("  Saved.")
            print("Goodbye.")
            break
        else:
            print("  Unknown option. Please try again.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Personal Budget Assistant")
    parser.add_argument("--gui", action="store_true", help="Launch GUI (default)")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode instead of GUI")
    parser.add_argument("--transactions", default=None, help="Path to transactions CSV file")
    parser.add_argument("--budgets", default=None, help="Path to budgets CSV file")
    args = parser.parse_args()

    if args.transactions:
        TRANSACTIONS_FILE = args.transactions
    if args.budgets:
        BUDGETS_FILE = args.budgets

    if args.cli:
        menu()
    else:
        from ui import run_gui
        run_gui(TRANSACTIONS_FILE, BUDGETS_FILE)
