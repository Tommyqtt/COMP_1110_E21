# Case Studies

This document describes the 4 case studies used to evaluate the Personal Budget and Spending Assistant. Each case study has its own transaction file and budget rules file in `tests/test_data/case_studies/`.

Each transaction file now includes a `payment_method` column reflecting how the bill was paid. The supported payment methods used across the case studies are:

| Payment Method | Typical Use |
|---|---|
| Octopus | MTR, buses, minibuses, canteens, groceries, convenience stores |
| Credit Card | Restaurants (higher spend), Airport Express, digital subscriptions, big-ticket shopping |
| Alipay HK | Taxis, dim sum / brunch restaurants |
| WeChat Pay | Bubble tea shops, takeaway, small F&B |
| PayPal | International app subscriptions (e.g. Duolingo) |
| Cash | Untracked / uncategorized purchases |

---

## Case Study 1 — Daily Food Cap (`case1_food_cap_*`)

**Scenario:** A university student tries to keep food spending under HK$50 per day across a two-week period. They commute daily by MTR and want to know which days they exceeded the food cap.

**Goal:** Test the daily category cap alert and the consecutive overspend streak alert for the `food` category.

**Sample budget rules:**
- food: daily cap HK$50
- transport: monthly cap HK$300

**Payment methods in this case study:**
- Most food: Octopus (canteen, dai pai dong, cha chaan teng, groceries)
- Bubble tea / takeaway / snacks: WeChat Pay
- Dim sum brunch: Alipay HK
- Pricier restaurant meals (HK$60+): Credit Card
- All MTR / bus / minibus: Octopus
- Taxi: Alipay HK

**Expected outputs:**
- OVERSPEND alerts on: 2026-03-03 (HK$55), 2026-03-04 (HK$62), 2026-03-07 (HK$70), 2026-03-09 (HK$52), 2026-03-12 (HK$68)
- STREAK alert: food exceeded daily cap on multiple consecutive days (Mar 3–4, Mar 7)
- No transport alert (monthly total ≈ HK$185 < HK$300)

**Strengths demonstrated:** Clear overspend warnings; streak detection helps identify habitual patterns. Payment method breakdown shows most overspends happen at sit-down restaurants paid by Credit Card or Alipay HK.

**Limitations:** System cannot distinguish between one expensive meal vs. multiple smaller ones on the same day; manual entry means a forgotten transaction can make a day appear under budget.


---

## Case Study 2 — Monthly Transport Tracking (`case2_transport_tracking_*`)

**Scenario:** A student commuting from Tuen Mun to campus uses the MTR twice daily (5 days/week). They want to track whether their monthly transport spend stays under HK$300. One trip to the airport inflates costs in one week.

**Goal:** Test monthly category cap alert and the weekly/monthly breakdown in summaries.

**Sample budget rules:**
- transport: monthly cap HK$300
- food: monthly cap HK$600

**Payment methods in this case study:**
- All MTR trips: Octopus (as expected for daily commuting)
- Airport Express: Credit Card (one-off purchase, commonly paid by card)
- Canteen lunches: Octopus

**Expected outputs:**
- Monthly transport total ≈ HK$373 → OVERSPEND alert (exceeds HK$300)
- Monthly food total ≈ HK$155 → no alert
- Summary shows clear weekly breakdown of transport spend
- Transport > food in % share → potential percentage threshold alert if configured (e.g. transport > 30%)

**Strengths demonstrated:** Monthly period tracking catches cumulative transport creep; weekly breakdown helps pinpoint the expensive week (the airport trip week). Payment method data clearly separates routine Octopus commuting from the one-off Credit Card Airport Express purchase.

**Limitations:** The system treats every transaction equally — it cannot flag that the airport trip was a one-off vs. routine overspending. No suggestion to use an Octopus monthly pass.

---

## Case Study 3 — Subscription Creep Detection (`case3_subscription_creep_*`)

**Scenario:** A student has multiple subscriptions (Netflix, Spotify, iCloud, ChatGPT Plus). Over 3 months, they add Adobe Creative Cloud in February, then YouTube Premium Family Plan and Duolingo Super in March. By March their monthly subscription cost has risen substantially.

**Goal:** Test the subscription creep alert (month-over-month increase > 20%) and the monthly summary breakdown.

**Sample budget rules:**
- subscriptions: monthly cap HK$300

**Payment methods in this case study:**
- Netflix, Spotify, iCloud, Adobe, YouTube Premium, ChatGPT Plus: Credit Card (all are recurring international charges)
- Duolingo Super: PayPal (international app, does not support local HK payment options)
- Bulk food / transport entries: Credit Card / Octopus respectively

**Expected outputs:**
- January subscriptions: HK$258
- February subscriptions: HK$326 → OVERSPEND alert (> HK$300)
- March subscriptions: HK$459 → OVERSPEND alert
- SUBSCRIPTION CREEP alert: March vs February is a ~41% increase
- Summary shows subscriptions growing as top-3 category by March

**Strengths demonstrated:** The subscription creep detector catches gradual spending growth that is easy to miss month-by-month. The monthly breakdown makes the trend visible. All subscriptions being Credit Card / PayPal makes this category easy to audit — no Octopus or cash involved.

**Limitations:** The system only compares the two most recent months; it cannot project future costs or identify which specific subscription added the most. No automated detection from bank statements.

---

## Case Study 4 — Habitual Overspending & Uncategorized Transactions (`case4_habitual_overspend_*`)

**Scenario:** A student has an inconsistent spending pattern. Food often exceeds the HK$50 daily cap, shopping spikes in certain weeks, and two transactions are logged as "other" (uncategorized) because the student forgot to categorize them.

**Goal:** Test consecutive overspend streak alert for food, weekly cap for shopping, percentage threshold alert, and the uncategorized transaction warning.

**Sample budget rules:**
- food: daily cap HK$50
- shopping: weekly cap HK$200
- transport: monthly cap HK$200

**Suggested percentage alert to configure (via menu option 8):**
- shopping > 25% of total spending

**Payment methods in this case study:**
- MTR: Octopus
- Taxi: Alipay HK
- 7-Eleven / convenience store / stationery / books: Octopus
- Uniqlo / shoes / electronics (large purchases): Credit Card
- Sit-down restaurant meals: Credit Card or Alipay HK
- Brunch: Alipay HK
- Untracked "other" purchases: Cash (reflects the unrecorded / mystery nature of these entries)

**Expected outputs:**
- STREAK alert: food exceeded daily cap on 3+ consecutive days (Apr 1–3, Apr 9–10, etc.)
- OVERSPEND alert: shopping weekly cap exceeded (Apr 10 week: HK$200+ in electronics alone)
- UNCATEGORIZED alert: 2 transactions are in the 'other' category (Apr 13, Apr 14)
- If % alert configured: shopping share is very high in this data set

**Strengths demonstrated:** Multiple alert types fire simultaneously; the uncategorized warning prompts the user to review and fix their records; the streak alert makes habitual overspend visible. The Cash payment method on the two "other" entries reinforces why they are untracked — cash purchases are the hardest to account for.

**Limitations:** "Other" transactions cannot be recategorized in-app currently (a future improvement would be an edit/re-categorize option). The system has no way to know that the HK$200 electronics purchase was a one-off gift rather than habitual shopping.

---

## How to Run a Case Study

### Manual Loading

> **Note:** Transaction files now include a `payment_method` column as the 5th field:
> ```
> date,amount,category,description,payment_method
> 2026-03-01,-45,food,Lunch at cha chaan teng,Octopus
> 2026-03-01,-12,transport,MTR Admiralty to HKU,Octopus
> ```

```bash
# Load the case study data files instead of the default CSV files
# Example for Case Study 1:
python3 main.py
# From the menu, choose option 9 (Load data)
# Then manually point to the case study files, or edit the
# TRANSACTIONS_FILE / BUDGETS_FILE constants in main.py to point to the case study paths.
```

### Synchronous Command-Line Execution

For direct loading of case study files:

```bash
# CLI mode with specific files
python3 main.py --cli --transactions tests/test_data/case_studies/case1_food_cap_transactions.csv --budgets tests/test_data/case_studies/case1_food_cap_budgets.csv

# GUI mode with specific files
python3 main.py --gui --transactions tests/test_data/case_studies/case1_food_cap_transactions.csv --budgets tests/test_data/case_studies/case1_food_cap_budgets.csv
```

Alternatively, to run a quick case study from the command line using the test generator:

```bash
python3 tests/test_generator.py
```
