# Personal Budget and Spending Assistant

COMP1110 E21 — Topic A: budget helper with optional MockWealth portfolio simulation.

Pure Python (stdlib only): CLI and Tkinter GUI.

## How to run

```bash
python3 main.py          # CLI
python3 main.py --gui    # or -g
```

Run from the repo root (same folder as `main.py`) so CSV paths resolve. **`budgets.csv`** lives next to `data.py` in the repo; CLI and GUI share that path. Design and alert behavior: [ARCHITECTURE.md](ARCHITECTURE.md).

## Key features

- **Spending summaries:** totals, category breakdown, rolling windows (`format_summary` in `stats.py`).
- **Predictive helpers:** burn-rate / month forecast utilities in `stats.py` (used by alerts and tests).
- **Subscription creep:** month-over-month recurring-cost checks (Case Study 3).
- **Budget rules:** daily / weekly / monthly caps, % of spend thresholds, and overspend alerts (`budgets.csv` + `alerts.py`).

## File formats

### transactions.csv

```
date,amount,category,description
2026-03-22,-50,food,Lunch
2026-03-22,-8,transport,MTR
```

- `date`: YYYY-MM-DD  
- `amount`: negative for expenses  
- `category`: defaults include food, transport, subscriptions, shopping, other (custom allowed)  
- `description`: optional  

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
| d | Delete |
| m | Edit |
| 5 | Summaries |
| 6 | Alerts |
| 7 | Configure budget cap |
| 8 | Configure % alert (session; see budgets note above) |
| c | Manage categories (add/view custom categories) |
| 9 | Reload from disk |
| s | Save |
| e | Export report |
| p | Portfolio (if available) |
| q | Quit |

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
├── main.py            # CLI; --gui / -g for Tkinter
├── ui.py              # Tkinter GUI
├── data.py            # Models, CSV I/O, unified budgets bundle
├── gui_settings.py    # Alert settings dict (with budgets.csv)
├── stats.py           # Summaries and predictive helpers
├── alerts.py          # Rule-based alerts
├── portfolio.py       # MockWealth simulation
├── assets.csv
├── transactions.csv
├── budgets.csv
├── ARCHITECTURE.md
├── UI_DESIGN.md
├── tests/
│   ├── test_core_logic.py
│   ├── test_alert_messages.py
│   ├── test_edge_generator.py
│   ├── test_generator.py
│   ├── test_predictive.py
│   └── test_data/
└── README.md
```

## Future roadmap

- Charts for trend / forecast views (e.g. Matplotlib).
- Smarter auto-category from keywords.
- Richer export (PDF / spreadsheet) from summary output.

## License

Educational use for COMP1110.
