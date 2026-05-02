# Personal Budget and Spending Assistant

COMP1110 E21 — Topic A: budget helper with optional MockWealth portfolio simulation.

Core app uses **Python stdlib only** (CLI and Tkinter GUI). **PDF export** (Summary tab **Export PDF**) is optional and requires the third-party package **`fpdf2`**:

```bash
python3 -m pip install fpdf2
# or: python3 -m pip install -r requirements-pdf.txt
```

## How to run

```bash
python3 main.py                              # Tkinter GUI (default)
python3 main.py --cli                        # text menu (CLI)
python3 main.py --transactions path.csv --budgets path.csv   # optional paths (GUI or CLI)
```

Run from the repo root (same folder as `main.py`) so CSV paths resolve. **`budgets.csv`** lives next to `data.py` in the repo; CLI and GUI share that path. Design and alert behavior: [ARCHITECTURE.md](ARCHITECTURE.md).

## Key features

- **Spending summaries:** totals, category breakdown, rolling windows (`format_summary` in `stats.py`).
- **Predictive helpers:** burn-rate / month forecast utilities in `stats.py` (used by alerts and tests).
- **Subscription creep:** month-over-month recurring-cost checks (Case Study 3).
- **Budget rules:** daily / weekly / monthly caps, % of spend thresholds, and overspend alerts (`budgets.csv` + `alerts.py`).
- **File upload/download:** GUI supports uploading custom transaction CSV files and downloading summary reports as PDF (requires `fpdf2`; see top of this file).

## Case studies

[**CASE_STUDIES.md**](CASE_STUDIES.md) walks through four realistic demo scenarios used to showcase behaviour (daily food caps, commute transport tracking, subscription creep, and habitual overspending with uncategorized items). For each scenario it explains goals, sample budget rules, expected summary/alert outputs, strengths, and limitations. Matching practice data lives under `tests/test_data/case_studies/` (`case*_transactions.csv` and `case*_budgets.csv`). Load any pair via CLI/GUI flags, for example:

```bash
python3 main.py --gui --transactions tests/test_data/case_studies/case1_food_cap_transactions.csv --budgets tests/test_data/case_studies/case1_food_cap_budgets.csv
```

## File formats

### transactions.csv

```
date,amount,category,description,payment_method
2026-03-22,-50,food,Lunch,octopus
2026-03-22,-8,transport,MTR,octopus
```

- `date`: YYYY-MM-DD  
- `amount`: negative for expenses  
- `category`: defaults include food, transport, subscriptions, shopping, other (custom allowed)  
- `description`: optional  
- `payment_method`: optional column (defaults to `cash` if omitted); recognized methods also listed in `payment_methods.txt` when customized  

Custom **categories** persist in `categories.txt`; custom **payment methods** persist in `payment_methods.txt` (created when you add methods or load transactions that introduce new ones).

### budgets.csv

Unified layout: caps, optional category-% rows, and alert settings.

```
row_type,v1,v2,v3,v4
cap,food,daily,50,overspend
pct,transport,30,50,
setting,consecutive_overspend_days,3,,
setting,subscription_creep_threshold_pct,20,,
setting,uncategorized_min_transactions,1,,
```

- `cap`: category, period (`daily` / `weekly` / `monthly`), HKD threshold, alert type (e.g. `overspend`).  
- `pct`: category, warning % of total spend, optional critical %, `v4` empty.  
- `setting`: key in `v1`, value in `v2` (supported keys as in the example).  

Legacy `category,period,threshold,alert_type` files still load. If only that layout exists and `gui_settings.json` is present beside `budgets.csv`, settings are merged once on load.

CLI menu option 8 keeps % rules in memory for the session; the GUI Settings tab writes caps and thresholds through the unified `budgets.csv` flow.

### assets.csv (MockWealth)

```
asset_id,asset_class,risk_level,mu_monthly,sigma_monthly,fee_rate,notes
CASH,cash,1,0.001,0.001,0,Low risk
```

## CLI menu

| Key | Action |
|-----|--------|
| 1 | Add transaction |
| 2 | View all |
| 3 | View by date |
| 4 | View by category |
| pm | View by payment method |
| d | Delete |
| m | Edit |
| 5 | Summaries |
| 6 | Alerts |
| f | Forecasts (projected end-of-period) |
| 7 | Configure budget cap |
| 8 | Configure % alert (session; see budgets note above) |
| r | Recommend budget caps |
| c | Manage categories (add/view custom categories) |
| y | Manage payment methods |
| 9 | Reload from disk |
| s | Save |
| e | Export report (plain text) |
| p | Portfolio (if available) |
| q | Quit |

## GUI Features

The graphical user interface provides an intuitive way to manage your budget and transactions. Tabs include **Summary**, **Add**, **Transactions**, **Portfolio** (MockWealth), **Settings** (caps, % rules, alert thresholds), and **Categories**.

- **Upload Transactions:** Load custom CSV files using **Load CSV…** (same columns as `transactions.csv`, including optional `payment_method`).
- **Export PDF:** Export the Summary view as a PDF (requires `fpdf2`; see top of this file).
- **Interactive Summary:** Spending KPIs, alerts, category/payment breakdowns, momentum, forecasts, and recommended caps.
- **Transaction Management:** Filterable list, add/edit/delete with payment method support.
- **Budget Configuration:** Caps, category share (%), and behaviour thresholds saved to `budgets.csv`.
- **Categories & payment methods:** Manage lists used in forms (backed by `categories.txt` / `payment_methods.txt`).

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Test data

Under `tests/test_data/`: `case1_normal.csv` … `case4_heavy_food.csv`, plus `edge_cases/*.csv` when generated.

```bash
python3 tests/test_generator.py
```

## UI

Tokens and layout notes: [UI_DESIGN.md](UI_DESIGN.md).

## Layout

```
├── main.py            # Entry: default GUI; --cli for text menu
├── ui.py              # Tkinter GUI
├── export_pdf.py      # PDF summary export (optional fpdf2)
├── data.py            # Models, CSV I/O, unified budgets bundle
├── gui_settings.py    # Alert settings dict (with budgets.csv)
├── stats.py           # Summaries and predictive helpers
├── alerts.py          # Rule-based alerts
├── portfolio.py       # MockWealth simulation
├── requirements-pdf.txt   # optional: pip install -r for PDF export
├── assets.csv
├── transactions.csv
├── budgets.csv
├── ARCHITECTURE.md
├── CASE_STUDIES.md
├── UI_DESIGN.md
├── tests/
│   ├── test_core_logic.py
│   ├── test_alert_messages.py
│   ├── test_generator.py
│   ├── test_predictive.py
│   ├── test_categories.py
│   └── test_data/
└── README.md
```

## Future roadmap

- Charts for trend / forecast views (e.g. Matplotlib).
- Smarter auto-category from keywords.
- Optional spreadsheet export from summary output.

