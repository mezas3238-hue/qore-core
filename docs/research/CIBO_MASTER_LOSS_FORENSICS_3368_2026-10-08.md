# CIBO MASTER LOSS FORENSICS — 3,368/3,368 trades, all big losses first

**Date:** 2026-10-08. **Priority:** sovereign P0 loss-concentration forensic study **before** more blind DD-parameter sweeps. **Repo:** `mezas3238-hue/qore-core`. **Research branch:** `agent/cibo-complete-loss-forensics-3368-h1-001`, isolated from concurrent architect. **Frozen input:** G2 `w8-p4020.json`, [successful run 37756517100](https://github.com/mezas3238-hue/qore-core/actions/runs/37756517100), artifact **11541140276**. G2 base commit `1ef9abcc9d21079cf3dcd1f0fe21131b87a071ed`. Historical research replay is *not* an unused out-of-sample holdout.

## 1. Critical finding — address the FULL LOSS BOOK, not only ATTACK or just one max DD event

Parsed **all 3,368** causal Trader Lab settlement receipts, not selected screenshots. Net-settlement accounting:
- **1,637 negative** receipts; **1,731 positive** receipts; zero flat.
- Accumulated negative settlements / gross loss **USD 942,631.9691091011**.
- Accumulated positive settlements / gross profit **USD 1,614,167.9758681149**.
- Net all settlements **USD 671,536.0067590**; initial capital USD 60 => final **USD 671,596.0067590**, cross-checks CIBO replay.
- **ATTACK**: 860 trades, **442 losers**, gross losses **USD 941,071.8523** (**99.834%** of total), 418 winners with **USD 1,612,367.22** gross positive P&L; mode net **+USD 671,295.36**.
- **MEDIUM**: 2,508 trades, 1,195 losers, gross losses **USD 1,560.1168** (**0.166%** of total), 1,313 winners with USD 1,800.76 gross positive P&L; mode net **+USD 240.64**.

**Therefore:** loss capital concentration and peak-to-trough max DD are NOT interchangeable. ATTACK owns almost all dollars lost and most capital growth, but a small early MEDIUM cluster controls the worst **37.65314425098%** DD. Optimizing only aggregate USD GL may improve profit without moving DD; optimizing only bootstrap MEDIUM may lower DD by tiny fractions while leaving huge ATTACK losses.

### Concentration of losses — by descending realized loss (all modes)

| Largest losing trades | Sum of realized losses (USD) | Share of ALL USD gross losses |
|---:|---:|---:|
| 1 | 54,100.00 | 5.74% |
| 3 | 136,000.00 | 14.43% |
| 5 | 200,900.00 | 21.31% |
| 10 | 315,393.26 | 33.46% |
| 20 | **457,209.57** | **48.50%** |
| 30 | 545,234.14 | 57.84% |
| 50 | 663,509.62 | 70.39% |
| 100 | 840,546.42 | 89.17% |
| 200 | 936,314.43 | **99.33%** |

Only **200 of 3,368** events (~5.94%) contribute **99.33%** of gross loss by USD due to strong compounding/path-dependent risk scale. This is an *in-sample descriptive statistic*, not a valid reason to blacklist ex-post losers.

### Largest ten losses — complete receipts, no forward-looking eligibility

| Loss USD | Mode | Multiplier | Trader / instrument | Decision UTC |
|---:|---|---:|---|---|
| 54,100.00 | ATTACK | 10,000x | R34_XAUUSD | 2022-03-07 03:55 |
| 43,900.00 | ATTACK | 10,000x | R34_XAUUSD | 2022-04-01 04:15 |
| 38,000.00 | ATTACK | 10,000x | R34_XAUUSD | 2021-12-06 12:50 |
| 37,300.00 | ATTACK | 10,000x | R34_XAUUSD | 2021-11-01 06:30 |
| 27,600.00 | ATTACK | 10,000x | VT08_FOREX | 2021-08-05 13:00 |
| 25,700.00 | ATTACK | 10,000x | R34_XAUUSD | 2021-05-21 19:45 |
| 25,400.00 | ATTACK | 10,000x | R34_XAUUSD | 2021-08-09 04:50 |
| 24,300.00 | ATTACK | 10,000x | R34_XAUUSD | 2021-10-01 13:55 |
| 19,993.26 | ATTACK | 7,602x | R34_XAUUSD | 2021-04-20 16:40 |
| 19,100.00 | ATTACK | 10,000x | R43_GBPUSD | 2021-08-19 15:20 |

These are already-settled outcomes (NOT safe predictive input). The absolute top loss **−USD 54,100** had initial declared stop risk **USD 52,100** and **−1.04 realized net R**, suggesting large *pre-committed exposure plus provider costs*, not merely an unexpected post-stop crash. Analyze fee, spread, slippage and stop sizing per trade before inventing a “smarter exit.”

### Global exposure vs winners — do NOT disable high multipliers blindly

| Bucket | Trades | Losers | Gross losses USD | Gross winners USD | Net USD |
|---|---:|---:|---:|---:|---:|
| ATTACK <1,000x | 603 | 326 | 79,617.56 | 87,561.38 | **+7,943.82** |
| ATTACK 1,000–3,999x | 27 | 8 | 22,318.53 | 38,061.14 | **+15,742.61** |
| ATTACK 4,000–7,999x | 199 | 96 | 522,835.76 | 919,779.09 | **+396,943.34** |
| ATTACK >=8,000x | 31 | 12 | **316,300.00** | **566,965.60** | **+250,665.60** |
| MEDIUM <=14x | 2,508 | 1,195 | 1,560.12 | 1,800.76 | +240.64 |

High-multiplier groups generate BOTH exceptional loss and exceptional profit. Blind multiplier cap, force-exit or broad partial interventions previously destroyed compounding. Adaptive CIBO MUST protect winners and preserve economic-group coordination (Sizing, Adaptive Leverage, CIBO Compound, Portfolio Compound).

Aggregate modeled provider-cost charges: **USD 130,537.06 ATTACK** across ATTACK trades, **USD 54,583.93** on ATTACK losing trades; **USD 239.65 MEDIUM** overall. Actual brokerage live leverage/volume caps may invalidate simulation's 10,000x economic assumption; these are research numbers, not executable guarantees.

## 2. ALL top ten peak-to-trough DD episodes (with 22% gap, fixed-peak *diagnostic* only)

Extracted from `drawdown_forensics.top_10_episodes`; all time windows are observed post-hoc and CANNOT be used as forward intervention flags.

| Rank | Window start → trough | Max DD | Peak USD | Peak–trough loss USD | USD loss compression needed if peak unchanged for 22% |
|---:|---|---:|---:|---:|---:|
| 1 | 2019-07-19 → 2019-08-12 | **37.653%** | 79.764 | 30.034 | **12.486** |
| 2 | 2020-09-10 → 2020-10-05 | **37.017%** | 12,867.902 | 4,763.291 | **1,932.353** |
| 3 | 2020-04-03 → 2020-05-13 | **36.407%** | 703.837 | 256.245 | **101.401** |
| 4 | 2021-02-09 → 2021-02-26 | **36.229%** | 59,984.688 | 21,732.041 | **8,535.409** |
| 5 | 2020-01-31 → 2020-03-02 | **34.873%** | 114.098 | 39.789 | 14.688 |
| 6 | 2020-03-23 → 2020-03-26 | **32.345%** | 566.078 | 183.101 | 58.563 |
| 7 | 2019-11-04 → 2019-12-18 | **31.542%** | 95.641 | 30.167 | 9.126 |
| 8 | 2020-08-19 → 2020-08-26 | **31.389%** | 11,794.575 | 3,702.142 | 1,107.335 |
| 9 | 2020-05-21 → 2020-06-08 | **30.747%** | 1,203.965 | 370.182 | 105.310 |
| 10 | 2020-06-24 → 2020-06-30 | **30.080%** | 4,143.966 | 1,246.505 | 334.832 |

All ten exceed 30%: reaching 22% is a **multi-regime structural risk project**. Static peak arithmetic is not a simulation; any changed policy changes future winners, capital high-water marks and triggers. A realized DD target on the current replay cannot guarantee OOS DD.

### Episode 1: 2019 low-capital MEDIUM loss clustering

- Peak capital ~**USD 79.76**, trough decline **USD 30.03**, **37.653%** DD.
- **75 completed settlements within episode**, **51 negative** trades with gross negative P&L **USD 51.05**, **24 winners** with positive P&L **USD 21.01** => ~USD **−30.04** net (matches episode DD within timing/precision).
- **All 75 were MEDIUM**. Loss was a dense cluster of tiny 1x/2x stops, NOT 10,000x ATTACK.
- Major negative contributors by gross loss *during episode*: R34_XAUUSD ~USD12.94 (also ~USD11.47 winners), R43_GBPUSD ~USD11.68 (only ~USD1.92 winners). **Do NOT reject trades from either Trader**; identity is attribution only.
- To attain 22% holding peak fixed, lose <=USD17.55 instead of USD30.03: must find **USD12.49 improvement (~41.6% reduction of net DD loss)**, rather than G2's hundredths-of-a-dollar partial tuning.
- Examine pre-entry regime, previous settled streak, funding cap, planned stop-risk, and **only closed M5** adverse excursion/recovery information. CIBO can tighten stops/manage partials after entry but cannot veto Trader execution.

### Episode 2: 2020-09 ATTACK risk clustering

- Peak ~USD12,868, peak-to-trough loss USD4,763 (37.017%), with 63 settlements; 39 negative totaling **USD6,457**, 24 winners totaling **USD1,694**.
- ATTACK 14 settlements, gross negative ~USD6,425 and gross positive ~USD1,661; MEDIUM 49 settlements largely self-offsetting.
- Need roughly **USD1,932** less peak-to-trough loss to reach 22% at unchanged peak. Examine aggregate same-symbol stop-risk and recent loss clustering causally; no 2020 date whitelist.

### Episode 4: 2021-02 ATTACK risk clustering

- Original worst 2021 episode migrated after independent W8. New peak ~USD59,985, DD ~36.229%; peak-to-trough loss ~USD21,732.
- Within 62 settled events: ATTACK 27, gross negative **USD23,370**, positive **USD1,629**; MEDIUM 35 with minimal net economic impact.
- Needed ~**USD8,535** less loss at unchanged peak to reach 22%. 2021-02 ATTACK **realized** losses often ~5,000–8,106x; 8th causal window made meaningful GL+wealth gain in earlier research but other regimes remain >30%.

### Why total loss ranking alone is insufficient

A single large −USD54k in March 2022 strongly affects gross loss and final wealth but may NOT belong to any top-ten *percentage* DD epoch when the account is far larger. Conversely a −USD2.84 MEDIUM stop during a USD80 bootstrap epoch may be extremely important to percentage DD. Rank by **two independent metrics**: (A) contribution to USD gross loss/wealth and (B) incremental stress as fraction of THEN-live high-water capital and clustered stop risk.

## 3. Priority P0 empirical tests — focus on avoidable loss, with causal evidence

**A. Reconstruct the before-entry state for every one of 1,637 historical losing trades** and a matched set of 1,731 winners (same prior data/market regime), never leaking the eventual outcome into the decision. For each, record:
- Decision time, already-settled outcomes up to decision only, predecision bankroll/peak/DD, Sizing risk, ATTACK multiplier and incremental stop-risk, open positions, aggregate worst-case open-stop-risk vs (0.78 H) if aiming 22%; cross-symbol portfolio correlation scenarios, volume/spread/fees.
- Causal pre-entry cognition: expected structural R and dispersion, market posture, H4 compression, liquidity/spread, volatility/range, previous trader loss streak, time-in-position expectations. Missing signal = no risk clearance claim.
- Post-entry sampled **M5 close-only** MAE/MFE before planned exit, proportion of stop cases for which a smaller causal loss could actually have been achieved at subsequent open, and winners falsely interrupted.
- Classify **preventable vs unpreventable/unknown**, and then replay the full 3,368-settlement portfolio under each candidate shield.
- **No Trader blacklist and no rejected/deferred entry.** Trader authority to execute entries remains sovereign. CIBO controls financial management *after* entry.

**B. Independent loss-control families, no blind parameter spray:**
1. **Loss clustering headroom:** open stop-risk + candidate risk + clustered/correlated stress reserve must fit a *forward-only* portfolio DD risk budget; manage post-entry stops, partials, and ATTACK exposure at authorized economic limits. Model adverse slippage and non-fill, so no guarantee of hard 22% from stops.
2. **Tail-loss containment:** target preventable large >=USD5k ATTACK losses subject to THEN-known exposure fraction, cost and downside context; compare matched winners especially >=8,000x where gross profit USD566,966. Avoid disabling 10,000x indiscriminately.
3. **Bootstrap MEDIUM cluster compression:** detect worsening portfolio path near USD60–100 and 2019-like causal regime (not 2019 date). Evaluate multiple linked stops and evolving previous settled loss streaks; apply selective initial stop / closed-M5 exit, not uniform exit.
4. **Explicit provider-cost audit:** ATTACK costs in benchmark ~USD130,537. These costs amplify losing stop outcomes; simulate realistic net expected gains, slippage and margin to assess whether reduced net loss also preserves capital growth.
5. **Joint four-engine diagnostics:** risk/wealth changes attributed separately to Sizing, adaptive leverage, CIBO Compound, Portfolio Compound, open risk occupancy. Do not shift costs from ATTACK to sovereign or disable economic engines.

**C. Promotion gates:** direct successor must preserve 3,368/3,368 executed Trader entries, zero reject/defer, zero ATTACK sovereign breach, no lookahead, capital >=USD582,440.03 (**prefer >=USD671,596.01**), total+ATTACK GL no worse, DD decreasing and PF competitive. Previous G2 max DD 37.653144% is the starting baseline. Note **`sovereign_floor_breach_usd` ~84.617** on G2 is a separate outstanding accounting anomaly; no clean certification claim while unresolved. Re-run top ten episodes, not only worst. Fresh independently sealed three-year holdout only after final freeze.

## 4. Reproducibility and active work

- Source artifact `11541140276` from [G2 run 37756517100](https://github.com/mezas3238-hue/qore-core/actions/runs/37756517100) contains all 3,368 receipts; use `w8-p4020.json`.
- Audit generated locally from all 3,368 receipts into a full CSV loss book and top-200 loss CSV; derived figures recalc from receipts, not cherry-picked extreme examples.
- **G3** causal MEDIUM partial micro [run 37757591148](https://github.com/mezas3238-hue/qore-core/actions/runs/37757591148) and **G4** bootstrap stop [run 37757768704](https://github.com/mezas3238-hue/qore-core/actions/runs/37757768704) were already launched on separate branches. Their existing results may be inspected as supportive evidence, but **future engineering priority switches to full loss-forensic and matched winner-protection study**, not blind tuning. No autonomous promise of 22%.
- This report is the canonical P0 for the new forensics lane; do not overwrite or silently change another architect's research branch.

**Present milestone: 22% DD not achieved. “Trabajo cumplido” requires a verified new replay meeting all gates, not a loss-concentration observation.**

## 5. Previously running G3/G4 closed: do not keep blind sweeps

- [G3 37757591148](https://github.com/mezas3238-hue/qore-core/actions/runs/37757591148) SUCCESS, 9 replays, **STRICT_PARETO_CASES=[]**. An earlier MEDIUM adverse trigger `p4020-r35` lowered DD to **37.029711%**, but capital dropped to **USD665,735.99** and gross loss increased to **USD955,333.35** (from USD942,631.97). **Reject economic regression**.
- [G4 37757768704](https://github.com/mezas3238-hue/qore-core/actions/runs/37757768704) SUCCESS, 9 replays, **STRICT_PARETO_CASES=[]**. The mild bootstrap initial stop `bt-stop25-dd10` produced DD **41.109836%**, total GL **USD949,891.34**, capital ~USD671,611.75; other variants further degraded DD, many collapsed wealth. **Reject**.
- These negative scientific results reinforce the user's P0 directive to STOP parameter tuning divorced from causal loss classification and protection of winners. Keep G2 as the best verified carrier for this workstream; distinguish any concurrently discovered stronger Pareto candidate on the main architect branch.

## 6. SECOND-PASS CAUSAL CONTEXT FORENSICS (full manifest-to-receipt join)

- Fetched historical source artifact **11389331836**, member `single-account-manifest-native.json`; it contains **exactly 3,368** structured predecision opportunities. Joined by immutable `signal_fingerprint` to **all 3,368** receipts in G2 artifact 11541140276: **100% coverage, all 3,368 fingerprints unique**. Do NOT use `settlement_outcome_research_only` as a predictor. Treat `decision_context`/regime inputs as contextual hypotheses, and postsettlement P&L as analysis-only outcome labels.
- Stratified ATTACK >=4,000x: **230 trades**, 2021 n=103, 2022 n=121, 2020 n=6. Confirmed exposure has causal context columns `reg_h4_range_state`, `reg_m5_volatility_state`, `ctx_strategy_projected_r_bucket`, `ctx_reclaim_latency_bucket`, `ctx_close_location_bucket`, and more.
- Within >=4,000x, *historically observed* M5-volatility `compressed`: n=50, 48% losing, gross loss ~USD216,193, gross profit ~USD234,376, profit factor **1.08**; `balanced`: n=115, 43% losing, gross loss ~USD350,373, gross profit ~USD779,732, PF **2.23**. **Not causal proof**, and may be distorted by market regime, trader mix, capital size and period.
- Within >=4,000x, predecision `ctx_reclaim_latency_bucket<=5m`: n=107, GL ~USD497,757, GP ~USD743,359, PF **1.49**; `6-15m`: n=67, GL ~USD166,323, GP ~USD415,513, PF **2.50**. Hypothesis: overly rapid reclaim may be less reliable in certain regimes. Require matched baseline and walk-forward checks before any trade management rule.
- Within ATTACK >=4,000x, `ctx_strategy_projected_r_bucket=q5:>2.5` **year dependence**: 2021 **n=8, 4 losers**, GL ~USD36,308, GP ~USD96,105, PF **2.65**; 2022 **n=21, 18 losers**, GL ~USD113,501, GP ~USD25,741, PF **0.23**. Crucial **regime instability**: blocking this bucket globally would also eliminate 2021 winners, and 2022 dates must not become policy predicates. Investigate causal market regime, volatility/correlation and expectation calibration drift.
- First 20 >=4,000x ATTACK losses: median initial stop risk ~USD18,486.43; combined provider costs ~USD23,157.87, net realized R median ~−1.043. **Primary intervention candidate is controlling concentration of precommitted stop-risk and costs without blocking entries, not assuming a last-moment stop can magically avoid −1R losses.**

### High-priority time-provenance warning (independent of strategy leakage)

**All 3,368/3,368** historical manifest opportunities (with market dates 2019–2022) contain `market_predecision_state.provider_observation.observed_at` dated **2026-10-01**, later than each historical decision. This may intentionally represent a single frozen 2026 *broker contract/commission/symbol configuration* applied retrospectively; it **does NOT alone prove future-price alpha leakage**, but it must not be called a contemporaneous broker observation from 2019. Separate economic model input provenance from truly historical causal market features, and run historical fee/slippage/margin stress before certification. No strategy feature should consume a provider observation whose timestamp is later than decision time unless explicitly allowed as a fixed documented simulation assumption.

### Formal research hypothesis for next architect

1. Match high-risk losing ATTACK opportunities to winning ATTACK opportunities in the *same causal regime, risk level and prior portfolio state*; reconstruct stop-risk headroom, open overlapping positions and provider cost at entry.
2. Compute **net benefit of proposed post-entry risk management** on *both* populations using closed M5 bars and prior-only cognition, not ex-post loss labels.
3. Use expanding chronological validation within the reused study to assess feature stability; never use regime/year of known losses as production rules. Preserve the sealed truly independent three-year holdout.
4. Separate risk findings from scientific certification until provenance of 2026 economic provider assumptions and `sovereign_floor_breach_usd` are resolved.
