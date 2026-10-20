# VT08 CRT PURE — R2-CG WAIT frontier & bad-fold attribution — results

**Date:** 2026-10-13  
**Status:** TECHNICALLY VERIFIED / DIAGNOSTIC CLOSED / NO CANDIDATE PROMOTION  
**Frozen protocol:** [R2-CG freeze](VT08-CRT-PURE-R2CG-FAILURE-ATTRIBUTION-WAIT-CAPACITY-FREEZE-001.md)  
**Authoritative GitHub Actions:** [run 38446929784](https://github.com/mezas3238-hue/qore-core/actions/runs/38446929784): quality SUCCESS, AUDUSD forensics SUCCESS, USDJPY forensics SUCCESS. An earlier R2-CG run 38446717520 already succeeded on the core diagnostics; the follow-up run adds the preregistered outcome attribution by first-M15 state.  
**Inputs:** read-only original R2-CC/CD frozen delayed ledgers and reports, plus original R2-CF result report; SHA256 and per-fold source-report reproduction recorded in artifacts. No cTrader account connection and no execution.

## 1. Crucial structural finding — 170/year cannot be reached under the frozen single-WAIT opportunities

This is an upper bound, NOT a profitable or simultaneously executable strategy. Counts rely on one original hypothesis per frozen opportunity; all initial ABSTAIN and all structurally terminal WAIT are excluded.

| Metric | AUDUSD (11 OOS years) | USDJPY (8 OOS years) |
|---|---:|---:|
| R2-CF actual original EXECUTE | 815 | 432 |
| R2-CF actual delayed WAIT EXECUTE | 365 | 132 |
| R2-CF **total** executed | 1,180 | 564 |
| R2-CF density/year | 107.27 | 70.50 |
| All **viable** one-M15 WAIT opportunities | 856 | 535 |
| Viable WAIT not yet executed | 491 | 403 |
| Absolute arithmetic ceiling trades | 1,671 | 967 |
| **Absolute ceiling/year** | **151.91** | **120.875** |
| Floor 170/year would require trades | 1,870 | 1,360 |
| Gap from current execution to floor | 690 | 796 |
| Even all 1-M15 WAIT viable? | **No: 199 trades short** | **No: 393 trades short** |

**Research decision:** moving the second WAIT decision threshold, adding a state, or treating all remaining viable WAIT as EXECUTE cannot reach the historic 170/year density goal, **even if every available WAIT were profitable**. Therefore repeating second-WAIT tuning is not a sufficient path to certifiability. ABSTAIN cannot be resurrected.

This does not prove CRT PURE could never have enough density: independent new source events/new hypotheses or a different preregistered opportunity-generation research identity are outside the frozen one-WAIT census and require separate causal verification.

## 2. AUDUSD 2016: underpowered historical journal drops positive cases, not new toxicity

R2-CF versus original CONTROL_ALL gross R: **-10.96495970R**, exact matched by per-transaction replay.

- OOS candidate count: 260; initial EXECUTE 106, WAIT 108, ABSTAIN 46.
- Terminal WAIT: stop touched 11; C3 expired 10; original target consumed 1. Viable for second action: 86.
- CONTROL_ALL second EXECUTE: 48. STRICT_NESTED second EXECUTE: **0**. The strict journal has only earlier partial history here (WARMUP_EXCLUDED 733 training rows), with inadequate supported favorable cells; the favorable original cases become UNKNOWN and remain WAIT.
- The 48 **CONTROL_ONLY_EXECUTE** delayed trades have frozen retrospective economic total **+10.96495970R**. Removing them explains *all* the model delta, without relying on a price-based after-the-fact filter.
- Their positive contribution by first-M15 state: `CLOSE_025_TO_050R` 11 trades **+5.25326120R**; `CLOSE_0_TO_025R` 23 **+2.54888125R**; `CLOSE_GE_050R` 14 **+3.16281725R**. All are classified `UNKNOWN` by strict historical memory.
- Other 38 viable WAIT are non-executed in both models and retrospectively total -7.21370374R. These are *diagnostic attribution only*, not an admissible PnL claim.

**Cause under frozen rules:** lack of support for favorable journey cells under strict 4Y warmup produces lost opportunities. DO NOT loosen warmup/min_support or fill historical data using future outcomes to rescue 2016; that would undo R2-CF's causal integrity.

## 3. USDJPY 2023: strictly nested journal admits losing early trajectory as KNOWN

R2-CF versus original CONTROL_ALL gross R: **-9.83056095R**, exactly reconciled.

- OOS candidate count: 245; initial EXECUTE 56, WAIT 69, ABSTAIN 120.
- Terminal WAIT: C3 expired 4; structural stop 2. Viable WAIT: 63.
- Original control second EXECUTE 3, STRICT_NESTED second EXECUTE **42**. Transitions: 42 NESTED_ONLY_EXECUTE, 3 CONTROL_ONLY_EXECUTE, 18 NEITHER_EXECUTE.
- 42 NESTED_ONLY_EXECUTE generated **-8.22413807R** total. Lost 3 CONTROL_ONLY_EXECUTE contributed an additional opportunity-cost delta of **-1.60642288R**. Exactly -9.83056095R.
- The 42 nested-only split: 27 trades `CLOSE_NEG_050_TO_0R | KNOWN | WAIT->EXECUTE` with frozen delayed result **-8.50289355R**; 15 `CLOSE_0_TO_025R | KNOWN | WAIT->EXECUTE` total **+0.27875548R**, already slightly negative at 0.02R/trade.
- The control-only 3 are `CLOSE_GE_050R | UNKNOWN | EXECUTE->WAIT`, +1.60642288R.
- Another 9 `CLOSE_LT_NEG_050R | UNKNOWN | ABSTAIN->WAIT` remain unexecuted in both; no resurrection.

**Cause under frozen rules:** prior-window Journey Memory made a negative early-M15 trajectory `KNOWN` and authorized some economically poor delayed entries in USDJPY's 2023 fold. This is *model generalization failure*, not license to ban the bucket post hoc. The retrospective 2023 attribution cannot become a filter without new preregistration and independent evidence.

## 4. Whole-population transition checks

| Metric | AUDUSD | USDJPY |
|---|---:|---:|
| Both models delayed EXECUTE | 122 | 14 |
| CONTROL_ONLY delayed EXECUTE | 130 | 65 |
| STRICT_NESTED_ONLY delayed EXECUTE | 243 | 118 |
| Neither delayed EXECUTE | 361 | 338 |
| All viable WAIT accounted | 856 | 535 |
| CONTROL_ONLY retrospective R | +13.22739416R | -0.92769139R |
| NESTED_ONLY retrospective R | +16.18751211R | -3.94975081R |

Exact frozen R2-CF metrics were reproduced **for each fold and pooled**, including trade count, origin mix, normalized R, PF, DD, DOA and 0.02/0.05R stress. Transition gain/loss difference equals total R2-CF-vs-CONTROL_ALL difference. All unknown support and market-specific states are recorded in artifact report JSON.

## 5. Scientific verdict

**R2-CG: PASS as diagnostic, NO_SUPPORT for using only the frozen single-WAIT population to achieve >=170/year.** No new trading edge discovered or certification granted.

This conclusion is conditional on:
- the actual frozen R2-CC/CD original opportunities,
- the one-M15 WAIT lifecycle,
- unchanged initial ABSTAIN terminal semantics,
- unchanged CRT strategy definition,
- historical research density threshold 170 trades/year.

R2-CG does NOT show whether a causal *new-source-event* stream is dense, distinct, executable, or profitable. Source-event overlap/concurrency can reduce true realizable capacity below this arithmetic ceiling.

BTCUSD frozen market-research certification untouched. No new provider data or fresh holdout used.

## 6. Required next work — new unique opportunity, not more WAIT tuning

1. Before any new model proposal, audit the existing R2-F multi-source/multi-hypothesis ledger: count truly independent causal source events and parent windows *not already represented in R2-CC/CD* by market, identity, timestamp and generation. This is **capacity only**.
2. Respect source identity/generation and original C3 boundaries; no fallback after ABSTAIN on the same source event and no duplicate outcome entries.
3. If a novel independent source population exists, preregister one non-mutating census and then a separately preregistered economic replay with existing cognition, stop/target/cost contract and honest competition rules; do not tune on negative 2016/2023 examples.
4. If independent source capacity is unavailable or insufficient, declare this research branch `NO_SUPPORT` for density without pretending methodology is inherently impossible.
5. Any **new** profitability claims still need broker-cost realism, robust PF margin, chronological WFO, independence, fresh holdout, certification gates and explicit Owner authorization for anything beyond research.
6. No sizing, volume, capital allocation, leverage, VPS, DEMO, LIVE, production or merge.

**Source of truth:** PR #626 DRAFT / unmerged, this freeze/results and the GitHub Actions run artifacts.
