# Personal Budget and Spending Assistant

COMP1110 E21 - Topic A: Personal Budget and Spending Assistant, with MockWealth portfolio simulation.

Pure Python, text-based CLI and Tkinter GUI. No external dependencies.

## Requirements

- Python 3.8+

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

Run from the project root directory so `transactions.csv`, `budgets.csv`, and `assets.csv` are found.

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
```
category,period,threshold,alert_type
food,daily,50,overspend
transport,monthly,300,overspend
```
- `period`: daily, weekly, or monthly
- `threshold`: HKD cap

### assets.csv (for MockWealth)
```
asset_id,asset_class,risk_level,mu_monthly,sigma_monthly,fee_rate,notes
CASH,cash,1,0.001,0.001,0,Low risk
```

## Menu Options

1. Add transaction
2. View all transactions
3. View by date
4. View by category
5. Summaries (totals, by category, top 3, trends)
6. Alerts (budget caps, percentage thresholds, uncategorized warnings)
7. Configure budget rule
8. Load data
9. Save data
p. Portfolio (MockWealth simulation)
q. Quit

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
├── main.py         # CLI entrypoint, --gui for Tkinter UI
├── ui.py           # Tkinter GUI (5 tabs)
├── data.py         # Data models, load/save
├── stats.py        # Summary statistics
├── alerts.py       # Rule-based alerts
├── portfolio.py    # MockWealth simulation
├── assets.csv      # Mock asset universe
├── transactions.csv
├── budgets.csv
├── tests/
│   ├── test_generator.py
│   └── test_data/
└── README.md
```

## License

Educational use for COMP1110.
