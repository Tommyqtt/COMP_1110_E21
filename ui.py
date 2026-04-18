"""
Personal Budget Assistant - Tkinter GUI
COMP1110 E21 - Topic A
"""

import calendar as cal_module
import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Any, Callable, List, Optional

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
FONT_SECTION = (FONT_FAMILY, FONT_SIZE + 1, "bold")
FONT_KPI = (FONT_FAMILY, 20, "bold")

# Distinct colors for category bars (unknown categories cycle by hash)
_CATEGORY_BAR_COLORS = (
    "#0d9488", "#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899",
    "#14b8a6", "#6366f1", "#84cc16", "#f43f5e",
)

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
from stats import (
    average_daily_spending,
    by_category,
    by_period,
    top_categories,
    total_spending,
    trend_last_n_days,
)
from alerts import run_all_alerts
import portfolio

TRANSACTIONS_FILE = "transactions.csv"
BUDGETS_FILE = "budgets.csv"

_MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _parse_ymd(s: str) -> Optional[tuple]:
    """Return (year, month, day) if s is valid YYYY-MM-DD, else None."""
    s = (s or "").strip()
    if len(s) != 10:
        return None
    try:
        t = datetime.strptime(s, "%Y-%m-%d")
        return t.year, t.month, t.day
    except ValueError:
        return None


def show_date_picker(parent: tk.Widget, target_var: tk.StringVar) -> None:
    """Small calendar popup; sets target_var to YYYY-MM-DD when a day is chosen."""
    parsed = _parse_ymd(target_var.get())
    if parsed:
        cur_y, cur_m, cur_d = parsed
    else:
        now = datetime.now()
        cur_y, cur_m, cur_d = now.year, now.month, now.day

    win = tk.Toplevel(parent)
    win.title("Pick date")
    win.resizable(False, False)
    win.configure(bg=COLORS["surface"])
    top = parent.winfo_toplevel()
    win.transient(top)
    win.grab_set()

    nav = tk.Frame(win, bg=COLORS["surface"])
    nav.pack(fill="x", padx=PAD_SM, pady=PAD_SM)

    month_holder = {"y": cur_y, "m": cur_m}

    header = tk.Label(nav, text="", bg=COLORS["surface"], fg=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE, "bold"))

    def update_header():
        header.config(text=f"{_MONTH_NAMES[month_holder['m'] - 1]} {month_holder['y']}")

    def shift_month(delta: int) -> None:
        y, m = month_holder["y"], month_holder["m"]
        m += delta
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        month_holder["y"], month_holder["m"] = y, m
        update_header()
        rebuild_days()

    ttk.Button(nav, text="◀", width=3, command=lambda: shift_month(-1)).pack(side="left", padx=2)
    header.pack(side="left", expand=True)
    ttk.Button(nav, text="▶", width=3, command=lambda: shift_month(1)).pack(side="left", padx=2)

    cal_area = tk.Frame(win, bg=COLORS["surface"])
    cal_area.pack(fill="both", expand=True, padx=PAD_SM, pady=(0, PAD_SM))
    day_buttons: List[tk.Widget] = []

    def rebuild_days():
        for b in day_buttons:
            b.destroy()
        day_buttons.clear()
        for c in range(7):
            wd = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[c]
            tk.Label(cal_area, text=wd, bg=COLORS["surface"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).grid(row=0, column=c, padx=1, pady=1)
        y, m = month_holder["y"], month_holder["m"]
        weeks = cal_module.monthcalendar(y, m)
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    tk.Label(cal_area, text="", bg=COLORS["surface"]).grid(row=r, column=c, padx=1, pady=1)
                    continue

                def pick(d: int = day) -> None:
                    target_var.set(f"{y}-{m:02d}-{d:02d}")
                    win.grab_release()
                    win.destroy()

                b = ttk.Button(cal_area, text=str(day), width=3, command=pick)
                b.grid(row=r, column=c, padx=1, pady=1)
                day_buttons.append(b)

    update_header()
    rebuild_days()

    btn_row = tk.Frame(win, bg=COLORS["surface"])
    btn_row.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))

    def today():
        n = datetime.now()
        month_holder["y"], month_holder["m"] = n.year, n.month
        update_header()
        rebuild_days()

    ttk.Button(btn_row, text="This month", command=today).pack(side="left")

    def cancel():
        win.grab_release()
        win.destroy()

    ttk.Button(btn_row, text="Cancel", command=cancel).pack(side="right")
    win.protocol("WM_DELETE_WINDOW", cancel)


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
    root.geometry("720x560")
    root.minsize(560, 440)
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
    tx_frame, refresh_transactions_view = create_transactions_tab(nb, state, reload_data, save_data)
    nb.add(tx_frame, text="Transactions")

    def on_notebook_tab_change(_event=None) -> None:
        try:
            if nb.tab(nb.select(), "text") == "Transactions":
                refresh_transactions_view()
        except tk.TclError:
            pass

    nb.bind("<<NotebookTabChanged>>", on_notebook_tab_change)

    # Alerts tab
    alerts_frame = create_alerts_tab(nb, state, reload_data)
    nb.add(alerts_frame, text="Alerts")

    # Portfolio tab
    portfolio_frame = create_portfolio_tab(nb)
    nb.add(portfolio_frame, text="Portfolio")

    root.mainloop()


def _category_bar_color(name: str) -> str:
    h = sum(ord(c) for c in name.lower())
    return _CATEGORY_BAR_COLORS[h % len(_CATEGORY_BAR_COLORS)]


def _canvas_mousewheel_handler(canvas: tk.Canvas):
    """Return a handler that scrolls *canvas* vertically from a mouse wheel event."""

    def on_wheel(event) -> Optional[str]:
        delta = 0
        if event.num == 5:
            delta = 1
        elif event.num == 4:
            delta = -1
        elif getattr(event, "delta", 0):
            if sys.platform == "darwin":
                delta = -event.delta
            else:
                delta = -1 if event.delta > 0 else 1
        if delta:
            canvas.yview_scroll(delta, "units")
            return "break"
        return None

    return on_wheel


def _bind_mousewheel_to_canvas_and_content(canvas: tk.Canvas, content: tk.Widget) -> None:
    """
    Wheel events hit the widget under the cursor; inner labels/frames do not bubble to the canvas.
    Bind the same scroll handler on the canvas and recursively on all descendants of content.
    """
    handler = _canvas_mousewheel_handler(canvas)
    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        canvas.bind(seq, handler)

    def bind_descendants(w: tk.Widget) -> None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            w.bind(seq, handler)
        for child in w.winfo_children():
            bind_descendants(child)

    bind_descendants(content)


def _kpi_card(parent: tk.Widget, title: str, value: str, subtitle: str = "") -> tk.Frame:
    card = tk.Frame(parent, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1)
    strip = tk.Frame(card, bg=COLORS["accent"], width=4)
    strip.pack(side="left", fill="y")
    box = tk.Frame(card, bg=COLORS["surface"], padx=PAD_MD, pady=PAD_MD)
    box.pack(side="left", fill="both", expand=True)
    tk.Label(
        box, text=title, bg=COLORS["surface"], fg=COLORS["text_muted"],
        font=(FONT_FAMILY, FONT_SIZE - 1),
    ).pack(anchor="w")
    tk.Label(
        box, text=value, bg=COLORS["surface"], fg=COLORS["text"],
        font=FONT_KPI,
    ).pack(anchor="w", pady=(2, 0))
    if subtitle:
        tk.Label(
            box, text=subtitle, bg=COLORS["surface"], fg=COLORS["accent"],
            font=(FONT_FAMILY, FONT_SIZE - 1),
        ).pack(anchor="w")
    return card


def _section_header(parent: tk.Widget, title: str, emoji: str = "") -> None:
    row = tk.Frame(parent, bg=COLORS["bg"])
    row.pack(fill="x", pady=(PAD_XL, PAD_MD))
    label = f"{emoji} {title}".strip() if emoji else title
    tk.Label(row, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=FONT_SECTION).pack(anchor="w")
    bar = tk.Frame(row, bg=COLORS["accent"], height=2)
    bar.pack(fill="x", pady=(PAD_SM, 0))


def _category_row(parent: tk.Widget, name: str, amount: float, pct: float, bar_width: int = 200) -> None:
    row = tk.Frame(parent, bg=COLORS["bg"])
    row.pack(fill="x", pady=PAD_SM)
    tk.Label(
        row, text=name.capitalize(), bg=COLORS["bg"], fg=COLORS["text"],
        font=(FONT_FAMILY, FONT_SIZE), width=11, anchor="w",
    ).pack(side="left")
    track = tk.Frame(row, bg=COLORS["border"], height=12, width=bar_width)
    track.pack(side="left", padx=(PAD_SM, PAD_SM), pady=2)
    track.pack_propagate(False)
    fill_w = max(2, int(bar_width * (pct / 100.0)))
    tk.Frame(track, bg=_category_bar_color(name), height=12, width=fill_w).place(x=0, y=0, relheight=1)
    tk.Label(
        row, text=f"{pct:.0f}%", bg=COLORS["bg"], fg=COLORS["accent"],
        font=(FONT_FAMILY, FONT_SIZE, "bold"), width=5, anchor="e",
    ).pack(side="right", padx=(0, PAD_SM))
    tk.Label(
        row, text=f"HK$ {amount:,.2f}", bg=COLORS["bg"], fg=COLORS["text_muted"],
        font=(FONT_FAMILY, FONT_SIZE), width=12, anchor="e",
    ).pack(side="right")


def _mini_stat_row(parent: tk.Widget, label: str, amount: float) -> None:
    row = tk.Frame(parent, bg=COLORS["accent_light"], padx=PAD_MD, pady=PAD_SM)
    row.pack(fill="x", pady=PAD_SM)
    tk.Label(
        row, text=label, bg=COLORS["accent_light"], fg=COLORS["text"],
        font=(FONT_FAMILY, FONT_SIZE),
    ).pack(side="left")
    tk.Label(
        row, text=f"HK$ {amount:,.2f}", bg=COLORS["accent_light"], fg=COLORS["accent"],
        font=(FONT_FAMILY, FONT_SIZE, "bold"),
    ).pack(side="right")


def _refresh_summary_dashboard(
    content: tk.Frame,
    state: dict,
    reload_data: Callable,
    canvas: tk.Canvas,
) -> None:
    reload_data()
    for w in content.winfo_children():
        w.destroy()

    txs = state["transactions"]
    if not txs:
        empty = tk.Frame(content, bg=COLORS["surface"], padx=PAD_XL, pady=PAD_XL,
                         highlightbackground=COLORS["border"], highlightthickness=1)
        empty.pack(fill="both", expand=True, pady=PAD_MD)
        tk.Label(
            empty,
            text="No transactions yet",
            bg=COLORS["surface"], fg=COLORS["text"],
            font=FONT_HEADING,
        ).pack(pady=(PAD_LG, PAD_SM))
        tk.Label(
            empty,
            text="Add a few expenses on the Add tab to see spending insights here.",
            bg=COLORS["surface"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, FONT_SIZE), wraplength=400, justify="center",
        ).pack()
        _bind_mousewheel_to_canvas_and_content(canvas, content)
        return

    total = total_spending(txs)
    n_tx = len(txs)
    avg_day = average_daily_spending(txs)
    t7 = trend_last_n_days(txs, 7)
    t30 = trend_last_n_days(txs, 30)

    hero = tk.Frame(content, bg=COLORS["bg"])
    hero.pack(fill="x")
    hero.grid_columnconfigure(0, weight=1)
    hero.grid_columnconfigure(1, weight=1)
    hero.grid_columnconfigure(2, weight=1)

    def _fmt_hk(x: float) -> str:
        return f"HK$ {x:,.2f}"

    _kpi_card(hero, "Total spending", _fmt_hk(total), f"{n_tx} transactions").grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM))
    _kpi_card(hero, "Avg. per active day", _fmt_hk(avg_day), "Days with at least one expense").grid(row=0, column=1, sticky="nsew", padx=PAD_SM)
    _kpi_card(hero, "Last 7 days", _fmt_hk(t7), "Rolling window").grid(row=0, column=2, sticky="nsew", padx=(PAD_SM, 0))

    _section_header(content, "Spending by category")

    cats = by_category(txs)
    for cat, amt in sorted(cats.items(), key=lambda x: x[1], reverse=True):
        pct = (amt / total * 100.0) if total else 0.0
        _category_row(content, cat, amt, pct)

    _section_header(content, "Momentum")
    trend_card = tk.Frame(content, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1)
    trend_card.pack(fill="x", pady=(0, PAD_SM))
    inner_t = tk.Frame(trend_card, bg=COLORS["surface"], padx=PAD_LG, pady=PAD_MD)
    inner_t.pack(fill="x")
    _mini_stat_row(inner_t, "Last 7 days (from latest activity)", t7)
    _mini_stat_row(inner_t, "Last 30 days (from latest activity)", t30)

    _section_header(content, "Top categories")
    top = top_categories(txs, 3)
    medals = ("🥇", "🥈", "🥉")
    top_box = tk.Frame(content, bg=COLORS["bg"])
    top_box.pack(fill="x")
    for i, (cat, amt) in enumerate(top):
        row = tk.Frame(top_box, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1)
        row.pack(fill="x", pady=PAD_SM)
        inn = tk.Frame(row, bg=COLORS["surface"], padx=PAD_MD, pady=PAD_SM)
        inn.pack(fill="x")
        badge = medals[i] if i < len(medals) else "•"
        tk.Label(
            inn, text=f"{badge}  {cat.capitalize()}", bg=COLORS["surface"], fg=COLORS["text"],
            font=(FONT_FAMILY, FONT_SIZE + 1, "bold"),
        ).pack(side="left")
        tk.Label(
            inn, text=f"HK$ {amt:,.2f}", bg=COLORS["surface"], fg=COLORS["accent"],
            font=(FONT_FAMILY, FONT_SIZE, "bold"),
        ).pack(side="right")

    monthly = by_period(txs, "monthly")
    if monthly:
        _section_header(content, "Recent months")
        for key in sorted(monthly.keys())[-3:]:
            _mini_stat_row(content, str(key), monthly[key])

    _bind_mousewheel_to_canvas_and_content(canvas, content)


def create_summary_tab(parent: ttk.Notebook, state: dict, reload_data: Callable) -> ttk.Frame:
    """Summary tab: KPI cards, category bars, trends."""
    outer = ttk.Frame(parent, padding=PAD_LG)

    scroll_wrap = tk.Frame(outer, bg=COLORS["bg"])
    scroll_wrap.pack(fill="both", expand=True)
    canvas = tk.Canvas(scroll_wrap, bg=COLORS["bg"], highlightthickness=0)
    vsb = ttk.Scrollbar(scroll_wrap, orient="vertical", command=canvas.yview)
    content = tk.Frame(canvas, bg=COLORS["bg"])
    inner_win = canvas.create_window((0, 0), window=content, anchor="nw")

    def on_canvas_configure(event: Any) -> None:
        canvas.itemconfigure(inner_win, width=event.width)

    canvas.bind("<Configure>", on_canvas_configure)

    def on_content_configure(_event: Any) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    content.bind("<Configure>", on_content_configure)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=PAD_MD)
    ttk.Button(
        outer,
        text="Refresh",
        command=lambda: _refresh_summary_dashboard(content, state, reload_data, canvas),
    ).pack(pady=PAD_SM)

    _refresh_summary_dashboard(content, state, reload_data, canvas)
    return outer


def create_add_tab(parent: ttk.Notebook, state: dict, save_data: Callable, reload_data: Callable) -> ttk.Frame:
    """Add transaction tab: form with date, amount, category, description."""
    frame = ttk.Frame(parent, padding=PAD_LG)
    card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_LG, pady=PAD_LG, highlightbackground=COLORS["border"], highlightthickness=1)
    card.pack(fill="x")

    # Date
    ttk.Label(card, text="Date (YYYY-MM-DD):").pack(anchor="w")
    date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    date_row = tk.Frame(card, bg=COLORS["surface"])
    date_row.pack(anchor="w", pady=(0, PAD_MD))
    ttk.Entry(date_row, textvariable=date_var, width=14).pack(side="left")
    ttk.Button(date_row, text="📅", width=3, command=lambda: show_date_picker(card, date_var)).pack(side="left", padx=(PAD_SM, 0))

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


def create_transactions_tab(
    parent: ttk.Notebook,
    state: dict,
    reload_data: Callable,
    save_data: Callable,
) -> ttk.Frame:
    """Transactions tab: scrollable list with live filters."""
    frame = ttk.Frame(parent, padding=PAD_LG)

    date_filter_var = tk.StringVar()
    cat_filter_var = tk.StringVar()
    desc_filter_var = tk.StringVar()

    def category_choices() -> List[str]:
        cats = {c for c in DEFAULT_CATEGORIES}
        for t in state["transactions"]:
            cats.add(t.category)
        return [""] + sorted(cats)

    # Filters in a card (packed after tree + footer so the button bar stays visible when resized)
    filter_card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_MD, pady=PAD_MD, highlightbackground=COLORS["border"], highlightthickness=1)
    row1 = tk.Frame(filter_card, bg=COLORS["surface"])
    row1.pack(fill="x")
    tk.Label(row1, text="Date:", bg=COLORS["surface"], fg=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE)).pack(side="left", padx=(0, PAD_SM))
    date_filter = ttk.Entry(row1, textvariable=date_filter_var, width=11)
    date_filter.pack(side="left", padx=(0, PAD_SM))
    ttk.Button(row1, text="📅", width=3, command=lambda: show_date_picker(filter_card, date_filter_var)).pack(side="left", padx=(0, PAD_MD))
    tk.Label(row1, text="Category:", bg=COLORS["surface"], fg=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE)).pack(side="left", padx=(0, PAD_SM))
    cat_filter = ttk.Combobox(row1, textvariable=cat_filter_var, values=category_choices(), width=14, state="normal")
    cat_filter.pack(side="left", padx=(0, PAD_MD))

    row2 = tk.Frame(filter_card, bg=COLORS["surface"])
    row2.pack(fill="x", pady=(PAD_SM, 0))
    tk.Label(row2, text="Search description:", bg=COLORS["surface"], fg=COLORS["text"], font=(FONT_FAMILY, FONT_SIZE)).pack(side="left", padx=(0, PAD_SM))
    desc_filter = ttk.Entry(row2, textvariable=desc_filter_var, width=40)
    desc_filter.pack(side="left", fill="x", expand=True)

    sep_below_filter = ttk.Separator(frame, orient="horizontal")

    # Treeview + scrollbars in card
    tree_card = tk.Frame(frame, bg=COLORS["surface"], relief="flat", padx=PAD_MD, pady=PAD_MD, highlightbackground=COLORS["border"], highlightthickness=1)
    tree_inner = tk.Frame(tree_card, bg=COLORS["surface"])
    tree_inner.pack(fill="both", expand=True)
    columns = ("date", "amount", "category", "description")
    tree = ttk.Treeview(tree_inner, columns=columns, show="headings", height=12, selectmode="browse")
    tree.heading("date", text="Date")
    tree.heading("amount", text="Amount (HKD)")
    tree.heading("category", text="Category")
    tree.heading("description", text="Description")
    tree.column("date", width=100, minwidth=80)
    tree.column("amount", width=90, minwidth=70)
    tree.column("category", width=100, minwidth=80)
    tree.column("description", width=220, minwidth=100)
    vsb = ttk.Scrollbar(tree_inner, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(tree_inner, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    tree_inner.grid_rowconfigure(0, weight=1)
    tree_inner.grid_columnconfigure(0, weight=1)

    # Row order matches the treeview (filtered, sorted); used to resolve selection for edit
    last_displayed: List[Transaction] = []

    def _bind_mousewheel(widget: tk.Widget) -> None:
        def on_wheel(event) -> Optional[str]:
            delta = 0
            if event.num == 5:
                delta = 1
            elif event.num == 4:
                delta = -1
            elif getattr(event, "delta", 0):
                if sys.platform == "darwin":
                    delta = -event.delta
                else:
                    delta = -1 if event.delta > 0 else 1
            if delta:
                tree.yview_scroll(delta, "units")
                return "break"
            return None

        widget.bind("<MouseWheel>", on_wheel)
        widget.bind("<Button-4>", on_wheel)
        widget.bind("<Button-5>", on_wheel)

    _bind_mousewheel(tree)

    sep_below_tree = ttk.Separator(frame, orient="horizontal")

    def apply_filters():
        cat_filter["values"] = category_choices()
        for item in tree.get_children():
            tree.delete(item)
        last_displayed.clear()
        tx_list = list(state["transactions"])
        date_prefix = date_filter_var.get().strip()
        cat_str = cat_filter_var.get().strip().lower()
        desc_q = desc_filter_var.get().strip().lower()
        if date_prefix:
            tx_list = [t for t in tx_list if t.date.startswith(date_prefix)]
        if cat_str:
            tx_list = [t for t in tx_list if t.category.startswith(cat_str)]
        if desc_q:
            tx_list = [t for t in tx_list if desc_q in (t.description or "").lower()]
        for i, t in enumerate(sorted(tx_list, key=lambda x: (x.date, x.amount))):
            last_displayed.append(t)
            tree.insert("", "end", iid=str(i), values=(t.date, f"{abs(t.amount):.2f}", t.category, t.description))

    def refresh():
        """Reload from disk and reapply filters."""
        reload_data()
        apply_filters()

    debounce_id: Optional[Any] = None

    def schedule_filter(*_args) -> None:
        nonlocal debounce_id
        if debounce_id is not None:
            try:
                frame.after_cancel(debounce_id)
            except tk.TclError:
                pass
        debounce_id = frame.after(120, apply_filters)

    date_filter_var.trace_add("write", lambda *_: schedule_filter())
    desc_filter_var.trace_add("write", lambda *_: schedule_filter())
    cat_filter_var.trace_add("write", lambda *_: schedule_filter())
    cat_filter.bind("<<ComboboxSelected>>", lambda _e: apply_filters())

    def edit_selected():
        sel = tree.selection()
        if not sel:
            return
        try:
            row_i = int(sel[0])
        except (ValueError, IndexError):
            return
        if not (0 <= row_i < len(last_displayed)):
            return
        t_orig = last_displayed[row_i]
        try:
            tx_index = state["transactions"].index(t_orig)
        except ValueError:
            return

        dlg = tk.Toplevel(parent)
        dlg.title("Edit transaction")
        dlg.resizable(False, False)
        dlg.configure(bg=COLORS["bg"])
        top = parent.winfo_toplevel()
        dlg.transient(top)
        dlg.grab_set()

        card = tk.Frame(dlg, bg=COLORS["surface"], padx=PAD_LG, pady=PAD_LG,
                        highlightbackground=COLORS["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=PAD_MD, pady=PAD_MD)

        ttk.Label(card, text="Date (YYYY-MM-DD):").pack(anchor="w")
        date_var = tk.StringVar(value=t_orig.date)
        date_row = tk.Frame(card, bg=COLORS["surface"])
        date_row.pack(anchor="w", pady=(0, PAD_MD))
        ttk.Entry(date_row, textvariable=date_var, width=14).pack(side="left")
        ttk.Button(date_row, text="📅", width=3, command=lambda: show_date_picker(card, date_var)).pack(side="left", padx=(PAD_SM, 0))

        ttk.Label(card, text="Amount (HKD):").pack(anchor="w")
        amount_var = tk.StringVar(value=f"{abs(t_orig.amount):.2f}")
        ttk.Entry(card, textvariable=amount_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

        ttk.Label(card, text="Category:").pack(anchor="w")
        cat_edit_var = tk.StringVar(value=t_orig.category)
        cat_edit = ttk.Combobox(card, textvariable=cat_edit_var, values=sorted(category_choices())[1:], width=20)
        cat_edit.pack(anchor="w", pady=(0, PAD_MD))

        ttk.Label(card, text="Description:").pack(anchor="w")
        desc_var = tk.StringVar(value=t_orig.description)
        ttk.Entry(card, textvariable=desc_var, width=40).pack(anchor="w", pady=(0, PAD_LG))

        msg = tk.Label(card, text="", bg=COLORS["surface"], fg=COLORS["error"], font=(FONT_FAMILY, FONT_SIZE))

        def close():
            dlg.grab_release()
            dlg.destroy()

        def save_edit():
            date_str = date_var.get().strip()
            if not validate_date(date_str):
                msg.config(text="Invalid date. Use YYYY-MM-DD.")
                return
            amt = validate_amount(amount_var.get().strip())
            if amt is None:
                msg.config(text="Invalid amount. Enter a positive number.")
                return
            category = cat_edit_var.get().strip().lower()
            if not category:
                msg.config(text="Enter a category.")
                return
            if not validate_category(category):
                msg.config(text="Invalid category.")
                return
            state["transactions"][tx_index] = Transaction(
                date=date_str,
                amount=-amt,
                category=category,
                description=desc_var.get().strip() or "",
            )
            save_data()
            close()
            apply_filters()

        btn_row = tk.Frame(card, bg=COLORS["surface"])
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Save", command=save_edit).pack(side="right", padx=(PAD_SM, 0))
        ttk.Button(btn_row, text="Cancel", command=close).pack(side="right")
        msg.pack(anchor="w", pady=(PAD_SM, 0))
        dlg.protocol("WM_DELETE_WINDOW", close)

    btn_row_tx = tk.Frame(frame)
    ttk.Button(btn_row_tx, text="Refresh from file", command=refresh).pack(side="left", padx=(0, PAD_SM))
    ttk.Button(btn_row_tx, text="Edit selected", command=edit_selected).pack(side="left")
    # Same pack pattern as Summary: pin footer with side=bottom, header with side=top, list expands in middle.
    btn_row_tx.pack(side="bottom", fill="x", pady=PAD_SM)
    sep_below_tree.pack(side="bottom", fill="x", pady=(0, PAD_MD))
    filter_card.pack(side="top", fill="x")
    sep_below_filter.pack(side="top", fill="x", pady=PAD_MD)
    tree_card.pack(fill="both", expand=True)
    apply_filters()

    def on_tab_shown() -> None:
        """Resync list from memory (e.g. after adding on another tab)."""
        apply_filters()

    return frame, on_tab_shown


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
    text_inner = tk.Frame(output_card, bg=COLORS["surface"])
    text_inner.pack(fill="both", expand=True)
    output_text = tk.Text(
        text_inner,
        wrap="word",
        height=10,
        width=52,
        state="disabled",
        bg=COLORS["surface"],
        fg=COLORS["text"],
        font=(FONT_FAMILY, FONT_SIZE),
        relief="flat",
        padx=PAD_MD,
        pady=PAD_MD,
    )
    out_vsb = ttk.Scrollbar(text_inner, orient="vertical", command=output_text.yview)
    output_text.configure(yscrollcommand=out_vsb.set)
    output_text.grid(row=0, column=0, sticky="nsew")
    out_vsb.grid(row=0, column=1, sticky="ns")
    text_inner.grid_rowconfigure(0, weight=1)
    text_inner.grid_columnconfigure(0, weight=1)

    def _bind_output_wheel(widget: tk.Widget) -> None:
        def on_wheel(event) -> Optional[str]:
            delta = 0
            if event.num == 5:
                delta = 1
            elif event.num == 4:
                delta = -1
            elif getattr(event, "delta", 0):
                if sys.platform == "darwin":
                    delta = -event.delta
                else:
                    delta = -1 if event.delta > 0 else 1
            if delta:
                output_text.yview_scroll(delta, "units")
                return "break"
            return None

        widget.bind("<MouseWheel>", on_wheel)
        widget.bind("<Button-4>", on_wheel)
        widget.bind("<Button-5>", on_wheel)

    _bind_output_wheel(output_text)
    return frame
