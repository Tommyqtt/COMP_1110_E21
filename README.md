# Personal Budget and Spending Assistant

COMP1110 E21 - Topic A: Personal Budget and Spending Assistant, with MockWealth portfolio simulation.

Pure Python, text-based CLI and Tkinter GUI. No external dependencies.

## Requirements

- Python 3.8+

## Joining this repository (group members)

1. **Get access**  
   Ask the repository owner to add you as a collaborator: on GitHub open the repo → **Settings** → **Collaborators** (or **Manage access**) → **Add people**, and send the invite to your GitHub account. Accept the invitation from the email or from [https://github.com/notifications](https://github.com/notifications).

2. **Clone the project** (after you can see the repo on GitHub), using either HTTPS or SSH:

   ```bash
   # HTTPS (works everywhere; GitHub will prompt for login or a personal access token)
   git clone https://github.com/Tommyqtt/COMP_1110_E21.git
   cd COMP_1110_E21
   ```

   ```bash
   # SSH (if you have SSH keys added to GitHub)
   git clone git@github.com:Tommyqtt/COMP_1110_E21.git
   cd COMP_1110_E21
   ```

3. **Optional: set your name and email** for commits (use your real name or what your course expects):

   ```bash
   git config user.name "Your Name"
   git config user.email "your.email@example.com"
   ```

4. **Stay in sync** before you push: `git pull` (or `git pull --rebase`) on your branch so you merge others’ latest changes.

If the project moves to another host or fork, replace the clone URL with the one shown on that service’s **Code** button.

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

Legacy **cap-only** CSV (`category,period,threshold,alert_type`) is still read on load; the app may merge a one-time `gui_settings.json` if present.

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
