"""
Load/save GUI-only settings (alert thresholds, etc.) in gui_settings.json.
pct_rules: list of [category, warning_pct, critical_pct] — critical 0 = warning tier only.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


def _normalize(data: Dict[str, Any]) -> Dict[str, Any]:
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
    return out


def load_gui_settings() -> Dict[str, Any]:
    if not SETTINGS_PATH.exists():
        data = _normalize({})
        save_gui_settings(data)
        return data
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return _normalize({})
        return _normalize(raw)
    except (OSError, json.JSONDecodeError):
        return _normalize({})


def save_gui_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize(data)
    SETTINGS_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    return normalized


def pct_rules_as_tuples(settings: Dict[str, Any]) -> List[Tuple[str, float, float]]:
    """Rows for alerts.normalize_pct_rules_rows / check_percentage_thresholds."""
    out: List[Tuple[str, float, float]] = []
    for row in settings.get("pct_rules") or []:
        pr = _parse_pct_row(row)
        if pr is not None:
            out.append((str(pr[0]), float(pr[1]), float(pr[2])))
    return out
