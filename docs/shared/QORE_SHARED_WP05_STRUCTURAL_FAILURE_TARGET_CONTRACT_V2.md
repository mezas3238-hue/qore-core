# QORE Shared WP-05 — Structural Failure Target Contract V2

**Status:** ACTIVE FOR CONSUMED DEVELOPMENT — activated after preregistered audit  
**Primary PR:** #635  
**Work package:** #643 — WP-05 Temporal Hierarchical Brain  
**Activation evidence:** GitHub Actions run `36259738096`, Git SHA `d7b6830d957a6dee12959236b6cef42d3b162f96`  
**Audit result:** `WP05_TARGET_CONTRACT_DIRECTIONALLY_INCONSISTENT`  
**V1–V4 remain immutable falsification history of the prior M15-oriented proxy.**

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

## 10. Activation condition — SATISFIED 26-SEP-2026

The preregistered activation condition has been satisfied by consumed-evidence audit run
`36259738096` at Git SHA `d7b6830d957a6dee12959236b6cef42d3b162f96`.

The audit did not change labels or fit a model. It measured the pre-existing target against the
higher-timeframe structural-failure question and found material directional inconsistency:

```text
R8 directional inversion: 5452 bps
R6 directional inversion: 5432 bps
R5 directional inversion: 5419 bps
material inversion threshold: 500 bps
```

Therefore Target V2 is now the active WP-05 target for new consumed-development experiments:

```text
current terminal direction = opposite M15                  -> historical V1–V4 only
Target V2 terminal direction = opposite higher-timeframe anchor -> active new experiments
```

No prior artifact is rewritten or reinterpreted as Target V2 evidence.

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
- Target V2 activation does not itself pass WP-05; a new corrected-target model must pass R6 and R5 before any fresh holdout may open.


## 13. Activation evidence

The consumed target-semantics audit activated this contract without opening
fresh evidence.

Authoritative audit:
- Git SHA: `d7b6830d957a6dee12959236b6cef42d3b162f96`
- GitHub Actions run: `36259738096`
- status: `WP05_TARGET_CONTRACT_DIRECTIONALLY_INCONSISTENT`
- protocol: PASS
- current target directionally inverted on the majority of identifiable baseline
  episodes in R8, R6 and R5.

Therefore all new WP-05 experiments must use
`HIGHER_TIMEFRAME_STRUCTURAL_FAILURE_V2`. The old M15-oriented target is
forbidden for new claims about higher-timeframe structural failure.

Fresh holdout remains CLOSED until a V2-target model passes the unchanged
consumed-development gate on both R6 and R5.
