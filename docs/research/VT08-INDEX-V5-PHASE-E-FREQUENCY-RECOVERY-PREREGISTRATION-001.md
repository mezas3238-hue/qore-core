# VT-08 INDEX V5 — PHASE E FREQUENCY RECOVERY PREREGISTRATION 001

Status: PRE-ECONOMIC / CONSUMED-EVIDENCE ONLY
Fresh holdout 2020–2022: SEALED
Candidate freeze: NOT PERMITTED BY THIS DOCUMENT

## Motivation

Phase D D1 (`VT08_INDEX_V5_D1_RELATIVE_STRENGTH_001`) passed its preregistered consumed-evidence gates but is operationally sparse. In the consumed 2022–23 window, the V3 base generated 142 raw structural signals but modeled only 51 after geometry/daily-selection constraints; D1 retained 13. The owner therefore requires explicit investigation of missed valid opportunities before any fresh-holdout opening.

This document does not invalidate the Phase D statistical result. It adds a new operational objective: recover source-valid opportunity frequency without sacrificing causal robustness.

## Source-bound rationale

TTrades relative-strength/SMT guidance treats SMT as a refinement tool after a valid fractal model, not as a standalone mandatory foundation. Relative strength may also be resolved with structure/separation and candle closures when clear SMT is absent. Positional entries require a completed fractal model and a valid Protected Swing before the new HTF candle opens.

The V3 numeric geometry gates (`protected_risk_fraction >= 0.003`, `closure/reference range ratio >= 1.2`) are QORE empirical research containments, not universal TTrades rules. The V3 `unique-raw-signal-only` daily admission rule is likewise not a source rule requiring only one H4 opportunity per NY date. Therefore these gates are legitimate targets for causal frequency-recovery research.

## Evidence scope

Only already-consumed evidence may be used:
- 2022-09-15 .. 2023-09-15 (consumed V3 fresh)
- 2023-09-15 .. 2024-08-13 (consumed V2 fresh)
- 2024-08-13 .. 2026-09-12 (consumed development/R1)

2020–2022 remains inaccessible.

## Phase E diagnostic census

For every symbol/NY date/anchor in NAS100, SP500, US30 at 02/06/10 NY, reconstruct before outcome inspection:
1. whether a source-valid fractal signal resolves under `C2_OR_C3_BODY_CLOSE` + `FARTHEST_STRUCTURAL`;
2. whether Protected Swing/CISD is valid before the new H4 open;
3. whether V3 geometry would admit/reject;
4. whether more than one distinct anchor on the same NY date resolves;
5. peer-index state available at that same `signal_at`;
6. relative-strength features available before entry: SMT structural divergence where defined, structural separation where SMT is absent, and closure-conviction comparison;
7. modeled outcome using frozen stop/target/lifecycle semantics only after the pre-entry census is complete.

No post-entry field may construct an admission rule.

## Preregistered hypotheses

### E1 — Remove non-source numeric geometry containment
Retain the completed fractal model, Protected Swing stop, existing target/lifecycle semantics, and fail-closed data rules, but do not require V3's numeric 0.003 risk-fraction or 1.2 closure/reference thresholds.

### E2 — Per-anchor opportunity sovereignty
Do not reject a valid H4 opportunity merely because another valid signal exists on the same NY date at a different authorized anchor. Ambiguity remains fail-closed only when competing candidates conflict at the same symbol/anchor decision.

### E3 — Source-faithful relative-strength resolver
Replace mandatory `exactly two same-side peer signals` as the final cross-index admission rule with a deterministic pre-entry resolver:
- valid fractal model is primary;
- if SMT structural divergence is present, prefer stronger market for LONG / weaker market for SHORT;
- if SMT is absent, use structural separation from the relevant prior extreme;
- if still unresolved, use candle-closure conviction;
- unresolved ties fail closed;
- relative strength refines market selection and does not create a trade without a valid fractal model.

E3 must be implemented from price/structure observable at `signal_at`; the existing D1 count field may be reported diagnostically but may not be used as a hidden fallback.

### E4 — Combined source-faithful recovery
Apply E1 + E2 + E3 together. E4 is not permitted to alter closure, Protected Swing stop semantics, target, lifecycle, anchors, markets, sides, or post-entry handling.

## Falsification requirements

Each hypothesis is evaluated independently on all three consumed windows with primary friction `-0.05R/trade` and additional `-0.10R/trade` stress.

A hypothesis may advance only if:
- stressed mean is positive in every consumed window;
- aggregate stressed PF > 1;
- NAS100, SP500, US30 aggregate stressed means are each positive;
- LONG and SHORT aggregate stressed means are each positive;
- chronological second half stressed mean is positive;
- leave-one-market-out stressed means are positive;
- no result depends on retrospective removal of a market, side, anchor, closure family, or period;
- the recovered sample is strictly larger than D1's 73 trades;
- end-to-end replay is deterministic and no-lookahead.

Frequency is a secondary objective after the robustness gates above. No hypothesis may be selected merely because it has the largest trade count or highest P&L.

If more than one hypothesis passes, prefer the source-simpler rule in this order: E3, E2+E3 if separately represented, then E4. Do not choose by best observed economics.

## Governance

- consumed-evidence-only: TRUE
- holdout_open_permitted: FALSE
- candidate_freeze_permitted: FALSE until Phase E adjudication and end-to-end hardening
- LIVE_AUTHORIZED: FALSE
- REAL_CAPITAL_AUTHORIZED: FALSE
- PRODUCTION_AUTHORIZED: FALSE
- no merge without owner order
