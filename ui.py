import calendar as cal_module
import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Any, Callable, List, Optional, Tuple

from data import (
    BUDGETS_PATH, BudgetRule, DEFAULT_CATEGORIES, Transaction, 
    load_budget_rules, load_transactions, save_budgets_bundle, 
    save_transactions, validate_amount, validate_category, validate_date
)
from stats import (
    average_daily_spending, total_spending, trend_last_n_days, 
    by_category, by_period, forecast_period_total
)
from gui_settings import load_gui_settings, pct_rules_as_tuples
from alerts import run_all_alerts, split_alert_message, compute_health_score

# --- Design System (Constants) ---
COLORS = {
    "bg": "#f5f6f8", "surface": "#ffffff", "accent": "#0d9488",
    "accent_light": "#ccfbf1", "text": "#1e293b", "text_muted": "#64748b",
    "border": "#e2e8f0", "success": "#10b981", "error": "#ef4444"
}
PAD_SM, PAD_MD, PAD_LG, PAD_XL = 4, 8, 12, 16
FONT_FAMILY = "Helvetica"
FONT_SIZE = 11
FONT_HEADING = (FONT_FAMILY, FONT_SIZE + 2, "bold")
TRANSACTIONS_FILE = "transactions.csv"
BUDGETS_FILE = str(BUDGETS_PATH)

# --- Main Application Class ---
class BudgetApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Budget Assistant")
        self.geometry("1100x760")
        self.configure(bg=COLORS["bg"])

        # Centralized State
        self.state = {
            "transactions": load_transactions(TRANSACTIONS_FILE),
            "rules": load_budget_rules(BUDGETS_FILE),
            "gui_settings": load_gui_settings(),
        }

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE))
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TButton", background=COLORS["accent"], foreground="white", padding=(PAD_MD, PAD_SM))
        style.configure("TNotebook", background=COLORS["bg"])
        style.configure("TNotebook.Tab", padding=(PAD_MD, PAD_SM))
        style.configure("Treeview", background=COLORS["surface"], fieldbackground=COLORS["surface"])

    def build_ui(self):
        # Header
        tk.Frame(self, bg=COLORS["accent"], height=4).pack(fill="x")
        title_frame = tk.Frame(self, bg=COLORS["bg"], padx=PAD_XL, pady=PAD_MD)
        title_frame.pack(fill="x")
        tk.Label(title_frame, text="Personal Budget Assistant", font=FONT_HEADING, bg=COLORS["bg"]).pack(anchor="w")

        # Tabs
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=PAD_XL, pady=(0, PAD_XL))

        # Initialize tab components
        self.summary_tab = SummaryTab(self.nb, self)
        self.add_tab = AddTransactionTab(self.nb, self)
        self.history_tab = TransactionsTab(self.nb, self)
        
        self.nb.add(self.summary_tab, text="Summary")
        self.nb.add(self.add_tab, text="Add")
        self.nb.add(self.history_tab, text="Transactions")

    def save_data(self):
        save_transactions(self.state["transactions"], TRANSACTIONS_FILE)
        save_budgets_bundle(self.state["rules"], self.state["gui_settings"], BUDGETS_FILE)

# --- Tab Component: Add Transaction ---
class AddTransactionTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=PAD_LG)
        self.app = app
        
        # Form Variables
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.amount_var = tk.StringVar()
        self.cat_var = tk.StringVar()
        self.desc_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        _tab_hero(self, "Add a Transaction", "Log your daily expenses.")
        
        card_outer, card = _surface_card_with_accent(self)
        card_outer.pack(fill="x", pady=(0, PAD_MD))

        _field_label(card, "Date")
        date_row = tk.Frame(card, bg=COLORS["surface"])
        date_row.pack(anchor="w", pady=(0, PAD_MD))
        ttk.Entry(date_row, textvariable=self.date_var, width=14).pack(side="left")
        ttk.Button(date_row, text="📅", width=3, 
                   command=lambda: show_date_picker(self, self.date_var)).pack(side="left", padx=PAD_SM)

        _field_label(card, "Amount (HKD)")
        ttk.Entry(card, textvariable=self.amount_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

        _field_label(card, "Category")
        ttk.Combobox(card, textvariable=self.cat_var, values=DEFAULT_CATEGORIES).pack(anchor="w", pady=(0, PAD_MD))

        _field_label(card, "Description")
        ttk.Entry(card, textvariable=self.desc_var, width=40).pack(anchor="w", pady=(0, PAD_LG))

        self.msg_label = tk.Label(card, text="", bg=COLORS["surface"], font=(FONT_FAMILY, FONT_SIZE))
        self.msg_label.pack(pady=PAD_SM)

        ttk.Button(self, text="Add Transaction", command=self.handle_add).pack(pady=PAD_SM)

    def handle_add(self):
        amt = validate_amount(self.amount_var.get().strip())
        if amt is None:
            self.msg_label.config(text="Invalid amount.", fg=COLORS["error"])
            return
        
        new_tx = Transaction(
            date=self.date_var.get(),
            amount=-amt,
            category=self.cat_var.get().strip().lower(),
            description=self.desc_var.get().strip()
        )
        
        self.app.state["transactions"].append(new_tx)
        self.app.save_data()
        self.amount_var.set("")
        self.desc_var.set("")
        self.msg_label.config(text="Transaction saved!", fg=COLORS["success"])

# --- Tab Component: Summary ---
class SummaryTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=PAD_LG)
        self.app = app
        self.content_frame = tk.Frame(self, bg=COLORS["bg"])
        self.content_frame.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        for w in self.content_frame.winfo_children():
            w.destroy()
        
        _tab_hero(self.content_frame, "Financial Overview", "Your current spending health.")
        # Logic to build KPI cards and graphs goes here, referencing self.app.state["transactions"]
        ttk.Button(self.content_frame, text="Update Dashboard", command=self.refresh).pack()

# --- Tab Component: Transactions ---
class TransactionsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=PAD_LG)
        self.app = app
        _tab_hero(self, "History", "Review and manage previous transactions.")
        # Build Treeview and Search logic here

# --- Utility: Date Picker (The code you provided) ---
def show_date_picker(parent: tk.Widget, target_var: tk.StringVar) -> None:
    # (Insert your calendar logic here - keep it as a standalone utility)
    pass

# --- UI Helpers (Keep these at the bottom of the file) ---
def _tab_hero(parent, title, subtitle):
    row = tk.Frame(parent, bg=COLORS["bg"])
    row.pack(fill="x", pady=(0, PAD_LG))
    tk.Label(row, text=title, font=FONT_HEADING, bg=COLORS["bg"]).pack(anchor="w")
    tk.Label(row, text=subtitle, fg=COLORS["text_muted"], bg=COLORS["bg"]).pack(anchor="w")
    tk.Frame(row, bg=COLORS["accent"], height=3).pack(fill="x", pady=(PAD_MD, 0))

def _surface_card_with_accent(parent):
    card = tk.Frame(parent, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1)
    strip = tk.Frame(card, bg=COLORS["accent"], width=4)
    strip.pack(side="left", fill="y")
    inner = tk.Frame(card, bg=COLORS["surface"], padx=PAD_LG, pady=PAD_LG)
    inner.pack(side="left", fill="both", expand=True)
    return card, inner

def _field_label(parent, text):
    tk.Label(parent, text=text, bg=COLORS["surface"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).pack(anchor="w")

if __name__ == "__main__":
    app = BudgetApp()
    app.mainloop()
