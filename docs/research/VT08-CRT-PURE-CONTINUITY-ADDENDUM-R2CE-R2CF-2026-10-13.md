# VT08 CRT PURE — CONTINUITY ADDENDUM — R2-CE / R2-CF (2026-10-13)

**Read alongside the frozen [master handoff](VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md).** This addendum supersedes its "latest research run R2-CD" marker only; it does not rewrite earlier historical findings or freeze BTCUSD.  
**Repo:** `mezas3238-hue/qore-core`  
**PR:** [#626](https://github.com/mezas3238-hue/qore-core/pull/626), OPEN / DRAFT / UNMERGED / MERGEABLE at this checkpoint.  
**Branch:** `agent/vt08-crt-pure-source-identity-001`.  
**Pre-addendum checkpoint:** `d4b268717a7a87d93b765998eae804185a1dfc1b`.

## 1. Mandate / architecture retained

VT08 CRT PURE remains exactly AUDUSD, USDJPY, BTCUSD with frozen CRT Model #1 identity. H4 CRT / M15 implementation, original C3 expiry, same-M15 STOP_FIRST, 1.5R target; AUDUSD BE_CLOSE_075, USDJPY CONTROL; initial cognitive EXECUTE/WAIT/ABSTAIN. ABSTAIN is terminal for the source event. No fallback after ABSTAIN. All research normalized to R, no trading quantity authority.

**SIZING, VOLUME, LEVERAGE, ACCOUNT ALLOCATION, PORTFOLIO RISK BUDGET are forbidden inside VT08.** CIBO/QORE controls remain external. No merge, VPS, DEMO, LIVE, production or real capital. The user authorized research continuation only.

## 2. Work performed in this continuation

1. Read and verified master handoff and PR #626 from GitHub.
2. Reviewed R2-CC/R2-CD code, WAIT Journey freeze, cognitive and replay engine interfaces.
3. Found cohort mismatch: Journey Experience training from ALL viable delayed prior-4Y historical trades, versus deployment of the second decision ONLY for initial WAIT.
4. Before outcomes, preregistered **R2-CE** CONTROL_ALL vs WAIT_ALIGNED_DIAGNOSTIC. Kept original R2-CC/R2-CD unchanged. Built the analyzer, fail-closed hypothesis keys, accounting and comparison, and 5 focused unit tests.
5. CI initially showed lint/mypy problems; fixed them. Historical replay initially blocked because cTrader account discovery would require an unavailable trading permission. **No permission escalation** was sought. Reused the frozen original R2-CC / R2-CD `delayed.jsonl` and `report.json` using GitHub Actions `actions:read` and logged SHA256; fail-closed exact reproduction checks verify R, PF, count, DD, DOA and origin counts.
6. R2-CE [run 38441743755](https://github.com/mezas3238-hue/qore-core/actions/runs/38441743755) fully GREEN, outputs published and analyzed. More density and positive modeled 0.02R R in both, BUT historical TRAIN WAIT membership was generated from the **same 4Y initial model** trained on those years — NOT an online historical journal.
7. Preregistered **R2-CF**, strictly prior-only 4Y inner history for each TRAIN year's WAIT label. Missing full warmup excluded (no silent carry-forward). Built independent code and 4 additional unit tests, GitHub read-only workflow and exact controls.
8. R2-CF [run 38442593863](https://github.com/mezas3238-hue/qore-core/actions/runs/38442593863) fully GREEN, showing R2-CE USDJPY gain does **NOT** survive strictly chronological training, and AUDUSD margins remain thin.
9. Published both results docs; registered findings in PR #626 comments. Confirmed PR stays draft/unmerged.

## 3. Authoritative results / red flags

### AUDUSD

| Status | R2-CC original | R2-CE exploratory | R2-CF strictly nested |
|---|---:|---:|---:|
| Trades / year | 97 | 112 | 107.27 |
| Gross PF | 1.07424 | 1.08351 | 1.07340 |
| Gross R | +28.14R | +36.44R | +31.10R |
| Gross DD | 17.01R | 19.49R | 18.38R |
| Net R with 0.02R cost/trade | +6.80R | +11.80R | +7.50R |
| Net R with 0.05R cost/trade | -25.21R | -25.16R | -27.90R |

R2-CF positive OOS fold count 8/11. Marginal expectancy remains extremely small; DD/DOA worsen vs original; **density floor >=170/year FAIL**.

### USDJPY

| Status | R2-CD original | R2-CE exploratory | R2-CF strictly nested |
|---|---:|---:|---:|
| Trades / year | 63.875 | 75 | 70.5 |
| Gross PF | 1.01154 | 1.10978 | **0.99649** |
| Gross R | +2.26R | +25.22R | **-0.76R** |
| Gross DD | 15.16R | 18.95R | 22.80R |
| Net R with 0.02R cost/trade | -7.96R | +13.22R | **-12.04R** |
| Net R with 0.05R cost/trade | -23.29R | -4.78R | **-28.96R** |

R2-CF positive OOS years 4/8. USDJPY 2023 (R2-CF -12.31R vs original -2.48R) is material. **Economic NO_SUPPORT under strict nested selection; cannot promote.**

### Governance / final verdict

- Technical replay/reproduction: SUCCESS.
- Nested chronological boundary: SUCCESS for the implemented historical-label contract.
- AUDUSD: still weak at thin cost, inadequate density, no robust candidate.
- USDJPY: original and nested fail cost tolerance; cannot claim economically defensible edge.
- BTCUSD: **market research certified only**, frozen, not reopened.
- Global trader: **NOT CERTIFIED**; no gate bypass.

## 4. Repository deliverables

- [R2-CE freeze](VT08-CRT-PURE-R2CE-WAIT-COHORT-ALIGNMENT-FREEZE-001.md)
- [R2-CE result](VT08-CRT-PURE-R2CE-WAIT-COHORT-ALIGNMENT-RESULT-001.md)
- [R2-CF freeze](VT08-CRT-PURE-R2CF-STRICT-NESTED-WAIT-JOURNAL-FREEZE-001.md)
- [R2-CF result](VT08-CRT-PURE-R2CF-STRICT-NESTED-WAIT-JOURNAL-RESULT-001.md)
- `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2ce_wait_cohort_alignment.py`
- `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2cf_strict_nested_wait_journal.py`
- `tests/infrastructure/trader_lab/test_vt08_crt_pure_r2ce_wait_cohort_alignment.py`
- `tests/infrastructure/trader_lab/test_vt08_crt_pure_r2cf_strict_nested_wait_journal.py`
- `.github/workflows/vt08-crt-pure-r2ce-wait-cohort-audit.yml`
- `.github/workflows/vt08-crt-pure-r2cf-strict-nested-wait.yml`
- CI outputs include per-fold historical action counts, historical eligible/terminal WAIT, both model memory supports, second action counts, exact R/economics, original immutable evidence checksums.

## 5. Next architect instructions / MUST NOT fabricate edge

1. Read R2-CF original output `report.json` from both market artifacts, and analyze **specific failure folds** AUDUSD 2016 and USDJPY 2023 using chronological state support and action changes, but do not turn a losing year into an ex-post exclusion rule.
2. Attribution: `strict historical WAIT labels -> Journey cells/support -> KNOWN/CONFLICTED/PARTIAL/UNKNOWN -> second actions -> executed R`; compare with all-sample and exploratory models per fold. Explicitly report unsupported cells vs adverse EXECUTE outcomes.
3. Recompute **maximum feasible WAIT capacity** from the frozen ledger, excluding invalidated / consumed / expired / unfilled, before trying a new methodology. Confirm whether reaching 170/year is arithmetically achievable without ABSTAIN resurrection. Capacity is not evidence of profit.
4. Audit potential subtle accounting hazards: unique source-event identity, concurrent hypotheses and hypothesis competition, original-C3 cutoff, missing M15 handling, execution candle boundaries, STOP_FIRST and whether spread/slippage are adequately represented by fixed costs.
5. IF genuinely new **causal market information** survives mechanism diagnostics, preregister a SINGLE bounded test with separate prior-only learning and explicit loss/density/cost thresholds; do not reopen falsified generic filters (CISD/FVG/OTE rescue, passive retracements, broad Expected-R, tie-safe overlap) on hope alone.
6. Stop optimizing known history if further diagnostics show no viable density/edge; classify NO_SUPPORT or BLOCKED properly rather than calling it permanently falsified.
7. Once real candidate exists, independent data/provider/tick or BID/ASK evidence, cost stress, chronological robustness, WFO, Monte Carlo, fresh holdout, 3-market replay and complete QORE gates remain mandatory. This work did **NOT** conduct fresh holdout.
8. Keep BTCUSD frozen. Keep PR OPEN/DRAFT/UNMERGED. Do not grant VT08 sizing/volume and do not activate trading.

**Bottom line:** the most important new scientific result is the failure of USDJPY's apparently promising R2-CE gains under strict nested historical WAIT membership. This is a required negative result, not reason to silently loosen the causal boundary.
