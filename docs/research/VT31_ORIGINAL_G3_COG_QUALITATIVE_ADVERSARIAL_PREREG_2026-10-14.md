# VT31 — PRE-REGISTERED: adversarial, qualitative cognition of ORIGINAL G3 source engine

Owner order: certify METHOD + COGNITION, NOT profits, PF, DD, Sharpe, return density or quantitative edge. This prereg is committed before code and new CI.

## Exact subject and boundaries
- Actual original engine: `src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py::VT31CleanroomCognition` and its own `CognitiveAssessment` and `CognitiveDecision`; not `scripts/vt31_ttrades_am_native_cog_v1_20261014.py` or a mimicking oracle.
- Original G3 code SHA locked `cognition.py=d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9`, `operations.py=0ce9707314aecb71155de8b57044b6ec028847b2`, acta `e99c70b4e018d626fb620d9a21b9314a51abc36d`. Do not alter any existing implementation, no logical retuning.
- Test only hardcoded SYNTHETIC closed M1 timelines originally exercised by native G3 test, not real 3Y or untouched OOS; preserve chronological streaming, source levels, and actual engine response. File SHA, actual behavior, reasons and as_of in JSON. Do not pass externally forged CognitiveDecision to native engine.
- No author certification is implied by a source-only positive. For each scenario, verdict `PROCEDURAL_CONSISTENT_WITH_EXPECTATION`, `EXPECTED_ABSTENTION`, `CAUSAL_INPUT_REJECTED`, or `UNRESOLVED_SOURCE_FIDELITY`, never `CERTIFIED_COGNITION` just because tests pass. Distinguish source ICT_GENERAL_2023 London versus TTRADES_NY_AM_2025; London does NOT inherit 09am H1 sweep.

## Fixed diagnostic scenarios; no later changes based on outcome
1. `LONDON_SOURCE_LONG`: exact 390 real-shaped synthetic prior NY cash closed M1 H1 with 150 high /80 low, Asia 180 M1 + London 03:00–03:05 M1 with confirmed high 105 and displacement to 107; expect original COG LONG, DOL prior NY high 150, MSS source level 105, no orders or live permission.
2. `LONDON_HOLD_SAME_ASOF`: repeated `assess` on same prefix, result logical decision invariant (do not reissue a different target).
3. `NO_PREVIOUS_CASH_POOL`: omit prior 390 NY cash bars entirely, retain Asia+London; source no valid previous cash pool, expect no decision with liquidity pool or no valid next draw.
4. `MSS_NOT_YET_CONFIRMED`: remove last 03:05 MSS candle, no confirmed shift, expect no decision.
5. `HTF_CONTEXT_MISSING`: retain prior cash + London M1 only; remove entire pre-London same-day Asia M1, expect no decision and H1 and M15 context missing.
6. `AFTER_DOL_CONSUMED`: begin with positive M1 thesis, append new M1 that wicks through 150 while closing below, expect original COG removes unswept pool and revokes thesis, not LONG to exhausted DOL.
7. `AFTER_PIVOT_REVERSAL`: append new M1 closing below confirmed 105 MSS pivot, expect revoke thesis, not a retained decision.
8. `FUTURE_RETRO_ASOF`: append next CLOSED M1 then invoke assess at prior as_of; expect error, no backdating.
9. `G3_MSS_ANCHOR`: initialize same actual COG with existing opt-in G3_MSS_FRAMEWORK_POLICY; positive current MSS must bind exact real M1 close 107 and latest original shift time, no fabricated C3 anchor; no stage promote.
10. `LONDON_NOT_TTRADES_PROFILE`: London positive is ICT-General-research contextual only; source-scope statement should NEVER promote TTrades NY AM author proof, even with DOL from prior NY cash. No independent source fidelity judgement based on this case.

## Success and limitations
Deliver ten raw per-case records with exact original engine state/missing, real source facts, decisions, analysis of abstentions (WAIT is correct), immutable G3 software fingerprint and CI passing QA. If any actual engine response contradicts expected logic, **report failing scenario and debug**, do not modify engine to pass without distinct prereg/Owner signoff. This proves scenario-conformant COG behavior, not autonomous full methodology fidelity nor real-market cognitive certification. Still need independent exemplar-based ICT & TTrades judgment, real COG NYC scenario, human COG/OPS double sign-off Issue #897; produce distinct METODOLOGIA_PENDING / COGNITIVA_PENDING.

NO PNL, HISTORICAL MARKET SCREENING, ORDERS, SIZING, MERGE, LIVE, VPS, FundedNext LIVE, DEMO promotion or counterfeit reviewer signatures.