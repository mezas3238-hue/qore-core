# VT08 CRT PURE — R2-CG frozen WAIT frontier and failure attribution

**Preregistered:** 2026-10-13. **Scope:** read-only AUDUSD / USDJPY. **Parent:** #626. **Status:** diagnostics only — no tuning and no candidate promotion.

## Question, no new trading rule

Determine why the **strictly prior-only** R2-CF WAIT Journal worsened specific historical folds (AUDUSD OOS-2016, USDJPY OOS-2023); determine the hard upper-bound of **eligible one-step WAIT opportunities** in the frozen original population without resurrecting ABSTAIN, adding third WAIT, altering identity, or using sizing/volume. No new threshold, filter, strategy adjustment or trained model is permitted in R2-CG.

## Immutable evidence and exact reconciliation

- Original R2-CC historical frozen delayed ledger and report from run `36173116494` (AUDUSD).
- Original R2-CD historical frozen delayed ledger and report from run `36173125334` (USDJPY).
- R2-CF strictly nested results report from run `38442593863`, one artifact per market.
- Read-only GitHub Actions artifact download, SHA256 provenance, no cTrader account permission.
- Fully replay the existing R2-CF initial/second decision machinery **unchanged** for diagnostic instrumentation only; compare per-year and full-population counts, PF, gross R, DD, OOS positive years and cost stress with frozen R2-CF report. Any mismatch = hard failure, no interpretation.

## Prespecified attribution

For every OOS original candidate: INITIAL_EXECUTE, INITIAL_ABSTAIN or INITIAL_WAIT. A WAIT must be terminal (structural stop / destination consumed / C3 expiry / missing data) or viable for next-M15 second decision. For each viable WAIT compare R2-CF CONTROL_ALL with STRICT_NESTED_WAIT_4Y, with transitions:

- BOTH_EXECUTE; NESTED_ONLY_EXECUTE; CONTROL_ONLY_EXECUTE; NEITHER_EXECUTE.
- Within each, record original frozen delayed-entry gross R and 0.02/0.05R stress as **conditional retrospective attribution**, not a promoted rule.
- Produce full 5-bucket first-M15 state × decision transition tables, and separate knowledge state (`KNOWN/PARTIAL/UNKNOWN/CONFLICTED`), support n, Expected-R and DOA from strictly prior-only memory. Aggregate counts and sums per fold and whole sample.
- For bad-year comparisons, show fold delta nested-versus-control as the exact R contribution of NESTED_ONLY_EXECUTE minus CONTROL_ONLY_EXECUTE. Assert reconciliation. No causal claim merely because losses occur in an identified subgroup.

## Capacity definition

For each market/outer year, `upper_bound = INITIAL_EXECUTE + ALL_VIABLE_INITIAL_WAIT`, a purely **arithmetic ceiling** on frozen source hypotheses; terminal WAIT and ABSTAIN excluded. Compare to 170 trades/year historical research floor.

Also report `unselected_viable = ALL_VIABLE_WAIT - NESTED_DELAYED_EXECUTE`, `needed_to_170 = max(0, 170*OOS_year_count - R2CF_trades)`, and all WAIT terminal causes. This ceiling does **not** account for concurrent hypotheses, execution competition, slippage, changing economics, or partial recovery of downstream events. No entry rule follows from it.

## Boundaries

- Pure original CRT and cognitive contracts, one M15 WAIT only; original structural stop, recalculated 1.5R, original C3 expiry, M15 STOP_FIRST; AUDUSD BE_CLOSE_075, USDJPY CONTROL.
- Prior-only nested training, 4Y warmup, minimum cell support 30, prior strength 100, market memories isolated.
- Costs reported as fixed R/trade scenarios only, never trader sizing/volume/leverage/capital assignment.
- No outcome-aware filtering, no fresh holdout consumed, no merge/VPS/DEMO/LIVE/production/real funds.
- If the data support only an upper bound and a failure attribution, classify economic edge `NO_SUPPORT` / insufficient, not `FALSIFIED FOREVER`.

## Mandatory output

Machine-readable full report + human-readable technical result after CI; original vs diagnostic checks, two bad years, per-state and per-action counters, and a clear next experiment recommendation **only if mechanisms justify one**.
