# VT-08 INDEX V5 — SOURCE CONTEXT PREREGISTRATION 001

Status: PRE-ECONOMIC / CONSUMED-EVIDENCE ONLY

Parent checkpoint: PR #548, HEAD `27d4742cda6f691b359d106c2b6fe8eb2b044fc4`.

## Research question
Determine whether V4 `previous_source_day_body_alignment` is a proxy for the TTrades source distinction between continuation closure and reversal closure, without selecting rules by outcome.

## Critical hypothesis discipline
`body_opposed == reversal_closure` and `body_aligned == continuation_closure` are NOT assumed. They are separate causal features and their relationship is the object of falsification.

## Causal time contract
Every predictor MUST be completely known at `signal_at`. An unclosed daily candle is forbidden. Any row that cannot reconstruct the relevant closed source candles without future information fails closed.

## Frozen Phase-A experiment
On the already-consumed 183-trade V3/V4 census reconstruct independently: existing body alignment; previous-closed-day closure context; whether closure context matches trade side; and exact source timestamps.

Directional definitions: bullish continuation = closed source day closes above preceding closed source-day high; bearish continuation = closes below preceding low; bullish reversal = trades below preceding low and closes back inside; bearish reversal = trades above preceding high and closes back inside. Two-sided/outside cases are unresolved, not outcome-selected.

Produce the full body-alignment × closure-context confusion matrix and decompose closure-context performance by all three consumed windows, NAS100/SP500/US30, LONG/SHORT, and 02/06/10 NY. Primary friction remains 0.05R/trade. Report all cells without post-hoc exclusions.

## Isolation rule
Phase A MUST NOT change POI, entry family, protected-swing selection, stop, target, expiry, management, markets, anchors, or execution mechanics. Exact V3 mechanics are retained to isolate context classification.

## Promotion gate
No V5 candidate is frozen here. Promotion requires causal/no-lookahead reconstruction, deterministic/fail-closed resolver, consumed temporal/core-strata stress, unchanged V3 mechanics outside admission/context, then a separate frozen candidate identity/fingerprint/provenance contract before unseen evidence.

## Sealed evidence
2020–2022 remains SEALED. This branch MUST NOT read, optimize on, or open that interval.

## Governance
`DEMO_ELIGIBLE=false`
`LIVE_AUTHORIZED=false`
`REAL_CAPITAL_AUTHORIZED=false`
`PRODUCTION_AUTHORIZED=false`
