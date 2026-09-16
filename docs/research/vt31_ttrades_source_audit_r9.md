# VT-31 post-R8 source audit — TTrades vs QORE

Status: RESEARCH ONLY / NO_R9_NOT_CERTIFIED / NO LIVE AUTHORITY

This audit is frozen before any new candidate or fresh holdout. It separates source claims from QORE empirical rules and records potential misformalizations that must be tested only on consumed evidence.

## Evidence classes

- **TTRADES_EXPLICIT**: stated directly in the named TTrades Silver Bullet/source lesson.
- **TTRADES_IMPLIED**: supported by TTrades supporting methodology but not stated as a universal AM Silver Bullet rule.
- **QORE_EMPIRICAL**: introduced by QORE research/backtests; not represented as a TTrades rule.
- **OWNER_AUTHORIZED_TRANSFER**: owner-authorized transfer from NQ/NAS100 to SP500/US30.
- **UNRESOLVED**: source ambiguity requiring fail-closed handling or separate research.

## Primary AM Silver Bullet source

Primary public source: https://ttrades.com/the-am-silver-bullet-strategy-on-nq/

| Topic | TTrades evidence class | Source interpretation | Current QORE R8 | Audit finding |
|---|---|---|---|---|
| Market | TTRADES_EXPLICIT | AM Silver Bullet lesson is on NQ | NAS100 + SP500 + US30 | SP500/US30 are OWNER_AUTHORIZED_TRANSFER, not source-explicit |
| Reference | TTRADES_EXPLICIT | Mark high/low of 9:00 a.m. hourly candle once 10:00 arrives | 09:00–10:00 NY range | faithful in intent; sparse-M1 reconstruction must remain evidence-aware |
| Setup window | TTRADES_EXPLICIT | Ignore setups outside 10:00–11:00 a.m. | 10:00–11:00, plus first executable setup <=10:20 | 10:20 is QORE_EMPIRICAL, not source rule |
| Liquidity raid | TTRADES_EXPLICIT | Price must take one side of 9:00 range before setup considered | strict first-side raid, both-side abstain | broadly faithful; exact equality/first-side mechanics are formalization details |
| Direction | TTRADES_EXPLICIT | sweep high -> focus shorts to 9:00 low; sweep low -> focus longs to 9:00 high | same directional mapping | faithful |
| Confirmation | TTRADES_EXPLICIT | sweep alone is insufficient; confirmation/displacement required | structural-close formalization | source requires displacement/confirmation; QORE's exact structural-close implementation needs audit |
| Entry models | TTRADES_EXPLICIT | displacement back into range, breaker, order block, FVG within structure are valid | breaker/FVG/OB | family set broadly faithful |
| Family priority | UNRESOLVED | primary Silver Bullet source does not prescribe universal family priority | nearest still-valid retracement to confirmation close | QORE policy, not source rule; likely material |
| Entry price within zone | UNRESOLVED / TTRADES_IMPLIED | supporting lessons use opening price, mean threshold, CE, or context-specific retest depending model | QORE near-stop/nearest retracement translation | not source-universal; must be audited by family |
| Initial stop | TTRADES_EXPLICIT | beyond the swing high/low that caused displacement | raid extreme, no buffer | potentially material misformalization: raid extreme is not necessarily the displacement/protected swing |
| Profit target | TTRADES_EXPLICIT | target always opposite side of 9:00 range in AM Silver Bullet source | fixed 2R | direct source divergence; 2R is QORE_EMPIRICAL for R7/R8 |
| Lifecycle after fill | UNRESOLVED / TTRADES_IMPLIED | primary source frames opposite 9:00 boundary as objective; supporting material discusses target/objective and structural management | QORE lifecycle to 16:00 plus M1 protected-swing trail | not explicitly the AM Silver Bullet rule; requires causal audit |
| Protected swing management | TTRADES_IMPLIED | protected swings define invalidation and may trail in trending price after proper close confirmation | M1 protected-swing trail | concept supported, exact QORE implementation must be checked against close-over-series rule |
| risk/reference <=0.175 | QORE_EMPIRICAL | no source rule found | required | empirical only |
| confirmation body >=0.50 | QORE_EMPIRICAL | no numeric source threshold found | required | empirical only |
| raid body >=0.35 | QORE_EMPIRICAL | no numeric source threshold found | required | empirical only |
| raid-to-final-extreme <=4 M1 | QORE_EMPIRICAL | no source rule found | required | empirical tail-control only |
| daily/HTF bias | TTRADES_IMPLIED | broader TTrades material repeatedly says context/HTF alignment improves reversal quality and warns against counter-bias reversal entries | absent from R8 AM contract | candidate root-cause hypothesis; cannot be promoted without consumed-only causal evidence |
| SMT | TTRADES_IMPLIED / OPTIONAL_CONFLUENCE | supporting reversal/continuation lessons present SMT as confluence, not universally mandatory | absent | do not make mandatory without source-specific evidence and consumed stability |

## Supporting TTrades source bindings

- Protected swing invalidation: https://ttrades.com/stop-loss-mastery-using-protected-swings-for-precise-invalidations/
- Protected swing confirmation: https://ttrades.com/protected-swings-understanding-trends-and-invalidations/
- Order-block reversal sequence: https://ttrades.com/my-favorite-reversal-pattern-orderblocks/
- Reversal sequence / increasing confirmation: https://ttrades.com/reversal-sequence-building-an-entry-model-for-trading/
- Fair value gap definition: https://ttrades.com/understanding-fair-value-gaps/
- Breaker blocks: https://ttrades.com/breaker-blocks-simplified/
- Timeframe alignment: https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/
- Top-down alignment: https://ttrades.com/mastering-top-down-analysis-aligning-multiple-timeframes-for-expansion-trading/
- Opposing/external liquidity context: https://ttrades.com/understanding-liquidity-buy-side-sell-side-and-swing-points/

## P0 divergences to test causally on consumed evidence

1. **Target mismatch** — R8 fixed 2R versus AM source's opposite 9:00 range objective.
2. **Stop-anchor mismatch** — R8 raid extreme versus source swing/protected swing that caused displacement.
3. **Entry-selection mismatch** — QORE nearest retracement / near-stop translation may choose a zone or price that the source would not prioritize.
4. **Confirmation/displacement weakness** — QORE structural close may admit weak displacement that source examples would regard as incomplete.
5. **Context omission** — R8 has no HTF/session-context gate despite TTrades supporting lessons emphasizing context/alignment for reversals.
6. **Lifecycle mismatch** — 16:00 lifecycle and M1 trail may not reflect the primary AM objective.

## Governance

None of the six P0 divergences is a new rule. They are hypotheses for consumed-only forensics. Any repair must be observable pre-entry, source-classified, finite, threshold-stable, walk-forwarded, provider-stressed, frozen, Full-QORE green, and only then tested once on a genuinely unseen holdout.
