# VT08 5M — Architect B Cognitive P0 — First Implemented Research Bridge

**Date:** 2026-10-10  
**Source PR:** [#764](https://github.com/mezas3238-hue/qore-core/pull/764) (DRAFT/RESEARCH ONLY), stacked on [#634](https://github.com/mezas3238-hue/qore-core/pull/634).  
**Architect B task:** [#763](https://github.com/mezas3238-hue/qore-core/issues/763); methodology counterpart [#762](https://github.com/mezas3238-hue/qore-core/issues/762).  
**Code CI proven on exact SHA:** `0e36246f1b0c1d9d37dcbc87cd7a04030fdbb62c` — [run 38069258846](https://github.com/mezas3238-hue/qore-core/actions/runs/38069258846), SUCCESS (Ruff + Mypy + Pytest).

## Technical changes already committed

- `src/qore/infrastructure/traders/vt08_cognitive_5m_research_scope.py`:
  - exact five-market research scope EURJPY/USDCHF/NZDUSD/CADJPY/USDCAD;
  - explicit separate research Situation Model inheriting all production validations except overridden market scope;
  - no production-market whitelist change and no order, capital or broker authority;
  - mandatory source event ID and timezone-aware closed-bar cutoff, rejecting known future bars;
  - market/anchor memory explicitly `UNKNOWN_NOT_BOUND`, including USDCAD unless temporal validity is proven; no fake new-market priors or imported historical performance;
  - deterministic *separate* research strategy/memory fingerprints.
- Original `vt08_cognitive_situation_model.py`: extracted overridable market-authorization hook, preserving existing production default validation for original Forex market list.
- `vt08_cognitive_reasoning.py`: handles research situation through research-only memories and identity, and prevents EXECUTE when explicit support is entirely missing (meta UNKNOWN -> WAIT).
- `vt08_cognitive_journey_intelligence.py`: research-only market/anchor memory and evidence fingerprint binding.
- `src/qore/infrastructure/trader_lab/vt08_cognitive_5m_consumed_gate_v1.py`:
  - consumes source-event-linked, synthetic as-of Situation snapshots through original `evaluate_cognitive_hypothesis()`;
  - preserves hypothesis WAIT across chronological snapshots;
  - kills source on ABSTAIN, never executes same source twice;
  - admits in-trade assessments only following source EXECUTE, with increasing as-of and matching position snapshot timestamps;
  - calls original `evaluate_in_trade_cognition()`, retaining Journey and Position fingerprints and reason codes;
  - returns immutable trace objects; no broker execution or economics, no management changes applied to trades;
  - uses uncalibrated research position policy, no unsourced stop or reduction policy.
- Tests: `test_vt08_cognitive_v1_research_scope.py` and `test_vt08_cognitive_5m_consumed_gate_v1.py` plus original Cognitive V1 kernel and journey tests.
- CI: `.github/workflows/vt08-cognitive-5m-research-bridge.yml`.

## Explicit limitations that must remain visible

1. Source methodology still owns entry family, decision-clock semantics, stops, targets, H4 lifecycle, cardinality and candidate priority. **This PR does not construct those**, recover executable trade density or alter old backtest economics.
2. The five-market Market Memory/Trader Experience Memory remain marked **UNKNOWN_NOT_BOUND**. Existing seven-market evidence is not valid substitute for four new markets. A future versioned training/as-of binding is required before claiming complete real five-market memory consumption.
3. Synthetic tests exercise real cognitive functions but are **not** a market replay. PF, DD, profitability improvement, recovered trades and per-entry real evidence are **not measured**.
4. The gate consumes as-of snapshots but does not yet prove each constituent upstream feature was computed exclusively from as-of visible bars; this requires full CandidateEvent provenance and adversarial bar perturbation tests.
5. Existing replay `vt08_cognitive_expansion_5m_backtest_v1.py` and latest-PS frontier are untouched and **still bypass full cognition**; therefore do not label historical PR #634 economics as full cognitive performance.
6. A registered/filled position remains a *hypothetical research path* until Architect A's complete source bundle and separately governed economic execution contract exist.
7. The sealed older seven-year archive remains untouched. No VPS, DEMO, LIVE or production authorization.

## Required joint next handshake with Architect A (issue #762)

Before beginning historic consumed-data replay, jointly freeze a versioned `VT08_5M_CANDIDATE_EVENT_V1` packet with:
- stable `source_event_id` across WAIT->EXECUTE updates, guaranteed new id for genuine rearm; fingerprint of source structure, not best-outcome id;
- methodology status `SOURCE_COMPLETE_EXECUTABLE` versus `SHAPE_ONLY` / `SOURCE_AMBIGUOUS`; only first ever eligible for filled replay;
- market, New York date, Owner anchor, LTF profile, direction and bounded H4 cycle;
- causal as-of and **every supporting feature's latest available closed-bar timestamp** (not merely top-level maximum);
- source identity + provenance of CISD/PS/POI and entry family; exact entry type/price/SL/TP/expiry/partial fill/lifecycle and daily priority, owned by Architect A;
- contradictions, uncertainties and supporting evidence that can be tested independent of outcomes;
- no terminal PnL, no future MFE/MAE, no hindsight "winner" selection;
- known producer fingerprint/contract SHA and immutable test fixture.

The shared golden fixture must include: valid source EXECUTE, incomplete WAIT then later confirmation, material contradiction ABSTAIN then attempted same-source fallback (must fail), new-source rearm, position HOLD plus source-governed exit, DST and missing memory examples. This is a proposal for **joint approval**, not unilateral methodology authority.

## Next Architect B sequence

1. Obtain written CandidateEvent V1 agreement with A on #762 and #763.
2. Implement source-event->situation adapter with causal data availability checks and explicit governance of source-unresolved bundles. Consume every candidate, not only postselected winners.
3. Replace direct backtest admissions **in a new versioned replay**, leaving original raw baseline intact. Enforce no fallback and one per market/NY date at actually filled stage with methodology-owned priority.
4. Consume closed-bar position updates chronologically, record decisions and only apply source/governance-authorized proposals to simulated executions.
5. Reconcile 100% per-entry cognitive provenance and position coverage; report matched baseline vs cognitive, false abstentions and rescued/forgone trades. Only then compute genuine PF/DD attributed to cognition.
6. Freeze final candidate and certification gates before ever opening older sealed validation.

**Status:** **P0 cognitive research bridge IMPLEMENTED + CI PASS**; **full real-market cognitive replay NOT YET IMPLEMENTED**; **five-market memory training NOT YET VERIFIED**; **VT08 NOT CERTIFIED**.
