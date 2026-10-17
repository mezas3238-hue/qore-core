# VT08 CRT PURE — R2-CH archived independent-source novelty census FREEZE

**Date:** 2026-10-13. **PR #626**. **Status:** research-only, capacity only, NO rule promotion.

## Rationale

R2-CG proved arithmetic upper ceilings under the *existing one-step WAIT* population only: AUDUSD 151.91/year; USDJPY 120.875/year. Both are below the historical research density floor 170/year. Therefore second-WAIT tuning alone cannot reach the floor, and resuscitating ABSTAIN is prohibited. R2-F has previously demonstrated multiple **causally distinct source events** within one parent CRT (not entry permission). Investigate whether a bounded new-source frontier exists.

## Frozen evidence before inspection

1. Archived R2-F audited 2Y `hypotheses.jsonl` and `report.json`, GitHub Actions run **35811162435** and evidence commit `24c5d2b8cc4e9f15d42d4d5396e72997fc5af8e3`; **AUDUSD** and **USDJPY** only. DO NOT reopen BTCUSD.
2. Original AUDUSD R2-CC / USDJPY R2-CD `delayed.jsonl` and `report.json` from respectively **36173116494** and **36173125334**. Original ledger includes long historical spans; comparison MUST be explicitly scoped to R2-F's original 2Y evidence window `2024-09-21T00:00:00Z` to `2026-09-21T00:00:00Z`, and use C3 opening timestamps, not whole OOS fold years.
3. SHA256 source fingerprints in CI. Fail closed if original R2-F report counts do not match JSONL unique IDs/state counts; original source R2-CC/CD control report must be exact well-formed and keyed to correct market. No broker calls or permission escalation.

## Frozen join + uncertainty

- Deterministic structural match key: `(market, parent_c3_opened_at / original_trade.c3_opened_at, source_opened_at)`. R2-F authoritative `source_event_id` additionally includes sorted reference IDs. Original R2-CC/CD normalized execution ledger lacks the same R2-F hash and may use a different source candidate/competition policy. Therefore **an unmatched structural key is only an unmatched candidate**, NOT proof of a brand-new tradeable independent opportunity or proof the source was unseen by the cognitive architecture.
- Ambiguity: if two R2-F source rows have same structural match key but distinct reference identities, count **AMBIGUOUS** and EXCLUDE from unique-match classification rather than conflate. Duplicate R2-F source_event_id, hypothesis_id or ledger key fails closed.
- Exact old-control matched source keys are descriptive. Count R2-F later events `event_generation > 1`, that are body-confirmed with contiguous next M15 entry **slot** (`CONFIRMED_ENTRY_SLOT_AVAILABLE`), and structurally not matched to the original frozen execution ledger. Group by parent, year, generation and confirmation. Missing original record and source mismatch are not equivalent to unreached economic opportunities.
- Report unmatched *all states* vs unmatched *confirmed slot* separately; additional concurrency is not automatically executable.
- No extrapolation of two-year capacity to AUDUSD 11-year or USDJPY 8-year WFO; no summation with R2-CG counts. Distinguish populations/denominators.
- R2-F's old competition policy is marked OPEN. Do not present multiple source events as multiple entries; no trade simulation.

## Governance

No new trading rule, no economic outcome, no market order, no sizing, volume, leverage, portfolio allocation or capital management inside trader. No merge, VPS, DEMO, LIVE or production. Frozen BTCUSD market certification untouched. Candidate certification remains FALSE.

## Output

Machine-readable market reports with matched / unmatched / ambiguous structural keys, independent later confirmed slots, parent duplication and event-generation distributions, exact R2-F report reproduction. Any unresolvable mapping classified `BLOCKED_PARTIAL` and recorded; not silently treated as a unique alpha source.
