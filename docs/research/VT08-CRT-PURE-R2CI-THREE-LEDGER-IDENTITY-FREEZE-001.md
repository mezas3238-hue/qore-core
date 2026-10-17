# VT08 CRT PURE — R2-CI three-ledger source equivalence and already-tested audit — FREEZE 001

**Date:** 2026-10-13 · **Scope:** AUDUSD, USDJPY; 2024-09-21 to 2026-09-21 · **PR:** #626 · **Research-only**.

## Why necessary

R2-CH found **43 AUDUSD** and **32 USDJPY** *later-confirmed R2-F events* that are structurally unmatched in the long-history R2-CC/CD selected trade ledgers. This is NOT yet new economic opportunity: a subsequent, already completed R2-G experiment explicitly considered competing later sources in the same parent C3, with frozen policy `NEWEST_SUPERSEDES_CONFIRMATION_FIRST` and at most ONE trade attempt per parent. It is therefore essential to determine which R2-CH apparent novel events are **already evaluated** under R2-G, before claiming new density potential or creating a new model.

## Original evidence (read-only, no provider calls)

- Frozen R2-F 2Y `hypotheses.jsonl` and `report.json`, run `35811162435`.
- Frozen R2-G 2Y `trades.jsonl` and `report.json`, run `35811391351`.
- Frozen R2-CC AUDUSD / R2-CD USDJPY `delayed.jsonl`, runs `36173116494` / `36173125334`.
- R2-F source keys: `(market, parent C3 timestamp, source timestamp, sorted source_reference_ids)`. R2-G selected trade keys use same market/C3/source + sorted `reference_ids`; strict exact reference-ID match required for "already evaluated R2-G" assertion. If refs or timestamp differ, classify PARTIAL/UNMATCHED not silently matched. Original R2-CC/CD structural match remains **3-component only** for same comparison definition as R2-CH.
- R2-G original report and per-policy trade counts must reconcile exactly, especially `NEWEST_SUPERSEDES_CONFIRMATION_FIRST`. One trade max per parent; all events available only after causal source/confirmation close. Other R2-G policy arms are separate diagnostics; no summing them as separate trades.

## Predeclared outputs

For each market, reproduce R2-CH count `later confirmed structurally unmatched with original = 43 / 32` as an integrity check. Within those, count:
1. exact event selected by R2-G frozen NEWEST policy,
2. exact event selected by another R2-G policy but not NEWEST (informational),
3. not selected by any R2-G policy,
4. ambiguous / unknown mapping. All groups mutually exclusive.
Also report R2-G NEWEST selected source events that cannot be matched EXACTLY to R2-F source identity, by reason (missing match vs reference mismatch), and the combined R2-G two-year PF/R from its original archived report AS HISTORICAL CONTEXT ONLY, without recomputing PnL.

Strictly no conversion of events to additional trades; R2-G has already shown competition-only insufficient for quality. Structural uniqueness and old "policy open" in R2-F do not overrule later R2-G frozen competition research and market identity.

## Invariants

- No new source selection, new entries, sizing, volume, leverage, allocation, costs, risk or future outcome use.
- No post-hoc action promotion, no ABSTAIN resurrection, no multiple entries per C3.
- Strict 2Y provenance; do not extrapolate to 11Y AUDUSD / 8Y USDJPY capacity.
- Missing exact reference ID = PARTIAL, not economic novelty.
- BTCUSD R3 frozen, no merge, VPS, DEMO, LIVE or production.
