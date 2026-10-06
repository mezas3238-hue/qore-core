# VT31 NAS100 — Final Pre-Holdout Metric Conventions 001

**Status:** FROZEN METRIC CONVENTIONS — PRE-HOLDOUT  
**Scope:** final VT31 pure-edge candidate only

These conventions are frozen before opening Fresh Holdout. They may not be
changed after seeing Fresh Holdout results.

## 1. Return basis

All trader certification economics remain in R.

No lot size, money PnL, equity sizing, leverage, compounding or portfolio weight
may enter these metrics.

For each executed trade:

`stressed_trade_r = raw_terminal_r - friction_r_per_trade`

Baseline friction remains the pre-existing:

`0.05R per executed trade`.

## 2. Eligible daily observation universe

Sharpe and Sortino use one observation per **eligible NY trading session** in
the immutable evidence.

A session is eligible only when the same existing VT31 admission-calendar
integrity condition is satisfied:

- exactly 60 M1 bars in 09:00–10:00 America/New_York; and
- exactly 60 M1 bars in 10:00–11:00 America/New_York.

This is the existing `_admitted_day` completeness definition. No calendar date
lookup is used as trading authority.

For each eligible session:

`daily_r = sum(stressed_trade_r for final-candidate trades on that NY date)`

An eligible session with no admitted final-candidate trade contributes exactly:

`0R`.

No-trade sessions may not be dropped. This prevents opportunity-frequency
selection from inflating risk-adjusted metrics.

## 3. Sharpe convention

Source series:

- eligible-session daily R;
- baseline 0.05R per-trade friction already applied;
- no-trade eligible sessions = 0R.

Risk-free assumption:

`risk_free_r_per_day = 0R`.

Dispersion:

- arithmetic mean daily R;
- sample standard deviation with denominator `N-1`, matching QORE's
  `research_periodic_risk_statistics` convention.

Daily Sharpe:

`mean(daily_r) / sample_stddev(daily_r)`.

Final reported Sharpe:

`annualized_sharpe = daily_sharpe * sqrt(252)`.

Certification gate:

`annualized_sharpe >= 1.50`.

Preferred direction:

approximately `>=2.00`.

If fewer than two eligible sessions exist or variance is zero, Sharpe is
undefined and does not pass by default.

## 4. Sortino convention

Source series is the same eligible-session daily R series used for Sharpe.

Minimum acceptable return:

`MAR = 0R/day`.

For every eligible session:

`downside_i = min(0, daily_r_i - MAR)`.

Downside deviation:

`sqrt(sum(downside_i^2) / N)`.

The denominator is all eligible sessions, matching QORE's
`research_periodic_sortino` convention.

Daily Sortino:

`(mean(daily_r) - MAR) / downside_deviation`.

Final reported Sortino:

`annualized_sortino = daily_sortino * sqrt(252)`.

Certification gate:

`annualized_sortino >= 2.00`.

If downside deviation is zero or the sample is insufficient, the ratio is
reported as undefined rather than silently promoted.

## 5. Payoff convention

Payoff is trade-based after baseline friction.

Let:

- winners = stressed trade R > 0;
- losses = stressed trade R < 0;
- flats = stressed trade R == 0.

Then:

`payoff = mean(winner_r) / abs(mean(loser_r))`.

Flats are excluded from the numerator and denominator averages.

Certification gate:

`payoff >= 1.20`.

Preferred direction:

approximately `>=1.50`.

## 6. Combined PF and expectancy

Before combining folds, assert that final-candidate `signal_at` identities do
not overlap across R5, R6, R8 and recent consumed.

Combined PF:

`sum(all positive stressed trade R) / abs(sum(all negative stressed trade R))`.

Combined expectancy:

`sum(all stressed trade R) / total final-candidate trade count`.

Certification gates:

- combined PF >=1.70;
- expectancy >0R/trade;
- operational target approximately >=+0.15R/trade.

Per-fold / era PF >=1.50 remains a separate robustness requirement.

## 7. Cost and slippage stress convention

Baseline:

- total all-in replay friction = 0.05R per executed trade.

Primary degraded-execution certification stress:

- total all-in friction = 0.10R per executed trade;
- equivalent to 2x the frozen baseline friction;
- degraded PF must remain >1.0.

Additional severe diagnostics, not a replacement for the sovereign gate:

- 0.15R per trade total friction;
- 0.20R per trade total friction.

The stress is intentionally applied adversely to every executed trade. It is a
pure-R all-in execution-cost/slippage proxy and does not use position size.

No stress tier may be selected after seeing Fresh Holdout.

## 8. Reporting scope

The final pre-holdout pack must report:

- each fold separately;
- combined R5+R6+R8+recent;
- eligible-session count;
- no-trade eligible-session count;
- annualized Sharpe;
- annualized Sortino;
- payoff;
- PF / expectancy;
- observed DD;
- losing streak;
- Monte Carlo;
- PF at 0.10R, 0.15R and 0.20R per-trade friction.

## 9. Governance

These formulas are now frozen before Fresh Holdout.

Fresh Holdout remains sealed.

Changing any of these conventions after observing Fresh Holdout would require
discarding that holdout as fresh evidence.

No sizing, leverage, compounding, portfolio weighting or capital rescue is
authorized by these metrics.
