# Personal Budget and Spending Assistant

COMP1110 E21 - Topic A: Personal Budget and Spending Assistant, with MockWealth portfolio simulation.

Pure Python, text-based CLI and Tkinter GUI. No external dependencies.

## How to Run

**CLI (text-based):**
```bash
python3 main.py
```

**GUI (Tkinter):**
```bash
python3 main.py --gui
```
or
```bash
python3 main.py -g
```

Run from the **project root** (the folder that contains `main.py`) so **`transactions.csv`** and **`assets.csv`** resolve as expected. **`budgets.csv`** is stored next to `data.py` in the repo; CLI and GUI both use that path so they stay in sync.

For system design and alert rules, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Key Features
* **Predictive Analytics:** Implemented a financial forecasting engine in `stats.py` that calculates your "Burn Rate" to predict total month-end spending.
* **Subscription Creep Detection:** (Case Study 3) Automated detection of month-over-month increases in recurring costs.
* **Dynamic Budget Rules:** Support for daily, weekly, and monthly caps with real-time overspend alerts.

### Summary Preview
When you run the summary, the assistant provides:
```text
==============================
      FINANCIAL SUMMARY      
==============================
Total Outgoing:  HK$ 1,250.00
Daily Burn Rate: HK$ 41.67
Month Forecast:  HK$ 1,291.77
------------------------------
## File Formats

### transactions.csv
```
date,amount,category,description
2026-03-22,-50,food,Lunch
2026-03-22,-8,transport,MTR
```
- `date`: YYYY-MM-DD
- `amount`: negative for expenses
- `category`: food, transport, subscriptions, shopping, other (or custom)
- `description`: optional text

### budgets.csv

Unified file: **budget caps**, **category % rules**, and **GUI alert thresholds** (`row_type` is `cap`, `pct`, or `setting`).

```
row_type,v1,v2,v3,v4
cap,food,daily,50,overspend
pct,food,25,60,
setting,consecutive_overspend_days,3,,
setting,subscription_creep_threshold_pct,20,,
setting,uncategorized_min_transactions,1,,
```

- **`cap`**: `v1` category, `v2` period (`daily` / `weekly` / `monthly`), `v3` HKD threshold, `v4` alert type (e.g. `overspend`).
- **`pct`**: `v1` category, `v2` warning % of total spending, `v3` optional critical %, `v4` blank.
- **`setting`**: `v1` key (`consecutive_overspend_days`, `subscription_creep_threshold_pct`, `uncategorized_min_transactions`), `v2` value.

Legacy **cap-only** CSV (`category,period,threshold,alert_type`) is still read on load. If a legacy **`gui_settings.json`** sits beside `budgets.csv`, it is merged once when migrating older setups.

**CLI vs GUI:** the text menu keeps **percentage-of-total** rules in memory for the session (option **8**). The **GUI Settings** tab reads and writes those rules (and all alert thresholds) in **`budgets.csv`**.

### assets.csv (for MockWealth)
```
asset_id,asset_class,risk_level,mu_monthly,sigma_monthly,fee_rate,notes
CASH,cash,1,0.001,0.001,0,Low risk
```

## CLI menu (`python3 main.py`)

| Key | Action |
|-----|--------|
| **1** | Add transaction |
| **2** | View all transactions |
| **3** | View by date |
| **4** | View by category |
| **d** | Delete a transaction |
| **m** | Edit a transaction |
| **5** | Summaries |
| **6** | Alerts |
| **7** | Configure budget rule (cap) |
| **8** | Configure % threshold alert (session only; see budgets note above) |
| **c** | Manage categories (add/view custom categories) |
| **9** | Load data from disk |
| **s** | Save data |
| **e** | Export report to file |
| **p** | Portfolio (MockWealth), if available |
| **q** | Quit |

## Tests

From the project root:

```bash
python3 -m unittest discover -s tests -v
```

## Test Data

Sample files in `tests/test_data/`:

- `case1_normal.csv` - typical 30-day spending
- `case2_zero.csv` - empty (edge case)
- `case3_uncategorized.csv` - all "other" category
- `case4_heavy_food.csv` - high food spending (triggers daily cap alerts)

To generate new test data:
```bash
python tests/test_generator.py
```

## UI Design

A design system (colors, typography, spacing) is applied across all tabs. See [UI_DESIGN.md](UI_DESIGN.md) for the token reference and coherence verification.

## Project Structure

```
├── main.py            # CLI entrypoint; --gui / -g for Tkinter UI
├── ui.py              # Tkinter GUI (Summary, Add, Transactions, Portfolio, Settings)
├── data.py            # Transaction, BudgetRule, CSV I/O, unified budgets bundle
├── gui_settings.py    # Normalize alert settings dict (used with budgets.csv)
├── stats.py           # Summary statistics & Predictive Analytics logic
├── alerts.py          # Rule-based alerts
├── portfolio.py       # MockWealth simulation
├── assets.csv         # Mock asset universe
├── transactions.csv   # Bundled sample spending (cwd-relative; safe to edit or replace)
├── budgets.csv        # Caps + % rules + settings (next to data.py)
├── ARCHITECTURE.md    # Design notes
├── UI_DESIGN.md       # GUI design tokens
├── tests/
│   ├── test_core_logic.py
│   ├── test_alert_messages.py
│   ├── test_generator.py
│   ├── test_predictive.py
│   └── test_data/
└── README.md
```

## Future Roadmap
Data Visualization: Integration of Matplotlib to turn the `stats.py` forecasts into visual trend lines.
Automated Categorization: Using basic keyword matching to automatically assign categories like "food" or "transport" to new transactions.
Exporting Reports: Capability to export the Financial Summary as a PDF or Excel file for external record-keeping.

## License

Educational use for COMP1110.
