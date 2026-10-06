# VT31 NAS100 — Comparator 010 Live-Context Adverse Exit Findings 001

**Status:** FALSIFIED BEFORE ECONOMIC REPLAY  
**Baseline:** `VT31_AB_COMP009_MAX_INTELLIGENCE_COMPOSED_SURVIVOR`  
**Predeclared gate:** `VT31_ARCH2_COMP010_LIVE_CONTEXT_ADVERSE_EXIT_GATE_001.md`  
**Fresh Holdout:** SEALED

## Result

The predeclared live-context adverse-exit hypotheses do not justify an economic
replay.

### Hypothesis A — FVG + current H1 mixed

Across the frozen Comparator-009 consumed population the predeclared state
matches 11 trades.

All 11 are losses, but at the first qualifying fully-closed M1 observation:

- `comp007_base_exit_authorized == true`: 11/11;
- `cognitive_exit_authorized == true`: 11/11.

Therefore Hypothesis A adds **zero new actuation**. It is completely subsumed by
the existing adverse-exit stack.

### Hypothesis B — LONG + current M15 bearish

The predeclared state matches 7 trades.

At the first qualifying observation:

- 5/7 are already authorized by Comparator 009;
- only 2/7 add any possible new authority.

The two non-redundant cases are consumed-development forensic instances only;
their dates are not runtime authority.

A deliberately impossible upper-bound diagnostic was then used only to decide
whether an expensive replay could possibly matter: both residual losses were
replaced by 0R while every other Comparator-009 outcome was left unchanged.

Even under that oracle upper bound:

- stitched DD remains approximately **9.0997R** — FAIL versus <=6R;
- frozen annualized Sharpe reaches only approximately **1.2876** — FAIL versus
  >=1.50.

A real next-M1-open implementation cannot be assumed to outperform that
zero-loss oracle enough to close the full remaining gap.

## Adjudication

Do not promote or replay:

- `COMP010_FVG_H1_MIXED_ADVERSE_EXIT`;
- `COMP010_LONG_M15_BEARISH_ADVERSE_EXIT`;
- their union.

This is a pre-replay falsification, not a failed workflow result. The earlier
GitHub workflow attempt failed at infrastructure/static setup because the
branch-local ultrafast runner had correctly been removed to keep GitHub Trader
Lab independent. No economic evidence was consumed by that failure.

## Consequence

Comparator 009 remains the economic baseline.

The remaining work should focus on the independently identified
replay/runtime maximum-intelligence parity gap and on causal market facts that
can actuate a materially broader portion of unresolved sudden invalidations.

## Governance

- consumed evidence only;
- oracle transformation used only as a feasibility upper bound, never runtime
  authority;
- no new threshold;
- no sizing, leverage, compounding, portfolio or capital weighting;
- Fresh Holdout remains sealed;
- VT31 remains not certified;
- no LIVE, real-capital or production authority.
