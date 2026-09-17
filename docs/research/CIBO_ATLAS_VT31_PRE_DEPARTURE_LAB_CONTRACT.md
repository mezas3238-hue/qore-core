# CIBO Atlas — VT-31 Pre-Departure Structure & Timing Lab Contract

Status: research-only / consumed evidence only / `NO_R9_NOT_CERTIFIED`.

## Question

Before price completes the AM Silver Bullet move toward the opposite frozen 09:00 boundary, **where does price make its last meaningful reaction and at what New York time does that reaction occur?**

The laboratory must answer this independently for NAS100, SP500 and US30.

## Market-path origin

CIBO Atlas is independent from trader acceptance. The path begins at the **first directional breach** of the frozen 09:00–10:00 reference range. A later sweep of the opposite side does not invalidate the market observation even if the trader methodology would abstain after both sides are swept.

A same-M1 breach of both sides is ambiguous and is never assigned a direction.

## Source objective

The destination is the first subsequent hit of the opposite frozen 09:00 reference boundary, observed through the consumed lifecycle available to 16:00 New York.

## Pre-departure pivot

The primary pivot is the **last confirmed 2x2 M1 swing between the first directional breach and the source objective that is not subsequently broken before that objective**.

If no such confirmed swing exists, Atlas records the path extreme as an explicit fallback. The pivot method is retained on every row.

This pivot is a diagnostic label derived from the completed consumed path. It can never be used directly as a live/pre-entry feature.

## Structure labels at the pivot

Atlas records a multi-label signature rather than forcing one winner:

- Breaker zone touch — frozen VT-31 source formalization;
- Order Block zone touch — frozen VT-31 source formalization;
- Fair Value Gap touch — frozen VT-31 source formalization;
- reference-liquidity sweep and reclaim;
- local-liquidity sweep and reclaim;
- combinations of the above;
- `none-recognized` when no frozen structure explains the pivot.

The lab must preserve both the structures available before the pivot and the structures actually touched by the pivot.

## Timing labels

All time statistics use **America/New_York, DST-aware**.

For every pre-departure pivot Atlas records:

- exact M1 opening timestamp;
- minute from 10:00 New York;
- hour distribution;
- 30-minute arrival bucket;
- 15-minute arrival bucket;
- 5-minute arrival bucket;
- P25 / P50 / P75 arrival time;
- first opposite-boundary objective timestamp;
- elapsed minutes from pivot to objective.

These buckets are reporting bins only. They are **not trading cutoffs** and cannot be promoted to specialist rules without a causal, pre-entry formulation and leakage-free WFO.

## Required comparisons

Statistics must be produced for:

1. the independent consumed market baseline;
2. NAS100 / SP500 / US30 separately;
3. LONG / SHORT separately;
4. each structure signature;
5. each source family touched;
6. the 163 already-demonstrated `exit-before-eventual-source-objective` stop cases;
7. initial-stop vs protected-stop within those demonstrated cases.

The next stage must join these results to trader telemetry so we can answer whether each specialist tends to enter **before**, **at**, or **after** the market's recurrent pre-departure reaction geometry.

## Governance

- consumed evidence only;
- no fresh holdout opened;
- no automatic parameter mutation;
- no market selection or deletion;
- no R9 promotion from descriptive frequencies;
- no live or production authority;
- market-specific repair hypotheses only after causal validation.
