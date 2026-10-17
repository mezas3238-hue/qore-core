# VT08 CRT PURE — R2-CJ ROLLING-H4 HISTORICAL COST-MARGIN RECONCILIATION — FREEZE 001

**Date:** 2026-10-13 · **Repo/PR:** mezas3238-hue/qore-core / #626  
**Status:** preregistered before R2-CJ results · AUDUSD / USDJPY only · no new strategy · normalized R only

## Reason

Recent R2-CG established a **restricted R2-CF single-WAIT capacity** ceiling of 151.91 AUDUSD and 120.875 USDJPY trades/year, below the 170/year research floor. This must NOT be misread as a universal CRT capacity limitation. Earlier, already frozen R2-AO rolling-H4 + R2-AQ historical-validation families delivered >240 trades/year for AUDUSD and USDJPY by observing six H4 triplet starts/day rather than two. Older R2-AQ and recent R2-AO used the same Model #1 source/NEWEST/one selected hypothesis per parent, structural stop and fixed 1.5R objective. Source direct: docs/research/VT08-CRT-PURE-HIGH-DENSITY-CORE-001.md and VT08-CRT-PURE-HIGH-DENSITY-HISTORICAL-VALIDATION-001.md. **Source authority:** Owner's 2026-09-22 OWNER-ENGINEERING-RESOLUTION-DIRECTIVE explicitly permits controlled empirical resolution of implementation ambiguity. Primary RomeoTPT material remains the canonical strategic identity, while a rolling-lattice choice is an engineering research policy; no literal original-source rule is required to audit this already exercised policy. This is NOT a license to merge or trade.

## Frozen original evidence — no external data retrieval

- AUDUSD and USDJPY archived **R2-AO recent development 2020-09-21 to 2026-09-21**, run `35863768335`, original per-market `report.json` plus `trades.jsonl` (multiple target arms: **select exactly FIXED_1_5R**).
- AUDUSD and USDJPY archived **R2-AQ earlier 2016-09-21 to 2020-09-21 AUDUSD; 2014-09-21 to 2020-09-21 USDJPY**, run `35865028789`, original market `report.json` plus `trades.jsonl`.
- SHA256 of all four original artifacts per market, output in CI. GitHub actions:read only. No cTrader credentials, market data access, or background live simulation.
- Validate archived market and methodology identities; normalized UTC entry times within correct date windows; disjoint older/newer windows; R2-AO target arm exactly FIXED_1_5R; R2-AQ preselected FIXED_1_5R contract. Reconcile **trade count, total R, PF** and annual fold count and total R to each archived report within 1e-6. Any mismatch => FAIL CLOSED; do not report partially reconstructed statistics.

## Predeclared measures (diagnostics, NOT new strategy)

1. Separate AUDUSD and USDJPY: pooled full older+newer historical trade ledger sorted chronologically, gross trades/R/PF, **global chronological max DD R**, fold/year metrics, positive gross years; any duplicate of `market+entry+source+C3` fail closed.
2. Frozen cost stress **0R / 0.005R / 0.01R / 0.02R / 0.05R per trade**, applied as additive normalized R cost to *every* trade, no sizing/volume. Report net R, net PF, net mean R, chronological max DD and positive annual windows. Historical results are **modelled costs**; actual bid/ask, commissions, slippage and fillability are not independently verified.
3. Compute exact **gross break-even cost per trade = gross total R / trades**; report as arithmetic mean, not executable cost allowance or robustness proof.
4. Compare 170/year research density floor to actual per-market average and every annual fold. Show counterfactual capacity vs economic evidence without mixing restricted R2-CF as identical sampling frame.
5. As a guard against over-claiming, compare only from historical artifacts; do not tune parameters, rescue PF, modify entry rules, select best cost after looking, run trading simulation, leverage, sizing, capital/risk, VPS, LIVE/DEMO or merge. BTCUSD research certification untouched.

## Explicit pre-results decision standard

`CAPACITY_CONFIRMED` if >170 trades/year over combined audited history; `ECONOMICALLY_UNSUPPORTED_AT_COST_C` if net <=0 or PF <=1 after prescribed cost C; `ECONOMICALLY_FRAGILE` if gross mean R <0.02R or fewer than 70% net-positive annual folds at cost 0.02R. **No automatic promotion from passing these checks**. Full certification requires new held-out evaluation and stronger loss robustness.

Deliverables: auditable Python archival runner, focused CI unit tests and read-only parallel AUDUSD/USDJPY workflow, detailed result report, PR #626 continuity amendment. Frozen models R2-AO and R2-AQ and their historical results MUST remain unchanged.
