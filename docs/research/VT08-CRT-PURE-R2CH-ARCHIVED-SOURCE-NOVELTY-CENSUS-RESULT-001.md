# VT08 CRT PURE — R2-CH ARCHIVED SOURCE NOVELTY — RESULTS 001

**Date:** 2026-10-13. **Status:** CHARACTERIZATION COMPLETE, NOT AN ECONOMIC CANDIDATE.  
**Freeze:** `docs/research/VT08-CRT-PURE-R2CH-ARCHIVED-SOURCE-NOVELTY-CENSUS-FREEZE-001.md`.  
**CI:** [GitHub Actions #38447732371](https://github.com/mezas3238-hue/qore-core/actions/runs/38447732371) — quality SUCCESS / AUDUSD SUCCESS / USDJPY SUCCESS.  
**Inputs:** archived R2-F run `35811162435`, frozen AUDUSD R2-CC `36173116494`, frozen USDJPY R2-CD `36173125334`. SHA256 provenance bound to each CI artifact, original archived R2-F event and state counts independently reproduced. No cTrader, trading API, fresh market data or capital authority.

## What was actually measured

Within the **R2-F-specific two-year historical window 2024-09-21 to 2026-09-21**, identify source events by R2-F audited source_event_id and test whether the source's **structural key** `market + parent C3 timestamp + source M15 timestamp` occurs in the original long-history R2-CC / R2-CD ledger. Exact R2-F reference-ID source identity is not present in the execution ledger, so **unmatched means no structural-key match, NOT verified novel executable signal**.

R2-F sources need an explicit causal body confirmation + contiguous next M15 slot to be labelled `CONFIRMED_ENTRY_SLOT_AVAILABLE`. This is a capacity observation only and does not grant entry authority.

## AUDUSD — original R2-F 2Y

| Census | Number |
|---|---:|
| Audited R2-F source events | 563 |
| Later source events (generation >1) | 325 |
| All confirmed contiguous-entry-slot source events | 217 |
| Later confirmed source events | 107 |
| Later confirmed matched to original structural key | 64 |
| **Later confirmed unmatched to original structural key** | **43** |
| Parent C3s with later confirmed unmatched key | **33** |
| Any source structural match | 156 |
| Any source structural unmatched | 407 |
| Source ledger original 2Y frozen selected records | 488 |
| Ambiguous R2-F structural join keys | 0 |

Note: 407 unmatched events includes unconfirmed / nonlater events, so cannot be used as a count of viable independent entries. Unique newly unmatched later-confirmed slots are at most **43 observations** inside the historical R2-F source construction, NOT guaranteed trades.

## USDJPY — original R2-F 2Y

| Census | Number |
|---|---:|
| Audited R2-F source events | 528 |
| Later source events (generation >1) | 305 |
| All confirmed contiguous-entry-slot source events | 191 |
| Later confirmed source events | 89 |
| Later confirmed matched to original structural key | 57 |
| **Later confirmed unmatched to original structural key** | **32** |
| Parent C3s with later confirmed unmatched key | **23** |
| Any source structural match | 139 |
| Any source structural unmatched | 389 |
| Source ledger original 2Y frozen selected records | 510 |
| Ambiguous R2-F structural join keys | 0 |

389 unmatched includes unconfirmed/no-entry cases and is not a capacity forecast.

## Interpretation vs R2-CG

R2-CG showed that the one-step WAIT frontiers are arithmetically capped below the 170/year density floor within their **11-year AUDUSD and 8-year USDJPY OOS evaluation**. R2-CH tests a DIFFERENT archived **2-year R2-F source construction** and cannot be added directly to those totals. Its 43/32 structurally unmatched later-confirmed slots support investigating **new source identities**, not a declaration that 170/year has been recovered.

Different source selection methods can explain why the old original ledger has 488/510 original records in the same two-year C3 scope but only 156/139 direct structural source matches to archived R2-F sources. This comparison is not a data-integrity failure: model lineage differs, and exact R2-F reference IDs are not the same available feature schema as the selected original ledger.

## Methodological hard blockers

1. Source-independent event is not yet proven to be an independent *entry*. R2-F `competition_policy_frozen=false`; simultaneous hypotheses can collide inside one C3.
2. Source identity must remain unique and learn memory separately per market; no fallback after ABSTAIN on the **same** source event.
3. Need explicit owner/source-derived authority for competition, selected generation and whether more than one hypothesis may execute in the same parent C3, rather than inventing executions from detected source multiplicity.
4. The 2Y subset is insufficient for an 11Y/8Y density or out-of-sample economic certification.
5. R2-CH contains **no PnL**, no normalized-R simulation, no cost/stress, no ML promotion and no fresh holdout. A source slot is not a fill.

## Next scientifically useful action

Write a separate preregistered **R2-CI source-identity causal-equivalence/competition audit** first: compare R2-F and selected-source lineage source by source, classify same parent C3 vs later independent source, prove when new hypotheses are actually known and distinct, enforce no overlapping accepted entry unless separately authorized. **Do not** run an economic replay until the competition contract can be sourced and frozen.

If the frozen original audited sources cannot be reconciled because differing source builder identity or reference IDs are absent, classify `BLOCKED_PARTIAL` and request explicit data/methodology authority, not a strategic rescue by post-hoc filtering.

BTCUSD market research certification remains frozen. No trader sizing, volume, risk budget, leverage, accounts, capital, merge, VPS, DEMO, LIVE or production.
