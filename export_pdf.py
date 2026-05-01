"""
PDF export for the Personal Budget Assistant.
Generates a styled PDF report matching the Summary tab content.
Requires: fpdf2 (pip install fpdf2)
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

from fpdf import FPDF

from alerts import (
    compute_health_score,
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
_GRADE_COLORS = {
    "A": "#059669", "B": "#65a30d", "C": "#ca8a04",
    "D": "#ea580c", "F": "#dc2626",
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


def _section_header(pdf: FPDF, title: str) -> None:
    """Section header with teal underline accent."""
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    _cell(pdf,0, 6, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(*_hex_rgb(_COLORS["accent"]))
    pdf.rect(_MARGIN, pdf.get_y(), _CONTENT_W, 0.6, "F")
    pdf.ln(3)


# ---------------------------------------------------------------------------
# Section renderers (each draws its content and advances y)
# ---------------------------------------------------------------------------

def _alerts_block(pdf: FPDF, state: dict) -> None:
    txs: List[Transaction] = state.get("transactions", [])
    rules: List[BudgetRule] = state.get("rules", [])
    gs = state.get("gui_settings") or load_gui_settings()
    pct_rules = pct_rules_as_tuples(gs)
    consec = int(gs.get("consecutive_overspend_days", 3))
    creep = float(gs.get("subscription_creep_threshold_pct", 20.0))

    messages = run_all_alerts(
        txs, rules,
        pct_rules=pct_rules,
        consecutive_days=consec,
        subscription_creep_threshold_pct=creep,
        include_health=False,
    )

    _section_header(pdf, "Alerts")

    if not messages:
        _alert_banner(pdf, "clear", "No budget or behaviour warnings right now.")
        return

    for msg in messages:
        kind, body = split_alert_message(msg)
        _alert_banner(pdf, kind, body or msg)


def _alert_banner(pdf: FPDF, kind: str, body: str) -> None:
    theme = _ALERT_THEME.get(kind, _ALERT_THEME["general"])
    strip_c = _hex_rgb(theme["strip"])
    bg_c = _hex_rgb(theme["bg"])
    title = theme["title"]

    y0 = pdf.get_y()
    pdf.set_fill_color(*bg_c)
    pdf.rect(_MARGIN, y0, _CONTENT_W, 0, "F")  # will expand via later fills

    # Strip
    pdf.set_fill_color(*strip_c)
    pdf.rect(_MARGIN, y0, 1.5, 12, "F")

    # Title
    pdf.set_xy(_MARGIN + 3, y0 + 0.5)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*strip_c)
    _cell(pdf,0, 3.5, title.upper(), new_x="LMARGIN", new_y="NEXT")

    # Body
    pdf.set_x(_MARGIN + 3)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    _multi_cell(pdf,_CONTENT_W - 4, 3.5, body)

    pdf.ln(1)


def _health_hero(pdf: FPDF, state: dict) -> None:
    txs = state.get("transactions", [])
    rules = state.get("rules", [])
    if not txs:
        return

    h = compute_health_score(txs, rules)
    grade = h["grade"]
    strip_c = _hex_rgb(_GRADE_COLORS.get(grade, _COLORS["accent"]))

    _section_header(pdf, "Budget Health")

    y0 = pdf.get_y()
    card_h = 26
    # Surface card background
    pdf.set_fill_color(*_hex_rgb(_COLORS["surface"]))
    pdf.rect(_MARGIN, y0, _CONTENT_W, card_h, "F")
    # Border
    pdf.set_draw_color(*_hex_rgb(_COLORS["border"]))
    pdf.rect(_MARGIN, y0, _CONTENT_W, card_h, "D")
    # Grade strip
    pdf.set_fill_color(*strip_c)
    pdf.rect(_MARGIN, y0, 1.8, card_h, "F")

    # Left column — score
    pdf.set_xy(_MARGIN + 4, y0 + 1)
    pdf.set_font("Helvetica", "B", 6)
    pdf.set_text_color(*strip_c)
    _cell(pdf,0, 3, "BUDGET HEALTH", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(_MARGIN + 4)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    _cell(pdf,12, 7, f"{h['score']:.0f}")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
    _cell(pdf,0, 7, "/ 100", new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(_MARGIN + 4)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*strip_c)
    _cell(pdf,0, 4, f"Grade {grade}", new_x="LMARGIN", new_y="NEXT")

    # Right column — stats
    right_x = _MARGIN + _CONTENT_W - 50
    pdf.set_xy(right_x, y0 + 2)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    _cell(pdf,0, 3.5, f"Max cap utilised: {h['max_util']:.0f}%", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(right_x, y0 + 8)
    _cell(pdf,0, 3.5, f"Projected end-of-period: {h['max_forecast']:.0f}%", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(right_x, y0 + 14)
    _cell(pdf,0, 3.5, f"Transactions categorised: {h['categorized_pct']:.0f}%", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(y0 + card_h + 3)


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


def _category_bars(pdf: FPDF, state: dict) -> None:
    txs = state.get("transactions", [])
    if not txs:
        return
    total = total_spending(txs)
    if total == 0:
        return
    cats = by_category(txs)

    _section_header(pdf, "Spending by Category")

    bar_w = 80
    for cat_name, amt in sorted(cats.items(), key=lambda x: x[1], reverse=True):
        pct = (amt / total) * 100.0
        y0 = pdf.get_y()

        # Category name
        pdf.set_xy(_MARGIN, y0)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
        _cell(pdf,16, 4, cat_name.capitalize())

        # Track
        track_x = _MARGIN + 17
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
        _cell(pdf,10, 4, f"{pct:.0f}%")

        # HK$ amount
        pdf.set_xy(track_x + bar_w + 12, y0)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
        _cell(pdf,0, 4, f"HK$ {amt:,.2f}")

        pdf.ln(4.5)


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


def _forecasts(pdf: FPDF, state: dict) -> None:
    txs = state.get("transactions", [])
    rules = state.get("rules", [])
    if not rules or not txs:
        return

    _section_header(pdf, "Forecasts")

    y0 = pdf.get_y()
    pdf.set_fill_color(*_hex_rgb(_COLORS["surface"]))
    pdf.rect(_MARGIN, y0, _CONTENT_W, 0, "F")  # background surface card

    pdf.set_xy(_MARGIN + 2, y0 + 1)
    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
    _multi_cell(pdf,_CONTENT_W - 4, 2.8,
                   "Projected end-of-period total at current pace. "
                   "Green under cap, orange 90%+, red 110%+.")

    pdf.set_y(y0 + 8)
    bar_w = 70
    for r in rules:
        fc = forecast_period_total(txs, r)
        pct = fc["forecast_pct"]
        y1 = pdf.get_y()

        # Pick colour
        if pct >= 110:
            fg = (220, 38, 38)   # red
        elif pct >= 90:
            fg = (234, 88, 12)   # orange
        else:
            fg = (5, 150, 105)   # green

        # Rule label
        pdf.set_xy(_MARGIN + 2, y1)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
        label = f"{r.category.capitalize()} ({r.period})"
        _cell(pdf,28, 4, label)

        # Track
        track_x = _MARGIN + 31
        pdf.set_fill_color(*_hex_rgb(_COLORS["border"]))
        pdf.rect(track_x, y1 + 0.5, bar_w, 3.5, "D")

        # Fill
        display_pct = max(0.0, min(100.0, pct))
        fill_w = max(0.6, bar_w * (display_pct / 100.0))
        pdf.set_fill_color(*fg)
        pdf.rect(track_x, y1 + 0.5, fill_w, 3.5, "F")

        # Percentage
        pdf.set_xy(track_x + bar_w + 1.5, y1)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*fg)
        _cell(pdf,8, 4, f"{pct:.0f}%")

        # Detail
        detail = (f"HK$ {fc['forecast']:,.0f} of {fc['threshold']:,.0f}  "
                  f"(day {fc['days_elapsed']}/{fc['days_total']})")
        pdf.set_xy(track_x + bar_w + 10, y1)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
        _cell(pdf,0, 4, detail)

        pdf.ln(5)

    pdf.ln(2)


def _recommended_budgets(pdf: FPDF, state: dict) -> None:
    txs = state.get("transactions", [])
    if not txs:
        return
    recommendations = recommend_budget_caps(txs, period="monthly", safety_factor=1.2)
    if not recommendations:
        return

    _section_header(pdf, "Recommended Budgets")

    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
    _multi_cell(pdf,_CONTENT_W, 2.8,
                   "Suggested monthly cap values based on your average monthly spending "
                   "with a 20% safety margin.")
    pdf.ln(1.5)

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
    for cat, amt in sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:6]:
        _cell(pdf,0, 4.5, f"{cat.capitalize()}: HK$ {amt:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _recent_months(pdf: FPDF, state: dict) -> None:
    txs = state.get("transactions", [])
    if not txs:
        return
    monthly = by_period(txs, "monthly")
    if not monthly:
        return

    _section_header(pdf, "Recent Months")

    for key in sorted(monthly.keys())[-3:]:
        y0 = pdf.get_y()
        pdf.set_fill_color(*_hex_rgb(_COLORS["accent_light"]))
        pdf.rect(_MARGIN, y0, _CONTENT_W, 5.5, "F")

        pdf.set_xy(_MARGIN + 3, y0 + 0.8)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["text"]))
        _cell(pdf,_CONTENT_W * 0.5, 3.5, str(key))

        pdf.set_xy(_MARGIN + _CONTENT_W - 35, y0 + 0.8)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*_hex_rgb(_COLORS["accent"]))
        _cell(pdf,0, 3.5, f"HK$ {monthly[key]:,.2f}")

        pdf.ln(5.5)
    pdf.ln(2)


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
    _cell(pdf,0, 8, "Personal Budget Assistant — Summary Report",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*_hex_rgb(_COLORS["text_muted"]))
    _cell(pdf,0, 4, f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── KPI row (appears even when no transactions) ──
    txs: List[Transaction] = state.get("transactions", [])
    if txs:
        total = total_spending(txs)
        avg_day = average_daily_spending(txs)
        t7 = trend_last_n_days(txs, 7)
    else:
        total = avg_day = t7 = 0.0
    _kpi_row(pdf, [
        ("Total spending", f"HK$ {total:,.2f}", f"{len(txs)} transactions"),
        ("Avg. per active day", f"HK$ {avg_day:,.2f}", "Days with at least one expense"),
        ("Last 7 days", f"HK$ {t7:,.2f}", "Rolling window"),
    ])

    # ── Sections ──
    _alerts_block(pdf, state)
    _health_hero(pdf, state)
    _category_bars(pdf, state)
    _momentum(pdf, state)
    _forecasts(pdf, state)
    _recommended_budgets(pdf, state)
    _recent_months(pdf, state)

    pdf.output(filepath)
    return filepath
