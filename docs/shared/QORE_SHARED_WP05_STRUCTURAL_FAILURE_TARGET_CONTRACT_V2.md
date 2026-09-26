# QORE Shared WP-05 — Structural Failure Target Contract V2

**Status:** preregistered / pending target-semantics audit  
**Primary PR:** #635  
**Work package:** #643 — WP-05 Temporal Hierarchical Brain  
**Supersedes V1 target only if the consumed target-semantics audit proves
material directional inconsistency.**

## 1. Scientific question

WP-05 is not asking whether M15 itself reverses.

It asks:

> When local adverse pressure opposes the higher-timeframe state, does that
> pressure remain a recoverable pullback or become a genuine terminal
> higher-timeframe structural failure?

The target must therefore be oriented by the higher-timeframe structural state,
not by a local timeframe that may itself be the adverse pressure under study.

## 2. Higher-timeframe anchor

At the source `as_of`, define the higher-timeframe anchor only from causal
source state:

```text
HIGHER_ANCHOR =
sign(mean(H1.direction, H4.direction, D1.direction))
```

No future state, trader identity, symbol identity, setup identity, trade
direction, position, PnL or outcome participates in the anchor.

If the anchor is zero/unidentifiable, the episode is not permitted to fabricate
a structural-failure direction.

## 3. Structural frontier

Using only market state available at the source timestamp:

```text
PRIOR_STRUCTURAL_WINDOW = last 20 closed M1 bars
PRIOR_PEAK  = max(high)
PRIOR_FLOOR = min(low)
```

For a bullish higher anchor, terminal structural failure is a downside breach.
For a bearish higher anchor, terminal structural failure is an upside breach.

## 4. Matured research target

The historical label may use the next 30 closed M1 bars **offline only** after
they mature.

Bullish higher anchor:

```text
terminal_failure =
    future_low < PRIOR_FLOOR
    AND final_30m_close < PRIOR_FLOOR
```

Bearish higher anchor:

```text
terminal_failure =
    future_high > PRIOR_PEAK
    AND final_30m_close > PRIOR_PEAK
```

This future path is a training/evaluation target only. It is forbidden at
runtime.

## 5. Baseline universe

The baseline declaration universe remains unchanged:

```text
local M1/M3/M5/M15 state opposes higher H1/H4/D1 state
```

The baseline still declares every such opposition as structural failure.

WP-05 cognition must reduce false declarations without erasing real terminal
higher-timeframe failures.

## 6. Development gate remains frozen

Changing a semantically incorrect target is not permission to weaken the
scientific standard.

On BOTH consumed R6 and R5 development partitions:

```text
false structural-failure declaration reduction >= 20%
terminal detection preservation >= 95%
```

No fresh holdout may be opened unless the exact corrected-target model passes
both consumed partitions under a frozen model/threshold.

## 7. Historical evidence law

V1–V4 results remain immutable evidence about the original M15-oriented proxy.

They are never rewritten, deleted or retroactively relabeled as V2 results.

If the target audit confirms material inconsistency:

```text
V1..V4 = VALID FALSIFICATION HISTORY OF OLD PROXY
V2 TARGET = NEW PREREGISTERED SCIENTIFIC CONTRACT
```

A corrected-target experiment receives a new identity and new artifacts.

## 8. Anti-leakage law

Target V2 may use matured future market path for offline labels only.

Runtime/candidate projection may use only source-time information.

Forbidden runtime inputs remain:

- future market path;
- terminal target;
- trade outcome;
- PnL;
- trader identity;
- strategy/setup identity;
- symbol identity as a shortcut;
- sizing;
- Risk decisions;
- broker mutation state as a label shortcut.

## 9. Sovereignty

Target V2 creates no actuation authority.

Shared remains unable to:

```text
enter
exit
resize
modify_stop
modify_tp
block_trade
force_trade
allocate_capital
authorize_risk
send_order
```

## 10. Activation condition

This contract is activated only if the GitHub target-semantics audit shows
material directional inconsistency between:

```text
current terminal direction = opposite M15
expected WP05 failure direction = opposite higher-timeframe anchor
```

Until that audit completes, this document is preregistration only.

## 11. Fresh evidence law

No fresh holdout is opened by this preregistration.

After activation, the corrected target must first survive consumed development.
Only then may an exact model fingerprint and independent holdout window be
preregistered before acquisition.

## 12. Governance

- PR #635 remains DRAFT / UNMERGED.
- No LIVE or production authority.
- No real-capital authority.
- No merge authority.
- No knowledge auto-promotion.
- Existing WP-05 gate remains unchanged.
