# VT-08 Index V3 — Geometry Quality Research 001

Checkpoint: 2026-09-14

## Governance

This is a **new research identity**. It does not reopen or override the V2 one-shot rejection recorded by run `34795405536`, decision artifact `10329479540`, digest `sha256:6e52693c4231b9d2bc65ead4f57d95c08ab442751b185649108d970fcba2dcd5`.

Candidate identity: `VT08_INDEX_V3_QORE_GEOMETRY_001`.

The numerical geometry gate and fixed 2.5R research target are QORE empirical research containments. They are **not** represented as universal TTrades/source rules. Source-derived/prior-frozen mechanics retained are H4/M15 timing, C2-or-C3 body-close closure, farthest structural protected swing, protected-swing stop, one H4 lifecycle, all three Index markets, and Owner anchors 02/06/10 New York.

## Failure forensics that motivated V3

V2 failed fresh validation on 146 trades with mean `-0.043235R`, PF `0.9154`, and max DD `20.7871R`. The failure was not explained by anchor 06 alone. Post-holdout forensics showed that weak setup geometry and a truncated right tail were materially associated with the failure. No retrospective market, side, or anchor subset is promoted by V3.

## Frozen V3 mechanics

- Markets: `NAS100`, `SP500`, `US30`.
- Anchors: `02:00`, `06:00`, `10:00` America/New_York; no anchor is removed.
- Closure: `c2-or-c3-body-close`.
- Protected swing: `farthest-structural`.
- Stop: exact protected-swing extreme.
- Daily policy: exactly one raw signal per market / New York date before geometry admission.
- Geometry admission 1: protected-swing risk width / entry price `>= 0.003` (0.30%).
- Geometry admission 2: completed closure-H4 range / causal reference-H4 range `>= 1.2`.
- Target: fixed `2.5R` as a QORE V3 research policy.
- Lifecycle: next H4 boundary (`16` M15 bars).
- Gap-through adverse stop: observed M15 open.
- Favorable target gap: capped at frozen target.
- Same-M15 stop/target ambiguity: STOP-first.
- Friction stress: `0.05R` per filled trade.

The selected numerical point is intentionally a rounded interior point of a broad positive research plateau, not the exact P&L maximizer. Around the frozen point, risk thresholds `0.00275..0.00325`, closure ratios `1.15..1.25`, and targets `2R..3R` remained materially positive on consumed research evidence. This reduces dependence on a knife-edge optimum.

## Consumed research evidence

Research-only evidence combines periods already consumed by QORE:

- former fresh holdout: `[2023-09-15, 2024-08-13)`;
- former development evidence: `[2024-08-13, 2026-09-12)`.

No result below is fresh validation for V3.

### Former development tranche

`90` admitted trades; total `+20.562268R`; mean `+0.228470R/trade`; PF `1.76997`; max DD `6.12753R`.

### Former fresh tranche, now consumed research

`42` admitted trades; total `+11.401573R`; mean `+0.271466R/trade`; PF `1.90955`; max DD `5.13033R`.

### Combined consumed research

`132` trades; total `+31.963842R`; mean `+0.242150R/trade`; PF `1.81455`; max DD `6.12753R`.

By market:

- NAS100: `54` trades, `+0.084271R/trade`, PF `1.2402`.
- SP500: `36` trades, `+0.391840R/trade`, PF `2.5656`.
- US30: `42` trades, `+0.316832R/trade`, PF `2.1790`.

By side:

- LONG: `61` trades, `+0.255504R/trade`, PF `1.8668`.
- SHORT: `71` trades, `+0.230677R/trade`, PF `1.7704`.

By closure:

- C2: `21` trades, `+0.559839R/trade`, PF `2.8232`.
- C3: `111` trades, `+0.182047R/trade`, PF `1.6162`.

Anchor results are diagnostic only and are **not** used for admission: 02 had only 3 research trades, 06 had 28, and 10 had 101. V3 therefore does not claim that one clock hour causes the edge.

## Six sequential half-year falsification slices

All six raw slices were positive. After subtracting the frozen `0.05R` friction from every trade, all six remained positive:

| Slice | N | Raw mean R | Stressed mean R | Raw PF | Raw DD R |
|---|---:|---:|---:|---:|---:|
| 2023-09-15 → 2024-03-15 | 24 | +0.311926 | +0.261926 | 2.0284 | 3.1774 |
| 2024-03-15 → 2024-09-15 | 20 | +0.270768 | +0.220768 | 1.8656 | 2.3736 |
| 2024-09-15 → 2025-03-15 | 17 | +0.127508 | +0.077508 | 1.4701 | 3.0859 |
| 2025-03-15 → 2025-09-15 | 21 | +0.251884 | +0.201884 | 1.8072 | 3.6218 |
| 2025-09-15 → 2026-03-15 | 24 | +0.362735 | +0.312735 | 2.5114 | 3.7420 |
| 2026-03-15 → 2026-09-12 | 26 | +0.111516 | +0.061516 | 1.3302 | 6.1275 |

This is materially stronger cross-period behavior than V2, but remains consumed-evidence research.

## Next falsification

V3 cannot be promoted from any period above. A new, truly unseen cTrader DEMO tranche is required. The next one-shot holdout is separately pre-registered as `[2022-09-15, 2023-09-15)` New York and must be acquired only after the candidate code/tests/freeze are committed.

No post-result tuning is permitted on that tranche. If V3 fails the frozen holdout gates, this identity is rejected.

`DEMO_ELIGIBLE=false`  
`LIVE_AUTHORIZED=false`  
`PRODUCTION_AUTHORIZED=false`
