"""
Data models and file I/O for the Personal Budget and Spending Assistant.
Handles transactions and budget rules in CSV format.
"""

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Default categories
DEFAULT_CATEGORIES = ["food", "transport", "subscriptions", "shopping", "other"]

# Single config file: budget caps + % rules + alert settings (replaces separate gui_settings.json)
BUDGETS_FILE = "budgets.csv"
BUDGETS_PATH = Path(__file__).resolve().parent / BUDGETS_FILE

_ROW_CAP = "cap"
_ROW_PCT = "pct"
_ROW_SETTING = "setting"

_UNIFIED_FIELDNAMES = ("row_type", "v1", "v2", "v3", "v4")

_SETTING_KEYS_IN_ORDER = (
    "consecutive_overspend_days",
    "subscription_creep_threshold_pct",
    "uncategorized_min_transactions",
)


@dataclass
class Transaction:
    """A single spending transaction."""
    date: str       # YYYY-MM-DD
    amount: float   # Negative for expenses
    category: str
    description: str

    def __post_init__(self):
        if self.amount > 0:
            self.amount = -abs(self.amount)  # Expenses are negative


@dataclass
class BudgetRule:
    """A budget rule for alerts."""
    category: str
    period: str     # daily, weekly, monthly
    threshold: float
    alert_type: str


def load_transactions(path: str) -> List[Transaction]:
    """Load transactions from CSV. Returns empty list if file missing or empty."""
    p = Path(path)
    if not p.exists():
        print(f"  [Info] Transactions file not found. Using empty list.")
        return []
    if p.stat().st_size == 0:
        return []

    transactions = []
    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and "date" not in (reader.fieldnames or []):
            print(f"  [Warn] Invalid CSV header in {path}. Expected: date,amount,category,description")
            return []
        for i, row in enumerate(reader):
            try:
                date_str = row.get("date", "").strip()
                amount = float(row.get("amount", 0))
                category = (row.get("category") or "").strip().lower() or "other"
                description = (row.get("description") or "").strip()
                _validate_date(date_str)
                transactions.append(Transaction(date=date_str, amount=amount, category=category, description=description))
            except (ValueError, KeyError) as e:
                print(f"  [Warn] Skipping malformed row {i + 2}: {e}")
    return transactions


def save_transactions(transactions: List[Transaction], path: str) -> None:
    """Save transactions to CSV."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "amount", "category", "description"])
        writer.writeheader()
        for t in transactions:
            writer.writerow({"date": t.date, "amount": t.amount, "category": t.category, "description": t.description})


def _lower_header_map(fieldnames: Optional[List[str]]) -> Dict[str, str]:
    return {str(f).strip().lower(): f for f in (fieldnames or []) if f}


def _row_col(row: Dict[str, str], hmap: Dict[str, str], *candidates: str) -> str:
    for c in candidates:
        k = c.lower()
        if k in hmap:
            v = row.get(hmap[k])
            return (v or "").strip() if v is not None else ""
    return ""


def _parse_legacy_cap_rows(rows: List[Dict[str, str]], fieldnames: Optional[List[str]]) -> List[BudgetRule]:
    rules: List[BudgetRule] = []
    for i, row in enumerate(rows):
        try:
            category = (row.get("category") or "").strip().lower()
            period = (row.get("period") or "").strip().lower()
            threshold = float(row.get("threshold", 0))
            alert_type = (row.get("alert_type") or "overspend").strip()
            if not category or period not in ("daily", "weekly", "monthly"):
                continue
            rules.append(BudgetRule(category=category, period=period, threshold=threshold, alert_type=alert_type))
        except (ValueError, KeyError) as e:
            print(f"  [Warn] Skipping malformed budget row {i + 2}: {e}")
    return rules


def _parse_unified_cap_pct_setting(
    rows: List[Dict[str, str]], fieldnames: Optional[List[str]],
) -> Tuple[List[BudgetRule], Dict[str, Any]]:
    hmap = _lower_header_map(fieldnames)
    rules: List[BudgetRule] = []
    pct_rules: List[List[Any]] = []
    settings_raw: Dict[str, Any] = {}
    for row in rows:
        rt = _row_col(row, hmap, "row_type").lower()
        if rt in ("cap", "budget_cap"):
            try:
                category = _row_col(row, hmap, "v1").strip().lower()
                period = _row_col(row, hmap, "v2").strip().lower()
                threshold = float(_row_col(row, hmap, "v3") or 0)
                alert_type = _row_col(row, hmap, "v4") or "overspend"
                if not category or period not in ("daily", "weekly", "monthly"):
                    continue
                rules.append(BudgetRule(category=category, period=period, threshold=threshold, alert_type=alert_type))
            except (ValueError, TypeError):
                continue
        elif rt in ("pct", "pct_rule"):
            try:
                cat = _row_col(row, hmap, "v1").strip().lower()
                w = float(_row_col(row, hmap, "v2") or 0)
                c = float(_row_col(row, hmap, "v3") or 0)
                if cat:
                    pct_rules.append([cat, w, c])
            except (ValueError, TypeError):
                continue
        elif rt in ("setting", "meta"):
            key = _row_col(row, hmap, "v1").strip()
            val_s = _row_col(row, hmap, "v2")
            if not key:
                continue
            if key == "consecutive_overspend_days":
                try:
                    settings_raw[key] = int(float(val_s))
                except ValueError:
                    pass
            elif key == "subscription_creep_threshold_pct":
                try:
                    settings_raw[key] = float(val_s)
                except ValueError:
                    pass
            elif key == "uncategorized_min_transactions":
                try:
                    settings_raw[key] = int(float(val_s))
                except ValueError:
                    pass
            else:
                settings_raw[key] = val_s

    gs: Dict[str, Any] = dict(settings_raw)
    gs["pct_rules"] = pct_rules
    return rules, gs


def load_budgets_bundle(path: Optional[str] = None) -> Tuple[List[BudgetRule], Dict[str, Any]]:
    """
    Load budget caps, category-% rules, and alert settings from budgets.csv (unified format).
    Migrates legacy budgets.csv (caps only) and optional gui_settings.json once.
    """
    from gui_settings import normalize_gui_settings

    path = path or str(BUDGETS_PATH)
    p = Path(path)
    legacy_json = p.parent / "gui_settings.json"

    if not p.exists():
        if legacy_json.exists():
            try:
                raw = json.loads(legacy_json.read_text(encoding="utf-8"))
                gs = normalize_gui_settings(raw if isinstance(raw, dict) else {})
            except (OSError, json.JSONDecodeError):
                gs = normalize_gui_settings({})
            save_budgets_bundle([], gs, str(p))
            return [], gs
        gs = normalize_gui_settings({})
        save_budgets_bundle([], gs, str(p))
        return [], gs

    if p.stat().st_size == 0:
        return [], normalize_gui_settings({})

    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        fns = {str(x).strip().lower() for x in fieldnames}
        rows = list(reader)

    if not rows and "row_type" not in fns:
        return [], normalize_gui_settings({})

    if "row_type" in fns:
        rules, gs_partial = _parse_unified_cap_pct_setting(rows, fieldnames)
        return rules, normalize_gui_settings(gs_partial)

    if "category" in fns and "period" in fns:
        rules = _parse_legacy_cap_rows(rows, fieldnames)
        if legacy_json.exists():
            try:
                raw = json.loads(legacy_json.read_text(encoding="utf-8"))
                gs = normalize_gui_settings(raw if isinstance(raw, dict) else {})
            except (OSError, json.JSONDecodeError):
                gs = normalize_gui_settings({})
        else:
            gs = normalize_gui_settings({})
        return rules, gs

    print(f"  [Warn] Unrecognized budgets.csv layout in {p}. Expected unified (row_type) or legacy caps.")
    return [], normalize_gui_settings({})


def save_budgets_bundle(rules: List[BudgetRule], gui_settings: Dict[str, Any], path: Optional[str] = None) -> Dict[str, Any]:
    """Write unified budgets.csv. Returns normalized gui_settings dict."""
    from gui_settings import normalize_gui_settings

    path = path or str(BUDGETS_PATH)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    merged_gs = normalize_gui_settings(dict(gui_settings))

    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(_UNIFIED_FIELDNAMES))
        w.writeheader()
        for r in rules:
            w.writerow(
                {
                    "row_type": _ROW_CAP,
                    "v1": r.category,
                    "v2": r.period,
                    "v3": f"{r.threshold:g}" if r.threshold == int(r.threshold) else str(r.threshold),
                    "v4": r.alert_type or "overspend",
                }
            )
        for pr in merged_gs.get("pct_rules") or []:
            if not isinstance(pr, (list, tuple)) or len(pr) < 2:
                continue
            cat, warn = pr[0], pr[1]
            crit = pr[2] if len(pr) >= 3 else 0.0
            w.writerow(
                {
                    "row_type": _ROW_PCT,
                    "v1": str(cat).strip().lower(),
                    "v2": str(warn),
                    "v3": str(crit),
                    "v4": "",
                }
            )
        for sk in _SETTING_KEYS_IN_ORDER:
            if sk not in merged_gs:
                continue
            val = merged_gs[sk]
            w.writerow({"row_type": _ROW_SETTING, "v1": sk, "v2": val, "v3": "", "v4": ""})

    return merged_gs


def load_budget_rules(path: str) -> List[BudgetRule]:
    """Load budget rules from unified budgets.csv (or legacy cap-only CSV)."""
    rules, _ = load_budgets_bundle(path)
    return rules


def save_budget_rules(rules: List[BudgetRule], path: str) -> None:
    """Persist budget rules; keeps other settings in the same file."""
    _, gs = load_budgets_bundle(path)
    save_budgets_bundle(rules, gs, path)


def _validate_date(date_str: str) -> None:
    """Raise ValueError if date is invalid."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")


def validate_date(date_str: str) -> bool:
    """Return True if date is valid YYYY-MM-DD."""
    try:
        _validate_date(date_str)
        return True
    except ValueError:
        return False


def validate_amount(value: str) -> Optional[float]:
    """Parse and validate positive amount. Returns float or None if invalid."""
    try:
        v = float(value)
        if v <= 0:
            return None
        return v
    except ValueError:
        return None


def validate_category(category: str) -> bool:
    """Return True if category is valid (in default list or non-empty)."""
    c = (category or "").strip().lower()
    return c in DEFAULT_CATEGORIES or (len(c) > 0 and c.isalnum())
