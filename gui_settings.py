"""
Alert thresholds and pct-rule normalization. Values are stored in budgets.csv (unified with caps).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import data as _data

from data import load_budgets_bundle, save_budgets_bundle

# Legacy path (migration only; data.load_budgets_bundle reads it if present)
SETTINGS_PATH = Path(__file__).resolve().parent / "gui_settings.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "pct_rules": [],
    "consecutive_overspend_days": 3,
    "subscription_creep_threshold_pct": 20.0,
}


def _parse_pct_row(row: Any) -> Optional[List[Any]]:
    """Return [cat, warn, crit] lists or None if invalid."""
    if not isinstance(row, (list, tuple)) or len(row) < 2:
        return None
    try:
        cat = str(row[0]).strip().lower()
        w = float(row[1])
        c = float(row[2]) if len(row) >= 3 else 0.0
    except (TypeError, ValueError, IndexError):
        return None
    if not cat:
        return None
    if not (0 < w <= 100):
        return None
    if c < 0:
        c = 0.0
    if c > 100:
        c = 100.0
    if c > 0 and c <= w:
        return None
    return [cat, w, c]


def normalize_gui_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate defaults and dedupe pct_rules (replacing former _normalize)."""
    out = DEFAULT_SETTINGS.copy()
    out.update(data)
    out.pop("alert_strip_width", None)  # removed from UI; ignore if present in old files
    raw = out.get("pct_rules")
    pr: List[List[Any]] = []
    if isinstance(raw, list):
        for row in raw:
            prr = _parse_pct_row(row)
            if prr is not None:
                pr.append(prr)
    seen_cats: set = set()
    pr_dedup: List[List[Any]] = []
    for row in pr:
        ck = str(row[0]).strip().lower()
        if ck in seen_cats:
            continue
        seen_cats.add(ck)
        pr_dedup.append(row)
    out["pct_rules"] = pr_dedup
    try:
        d = int(out.get("consecutive_overspend_days", 3))
        out["consecutive_overspend_days"] = max(1, min(30, d))
    except (TypeError, ValueError):
        out["consecutive_overspend_days"] = 3
    try:
        c = float(out.get("subscription_creep_threshold_pct", 20.0))
        out["subscription_creep_threshold_pct"] = max(0.0, min(500.0, c))
    except (TypeError, ValueError):
        out["subscription_creep_threshold_pct"] = 20.0
    try:
        u = out.get("uncategorized_min_transactions")
        if u is not None:
            out["uncategorized_min_transactions"] = max(1, int(u))
    except (TypeError, ValueError):
        out.pop("uncategorized_min_transactions", None)
    return out


def load_gui_settings() -> Dict[str, Any]:
    _, gs = load_budgets_bundle(str(_data.BUDGETS_PATH))
    return gs


def save_gui_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    rules, _ = load_budgets_bundle(str(_data.BUDGETS_PATH))
    return save_budgets_bundle(rules, data, str(_data.BUDGETS_PATH))


def pct_rules_as_tuples(settings: Dict[str, Any]) -> List[Tuple[str, float, float]]:
    """Rows for alerts.normalize_pct_rules_rows / check_percentage_thresholds."""
    out: List[Tuple[str, float, float]] = []
    for row in settings.get("pct_rules") or []:
        pr = _parse_pct_row(row)
        if pr is not None:
            out.append((str(pr[0]), float(pr[1]), float(pr[2])))
    return out
