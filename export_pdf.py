"""
PDF export for the Personal Budget Assistant.
Generates a styled PDF report matching the Summary tab content.
Requires: fpdf2 (pip install fpdf2)
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

from fpdf import FPDF

from alerts import (
    run_all_alerts,
    split_alert_message,
)
from data import BudgetRule, Transaction
from gui_settings import load_gui_settings, pct_rules_as_tuples
from stats import (
    average_daily_spending,
    by_category,
    by_period,
    forecast_period_total,
    recommend_budget_caps,
    total_spending,
    trend_last_n_days,
)

# ---------------------------------------------------------------------------
# Design tokens (mirrors ui.py COLORS + helper colour maps)
# ---------------------------------------------------------------------------
_COLORS = {
    "accent": "#0d9488",
    "accent_light": "#ccfbf1",
    "text": "#1e293b",
    "text_muted": "#64748b",
    "bg": "#f5f6f8",
    "surface": "#ffffff",
    "border": "#e2e8f0",
}
_ALERT_THEME = {
    "overspend":          {"strip": "#e11d48", "bg": "#fff1f2", "title": "Budget cap exceeded"},
    "budget_pct_warn":    {"strip": "#d97706", "bg": "#fffbeb", "title": "Share of spending (warning)"},
    "budget_pct_critical":{"strip": "#b45309", "bg": "#fff7ed", "title": "Share of spending (critical)"},
    "budget_pct":         {"strip": "#d97706", "bg": "#fffbeb", "title": "Share of spending high"},
    "streak":             {"strip": "#7c3aed", "bg": "#f5f3ff", "title": "Consecutive overspend"},
    "uncategorized":      {"strip": "#475569", "bg": "#f8fafc", "title": "Uncategorized"},
    "subscription_creep": {"strip": "#ea580c", "bg": "#fff7ed", "title": "Subscription creep"},
    "forecast":           {"strip": "#ea580c", "bg": "#fff7ed", "title": "On pace to overspend"},
    "anomaly":            {"strip": "#dc2626", "bg": "#fef2f2", "title": "Spending anomaly"},
    "recurring":          {"strip": "#2563eb", "bg": "#eff6ff", "title": "Recurring charge detected"},
    "health":             {"strip": "#059669", "bg": "#ecfdf5", "title": "Budget health"},
    "general":            {"strip": "#0e7490", "bg": "#ecfeff", "title": "Notice"},
    "clear":              {"strip": "#059669", "bg": "#ecfdf5", "title": "All clear"},
}
_CATEGORY_BAR_COLORS = (
    "#0d9488", "#3b82f6", "#8b5cf6", "#f59e0b", "#ec4899",
    "#14b8a6", "#6366f1", "#84cc16", "#f43f5e",
)

# Page geometry (mm)
_MARGIN = 20
_PAGE_W = 210  # A4
_CONTENT_W = _PAGE_W - 2 * _MARGIN  # 170 mm


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _hex_rgb(h: str) -> Tuple[int, int, int]:
    """'#ff5733' → (255, 87, 51)"""
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


def _sanitize(text: str) -> str:
    """Replace characters outside Latin-1 so fpdf2 built-in fonts don't choke."""
    return text.replace("—", "-").replace("–", "-") \
               .replace("‘", "'").replace("’", "'") \
               .replace("“", '"').replace("”", '"') \
               .replace("…", "...").replace("•", "-")


# ---- Convenience wrappers that auto-sanitize text ----

def _cell(pdf: FPDF, w: float, h: float, txt: str, **kw: Any) -> None:
    FPDF.cell(pdf, w, h, _sanitize(txt), **kw)


def _multi_cell(pdf: FPDF, w: float, h: float, txt: str, **kw: Any) -> None:
    FPDF.multi_cell(pdf, w, h, _sanitize(txt), **kw)


def _cat_bar_color(name: str) -> str:
    h = sum(ord(c) for c in name.lower())
    return _CATEGORY_BAR_COLORS[h % len(_CATEGORY_BAR_COLORS)]


def _section_header(pdf: FPDF, title: str, w: float = 0) -> None:
    """Section header with teal underline accent."""
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    _cell(pdf, 0 if w == 0 else w, 6, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(*_hex_rgb(_COLORS["accent"]))
    if w == 0:
        w = _CONTENT_W
    pdf.rect(_MARGIN, pdf.get_y(), w, 0.6, "F")
    pdf.ln(3)


# ---------------------------------------------------------------------------
# Section renderers (each draws its content and advances y)
# ---------------------------------------------------------------------------

def _alerts_block(pdf: FPDF, state: dict, x0: float = 0, w: float = 0) -> None:
    txs: List[Transaction] = state.get("transactions", [])
    rules: List[BudgetRule] = state.get("rules", [])
    gs = state.get("gui_settings") or load_gui_settings()
    pct_rules = pct_rules_as_tuples(gs)
    consec = int(gs.get("consecutive_overspend_days", 3))
    creep = float(gs.get("subscription_creep_threshold_pct", 20.0))

    x0 = x0 or _MARGIN
    w = w or _CONTENT_W

    messages = run_all_alerts(
        txs, rules,
        pct_rules=pct_rules,
        consecutive_days=consec,
        subscription_creep_threshold_pct=creep,
        include_health=False,
    )

    _section_header(pdf, "Alerts", w)

    if not messages:
        _alert_banner(pdf, "clear", "No budget or behaviour warnings right now.", x0, w)
        return

    for msg in messages:
        kind, body = split_alert_message(msg)
        _alert_banner(pdf, kind, body or msg, x0, w)


def _alert_banner(pdf: FPDF, kind: str, body: str, x0: float = 0, w: float = 0) -> None:
    theme = _ALERT_THEME.get(kind, _ALERT_THEME["general"])
    x0 = x0 or _MARGIN
    w = w or _CONTENT_W
    strip_c = _hex_rgb(theme["strip"])
    bg_c = _hex_rgb(theme["bg"])
    title = theme["title"]

    y0 = pdf.get_y()
    pdf.set_fill_color(*bg_c)
    pdf.rect(x0, y0, w, 0, "F")

    # Strip
    pdf.set_fill_color(*strip_c)
    pdf.rect(x0, y0, 1.5, 10, "F")

    # Title
    pdf.set_xy(x0 + 3, y0 + 0.5)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*strip_c)
    _cell(pdf, 0, 3, title.upper(), new_x="LMARGIN", new_y="NEXT")

    # Body
    pdf.set_x(x0 + 3)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    _multi_cell(pdf, w - 4, 3.2, body)

    pdf.ln(1)


def _kpi_row(pdf: FPDF, cards: List[Tuple[str, str, str]]) -> None:
    """Three KPI cards in a row: (title, value, subtitle) each."""
    col_w = _CONTENT_W / 3.0
    card_h = 18

    for idx, (title, value, subtitle) in enumerate(cards):
        x = _MARGIN + idx * col_w
        y0 = pdf.get_y()

        # Surface card
        pdf.set_fill_color(*_hex_rgb(_COLORS["surface"]))
        pdf.rect(x, y0, col_w - 1.2, card_h, "F")
        pdf.set_draw_color(*_hex_rgb(_COLORS["border"]))
        pdf.rect(x, y0, col_w - 1.2, card_h, "D")
        # Teal strip
        pdf.set_fill_color(*_hex_rgb(_COLORS["accent"]))
        pdf.rect(x, y0, 0.8, card_h, "F")

        # Title
        pdf.set_xy(x + 2, y0 + 1)
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
        _cell(pdf,col_w - 4, 2.5, title)

        # Value
        pdf.set_xy(x + 2, y0 + 5.5)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
        _cell(pdf,col_w - 4, 5, value)

        # Subtitle
        if subtitle:
            pdf.set_xy(x + 2, y0 + 12)
            pdf.set_font("Helvetica", "", 6.5)
            pdf.set_text_color(*_hex_rgb(_COLORS["accent"]))
            _cell(pdf,col_w - 4, 2.5, subtitle)

    pdf.set_y(pdf.get_y() + card_h + 2)


def _category_bars(pdf: FPDF, state: dict, x0: float = 0, w: float = 0) -> None:
    txs = state.get("transactions", [])
    if not txs:
        return
    total = total_spending(txs)
    if total == 0:
        return
    cats = by_category(txs)
    x0 = x0 or _MARGIN
    w = w or _CONTENT_W

    _section_header(pdf, "Spending by Category", w)

    bar_w = min(70, w - 50)
    for cat_name, amt in sorted(cats.items(), key=lambda x: x[1], reverse=True):
        pct = (amt / total) * 100.0
        y0 = pdf.get_y()

        # Category name
        pdf.set_xy(x0, y0)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
        _cell(pdf, 14, 4, cat_name.capitalize())

        # Track
        track_x = x0 + 15
        pdf.set_fill_color(*_hex_rgb(_COLORS["border"]))
        pdf.rect(track_x, y0 + 0.8, bar_w, 3, "D")

        # Fill
        fill_w = max(0.6, bar_w * (pct / 100.0))
        bar_color = _hex_rgb(_cat_bar_color(cat_name))
        pdf.set_fill_color(*bar_color)
        pdf.rect(track_x, y0 + 0.8, fill_w, 3, "F")

        # Percentage
        pdf.set_xy(track_x + bar_w + 1.5, y0)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*_hex_rgb(_COLORS["accent"]))
        _cell(pdf, 8, 4, f"{pct:.0f}%")

        # HK$ amount
        pdf.set_xy(track_x + bar_w + 10, y0)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
        _cell(pdf, 0, 4, f"HK$ {amt:,.2f}")

        pdf.ln(4)


def _momentum(pdf: FPDF, state: dict) -> None:
    txs = state.get("transactions", [])
    if not txs:
        return
    total = total_spending(txs)
    if total == 0:
        total = 1e-12

    t7 = trend_last_n_days(txs, 7)
    t30 = trend_last_n_days(txs, 30)
    t365 = trend_last_n_days(txs, 365)
    pct7 = (t7 / total) * 100.0
    pct30 = (t30 / total) * 100.0
    pct365 = (t365 / total) * 100.0

    _section_header(pdf, "Momentum")
    _kpi_row(pdf, [
        ("Last 7 days", f"HK$ {t7:,.2f}", f"{pct7:.1f}% of total spending"),
        ("Last 30 days", f"HK$ {t30:,.2f}", f"{pct30:.1f}% of total spending"),
        ("Last year", f"HK$ {t365:,.2f}", f"{pct365:.1f}% of total spending"),
    ])


def _forecasts(pdf: FPDF, state: dict, x0: float = 0, w: float = 0) -> None:
    txs = state.get("transactions", [])
    rules = state.get("rules", [])
    if not rules or not txs:
        return
    x0 = x0 or _MARGIN
    w = w or _CONTENT_W

    _section_header(pdf, "Forecasts", w)

    y0 = pdf.get_y()
    pdf.set_fill_color(*_hex_rgb(_COLORS["surface"]))
    pdf.rect(x0, y0, w, 0, "F")

    pdf.set_xy(x0 + 2, y0 + 1)
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
    _multi_cell(pdf, w - 4, 2.8,
                   "Projected end-of-period total at current pace.")

    pdf.set_y(y0 + 7)
    bar_w = min(60, w - 60)
    for r in rules:
        fc = forecast_period_total(txs, r)
        pct = fc["forecast_pct"]
        y1 = pdf.get_y()

        if pct >= 110:
            fg = (220, 38, 38)
        elif pct >= 90:
            fg = (234, 88, 12)
        else:
            fg = (5, 150, 105)

        pdf.set_xy(x0 + 2, y1)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
        label = f"{r.category.capitalize()} ({r.period})"
        _cell(pdf, 24, 4, label)

        track_x = x0 + 27
        pdf.set_fill_color(*_hex_rgb(_COLORS["border"]))
        pdf.rect(track_x, y1 + 0.5, bar_w, 3, "D")

        display_pct = max(0.0, min(100.0, pct))
        fill_w = max(0.6, bar_w * (display_pct / 100.0))
        pdf.set_fill_color(*fg)
        pdf.rect(track_x, y1 + 0.5, fill_w, 3, "F")

        pdf.set_xy(track_x + bar_w + 1.5, y1)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*fg)
        _cell(pdf, 8, 4, f"{pct:.0f}%")

        detail = (f"HK$ {fc['forecast']:,.0f} of {fc['threshold']:,.0f}  "
                  f"(day {fc['days_elapsed']}/{fc['days_total']})")
        pdf.set_xy(track_x + bar_w + 10, y1)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
        _cell(pdf, 0, 4, detail)

        pdf.ln(4.5)

    pdf.ln(1)


def _recommended_budgets(pdf: FPDF, state: dict, x0: float = 0, w: float = 0) -> None:
    txs = state.get("transactions", [])
    if not txs:
        return
    recommendations = recommend_budget_caps(txs, period="monthly", safety_factor=1.2)
    if not recommendations:
        return
    x0 = x0 or _MARGIN
    w = w or _CONTENT_W

    _section_header(pdf, "Recommended Budgets", w)

    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
    _multi_cell(pdf, w, 2.8,
                   "Suggested monthly caps with 20% safety margin.")
    pdf.ln(1)

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    for cat, amt in sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:6]:
        _cell(pdf, 0, 4, f"{cat.capitalize()}: HK$ {amt:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _recent_months(pdf: FPDF, state: dict, x0: float = 0, w: float = 0) -> None:
    txs = state.get("transactions", [])
    if not txs:
        return
    monthly = by_period(txs, "monthly")
    if not monthly:
        return
    x0 = x0 or _MARGIN
    w = w or _CONTENT_W

    _section_header(pdf, "Recent Months", w)

    for key in sorted(monthly.keys())[-3:]:
        y0 = pdf.get_y()
        pdf.set_fill_color(*_hex_rgb(_COLORS["accent_light"]))
        pdf.rect(x0, y0, w, 4.5, "F")

        pdf.set_xy(x0 + 2, y0 + 0.5)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
        _cell(pdf, w * 0.5, 3, str(key))

        pdf.set_xy(x0 + w - 30, y0 + 0.5)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["accent"]))
        _cell(pdf, 0, 3, f"HK$ {monthly[key]:,.2f}")

        pdf.ln(4.5)
    pdf.ln(1)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_summary_pdf(filepath: str, state: dict) -> str:
    """Generate a styled PDF of the Summary tab content.

    Parameters
    ----------
    filepath : str
        Destination path for the .pdf file.
    state : dict
        The GUI state dict (must contain ``transactions``, ``rules``,
        and optionally ``gui_settings``).

    Returns
    -------
    str
        The filepath that was written to.

    Raises
    ------
    ImportError
        If ``fpdf2`` is not installed.
    OSError
        If the file cannot be written.
    """
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Title block ──
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    _cell(pdf, 0, 8, "Personal Budget Assistant - Summary Report",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
    _cell(pdf, 0, 4, f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    # ── KPI row (full width, 3 columns) ──
    txs: List[Transaction] = state.get("transactions", [])
    if txs:
        kpi_total = total_spending(txs)
        kpi_avg = average_daily_spending(txs)
        kpi_t7 = trend_last_n_days(txs, 7)
    else:
        kpi_total = kpi_avg = kpi_t7 = 0.0
    _kpi_row(pdf, [
        ("Total spending", f"HK${kpi_total:,.2f}", f"{len(txs)} transactions"),
        ("Avg. per active day", f"HK${kpi_avg:,.2f}", "Days with at least one expense"),
        ("Last 7 days", f"HK${kpi_t7:,.2f}", "Rolling window"),
    ])

    # ── Alerts (full width) ──
    _alerts_block(pdf, state, _MARGIN, _CONTENT_W)
    pdf.ln(1)

    # ── Two-column row: Spending by Category | Forecasts ──
    col_w = _CONTENT_W / 2 - 2
    y_row = pdf.get_y()
    _category_bars(pdf, state, _MARGIN, col_w + 8)
    y_left = pdf.get_y()

    pdf.set_xy(_MARGIN + col_w + 10, y_row)
    _forecasts(pdf, state, _MARGIN + col_w + 10, col_w - 2)
    y_right = pdf.get_y()

    pdf.set_y(max(y_left, y_right) + 1)

    # ── Momentum (full width, 3 columns) ──
    _momentum(pdf, state)

    # ── Two-column row: Recommended Budgets | Recent Months ──
    y_row = pdf.get_y()
    _recommended_budgets(pdf, state, _MARGIN, col_w + 8)
    y_left = pdf.get_y()

    pdf.set_xy(_MARGIN + col_w + 10, y_row)
    _recent_months(pdf, state, _MARGIN + col_w + 10, col_w - 2)
    y_right = pdf.get_y()

    pdf.set_y(max(y_left, y_right) + 1)

    pdf.output(filepath)
    return filepath
