# VT08 CRT PURE — CONTINUITY ADDENDUM R2-CJ / R2-CK — 2026-10-13

**Repository sovereign:** `mezas3238-hue/qore-core`  
**PR:** [#626](https://github.com/mezas3238-hue/qore-core/pull/626) · branch `agent/vt08-crt-pure-source-identity-001`  
**Read with:** `VT08-CRT-PURE-MASTER-HANDOFF-2026-10-13.md` and previous R2CE/CF, R2CG/CH/CI addenda.  
**Purpose:** preserve research continuation, correction to capacity interpretation, real results, outstanding blockers and explicit task order. No certification.

## 1. Principal correction from GitHub reinspection

The earlier **R2-CG** bound (AUDUSD 151.91 and USDJPY 120.875 opportunities/year) is NOT a maximum CRT PURE structural capacity. It applies only to R2-CF's historical restricted-time, fixed-initial-decision + one-step WAIT population, excluding all terminal WAIT/ABSTAIN. This scope was not sufficiently emphasized in some continuation messaging.

Earlier validated rolling H4 research has **separate, higher opportunity capacity**:
- R2-AJ H4 lattice: six start times 01/05/09/13/17/21 NY, no new trading rule.
- R2-AK/AO + R2-AQ fixed 1.5R, structural stop, NEWEST competition, one attempt per parent, no EFF.
- AUDUSD **2,468 trades / 10 years = 246.8/year**.
- USDJPY **3,053 trades / 12 years = 254.4167/year**.

The true scientific bottleneck of rolling H4 is **economic suitability, not frequency**.

**Owner 2026-09-22 authority**: the file `VT08-CRT-PURE-OWNER-ENGINEERING-RESOLUTION-DIRECTIVE-001.md` explicitly authorizes QORE Engineering to resolve implementation ambiguities empirically with a separate research identity and preregistration; this does NOT require every engineering choice to be attributed word-for-word to RomeoTPT. Primary material retains canonical identity authority. Earlier R2-CI wording that only newly "source-authorized" engineering variants may be investigated was too restrictive. Correct the boundary: **Owner-authorized research allowed; canonical methodology changes and live/deployment NOT allowed without subsequent governance.** No sizing/volume/position authority for trader.

## 2. R2-CJ audit — archived rolling H4 long-history costs

- [Freeze](VT08-CRT-PURE-R2CJ-ROLLING-H4-COST-MARGIN-FREEZE-001.md)
- [Results](VT08-CRT-PURE-R2CJ-ROLLING-H4-COST-MARGIN-RESULT-001.md)
- Module `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2cj_rolling_cost_margin.py`, five unit tests, workflow `.github/workflows/vt08-crt-pure-r2cj-rolling-cost-margin.yml`.
- **Green authoritative CI**: [38452638123](https://github.com/mezas3238-hue/qore-core/actions/runs/38452638123), quality + AUDUSD + USDJPY succeeded, original reports and annual counts/PF/R reproduced.
- Runs consume exactly archived R2-AQ earlier run **35865028789** and R2-AO recent run **35863768335**, with SHA256 source evidence; no broker API. Costs hypothetical normalized R/trade only.

| Full history | AUDUSD 10y | USDJPY 12y |
|---|---:|---:|
| Entries | 2,468 | 3,053 |
| Density/year | 246.8 | 254.42 |
| PF gross | 1.00974499 | 0.94375362 |
| Gross total | +10.22574427R | -74.55860040R |
| Mean gross/trade | +0.00414333R | -0.02442142R |
| Max gross DD | 67.37729085R | 111.92396566R |
| Net at 0.005R/trade | -2.11425573R | -89.82360040R |
| Net at 0.02R/trade | -39.13425573R | -135.61860040R |
| Net at 0.05R/trade | -113.17425573R | -227.20860040R |

AUDUSD arithmetic break-even cost: **0.00414333R/trade**; smaller than even the 0.005R diagnostic. USDJPY already negative at zero friction. **High-density unfiltered candidate is NOT profitable/certified.**

## 3. R2-CK audit — six ex-ante H4 starts, NO filter promotion

- [Freeze](VT08-CRT-PURE-R2CK-SIX-START-TIMING-ATTRIBUTION-FREEZE-001.md)
- [Results](VT08-CRT-PURE-R2CK-SIX-START-TIMING-ATTRIBUTION-RESULT-001.md)
- Module `src/qore/infrastructure/trader_lab/vt08_crt_pure_r2ck_timing_attribution.py`, four unit tests; workflow `.github/workflows/vt08-crt-pure-r2ck-timing-attribution.yml`.
- **Authoritative CI**: [38453530235](https://github.com/mezas3238-hue/qore-core/actions/runs/38453530235), quality + AUDUSD + USDJPY SUCCESS; original AO/AQ and R2CJ reconciled.
- Operational bug fixed: first two R2-CK workflow runs `38453200166` and `38453391681` invoked R2-CJ due a copied workflow command. Those green runs are INVALID as evidence for per-H4 labels. Corrected commit `c9532147ae7dd2533a974efd067d1ff80bcda509` and authoritative run above.
- No multiple-testing statistical claim: the six strata have been seen in an already explored data sample, so any apparently good time label is EXPLORATORY.

Combined modeled **0.02R per-trade** results:

| H4 start NY | AUDUSD net / 10y | USDJPY net / 12y |
|---|---:|---:|
| 01:00 | -21.94307107R | -25.24247395R |
| 05:00 | -21.95227641R | **+8.59419901R** |
| 09:00 | -16.74054370R | -22.93287683R |
| 13:00 | -3.79943908R | -1.21252099R |
| 17:00 | **+36.98913996R** | -50.18021636R |
| 21:00 | -11.68806543R | -44.64471128R |
| ALL STARTS | -39.13425573R | -135.61860040R |

AUDUSD 17 NY = **450/10y = 45/year**, positive after 0.02R in both older (190 trades, +25.50332665R) and recent (260, +11.48581331R). USDJPY 05 NY = **472/12y = 39.33/year**, net positive in older (240, +6.03559982R) and recent (232, +2.55859919R). Each is **far below 170/year** by itself; recent USDJPY advantage is marginal and annual years positive only 3/6.

**DO NOT now make AUDUSD 17 NY / USDJPY 05 NY trade filters**: winners were observed post hoc among six tested strata; older/recent windows were already consumed by research; results do not prove a causal transferable edge, and trading those single hours cannot meet the original density research goal.

## 4. Economic and governance consequences

- True engineering problem is to identify causal pre-entry information that separates suitable from unsuitable **across multiple H4 starts while retaining enough trades**.
- Current replay R-multiples and simplistic R cost stress are not broker BID/ASK validated fills. No demonstrated real economic edge after realistic costs.
- Rolling-H4 parent windows overlap in time; one selected hypothesis per parent is NOT proof of no simultaneous open positions from different parents. This remains a live risk/sequencing gate, not trader sizing authority.
- BTCUSD research market certification remains frozen, no USDJPY/AUDUSD experience transfer.
- Historical R2-G alternatives, R2-AJ H4 windows, R2-AM EFF suitability failures, R2-AR and subsequent context/WFO research should be read **before** proposing an already-tested filter.
- The expected-R and post-outcome state analyses of R2-CK are exploratory; no data snooping promoted to frozen strategy.

## 5. Exact next architect checklist

1. Audit whether parent-overlap / execution collision can **reduce executable** density from the historical 246.8/254.42 trades/year: use immutable prior rolling ledger to count same-entry timestamp, same source under different parent C3, and inspect lifecycle concurrency if reliable exit timestamps can be reconstructed causally. Do not generate trades.
2. Read R2-AR/M/N+ suitability WFO, R2-J/K/L and consumed full-year window outcomes. Build a **negative-results register** of already falsified market suitability features to avoid repeating them.
3. If a non-redundant causal pre-entry regime hypothesis emerges, preregister one bounded high-retention model with fixed feature set and train-only thresholds; predeclare annual density floor, maximum acceptable DD, economic margin and cost stress at 0.02/0.05R. Never select one profitable session from R2-CK as a finished policy.
4. Evaluate independent chronological holdout not used for designing that hypothesis. If none remains, mark `BLOCKED_DATA/NO_FRESH_HOLDOUT` until equivalent new evidence is acquired; do not dress consumed old history as OOS.
5. Once true edge + density + drawdown + cost robustness exists, follow certification gates per trader. If none exists, accurately close this scope as `NO_SUPPORT` rather than endlessly manufacturing candidates.
6. Never use sizing/lot/volume/leverage/capital budgeting in VT08; CIBO/QORE Risk owns capital authority. No merge, VPS, DEMO, LIVE, production, FundedNext live or real capital.

**New master continuation checkpoint:** this document + linked result files at the latest PR branch head. These are fully archived, reproducible, and read-only. Global trader **NOT CERTIFIED**.
