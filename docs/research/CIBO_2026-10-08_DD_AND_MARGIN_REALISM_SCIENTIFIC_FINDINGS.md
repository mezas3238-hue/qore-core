# CIBO scientific continuity — causal DD experiments and provider margin realism
Date 2026-10-08 | Research only | branch `agent/cibo-dual-dd-context-defense-20261008-001`

## Sovereign unchanged
Initial USD 60; terminal floor >= USD 582440.0252953678696769360345; 3368/3368 Trader entries; zero rejection/defer; zero sovereign breach; generic causal features, no future outcomes, dates, Trader IDs or symbol blacklists. DD target <=25%, ideal 20–22%. Reused holdout research cannot certify live fundability or predictive returns.

## Baseline and new local DD frontier

1. Original canonical master `docs/research/CIBO_MASTER_CONTINUITY_HANDOFF_2026-10-07_TRUE_CEILING_DD_AND_ATTACK_LOSS_COMPRESSION.md`; local baseline `m1cliff-n00624` from [run 37765706712](https://github.com/mezas3238-hue/qore-core/actions/runs/37765706712): capital 670925.7614734999606339602478, DD 35.206607393045501467%, total GL 959321.223795176541180456, ATTACK GL 957755.192064147558231916. Local global STRICT Pareto status must be separately assessed.
2. [New independent ridge 37766565962](https://github.com/mezas3238-hue/qore-core/actions/runs/37766565962) on isolated branch: `m2-reclaim-060` DD **34.92401406329469%**, capital **USD 671185.0736747881**, total GL **USD 959500.2966357417**, ATTACK GL **USD 957941.0786191801**, PF 1.69945270056. Floor-valid and improves both DD and terminal capital against local baseline, but total GL +179.072840565 and ATTACK GL +185.886555033. **NOT local strict Pareto, NOT global strict Pareto; retain candidate for research only.**
3. Non-winning candidates in same ridge: `m2-wick-060` DD 34.96083775%, cap USD 670487.83, GL 961747.18; `m2-h4m5-060` DD 35.005551%, cap USD 670938.38, GL 959332.54; several other stop levels incur severe capital cliffs below the sovereign floor. Do not promote. Cases preserve entry count via replay assertions.
4. Next actual experimental sweep: [workflow `cibo-trader-lab-dual-dd-reclaim-cliff-ridge-20261008.yml`](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-dual-dd-context-defense-20261008-001/.github/workflows/cibo-trader-lab-dual-dd-reclaim-cliff-ridge-20261008.yml). Test stop-R local ridge and small W6 taper shifts; require exact metric evaluation before promotion. No live deployment.

## Ten-episode risk audit and margin feasibility red flag

[Successful GitHub forensic run 37766756802](https://github.com/mezas3238-hue/qore-core/actions/runs/37766756802), source artifact 11543738930 ZIP SHA256 `7643863b5d53ae762f2d63e956b20278132d0a9ec554235b28cabaca659f5be9`. Workflow: `.github/workflows/cibo-dualdd-top10-capital-risk-forensics-20261008.yml`. Source case `m1cliff-n00624`. DD snapshot top exposures:

| Episode DD rank | Date of peak | Observed DD | Peak simulated total capital USD | Open stop risk / capital | Open margin / capital |
|---:|---|---:|---:|---:|---:|
| 1 | 2019-07-19 | 35.2066% | 79.76394 | 8.16% | 41.76% |
| 2 | 2020-04-03 | ~35.01% | 705.17 | 1.03% | 0.38% |
| 3 | 2020-09-10 | ~34.60% | 12866.09 | ~0.01% | 0.12% |
| 4 | 2021-02-09 | ~33.38% | 61689.77 | ~0.0025% | 0.10% |
| 5 | 2020-03-23 | ~32.27% | 567.41 | **20.07%** | 4.97% |
| 6 | 2020-08-19 | ~31.90% | 12199.41 | ~0.01% | ~0.01% |
| 7 | 2020-05-21 | ~30.83% | 1227.49 | **18.45%** | **184.46%** |
| 8 | 2020-06-24 | ~30.82% | 4289.78 | 0.36% | 0.29% |
| 9 | 2020-01-31 | ~30.02% | 123.66 | **19.69%** | **34.39%** |
| 10 | 2019-11-04 | ~28.69% | 109.15 | 0.76% | 1.85% |

**Critical finding for broker-realism certification:** at 2020-05-21 peak the recorded open margin was approximately USD 2264.25 on a simulated capital snapshot of USD 1227.49, ratio 184.46%. The engine file `src/qore/infrastructure/trader_lab/cibo_three_mode_capital_lab.py` contains `MARGIN_CAPACITY_MULTIPLE = Decimal("100")` and calculates `margin_capacity = total * MARGIN_CAPACITY_MULTIPLE`. Thus the replay allows synthetic risk/margin capacity materially above its capital in this lane. The snapshot does not prove executable broker collateral/margin-level admissibility: it is a scientific **red flag**, not an assertion about a specific provider.

### Independent certification and live deployment gates (NOT YET PASSED)
- State exact broker/account leverage, symbol-by-symbol margin requirements and volume min/step/max; reconcile simulated `margin_per_volume` and actual executable lot.
- Model free margin, margin level and broker stop-out / margin-call thresholds **using provider specifications**, including peak-to-trough mark-to-market open-position equity, hedged and correlated concurrency, slippage/gaps and spread spikes. Do not assume fixed stop-out percentages.
- Verify account total equity vs treasury `sovereign_bank+portfolio_cushion` and mark-to-market unrealized P&L, reservations, open stop risk, provider costs and stop-out liquidation path.
- Produce exact per-event feasibility exceptions, zero unsupported fills, unrealizable P&L quarantined, and risk-of-ruin under clustered losses.
- Until these gates pass, do NOT describe simulated USD 671k as realizable cash, deploy an aggressive 10000x exposure into a live or funded account, or assert full certification.
- Risk snapshots at drawdown peaks are explanatory ex-post forensics, NOT date-specific runtime policy triggers.

## Risk-engineering direction
Current DD cannot reach 25% by targeting one episode: 10 recorded episodes exceed ~28.69% on the baseline. Need causal **multi-episode** risk envelope, not date/identity targeting. Features to test on logged past-state: realized live DD and running peak; normalized open stop risk / mark-to-market equity; provider margin level; last observed closed-bar regime/expected-R; portfolio concurrence/loss clusters; protected profit-keeping lifecycle. Quantify winners lost and economic cliff for each. Promote only if global policy condition satisfied; all holdout-reused research remains uncertified.

## Current artifacts
- [Own post-entry context ridge](https://github.com/mezas3238-hue/qore-core/actions/runs/37766565962)
- [Top-ten margin risk forensic](https://github.com/mezas3238-hue/qore-core/actions/runs/37766756802)
- [Prior causal 2019 atlas](https://github.com/mezas3238-hue/qore-core/actions/runs/37765762713)
- [Prior ATTACK 2020 atlas](https://github.com/mezas3238-hue/qore-core/actions/runs/37765061391)
- [Next reclaim threshold experiment workflow](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-dual-dd-context-defense-20261008-001/.github/workflows/cibo-trader-lab-dual-dd-reclaim-cliff-ridge-20261008.yml)

This is an isolated technical supplement for the canonical master; never rewrite another active architect's handoff concurrently.

## Second W6 rescue result (verified 2026-10-08 11:00 UTC)

[W6 rebound recovery run 37767150980](https://github.com/mezas3238-hue/qore-core/actions/runs/37767150980), workflow `.github/workflows/cibo-trader-lab-dual-dd-w6-gl-rebound-recovery-20261008.yml`, 16 cases. `reclaim-base`: DD 34.924014%, capital USD 671185.07, total GL USD 959500.30. W6 fractions **0.94916–0.94935** preserve identical 34.924014% DD but improve gross loss to USD **959347.01**, ATTACK GL **957787.79**, capital **670889.32**. These cases are **not global strict Pareto**, and DD is unchanged; they trade ~USD 296 final capital for ~USD 153 loss compression. At **0.94940** or greater tested, discrete compounding cliff collapses capital to **USD 521136.07**, below floor. Explicitly reject those. Keep a separate DD/GL frontier: no single universal winner.

## NEW P0 blocker: Sovereign subledger floor violation, not just ATTACK breach

[Exact-artifact sovereign audit 37767236400](https://github.com/mezas3238-hue/qore-core/actions/runs/37767236400) discloses **nonzero `sovereign_floor_breach_usd` despite `attack_sovereign_breach_usd=0`** for every sampled candidate. In `m2-reclaim-060`:
- total ending simulated capital = **USD 671185.0736747881** = Sovereign bank **-USD 45.6047501253** + cushion **USD 671230.6784249133**; arithmetic reconciles;
- minimum Sovereign bank = **-USD 54.2945470025**;
- Sovereign protection floor breach = **USD 84.2945470025** (positive);
- ATTACK Sovereign breach = zero;
- minimum total capital among ten known historical DD troughs ~= USD 52.05776 (this is NOT a verified global minimum or mark-to-market broker equity).

The engine's `_State.sovereign_protection_floor_usd` is peak Sovereign bank times `1 - SOVEREIGN_DEFENSIVE_DRAWDOWN`; the constant is `0.50`. Its `mark()` tracks `sovereign_floor_breach_usd` whenever bank falls below floor. Current ranking scripts check **ATTACK** breach but do not require zero separate **Sovereign** floor breach or nonnegative minimum Sovereign. Never claim this test passes full sovereign invariants based on the ATTACK-only check. The negative compartment balance alone does NOT prove the consolidated broker account became negative; causal funding, reservations, transfers and liquidation must be audited separately. However **positive ending combined capital does NOT cure an explicit Sovereign floor breach**.

### Prevent false certification: implemented independent gate

Code: `scripts/cibo_replay_integrity_gate.py`  
Tests: `tests/test_cibo_replay_integrity_gate.py`  
[Validation run 37767520613](https://github.com/mezas3238-hue/qore-core/actions/runs/37767520613) **SUCCESS**: 8 unit tests passed; exact artifact SHA256 verified; both baseline `m1cliff-n00624` and `m2-reclaim-060` correctly flagged as **FAIL** for independent Sovereign floor/minimum-balance and 25% DD gates. `certified=false` always, separate margin/OOS gates also required. Audit does **not** change PnL or force a hard failure of research experiments.

**Governance:** From now on report separate columns for terminal floor, DD, full Sovereign floor breach, minimum Sovereign, ATTACK breach, economic preservation, provider margin feasibility, and OOS/certification. Do not promote a candidate as **sovereign-certified** with any missing/failed gate. If the floor is allowed to be cross-funded from cushion, implement an auditable, causal, reserved-capital-safe transfer/reconciliation contract and test without double spend; do not silently net subledgers or retroactively erase violation. Formal ledger design choice belongs to explicit governance and scientific proof.

## Remaining tasks
1. Reproduce first timestamp of Sovereign floor breach, with prior Sovereign/cushion balances, reservations, provider fills and MEDIUM settlement. Inspect whether transfers were possible at that moment; rule out unsupported cross-book funding.
2. Add exact accounting/provenance/zero-double-spend tests to any ledger repair, including every one of 3368 entries; rerun holdout for DD/GL/capital.
3. Re-evaluate realistic margin and provider capacity (current engine permits synthetic margin capacity 100x simulated total).
4. Continue causal DD compression across multiple bottlenecks on the **research lane**, but certification promotion is blocked until all invariants pass and sealed fresh OOS is completed.

## CAUSAL CROSS-LEDGER SOVEREIGN PILOT — quantitative validated result (11:11 UTC)

[Exact historical replay pilot 37768334319](https://github.com/mezas3238-hue/qore-core/actions/runs/37768334319) completed **SUCCESS** after fixing Decimal precision to 100 digits rather than weakening capital conservation assertions. Isolated script: `scripts/cibo_sovereign_causal_rebalance_replay.py`; original QORE engine remains untouched. Three same-input cohorts:
- **Original baseline `m2-reclaim-060`:** capital 671185.073674788065, DD 34.924014063%, total GL 959500.29663574, ATTACK GL 957941.07861918; end bank -45.6047501; min bank -54.2945470; sovereign protection breach 84.2945470. INVALID full Sovereign.
- **`transfer-zero-m2-reclaim`:** transfers only when internal bank <0, 68 transfers / USD 71.9682372; end capital **670960.60574**, DD **34.94718357%**, GL **962130.15647**; end bank +7.51928, min bank 0 but **Sovereign floor breach still 54.85981554**. Not full-safe; a mere nonnegative treasury is insufficient.
- **`transfer-floor-m2-reclaim`:** transfers exactly the funding gap to current Sovereign protection floor from **unreserved cushion**, debits both cushion and outstanding ATTACK credit without creating any capital, identity/date/outcome hardcoding. 49 transfers / USD 167.85675067, cumulative unfunded demand 0. Final capital **USD 671563.397206547512**, DD **34.92401406329469%**, total GL **USD 962534.884427226939**, ATTACK GL **USD 960442.464276750417**; end Sovereign **USD +123.88585558**, min Sovereign **USD 30.00**, `sovereign_floor_breach_usd = 0`. All 3368 entries and zero ATTACK breach preserved. **FULL SOVEREIGN GATE PASS in this exact reuse-holdout simulation**, but **DD still >25%**, **GL degrades USD 3034.58779 vs original baseline**, no global strict Pareto, no provider margin proof or certification.
- First causal funding event in floor-policy case at state mark 753: bank 26.50342696 vs floor 30, open margin 0, free cushion 68.33166196; transfer 3.49657304 to Sovereign, without change in combined USD 94.83508891. Earlier [unmodified first breach forensic run 37767846850](https://github.com/mezas3238-hue/qore-core/actions/runs/37767846850) confirms the same state. Do not infer timestamps from state-mark index alone.
- Code invariant first run rejected Decimal 28-digit rounding: [failed initial pilot 37768197756](https://github.com/mezas3238-hue/qore-core/actions/runs/37768197756) was repaired with explicit 100-digit local Decimal context, not by suppressing the conservation check. This demonstrates nontrivial safety-fail-closed instrumentation.

**Nonpromotion policy:** this result is a *scientific proof of concept* that a ledger-compatible, causal cross-book transfer can remove the specific internal floor breach while preserving entry count and terminal floor in an already-tuned research replay. Not evidence that deposits, transfers or high leverage are actually executable in live broker conditions; no live action performed. Do not merge transfer monkeypatch into real engine without audited production-quality transfer journal, atomic reservation/release, crash/restart/idempotency, open-balance and cross-book authority proof. Compare against all global GL and capital comparators. GL compensation ongoing via `.github/workflows/cibo-sovereign-floor-dd-gl-recovery-ridge-20261008.yml`; track outputs explicitly.


## Subsequent DD/GL recovery tests — no sovereign-safe global strict improvement

The new floor-preserving internal rebalance case `transfer-floor-m2-reclaim` is not yet an approved carrier. Tested additional causal, identity-free hypotheses against its USD 671563.397 / DD 34.924014 / GL USD 962534.884 baseline.

- [Run 37768481075 — 12-case sovereign-floor-safe W6/reclaim ridge](https://github.com/mezas3238-hue/qore-core/actions/runs/37768481075) **SUCCESS**. All 12 show zero Sovereign floor breach. W6 thresholds ~0.94916–0.94935 kept DD ~34.924% but terminal capital fell to **USD 551604.62**, below the frozen floor despite gross loss reduction. Reclaim stop variants -0.70,-0.66,-0.64 etc retained capital > floor and Sovereign integrity but were **not better on DD and gross loss together**. `SOVEREIGN_SAFE_GL_RESCUE_CASES=[]`.
- [Run 37768716779 — exact transfer loss forensics](https://github.com/mezas3238-hue/qore-core/actions/runs/37768716779) **SUCCESS**; comparison of all 3368 same signal fingerprints reconciles **USD +3034.587791485** official total gross loss exactly with final trade receipt deltas (residual ~2.8e-22), while terminal net improves +USD 378.32353176. **305** trade economic outcomes change, primarily 101 ATTACK (loss increase USD +2501.38565757) and 204 MEDIUM (+USD 533.20213391). Significant 2021 multiplier sensitivities: a single ATTACK trade moved 766x→4024x and caused USD +6287.94 more loss, offset by reduced losses on other events (5000x→500x saved USD ~2167 etc). **DO NOT hardcode those IDs/years/outcomes in policy**. The next hypothesis must be generic risk-band/projected-risk/regime based, tested on fresh data later; archive 2021 differences for *forensic attribution only*.
- [Run 37768818893 — 9-case sovereign-safe high-multiplier band extension](https://github.com/mezas3238-hue/qore-core/actions/runs/37768818893) **SUCCESS**. All candidates preserved full Sovereign floor, but no valid DD+GL improvement. Extending ATTACK risk band from 3999 to **4020** yields DD 34.924014% / GL 943797.64 / terminal capital **USD 528744.05** **FAIL floor**. Upper 4200: terminal USD 567408.75 FAIL. Upper 4100: capital USD 158143.12 and DD 53.90% FAIL. Upper 4400: capital USD 131442.55 and DD 56.74% FAIL. Original upper 3999 or 4000 retains USD 671563.40 and DD 34.924. No promotion. Small parameter changes produce severe discontinuous capital cliffs due leveraged compounding.
- [Run 37768548663 — independent full-Sovereign protection gate](https://github.com/mezas3238-hue/qore-core/actions/runs/37768548663) **SUCCESS**. Standalone gate passes full Sovereign internal assertions and 3368-admission for transfer-to-floor case; specifically **rejects** transfer-to-zero case because Sovereign protection still breached, and rejects all cases as fully qualified since DD >25% and broker/OOS gates remain unknown.
- [Run 37769046152 — robust Pareto comparator regression](https://github.com/mezas3238-hue/qore-core/actions/runs/37769046152) **SUCCESS**, **12 unit tests pass**. Added `assess_research_pareto()` to `scripts/cibo_replay_integrity_gate.py` with materially positive drawdown threshold (1e-8 fraction) and independent full Sovereign safety. This corrects a secondary finding: legacy ridge scripts sometimes **mislabel an identical comparator as STRICT PARETO TRUE** when a change of only ~2e-32 appears from high-precision Decimal state. Such a flag is a numeric artifact, **not a genuine improvement**. No production/trading policy altered.

### Current exact separation of gates

1. **Research historical DD frontier**: 34.924014% with capital ≥ floor; target ≤25% NOT met.
2. **Full internal Sovereign integrity**: transfer-to-floor experimental variant PASS in reused historical replay; unmodified main CIBO core still FAIL. No independent proof of atomic transfers/idempotent double-spend-safe live ledger yet.
3. **Global capital/DD/GL Strict Pareto**: NOT attained by the transfer-to-floor research policy; GL rebound unacceptable for global promotion.
4. **Provider margin / mark-to-market solvency / stop-out**: UNPROVEN.
5. **New sealed OOS + full scientific battery**: NOT PERFORMED.
6. **Certification / live deployment**: BLOCKED.

No high-dimensional after-the-fact ridge may be called certification evidence; keep all research cases isolated and do not modify source-of-truth carrier until every hard criterion is proven. This supplement complements the original master handoff and open issue #733.

## Final dual-bottleneck DD ledger atlas (post-transfer, exact)

[Run 37769298700](https://github.com/mezas3238-hue/qore-core/actions/runs/37769298700) completed **SUCCESS** from SHA256-checked original 3-case pilot artifact. On `transfer-floor-m2-reclaim`, top replay DD peaks:
- 2020-04-03 to 2020-05-13 **34.924014%**, peak equity **USD 706.9201**, amount beyond a hypothetical 25% peak-to-trough loss ~**USD 70.15**, ATTACK ~ -252.296887, MEDIUM ~ +5.412013.
- 2021-02-09 to 2021-03-03 **34.918%**, peak equity ~**USD 56969.44**, amount beyond 25% ~**USD 5650.08**, strongly ATTACK losses ~ -19901.63. This is a near-tie with 2020. Eliminating the 2020 episode alone cannot achieve 25%.
- 2019-07-19 MEDIUM **34.735%**; 2020-09-10 ATTACK **34.504%**; 2020-03-23 **32.190%**; 2020-08-19 **31.890%**; 2020-06-24 **30.835%**; 2020-05-21 **30.808%**; 2020-01-31 **29.455%**; 2019-11-04 **28.449%**. All ten historical episodes exceed 25%. Do not treat amounts beyond 25% as directly additive: each intervention changes the equity path.

**Causal research priority after accounting fixes:** design multi-episode ex-ante projected risk and portfolio-concurrency envelope with still-active Trader entries and post-entry context; independently measure protected winners and losses, reserve/cushion pressure and compounded terminal capital. High-multiplier broad caps provably violate the capital floor in current sweeps. No identity/date/outcome policy hardcoding. Report both pure DD-physical and strict-safe + GL comparisons after every test. This historical holdout is already mined extensively and will require entirely sealed fresh OOS after freeze.


## Latest 2026-10-08 causal-risk probes — definitive negative findings

Research-only exact replay baseline in all probes: `transfer-floor-m2-reclaim`: USD 671563.39720655 terminal, 34.9240140633% DD, USD 962534.88442723 gross loss, full internal Sovereign protection. All 3 suites preserve 3368 admissions and their Sovereign accounting; no production policy changed.

- [13-case ATTACK DD-triggered single-trade risk sweep SUCCESS 37783453703](https://github.com/mezas3238-hue/qore-core/actions/runs/37783453703). Vary risk fraction 20%, 15%, 12%, 10%, 8%, 5%; activate only with causal observed DD >=5%,10%,15%, between live simulated total capital USD 50 and USD 75000. **No sovereign-safe + floor-valid + materially lower DD + loss improvement**. Notable: 12% risk triggered at 10% DD produced capital USD **688808.89** (higher final) but DD **53.38873%** (FAIL); 5% at 10% DD yielded only USD **2007.18**, DD **52.25178%**; at 5% DD it yielded USD **2895.14**, DD **52.94455%**. The 5% gate is ATTACK-specific and conditional, NOT a proof of correct $60 micro-account per-entry sizing. Massive nonlinear path dependence: simple per-trade caps do not guarantee overall DD.
- [14-case post-settlement Portfolio shock response SUCCESS 37783724548](https://github.com/mezas3238-hue/qore-core/actions/runs/37783724548). Generic causally triggered only by last settled ATTACK loss as fraction of then-known capital; vary trigger 3%–7%, retained-risk multiplier 35%–90%, one-shot vs persistent. All variants remain internally Sovereign-safe but **no Pareto/capital/DD success**; one-shot around trigger 5% led to only ~USD **551631.13**, below floor, while trigger 7% / taper 50% retained USD **671472.20** but DD **37.06377%**. Aggressive alternatives DD as high as ~82%.
- [12-case settled per-Trader ATTACK gross-loss/profit pressure SUCCESS 37784126367](https://github.com/mezas3238-hue/qore-core/actions/runs/37784126367). Only prior settled cumulative outcomes, min 10–30 settlements, ratio trigger 0.60–1.20, 90%–98% cap retention; 12/12 internally sovereign-safe but **no successful Pareto**. Most promising DD 34.95347% with terminal USD **526899.80** and GL ~944669.80 (below frozen floor); several reach DD >65%. Do not use Trader identity/date/outcome to blacklist; per-Trader causal summary is legitimate historical statistic, but these exact parameters FAIL.
- [Account transfer arithmetic CI 37783957462 SUCCESS](https://github.com/mezas3238-hue/qore-core/actions/runs/37783957462): **21 unit tests pass** (9 tests verifying exact Decimal capital conservation, reserved Portfolio, ATTACK credit reduction, partial funding and idempotence, plus 12 independent full-Sovereign replay eligibility/Pareto tests). None establishes actual broker margin feasibility, fresh OOS, atomic restart-safe durable journal or live safety.
- New lane [post-entry adverse partial reduction](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-dual-dd-context-defense-20261008-001/.github/workflows/cibo-sovereign-postentry-adverse-partial-ridge-20261008.yml) tests closed-bar causal exit management instead of early portfolio-wide scaling. Promotion only after exact completed report and entire gate set. **Do not fabricate outcomes while job is pending.**

### Engineering interpretation
The DD problem is path-dependent: generic pretrade throttles collapse the compounding staircase, preserving nominal Sovereign floor in the research ledger but violating terminal floor or increasing DD. Continue developing *post-entry causal loss compression* and linked position-level drawdown risk, keeping 3368 entries and independent Sovereign/GL/profit tests. All these repeatedly optimized reused-holdout results are hypothesis-generation evidence only; require new sealed OOS and operational broker-realism test before certification.

## Post-entry adverse partial reductions: fail and identified profit-preservation mechanism (2026-10-08)

- [10-case causal M5 closed-bar ATTACK override replay 37784390074](https://github.com/mezas3238-hue/qore-core/actions/runs/37784390074) SUCCESS. Adds `ADVERSE_PARTIAL_REDUCTION` to the ATTACK lifecycle map, preserving existing context-specific hard stop, tuning 10%-50% of current exposure released on observed closed-bar adverse signal; all 3368 entries admitted, internal full Sovereign protection maintained, but **every noncontrol variant failed frozen terminal floor and worsened DD**. Example 50% adverse partial, prior favorable R capped 0.50: terminal **USD 104321.24**, DD **57.04531%**, GL **USD 472391.16**. Lower gross losses here are NOT evidence of a successful policy; entire gain engine shrank.
- [Exact per-fingerprint post-entry winner and loss attribution 37784720253](https://github.com/mezas3238-hue/qore-core/actions/runs/37784720253) SUCCESS; immutable artifact 11552864997 zip SHA256 `992d147baec7dc7e2db0fa940a5d1597c43f95dc03cdde29d4b415be3658840e`. For `transfer-floor-part50-f50` vs exact same Sovereign-protected control, **935/3368 receipts changed** (629 ATTACK, 306 MEDIUM), terminal -**USD 567242.15**; **USD 1,135,888.02 profit sacrificed in historically positive trades**, against **USD 596,379.04 less loss on historically negative trades**. Baseline summed positive-trade net ~USD 1,634,038.28, new summed positive-trade net ~USD 576,652.41. Winner-to-flat/loser count 10, loser-to-winner count 2. This is *full replay path attribution*, including future altered sizing/compounding, NOT purely incremental mechanical stop PnL; never use final-outcome labels as runtime signals.
- Example of cascading loss of growth: a previously winning high-multiplier ATTACK trade was ~USD +65096.60 baseline at 7796x but in altered compounded path only ~USD +968.60 at 116x; another formerly ~USD +56100 at 10000x became ~USD +4011.15 at 715x. These identify lost win convexity, not admissible identity/date targets.
- **New design hypothesis:** do not apply universal adverse reduction. Separate recoverable temporary heat from irreversible deterioration using *only past closed-bar evidence and current book states*, perhaps conditional closed-bar adverse + native context confluence + minimal-favorable-excursion window. This must be tested against *wins saved, losses compressed, real DD, all capital and Sovereign gates*; no lookahead via MFE computed after exit, no preemptive admission veto.
- Parallel risk/accounting blocker remains: internal protected Sovereign != broker executable leverage/margin. Current reused holdout is already contaminated by many iterative searches and cannot certify an eventual candidate.


## New experiment: causal context gating instead of universal ATTACK adverse reduction

[Pre-entry cohort attribution SUCCESS 37785085926](https://github.com/mezas3238-hue/qore-core/actions/runs/37785085926) joined SHA256-frozen 3368-entry manifest source `11451743578` with paired postentry full-replay receipts from immutable `11552864997`. Grouped results by strictly **pre-decision** `trader_opportunity.decision_context` values, then compared ex-post winner destruction and losing trade relief. All feature cohort sums overlap; no feature may be mistaken for an independent controlled causal effect. **Data snooping risk is severe; this is hypothesis generation ONLY**, must verify on new sealed holdout before any promotion.

Examples of net **historical** gain/loss attributable to universal partial conditioned on named pre-entry feature subcohort (do NOT hardcode dates/Trader IDs/strategy family):
- `ctx_source_range_state_bucket=q4:<=2.0`: n=122, 52 economic receipts changed, approximately +USD 25,261 historical net contribution under partial-vs-control attribution (cohort-only).
- `reg_m5_volatility_state=compressed`: n=977, 207 changed, ~+USD 7,950 historical cohort net contribution, with USD ~175,089 loss relief vs USD ~179,679 damage to preexisting winners (non-exhaustive decomposition, global compounding interactions).
- `reg_h1_body_alignment=flat`: n=29, only 6 changes, historical contribution ~+USD 4,708.
- Most universal-partial harm happens outside those groups. Features `family`, `ctx_symbol`, calendar fields, source strategy identity are **not** admissible post hoc policy targets. Even suggested generic features are subject to postselection and not OOS.

Research-only opt-in `--lifecycle-attack-override-partial-require KEY=VALUE` added to `scripts/cibo_trader_lab_three_mode_ceiling.py`. The new pure `_causal_partial_features()` gate:
- reads only immutable pre-entry decision context,
- disables **only** `ADVERSE_PARTIAL_REDUCTION` on nonmatches,
- preserves existing `DEFENSIVE_INITIAL_STOP_CAP` and Trader entry custody,
- defaults to original behavior if the new option is absent,
- fails closed on missing required context and refuses context gate without partial feature enabled.
[CI SUCCESS 37785336579](https://github.com/mezas3238-hue/qore-core/actions/runs/37785336579): 27 unit tests pass (9 transfer, 12 sovereign/robust Pareto, 6 context gate).

[12-case context-specific replay workflow](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-dual-dd-context-defense-20261008-001/.github/workflows/cibo-sovereign-context-only-postentry-partial-ridge-20261008.yml) isolates cause with same base parameters and independent Sovereign/GL/DD gates, using only normalized geometry/volatility context. Record actual outcomes only after completed receipts; no policy promotion from reused holdout.


## Scientific breakthrough: full-Sovereign economic noninferiority with H1 flat context (2026-10-08)

[12-case contextual ATTACK partial ridge 37785438088](https://github.com/mezas3238-hue/qore-core/actions/runs/37785438088) **SUCCESS** (SHA256-frozen exact outputs artifact `11554376374` digest `37ff402efa052719f8fed635b015bac1586603dc929c86422bebb20e226d291c`).

Research candidate `transfer-floor-h1flat50` adds closed-bar ATTACK adverse partial release of fraction 0.50, but **only when immutable pre-entry `reg_h1_body_alignment=flat`**. It **does not reject any** of 3368 opportunities, and removes only the partial feature on nonmatches, while preserving the pre-existing context-dependent defensive stop.

Exact vs original full-Sovereign-protected `transfer-floor-control`:
- Candidate final USD **672671.4731058652870261462079**, from control USD 671563.3972065475124241607281; **+USD 1108.0758993177746019854798**.
- DD **0.349240140632946906062729154214387036177284... = 34.92401406329469%**; actual numeric change to source control 0E-100 in independent replay, **NO MATERIAL DD REDUCTION**. Critical 2020/2021 episodes unresolved.
- Total gross loss **USD 959378.8420864768849772034844**, down **USD 3156.0423407500542774184468** from USD 962534.884427226939.
- ATTACK gross loss **USD 957286.4219360003626447298416**, down USD 3156.0423407500542774184466.
- PF 1.70109058444842914, final Sovereign bank USD +123.88585558, minimum Sovereign USD +30, `sovereign_floor_breach_usd=0`; all entries 3368/3368 preserved and the fixed terminal floor USD 582440.02529537 satisfied.
- **Not global strict DD Pareto**: DD not reduced meaningfully and compared with older global gross-loss benchmarks is still higher. Treat as an economic noninferiority proof / additional R&D headroom, not true final ceiling or certification.

[Independent SHA256-artifact audit 37785929563](https://github.com/mezas3238-hue/qore-core/actions/runs/37785929563) **SUCCESS**, 17 regression tests pass. Added `assess_economic_noninferiority()` into independent `scripts/cibo_replay_integrity_gate.py`: requires baseline & candidate full Sovereign-safe, all 3368, terminal above frozen floor, material positive capital improvement, material gross loss compression, ATTACK gross loss nonworsening and DD noninferiority tolerance 1e-8. Exact result: `economic_noninferiority_pass=true`, `dd_target_pass=false`, `certified=false`, `fresh_oos_verified=false`, `broker_margin_verified=false`. No live deployment or merge.

Notably `transfer-floor-h1flat20` (20% partial) collapses capital to USD 552130.09 below frozen floor even though DD stays ~34.924%; fractions strongly nonlinear. Further [H1 flat fraction ridge workflow](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-dual-dd-context-defense-20261008-001/.github/workflows/cibo-sovereign-h1flat-partial-cliff-ridge-20261008.yml) brackets 35%-70% to seek a better GL/capital frontier. Record actual results after completion; do not assume material DD progress.

**Next scientific priority:** use newly protected and economically superior R&D carrier to seek joint, ex-ante causal 2020+2021 DD reduction without reducing winner convexity. All discovery is overfit-prone because 2019-2022 holdout repeatedly mined; eventual promotion requires untouched sealed out-of-sample evaluation and provider-realistic execution/funding certification.

## H1-flat 50% local economic ridge bracket: stable only at/below cliff

[14-case fraction cliff ridge 37786035895](https://github.com/mezas3238-hue/qore-core/actions/runs/37786035895) SUCCESS. Tested fractions 35%,40%,42%,44%,46%,48%,49%,50%,51%,52%,55%,60%,65%,70% with constant immutable H1 flat geometry and original Sovereign protection. All remain 3368-admitted, full protected Sovereign, but **no variant dominates 50%** on both capital and GL at non-worse DD:
- 50% remains the most favorable observed: capital USD **672671.47**, DD **34.924014%**, total GL USD **959378.84**;
- 49%: USD **672640.74**, total GL **959397.83**, same DD;
- 48%: USD **672615.81**, total GL **959422.76**, same DD;
- 51%-70%: nonlinear cliff to ~USD **666403–666883**, DD **44.970–44.974%**, GL **978194–978669**. No promotion.
This is a local historical boundary, **not evidence of a universal optimum**; it may be overfit to already mined 2019–2022 data.

New independent scientific direction: [dual DD bottleneck causal feature atlas](https://github.com/mezas3238-hue/qore-core/blob/agent/cibo-dual-dd-context-defense-20261008-001/.github/workflows/cibo-dual-bottleneck-causal-risk-atlas-20261008.yml), comparing peak-to-trough 2020 and 2021 losing-event geometry to all ATTACK winners; no date/Trader ID/realized outcome is permitted as a future runtime trigger. The objective remains **material DD <=25%**, ideally 20–22%, while preserving the now-verified experimental economic headroom. No live deployment approved.

## Critical updated DD episode ranking and failed early-capital DD budget intervention (2026-10-08)

[Exact replay episode diff 37786561457](https://github.com/mezas3238-hue/qore-core/actions/runs/37786561457) **SUCCESS**, comparing baseline `transfer-floor-control` and R&D carrier `transfer-floor-h1flat50` from one hash-verified artifact:
- Overall max DD remains **34.924014%**, 2020-04-03 → 2020-05-13, primarily ATTACK (net about -USD252.30).
- The formerly *nearly tied* 2021-02-09 → 2021-03-03 DD fell materially from **34.917732%** to **33.391652%** (~**1.52608 pp improvement**). Its ATTACK absolute losses did NOT simply shrink (net about -USD19901 baseline vs -USD20598 candidate): the relative DD improvement is driven by changed capital/peak path. Do not claim causal trade-level ATTACK losses alone fell in that episode.
- The now-second highest DD is **2019-07-19 → 2019-08-07 MEDIUM-only, 34.735216%** (unchanged), then **2020-09-10 → 2020-09-28 ATTACK-led, 34.511782%**. 2021 is now fourth. All ten biggest DD episodes still exceed 25%. Thus immediate multi-bottleneck problem after economic carrier freeze: 2020 spring ATTACK, 2019 MEDIUM1x, 2020 fall ATTACK. Other episodes remain.
- Earlier [generic dual-bottleneck atlas 37786371555](https://github.com/mezas3238-hue/qore-core/actions/runs/37786371555) selected by **current** rank, not hard-coded calendar years. Therefore its second selected event was in **2019 MEDIUM**, and `episode2_attack_top_loss_events=0`; it is **not** a valid shared ATTACK 2020+2021 factor inference. Do not overinterpret or promote its feature correlations. The 2020 top ATTACK loss event cohort is small and broadly overlaps ATTACK winners; no robust predictor was established by it.

[14-case early-capital ATTACK DD-budget2 sweep 37786760074](https://github.com/mezas3238-hue/qore-core/actions/runs/37786760074) **SUCCESS** (research experiment, no real-world orders). Added a second causal ATTACK DD budget fraction (0.10–0.40) only while live simulated capital within several bands between ~USD400 and USD900. All Sovereign-protected, 3368 custody, but **NONE** preserved the frozen USD582440 terminal floor **and** improved DD/GL. Some variants ruined compounding catastrophically:
- Budget2 0.15 in $550–$800 band: terminal only **USD 668.55**, DD 36.692882%.
- Budget2 0.20 in $400–$900: terminal only **USD 886.95**, DD 74.786857%.
- Budget2 0.40 in $400–$900: terminal USD 568454.54 (below floor), DD 50.884136%.
- Control remains **USD 672671.4731**, max DD 34.924014%, total GL USD959378.8421, complete Sovereign internal floor protection.
This is evidence of nonlinear portfolio compounding and physical capacity constraints, not that DD protections are inherently useless. A naive capital-band risk clamp is **not** a satisfactory solution and must not be promoted.

**Engineering handoff:** prioritize rigorous accounting and *local post-entry, position-level, mark-to-market drawdown causes* over wide synchronized early-capital multipliers. Preserve current research economic carrier `transfer-floor-h1flat50` as a separate benchmark without claiming full Pareto/25%-DD certification; production remains unchanged. Next genuine scientific step needs new sealed independent OOS after methodology freeze, and broker-realistic lot/margin/cost/stop-out validation. Strict target DD <=25% (ideal 20–22%) continues.

## Direct scientific answer: Why 34.924% DD versus 59.581% and 94.057% DD?

[Immutable-paired replay forensics SUCCESS 37789599955](https://github.com/mezas3238-hue/qore-core/actions/runs/37789599955) compares same 3368 signal fingerprints and identical recorded opportunities across three ATTACK context-stop policies. Inputs are SHA256-verified artifacts from [exact 13-case replay 37789129611](https://github.com/mezas3238-hue/qore-core/actions/runs/37789129611). Main line code unchanged.

- **Reference `transfer-floor-attackctx-control`:** terminal USD **672671.4731**, max DD **34.924014%** in **2020-04-03 → 2020-05-13**, gross loss USD **959378.8421**, PF **1.70109**. DD is a *fraction* of equity peak and scales differently from nominal dollar loss.
- **Context stop `balanced-risk-55` (different broader H4-range balanced + protected risk conditions, stop -0.55 R):** terminal USD **33503.4074**, max DD **59.580967%**, its max episode **2022-04-12 → 2022-06-09** (peak USD 51979.6712, trough USD 21009.6804), ATTACK net ~**-USD30934.47**, PF **1.129984**. **951/3368** receipts changed, 11 switched financial mode. Ex-post profit sacrificed on formerly profitable trades USD **1382419.95**, loss relief on formerly negative trades USD **749578.78**. Terminal delta **-USD639168.07**; 44 former winners become <=0. This is the nonlinear opportunity cost of aggressive closure and compound capital shrinkage.
- **Context stop `balanced-only-55` (broader H4-range balanced, stop -0.55 R):** terminal USD **5901.28095**, max DD **94.057043%** in **2022-04-12 → 2022-06-14**, peak USD **84534.55045**, trough USD **5023.85202**, DD-episode ATTACK net **-USD79467.6530**, MEDIUM net ~-USD43.04542. PF drops to **1.018737**. Despite lower lifetime gross losses USD **311751.2763**, **937/3368** individual receipts changed (only 6 mode switches), sacrificing USD **1374183.54** on formerly positive trades versus USD **723436.06** relief on formerly negative trades. Terminal delta **-USD666770.19**. **46 former winners become <=0, only 3 former losers become positive.** The top five winner opportunities alone give dramatic examples of downstream multiplier reductions (10000x→4340x, 5000x→604x, 7792x→442x, 10000x→497x, 6722x→283x); these are *ex-post attribution*, NEVER permitted live triggers.
- **Mechanism confirmed**: stop applied more broadly changes exits of profitable trades, loss avoidance and capital reinvestment; weaker accrued profits cause drastically altered future ATTACK sizing/multipliers. Huge losses then occur at a *different* equity peak/trough and the measured **percentage** DD can increase even while total lifetime gross dollar losses are smaller. Thus a smaller stop R or less total gross loss does NOT entail lower global DD. Finance is path-dependent. It is incorrect to say the 94% DD arose from the original 2020 drawdown episode or one specific 2019 loss.
- These numbers reconcile exactly at final signal-receipt PnL delta; this remains *historical mined holdout* and is not fresh OOS. **Reject** both variants; the 34.924% DD reference and USD582440.0253 floor remain the research constraints. Full Sovereign protection passes in these experiments but no provider margin certification or <=25% DD proof exists.

**Next targeted DD engineering**: protect the future high-payoff trades while reducing downside *during open positions* with causal price/regime and live equity constraints, plus independent MEDIUM risk modeling in 2019. Require winner opportunity cost, forward PnL, actual peak/trough episodes, global GL and all Sovereign ledger gates for every candidate. No late hindsight filters and no trade veto.
