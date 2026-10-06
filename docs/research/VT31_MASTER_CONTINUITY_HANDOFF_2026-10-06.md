# QORE CORE — VT31 NAS100 MASTER CONTINUITY HANDOFF

## PURE EDGE CLOSURE -> <=6R HARD GATE -> FINAL ROBUSTNESS -> FRESH HOLDOUT -> CERTIFICATION

**Owner / CEO:** Sergio Meza  
**Repository source of truth:** `mezas3238-hue/qore-core`  
**Canonical working branch:** `agent/vt31-edge-position-cert-b-001`  
**Current canonical research HEAD:** `e2c2ff6fef485cd445d461b422aa47df415c3b55`  
**Latest decisive workflow:** `37508820071` — QORE VT31 Rapid Breaker Conflict Admission Frontier V1 — SUCCESS  
**Status:** VT31 IS NOT CERTIFIED. Fresh holdout remains sealed.

---

## 0. SOVEREIGN DIRECTIVE FOR THE NEXT ARCHITECT

Continue immediately from the current branch and evidence. Do not restart the research from zero and do not resurrect superseded certification rules.

The mission is now extremely narrow:

1. preserve the current pure-edge economic gains;
2. reduce the remaining recent observed maximum drawdown from approximately `6.5934R` to `<=6.00R`;
3. keep every consumed historical fold at `<=6R`;
4. retain the current PF/expectancy/Monte Carlo/winner-preservation quality;
5. complete final robustness metrics and causal/runtime parity;
6. freeze the exact candidate;
7. open the fresh sealed holdout exactly once;
8. certify only if every sovereign gate passes.

No sizing, dynamic sizing, leverage, compounding, portfolio allocation, capital weighting, exposure masking, CIBO capital rescue, or equivalent monetary engineering may be used to obtain certification.

Sovereign rule:

> R is allowed as trader logic. Sizing to obtain certification is forbidden.

Use the maximum available causal intelligence. Available cognition may be neutral, but may not be silently bypassed.

---

## 1. CANONICAL CERTIFICATION STANDARD

Canonical file:

`docs/research/VT31_NAS100_SOVEREIGN_TRADER_CERTIFICATION_STANDARD_001.md`

Current requirements:

- observed maximum DD `<=6R` HARD GATE;
- `6.00R` may PASS, `6.01R` FAILS;
- old observed-DD thresholds of 10R and 15R are superseded;
- certification must be PURE EDGE / equal-R;
- market decisions must be invariant to absolute volume;
- sizing, leverage, compounding, portfolio weighting and capital rescue are forbidden during trader certification;
- R-based stop/target/management logic is allowed when causally justified;
- maximum applicable intelligence is mandatory;
- OOS/era PF `>=1.50`;
- combined PF `>=1.70`, preferred `>=2.00`;
- expectancy `>0R/trade`, operational target about `>=+0.15R/trade`;
- payoff `>=1.20`, preferred `>=1.50`;
- Sharpe `>=1.50`, preferred about `>=2.00`;
- Sortino `>=2.00`;
- Monte Carlo positive-terminal probability about `>=90%`, preferred `>=95%`;
- no severe clustering/fragility;
- temporal/OOS robustness across eras, years, regimes, folds and meaningful blocks;
- degraded-cost PF must stay `>1.0`;
- winner preservation approximately `>=80%` winner count and `>=90%` winner-R;
- exact candidate and formulas must be frozen before fresh holdout;
- fresh holdout may be opened once; no retuning after opening;
- no future outcome, oracle, fold/date identity, consumed-holdout reuse, or evidence mixing may certify a candidate.

Monte Carlo p95 DD is a separate robustness metric. It is NOT the observed-DD 6R certification gate.

---

## 2. ARCHITECTURAL RULES THAT MUST NOT BE BROKEN

Certification is:

`ENTRY EDGE + EXIT EDGE + WINNER PRESERVATION + MAXIMUM CAUSAL INTELLIGENCE`

Current architecture:

- H4/H1 = higher-timeframe causal context;
- M15 = causal context but not an isolated directional veto;
- M5/M1 = execution, especially Silver Bullet;
- frozen entry thesis is separated from post-entry reasoning;
- `reason()` handles entry reasoning;
- `reason_position()` / full position cognition handles live post-entry reassessment;
- live cognition can HOLD / PROTECT / EXTEND / EXIT;
- DOL1 touch does not equal acceptance;
- DOL1 acceptance requires later fully closed M1 evidence beyond DOL1 in favorable direction;
- DOL1 remains a soft checkpoint when extending;
- DOL2 has demonstrated real economic capacity;
- DOL3 is currently rejected by edge economics;
- universal target extension is not allowed; cognition must select extension;
- runtime decisions may not use fold ID, future bars, final outcome or date lookup;
- a research blocker closes only with a causal mechanism, cross-fold replay, winner preservation, runtime wiring and anti-lookahead evidence.

---

## 3. IMPORTANT WORK ALREADY COMPLETED

### 3.1 Sovereign 6R certification enforcement

Changed VT31 certification runtime so observed DD uses the single hard maximum of `6R`.

Important file:

`src/qore/infrastructure/traders/vt31_nas100_edge_certification.py`

Important canonical commit:

`8e61c437ec863056581faee2d2d78e7a95bfe313`  
`governance(vt31): enforce sovereign 6R edge-only certification`

Tests lock:

- `6.00R = PASS`;
- `6.01R = FAIL`;
- old 10R/15R observed-DD certification ceilings are inactive.

Legacy capital-weighted certification logic was superseded and retained only as audit provenance.

### 3.2 Maximum-intelligence / M15 / post-entry cognition wiring

Completed the causal separation between entry thesis and post-entry management.

Relevant runtime files:

- `src/qore/infrastructure/traders/vt31_nas100_reasoning_engine.py`
- `src/qore/infrastructure/traders/vt31_nas100_position_intelligence.py`
- `src/qore/infrastructure/traders/vt31_nas100_post_entry_cognitive_runtime.py`
- `src/qore/infrastructure/traders/vt31_nas100_situation_model.py`
- `src/qore/infrastructure/traders/vt31_nas100_market_context_runtime.py`

H3 full-cognition post-1R management became the strongest management path.

DOL2 was retained as real economic capacity. DOL3 was rejected.

### 3.3 H3 + W5 + DOL2 + PS2 composition

A fixed B-side research stack emerged:

- H3 full cognition;
- W5 soft-DOL1 logic;
- cognition-selected DOL2;
- post-acceptance PS2.

This improved PF/expectancy/winner preservation but initially did not solve DD.

### 3.4 Positive-evidence admission work

Blanket Order Block abstention was rejected as too aggressive.

The preferred positive-evidence admission witness became:

`A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`

This was selected because its semantics are market-native: SHORT requirement plus matured reclaim `>=15m`, rather than an outcome-maximized filter.

Important commit:

`5e442fd469517ccb5e29b625a43e1d333451d0fd`

Important findings:

`docs/research/VT31_ARCH2_ORDER_BLOCK_POSITIVE_EVIDENCE_FINDINGS_001.md`

At that stage the strong A+B baseline still had approximately:

- recent PF `1.5537`;
- expectancy `+0.449R`;
- observed DD `10.571R`;
- MC positive `81.54%`;
- winner preservation 100% / 100%.

### 3.5 Universal Breaker pretarget protection research

A pure-edge structural Breaker protection hook was added to the H3/DOL2 simulator.

Relevant files:

- `scripts/vt31_nas100_h3_dol2_composition_frontier_v1.py`
- `scripts/vt31_nas100_breaker_pretarget_protection_frontier_v1.py`
- `.github/workflows/vt31-breaker-pretarget-protection-frontier-v1.yml`

Important finding:

Universal Breaker PS2 proved that structural stop protection can compress DD strongly in some folds. R6 reached about `5.31R`.

However universal protection damaged winner-R and expectancy in other folds. It was therefore NOT promotable.

Conclusion:

> Breaker protection has real capacity, but must be cognition-selective.

### 3.6 Live cognitive Breaker protection and the false-exhaustion bug

A live cognitive authorizer was wired so a confirmed improving Breaker swing could be evaluated through full post-entry cognition.

Relevant files:

- `scripts/vt31_nas100_live_cognitive_breaker_protection_frontier_v1.py`
- `docs/research/VT31_ARCH2_LIVE_COGNITIVE_BREAKER_PROTECTION_GATE_001.md`

The first GREEN workflow appeared to show survivors but all were economic no-ops:

- many cognitive evaluations;
- zero TRAIL authorizations;
- `changed_trade_count=0`;
- most decisions returned `COGNITIVE_EXHAUSTION_CONFIRMED`.

Root cause discovered:

`NO_CONFIRMED_EXHAUSTION` contained the token `EXHAUST`, and the helper `_confirmed_exhaustion()` treated it as confirmed exhaustion.

This was a real semantic bug, not an economic hypothesis failure.

Fix commits:

- `41ed9b65310475e309b9d6790fbe5eef430986ec` — distinguish explicit non-exhaustion from exhaustion;
- `9733af9a899478644be1eab16fee6992c6497f18` — lock explicit non-exhaustion semantics;
- `380ef12cc4f84399e157916be59c93c18972e898` — require non-exhausted adverse journey to reach TRAIL.

After the fix, `NO_CONFIRMED_EXHAUSTION + current_open_r=-0.50R + valid protective swing` is required by tests to reach `PRESERVE_DOL1` / TRAIL, not false EXIT.

### 3.7 Causal current_open_r journey intelligence

Added causal strategy-native live R journey state:

- computed from frozen entry;
- frozen initial structural risk;
- side;
- latest fully closed causal price.

This is R-based trader logic, not position sizing.

Key commits include:

- `90ded2f1b12909f0fc332741769cc6151064e4ce` — expose causal open-R in Situation Model;
- `b0c750a00a99a1a996597c9d5cb37e9f0b076ded` — wire open-R through post-entry cognition;
- `f0b3a4ecd50f7f5b66d96b8aa102ba4c686a3023` — distinguish causal pre-DOL1 journey;
- `8abdb1d71387bb83c9f9424755fab39c89ca0f1b` — actuate causal open-R in full position cognition;
- `ea53da22033da9ed4dc205293805cc55341c937d` — materially adverse journey cannot remain low urgency.

Current material-adverse band used in development:

`current_open_r <= -0.50R`

### 3.8 Adverse-journey cognitive exits

A separate predeclared frontier tested causal early exits after fully closed M1 observations, with execution only at the next M1 open.

No same-bar hindsight.

Relevant:

- `scripts/vt31_nas100_adverse_journey_cognitive_exit_frontier_v1.py`
- `docs/research/VT31_ARCH2_ADVERSE_JOURNEY_COGNITIVE_EXIT_GATE_001.md`

The first useful CAUTIOUS exit improved recent metrics while preserving winners.

Subsequent stale-MIXED and residual-state research produced larger pure-edge improvements.

Broad `NONSUPPORTIVE` exits were rejected because they destroyed winners and worsened DD in historical folds.

### 3.9 Comparator 003

Canonical file:

`docs/research/VT31_ARCH2_BSIDE_RESEARCH_COMPARATOR_003.md`

Comparator ID:

`VT31_BSIDE_COMP003_CAUTION_STALE_RESIDUAL_CONTEXT_EXIT`

Fixed B-side stack:

- H3;
- W5;
- full cognition DOL2;
- post-acceptance PS2;
- causal current_open_r;
- maximum-cognition pre-DOL1 exits for validated CAUTIOUS / stale-MIXED / residual states.

Recent consumed Comparator 003:

- PF about `1.7206`;
- expectancy `+0.5279R`;
- observed DD `9.3398R`;
- MC positive `85.70%`;
- winner count preservation 100%;
- winner-R preservation 100%.

### 3.10 Breaker rotation admission discovery

A causal entry-time class was found:

`Breaker + SHORT + prior_day=rotation + reference_volatility=compressed`

Consumed discovery support:

- R5: 1 loss / 0 winners;
- R6: 3 losses / 0 winners;
- R8: 3 losses / 0 winners;
- recent: 2 losses / 0 winners;
- total: 9 losses / 0 winners.

A first broad abstention improved DD strongly but slightly degraded one R8 half-year, so it was not promoted directly.

A recovery exception was then added to preserve a bullish recovery sequence rather than over-filter.

Relevant files:

- `docs/research/VT31_ARCH2_BREAKER_ROTATION_ADMISSION_GATE_001.md`
- `docs/research/VT31_ARCH2_BREAKER_ROTATION_RECOVERY_EXCEPTION_GATE_001.md`
- `scripts/vt31_nas100_breaker_rotation_recovery_exception_frontier_v1.py`

### 3.11 FVG fresh-fast admission and residual episode repair

Further observation-only attribution isolated additional weak admission states while preserving winners.

Important sequence of work:

- FVG short + compressed reference + fresh reclaim + fast confirmation;
- residual episode Breaker bearish/compressed/H1-bullish conflict;
- rejected broader filters that touched winners;
- cross-fold and half-year gates remained mandatory.

Important commits:

- `cc50cd94fe07f62628ff894f329e0d8e78819e49`
- `3cfba56ba9459c928e8f52b55aaa4f6b92405ee8`
- `d00c2ea46acd66b7ec70cabde0d1fe3f29d660e5`
- `a923b07473698003b793a0250040a7da6de0e61f`
- `4e1580fa1ee490aad43f63aada12b83c2ad0c2c1`
- `ac21025b22c868097de83a2ec39f3fc28fdcbd35`
- `c81f900fe2fa68e61b9947ae0ff4bc7da5c3163d`

### 3.12 Comparator 006 — current clean integrated base before latest frontier

Canonical file:

`docs/research/VT31_ARCH2_INTEGRATED_RESEARCH_COMPARATOR_006.md`

Comparator ID:

`VT31_AB_COMP006_CLEAN_BREAKER_CONFLICT_SURVIVOR`

Fixed admission stack:

1. `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
2. abstain Breaker + SHORT + prior-day rotation + compressed reference, except bullish recovery sequence;
3. abstain FVG + SHORT + compressed reference + FRESH_LT8M reclaim + FAST_LE5M confirmation;
4. abstain Breaker + SHORT + prior-day bearish + compressed reference + H1 bullish.

Comparator 006 results:

R5:
- PF `4.64358`;
- mean `+2.10502R`;
- DD `5.25R`;
- MC positive `98.34%`;
- MC p95 DD `14.79R`.

R6:
- PF `4.80485`;
- mean `+2.54872R`;
- DD `5.39444R`;
- MC positive `98.43%`;
- MC p95 DD `8.54R`.

R8:
- PF `5.53228`;
- mean `+2.61260R`;
- DD `6.00502R`;
- MC positive `99.13%`;
- MC p95 DD `9.42R`.

Recent consumed:
- PF `2.01711`;
- mean `+0.70825R`;
- DD `7.23975R`;
- MC positive `90.76%`;
- MC p95 DD `14.70R`;
- winner count 100%;
- winner-R 100%.

Comparator 006 was not certified because R8 exceeded 6R by about 0.005R and recent exceeded by about 1.24R.

---

## 4. LATEST DECISIVE RESULT — RAPID BREAKER CONFLICT FRONTIER

Predeclared gate:

`docs/research/VT31_ARCH2_RAPID_BREAKER_CONFLICT_ADMISSION_GATE_001.md`

Implementation:

`scripts/vt31_nas100_rapid_breaker_conflict_admission_frontier_v1.py`

Workflow:

`.github/workflows/vt31-rapid-breaker-conflict-admission-frontier-v1.yml`

Run:

`37508820071` — SUCCESS.

Base:

`VT31_AB_COMP006_CLEAN_BREAKER_CONFLICT_SURVIVOR`

Two narrow pre-entry causal classes were tested.

### Conflict A — H4 bullish conflict

Breaker + SHORT + prior-day bullish + normal reference volatility + H4 bullish + H1 mixed + M15 mixed + premarket bearish + cash open bullish.

Discovery support:

3 losses / 0 winners across consumed development evidence.

### Conflict B — fresh reclaim + mid confirmation

Breaker + SHORT + normal reference volatility + FRESH_LT8M reclaim + MID_6_10M confirmation.

Discovery support:

3 losses / 0 winners.

### Variants tested

- `COMP006_PLUS_H4_BULLISH_CONFLICT`
- `COMP006_PLUS_FRESH_MID_NORMAL_BREAKER`
- `COMP006_PLUS_RAPID_BREAKER_UNION`

All three were development survivors:

- PF non-degrade 4/4;
- mean-R non-degrade 4/4;
- DD non-degrade 4/4;
- density floor 4/4;
- winner preservation PASS;
- half-year temporal non-degrade PASS.

No variant reached <=6R in every consumed fold because recent remains above 6R.

### Strongest current development survivor

`COMP006_PLUS_RAPID_BREAKER_UNION`

R5:
- sample 35;
- PF `4.64358`;
- mean `+2.10502R`;
- DD `5.25R`;
- MC positive `98.34%`;
- MC p95 DD `14.7945R`;
- winners preserved 100%.

R6:
- sample 23;
- PF `5.14059`;
- mean `+2.70518R`;
- DD `5.39444R`;
- MC positive `98.97%`;
- MC p95 DD `7.49444R`;
- winners preserved 100%.

R8:
- sample 21;
- PF `6.95158`;
- mean `+3.12034R`;
- DD `5.06613R`;
- MC positive `98.60%`;
- MC p95 DD `7.94946R`;
- winners preserved 100%.

Recent consumed:
- sample 33;
- wins 8;
- losses 25;
- PF `2.2073021627`;
- mean `+0.8148066039R/trade`;
- total `+26.88861793R`;
- observed DD `6.5933831126R`;
- max losing streak 5;
- MC positive `93.70%`;
- MC p95 DD `12.146999R`;
- winner count preservation 100%;
- winner-R preservation 100%.

This is the best current pure-edge development state.

It is NOT certified because recent DD remains approximately `0.5934R` above the sovereign 6R gate.

Fresh holdout remains sealed.

---

## 5. WHAT HAS BEEN REJECTED AND MUST NOT BE REPEATED BLINDLY

Do not restart or promote the following without a new causal reason:

- blanket historical Order Block abstention — too aggressive / density-generalization problem;
- universal Breaker pretarget trailing — can compress DD but damages winner-R/expectancy;
- broad MIXED/NONSUPPORTIVE adverse exits — destroys winners in historical folds;
- DOL3 extension — rejected by edge economics;
- using DOL1 touch as acceptance — incorrect;
- same-bar exit after a closed-bar cognitive decision — hindsight; execution must be next M1 open;
- treating `NO_CONFIRMED_EXHAUSTION` as exhaustion — fixed semantic bug;
- broad Breaker vetoes that include the known large R8 winner;
- any fold/date/outcome-aware admission rule;
- any sizing/leverage/compound/portfolio rescue;
- calling a no-op variant a meaningful survivor only because metrics equal control.

---

## 6. CURRENT PROBLEMS THE NEXT ARCHITECT MUST SOLVE

### Problem 1 — recent DD still 6.593R

This is now the principal certification blocker.

All historical consumed folds for the strongest union are already <=6R:

- R5 5.25R;
- R6 5.394R;
- R8 5.066R.

Recent consumed is 6.593R.

The next architect must reconstruct the maximum-DD episode of the strongest union and find a causal market explanation for the remaining approximately 0.593R excess.

Do NOT invent a numerical threshold solely to remove the losing trade.

Prefer already-existing causal states and buckets.

### Problem 2 — risk of overfitting narrow admission classes

The newest admission classes are economically strong but small-sample.

They have passed cross-fold direction, winner preservation and half-year checks, but they are still consumed-evidence development hypotheses.

Do not treat 3-loss/0-winner discovery bins as certification proof by themselves.

The final defense is:

- causal semantics;
- cross-fold stability;
- density;
- winner preservation;
- runtime parity;
- final fresh holdout.

### Problem 3 — latest survivor is not yet a frozen integrated comparator/candidate

The rapid Breaker union is the best development result, but the branch has not yet frozen it as a new canonical integrated comparator/candidate contract.

The next architect should first document/freeze the development base before stacking another experiment, so evidence provenance remains clear.

Recommended new comparator identity:

`VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

This would still be a research comparator, NOT final candidate freeze, until DD <=6R and all pre-holdout gates are complete.

### Problem 4 — final runtime parity for newest admission logic

The latest admission filters currently live in research frontier composition.

Before certification candidate freeze, the exact chosen admission/management logic must be wired into the real VT31 runtime path and tested so research replay and runtime decision semantics cannot diverge.

### Problem 5 — final metrics not yet fully frozen

The sovereign standard also requires final:

- payoff;
- Sharpe;
- Sortino;
- degraded cost/slippage stress;
- combined PF;
- formal temporal/OOS pack;
- final Monte Carlo robustness.

Sharpe/Sortino formula and annualization conventions must be frozen before fresh holdout.

Do not open fresh holdout until those conventions are fixed.

### Problem 6 — semantic robustness audit

The `NO_CONFIRMED_EXHAUSTION` bug proved that string-token semantic parsing can create false cognition.

Audit other categorical helpers for similar substring collisions before candidate freeze.

Prefer explicit enum/state comparisons where feasible.

### Problem 7 — no-op survivor governance

Earlier cognitive variants passed development comparison only because they changed zero trades.

Future aggregate gates should explicitly require real actuation (`changed_trade_count > 0` or equivalent) when the experiment claims an economic mechanism.

A no-op may be a valid control but not a meaningful improvement survivor.

### Problem 8 — fresh holdout is still sealed

This is intentional.

Do not open it to see whether the current 6.593R version happens to pass.

Opening before candidate freeze would consume the holdout and compromise certification.

---

## 7. EXACT NEXT WORK ORDER

### Phase A — freeze the latest development survivor as the next comparator

Create a canonical comparator document for:

`COMP006_PLUS_RAPID_BREAKER_UNION`

Record exact:

- admission conditions;
- B-side position stack;
- code paths;
- workflow `37508820071`;
- metrics per fold;
- evidence hashes;
- governance;
- no fresh holdout.

Do not call it certified.

### Phase B — reconstruct remaining recent max-DD episode

Run observation-only forensics on the union survivor.

For every trade inside the max-DD path capture only causal state available at the relevant decision time:

- entry family;
- side;
- prior-day regime;
- H4/H1/M15;
- premarket;
- cash open;
- volatility/reference state;
- position in prior-day range;
- liquidity/raid state;
- path efficiency;
- overlap;
- reclaim state/age;
- confirmation latency/freshness;
- risk geometry;
- destination geometry;
- post-entry current_open_r;
- structure event family/age;
- whether loss was rapid invalidation before cognition could act.

Compare those trades against winners with the same causal families.

### Phase C — predeclare one narrow residual hypothesis at a time

The target is only about 0.593R of recent DD.

Do not create broad filters.

Candidate mechanisms should preferably be:

- a market-native admission conflict;
- a causal structural invalidation avoidance;
- a live post-entry action that can occur before the harmful loss;
- a stronger but winner-preserving causal confirmation requirement.

Every hypothesis must be documented BEFORE economic replay.

### Phase D — cross-fold adjudication

Require, at minimum:

- PF non-degrade 4/4;
- mean non-degrade 4/4;
- DD non-degrade 4/4;
- observed DD <=6R in R5/R6/R8/recent;
- winner count >=80%;
- winner-R >=90%;
- density >=75%;
- half-year mean/DD non-degrade;
- recent PF >=1.70;
- each era PF >=1.50;
- expectancy positive and preferably >=+0.15R;
- MC positive >=90%;
- MC p95 DD <=15R as current robustness direction.

The first truly important milestone is:

`six_r_all_fold_survivors != []`

### Phase E — final pre-holdout certification pack

Once a genuine all-fold <=6R survivor exists:

1. wire exact logic into runtime;
2. run focused/unit/integration tests;
3. audit maximum-intelligence accounting;
4. audit no future leakage;
5. run degraded cost/slippage stress;
6. compute/freeze payoff;
7. compute/freeze Sharpe convention and result;
8. compute/freeze Sortino convention and result;
9. compute final combined PF/expectancy;
10. run full MC/sequence/temporal robustness;
11. freeze all thresholds, formulas and evidence exclusions;
12. record exact commit SHA and candidate fingerprint.

### Phase F — candidate freeze

Only after all pre-holdout gates pass:

- freeze exact code SHA;
- freeze exact configuration;
- freeze exact memory/cognition fingerprints;
- freeze exact formulas;
- freeze exact admission/management rules;
- freeze evidence exclusions;
- declare fresh-holdout candidate.

No tuning after this point.

### Phase G — fresh sealed holdout exam

Open once.

If it passes every sovereign gate, proceed to formal certification.

If it fails, it does not certify and the holdout becomes consumed. Return to development with a new future holdout.

---

## 8. FILES THE NEXT ARCHITECT SHOULD READ FIRST

Canonical governance:

- `docs/research/VT31_NAS100_SOVEREIGN_TRADER_CERTIFICATION_STANDARD_001.md`

Current integrated base:

- `docs/research/VT31_ARCH2_INTEGRATED_RESEARCH_COMPARATOR_006.md`

Latest predeclared gate:

- `docs/research/VT31_ARCH2_RAPID_BREAKER_CONFLICT_ADMISSION_GATE_001.md`

Latest implementation:

- `scripts/vt31_nas100_rapid_breaker_conflict_admission_frontier_v1.py`
- `.github/workflows/vt31-rapid-breaker-conflict-admission-frontier-v1.yml`

Critical research/runtime files:

- `src/qore/infrastructure/traders/vt31_nas100_edge_certification.py`
- `src/qore/infrastructure/traders/vt31_nas100_reasoning_engine.py`
- `src/qore/infrastructure/traders/vt31_nas100_position_intelligence.py`
- `src/qore/infrastructure/traders/vt31_nas100_post_entry_cognitive_runtime.py`
- `src/qore/infrastructure/traders/vt31_nas100_situation_model.py`
- `src/qore/infrastructure/traders/vt31_nas100_market_context_runtime.py`
- `scripts/vt31_nas100_specialist_r1_candidate.py`
- `scripts/vt31_nas100_h3_dol2_composition_frontier_v1.py`
- `scripts/vt31_nas100_adverse_journey_cognitive_exit_frontier_v1.py`
- `scripts/vt31_nas100_breaker_rotation_recovery_exception_frontier_v1.py`
- `scripts/vt31_nas100_live_cognitive_breaker_protection_frontier_v1.py`

Important tests:

- `tests/infrastructure/test_vt31_nas100_edge_certification.py`
- `tests/infrastructure/test_vt31_nas100_position_intelligence.py`
- `tests/infrastructure/test_vt31_nas100_post_entry_cognitive_runtime.py`

---

## 9. WORKFLOW / EVIDENCE DISCIPLINE

Use GitHub as source of truth.

Use consumed immutable artifacts for development and cross-fold replay.

Keep evidence SHA256 verification.

Do not wait on irrelevant workflows if a focused Trader Lab / workflow can answer the hypothesis faster, but all promotion-level evidence must be reproducible and recorded.

Fresh holdout stays sealed until candidate freeze.

The latest decisive run is:

`37508820071`

Head tested:

`e4dda550814d21894a6a79e995e480530cc59912`

Result:

all three rapid Breaker variants are development survivors; no all-fold <=6R survivor yet.

Best current development economics:

`COMP006_PLUS_RAPID_BREAKER_UNION`

Recent:

`PF 2.2073 | mean +0.8148R | DD 6.5934R | MC+ 93.70% | MC p95 DD 12.147R | winner preservation 100/100`

Historical DD:

`R5 5.25R | R6 5.394R | R8 5.066R`

---

## 10. WHAT MUST NEVER BE CLAIMED YET

Do not say:

- VT31 is certified;
- the fresh holdout passed;
- the latest union is production-ready;
- LIVE or real capital is authorized;
- 6R gate has been closed;
- final Sharpe/Sortino/cost-stress gates are complete;
- CIBO may rescue VT31 with sizing.

Correct current statement:

> VT31 has a strong pure-edge development survivor with all historical consumed folds <=6R and recent DD reduced to about 6.593R while preserving 100% of winners and passing current PF/expectancy/MC direction. Certification remains blocked by the recent observed-DD hard gate and the unfinished final pre-holdout certification pack.

---

## 11. DEFINITION OF DONE

VT31 is done only when one exact frozen candidate demonstrates:

- observed DD <=6R everywhere required;
- pure-edge profitability;
- maximum causal intelligence;
- PF / expectancy / payoff / Sharpe / Sortino gates;
- temporal robustness;
- cost/slippage robustness;
- Monte Carlo robustness;
- winner preservation;
- no causal leakage;
- runtime/replay parity;
- fresh sealed holdout PASS.

Only then may VT31 be called certified.

Only after trader certification may CIBO apply capital engineering such as sizing, leverage, compounding or portfolio allocation.

---

## 12. IMMEDIATE FIRST ACTION FOR THE NEXT CHAT

Read this handoff, then inspect:

1. branch HEAD;
2. workflow `37508820071`;
3. the union survivor's recent maximum-DD path.

Freeze the union as the next development comparator before adding another hypothesis.

Then attack only the remaining approximately `0.593R` recent DD gap using causal market intelligence.

Do not reopen already rejected broad mechanisms. Do not touch the fresh holdout.

---

## 13. AUTHORITATIVE LATEST DELTA — COMPARATOR 007 IS NOW FROZEN

This section supersedes any older wording above that says the rapid Breaker union still needs to be frozen as a comparator.

Latest commit:

`e2c2ff6fef485cd445d461b422aa47df415c3b55`

Commit message:

`docs(vt31): freeze rapid breaker union as comparator 007`

Canonical comparator file:

`docs/research/VT31_ARCH2_INTEGRATED_RESEARCH_COMPARATOR_007.md`

Comparator ID:

`VT31_AB_COMP007_RAPID_BREAKER_UNION_SURVIVOR`

Source workflow:

`37508820071` — SUCCESS

Evaluated research head:

`e4dda550814d21894a6a79e995e480530cc59912`

Source variant:

`COMP006_PLUS_RAPID_BREAKER_UNION`

### 13.1 Comparator 007 fixed stack

Position side remains Comparator 003:

- H3 full-cognition post-1R management;
- W5 soft-DOL1;
- cognition-selected DOL2;
- post-acceptance PS2;
- causal `current_open_r`;
- validated maximum-cognition pre-DOL1 exits.

Admission stack:

1. `A_EXPANDED_OB_REQUIRE_SHORT_RECLAIM_15M`;
2. abstain Breaker + SHORT + prior-day rotation + compressed reference, except bullish recovery;
3. abstain FVG + SHORT + compressed reference + `FRESH_LT8M` reclaim + `FAST_LE5M` confirmation;
4. abstain Breaker + SHORT + prior-day bearish + compressed reference + H1 bullish;
5. rapid Breaker Conflict A:
   - Breaker;
   - SHORT;
   - prior-day bullish;
   - normal reference volatility;
   - H4 bullish;
   - H1 mixed;
   - M15 mixed;
   - premarket bearish;
   - cash-open bullish;
6. rapid Breaker Conflict B:
   - Breaker;
   - SHORT;
   - normal reference volatility;
   - `FRESH_LT8M` reclaim;
   - `MID_6_10M` confirmation.

The union abstains when Conflict A or Conflict B is present.

### 13.2 Current strongest consumed-evidence economics

R5:

- PF 4.64358;
- mean +2.10502R;
- observed DD 5.25R;
- MC positive 98.34%;
- MC p95 DD 14.7945R;
- winner count preservation 100%;
- winner-R preservation 100%.

R6:

- PF 5.14059;
- mean +2.70518R;
- observed DD 5.39444R;
- MC positive 98.97%;
- MC p95 DD 7.49444R;
- winner count preservation 100%;
- winner-R preservation 100%.

R8:

- PF 6.95158;
- mean +3.12034R;
- observed DD 5.06613R;
- MC positive 98.60%;
- MC p95 DD 7.94946R;
- winner count preservation 100%;
- winner-R preservation 100%.

Recent consumed:

- sample 33;
- wins 8;
- losses 25;
- PF 2.2073021627;
- mean +0.8148066039R/trade;
- total +26.88861793R;
- observed DD 6.5933831126R;
- max losing streak 5;
- MC positive 93.70%;
- MC p95 DD 12.146999R;
- winner count preservation 100%;
- winner-R preservation 100%.

### 13.3 Current certification blocker

Historical consumed folds all satisfy the sovereign observed-DD gate:

- R5 PASS;
- R6 PASS;
- R8 PASS.

Recent consumed remains:

`6.5933831126R`

Residual excess above the hard gate:

`0.5933831126R`

Therefore:

`six_r_all_fold_survivor = false`

VT31 remains NOT CERTIFIED.

### 13.4 Immediate next work

Do NOT create another filter immediately.

First:

1. reconstruct the exact recent Comparator-007 peak-to-trough max-DD episode;
2. identify every trade inside that path;
3. separate rapid invalidations from losses that had causal post-entry observation time;
4. compare those losing paths against matched winners;
5. inspect existing causal fields/buckets before inventing any new threshold;
6. predeclare only one narrow mechanism at a time;
7. replay 4/4 consumed folds;
8. require observed DD <=6R in all folds without destroying winners.

The remaining gap is small enough that a broad filter is scientifically unnecessary and likely dangerous.

### 13.5 Work still required after <=6R is achieved

A 6R survivor is necessary but not sufficient.

Before fresh holdout:

- wire exact Comparator-007-plus-final-repair logic into runtime;
- prove replay/runtime semantic parity;
- audit maximum-intelligence accounting;
- audit categorical semantic parsers for substring collisions;
- freeze payoff formula/result;
- freeze Sharpe formula/annualization/result;
- freeze Sortino formula/result;
- run degraded cost/slippage stress;
- run final temporal/OOS pack;
- run final Monte Carlo/sequence robustness;
- compute final combined PF/expectancy;
- freeze exact code SHA/config/cognition fingerprints;
- freeze evidence exclusions;
- freeze final candidate.

Only then open fresh sealed holdout exactly once.

No sizing, leverage, compounding, portfolio weighting, CIBO rescue, capital engineering, fold/date lookup or future-outcome authority may be introduced to obtain certification.

