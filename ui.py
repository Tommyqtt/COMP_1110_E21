"""
Personal Budget Assistant - Tkinter GUI
COMP1110 E21 - Topic A
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import List, Callable

# Design system: colors, spacing, typography
COLORS = {
    "bg": "#f5f6f8",           # Page background
    "surface": "#ffffff",      # Card/panel background
    "accent": "#0d9488",       # Primary accent (teal)
    "accent_light": "#ccfbf1", # Accent tint
    "text": "#1e293b",         # Primary text
    "text_muted": "#64748b",   # Secondary text
    "border": "#e2e8f0",       # Borders and dividers
    "alert_bg": "#fef3c7",     # Alert/warning background
    "success": "#10b981",      # Success feedback
    "error": "#ef4444",        # Error feedback
}
PAD_SM = 4
PAD_MD = 8
PAD_LG = 12
PAD_XL = 16
FONT_FAMILY = "Helvetica"
FONT_SIZE = 11
FONT_HEADING = (FONT_FAMILY, FONT_SIZE + 2, "bold")

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
from stats import format_summary
from alerts import run_all_alerts
import portfolio

TRANSACTIONS_FILE = "transactions.csv"
BUDGETS_FILE = "budgets.csv"


def setup_styles(root: tk.Tk) -> ttk.Style:
    """Configure ttk styles for coherent look."""
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE))
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE))
    style.configure("TButton", background=COLORS["accent"], foreground="white", padding=(PAD_MD, PAD_SM))
    style.map("TButton", background=[("active", "#0f766e"), ("pressed", "#115e59")])
    style.configure("TNotebook", background=COLORS["bg"])
    style.configure("TNotebook.Tab", padding=(PAD_MD, PAD_SM))
    style.map("TNotebook.Tab", background=[("selected", COLORS["surface"])], foreground=[("selected", COLORS["accent"])])
    style.configure("Treeview", background=COLORS["surface"], foreground=COLORS["text"], fieldbackground=COLORS["surface"])
    style.configure("Treeview.Heading", background=COLORS["border"], foreground=COLORS["text"])
    return style


def run_gui() -> None:
    """Launch the Tkinter GUI."""
    root = tk.Tk()
    root.title("Personal Budget Assistant")
    root.geometry("640x500")
    root.minsize(520, 420)
    root.configure(bg=COLORS["bg"])
    setup_styles(root)

    # Shared state
    state = {
        "transactions": load_transactions(TRANSACTIONS_FILE),
        "rules": load_budget_rules(BUDGETS_FILE),
    }

    def reload_data():
        state["transactions"] = load_transactions(TRANSACTIONS_FILE)
        state["rules"] = load_budget_rules(BUDGETS_FILE)

    def save_data():
        save_transactions(state["transactions"], TRANSACTIONS_FILE)
        save_budget_rules(state["rules"], BUDGETS_FILE)

    # Header bar with accent line
    header = tk.Frame(root, bg=COLORS["accent"], height=4)
    header.pack(fill="x")
    title_frame = tk.Frame(root, bg=COLORS["bg"], padx=PAD_XL, pady=PAD_MD)
    title_frame.pack(fill="x")
    tk.Label(title_frame, text="Personal Budget Assistant", font=FONT_HEADING, bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor="w")

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=PAD_XL, pady=(0, PAD_XL))

    # Summary tab
    summary_frame = create_summary_tab(nb, state, reload_data)
    nb.add(summary_frame, text="Summary")

    # Add tab
    add_frame = create_add_tab(nb, state, save_data, reload_data)
    nb.add(add_frame, text="Add")

    # Transactions tab
    tx_frame = create_transactions_tab(nb, state, reload_data)
    nb.add(tx_frame, text="Transactions")

    # Alerts tab
    alerts_frame = create_alerts_tab(nb, state, reload_data)
    nb.add(alerts_frame, text="Alerts")

    # Portfolio tab
    portfolio_frame = create_portfolio_tab(nb)
    nb.add(portfolio_frame, text="Portfolio")

    root.mainloop()


def create_summary_tab(parent: ttk.Notebook, state: dict, reload_data: Callable) -> ttk.Frame:
    """Summary tab: totals, by category, top 3, trends."""
    frame = ttk.Frame(parent, padding=PAD_LG)
    card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_LG, pady=PAD_LG, highlightbackground=COLORS["border"], highlightthickness=1)
    card.pack(fill="both", expand=True)

    text = tk.Text(card, wrap="word", height=18, width=58, state="disabled", bg=COLORS["surface"], fg=COLORS["text"],
                   font=(FONT_FAMILY, FONT_SIZE), relief="flat", padx=PAD_MD, pady=PAD_MD)
    text.pack(fill="both", expand=True)

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=PAD_MD)
    btn = ttk.Button(frame, text="Refresh", command=lambda: _refresh_summary(text, state, reload_data))
    btn.pack(pady=PAD_SM)

    _refresh_summary(text, state, reload_data)
    return frame


def _refresh_summary(text: tk.Text, state: dict, reload_data: Callable) -> None:
    reload_data()
    text.config(state="normal")
    text.delete("1.0", "end")
    text.insert("1.0", format_summary(state["transactions"]))
    text.config(state="disabled")


def create_add_tab(parent: ttk.Notebook, state: dict, save_data: Callable, reload_data: Callable) -> ttk.Frame:
    """Add transaction tab: form with date, amount, category, description."""
    frame = ttk.Frame(parent, padding=PAD_LG)
    card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_LG, pady=PAD_LG, highlightbackground=COLORS["border"], highlightthickness=1)
    card.pack(fill="x")

    # Date
    ttk.Label(card, text="Date (YYYY-MM-DD):").pack(anchor="w")
    date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    date_entry = ttk.Entry(card, textvariable=date_var, width=15)
    date_entry.pack(anchor="w", pady=(0, PAD_MD))

    # Amount
    ttk.Label(card, text="Amount (HKD):").pack(anchor="w")
    amount_entry = ttk.Entry(card, width=15)
    amount_entry.pack(anchor="w", pady=(0, PAD_MD))

    # Category
    ttk.Label(card, text="Category:").pack(anchor="w")
    cat_var = tk.StringVar()
    cat_combo = ttk.Combobox(card, textvariable=cat_var, values=DEFAULT_CATEGORIES, width=20)
    cat_combo.pack(anchor="w", pady=(0, PAD_MD))

    # Description
    ttk.Label(card, text="Description (optional):").pack(anchor="w")
    desc_entry = ttk.Entry(card, width=40)
    desc_entry.pack(anchor="w", pady=(0, PAD_LG))

    msg_label = tk.Label(card, text="", bg=COLORS["surface"], fg=COLORS["success"], font=(FONT_FAMILY, FONT_SIZE))

    def do_add():
        date_str = date_var.get().strip()
        if not validate_date(date_str):
            msg_label.config(text="Invalid date. Use YYYY-MM-DD.", fg=COLORS["error"])
            return
        amt = validate_amount(amount_entry.get().strip())
        if amt is None:
            msg_label.config(text="Invalid amount. Enter a positive number.", fg=COLORS["error"])
            return
        category = cat_var.get().strip().lower()
        if not category:
            msg_label.config(text="Enter a category.", fg=COLORS["error"])
            return
        if not validate_category(category):
            msg_label.config(text="Invalid category.", fg=COLORS["error"])
            return
        state["transactions"].append(Transaction(
            date=date_str,
            amount=-amt,
            category=category,
            description=desc_entry.get().strip() or ""
        ))
        save_data()
        date_var.set(datetime.now().strftime("%Y-%m-%d"))
        amount_entry.delete(0, "end")
        desc_entry.delete(0, "end")
        msg_label.config(text="Transaction added.", fg=COLORS["success"])

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=PAD_MD)
    ttk.Button(frame, text="Add Transaction", command=do_add).pack(pady=PAD_SM)
    msg_label.pack(pady=PAD_SM)
    return frame


def create_transactions_tab(parent: ttk.Notebook, state: dict, reload_data: Callable) -> ttk.Frame:
    """Transactions tab: list with optional filter."""
    frame = ttk.Frame(parent, padding=PAD_LG)

    # Filters in a card
    filter_card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_MD, pady=PAD_MD, highlightbackground=COLORS["border"], highlightthickness=1)
    filter_card.pack(fill="x")
    filter_frame = tk.Frame(filter_card, bg=COLORS["surface"])
    filter_frame.pack(fill="x")
    tk.Label(filter_frame, text="Date:", bg=COLORS["surface"], fg=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE)).pack(side="left", padx=(0, PAD_SM))
    date_filter = ttk.Entry(filter_frame, width=12)
    date_filter.pack(side="left", padx=(0, PAD_MD))
    tk.Label(filter_frame, text="Category:", bg=COLORS["surface"], fg=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE)).pack(side="left", padx=(0, PAD_SM))
    cat_filter = ttk.Combobox(filter_frame, values=[""] + DEFAULT_CATEGORIES, width=12)
    cat_filter.pack(side="left", padx=(0, PAD_MD))

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=PAD_MD)

    # Treeview in card
    tree_card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_MD, pady=PAD_MD, highlightbackground=COLORS["border"], highlightthickness=1)
    tree_card.pack(fill="both", expand=True)
    columns = ("date", "amount", "category", "description")
    tree = ttk.Treeview(tree_card, columns=columns, show="headings", height=14, selectmode="browse")
    tree.heading("date", text="Date")
    tree.heading("amount", text="Amount (HKD)")
    tree.heading("category", text="Category")
    tree.heading("description", text="Description")
    tree.column("date", width=100)
    tree.column("amount", width=90)
    tree.column("category", width=100)
    tree.column("description", width=250)
    tree.pack(fill="both", expand=True)

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=PAD_MD)

    def refresh():
        reload_data()
        for item in tree.get_children():
            tree.delete(item)
        tx_list = state["transactions"]
        date_str = date_filter.get().strip()
        cat_str = cat_filter.get().strip().lower()
        if date_str:
            tx_list = [t for t in tx_list if t.date == date_str]
        if cat_str:
            tx_list = [t for t in tx_list if t.category == cat_str]
        for t in sorted(tx_list, key=lambda x: (x.date, x.amount)):
            tree.insert("", "end", values=(t.date, f"{abs(t.amount):.2f}", t.category, t.description))

    ttk.Button(frame, text="Refresh", command=refresh).pack(pady=PAD_SM)
    refresh()
    return frame


def create_alerts_tab(parent: ttk.Notebook, state: dict, reload_data: Callable) -> ttk.Frame:
    """Alerts tab: text area with alert messages."""
    frame = ttk.Frame(parent, padding=PAD_LG)
    card = tk.Frame(frame, bg=COLORS["alert_bg"], relief="flat", padx=PAD_LG, pady=PAD_LG, highlightbackground=COLORS["border"], highlightthickness=1)
    card.pack(fill="both", expand=True)

    text = tk.Text(card, wrap="word", height=18, width=58, state="disabled", bg=COLORS["alert_bg"], fg=COLORS["text"],
                   font=(FONT_FAMILY, FONT_SIZE), relief="flat", padx=PAD_MD, pady=PAD_MD)
    text.pack(fill="both", expand=True)

    def refresh():
        reload_data()
        pct_rules = [("transport", 30)]
        messages = run_all_alerts(state["transactions"], state["rules"], pct_rules=pct_rules)
        text.config(state="normal")
        text.delete("1.0", "end")
        if not messages:
            text.insert("1.0", "No alerts.")
        else:
            text.insert("1.0", "\n".join(messages))
        text.config(state="disabled")

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=PAD_MD)
    ttk.Button(frame, text="Refresh", command=refresh).pack(pady=PAD_SM)
    refresh()
    return frame


def create_portfolio_tab(parent: ttk.Notebook) -> ttk.Frame:
    """Portfolio tab: inputs and run simulation."""
    frame = ttk.Frame(parent, padding=PAD_LG)
    inputs_card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_LG, pady=PAD_LG, highlightbackground=COLORS["border"], highlightthickness=1)
    inputs_card.pack(fill="x")

    ttk.Label(inputs_card, text="Initial deposit (HKD):").pack(anchor="w")
    init_var = tk.StringVar(value="10000")
    ttk.Entry(inputs_card, textvariable=init_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

    ttk.Label(inputs_card, text="Monthly contribution (HKD):").pack(anchor="w")
    monthly_var = tk.StringVar(value="500")
    ttk.Entry(inputs_card, textvariable=monthly_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

    ttk.Label(inputs_card, text="Time horizon (months):").pack(anchor="w")
    months_var = tk.StringVar(value="12")
    ttk.Entry(inputs_card, textvariable=months_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

    ttk.Label(inputs_card, text="Risk tolerance 1-5 (1=conservative, 5=aggressive):").pack(anchor="w")
    risk_var = tk.StringVar(value="3")
    ttk.Entry(inputs_card, textvariable=risk_var, width=5).pack(anchor="w", pady=(0, PAD_LG))

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=PAD_MD)

    def run_sim():
        try:
            initial = float(init_var.get().strip())
            monthly = float(monthly_var.get().strip())
            months = int(months_var.get().strip())
            risk = int(risk_var.get().strip())
        except ValueError:
            output_text.config(state="normal")
            output_text.delete("1.0", "end")
            output_text.insert("1.0", "Invalid input. Use numbers.")
            output_text.config(state="disabled")
            return
        if initial < 0 or monthly < 0 or months <= 0 or risk < 1 or risk > 5:
            output_text.config(state="normal")
            output_text.delete("1.0", "end")
            output_text.insert("1.0", "Invalid values.")
            output_text.config(state="disabled")
            return
        assets = portfolio.load_assets(portfolio.ASSETS_FILE)
        alloc = portfolio.get_allocation(risk)
        result = portfolio.simulate(initial, monthly, months, alloc, assets)
        lines = [
            "Allocation:",
        ]
        for ac, w in alloc.items():
            if w > 0:
                lines.append(f"  {ac}: {w*100:.0f}%")
        lines.extend([
            "",
            "Simulated outcomes (1000 paths):",
            f"  P10 (pessimistic): HK$ {result['p10']:,.2f}",
            f"  P50 (typical):     HK$ {result['p50']:,.2f}",
            f"  P90 (optimistic):  HK$ {result['p90']:,.2f}",
            f"  Loss probability:  {result['loss_prob']*100:.1f}%",
        ])
        output_text.config(state="normal")
        output_text.delete("1.0", "end")
        output_text.insert("1.0", "\n".join(lines))
        output_text.config(state="disabled")

    ttk.Button(frame, text="Run Simulation", command=run_sim).pack(pady=PAD_SM)
    output_card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_LG, pady=PAD_LG, highlightbackground=COLORS["border"], highlightthickness=1)
    output_card.pack(fill="both", expand=True)
    output_text = tk.Text(output_card, wrap="word", height=10, width=52, state="disabled", bg=COLORS["surface"], fg=COLORS["text"],
                         font=(FONT_FAMILY, FONT_SIZE), relief="flat", padx=PAD_MD, pady=PAD_MD)
    output_text.pack(fill="both", expand=True)
    return frame
