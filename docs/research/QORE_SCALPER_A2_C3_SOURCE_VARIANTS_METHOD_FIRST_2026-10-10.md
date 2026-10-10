# QORE Scalper A2 — Candle 3 primary-source variants (METHOD FIRST)

Date: 2026-10-10. PR #759. RESEARCH ONLY: NO LIVE, NO V49 ENTRY CHANGES, NO CERTIFICATION.

## Direct TTrades texts

- December 3, 2025: https://ttrades.com/candle-3-closure-a-complete-guide-to-identifying-continuations-and-reversals/ — Sections "Candle 2 vs. Candle 3 Closure", "When Candle 2 Fails, Candle 3 Can Still Confirm", "Chart Examples". After failed C2 reversal, C3 does not sweep C2 high/low, yet closes through its body; a POI and valid closure are necessary to validate a swing.
- January 10, 2026: https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/ — "CISD Without a Higher Time Frame Closure Means Nothing" and "Candle 3 Closure With CISD". Describes C3 closing beyond C2 opening price AND range, with LTF CISD closing through candles causing the swing.
- February 7, 2026: https://ttrades.com/ttrades-scalping-model-simple-day-trading-strategy/ — H1 C2/C3 bias, M15 swing, M1 execution; Daily broader context.

**SOURCE_AMBIGUITY NOT RESOLVED:** December inside-range and January beyond-range may describe separate contexts, editorial ambiguity or different models. Neither interpretation can be chosen using in-sample returns.

## Research implementation and falsifiers

New research module: src/qore/infrastructure/trader_lab/capitalizer_scalper_c3_source_variants_v1.py.

Variant DECEMBER_2025_NO_SWEEP_BODY_ENGULF delegates to the frozen V49 source detector. Variant JANUARY_2026_CLOSE_BEYOND_C2_RANGE operationalizes the later text as close strictly beyond C2 high/low and C2 body; this is an **A2 engineering hypothesis**, not source-certified author logic.

C3AsOfInput requires ordered timezone-aware H1 closes, prohibits POI or LTF CISD witnesses from after C3 closure, and requires LTF confirmation inside C3. Missing POI/CISD yields a geometrical observation without a complete contextual chain. Witness records ALWAYS have source_fidelity_certified=false, changes_v49_admission=false, authorizes_execution=false. In addition, the tests exercise bullish and bearish counterexamples, failed-C2 precedence, missing witnesses, future data rejection and zero trade authority.

Automated quality workflow: .github/workflows/qore-scalper-a2-c3-source-variants.yml. This is **not** nine-market historical A/B and does not claim PF/DD.

## 381 CISD differences: verified mechanism and limits

Original population 2876, 2495 matched, 247 SENSOR_EARLIER_THAN_V49 (171 original FVG -> sensor Sweep and 76 original Sweep -> sensor FVG), 134 SAME_TIME_DIFFERENT_FAMILY (original Sweep -> sensor FVG). Original 9-market experiment: https://github.com/mezas3238-hue/qore-core/actions/runs/38076268436 .

Verified code fact: V49 runs its two M1 V48 observers over a M15-to-next-M15-or-H1-deadline window, then picks minimum (confirmation time, route family). Shadow sensors only see the prefix through original decision close, call both observers and apply the **same** minimum time/family priority. A full-horizon observer searching an earlier precursor and a short-prefix observer returning the first already-confirmed precursor can disagree, especially if observer selection is not prefix-stable.

If both observers return identical candidate sets, identical time/family tie priority cannot explain the 134 same-time family differences by itself. Underlying observed candidates, temporal scope and series/POI linkage must be reconciled. This is NOT source adjudication of 381 individual IDs: status stays UNRESOLVED until bar-level proof. The 381 are not proof of an opposite-direction CISD; the sensor inherits H1 side. Reject automatic veto (observed PF .664 -> .621, DD 236.13R -> 252.10R).

## PRE-REGISTERED next P0 — nine-market historical A/B (not yet executed)

1. Lock original V49 2876-source run #38053946695, native 9-market M1 #35548099334, sensor run #38071138991 and A1 H1/M15/M1 witness ledgers; reject duplicate ID, synthetic data, timestamps after decision or missing source manifest.
2. Build both C3 universes on exactly the same native 60/60 H1 candle triples. Distinguish pure geometry, real POI, HTF close, and LTF CISD source witnesses. Enumerate C2-only, December-only, January-only, neither, and any overlaps BEFORE looking at P&L; keep all original 2876 source IDs in the reconciliation.
3. Bind H1 bias to M15 setup/protected swing and first M1 route using causal source IDs; preserve the original stops, targets, MAX3, session and broker-cost assumptions in any later replay. Compare observer full-window vs each at-time prefix only for forensic diagnosis; NEVER transmit future witness, MFE/MAE or winner labels to Master Frame.
4. Produce 381 source-ID rows with evidence and categories only when proved: SOURCE_WINDOW_SUPERSEDED, OBSERVER_PREFIX_UNSTABLE, ROUTE_TIE_POLICY, HTF_POI_OR_SERIES_MISLINKED, UNRESOLVED. Do not hallucinate a per-ID cause from aggregate counts.
5. Report 9/9 market denominators and sessions, paired C3 overlap, favorable +30m EX-POST separately, and only later economic PAPER PF/DD if a fully chronological native replay exists. Freeze a genuinely outside-sample validation for certification. The 2025-09 to 2026-09 V49 period is already development data.

Owner's density/preservation limits: >=934 original winning IDs, >=415.74848565 original winning R, no promotion of a 94-trade V50-G subset, no new automatic CISD veto, no source claim without direct rule evidence.

**Current explicit blockers:** Historical C3 nine-market paired A/B not executed; 381 discrepancy roots not yet adjudicated individually; full nine-market Master Frame economic PF/DD absent. V49 remains unchanged and certification blocked.
