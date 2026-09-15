# VT-08 CRT / H4 Power of Three V2 — video-fidelity re-audit 002

## Status

This document re-opens VT-08 V2 against the Human Owner-provided primary video before any further economic claim is allowed.

The earlier `v2.2-source-faithful` implementation is **not certified source-faithful**. Its previous 11-market run remains useful engineering evidence, but neither the old 13,468 trades nor the newer 16,351 mechanical candidates may be treated as final evidence of the methodology.

The corrected research contract is now versioned `v2.4-source-fidelity-reaudit`. It fails closed on unresolved source judgments and MUST remain non-economic until the source execution contract is complete.

## Primary authority

- Human Owner file: `1000854868.mp4`
- Public identity: `youtube:FAKWJ-1NlLE`
- SHA-256: `bfe76fa4346ec4d7442886c21834aa26f0d82172bdb55666e8c77226cdf83271`
- TTrades lesson: **Trading The 4 Hour Power Of Three - OHLC / OLHC**
- Same-author companion material released with the lesson: H4 PO3 PDF/blog.
- Explicit prerequisites named by the lesson: TTrades Candle 2, Candle 3, and CISD/protected-swing material. They may define concepts the primary lesson depends on but may not introduce a different strategy.

## Re-audit rule

Every mandatory software rule must be classified as one of:

1. `EXPLICITLY_STATED`
2. `VISUALLY_DEMONSTRATED`
3. `REQUIRES_FORMALIZATION / SOURCE_AMBIGUOUS`

A `REQUIRES_FORMALIZATION / SOURCE_AMBIGUOUS` item MUST NOT silently become a mandatory automated trading rule.

## Confirmed source rules

| Source fact | Classification | Software consequence |
| --- | --- | --- |
| H4 PO3 is Accumulation -> Manipulation -> Distribution/Expansion | EXPLICITLY_STATED + VISUALLY_DEMONSTRATED | Preserve H4 PO3 state model |
| Candle 2 with shallow opposing wick/run may reverse-to-expansion in the same H4 candle | EXPLICITLY_STATED + VISUALLY_DEMONSTRATED | Preserve Candle-2 scenario |
| Candle 2 with a large/deep opposing run should not be forced into same-candle expansion; wait for Candle 3 continuation | EXPLICITLY_STATED + VISUALLY_DEMONSTRATED | Preserve Candle-3 scenario |
| Let the wick form, trade the body | EXPLICITLY_STATED | No pre-wick or anticipatory entry |
| M15 is the demonstrated lower timeframe paired with H4 in this lesson | EXPLICITLY_STATED + VISUALLY_DEMONSTRATED | Preserve M15 confirmation evidence |
| Lower-timeframe sequence includes reach into a source-defined point of interest before CISD/protected-swing continuation confirmation | EXPLICITLY_STATED in the same-author lesson companion + prerequisite-defined | POI state/provenance is mandatory; do not invent a universal POI selector |
| CISD/protected swing confirms that the opposing run formed a swing | EXPLICITLY_STATED + prerequisite-defined | Preserve causal CISD/protected-swing confirmation |
| Higher-timeframe bias/candle-closure context matters | EXPLICITLY_STATED | Bias must have source-bound provenance; no fabricated D1 formula |
| Protected-swing extreme is the structural invalidation reference | VISUALLY_DEMONSTRATED + prerequisite-defined | Preserve the extreme as invalidation reference; do not invent a stop buffer |

## Finding F1 — incomplete H4 timing coverage (P0)

The previous V2 audit scanned only:

- Forex: `01:00 / 05:00 / 09:00` New York
- Futures: `02:00 / 06:00 / 10:00` New York

The primary video's Timing slide shows the complete repeating H4 opening families:

- Forex: `17:00 / 21:00 / 01:00 / 05:00 / 09:00 / 13:00` New York
- Futures: `18:00 / 22:00 / 02:00 / 06:00 / 10:00 / 14:00` New York

Therefore the previous historical source audit under-scanned source-authorized H4 windows. The existing `16,351` mechanical-candidate total is **not a final source-fidelity count** and must be recomputed after the timing correction.

This does not mean every H4 candle is automatically a trade. The six values are H4 opening anchors, not an instruction to force six entries per day.

## Finding F2 — CISD close was promoted to an exact entry price without sufficient source authority (P0)

The earlier evaluator set:

`entry_price = confirmation.close`

The source supports CISD/protected swing as **confirmation that the wick/swing has formed**. It does not establish a universal rule that every valid VT-08 V2 trade must execute exactly at the confirming candle close.

The exact CISD closing price must therefore remain an observation/confirmation price unless an exact entry model is demonstrated by the primary lesson or an explicitly required prerequisite.

The corrected evaluator no longer emits an executable `SETUP` from CISD alone.

## Finding F3 — bias provenance is insufficiently constrained (P0)

The primary lesson explicitly uses H4/candle-closure context and expansion in line with higher-timeframe/daily context. The source does **not** provide one universal OHLC-only formula that can mechanically replace that judgment.

Required behavior:

- retain unresolved bias when source context cannot be reproduced;
- provenance must identify the exact source-bound context evidence used;
- no arbitrary label, future information, post-outcome label, or invented D1 formula may authorize an automated historical trade.

The corrected contract timestamps source context and rejects context observed after the CISD confirmation.

## Finding F4 — shallow versus large/deep remains qualitative (blocking)

The source repeatedly distinguishes small/shallow versus large/deep opposing runs, but the lesson does not state a universal numerical threshold.

Still prohibited:

- 50% wick threshold;
- ATR threshold;
- body/wick ratio invented by QORE;
- volatility percentile;
- optimization-selected cut-off.

This remains a source judgment unless an explicitly required source supplies an unambiguous operational definition.

## Finding F5 — target remains contextual, not universal (blocking)

The lesson/examples use contextual objectives. A previous-day high is demonstrated in an example, but that does not authorize a universal `PDH/PDL` target for every setup. The prerequisite material also varies objectives with structure/wick context.

Therefore these remain prohibited as universal rules:

- fixed R target;
- universal previous-day high/low target;
- arbitrary H4 opposite boundary target;
- optimized target chosen from backtest results.

Without a source-authorized target/lifecycle, there is no valid economic win/loss series.

## Finding F6 — XAUUSD timing family remains unresolved

The source distinguishes Forex and Futures timing families but does not unambiguously classify XAUUSD for this methodology. QORE must continue to abstain rather than guess.

## Finding F7 — current 16,351 candidates remain candidates, not trades

The previous 11-market audit correctly refused to fabricate economic trades, but its candidate coverage is incomplete because of F1.

After correction, the audit may produce a different mechanical-candidate count. Regardless of the count:

`MECHANICAL CANDIDATE != SOURCE-AUTHORIZED ENTRY`

and descriptive MFE/MAE after confirmation is not a win/loss classification.

## Finding F8 — point-of-interest reach was missing from the executable contract (P0)

The exact H4 PO3 lesson companion states the lower-timeframe process as a reach into a point of interest, then CISD/protected-swing confirmation, then continuation entries after the wick has formed. The Candle-3 prerequisite likewise names source POIs such as FVG/high/low.

The earlier V2 evaluator could accept H4 structure + wick classification + CISD without retaining proof that the source-defined POI had been reached.

The correction is deliberately conservative:

- `point_of_interest_reached` is an explicit tri-state source judgment (`true`, `false`, unresolved);
- any resolved POI state requires provenance;
- unresolved POI -> `ABSTAIN`;
- POI not reached -> `ABSTAIN`;
- POI reached still does **not** create a trade because exact entry/target remain unresolved;
- QORE does not invent a universal POI-ranking or selection algorithm when multiple FVG/high/low candidates exist.

Historical mechanical candidates therefore record `requires-source-poi-confirmation`; they remain research observations, not entries.

## Required V2 redesign before the next historical campaign

1. Correct the full H4 timing families and add regression tests covering all six anchors per family plus DST behavior.
2. Separate `CISD confirmation price` from `source-authorized executable entry price`.
3. Fail closed when exact entry remains unresolved.
4. Strengthen source-context provenance for bias and prohibit oracle/post-outcome context.
5. Require source-defined POI reach/provenance before accepting CISD confirmation; do not invent POI selection.
6. Preserve qualitative wick state without inventing a threshold.
7. Preserve protected-swing extreme as invalidation reference without inventing a buffer.
8. Keep target/lifecycle unresolved unless the source proves a deterministic rule.
9. Preserve XAUUSD timing as unresolved unless the source classifies it.
10. Re-run focused fidelity tests and full QG.
11. Only then re-run the >=730-day broker-backed source-fidelity audit.
12. Do not run an economic backtest, Stress, Monte Carlo, or claim wins/losses unless entry + invalidation + target/lifecycle + selection become source-authorized.

## Governance consequence

The correct immediate state for VT-08 V2 is:

`SOURCE RE-AUDIT OPEN -> SOURCE-SAFE IMPLEMENTATION UNDER QG -> ECONOMIC BACKTEST NOT AUTHORIZED`

No CI result, candidate count, favorable path, or green workflow may override this source-fidelity gate.
