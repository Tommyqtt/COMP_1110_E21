# System design, architecture, and core logic

This document describes how the **Personal Budget and Spending Assistant** (COMP1110 E21) is structured, how data flows through it, and how the main behavioral rules work. It complements `README.md` (usage and file formats).

---

## 1. Purpose and technology stack

The application helps users **record expenses**, **see summaries** (totals, categories, rolling windows), and **surface rule-based alerts** (budget caps, category share of spending, streaks, subscription creep, uncategorized items). It also includes a separate **MockWealth** module for an educational **portfolio Monte Carlo simulation** (not real financial advice).

| Aspect | Choice |
|--------|--------|
| Language | Python 3.8+ |
| External dependencies | **None** (stdlib only: `csv`, `datetime`, `tkinter`, `json`, etc.) |
| Interfaces | Text **CLI** (`main.py`) and **Tkinter GUI** (`ui.py`) |

The **same core modules** (`data`, `stats`, `alerts`, `portfolio`) are shared; only the presentation layer differs.

---

## 2. Layered architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Presentation                                                            │
│  • main.py          CLI menu, interactive forms, optional --gui handoff   │
│  • ui.py            Notebook tabs, forms, scrollable Summary, Settings  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ calls
┌───────────────────────────────────▼─────────────────────────────────────┐
│  Domain / rules                                                          │
│  • alerts.py        run_all_alerts, per-check functions, message prefixes │
│  • stats.py         Aggregations for summaries and alert inputs           │
│  • portfolio.py     Risk→allocation map, Monte Carlo on assets.csv        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ uses
┌───────────────────────────────────▼─────────────────────────────────────┐
│  Data                                                                    │
│  • data.py          Transaction, BudgetRule; unified budgets CSV I/O       │
│  • gui_settings.py  normalize / load helper for alert settings dict     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│  Persistence (CSV; optional legacy gui_settings.json for migration)       │
│  • transactions.csv    • budgets.csv (caps + % rules + settings rows)    │
│  • assets.csv                                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Dependency direction:** UI and CLI depend on `alerts` + `stats` + `data`; `alerts` depends on `stats` and `data` only; `stats` depends on `data`; `portfolio` reads `assets.csv` and does not depend on transactions.

---

## 3. Persistence model

### 3.1 `transactions.csv`

- One row per expense (or positive amount normalized to negative expense in `Transaction.__post_init__`).
- Columns: `date`, `amount`, `category`, `description`.
- `load_transactions` skips malformed rows with a warning; empty/missing file → empty list.

### 3.2 `budgets.csv` (unified)

Caps, category **% of total** rules, and **alert settings** live in one CSV with columns `row_type`, `v1`–`v4`:

| `row_type` | Meaning |
|------------|---------|
| `cap` | Budget cap: `v1` category, `v2` period (`daily` / `weekly` / `monthly`), `v3` threshold HK$, `v4` `alert_type`. |
| `pct` | Share alert: `v1` category, `v2` warning %, `v3` optional critical %, `v4` blank. |
| `setting` | Scalar: `v1` key (`consecutive_overspend_days`, `subscription_creep_threshold_pct`, `uncategorized_min_transactions`), `v2` value. |

Period semantics for caps: **`daily`**, **`weekly`** (ISO week), **`monthly`**; caps drive **overspend** and **streak** (daily only).

**Legacy:** older **cap-only** CSV headers (`category`, `period`, …) still load; optional `gui_settings.json` beside the file is merged once if present.

`gui_settings.py` still **normalizes** the settings dict after load and before save; unknown legacy keys may be stripped.

### 3.3 `assets.csv` (portfolio)

Defines mock assets (returns, volatility, fees) for MockWealth; `portfolio.load_assets` falls back to built-in defaults if the file is missing or empty.

---

## 4. Core data structures

### 4.1 `Transaction` (`data.py`)

- `date`: `YYYY-MM-DD` string (validated on load).
- `amount`: negative for expenses; **positive values are coerced to negative** (`__post_init__`) so “mistyped sign” still counts as spending.

### 4.2 `BudgetRule`

- Links a **category** + **period** + **HK$ threshold** + **alert_type** (e.g. `overspend`).

---

## 5. Statistics module (`stats.py`)

Used by the CLI summary, GUI dashboard, and **all alerts that depend on totals or periods**.

| Function | Behavior |
|----------|----------|
| `total_spending` | Sum of `abs(amount)` for negative amounts only. |
| `by_category` | Per-category spend totals. |
| `by_period` | Buckets by `daily` / `weekly` / `monthly`; **skips invalid dates** and non-expenses. |
| `trend_last_n_days` | From the **latest** transaction date, sums expenses in the last *n* calendar days. |
| `average_daily_spending` | Mean of **daily** bucket totals over days that have at least one expense. |
| `format_summary` | Plain-text block for CLI. |

---

## 6. Alert system (`alerts.py`)

### 6.1 Orchestrator: `run_all_alerts`

Runs checks in a fixed order and returns a **flat list of strings**. Each message starts with a **tag** like `[OVERSPEND]` so the GUI can style banners (`split_alert_message` maps prefix → **kind**). **Longer prefixes are matched first** (e.g. `[BUDGET % CRITICAL]` before `[BUDGET %]`).

Parameters include: `pct_rules` (legacy 2-tuples or 3-tuples), `consecutive_days`, `subscription_creep_threshold_pct`, `uncategorized_min_transactions`.

### 6.2 Alert types (core logic)

1. **Category caps — `check_category_caps`**  
   For each `BudgetRule`, uses **`by_period` only on that category’s transactions**, finds the **latest period key**, compares spend to `threshold`. If over → `[OVERSPEND]` with period label (e.g. date, ISO week, month).

2. **Share of total — `check_percentage_thresholds`**  
   After `normalize_pct_rules_rows` (validates warn/crit, drops bad rows), computes each category’s **% of total spend**. If total spend is 0 → no alerts. **Critical** fires if `crit > warn` and actual % **>** critical; else **warning** if actual % **>** warning (strict inequalities). Legacy `[BUDGET %]` style is preserved for older strings in parsing only.

3. **Streak — `check_consecutive_overspend`**  
   Only **daily** rules. Builds per-day totals for that category. Counts **calendar-consecutive** overspend days: each new day must be **exactly one calendar day after** the previous day in the current run to increment the streak; under-cap days reset; gaps with **no spending** on a category for a calendar day break the run because the next overspend day is not adjacent. Fires if **max streak ≥ configured consecutive days**.

4. **Uncategorized — `check_uncategorized`**  
   Counts transactions with `category == "other"`. If **min count is 0** → never alert. Otherwise alerts when **count ≥ min_count**.

5. **Subscription creep — `check_subscription_creep`**  
   Subscription transactions only, **monthly** totals. Compares the **two most recent calendar months** that appear. If previous month spend is **0** → no alert. If **% increase > threshold** (strict) → `[SUBSCRIPTION CREEP]`.

### 6.3 `normalize_pct_rules_rows`

- Accepts rows with 2 or 3 elements; enforces `0 < warn ≤ 100`, optional `crit`, rejects `crit ≤ warn` when `crit > 0`.

---

## 7. GUI architecture (`ui.py`)

### 7.1 Application state

`run_gui` holds a **`state` dict**:

- `transactions` — list of `Transaction`
- `rules` — list of `BudgetRule` (from `budgets.csv`)
- `gui_settings` — dict from `gui_settings.load_gui_settings()`

**Save** paths: `save_transactions` for transactions; **`save_budgets_bundle`** (or `save_budget_rules` / `save_gui_settings`, which delegate to it) for `budgets.csv`. **Reload** refreshes from disk where needed.

### 7.2 Tabs (Notebook)

| Tab | Responsibility |
|-----|------------------|
| **Summary** | Scrollable canvas: **Alerts** block (banners from `run_all_alerts`), **Spending statistics** (KPI cards), **Spending by category** (bars), **Momentum** (rolling-window KPI cards), **Recent months** (optional). |
| **Add** | Form to append a transaction and save. |
| **Transactions** | Filterable tree, edit selected, refresh. |
| **Portfolio** | MockWealth inputs + Monte Carlo results (scrollable). |
| **Settings** | Scrollable: **budget caps**, **category % rules**, **other thresholds** (streak days, creep %, uncategorized min) → unified **`budgets.csv`**. **Save** writes CSV and reloads. |

### 7.3 UX patterns

- Scrollable areas use a **canvas + scrollbar** + **mouse wheel** bound on the canvas and descendants.
- **Design tokens** in-module: colors, spacing, fonts (`COLORS`, `PAD_*`, etc.).
- Alerts rendered as **typed banners** (`_alert_type_banner`) with accent strip + tint per kind.

---

## 8. CLI architecture (`main.py`)

- **Interactive loop**: loads transactions and budgets once; **`pct_rules` for CLI** is held **in memory** (menu option to configure % rules). The **GUI** reads/writes **`pct_rules` and settings from `budgets.csv`** via `load_budgets_bundle` / `save_budgets_bundle`.
- **Alerts / export** use the **in-memory** `pct_rules` list passed into `run_all_alerts` — so **CLI and GUI can differ** unless CLI is pointed at `gui_settings` for parity.

Entry: `python3 main.py` → menu; `python3 main.py --gui` / `-g` → `ui.run_gui()`.

---

## 9. Portfolio module (`portfolio.py`)

- **`RISK_ALLOCATION`**: maps risk level 1–5 to weights over asset **classes** (cash, bonds, balanced, equity, high_risk).
- **`simulate`**: many Monte Carlo paths; each month applies Gaussian returns per asset class (minus fees), weighted by allocation; adds contributions. Returns **P10, P50, P90**, and **loss probability** vs. contributions.

Independent of budgeting; shares only the project’s “HK$” presentation style in the GUI.

---

## 10. Testing

- **`tests/test_alert_messages.py`**: `split_alert_message` prefix → kind + body.
- **`tests/test_core_logic.py`**: alerts (caps, %, streak calendar logic, creep boundaries), stats edge cases, `gui_settings` normalization (with patched temp path), portfolio smoke, `run_all_alerts` integration.

---

## 11. Extension points

- **New alert type**: add a `check_*` function, call it from `run_all_alerts`, add prefix to `ALERT_PREFIX_KIND` and styling in `ui._alert_type_banner`.
- **New setting**: extend `gui_settings.DEFAULT_SETTINGS` + `_normalize`, Settings tab fields, and pass into `run_all_alerts`.
- **New CSV field**: extend `data` models and loaders with backward-compatible defaults.
- 