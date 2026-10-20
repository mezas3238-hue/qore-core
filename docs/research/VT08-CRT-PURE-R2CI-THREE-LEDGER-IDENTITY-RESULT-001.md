# VT08 CRT PURE — R2-CI THREE LEDGER EXACT SOURCE IDENTITY — RESULTS

**Date:** 2026-10-13. **Status:** CHARACTERIZATION COMPLETE / NO AUTOMATIC NEW TRADES.  
**Preregistered freeze:** `docs/research/VT08-CRT-PURE-R2CI-THREE-LEDGER-IDENTITY-FREEZE-001.md`.  
**CI:** [run 38448705957](https://github.com/mezas3238-hue/qore-core/actions/runs/38448705957), quality GREEN, AUDUSD GREEN, USDJPY GREEN.  
**Evidence:** original R2-F run `35811162435`, original R2-G run `35811391351`, original R2-CC/CD runs `36173116494`/`36173125334`. Immutable artifacts, checksum provenance, all original report and per-policy R2-G execution counts reproduced; no new prices or trades.

## 1. Problem solved

R2-CH marked 43 AUDUSD and 32 USDJPY later-confirmed R2-F sources *structurally unmatched* in the original selected CRT ledger (2Y scope only). However R2-G *later than R2-F* had already frozen a same-parent `NEWEST_SUPERSEDES_CONFIRMATION_FIRST` policy with **maximum one trade attempt per C3 parent**, and also independently evaluated other policy arms.

R2-CI performs strict source identity matching across all three historical ledgers by **market + parent C3 opening time + source M15 opening time + exact sorted reference IDs**. It does not conflate separate reference groups, does not infer a new trade from a new source, and does not authorize PnL/methodology changes.

## 2. Exact cross-ledger adjudication

| R2-F later confirmed source events unmatched by original selected structural key | AUDUSD | USDJPY |
|---|---:|---:|
| R2-CH numerator reproduced exactly | **43** | **32** |
| Exact R2-G NEWEST-selected source event | **0** | **0** |
| Exact source selected by OTHER archived R2-G policy only | **4** | **4** |
| Exact source NOT SELECTED by ANY archived R2-G policy | **39** | **28** |
| Ambiguous reference-ID mismatch or partial R2-G mapping | **0** | **0** |
| Parents containing other-policy-only sources | 4 | 4 |
| Parents containing not-selected sources | 31 | 21 |

All 43/32 counts reconciled with R2-CH. All R2-G selected-trade rows mapped to an exact R2-F source ID (no unmatched R2-G selected rows due source/reference mismatch): AUDUSD 411 source-policy row matches over its four arms, USDJPY 377.

**Why "not selected by any policy" is not a newly eligible independent trade:** selection in R2-G was explicitly competition among many source hypotheses WITH one attempt per parent. The other source might have won, an entry slot could have been consumed, and risk geometry could fail. Lack of selection is not evidence the market omitted a lawful executable entry.

## 3. R2-G historical economic context — NOT equivalent to current R2-CF/R2-CC/CD

Original **NEWEST_SUPERSEDES_CONFIRMATION_FIRST** R2-G two-year results:

- AUDUSD: 114 trades, PF **0.97640734**, **-0.99985228R**, max DD 9.68734541R.
- USDJPY: 104 trades, PF **1.11385968**, **+4.16034174R**, max DD 12.32148922R; year 2 already negative (-0.59139120R).
- This older R2-G used a C1-midpoint target control while R2-CC/CD use a fixed 1.5R delayed-entry research line. **Do NOT transplant R2-G profitability or infer economic advantage from its 2Y numbers.** Its relevance here is source identity and same-parent competition already tested under other economics.

## 4. Key status correction: R2-F competition OPEN was historical, not current

R2-F originally had `competition_policy_frozen=false`. That is a status **at the R2-F checkpoint**. Subsequent R2-G explicitly froze the base `NEWEST_SUPERSEDES_CONFIRMATION_FIRST` for later Model #1 research. Do not interpret older R2-F "OPEN" as a current permission for additional entries.

The freeze is **research methodology**, not owner authorization to break the one-trade-per-parent exposure/control seam, and the R2-G historical variants were not strong enough alone to certify an economic edge.

## 5. Scientific conclusion

The initially promising 43/32 apparent source additions were **not overlooked NEWEST winners**. They are other-policy sources (4+4) or outside all four evaluated R2-G winning selections (39+28). Therefore the simplistic "include missed later sources" fix would mutate hypothesis competition, and may violate the existing one-attempt-per-C3 contract.

Combined with R2-CG's strict one-WAIT capacity ceiling:
- AUDUSD 151.91/year arithmetic ceiling vs 170 goal.
- USDJPY 120.875/year arithmetic ceiling vs 170 goal.
- Current USDJPY R2-CF PF 0.99649 (before friction), AUDUSD thin after 0.02R and negative after 0.05R.

**R2-CI decision:** NO_PROMOTION, no automatically executable new population and no new positive PnL established. The scientific evidence supports looking outside the presently frozen one-source-selection-plus-one-WAIT space **only after a separately source-authorized, preregistered new methodology/hypothesis generation contract**, not repeating old policy arms or relaxing cognition.

## 6. Next research boundary

1. Audit original RomeoTPT source authorization versus engineering `one selected hypothesis per parent` and `NEWEST_SUPERSEDES_CONFIRMATION_FIRST`: record unambiguously which constraints are user/source-authorized, which are historical experiment assumptions, and what would constitute a genuinely new source event after terminality without ABSTAIN resurrection.
2. Audit exact economic execution eligibility for any **new independently identified parent/source population**, while preserving separate CIBO sizing authority.
3. Without a lawful, causal new source contract and new unconsumed historical evidence, classify this research branch **NO_SUPPORT for density/edge under its current search space**, not `CERTIFIED` or `impossible forever`.
4. BTCUSD frozen market research certification remains intact. No merge, VPS, DEMO, LIVE, production or real capital. Trader may not size lots/volume/leverage/portfolio risk.

**R2-CI is identity/governance evidence, not a profitable strategy test.**
