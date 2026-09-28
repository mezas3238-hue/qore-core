# CIBO CE2I — FULL-SURFACE 20/20 ARCHITECTURE CONTRACT

**PR:** #651  
**Branch:** `agent/cibo-capital-efficiency-sizing-lab-001`  
**Status:** RESEARCH / DRAFT / UNMERGED  
**Owner decision:** certification with a partial CE2I surface is REJECTED.

## 1. Non-negotiable completeness law

CIBO cannot enter a certification population while any canonical CE2I tool is
`ARCHITECTURE_ONLY` or `REJECTED`.

The canonical surface is exactly:

`T01..T20`.

DEMO capability discovery must bind all twenty tool contracts. A tool may return:

- `APPLIED` when causal evidence supports its use;
- `ABSTAIN` when the tool is implemented but no economically valid/certified
  expression exists at that decision;
- `FAIL_CLOSED` when required evidence/infrastructure is missing, stale,
  contaminated or invalid.

A certification population containing an advanced-tool `FAIL_CLOSED` is invalid.
An explicit `ABSTAIN` is not equivalent to missing implementation.

## 2. Advanced engines completed

### T02 — Structural Leverage

Engine: `evaluate_structural_leverage`.

Required evidence:

- verified structural invalidation identity;
- out-of-sample stop evidence;
- minimum OOS sample;
- unchanged Trader stop geometry;
- no worse stop incidence;
- no worse tail loss;
- proven released-risk/protected capacity.

The engine never narrows or manufactures the Trader structural stop.

### T03 — Margin Efficiency

Engine: `evaluate_margin_efficiency`.

It compares only executable, economics-verified expressions with materially
equivalent normalized exposure. An alternative is eligible only if it does not
increase true stop risk or all-in cost and strictly reduces margin.

No equivalent expression -> explicit `ABSTAIN`.

### T04 — Risk Efficiency

Engine: `evaluate_risk_efficiency`.

Candidate capital policies require OOS evidence and are ranked by net economic
output per true monetary stop-risk dollar, subject to non-worsening p95 drawdown
and tail-loss gates.

No strict robust improvement -> `ABSTAIN`.

### T08 — Portfolio Netting

Engine: `evaluate_portfolio_netting`.

Inputs:

- verified factor map;
- position-level signed factor risk;
- causal/stable correlation state;
- capped netting-credit fraction.

Only true factor offsets can create `TRUE_PORTFOLIO_NETTING` capacity.
Nominal position count is never netting evidence.

### T10 — Capital Velocity

Engine: `evaluate_capital_velocity`.

Uses realized output and real capital-time evidence. Candidate policies require
OOS samples and cannot worsen p95 drawdown or tail loss. Selection maximizes
realized net output per capital-minute and must strictly improve the baseline.

### T16 — Hedged Exposure / Risk Transfer

Engine: `evaluate_hedged_exposure`.

A hedge must be:

- instrument-certified;
- execution-supported;
- sufficiently correlated;
- correlation-stable;
- positive net risk transfer after basis risk and hedge cost.

If the provider has no certified hedge instrument, the only legal result is
`NO_CERTIFIED_HEDGE_INSTRUMENT / ABSTAIN`.

### T17 — Convex / Limited-Downside Exposure

Engine: `evaluate_convex_exposure`.

A convex expression requires:

- instrument certification;
- fresh pricing;
- settlement certification;
- execution support;
- explicit bounded downside;
- downside inside certified limited-downside capacity;
- positive net upside after premium/cost.

If no such instrument exists, the only legal result is
`NO_CERTIFIED_LIMITED_DOWNSIDE_INSTRUMENT / ABSTAIN`.

CIBO may never relabel an ordinary linear CFD/spot position as convex.

## 3. Scope separation

Advanced tools are evaluated at the correct authority level.

Per-opportunity:

- T02
- T03
- T04
- T17

Portfolio/account level:

- T08
- T10
- T16

This prevents repeated portfolio netting/hedging decisions from being fabricated
once per Trader opportunity.

## 4. Full-surface coordinator

Canonical entry point:

`src/qore/infrastructure/cibo_ce2i_full_surface.py`

It binds:

1. account-derived CIBO mission;
2. causal regime selection;
3. canonical T01..T20 registry;
4. per-opportunity advanced evidence;
5. portfolio-level advanced evidence;
6. fail-closed advanced decisions.

It rejects any registry that is not exactly T01..T20 or contains
`ARCHITECTURE_ONLY` / `REJECTED`.

## 5. Regime law

New-capital / expansion tools include T02, T04, T16 and T17.

Recovery-safe advanced tools include T03, T08, T10 and T16, subject to their own
evidence gates.

Correlation BREAK blocks T08 and T16 together with portfolio competition that
depends on stable factor relationships.

Provider degradation/stress cannot be bypassed by an advanced CE2I tool.

## 6. Phase20 binding

The rejected partial candidate is preserved as historical evidence and cannot
be reused for certification.

The current full-surface candidate binds all T01..T20 and evaluates the seven
advanced tools before downstream MPC / allocation / QORE Risk.

Every Phase20 policy record contains a `full_surface` assessment. Therefore a
future qualification cannot silently omit an advanced tool.

## 7. Qualification law

The full-surface qualification plan contains hard gates:

- `FULL_CE2I_TOOL_SURFACE_20_OF_20_IMPLEMENTED`
- `ADVANCED_TOOL_EVIDENCE_COMPLETE_OR_EXPLICIT_ABSTENTION`

The qualifier reads the sealed full-surface policy record.

- `APPLIED`: counted as exercised capability.
- `ABSTAIN`: legal only as an explicit causal decision.
- `FAIL_CLOSED`: invalidates qualification.

This is in addition to all existing causal, execution-economics, capital
conservation, concentration, temporal-fold, drawdown and productivity gates.

## 8. Anti-cheating invariants

Completion of the toolbox does not permit:

- outcome-aware sizing;
- future leakage;
- synthetic OOS evidence relabeled as observed;
- fabricated structural stops;
- floating PnL as realized funding;
- fictitious netting;
- assumed hedge correlation;
- simulated convexity presented as executable;
- double-spent margin/risk;
- loosening QORE Risk;
- bypassing provider constraints.

## 9. Certification status

Architecture implementation is not economic certification.

Certification remains blocked until:

1. CI proves the complete code surface;
2. every advanced tool receives causal evidence or an explicit valid abstention;
3. the full-surface candidate is frozen against the final architecture commit;
4. a fresh post-freeze forward population satisfies the preregistered minimums;
5. Phase21 freeze and the disjoint Phase22 sealed holdout pass.

No old 13/20 population can be reused.
