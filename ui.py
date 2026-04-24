"""
Personal Budget Assistant - Tkinter GUI
COMP1110 E21 - Topic A
"""

import calendar as cal_module
import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Any, Callable, List, Optional, Tuple

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
    BUDGETS_PATH,
    BudgetRule,
    DEFAULT_CATEGORIES,
    CATEGORIES,
    Transaction,
    load_budget_rules,
    load_transactions,
    save_budgets_bundle,
    save_transactions,
    validate_amount,
    validate_category,
    validate_date,
    load_categories,
    add_category,
)
from stats import (
    average_daily_spending,
    budget_utilization,
    by_category,
    by_period,
    forecast_period_total,
    total_spending,
    trend_last_n_days,
)
from alerts import compute_health_score, run_all_alerts, split_alert_message
import portfolio
from gui_settings import load_gui_settings, pct_rules_as_tuples

TRANSACTIONS_FILE = "transactions.csv"
BUDGETS_FILE = str(BUDGETS_PATH)

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
    style.configure("Treeview.Heading", background=COLORS["accent_light"], foreground=COLORS["accent"])
    style.configure("TCombobox", fieldbackground=COLORS["surface"])
    style.configure("TEntry", fieldbackground=COLORS["surface"])
    return style


def run_gui() -> None:
    """Launch the Tkinter GUI."""
    load_categories()  # Load custom categories at startup
    root = tk.Tk()
    root.title("Personal Budget Assistant")
    root.geometry("1100x760")
    root.minsize(680, 540)
    root.configure(bg=COLORS["bg"])
    setup_styles(root)

    # Shared state
    state = {
        "transactions": load_transactions(TRANSACTIONS_FILE),
        "rules": load_budget_rules(BUDGETS_FILE),
        "gui_settings": load_gui_settings(),
    }

    def reload_data():
        state["transactions"] = load_transactions(TRANSACTIONS_FILE)
        state["rules"] = load_budget_rules(BUDGETS_FILE)
        state["gui_settings"] = load_gui_settings()

    def save_data():
        save_transactions(state["transactions"], TRANSACTIONS_FILE)
        merged = save_budgets_bundle(
            state["rules"],
            state.get("gui_settings") or load_gui_settings(),
            BUDGETS_FILE,
        )
        state["gui_settings"] = merged

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

    # Portfolio tab
    portfolio_frame = create_portfolio_tab(nb)
    nb.add(portfolio_frame, text="Portfolio")

    # Settings tab (unified budgets.csv: caps, % rules, alert thresholds)
    settings_frame = create_settings_tab(nb, state, reload_data)
    nb.add(settings_frame, text="Settings")

    # Categories tab (manage custom categories)
    categories_frame = create_categories_tab(nb)
    nb.add(categories_frame, text="Categories")

    root.mainloop()


_BUDGET_PERIODS = ("daily", "weekly", "monthly")


def create_settings_tab(parent: ttk.Notebook, state: dict, reload_data: Callable) -> ttk.Frame:
    """Edit budgets.csv (caps, category % rules, alert thresholds; alerts on Summary)."""
    outer = ttk.Frame(parent, padding=PAD_LG)

    scroll_wrap = tk.Frame(outer, bg=COLORS["bg"])
    canvas = tk.Canvas(scroll_wrap, bg=COLORS["bg"], highlightthickness=0)
    vsb = ttk.Scrollbar(scroll_wrap, orient="vertical", command=canvas.yview)
    content = tk.Frame(canvas, bg=COLORS["bg"])
    settings_inner = canvas.create_window((0, 0), window=content, anchor="nw")

    def on_settings_canvas_configure(event: Any) -> None:
        canvas.itemconfigure(settings_inner, width=event.width)

    canvas.bind("<Configure>", on_settings_canvas_configure)

    def on_settings_content_configure(_event: Any) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    content.bind("<Configure>", on_settings_content_configure)
    canvas.configure(yscrollcommand=vsb.set)

    def _sync_settings_scroll() -> None:
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox:
            canvas.configure(scrollregion=bbox)

    _pg_pad = (0, PAD_MD)

    _tab_hero(
        content,
        "Settings",
        "Budget caps (HK$) drive overspend and streak alerts. Category % rules and the options below are stored in budgets.csv with the caps.",
    )

    _section_header(content, "Budget caps (HK$)")
    tk.Label(
        content,
        text="Maximum spending per category for each period. Daily caps also power consecutive-day streak alerts.",
        bg=COLORS["bg"],
        fg=COLORS["text_muted"],
        font=(FONT_FAMILY, FONT_SIZE - 1),
        wraplength=560,
        justify="left",
    ).pack(anchor="w", pady=(0, PAD_MD))

    budget_table = tk.Frame(content, bg=COLORS["bg"])
    budget_table.pack(fill="x")
    row_bindings_budget: List[Tuple[tk.StringVar, tk.StringVar, tk.StringVar]] = []

    def _sync_budget_from_ui() -> None:
        if not row_bindings_budget:
            return
        rules = state.setdefault("rules", [])
        for i, (cv, pv, tv) in enumerate(row_bindings_budget):
            if i >= len(rules):
                continue
            cat = (cv.get() or "").strip().lower() or rules[i].category
            per = (pv.get() or "").strip().lower() or rules[i].period
            try:
                thr = float(tv.get().strip())
            except ValueError:
                thr = rules[i].threshold
            at = rules[i].alert_type or "overspend"
            rules[i] = BudgetRule(category=cat, period=per, threshold=thr, alert_type=at)

    def redraw_budget_rows() -> None:
        _sync_budget_from_ui()
        for w in budget_table.winfo_children():
            w.destroy()
        row_bindings_budget.clear()
        rules = state.setdefault("rules", load_budget_rules(BUDGETS_FILE))
        state["rules"] = rules

        tk.Label(budget_table, text="Category", bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).grid(
            row=0, column=0, sticky="w", padx=_pg_pad, pady=(0, PAD_SM)
        )
        tk.Label(budget_table, text="Period", bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).grid(
            row=0, column=1, sticky="w", padx=_pg_pad, pady=(0, PAD_SM)
        )
        tk.Label(budget_table, text="Cap (HK$)", bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).grid(
            row=0, column=2, sticky="w", padx=_pg_pad, pady=(0, PAD_SM)
        )

        def on_budget_dim_change(_e: Any) -> None:
            _sync_budget_from_ui()
            redraw_budget_rows()

        n_b = len(rules)
        for idx, br in enumerate(rules):
            cv_s = tk.StringVar(value=br.category)
            pv_s = tk.StringVar(value=br.period)
            tv_s = tk.StringVar(value=str(br.threshold))
            row_ix = idx + 1
            other_pairs = {(rules[j].category, rules[j].period) for j in range(n_b) if j != idx}
            cats = list(CATEGORIES)
            if br.category and br.category not in cats:
                cats = [br.category] + cats
            cat_vals = [
                c
                for c in cats
                if c == br.category
                or any((c, p) not in other_pairs for p in _BUDGET_PERIODS)
            ]
            if br.category not in cat_vals:
                cat_vals.insert(0, br.category)
            per_vals = [
                p
                for p in _BUDGET_PERIODS
                if p == br.period or (br.category, p) not in other_pairs
            ]
            if br.period not in per_vals:
                per_vals.insert(0, br.period)
            cbc = ttk.Combobox(budget_table, textvariable=cv_s, values=cat_vals or cats, width=16, state="readonly")
            cbc.grid(row=row_ix, column=0, sticky="w", padx=_pg_pad, pady=PAD_SM)
            cbc.bind("<<ComboboxSelected>>", on_budget_dim_change)
            cbp = ttk.Combobox(budget_table, textvariable=pv_s, values=per_vals or list(_BUDGET_PERIODS), width=10, state="readonly")
            cbp.grid(row=row_ix, column=1, sticky="w", padx=_pg_pad, pady=PAD_SM)
            cbp.bind("<<ComboboxSelected>>", on_budget_dim_change)
            ttk.Entry(budget_table, textvariable=tv_s, width=12).grid(row=row_ix, column=2, sticky="w", padx=_pg_pad, pady=PAD_SM)

            def remove_b(ii: int = idx) -> None:
                rr = state["rules"]
                if 0 <= ii < len(rr):
                    rr.pop(ii)
                    redraw_budget_rows()

            ttk.Button(budget_table, text="Remove", command=remove_b).grid(row=row_ix, column=3, sticky="w", padx=_pg_pad, pady=PAD_SM)
            row_bindings_budget.append((cv_s, pv_s, tv_s))

        used_pairs = {(r.category, r.period) for r in rules}
        max_rules = len(CATEGORIES) * len(_BUDGET_PERIODS)
        can_add_b = len(used_pairs) < max_rules and any(
            (c, p) not in used_pairs for c in CATEGORIES for p in _BUDGET_PERIODS
        )
        if can_add_b:
            add_budget_btn.state(["!disabled"])
        else:
            add_budget_btn.state(["disabled"])
        _sync_settings_scroll()

    def add_budget_rule() -> None:
        _sync_budget_from_ui()
        rules = state.setdefault("rules", [])
        used_pairs = {(r.category, r.period) for r in rules}
        picked = None
        for c in CATEGORIES:
            for p in _BUDGET_PERIODS:
                if (c, p) not in used_pairs:
                    picked = (c, p)
                    break
            if picked:
                break
        if picked is None:
            return
        rules.append(BudgetRule(category=picked[0], period=picked[1], threshold=100.0, alert_type="overspend"))
        redraw_budget_rows()

    add_budget_btn = ttk.Button(content, text="Add budget cap", command=add_budget_rule)
    add_budget_btn.pack(anchor="w", pady=PAD_SM)
    redraw_budget_rows()

    _section_header(content, "Category share of total spending")
    tk.Label(
        content,
        text="Warning % fires first. Critical % (optional) must be higher than warning; leave blank for warning-only.",
        bg=COLORS["bg"],
        fg=COLORS["text_muted"],
        font=(FONT_FAMILY, FONT_SIZE - 1),
        wraplength=560,
        justify="left",
    ).pack(anchor="w", pady=(0, PAD_MD))

    pct_table = tk.Frame(content, bg=COLORS["bg"])
    pct_table.pack(fill="x")
    row_bindings: List[Tuple[tk.StringVar, tk.StringVar, tk.StringVar]] = []

    def _migrate_row(row: List[Any]) -> List[Any]:
        if len(row) >= 3:
            return [row[0], float(row[1]), float(row[2])]
        if len(row) == 2:
            return [row[0], float(row[1]), 0.0]
        return []

    def _sync_pct_rules_from_ui() -> None:
        """Persist current row StringVars into gui_settings before redraw (keeps edits)."""
        if not row_bindings:
            return
        gs = state.setdefault("gui_settings", load_gui_settings())
        rules = gs.setdefault("pct_rules", [])
        for i, (cv_s, wv_s, cr_s) in enumerate(row_bindings):
            if i >= len(rules):
                continue
            cat = (cv_s.get() or "").strip().lower() or str(rules[i][0])
            try:
                wn = float(wv_s.get().strip())
            except ValueError:
                wn = float(rules[i][1])
            cr_raw = (cr_s.get() or "").strip()
            try:
                crit = 0.0 if not cr_raw else float(cr_raw)
            except ValueError:
                crit = float(rules[i][2])
            rules[i] = [cat, wn, crit]

    def redraw_pct_rows() -> None:
        _sync_pct_rules_from_ui()
        for w in pct_table.winfo_children():
            w.destroy()
        row_bindings.clear()
        gs = state.setdefault("gui_settings", load_gui_settings())
        raw = gs.get("pct_rules") or []
        rules = []
        for r in raw:
            rr = _migrate_row(list(r) if isinstance(r, (list, tuple)) else [])
            if rr:
                rules.append(rr)
        gs["pct_rules"] = rules

        n_rules = len(gs["pct_rules"])
        tk.Label(pct_table, text="Category", bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).grid(
            row=0, column=0, sticky="w", padx=_pg_pad, pady=(0, PAD_SM)
        )
        tk.Label(pct_table, text="Warning %", bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).grid(
            row=0, column=1, sticky="w", padx=_pg_pad, pady=(0, PAD_SM)
        )
        tk.Label(pct_table, text="Critical %", bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).grid(
            row=0, column=2, sticky="w", padx=_pg_pad, pady=(0, PAD_SM)
        )
        tk.Label(pct_table, text="(optional)", bg=COLORS["bg"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 2)).grid(
            row=0, column=3, sticky="w", padx=_pg_pad, pady=(0, PAD_SM)
        )

        def on_pct_cat_selected(_e: Any) -> None:
            _sync_pct_rules_from_ui()
            redraw_pct_rows()

        for idx, triple in enumerate(gs["pct_rules"]):
            cat, wv, cv = triple[0], triple[1], triple[2]
            cv_s = tk.StringVar(value=str(cat))
            wv_s = tk.StringVar(value=str(wv))
            cr_s = tk.StringVar(value="" if float(cv) <= 0 else str(cv))
            row_ix = idx + 1
            used_elsewhere: set = set()
            for j in range(n_rules):
                if j == idx:
                    continue
                used_elsewhere.add(str(gs["pct_rules"][j][0]).strip().lower())
            vals = list(CATEGORIES)
            cur = cv_s.get().strip().lower()
            if cur and cur not in vals:
                vals = [cur] + vals
            combo_vals = [c for c in vals if c not in used_elsewhere or c == cur]
            cb = ttk.Combobox(pct_table, textvariable=cv_s, values=combo_vals or vals, width=18, state="readonly")
            cb.grid(row=row_ix, column=0, sticky="w", padx=_pg_pad, pady=PAD_SM)
            cb.bind("<<ComboboxSelected>>", on_pct_cat_selected)
            ttk.Entry(pct_table, textvariable=wv_s, width=10).grid(row=row_ix, column=1, sticky="w", padx=_pg_pad, pady=PAD_SM)
            ttk.Entry(pct_table, textvariable=cr_s, width=10).grid(row=row_ix, column=2, sticky="w", padx=_pg_pad, pady=PAD_SM)

            def remove(ii: int = idx) -> None:
                r = state["gui_settings"]["pct_rules"]
                if 0 <= ii < len(r):
                    r.pop(ii)
                    redraw_pct_rows()

            ttk.Button(pct_table, text="Remove", command=remove).grid(row=row_ix, column=4, sticky="w", padx=_pg_pad, pady=PAD_SM)
            row_bindings.append((cv_s, wv_s, cr_s))

        used_cats = {str(r[0]).strip().lower() for r in (gs.get("pct_rules") or [])}
        can_add = any(c not in used_cats for c in CATEGORIES)
        if can_add:
            add_pct_btn.state(["!disabled"])
        else:
            add_pct_btn.state(["disabled"])
        _sync_settings_scroll()

    def add_pct_rule() -> None:
        _sync_pct_rules_from_ui()
        gs = state.setdefault("gui_settings", load_gui_settings())
        used = {str(r[0]).strip().lower() for r in (gs.get("pct_rules") or [])}
        pick = None
        for c in CATEGORIES:
            if c not in used:
                pick = c
                break
        if pick is None:
            return
        gs.setdefault("pct_rules", []).append([pick, 25.0, 0.0])
        redraw_pct_rows()

    add_pct_btn = ttk.Button(content, text="Add category rule", command=add_pct_rule)
    add_pct_btn.pack(anchor="w", pady=PAD_SM)
    redraw_pct_rows()

    _section_header(content, "Other alert thresholds")
    other_outer, other_inner = _surface_card_with_accent(content)
    other_outer.pack(fill="x", pady=(0, PAD_MD))

    gs0 = state.get("gui_settings") or load_gui_settings()
    consec_var = tk.StringVar(value=str(gs0.get("consecutive_overspend_days", 3)))
    creep_var = tk.StringVar(value=str(gs0.get("subscription_creep_threshold_pct", 20.0)))

    _field_label(other_inner, "Consecutive overspend days (daily budget streak)")
    ttk.Entry(other_inner, textvariable=consec_var, width=8).pack(anchor="w", pady=(0, PAD_MD))
    _field_label(
        other_inner,
        "Subscription creep — month-on-month rise (%) that triggers an alert",
    )
    ttk.Entry(other_inner, textvariable=creep_var, width=8).pack(anchor="w", pady=(0, PAD_LG))

    settings_footer = tk.Frame(outer, bg=COLORS["bg"])
    msg = tk.Label(
        settings_footer,
        text="",
        bg=COLORS["bg"],
        font=(FONT_FAMILY, FONT_SIZE),
        wraplength=560,
        justify="left",
    )

    def save_settings() -> None:
        _sync_budget_from_ui()
        _sync_pct_rules_from_ui()

        pairs_b: set = set()
        for br in state.setdefault("rules", []):
            key = (br.category.strip().lower(), br.period.strip().lower())
            if key in pairs_b:
                msg.config(
                    text=f'Duplicate budget cap for "{br.category}" ({br.period}). Remove or edit one row.',
                    fg=COLORS["error"],
                )
                return
            pairs_b.add(key)
            if br.threshold <= 0:
                msg.config(text="Each budget cap (HK$) must be greater than zero.", fg=COLORS["error"])
                return
            if br.period not in _BUDGET_PERIODS:
                msg.config(text=f'Invalid period "{br.period}". Use daily, weekly, or monthly.', fg=COLORS["error"])
                return

        cats: List[str] = []
        new_pct: List[List[Any]] = []

        for cv_s, wv_s, cr_s in row_bindings:
            cat = cv_s.get().strip().lower()
            if not cat:
                msg.config(text="Each row needs a category.", fg=COLORS["error"])
                return
            if cat in cats:
                msg.config(text=f"Duplicate category \"{cat}\". Each category can appear only once.", fg=COLORS["error"])
                return
            cats.append(cat)
            try:
                wn = float(wv_s.get().strip())
            except ValueError:
                msg.config(text=f"Invalid warning % for {cat}.", fg=COLORS["error"])
                return
            if not (0 < wn <= 100):
                msg.config(text="Warning % must be between 0 and 100.", fg=COLORS["error"])
                return
            cr_raw = cr_s.get().strip()
            if not cr_raw:
                crit = 0.0
            else:
                try:
                    crit = float(cr_raw)
                except ValueError:
                    msg.config(text=f"Invalid critical % for {cat}.", fg=COLORS["error"])
                    return
                if crit <= 0:
                    msg.config(text="Critical % must be blank or strictly positive.", fg=COLORS["error"])
                    return
                if crit <= wn:
                    msg.config(
                        text=f"{cat}: critical % must be greater than warning %.",
                        fg=COLORS["error"],
                    )
                    return
                if crit > 100:
                    msg.config(text="Critical % cannot exceed 100.", fg=COLORS["error"])
                    return
            new_pct.append([cat, wn, crit])

        try:
            cd = int(consec_var.get().strip())
            creep = float(creep_var.get().strip())
        except ValueError:
            msg.config(text="Use an integer for days and a number for creep.", fg=COLORS["error"])
            return

        state.setdefault("gui_settings", load_gui_settings())
        state["gui_settings"]["pct_rules"] = new_pct
        state["gui_settings"]["consecutive_overspend_days"] = max(1, min(30, cd))
        state["gui_settings"]["subscription_creep_threshold_pct"] = max(0.0, min(500.0, creep))
        merged = save_budgets_bundle(state["rules"], state["gui_settings"], BUDGETS_FILE)
        state["gui_settings"] = merged
        reload_data()
        msg.config(
            text="Saved to budgets.csv. Refresh the Summary tab if alerts look stale.",
            fg=COLORS["success"],
        )
        redraw_budget_rows()
        redraw_pct_rows()

    ttk.Separator(settings_footer, orient="horizontal").pack(fill="x", pady=(0, PAD_MD))
    save_btn_row = tk.Frame(settings_footer, bg=COLORS["bg"])
    save_btn_row.columnconfigure(0, weight=1)
    save_btn_row.columnconfigure(1, weight=0)
    save_btn_row.columnconfigure(2, weight=1)
    ttk.Button(save_btn_row, text="Save settings", command=save_settings).grid(row=0, column=1)
    save_btn_row.pack(fill="x")
    msg.pack(anchor="w", fill="x", pady=(PAD_SM, 0))

    settings_footer.pack(side="bottom", fill="x")
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    scroll_wrap.pack(fill="both", expand=True)

    _bind_mousewheel_to_canvas_and_content(canvas, content)
    _sync_settings_scroll()
    return outer

def create_categories_tab(parent: ttk.Notebook) -> ttk.Frame:
    """Categories tab: manage (add/view) custom categories."""
    frame = ttk.Frame(parent, padding=PAD_LG)
    _tab_hero(
        frame,
        "Manage Categories",
        "View your custom categories and add new ones for organizing expenses.",
    )

    card_outer, card = _surface_card_with_accent(frame)
    card_outer.pack(fill="x", pady=(0, PAD_MD))

    _section_header(card, "Current categories")
    
    # Scrollable list of current categories
    list_frame = tk.Frame(card, bg=COLORS["surface"])
    list_frame.pack(fill="both", expand=True, pady=(0, PAD_MD))
    
    def refresh_category_list():
        """Refresh the displayed list of categories."""
        for w in list_frame.winfo_children():
            w.destroy()
        
        if not CATEGORIES:
            tk.Label(
                list_frame, text="No categories yet.",
                bg=COLORS["surface"], fg=COLORS["text_muted"],
                font=(FONT_FAMILY, FONT_SIZE)
            ).pack(anchor="w", pady=PAD_SM)
        else:
            for i, cat in enumerate(CATEGORIES, 1):
                cat_item = tk.Frame(list_frame, bg=COLORS["accent_light"], padx=PAD_MD, pady=PAD_SM, highlightbackground=COLORS["border"], highlightthickness=1)
                cat_item.pack(fill="x", pady=PAD_SM)
                tk.Label(
                    cat_item, text=f"{i}. {cat}", bg=COLORS["accent_light"], fg=COLORS["text"],
                    font=(FONT_FAMILY, FONT_SIZE, "bold"), width=20, anchor="w"
                ).pack(side="left")
    
    refresh_category_list()

    _field_label(card, "Add new category")
    add_frame = tk.Frame(card, bg=COLORS["surface"])
    add_frame.pack(fill="x", pady=(0, PAD_LG))
    
    new_cat_entry = ttk.Entry(add_frame, width=25)
    new_cat_entry.pack(side="left", padx=(0, PAD_SM))
    
    msg_label = tk.Label(card, text="", bg=COLORS["surface"], fg=COLORS["success"], font=(FONT_FAMILY, FONT_SIZE))

    def do_add():
        """Add a new category."""
        category = new_cat_entry.get().strip().lower()
        if not category:
            msg_label.config(text="Enter a category name.", fg=COLORS["error"])
            return
        if add_category(category):
            msg_label.config(text=f"Category '{category}' added successfully!", fg=COLORS["success"])
            new_cat_entry.delete(0, "end")
            refresh_category_list()
        else:
            msg_label.config(text=f"Category '{category}' already exists.", fg=COLORS["error"])

    ttk.Button(add_frame, text="Add category", command=do_add).pack(side="left")
    msg_label.pack(anchor="w", pady=PAD_SM)

    ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=PAD_MD)
    ttk.Button(frame, text="Refresh", command=refresh_category_list).pack(pady=PAD_SM)
    
    return frame

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
    strip = tk.Frame(card, bg=COLORS["accent"], width=5)
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


def _tab_hero(parent: tk.Widget, title: str, subtitle: str = "") -> None:
    """Title + optional subtitle + accent bar (matches Summary tab rhythm)."""
    row = tk.Frame(parent, bg=COLORS["bg"])
    row.pack(fill="x", pady=(0, PAD_LG))
    tk.Label(row, text=title, bg=COLORS["bg"], fg=COLORS["text"], font=FONT_HEADING).pack(anchor="w")
    if subtitle:
        tk.Label(
            row, text=subtitle, bg=COLORS["bg"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, FONT_SIZE), wraplength=560, justify="left",
        ).pack(anchor="w", pady=(PAD_SM, 0))
    tk.Frame(row, bg=COLORS["accent"], height=3).pack(fill="x", pady=(PAD_MD, 0))


def _surface_card_with_accent(parent: tk.Widget) -> Tuple[tk.Frame, tk.Frame]:
    """White card with teal left strip; return (card, inner) to pack fields into inner."""
    card = tk.Frame(parent, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1)
    strip = tk.Frame(card, bg=COLORS["accent"], width=4)
    strip.pack(side="left", fill="y")
    inner = tk.Frame(card, bg=COLORS["surface"], padx=PAD_LG, pady=PAD_LG)
    inner.pack(side="left", fill="both", expand=True)
    return card, inner


def _field_label(parent: tk.Widget, text: str, bg: str = COLORS["surface"]) -> None:
    tk.Label(
        parent, text=text, bg=bg, fg=COLORS["text_muted"],
        font=(FONT_FAMILY, FONT_SIZE - 1),
    ).pack(anchor="w")


def _category_row(
    parent: tk.Widget,
    name: str,
    amount: float,
    pct: float,
    bar_width: int = 200,
    label_width: int = 11,
) -> None:
    row = tk.Frame(parent, bg=COLORS["bg"])
    row.pack(fill="x", pady=PAD_SM)
    tk.Label(
        row, text=name.capitalize(), bg=COLORS["bg"], fg=COLORS["text"],
        font=(FONT_FAMILY, FONT_SIZE), width=label_width, anchor="w",
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


def _portfolio_block_heading(parent: tk.Widget, title: str, subtitle: str = "") -> None:
    """Subsection title inside Portfolio results (on surface)."""
    wrap = tk.Frame(parent, bg=COLORS["surface"])
    wrap.pack(fill="x", pady=(PAD_MD, PAD_SM))
    tk.Label(wrap, text=title, bg=COLORS["surface"], fg=COLORS["text"], font=FONT_SECTION).pack(anchor="w")
    if subtitle:
        tk.Label(
            wrap, text=subtitle, bg=COLORS["surface"], fg=COLORS["text_muted"],
            font=(FONT_FAMILY, FONT_SIZE - 1),
        ).pack(anchor="w", pady=(2, 0))
    tk.Frame(wrap, bg=COLORS["accent_light"], height=2).pack(fill="x", pady=(PAD_SM, 0))


def _portfolio_alloc_bar_row(parent: tk.Widget, asset_name: str, weight: float, bar_width: int = 200) -> None:
    """Allocation strip mirroring Summary category bars, on card surface."""
    pct = max(0.0, min(100.0, weight * 100.0))
    row = tk.Frame(parent, bg=COLORS["surface"])
    row.pack(fill="x", pady=PAD_SM)
    label = asset_name.replace("_", " ").strip().title() if asset_name else ""
    tk.Label(
        row, text=label, bg=COLORS["surface"], fg=COLORS["text"],
        font=(FONT_FAMILY, FONT_SIZE), width=12, anchor="w",
    ).pack(side="left")
    track = tk.Frame(row, bg=COLORS["border"], height=14, width=bar_width)
    track.pack(side="left", padx=(PAD_SM, PAD_SM), pady=2)
    track.pack_propagate(False)
    fill_w = max(2, int(bar_width * (pct / 100.0)))
    tk.Frame(track, bg=_category_bar_color(asset_name), height=14, width=fill_w).place(x=0, y=0, relheight=1)
    tk.Label(
        row, text=f"{pct:.0f}%", bg=COLORS["surface"], fg=COLORS["accent"],
        font=(FONT_FAMILY, FONT_SIZE, "bold"), width=5, anchor="e",
    ).pack(side="right", padx=(0, PAD_SM))


def _portfolio_percent_strip(parent: tk.Widget, label: str, fraction: float) -> None:
    row = tk.Frame(parent, bg=COLORS["accent_light"], padx=PAD_MD, pady=PAD_MD)
    row.pack(fill="x", pady=(PAD_MD, 0))
    tk.Label(
        row, text=label, bg=COLORS["accent_light"], fg=COLORS["text"],
        font=(FONT_FAMILY, FONT_SIZE),
    ).pack(side="left")
    tk.Label(
        row, text=f"{fraction * 100:.1f}%", bg=COLORS["accent_light"], fg=COLORS["accent"],
        font=(FONT_FAMILY, FONT_SIZE, "bold"),
    ).pack(side="right")


# Per–alert-type banners (paired with alerts.split_alert_message kinds)
_ALERT_BANNER_THEME = {
    "overspend": {
        "strip": "#e11d48",
        "bg": "#fff1f2",
        "title": "Budget cap exceeded",
    },
    "budget_pct_warn": {
        "strip": "#d97706",
        "bg": "#fffbeb",
        "title": "Share of spending (warning)",
    },
    "budget_pct_critical": {
        "strip": "#b45309",
        "bg": "#fff7ed",
        "title": "Share of spending (critical)",
    },
    "budget_pct": {
        "strip": "#d97706",
        "bg": "#fffbeb",
        "title": "Share of spending high",
    },
    "streak": {
        "strip": "#7c3aed",
        "bg": "#f5f3ff",
        "title": "Consecutive overspend",
    },
    "uncategorized": {
        "strip": "#475569",
        "bg": "#f8fafc",
        "title": "Uncategorized",
    },
    "subscription_creep": {
        "strip": "#ea580c",
        "bg": "#fff7ed",
        "title": "Subscription creep",
    },
    "forecast": {
        "strip": "#ea580c",
        "bg": "#fff7ed",
        "title": "On pace to overspend",
    },
    "anomaly": {
        "strip": "#dc2626",
        "bg": "#fef2f2",
        "title": "Spending anomaly",
    },
    "recurring": {
        "strip": "#2563eb",
        "bg": "#eff6ff",
        "title": "Recurring charge detected",
    },
    "health": {
        "strip": "#059669",
        "bg": "#ecfdf5",
        "title": "Budget health",
    },
    "general": {
        "strip": "#0e7490",
        "bg": "#ecfeff",
        "title": "Notice",
    },
    "clear": {
        "strip": "#059669",
        "bg": "#ecfdf5",
        "title": "All clear",
    },
}


def _alert_type_banner(parent: tk.Widget, kind: str, body: str) -> None:
    """One full-width banner row for a single alert (or all-clear)."""
    theme = _ALERT_BANNER_THEME.get(kind) or _ALERT_BANNER_THEME["general"]
    strip_c = theme["strip"]
    bg_c = theme["bg"]
    title = theme["title"]
    sw = 5

    outer = tk.Frame(parent, bg=COLORS["bg"])
    outer.pack(fill="x", pady=(0, PAD_MD))
    card = tk.Frame(outer, bg=bg_c, highlightbackground=COLORS["border"], highlightthickness=1)
    card.pack(fill="x")
    strip = tk.Frame(card, bg=strip_c, width=sw)
    strip.pack(side="left", fill="y")
    inner = tk.Frame(card, bg=bg_c, padx=PAD_MD, pady=PAD_MD)
    inner.pack(side="left", fill="both", expand=True)

    top = tk.Frame(inner, bg=bg_c)
    top.pack(fill="x")
    tk.Label(
        top,
        text=title.upper(),
        bg=bg_c,
        fg=strip_c,
        font=(FONT_FAMILY, FONT_SIZE - 1, "bold"),
    ).pack(side="left")
    tk.Label(
        inner,
        text=body,
        bg=bg_c,
        fg=COLORS["text"],
        font=(FONT_FAMILY, FONT_SIZE),
        wraplength=520,
        justify="left",
    ).pack(anchor="w", pady=(PAD_SM, 0))


# Grade letter -> strip colour for the health hero card.
_HEALTH_GRADE_COLORS = {
    "A": "#059669",
    "B": "#65a30d",
    "C": "#ca8a04",
    "D": "#ea580c",
    "F": "#dc2626",
}


def _health_hero_card(parent: tk.Widget, state: dict) -> None:
    """Prominent card with overall budget health score and letter grade."""
    txs = state["transactions"]
    rules = state["rules"]
    if not txs:
        return
    h = compute_health_score(txs, rules)
    grade = h["grade"]
    strip_c = _HEALTH_GRADE_COLORS.get(grade, COLORS["accent"])

    outer = tk.Frame(parent, bg=COLORS["bg"])
    outer.pack(fill="x", pady=(0, PAD_MD))
    card = tk.Frame(outer, bg=COLORS["surface"],
                    highlightbackground=COLORS["border"], highlightthickness=1)
    card.pack(fill="x")
    strip = tk.Frame(card, bg=strip_c, width=6)
    strip.pack(side="left", fill="y")
    inner = tk.Frame(card, bg=COLORS["surface"], padx=PAD_LG, pady=PAD_LG)
    inner.pack(side="left", fill="both", expand=True)

    row = tk.Frame(inner, bg=COLORS["surface"])
    row.pack(fill="x")

    left = tk.Frame(row, bg=COLORS["surface"])
    left.pack(side="left", fill="y")
    tk.Label(left, text="BUDGET HEALTH", bg=COLORS["surface"], fg=strip_c,
             font=(FONT_FAMILY, FONT_SIZE - 1, "bold")).pack(anchor="w")
    score_row = tk.Frame(left, bg=COLORS["surface"])
    score_row.pack(anchor="w", pady=(PAD_SM, 0))
    tk.Label(score_row, text=f"{h['score']:.0f}", bg=COLORS["surface"],
             fg=COLORS["text"], font=(FONT_FAMILY, 32, "bold")).pack(side="left")
    tk.Label(score_row, text="/ 100", bg=COLORS["surface"], fg=COLORS["text_muted"],
             font=(FONT_FAMILY, FONT_SIZE + 2)).pack(side="left", padx=(PAD_SM, 0))
    tk.Label(left, text=f"Grade {grade}", bg=COLORS["surface"], fg=strip_c,
             font=(FONT_FAMILY, FONT_SIZE + 1, "bold")).pack(anchor="w", pady=(PAD_SM, 0))

    right = tk.Frame(row, bg=COLORS["surface"])
    right.pack(side="right", fill="y")
    tk.Label(right, text=f"Max cap utilised: {h['max_util']:.0f}%",
             bg=COLORS["surface"], fg=COLORS["text"],
             font=(FONT_FAMILY, FONT_SIZE)).pack(anchor="e")
    tk.Label(right, text=f"Projected end-of-period: {h['max_forecast']:.0f}%",
             bg=COLORS["surface"], fg=COLORS["text"],
             font=(FONT_FAMILY, FONT_SIZE)).pack(anchor="e", pady=(PAD_SM, 0))
    tk.Label(right, text=f"Transactions categorised: {h['categorized_pct']:.0f}%",
             bg=COLORS["surface"], fg=COLORS["text"],
             font=(FONT_FAMILY, FONT_SIZE)).pack(anchor="e", pady=(PAD_SM, 0))


def _forecast_row(parent: tk.Widget, rule_label: str, fc: dict, bar_width: int = 200) -> None:
    """Single row showing projected spending vs cap as a coloured bar."""
    pct = fc["forecast_pct"]
    if pct >= 110:
        color = "#dc2626"
    elif pct >= 90:
        color = "#ea580c"
    else:
        color = "#059669"
    row = tk.Frame(parent, bg=COLORS["surface"])
    row.pack(fill="x", pady=PAD_SM)
    tk.Label(row, text=rule_label, bg=COLORS["surface"], fg=COLORS["text"],
             font=(FONT_FAMILY, FONT_SIZE), width=22, anchor="w").pack(side="left")
    track = tk.Frame(row, bg=COLORS["border"], height=14, width=bar_width)
    track.pack(side="left", padx=(PAD_SM, PAD_SM), pady=2)
    track.pack_propagate(False)
    display_pct = max(0.0, min(100.0, pct))
    fill_w = max(2, int(bar_width * (display_pct / 100.0)))
    tk.Frame(track, bg=color, height=14, width=fill_w).place(x=0, y=0, relheight=1)
    tk.Label(row, text=f"{pct:.0f}%", bg=COLORS["surface"], fg=color,
             font=(FONT_FAMILY, FONT_SIZE, "bold"), width=5, anchor="e").pack(side="right")
    tk.Label(row,
             text=f"HK$ {fc['forecast']:,.0f} of {fc['threshold']:,.0f}  "
                  f"(day {fc['days_elapsed']}/{fc['days_total']})",
             bg=COLORS["surface"], fg=COLORS["text_muted"],
             font=(FONT_FAMILY, FONT_SIZE - 1)).pack(side="right", padx=(0, PAD_MD))


def _forecasts_section(parent: tk.Widget, state: dict) -> None:
    """Per-rule projected end-of-period totals shown as coloured bars."""
    rules = state["rules"]
    txs = state["transactions"]
    if not rules or not txs:
        return
    _section_header(parent, "Forecasts")
    card = tk.Frame(parent, bg=COLORS["surface"],
                    highlightbackground=COLORS["border"], highlightthickness=1)
    card.pack(fill="x", pady=(0, PAD_SM))
    inner = tk.Frame(card, bg=COLORS["surface"], padx=PAD_LG, pady=PAD_MD)
    inner.pack(fill="x")
    tk.Label(inner,
             text="Projected end-of-period total at current pace. "
                  "Green under cap, orange 90%+, red 110%+.",
             bg=COLORS["surface"], fg=COLORS["text_muted"],
             font=(FONT_FAMILY, FONT_SIZE - 1), wraplength=520,
             justify="left").pack(anchor="w", pady=(0, PAD_SM))
    for r in rules:
        fc = forecast_period_total(txs, r)
        label = f"{r.category.capitalize()} ({r.period})"
        _forecast_row(inner, label, fc)


def _summary_alerts_block(parent: tk.Widget, state: dict) -> None:
    """Alerts only (banners). Stats are built separately below a 'Spending statistics' header."""
    gs = state.get("gui_settings") or load_gui_settings()
    pct_rules = pct_rules_as_tuples(gs)
    consec = int(gs.get("consecutive_overspend_days", 3))
    creep_thr = float(gs.get("subscription_creep_threshold_pct", 20.0))
    messages = run_all_alerts(
        state["transactions"],
        state["rules"],
        pct_rules=pct_rules,
        consecutive_days=consec,
        subscription_creep_threshold_pct=creep_thr,
        include_health=False,
    )
    _section_header(parent, "Alerts")
    if not messages:
        _alert_type_banner(
            parent,
            "clear",
            "No budget or behaviour warnings right now. Numbers below reflect your recorded spending.",
        )
    else:
        for msg in messages:
            kind, body = split_alert_message(msg)
            _alert_type_banner(parent, kind, body or msg)


def _refresh_summary_dashboard(
    content: tk.Frame,
    state: dict,
    reload_data: Callable,
    canvas: tk.Canvas,
) -> None:
    reload_data()
    for w in content.winfo_children():
        w.destroy()

    _summary_alerts_block(content, state)
    _health_hero_card(content, state)
    _section_header(content, "Spending statistics")

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
    t365 = trend_last_n_days(txs, 365)

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
    denom = total if total > 0 else 1e-12
    pct7 = (t7 / denom) * 100.0
    pct30 = (t30 / denom) * 100.0
    pct365 = (t365 / denom) * 100.0
    mom = tk.Frame(content, bg=COLORS["bg"])
    mom.pack(fill="x", pady=(0, PAD_SM))
    mom.grid_columnconfigure(0, weight=1)
    mom.grid_columnconfigure(1, weight=1)
    mom.grid_columnconfigure(2, weight=1)
    _kpi_card(mom, "Last 7 days", _fmt_hk(t7), f"{pct7:.1f}% of total spending").grid(
        row=0, column=0, sticky="nsew", padx=(0, PAD_SM),
    )
    _kpi_card(mom, "Last 30 days", _fmt_hk(t30), f"{pct30:.1f}% of total spending").grid(
        row=0, column=1, sticky="nsew", padx=PAD_SM,
    )
    _kpi_card(mom, "Last year", _fmt_hk(t365), f"{pct365:.1f}% of total spending").grid(
        row=0, column=2, sticky="nsew", padx=(PAD_SM, 0),
    )

    _forecasts_section(content, state)

    monthly = by_period(txs, "monthly")
    if monthly:
        _section_header(content, "Recent months")
        months_card = tk.Frame(
            content, bg=COLORS["surface"], highlightbackground=COLORS["border"], highlightthickness=1,
        )
        months_card.pack(fill="x", pady=(0, PAD_SM))
        inner_m = tk.Frame(months_card, bg=COLORS["surface"], padx=PAD_LG, pady=PAD_MD)
        inner_m.pack(fill="x")
        for key in sorted(monthly.keys())[-3:]:
            _mini_stat_row(inner_m, str(key), monthly[key])

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
    _tab_hero(
        frame,
        "Add a transaction",
        "Log an expense with date, amount, category, and an optional note.",
    )

    card_outer, card = _surface_card_with_accent(frame)
    card_outer.pack(fill="x", pady=(0, PAD_MD))

    _field_label(card, "Date (YYYY-MM-DD)")
    date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
    date_row = tk.Frame(card, bg=COLORS["surface"])
    date_row.pack(anchor="w", pady=(0, PAD_MD))
    ttk.Entry(date_row, textvariable=date_var, width=14).pack(side="left")
    ttk.Button(date_row, text="📅", width=3, command=lambda: show_date_picker(card, date_var)).pack(side="left", padx=(PAD_SM, 0))

    _field_label(card, "Amount (HKD)")
    amount_entry = ttk.Entry(card, width=15)
    amount_entry.pack(anchor="w", pady=(0, PAD_MD))

    _field_label(card, "Category")
    cat_var = tk.StringVar()
    cat_combo = ttk.Combobox(card, textvariable=cat_var, values=CATEGORIES, width=20)
    cat_combo.pack(anchor="w", pady=(0, PAD_MD))

    _field_label(card, "Description (optional)")
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
    ttk.Button(frame, text="Add transaction", command=do_add).pack(pady=PAD_SM)
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
    _tab_hero(
        frame,
        "Transactions",
        "Filter the list, refresh from disk, or edit the selected row.",
    )
    _section_header(frame, "Filters")

    date_filter_var = tk.StringVar()
    cat_filter_var = tk.StringVar()
    desc_filter_var = tk.StringVar()

    def category_choices() -> List[str]:
        cats = {c for c in CATEGORIES}
        for t in state["transactions"]:
            cats.add(t.category)
        return [""] + sorted(cats)

    filter_outer, filter_card = _surface_card_with_accent(frame)
    row1 = tk.Frame(filter_card, bg=COLORS["surface"])
    row1.pack(fill="x")
    tk.Label(row1, text="Date", bg=COLORS["surface"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).pack(side="left", padx=(0, PAD_SM))
    date_filter = ttk.Entry(row1, textvariable=date_filter_var, width=11)
    date_filter.pack(side="left", padx=(0, PAD_SM))
    ttk.Button(row1, text="📅", width=3, command=lambda: show_date_picker(filter_card, date_filter_var)).pack(side="left", padx=(0, PAD_MD))
    tk.Label(row1, text="Category", bg=COLORS["surface"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).pack(side="left", padx=(0, PAD_SM))
    cat_filter = ttk.Combobox(row1, textvariable=cat_filter_var, values=category_choices(), width=14, state="normal")
    cat_filter.pack(side="left", padx=(0, PAD_MD))

    row2 = tk.Frame(filter_card, bg=COLORS["surface"])
    row2.pack(fill="x", pady=(PAD_SM, 0))
    tk.Label(row2, text="Search description", bg=COLORS["surface"], fg=COLORS["text_muted"], font=(FONT_FAMILY, FONT_SIZE - 1)).pack(side="left", padx=(0, PAD_SM))
    desc_filter = ttk.Entry(row2, textvariable=desc_filter_var, width=40)
    desc_filter.pack(side="left", fill="x", expand=True)

    sep_below_filter = ttk.Separator(frame, orient="horizontal")
    filter_outer.pack(side="top", fill="x")
    sep_below_filter.pack(side="top", fill="x", pady=PAD_MD)
    _section_header(frame, "Your transactions")

    tree_outer, tree_host = _surface_card_with_accent(frame)
    tree_inner = tk.Frame(tree_host, bg=COLORS["surface"])
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

        wrap = tk.Frame(dlg, bg=COLORS["bg"], padx=PAD_MD, pady=PAD_MD)
        wrap.pack(fill="both", expand=True)
        tk.Label(wrap, text="Edit transaction", bg=COLORS["bg"], fg=COLORS["text"], font=FONT_SECTION).pack(anchor="w", pady=(0, PAD_MD))

        card_outer, card = _surface_card_with_accent(wrap)
        card_outer.pack(fill="both", expand=True)

        _field_label(card, "Date (YYYY-MM-DD)")
        date_var = tk.StringVar(value=t_orig.date)
        date_row = tk.Frame(card, bg=COLORS["surface"])
        date_row.pack(anchor="w", pady=(0, PAD_MD))
        ttk.Entry(date_row, textvariable=date_var, width=14).pack(side="left")
        ttk.Button(date_row, text="📅", width=3, command=lambda: show_date_picker(card, date_var)).pack(side="left", padx=(PAD_SM, 0))

        _field_label(card, "Amount (HKD)")
        amount_var = tk.StringVar(value=f"{abs(t_orig.amount):.2f}")
        ttk.Entry(card, textvariable=amount_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

        _field_label(card, "Category")
        cat_edit_var = tk.StringVar(value=t_orig.category)
        cat_edit = ttk.Combobox(card, textvariable=cat_edit_var, values=sorted(category_choices())[1:], width=20)
        cat_edit.pack(anchor="w", pady=(0, PAD_MD))

        _field_label(card, "Description")
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

    btn_row_outer = tk.Frame(frame)
    btn_row_outer.columnconfigure(0, weight=1)
    btn_row_outer.columnconfigure(1, weight=0)
    btn_row_outer.columnconfigure(2, weight=1)
    btn_row_tx = tk.Frame(btn_row_outer)
    ttk.Button(btn_row_tx, text="Refresh from file", command=refresh).pack(side="left", padx=(0, PAD_SM))
    ttk.Button(btn_row_tx, text="Edit selected", command=edit_selected).pack(side="left")
    btn_row_tx.grid(row=0, column=1)
    # Same pack pattern as Summary: pin footer with side=bottom, header with side=top, list expands in middle.
    btn_row_outer.pack(side="bottom", fill="x", pady=PAD_SM)
    sep_below_tree.pack(side="bottom", fill="x", pady=(0, PAD_MD))
    tree_outer.pack(fill="both", expand=True)
    apply_filters()

    def on_tab_shown() -> None:
        """Resync list from memory (e.g. after adding on another tab)."""
        apply_filters()

    return frame, on_tab_shown


def create_portfolio_tab(parent: ttk.Notebook) -> ttk.Frame:
    """Portfolio tab: full-page scroll (same pattern as Summary); inputs + results."""
    outer = ttk.Frame(parent, padding=PAD_LG)

    scroll_wrap = tk.Frame(outer, bg=COLORS["bg"])
    scroll_wrap.pack(fill="both", expand=True)
    p_canvas = tk.Canvas(scroll_wrap, bg=COLORS["bg"], highlightthickness=0)
    p_vsb = ttk.Scrollbar(scroll_wrap, orient="vertical", command=p_canvas.yview)
    content = tk.Frame(p_canvas, bg=COLORS["bg"])
    p_inner = p_canvas.create_window((0, 0), window=content, anchor="nw")

    def _p_canvas_width(event: Any) -> None:
        p_canvas.itemconfigure(p_inner, width=event.width)

    p_canvas.bind("<Configure>", _p_canvas_width)

    def _p_scrollregion(_event: Any) -> None:
        p_canvas.configure(scrollregion=p_canvas.bbox("all"))

    content.bind("<Configure>", _p_scrollregion)
    p_canvas.configure(yscrollcommand=p_vsb.set)
    p_canvas.pack(side="left", fill="both", expand=True)
    p_vsb.pack(side="right", fill="y")

    _tab_hero(
        content,
        "Portfolio (MockWealth)",
        "Set inputs and run a Monte Carlo-style simulation; results update below.",
    )
    _section_header(content, "Simulation inputs")

    inputs_outer, inputs_card = _surface_card_with_accent(content)
    inputs_outer.pack(fill="x", pady=(0, PAD_MD))

    _field_label(inputs_card, "Initial deposit (HKD)")
    init_var = tk.StringVar(value="10000")
    ttk.Entry(inputs_card, textvariable=init_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

    _field_label(inputs_card, "Monthly contribution (HKD)")
    monthly_var = tk.StringVar(value="500")
    ttk.Entry(inputs_card, textvariable=monthly_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

    _field_label(inputs_card, "Time horizon (months)")
    months_var = tk.StringVar(value="12")
    ttk.Entry(inputs_card, textvariable=months_var, width=15).pack(anchor="w", pady=(0, PAD_MD))

    _field_label(inputs_card, "Risk tolerance (1 = conservative … 5 = aggressive)")
    risk_var = tk.StringVar(value="3")
    ttk.Entry(inputs_card, textvariable=risk_var, width=5).pack(anchor="w", pady=(0, PAD_MD))

    _field_label(inputs_card, "Random seed (optional — same seed = same result)")
    seed_var = tk.StringVar(value="")
    ttk.Entry(inputs_card, textvariable=seed_var, width=15).pack(anchor="w", pady=(0, PAD_LG))

    output_outer, output_host = _surface_card_with_accent(content)
    results_body = tk.Frame(output_host, bg=COLORS["surface"])
    results_body.pack(fill="both", expand=True)

    def _sync_portfolio_scroll() -> None:
        p_canvas.update_idletasks()
        p_canvas.configure(scrollregion=p_canvas.bbox("all"))

    def _bind_portfolio_results_wheel() -> None:
        handler = _canvas_mousewheel_handler(p_canvas)

        def walk(w: tk.Widget) -> None:
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                w.bind(seq, handler)
            for ch in w.winfo_children():
                walk(ch)

        walk(results_body)

    tk.Label(
        results_body,
        text="Run the simulation above to see your allocation mix and projected portfolio values.",
        bg=COLORS["surface"],
        fg=COLORS["text_muted"],
        font=(FONT_FAMILY, FONT_SIZE),
        wraplength=480,
        justify="left",
    ).pack(anchor="w", pady=(0, PAD_SM))

    def _clear_results_body() -> None:
        for w in results_body.winfo_children():
            w.destroy()

    def _fmt_hk(x: float) -> str:
        return f"HK$ {x:,.2f}"

    def _render_results_error(message: str) -> None:
        _clear_results_body()
        err = tk.Frame(results_body, bg=COLORS["surface"])
        err.pack(fill="x")
        tk.Label(
            err, text=message, bg=COLORS["surface"], fg=COLORS["error"],
            font=(FONT_FAMILY, FONT_SIZE), wraplength=480, justify="left",
        ).pack(anchor="w")
        _sync_portfolio_scroll()
        _bind_portfolio_results_wheel()

    def _render_results_success(alloc: dict, result: dict) -> None:
        _clear_results_body()
        _portfolio_block_heading(
            results_body, "Allocation", "How your risk level maps to MockWealth asset classes.",
        )
        for ac, w in sorted(((a, wt) for a, wt in alloc.items() if wt > 0), key=lambda x: -x[1]):
            _portfolio_alloc_bar_row(results_body, ac, w)

        _portfolio_block_heading(
            results_body, "Projected portfolio value", "Monte Carlo simulation — 1000 paths; amounts in HKD.",
        )
        outcomes = tk.Frame(results_body, bg=COLORS["surface"])
        outcomes.pack(fill="x", pady=(0, PAD_MD))
        for c in range(3):
            outcomes.grid_columnconfigure(c, weight=1)
        _kpi_card(outcomes, "P10 (pessimistic)", _fmt_hk(result["p10"]), "Lower tail").grid(
            row=0, column=0, sticky="nsew", padx=(0, PAD_SM),
        )
        _kpi_card(outcomes, "P50 (median)", _fmt_hk(result["p50"]), "Typical outcome").grid(
            row=0, column=1, sticky="nsew", padx=PAD_SM,
        )
        _kpi_card(outcomes, "P90 (optimistic)", _fmt_hk(result["p90"]), "Upper tail").grid(
            row=0, column=2, sticky="nsew", padx=(PAD_SM, 0),
        )

        _portfolio_block_heading(
            results_body, "Risk metrics", "Tail loss, drawdown, volatility, and risk-adjusted return.",
        )
        risk_grid = tk.Frame(results_body, bg=COLORS["surface"])
        risk_grid.pack(fill="x", pady=(0, PAD_MD))
        for c in range(2):
            risk_grid.grid_columnconfigure(c, weight=1)
        _kpi_card(
            risk_grid, "5% VaR",
            _fmt_hk(result["var_5pct"]),
            "Loss in worst 5% of paths",
        ).grid(row=0, column=0, sticky="nsew", padx=(0, PAD_SM), pady=(0, PAD_SM))
        _kpi_card(
            risk_grid, "Avg max drawdown",
            f"{result['max_drawdown_avg'] * 100:.1f}%",
            "Peak-to-trough drop",
        ).grid(row=0, column=1, sticky="nsew", padx=(PAD_SM, 0), pady=(0, PAD_SM))
        _kpi_card(
            risk_grid, "Volatility",
            _fmt_hk(result["volatility"]),
            "Stdev of final values",
        ).grid(row=1, column=0, sticky="nsew", padx=(0, PAD_SM))
        _kpi_card(
            risk_grid, "Sharpe-like",
            f"{result['sharpe_like']:.2f}",
            f"Annualized {result['annualized_return'] * 100:.2f}%",
        ).grid(row=1, column=1, sticky="nsew", padx=(PAD_SM, 0))

        _portfolio_percent_strip(
            results_body,
            "Estimated probability of ending below your total contributions",
            float(result["loss_prob"]),
        )

        _sync_portfolio_scroll()
        _bind_portfolio_results_wheel()

    def run_sim():
        try:
            initial = float(init_var.get().strip())
            monthly = float(monthly_var.get().strip())
            months = int(months_var.get().strip())
            risk = int(risk_var.get().strip())
        except ValueError:
            _render_results_error("Invalid input. Use numbers for all fields.")
            return
        if initial < 0 or monthly < 0 or months <= 0 or risk < 1 or risk > 5:
            _render_results_error("Invalid values. Deposits and contributions must be non-negative; horizon and risk must be in range.")
            return
        seed_raw = seed_var.get().strip()
        seed = None
        if seed_raw:
            try:
                seed = int(seed_raw)
            except ValueError:
                _render_results_error("Seed must be a whole number (or blank).")
                return
        assets = portfolio.load_assets(portfolio.ASSETS_FILE)
        alloc = portfolio.get_allocation(risk)
        result = portfolio.simulate(initial, monthly, months, alloc, assets, seed=seed)
        _render_results_success(alloc, result)

    ttk.Separator(content, orient="horizontal").pack(fill="x", pady=PAD_MD)
    ttk.Button(content, text="Run simulation", command=run_sim).pack(pady=PAD_SM)
    _section_header(content, "Results")
    output_outer.pack(fill="x", pady=(0, PAD_SM))

    _bind_mousewheel_to_canvas_and_content(p_canvas, content)
    _sync_portfolio_scroll()
    return outer
