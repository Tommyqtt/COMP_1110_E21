"""
Main CLI
"""

import sys
from typing import List, Tuple

from data import (
    BUDGETS_PATH,
    BudgetRule,
    DEFAULT_CATEGORIES,
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
)
from stats import (
    budget_utilization,
    by_category,
    by_period,
    forecast_period_total,
    format_summary,
)
from alerts import compute_health_score, run_all_alerts
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

    removed = transactions.pop(idx)
    print(f"  Deleted: {removed.date} | HK$ {abs(removed.amount):.2f} | {removed.category}")


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

    print(f"  Categories: {', '.join(DEFAULT_CATEGORIES)}")
    while True:
        category = input(f"Category [current: {t.category}, Enter to keep]: ").strip().lower()
        if not category:
            category = t.category
            break
        if validate_category(category):
            break
        print("  Invalid category. Use one from the list or a valid word.")

    desc = input(f"Description [current: {t.description}, Enter to keep]: ").strip()
    if not desc:
        desc = t.description

    transactions[idx] = Transaction(
        date=date_str, amount=-amt,
        category=category, description=desc,
    )
    print("  Transaction updated.")


def view_transactions(
    transactions: List[Transaction],
    filter_date: str = None,
    filter_category: str = None,
) -> None:
    """Display transactions, optionally filtered by date or category."""
    filtered = transactions
    if filter_date:
        filtered = [t for t in filtered if t.date == filter_date]
    if filter_category:
        filtered = [t for t in filtered if t.category == filter_category.lower()]

    if not filtered:
        print("  No transactions match.")
        return

    print(f"\n  Found {len(filtered)} transaction(s):")
    return sorted(filtered, key=lambda x: (x.date, x.amount))

def show_summaries(transactions: List[Transaction]) -> None:
    """Print summary statistics."""
    print("\n--- Summary ---")
    print(format_summary(transactions))


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


def show_health(
    transactions: List[Transaction],
    rules: List[BudgetRule],
) -> None:
    """Print the budget health score breakdown."""
    print("\n--- Budget Health ---")
    h = compute_health_score(transactions, rules)
    print(f"  Score:               {h['score']:.0f}/100 (grade {h['grade']})")
    print(f"  Max cap utilisation: {h['max_util']:.0f}%")
    print(f"  Max projected end:   {h['max_forecast']:.0f}%")
    print(f"  Categorised share:   {h['categorized_pct']:.0f}%")


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
    print("  Categories:", ", ".join(DEFAULT_CATEGORIES))

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
    """Write summaries, forecasts, health, and alerts to a plain-text file."""
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

    h = compute_health_score(transactions, rules)
    lines.append("--- Budget Health ---")
    lines.append(
        f"  Score: {h['score']:.0f}/100 (grade {h['grade']});  "
        f"max util {h['max_util']:.0f}%, projected {h['max_forecast']:.0f}%, "
        f"categorised {h['categorized_pct']:.0f}%"
    )
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


# Main menu loop


def menu() -> None:
    """Main menu loop."""
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
        print("  d. Delete a transaction")
        print("  m. Edit a transaction")
        print("  5. Summaries")
        print("  6. Alerts")
        print("  f. Forecasts (projected end-of-period)")
        print("  h. Budget health score")
        print("  7. Configure budget rule (cap)")
        print("  8. Configure % threshold alert")
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
        elif choice == "d":
            delete_transaction_interactive(transactions)
        elif choice == "m":
            edit_transaction_interactive(transactions)
        elif choice == "5":
            show_summaries(transactions)
        elif choice == "6":
            show_alerts(transactions, rules, settings)
        elif choice == "f":
            show_forecasts(transactions, rules)
        elif choice == "h":
            show_health(transactions, rules)
        elif choice == "7":
            configure_budgets(rules)
        elif choice == "8":
            configure_pct_rules(settings)
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
    from ui import run_gui
    run_gui()
