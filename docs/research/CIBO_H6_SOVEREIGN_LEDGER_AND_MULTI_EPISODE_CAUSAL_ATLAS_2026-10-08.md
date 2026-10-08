# CIBO H6 — Root cause: sovereign bank + multi-episode DD loss atlas (2026-10-08)

**Status:** RESEARCH ONLY. **CIBO NOT CERTIFIED.** This is an exact audit of historical em-s06745 receipts, **not a new policy or DD improvement**. All interventions remain subject to causality, full 3,368 replay, gross-loss/PF/wealth and sovereign gates. Preserve all Trader entries; never veto, delay, cherry-pick, use hindsight date/trader/symbol or results to choose actions.

## Frozen evidence / provenance

- Repository `mezas3238-hue/qore-core`; isolated branch `agent/cibo-sovereign-dd-rootcause-h6-001`.
- Source full historical 3,368 manifest: artifact **11389331836**, archive SHA256 `30177639f660c9647ab70257c2d12c541bdade49ab5582347a3890f920070fee`; manifest SHA256 `76ffb7e1c72bf3c18e2fc7614007e8f2124463379acd185167cc5e46b8b2e669`.
- Full em-s06745 replay: successful [run 37759974174](https://github.com/mezas3238-hue/qore-core/actions/runs/37759974174), artifact **11542321736**, archive SHA256 `0e14d059be5053f453861ef02d119a7290d803d01ca3c74735a94e3a0f127d52`; exact internal member `em-s06745.json`.
- **3,368/3,368** settlements matched by `signal_fingerprint` to the 3,368 historical predecision rows. Fingerprint is join ID **only**, never eligibility criterion. In-sample 2019–2022 research, NOT sealed out-of-sample.
- New automated H6 forensic: `scripts/cibo_sovereign_dd_rootcause_h6.py`, workflow `.github/workflows/cibo-sovereign-dd-rootcause-h6.yml`. Note that em-s06745 uses `--summary-telemetry` and publishes 0 `epoch_receipts`; the H6 script explicitly reconciles the frozen ledger, uses receipt-order proxy for chronology, and MUST NOT mislabel missing snapshots as precise intratrade liquidity history.

## P0 finding: the sovereign floor breach is real in modeled accounting, NOT floating-point noise

Frozen ledger counters:
- Initial sovereign bank: **USD 60.00**.
- MEDIUM negative PnL debited to sovereign: **USD 1,565.637707386094960431165498**.
- MEDIUM recovery credits returned: **USD 1,458.911008589383575533887003**.
- MEDIUM ordinary distributable profit allocated directly to sovereign: **USD 0** due to 100% bootstrap cushion reinvestment.
- ATTACK sovereign overrun: **USD 0**.
- Reconciliation: **60 − 1,565.637707386094960431165498 + 1,458.911008589383575533887003 + 0 − 0 = −46.726698796711384897278495** (within ~6e−25 of reported, Decimal canonical precision differences).
- Reported ending sovereign bank **−USD 46.72669879671138489727849439**.
- Peak sovereign **~USD 60.00**, live defensive floor **~USD 30.00**, minimum bank **−USD 55.41649567391081325466487566**, hence **~USD 85.41649567391081325466487569** under the 50% bank floor. **This is a genuine shortfall in the modeled bank, not hidden ATTACK leakage.**
- Unrecovered MEDIUM deficit at end **USD 106.7266987967113848972784943**; 60 minus this deficit is the negative final bank. Ending total wealth **USD 673,146.52545398** because portfolio cushion **USD 673,193.25215278** offsets negative bank; this **does not** make treasury exposure safe.
- Sorting final MID/medium settlements (not intermediate lifecycle realization events) yields a **chronological proxy** for the *first* bank crossing at **2020-02-28T01:30:00+00:00**, bank ~**USD 28.5198849**, deficit ~**USD 31.4801151**. This timestamp is **approximate** and must be confirmed from an event-level replay. The receipt-order minimum reproduces the frozen minimum around **2022-05-18 15:10 UTC**; this is still NOT sufficient for eventwise timestamp certification.

**Mechanism:** in ceiling mode with `economic_group_bootstrap_cushion_share=1.00`, positive MEDIUM settlements first repay the historic recovery deficit, then send remaining distributable gains to Portfolio Compound; losses still charge the sovereign bank. This permits the MEDIUM sovereign balance to breach its 50% floor while ATTACK stays at zero `attack_sovereign_breach_usd`. The high-level risk budget must be verified at entry, settlement and outstanding liabilities; a displayed floor metric by itself is not enforcement. Never 'fix' this by renaming risk or minting imaginary capital.

## Top ten DD episodes for em-s06745 — exact receipts in peak→trough windows

Fixed-peak amounts below are mathematical gap estimates to **25%** assuming same equity peaks, **not** a replay/prediction.

| Rank | DD % | Window MEDIUM net USD | ATTACK net USD | Required change for 25% if same peak USD |
|---:|---:|---:|---:|---:|
| 1 | 36.9105 | −29.44 | 0.00 | 9.50 |
| 2 | 36.6926 | +5.41 | −269.96 | 84.30 |
| 3 | 36.4126 | −20.51 | −1,541.13 | 489.46 |
| 4 | 34.7371 | −14.71 | −4,341.77 | 1,221.15 |
| 5 | 33.1508 | +9.19 | −20,779.28 | 5,106.75 |
| 6 | 33.1498 | +10.76 | −44.62 | 9.73 |
| 7 | 32.1851 | +2.67 | −188.64 | 41.52 |
| 8 | 30.8179 | −9.75 | −367.98 | 71.31 |
| 9 | 30.1530 | −12.39 | −16.63 | 4.96 |
| 10 | 25.6386 | −8.85 | −12.56 | 0.53 |

**All ten exceed 25%**. July–Aug 2019 rank 1 = 75 MEDIUM settlements, 51 losers/24 winners, net approximately −USD29.44. Hence cutting ATTACK alone cannot lower the maximum DD; simultaneously cutting bootstrap MEDIUM too broadly destroys recovery winners. Each replay must recompute all ten episodes.

## Exact manifest join — promising context-coverage hypothesis, NOT proven alpha

Predecision `reg_m5_volatility_state` is available for 675 of 860 ATTACK trades; **185/860 ATTACK entries have no such context**. They must still be executed and administered.

- ATTACK with missing context (185 trades): **gross profit USD 26,408.41**, **gross loss USD 65,264.26**, **net −USD 38,855.85**, **PF ~0.405**.
- ATTACK with observed context (675 trades): **gross profit USD 1,585,365.78**, **gross loss USD 873,608.59**, **net +USD 711,757.19**, **PF ~1.815**.
- This is an **in-sample association**, potentially confounded by which systems deliver context, NOT proof that data missingness independently predicts future losses. Do not reject any trades based on missingness.
- Among the worst DD episodes, missing-context ATTACK settlements contribute ~−USD3,098.50 to rank 4 and ~−USD853.01 to rank 3; first rank 1 remains **entirely MEDIUM**.
- MEDIUM missing context: 461 trades, PF~1.044, so a universal missing-context suppression would be demonstrably inappropriate.
- Candidate *controlled scientific experiment*: use **pre-entry observable context absence** only to select a **causal post-entry M5 closed-bar defensive stop** for ATTACK; compare full exact baseline and several stop strengths, preserving 3,368 entries and measuring winners lost, capital, DD, all GL, PF and all episodes. This cannot by itself solve rank 1. Guard against hidden 'date/trader/symbol' discrimination and any lookahead.
- Separate bootstrap MEDIUM mechanism experiment should be driven by available-before-state `loss streak, equity high-water, outstanding stop-risk, closed M5 adverse excursion`, not retrospective labels.

## Next research and certification gates

1. Validate H6 workflow SUCCESS and its artifact; never infer workflow completion from GitHub commit alone.
2. Capture real eventwise sovereign balances and concurrent reserved bank/cushion into an opt-in full-telemetry replay. Disambiguate first below-floor event vs final-settlement proxy.
3. Implement and test **capital-conserving** bank protection (no transfers from thin air, no spend of reserved cushion) while keeping all Trader executions intact. This does not automatically reduce **total portfolio DD** and must be evaluated separately.
4. New DD intervention requires paired exact replays and STRICT PARETO: floor capital ≥USD582,440.0253 **and** defend frontier ~USD673k, DD improve, total/ATTACK gross loss non-increasing, PF/GP measured, zero sovereign breaches, 3,368 preserved, zero rejected/deferred.
5. Pursue two structurally different modes (bootstrap and high-capital ATTACK); avoid global multiplier cuts, blind stop sweeps, retrospective selection, and false precision.
6. Repeat temporal walk-forward, provenance audit of 2026 provider observation on 2019–2022 decisions, shock/fees/slippage stress, bank ledger reconciliation, independent OOS, full CIBO+Traders+Shared integration before certification or live exposure.

**20% = ideal, 25% = max tolerated; no evidence yet of ≤25%. CIBO remains NOT CERTIFIED.**

## P0 CORRECTION — historical profit curve is NOT economically certified / source capacity loophole

**Observed exact legacy carrier `em-s06745`:** 3,368/3,368 terminal settlements reconstruct a final aggregate balance of USD673,146.52545398, but **the minimum aggregate balance from settlement-only ordering is USD50.3226387449748654** on 2019-08-12 11:25 UTC (not zero). This is a *closed-settlement equity proxy*, not reliable intratrade mark-to-market equity, broker liquidation margin, or legal account cash. Therefore the claim “entire account did reach zero” is **not established**, while the sovereign reserve-breach is **established and disqualifying**. Both statements must be kept together.

Approximate terminal-settlement state (using declared MEDIUM accounting rules):
- First sovereign floor crossing: **2020-02-28 01:30 UTC**; bank **USD28.5198849**, aggregate equity proxy **USD94.9703702**.
- First sovereign bank negative: **2020-08-26 12:20 UTC**; bank **−USD6.3414328**, aggregate equity proxy **USD9,226.2296018**.
- Minimum sovereign bank: **2022-05-18 15:10 UTC**; bank **−USD55.41649567**, aggregate equity proxy **USD675,683.403337**.

**New code-level flaw requiring a separate fail-closed regression:**
In `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py`, branch [G5 source](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-loss-tail-causal-exposure-g5-001/src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py), lines approximately **5933–5978**: if an ATTACK candidate fails `risk_left`, `margin_left`, or `source_left`, the fallback sets `candidate_mode=MEDIUM`, `multiplier=1`, recomputes `source_reserved`, then directly appends to `selected` **without rechecking** the new baseline `source_reserved <= sovereign_left`, `stop_risk <= risk_left`, `margin <= margin_left`, or whether its worst credible charge breaches the sovereign protection floor. This is a **potential funding/capacity bypass** in the fallback; proving its effect on every historical trade requires an instrumented full replay, not just reading the code. It can invalidate claims that all 3,368 entries are physically fundable under the actual risk/margin limits.

**Hard conclusion**: `673,146 USD` is a model ledger output, not verified, withdrawable economic profit and not a certified account outcome. Do not promote *any* carrier with `sovereign_floor_breach_usd > 0`, negative bank, zero/null execution evidence, or unmodeled funded-minimum capacity. Successful PnL arithmetic reconciliation **does not establish trade feasibility**.

**Priority over DD parameter tuning**:
1. In a **new isolated branch**, install a mandatory `funded_minimum_capacity` assertion *after* any ATTACK→MEDIUM fallback and before accounting `selected`. Check stop risk+provider costs, margin, risk headroom and sovereign floor, with no invented transfers. If insufficient for Trader's already-executed baseline entry, **fail the backtest as physically infeasible** and explain rather than silently dropping or fabricating funds. This is a critical conflict to resolve at architecture/execution layer, not permission for CIBO to veto Traders.
2. Capture the first invalid entry and exact source/custody accounting with deterministic sensors. Retroactively reject old “wins” from certification, preserve them only for research.
3. Re-run full 3,368 and the precise physical broker budget + costs + gap stress. Recompute a feasible true economic ceiling **from scratch** if the old curve fails.
4. Sovereign-floor and funded-minimum violations must be **hard disqualifiers in Pareto rankers**; H7 ranking has been patched on its isolated branch at commit `8cc1f6917a831c311c72d2aacaf52636b1a7d38a` so the original invalid carrier cannot be promoted.
5. Only then resume causal loss/DD containment aiming for ≤25% maximum and ≤20% ideal. No claim that the old historic capital is available for a real account.

