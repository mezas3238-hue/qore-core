# QORE CORE — VT31 NAS100 MASTER CONTINUITY HANDOFF

## EDGE PURO · MÁXIMA INTELIGENCIA · CERTIFICATION CLOSURE

**Owner / CEO:** Sergio Meza  
**Repository source of truth:** `mezas3238-hue/qore-core`  
**Primary Architect-B branch:** `agent/vt31-edge-position-cert-b-001`  
**Branch checkpoint before this handoff:** `8d5b764b9104120fded7ec743e94ea5ef0ef6d14`  
**Architect-A branch:** `agent/vt31-edge-entry-reasoning-a-001`  
**Architect-A last observed checkpoint:** `b00b28868e7140aeff6c835669f84932ea774f3e`  
**Operational environment:** GitHub + GitHub Actions workflows + immutable replay artifacts. VPS/Desktop Commander is unavailable and must not be treated as a required execution path.

---

# 1. OWNER SOVEREIGN RULES

## 1.1 Certification is pure trader edge

VT31 must certify from its own trading quality:

`ENTRY EDGE + EXIT EDGE + WINNER PRESERVATION`

Certification may not be obtained, improved, rescued, or cosmetically repaired by:

- position sizing;
- dynamic sizing;
- reducing volume because a stop is wide;
- increasing volume after losses;
- leverage as a certification improver;
- compounding as a certification improver;
- CIBO capital rescue;
- risk budgeting;
- portfolio allocation;
- capital weighting;
- special lot logic.

If VT31 only passes because economic exposure is changed, VT31 is **not certified**.

The geometry must be tradable on its own.

## 1.2 R is allowed

Critical clarification from Owner:

> **R IS NOT FORBIDDEN. SIZING TO OBTAIN CERTIFICATION IS FORBIDDEN.**

VT31 may use R as genuine trader logic for:

- entry geometry;
- stop management;
- breakeven;
- trailing;
- partials;
- fixed/adaptive R targets;
- target extensions;
- MFE/MAE logic;
- combinations of R + structure + liquidity + cognition.

A rule such as `+3R -> breakeven` is eligible if it causally improves the trader.

A rule is rejected because its economics or robustness are inferior, **not because it contains R**.

R may never be used to change volume for certification.

## 1.3 Universal volume invariance

VT31 produces the same market decision independently of provider-permitted volume.

The trade must be logically identical at:

`0.01, 0.02, 0.05, 0.10, 1.00, ...`

Volume belongs to provider/execution adaptation only.

The certification harness uses equal/neutral trade weighting and ignores capital-engineering fields.

## 1.4 Maximum intelligence is mandatory

VT31 may not certify using a reduced or convenience slice of its intelligence.

For every applicable decision VT31 must use the maximum causal intelligence available, including:

- strategy identity;
- prior-day context;
- H4 context;
- H1 context;
- M15 context;
- M1 microstructure/execution;
- structure;
- liquidity;
- regime;
- volatility;
- timing/freshness;
- entry intelligence;
- risk geometry;
- journey/position intelligence;
- target/exit intelligence;
- Strategy Identity Memory;
- CIBO NAS100 Market Memory;
- Trader Experience / Lab Memory;
- Cognitive Memory;
- cross-index context when causally available;
- full post-entry reassessment;
- strategy-native R when evidence supports it.

A module may be neutral or non-applicable. What is forbidden is silently bypassing applicable available intelligence to simplify certification.

## 1.5 Timeframe interpretation

Silver Bullet is not an H4 execution strategy.

Current architecture:

- H4/H1/M15 = higher/intermediate context;
- M1 = causal microstructure and execution path;
- H4 informs the brain; it does not become the execution candle.

M15 is now explicitly reconstructed from fully closed NY-aligned M1 buckets without lookahead.

## 1.6 Governance

Until Owner explicitly changes authority:

- NO MERGE;
- NO LIVE;
- NO REAL CAPITAL;
- NO PRODUCTION;
- fresh holdout remains sealed until an exact candidate is frozen;
- GitHub is source of truth;
- all current replay work is on consumed evidence.

---

# 2. EDGE-ONLY CERTIFICATION HARNESS COMPLETED

Canonical module:

`src/qore/infrastructure/traders/vt31_nas100_edge_certification.py`

Major properties already implemented:

- structural/equal-R terminal economics;
- ignores/removes sizing/capital fields from edge metrics;
- volume agnostic;
- R runtime strategy allowed;
- R-driven volume changes forbidden;
- cost stress;
- temporal year/era/fold metrics;
- deterministic moving-block Monte Carlo;
- winner preservation;
- candidate-freeze governance;
- maximum-intelligence governance.

Important hardening already completed:

- empty samples cannot accidentally pass PF;
- non-empty all-winner samples retain mathematically infinite PF semantics;
- provider minimum volume is not trader certification authority;
- final report states certification basis as entries/profits/edge only.

Final risk-adjusted convention is intentionally still unbound:

- descriptive trade-period Sharpe is available;
- descriptive trade-period Sortino is available;
- final certification annualization/convention has **not yet been frozen**.

This remains a certification-closure task.

---

# 3. EARLY POSITION-MANAGEMENT RESEARCH

## 3.1 Structural protection / Journey Lock

Development survivor:

`LBB_PATH_SHALLOW_PS1`

Mechanism:

- cognition identifies the eligible structural state;
- first confirmed M1 protective swing;
- effective next M1;
- one stop improvement;
- never widens;
- no sizing.

It improved consumed folds but did not solve the complete certification problem.

## 3.2 Deep Giveback Rescue

Burned research found a narrow rescue region using R/MFE/giveback.

Important Owner correction:

DGR is **not invalid merely because it uses R**.

However its original evidence remains only burned development evidence and is not a runtime/certification authority.

It must compete against newer full-cognition management rather than be promoted directly.

## 3.3 Generic early-no-progress

Global 5M and 8M scratch rules were rejected.

Reason:

- they improved some folds;
- they damaged R6 by cutting trades that later became structural winners.

Conclusion:

"no progress after N minutes" is not sufficient thesis invalidation.

A reference-liquidity-sweep substate looked promising post-hoc but was not promoted because it was discovered after reading outcomes.

---

# 4. R-MANAGEMENT FRONTIER COMPLETED

Document:

`docs/research/VT31_ARCH2_SOVEREIGN_R_FRONTIER_FINDINGS_001.md`

Workflow:

`37402739775` — SUCCESS

Variants:

- STRUCTURAL_ONLY
- BE_1R
- BE_2R
- BE_3R
- BE_4R

No sizing/capital engineering was used.

## Findings

No universal context-blind BE threshold survived.

### BE 1R
- PF non-degrading: 4/4
- mean-R non-degrading: 1/4
- DD non-degrading: 3/4
- winner preservation: FAIL

### BE 2R
- PF non-degrading: 2/4
- mean-R non-degrading: 0/4
- DD non-degrading: 2/4
- winner preservation: FAIL

### BE 3R
- PF non-degrading: 3/4
- mean-R non-degrading: 2/4
- DD non-degrading: 3/4
- global winner preservation: FAIL

Consumed recent 2Y:
- PF 1.0464 -> 1.1000
- mean +0.0406R -> +0.0751R
- DD 13.83R -> 12.83R

### BE 4R
- PF non-degrading: 3/4
- mean-R non-degrading: 2/4
- DD non-degrading: 3/4
- global winner preservation: FAIL

Consumed:
- PF 1.0464 -> 1.1566
- mean +0.0406R -> +0.1240R
- DD 13.83R -> 12.83R
- winner count/R preservation: 100% / 100%

But R5/R8 lose too much winner-R.

Scientific conclusion:

**R is useful, but a universal R threshold is too crude. R management must be routed by full cognition + live journey state.**

---

# 5. MAXIMUM-COGNITION ARCHITECTURE COMPLETED

## 5.1 M15 wiring

M15 was originally missing as an explicit causal layer.

This was repaired.

M15 now comes from:

- M1 source evidence;
- fully closed 15-minute buckets;
- NY alignment;
- no future bars;
- no lookahead.

The prior `M15_CONTEXT_UNWIRED` blocker is closed.

M15 was tested as a standalone directional gate and was not stable enough to become an isolated buy/sell prohibition.

Correct role:

**M15 remains one component of multidimensional cognition, not a standalone veto.**

## 5.2 Full cognition accounting

The runtime now audits whether all applicable information is present/accounted for.

Important semantic repair:

Two concepts are separated:

### FULL COGNITIVE ACCOUNTING

Means the available causal information and memory bundle are completely represented and auditable.

This is required for research/calibration.

### MAXIMUM INTELLIGENCE CERTIFICATION-READY

Means, in addition, all applicable action policies are calibrated and no certification blocker remains.

A trader cannot be called maximum-intelligence certified simply because it observes all fields.

## 5.3 Memory sovereignty

Maximum-cognition sovereignty has been persisted into:

- Strategy Identity Memory;
- Trader Experience / Lab Memory;
- Cognitive Memory bundle.

The trader must consult the complete memory bundle.

---

# 6. CRITICAL POST-ENTRY REASONING REPAIR

The architecture now separates:

- `reason()` = admission reasoning for a **new** trade;
- `reason_position()` = reasoning for a **live already-admitted** trade.

This repair was essential.

Entry-only predicates such as:

- late entry cutoff;
- new-entry compression gate;
- low-DD reference admission rules;

remain visible in audit but no longer become automatic EXIT/PROTECT authority after the trade exists.

Post-entry cognition now:

1. preserves the frozen entry thesis;
2. rebuilds the current Situation Model from causal newly closed market data;
3. re-runs current reasoning;
4. re-synthesizes full cognition;
5. decides HOLD / protection / extension / exit from live position information.

This prevents admission logic from masquerading as position-management logic.

---

# 7. POST-1R JOURNEY CALIBRATION COMPLETED

Document:

`docs/research/VT31_ARCH2_POST_1R_MAX_COGNITION_CALIBRATION_FINDINGS_001.md`

Workflow:

`37403585235` — SUCCESS

Exact sovereign specialist populations:

- R5: 54 trades
- R6: 37
- R8: 33
- recent consumed 2Y: 48

Observation horizons were predeclared:

- H2 = 2 closed M1 after first unambiguous +1R;
- H3 = 3;
- H5 = 5.

Future journey labels were research-only.

## Stable H5 mechanism

### PERSISTENT_1R_FLOOR

Eventual 3R+:
- R5 100%
- R6 100%
- R8 100%
- consumed 80%

Generic BE should not cut this state.

### RECOVERED_1R_FLOOR

Eventual 3R+:
- R5 100%
- R6 80%
- R8 100%
- consumed 100%

Runner-supportive.

### POSITIVE_BELOW_1R

Giveback:
- R5 55.56%
- R6 33.33%
- R8 60%
- consumed 80%

This is caution/deterioration, not deterministic failure.

### ENTRY_OR_WORSE

Observed sample is tiny, but:
- eventual 3R+ = 0% in 4/4
- giveback = 100% in 4/4

Eligible only for conservative causal testing.

---

# 8. FULL-COGNITION POST-1R MANAGEMENT — 4/4 SURVIVOR

Document:

`docs/research/VT31_ARCH2_POST1R_FULL_COGNITION_FINDINGS_001.md`

Workflow:

`37405258891` — SUCCESS

Status:

**CROSS-FOLD RESEARCH SURVIVOR / NOT CANDIDATE-FROZEN**

All H2/H3/H5 full-cognition variants passed:

- PF non-degrading 4/4;
- mean-R non-degrading 4/4;
- DD non-degrading 4/4;
- winner count preservation 100% every fold;
- winner-R preservation 100% every fold;
- half-years non-degrading.

## H3 is current best-balanced research witness

### R5

Baseline:
- PF 1.916915
- mean +0.748814R
- total +40.435968R
- DD 12.600000R

H3:
- PF 2.025267
- mean +0.792506R
- total +42.795317R
- DD 11.907317R
- winner preservation 100% / 100%

### R6

Baseline:
- PF 2.303462
- mean +1.109704R
- total +41.059062R
- DD 12.744444R

H3:
- PF 2.378986
- mean +1.136731R
- total +42.059062R
- DD 12.744444R
- winner preservation 100% / 100%

### R8

H3 correctly did nothing economically:

- PF 2.670846
- mean +1.329082R
- total +43.859711R
- DD 11.661905R
- winner preservation 100% / 100%

This is important: full cognition learned that HOLD / no intervention can be the best action.

### Recent consumed 2Y

Baseline:
- PF 1.046435
- mean +0.040631R
- total +1.950268R
- DD 13.834146R

H3:
- PF 1.069586
- mean +0.059570R
- total +2.859359R
- DD 12.925055R
- winner preservation 100% / 100%

Every half-year is non-degrading.

## Mechanism behavior

Sparse/selective management rather than aggressive protection.

Examples:

- R5: 1 BE arm, 2 depleted exits, 30 runner holds;
- R6: 1 BE arm, 14 runner holds;
- R8: 19 runner holds, zero economic modification;
- consumed: 1 depleted exit, 24 runner holds.

This is the strongest Architect-B position-management result so far.

It does **not** solve the consumed edge deficit by itself.

---

# 9. TARGET-DEPTH / DOL CALIBRATION — STATISTICAL PASS 4/4

Document:

`docs/research/VT31_ARCH2_FULL_COGNITION_TARGET_DEPTH_FINDINGS_001.md`

Workflow:

`37440683395` — SUCCESS

Head tested:

`52d7b443e15802250936e1a89db5a9b90fda3d91`

Aggregate artifact:

`11401715062`

Exact sovereign terminal populations:

- R5 54
- R6 37
- R8 33
- recent consumed 48

DOL1 touch was **not** treated as acceptance.

Acceptance required a subsequent fully closed M1 beyond DOL1 in trade direction.

## Results after DOL1 acceptance

### R5
- accepted: 10 / 54
- DOL2: 90%
- DOL3: 60%
- DOL4: 20%

### R6
- accepted: 6 / 37
- DOL2: 100%
- DOL3: 83.33%
- DOL4: 83.33%

### R8
- accepted: 8 / 33
- DOL2: 100%
- DOL3: 75%
- DOL4: 37.5%

### Recent consumed 2Y
- accepted: 7 / 48
- DOL2: 71.43%
- DOL3: 57.14%
- DOL4: 28.57%

Predeclared gates all passed:

- non-zero DOL1 acceptance 4/4;
- DOL2 >=70% 4/4;
- DOL3 >=50% 4/4.

Therefore:

- `dol2_calibration_witness = true`
- `dol3_calibration_witness = true`

## Physical execution discovery

A hard take-profit at DOL1 cannot later decide to extend after DOL1 acceptance because the trade would already be closed.

Therefore target intelligence needs a **soft DOL1 checkpoint** and finite causal acceptance window.

Predeclared windows:

- next closed M1;
- within 3 closed M1;
- within 5 closed M1.

If acceptance fails inside the window -> exit at observed close.

If acceptance occurs -> evaluate extension to DOL2/DOL3.

---

# 10. TARGET-DEPTH ECONOMIC FRONTIER — CURRENTLY RUNNING

Script:

`scripts/vt31_nas100_target_depth_economic_frontier_v1.py`

Workflow:

`.github/workflows/vt31-target-depth-economic-frontier-v1.yml`

Workflow run at handoff time:

`37441363254`

Workflow head:

`8473ab0c0ac4fefa15e7b7e15aaa21cc0c71d24e`

Status at handoff creation:

**IN PROGRESS**

Do not claim a result until this run completes.

This is the immediate next result the next architect must read.

Purpose:

- test soft DOL1 finite acceptance windows;
- test economically executable DOL2/DOL3 extension;
- preserve equal/neutral certification exposure;
- preserve winner-R;
- keep sizing completely out.

---

# 11. CURRENT CERTIFICATION ECONOMICS — IMPORTANT

The current entry population is still the primary certification bottleneck.

Recent sovereign baseline / full-cognition management shows:

- R5 strong;
- R6 strong;
- R8 strong;
- recent consumed 2Y remains weak.

Best H3 recent consumed result:

- PF **1.069586**
- mean **+0.059570R**
- total **+2.859359R**
- DD **12.925055R**
- winner count preservation 100%
- winner-R preservation 100%

This is positive but still below Owner final gates.

Therefore Architect B must **not** try to manufacture certification with increasingly aggressive exits.

If target-depth economics cannot lift recent consumed sufficiently without winner destruction, the remaining root issue is entry/admission edge and belongs to Architect A.

---

# 12. ARCHITECT A STATUS / ENTRY-SIDE BLOCKER

Architect-A branch:

`agent/vt31-edge-entry-reasoning-a-001`

Last observed checkpoint:

`b00b28868e7140aeff6c835669f84932ea774f3e`

Message:

`docs(vt31): define architect A edge-only entry reasoning scope`

Observed date:

2026-10-05T20:06:18Z

Architect A has not kept pace with Architect B.

A handoff of entry defects already exists:

`docs/research/VT31_ARCH2_TO_ARCH1_EDGE_DEFECT_EVIDENCE_001.md`

Stable negative consumed cognition previously exposed to Architect A includes:

- Breaker + NEUTRAL;
- Breaker + SHALLOW;
- last structure breaker + breaker entry;
- latest structure breaker;
- CURRENT_PATH_NOT_COMPRESSED contradiction.

Stable positive regions include:

- FVG + DEEP;
- FVG + NEUTRAL;
- latest structure fair-value-gap, weaker.

These are evidence targets, not blind filters.

Architect A must solve admission/entry causally with maximum intelligence, not by deleting trades after seeing outcomes.

---

# 13. WHAT REMAINS BEFORE VT31 CAN CERTIFY

The next architect must execute in this order.

## Phase A — finish target-depth economics

1. Read run `37441363254`.
2. Download/read all fold + aggregate artifacts.
3. Compare soft DOL1 acceptance windows 1/3/5 M1.
4. Determine whether whole-position DOL2/DOL3 extension:
   - improves PF/expectancy;
   - improves or preserves DD;
   - preserves winner count >=80% / preferred 90%;
   - preserves winner-R >=90% / preferred 95%;
   - remains stable by half-year/fold.
5. Reject any target-depth policy that wins only by sacrificing runner quality.
6. If an economic survivor exists, encode it causally into Position Intelligence.
7. Remove DOL2/DOL3 certification blockers only when economic actuation, not merely statistical reach, is validated.

## Phase B — finalize contextual management actuation

The H3 full-cognition mechanism is the current leading consumed research witness.

Next architect must:

1. convert research witness into an exact deterministic candidate contract;
2. ensure live-position `reason_position()` owns position authority;
3. preserve entry reasoning separately;
4. preserve the full memory bundle;
5. verify no future journey label leaks into action;
6. verify post-entry M15/H1/M1 states are causal;
7. re-run R5/R6/R8/consumed after target-depth logic composes with H3 management;
8. test interaction, because two individually good mechanisms can still conflict.

## Phase C — close maximum-intelligence blockers honestly

Current code can still emit blockers such as:

- `DEEPER_JOURNEY_CAPACITY_UNCALIBRATED`
- `CONTEXTUAL_POSITION_MANAGEMENT_UNRESOLVED`
- `DOL2_TARGET_INTELLIGENCE_UNCALIBRATED`
- `DOL3_TARGET_INTELLIGENCE_UNCALIBRATED`

M15 blocker has been solved.

Do not simply delete blocker strings.

Each blocker may be removed only after its causal runtime policy has been validated and wired.

Research accounting and certification-ready intelligence must remain separate.

## Phase D — entry/admission repair

This is likely the largest remaining economic task.

Recent consumed PF around 1.07 is far below final certification target.

Architect A must use maximum intelligence to improve:

- entry timing;
- M1 precision;
- invalidation geometry;
- stale opportunity rejection;
- structure/liquidity interpretation;
- regime/volatility compatibility;
- Breaker false positives;
- opportunity aging;
- rearm/new-event logic.

Absolutely no sizing rescue.

Architect B should provide evidence but must not silently take ownership of entry gates.

## Phase E — compose A + B

After Architect A improves admission:

1. combine the frozen entry candidate with Architect-B H3 management;
2. combine validated target-depth economics;
3. re-run all consumed folds;
4. confirm same causal definitions across folds;
5. ensure no outcome-derived fold identity enters runtime.

## Phase F — bind final certification metrics

The edge harness still needs a final fixed convention for:

- Sharpe;
- Sortino.

Current trade-period descriptive values are not silently accepted as the final certification convention.

Freeze the exact convention **before** final exam.

## Phase G — candidate freeze

Only freeze when:

- entry candidate is exact;
- management candidate is exact;
- target-depth policy is exact;
- all applicable maximum-intelligence blockers are closed;
- sizing/capital neutrality is proven;
- R-management contract is explicit;
- same logic runs across provider-permitted volumes;
- all consumed development gates pass strongly enough to justify fresh holdout.

Generate exact:

- candidate ID;
- source SHA;
- config;
- fingerprints;
- evidence exclusions;
- runtime-governance manifest;
- intelligence-completeness manifest.

## Phase H — one-shot fresh holdout

Only after freeze:

- open the sealed fresh holdout once;
- no retuning on its outcomes;
- run equal/neutral edge certification;
- measure PF, expectancy, payoff, DD, winner preservation, severe costs, temporal stability, Monte Carlo, Sharpe/Sortino under frozen convention;
- if failed, holdout is consumed and candidate is not certified.

## Phase I — final certification

Owner target gates remain approximately:

- PF OOS each era >=1.50;
- combined >=1.70, preferred >=2.00;
- expectancy >0, target >=+0.15R/trade;
- DD <=10R preferred 6–8R;
- reject >15R;
- Sharpe >=1.50 preferred >=2.00;
- Sortino >=2.00;
- payoff >=1.20 preferred >=1.50;
- MC positive terminal >=90%, preferred >=95%;
- MC p95 DD <=15R preferred <=10–12R;
- severe-cost PF >1;
- winner preservation >=80% count / >=90% R, preferred 90% / 95%;
- positive/stable by year/era/fold.

No sizing may be used to reach any of these gates.

---

# 14. WHAT THE NEXT ARCHITECT MUST NOT DO

Do not:

- use sizing to rescue consumed PF/DD;
- assume R is prohibited;
- remove 3R-BE or any R mechanism solely because it uses R;
- promote universal BE1/2/3/4 despite failed cross-fold winner preservation;
- use H4 as the Silver Bullet execution timeframe;
- use M15 as an isolated directional veto because consumed evidence does not support that;
- treat DOL1 touch as DOL1 acceptance;
- hard-close at DOL1 and then pretend extension can be decided later;
- use future labels in runtime;
- use entry-only contradictions as live-position exit authority;
- call full accounting "maximum intelligence certification-ready";
- remove blocker flags without calibrating their actual runtime behavior;
- open fresh holdout before freeze;
- merge;
- enable LIVE/real capital/production.

---

# 15. IMMEDIATE NEXT COMMANDMENT

At the start of the new chat:

1. re-fetch branch `agent/vt31-edge-position-cert-b-001`;
2. verify current HEAD because branch is actively advancing;
3. read workflow `37441363254` first;
4. adjudicate target-depth economics;
5. integrate only a genuine cross-fold survivor;
6. rerun composition with H3 full-cognition management;
7. if recent consumed still misses certification materially, escalate the defect to Architect A rather than compensating with management or sizing;
8. continue until all maximum-intelligence blockers and edge gates are genuinely closed.

---

# 16. CORE PRINCIPLE FOR CONTINUITY

> **VT31 MUST LEARN TO TRADE BETTER, NOT LEARN TO HIDE BAD TRADES WITH CAPITAL ENGINEERING.**

And simultaneously:

> **VT31 MUST USE THE MAXIMUM CAPACITY OF ITS OWN INTELLIGENCE TO DECIDE WHEN TO ENTER, WHEN TO WAIT, WHEN TO HOLD, WHEN TO PROTECT, WHEN TO EXTEND AND WHEN TO EXIT.**

The target is not merely a profitable backtest.

The target is a **causal, volume-invariant, maximum-intelligence NAS100 Silver Bullet trader whose edge survives certification without sizing rescue.**
