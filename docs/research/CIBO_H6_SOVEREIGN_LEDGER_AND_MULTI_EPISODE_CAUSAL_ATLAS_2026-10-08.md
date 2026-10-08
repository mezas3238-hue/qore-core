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
