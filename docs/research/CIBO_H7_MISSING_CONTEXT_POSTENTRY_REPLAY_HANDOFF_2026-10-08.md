# CIBO H7 — Missing predecision M5 context: postentry ATTACK containment experiment

**Status: experiment committed, results NOT verified.** This is in-sample reuse of the historical 2019–2022 CIBO 3,368 trades, not certification and not approved for LIVE/DEMO.

## Source of causal hypothesis — H6 complete loss atlas

[H6 audit and all ten DD episodes](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-sovereign-dd-rootcause-h6-001/docs/research/CIBO_H6_SOVEREIGN_LEDGER_AND_MULTI_EPISODE_CAUSAL_ATLAS_2026-10-08.md).
Inputs: full historical manifest artifact **11389331836** and em-s06745 carrier artifact **11542321736**; verified archive SHA256 respectively `30177639f660c9647ab70257c2d12c541bdade49ab5582347a3890f920070fee`, `0e14d059be5053f453861ef02d119a7290d803d01ca3c74735a94e3a0f127d52`.

Join of 3,368 trades to 3,368 predecision source records:
- 675 ATTACK trades with `reg_m5_volatility_state`: gross profit USD1,585,365.78, gross loss USD873,608.59, PF~1.815.
- 185 ATTACK trades with that key **genuinely absent at decision**: gross profit USD26,408.41, gross loss USD65,264.26, PF~0.405, net −USD38,855.85.
- In DD episodes rank 3 and 4, missing-context ATTACK contributes ~−USD853.01 and ~−USD3,098.50, respectively.
- Descriptive, in-sample association; may reflect identity/data-coverage confounding. DO NOT use hindsight outcome, dates, symbols, fingerprint or trader ID as a condition.

## One opt-in source change (branch-local)

`scripts/cibo_trader_lab_three_mode_ceiling.py` now offers explicit matching for **absence at decision time**: `KEY=__MISSING__`. Added `_causal_context_matches()`; it matches absent key only, not a present literal "__MISSING__". Existing VALUE equality semantics unchanged. The new trigger selects a postentry stop only; no Trader entrance rejection, delay, suppression, or retroactive management. Position lifecycle still respects M5 closed-bar/next available executable event mechanics.

## Paired exact replay matrix

Workflow `.github/workflows/cibo-trader-lab-missing-context-h7.yml`, pinned and isolated branch `agent/cibo-missing-context-postentry-h7-001`.

- `h7-control-em-s06745`: exact verified em-s06745: capital USD673,146.52545398, DD36.91053924475%, gross loss USD940,435.76305544, ATTACK gross loss USD938,872.84954047.
- `h7-missing-stop050`: same configuration plus ATTACK context2 defensive initial stop −0.50R for genuinely missing `reg_m5_volatility_state`.
- `h7-missing-stop070`: same, −0.70R.
- `h7-missing-stop085`: same, −0.85R.

All four cases must produce EXACT 3,368 decision/trade receipts; `all_entries_preserved` TRUE, zero sizing rejected/deferred, zero ATTACK sovereign loss, and parity of frozen control capital/DD/gross losses. No promotion purely for lower gross loss or profitable subset. Read all JSON results, `attack_context_stop2_applied_count`, report winners forgone and net capital, DD, both gross losses, PF, all ten drawdown episodes and sovereign floor before any conclusion.

**Critical limitation:** rank1 max DD in 2019 consists of MEDIUM, not ATTACK. This H7 hypothesis alone is not expected to deliver global DD ≤25%. Next phase must separately and causally attack bootstrap MEDIUM with no wholesale winner deletion. Sovereign floor P0 from H6 also remains open until real ledger policy repair and full replay.

**Goal:** DD≤25% tolerable, ≤20% ideal, with capital floor >USD582,440.0253 and preservation of best economic frontier ~USD673k, no increased GL, all 3,368 entries retained. `STRICT_PARETO_CASES=[]` is failure, even if the GitHub job itself reports SUCCESS.
