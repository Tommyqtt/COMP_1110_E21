Case Study: Predictive Financial Analytics

Overview

This document outlines the implementation and mathematical logic behind the predictive analytics engine found in stats.py.

1. Monthly Burn Rate & Forecasting

The goal was to provide users with a "look-ahead" feature. Instead of just seeing what they spent, the app predicts where they will finish the month.

Logic:

Daily Burn Rate: Calculated as Total Spending / Days Passed.

Forecast: Burn Rate * Total Days in Month.

Edge Case Handling: Implemented max(1, today.day) to prevent division by zero errors on the first day of the month.

2. Subscription Creep Detection (Case Study 3)

One of the core requirements was identifying subtle increases in recurring costs.

Detection Algorithm:

Identifies transactions categorized as Subscriptions.

Compares the current_month_total against the last_month_total.

Threshold Trigger: A 20% increase (default) triggers a high-visibility warning in the format_summary output.

3. Verification & Testing

To ensure the reliability of the financial projections, a unit testing suite was developed in tests/test_predictive.py. This suite validates:

Calculations with empty datasets.

Calculation accuracy for standard spending patterns.

Date parsing robustness.

Developed by Stephanie Kim/3036603781 as part of the COMP1110 Final Project.
