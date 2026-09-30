> **SUPERSEDED BY MASTER ROADMAP V2 — CIBO Capital Management Authority + CE2I.**  
> Canonical continuation: `docs/research/CIBO-CAPITAL-MANAGEMENT-AUTHORITY-CE2I-MASTER-ROADMAP-V2.md`
>
# CIBO CAPITAL EFFICIENCY & EXPOSURE INTELLIGENCE — MASTER ROADMAP V1

**Program identity:** CIBO Capital Efficiency & Exposure Intelligence  
**Short name:** CE2I  
**Primary research PR:** #651  
**Branch:** `agent/cibo-capital-efficiency-sizing-lab-001`  
**Governance:** OPEN / DRAFT / UNMERGED / RESEARCH ONLY  
**Authority:** no broker authority, no Risk authority, no LIVE authority, no real-capital authority

---

# 0. Owner intent

The objective is not to build a larger lot-size calculator.

The objective is to give CIBO a governed **capitalization toolbox** capable of selecting the most
capital-efficient way to express a valid Trader opportunity under the actual market condition.

The long-term optimization target is:

```text
MAXIMIZE ECONOMIC PRODUCTIVITY OF CAPITAL
WHILE MINIMIZING:
- incremental capital at risk;
- margin immobilized;
- drawdown contribution;
- concentration/correlation risk;
- execution friction;
- loss of capacity for the next opportunity.
```

Literal risk-free leverage does not exist. The research target is therefore not "free leverage".
The target is **more useful exposure and more economic output per dollar truly put at risk**.

CIBO must be able to explain the exact source of any additional exposure.

No additional exposure is accepted merely because a formula permits it.

---

# 1. Canonical identity

This program supersedes the narrow interpretation of PR #651 as only a sizing laboratory.

The canonical identity is now:

## CIBO Capital Efficiency & Exposure Intelligence — CE2I

Sizing is one CE2I tool.

CE2I is the broader intelligence that studies, compares and eventually recommends how an already
valid Trader opportunity could be capitalized most efficiently.

Canonical question:

> Given one valid Trader opportunity, current account state, current market regime and current
> portfolio state, what exposure structure produces the best economic use of capital without
> exceeding the authorized risk envelope or corrupting Trader methodology?

---

# 2. Non-negotiable sovereignty laws

## LAW-01 — Trader methodology sovereignty

Trader owns:

- setup validity;
- entry;
- structural invalidation;
- stop geometry;
- target geometry;
- methodology-specific management state.

CE2I cannot invent a tighter stop to create apparent leverage.

```text
MORE SIZE BY ARTIFICIALLY TIGHTENING STOP
!= CAPITAL EFFICIENCY
```

Any narrower invalidation used by CE2I must be produced and separately validated by the Trader
methodology or by an explicitly governed Trader research candidate.

## LAW-02 — QORE Risk sovereignty

CE2I may measure, compare, simulate, recommend or request.

QORE Risk remains final authority for:

- monetary risk;
- aggregate open risk;
- margin headroom;
- provider limits;
- reservations;
- correlated exposure limits;
- account survivability;
- final admission/reduction/rejection.

```text
CE2I RECOMMENDATION != RISK AUTHORIZATION
```

## LAW-03 — Execution sovereignty

CE2I does not create broker-native orders.

It does not mutate existing orders, stops, targets or positions unless a separately governed runtime
integration explicitly grants that action after certification.

## LAW-04 — Additional exposure requires a proven funding source

Every increment of exposure must identify one or more admissible sources:

- verified reduction in structural stop risk;
- lower margin consumption for equivalent exposure;
- released risk capacity;
- realized profit;
- true diversification / factor-risk reduction;
- reduction of another exposure;
- a certified limited-downside structure;
- provider/contract efficiency;
- other explicitly validated economic capacity.

If no source can be proven:

```text
NO PROVEN CAPACITY SOURCE
-> NO ADDITIONAL EXPOSURE CLAIM
```

## LAW-05 — Floating profit is not free capital

Unrealized profit cannot be treated as equivalent to reconciled realized capital.

Any future profit-funded expansion must distinguish:

- unrealized PnL;
- protected but unrealized PnL;
- realized/reconciled PnL;
- released reserved risk.

## LAW-06 — Capacity cannot be double spent

Risk, margin or released capital may only be recycled after authoritative reservation/reconciliation
proves that the original capacity is no longer consumed.

```text
RISK APPEARS LOWER
!= RISK CAPACITY RELEASED
```

## LAW-07 — No outcome-aware sizing

No future trade outcome, future MAE/MFE, future target touch or future stop avoidance may enter a
decision-time sizing feature.

Research replay must preserve strict chronology.

---

# 3. CE2I capitalization toolbox

CE2I must evolve into a toolbox. A market regime does not force one sizing rule.

## TOOL-01 — Structural Leverage

Purpose:

Obtain more exposure for the same monetary loss ceiling when a genuinely more precise structural
invalidation is already proven by the Trader methodology.

Research variables:

- stop_loss_per_volume;
- verified invalidation distance;
- stop frequency;
- MAE distribution;
- slippage around invalidation;
- post-stop afterlife;
- PF / Total R / DD.

Fail condition:

Higher nominal exposure is rejected if the narrower invalidation degrades expectancy or survivability.

---

## TOOL-02 — Margin Efficiency

Purpose:

For equivalent economic exposure, find the expression that consumes the least usable margin.

Primary metric:

```text
EXPOSURE_PER_MARGIN_DOLLAR
```

Research dimensions:

- broker/provider;
- contract size;
- margin per volume;
- leverage tier;
- symbol specification;
- session;
- volatility;
- spread;
- provider-specific restrictions.

False advantage protection:

Economic exposure must be normalized consistently before comparisons.

---

## TOOL-03 — Risk Efficiency

Purpose:

Measure economic output per dollar genuinely exposed to structural loss.

Primary metrics:

```text
EXPECTED_R_PER_STOP_RISK_DOLLAR
REALIZED_R_PER_STOP_RISK_DOLLAR
EXPOSURE_PER_STOP_RISK_DOLLAR
```

This is not a license to enlarge size from a high subjective confidence score.

Any risk differentiation must be supported by out-of-sample evidence.

---

## TOOL-04 — Capital Recycling

Purpose:

Reuse risk capacity after authoritative position-state evidence proves that part of the original
loss capacity has been released.

Candidate sources:

- realized partial;
- valid protected stop advancement;
- volume reduction;
- full risk release after reconciliation;
- other certified position-management state.

Required architecture:

```text
POSITION STATE
-> VERIFIED NEW WORST-CASE LOSS
-> RISK RESERVATION UPDATE
-> RECONCILIATION
-> CAPACITY RELEASE
-> CE2I MAY CONSIDER NEW OPPORTUNITY
```

No double spending is allowed.

---

## TOOL-05 — Profit-Funded Expansion

Purpose:

Allow future exposure to be funded partly or wholly from realized, reconciled profit rather than from
the original capital base.

Required separation:

```text
REALIZED PROFIT != FLOATING PROFIT
PROTECTED FLOATING PROFIT != REALIZED PROFIT
```

Research questions:

- how much realized profit can be redeployed;
- whether profit should create temporary or permanent risk capacity;
- session/day reset semantics;
- drawdown survivability;
- funded-account constraints.

---

## TOOL-06 — Portfolio Netting Intelligence

Purpose:

Understand the real economic exposure across multiple nominally separate positions.

Examples:

- repeated USD factor exposure;
- index beta overlap;
- JPY cluster exposure;
- gold/USD macro factor overlap;
- same-session strategy clustering.

Required output:

- gross exposure;
- net exposure;
- factor exposure;
- directional concentration;
- correlation concentration;
- incremental portfolio risk of the next trade.

Nominal trade count is not diversification.

---

## TOOL-07 — Hedged Exposure / Risk Transfer

Purpose:

Research whether part of a directional opportunity can be retained while specific unwanted risk is
reduced through an economically valid hedge or offset.

Must measure:

- hedge cost;
- basis risk;
- slippage;
- spread;
- correlation stability;
- margin impact;
- net payoff degradation;
- failure in regime transitions.

A hedge that consumes more margin or destroys expected return is not capital efficiency.

---

## TOOL-08 — Convex / Limited-Downside Exposure

Purpose:

Where QORE later supports a separately certified instrument, study structures with explicitly bounded
downside and asymmetric upside.

No such structure is automatically authorized by this roadmap.

Each instrument/provider requires independent semantic, pricing, execution and Risk certification.

---

## TOOL-09 — Opportunity Competition

Purpose:

When several valid opportunities coexist, decide which combination provides the best use of scarce
risk and margin capacity.

Inputs:

- each Trader's valid opportunity;
- stop risk;
- margin consumption;
- normalized expected value evidence;
- correlation;
- factor concentration;
- expected holding time;
- execution cost;
- next-opportunity capacity.

Output:

A recommendation-only portfolio of opportunity allocations.

Risk remains final authority.

---

## TOOL-10 — Capital Velocity / Time Efficiency

Purpose:

Measure how quickly capital produces economic output and becomes reusable.

Candidate metric:

```text
CAPITAL_VELOCITY =
REALIZED_ECONOMIC_OUTPUT
/
(CAPITAL_AT_RISK * TIME_AT_RISK)
```

Research use:

Two opportunities with similar expectancy may have very different capital productivity if one blocks
risk/margin capacity for much longer.

No forced early exit is implied.

---

## TOOL-11 — Execution-Efficient Exposure

Purpose:

Find the region where adding exposure no longer improves net economics because spread, slippage,
commission, fill quality or latency consume the marginal edge.

Required curve:

```text
VOLUME
-> GROSS EXPECTANCY
-> EXECUTION COST
-> NET EXPECTANCY
```

The economically optimal size may be below the mathematical risk maximum.

---

## TOOL-12 — Regime-Adaptive Capitalization

Purpose:

Select among CE2I tools based on current market conditions rather than applying one universal sizing
formula.

Possible decision-time states:

- volatility regime;
- spread regime;
- liquidity state;
- session transition;
- pre-close;
- correlation regime;
- trend/compression state;
- cross-market stress;
- provider condition.

Regime state may select the capitalization mechanism. It may not rewrite Trader edge.

---

## TOOL-13 — Drawdown Reserve

Purpose:

Preserve deliberately unused capacity when keeping optionality has greater expected value than
consuming all available risk immediately.

Research variables:

- current drawdown;
- loss cluster state;
- number of concurrent positions;
- next-opportunity density;
- expected future opportunity quality;
- provider daily-loss envelope.

Unused capital can be an active strategic choice.

---

## TOOL-14 — Dynamic De-risking

Purpose:

Study reduction of consumed risk during the lifecycle of a valid open position.

Potential mechanisms, only when Trader management permits:

- partial realization;
- partial volume reduction;
- structural stop improvement;
- protection state;
- risk-off transition.

CE2I measures released capacity. It does not independently command the management action.

---

## TOOL-15 — Capital Optionality

Purpose:

Measure not only what the current trade can earn, but what capacity remains for future valid
opportunities after taking it.

Candidate metric:

```text
NEXT_OPPORTUNITY_CAPACITY =
AVAILABLE SAFE RISK/MARGIN AFTER CURRENT DECISION
```

This is a first-class CE2I variable.

---

# 4. Capital Opportunity Graph

CE2I's central representation should become a **Capital Opportunity Graph (COG)**.

The graph represents every currently valid opportunity and every economically valid way of expressing
it.

## Opportunity node

Each opportunity node should carry:

- Trader identity/version;
- market;
- session;
- side;
- entry/stop/target provenance;
- structural-stop verification;
- risk per volume;
- margin per volume;
- economic exposure per volume;
- spread/commission/slippage;
- expected holding-time evidence;
- regime;
- execution-quality state;
- sizing-path identity.

## Portfolio edges

Edges represent interactions:

- correlation;
- common factor;
- same-currency exposure;
- same-index beta;
- margin competition;
- risk-capacity competition;
- mutually hedging exposure;
- mutually amplifying exposure;
- temporal overlap.

## Capitalization candidate node

One opportunity may have multiple research-only capitalization candidates:

- baseline size;
- structural-efficiency size;
- margin-efficient expression;
- reduced-risk expression;
- profit-funded increment;
- recycled-capital increment;
- hedged form;
- reserve-capital form.

## Graph output

The graph must make it possible to answer:

```text
WHICH VALID OPPORTUNITIES?
WHICH EXPOSURE FORMS?
WHAT TRUE RISK?
WHAT TRUE MARGIN?
WHAT CROSS-POSITION INTERACTION?
WHAT CAPITAL REMAINS AFTER EACH CHOICE?
```

The graph is research/recommendation state, not execution authority.

---

# 5. Canonical CE2I objective family

There must not be one deceptive "maximize leverage" metric.

CE2I must report a vector of economic objectives.

Core measurements:

```text
EXPOSURE_GAIN_MULTIPLE
STOP_RISK_USD
MARGIN_COMMITTED_USD
EXPOSURE_PER_STOP_RISK_DOLLAR
EXPOSURE_PER_MARGIN_DOLLAR
EXPECTED_R_PER_STOP_RISK_DOLLAR
REALIZED_R_PER_STOP_RISK_DOLLAR
RISK_BUDGET_UTILIZATION
MARGIN_BUDGET_UTILIZATION
CAPITAL_VELOCITY
NEXT_OPPORTUNITY_CAPACITY
PEAK_SIMULTANEOUS_STOP_RISK
PEAK_SIMULTANEOUS_MARGIN
FACTOR_CONCENTRATION
CORRELATION_CONCENTRATION
EXECUTION_COST_PER_EXPOSURE
```

Strategy-level validation must additionally retain:

- trades;
- PF;
- Total R;
- observed DD;
- longest loss streak;
- MAE/MFE;
- stop frequency;
- temporal stability;
- WFO;
- sealed holdout;
- Monte Carlo survivability;
- provider portability;
- stress costs.

---

# 6. Research anti-cheating matrix

A CE2I result is invalid if it relies on any of the following:

| False efficiency | Disposition |
|---|---|
| tighter stop not produced by verified Trader structure | reject |
| future outcome used to select size | reject |
| floating profit counted as realized capital | reject |
| inconsistent contract normalization | reject |
| ignoring broker minimum/step | reject |
| ignoring margin requirement | reject |
| ignoring spread/commission/slippage | reject |
| ignoring correlation/concentration | reject in portfolio phase |
| released capacity not reconciled | reject |
| same capital counted twice | reject |
| higher exposure obtained by silently increasing allowed loss | label as higher risk, not efficiency |
| lower DD created only by reducing nominal R | not structural CE2I improvement |
| provider-specific advantage claimed universal | reject portability claim |

---

# 7. Master engineering roadmap

The roadmap is sequential. A later phase cannot be declared solved from theory alone.

## PHASE 0 — Architecture freeze

**Status: ACTIVE / THIS ROADMAP**

Deliverables:

- canonical CE2I identity;
- sovereignty laws;
- capitalization toolbox;
- Capital Opportunity Graph concept;
- metric family;
- anti-cheating matrix;
- staged promotion chain.

Exit gate:

- roadmap committed to PR #651;
- continuity comment in PR;
- no conflict with Trader/Risk/Execution sovereignty.

---

## PHASE 1 — Static single-opportunity frontier

**Status: IMPLEMENTED / GREEN — Slice 001**

Current implementation:

`src/qore/infrastructure/cibo_capital_efficiency_sizing_lab.py`

Capabilities:

- simultaneous stop-risk bound;
- margin bound;
- broker maximum;
- broker step flooring;
- broker-minimum infeasibility;
- baseline exposure comparison;
- exposure-per-risk-dollar;
- exposure-per-margin-dollar;
- Pareto frontier;
- verified-structural-stop fail-closed law.

Validation checkpoint:

- HEAD before roadmap expansion: `4377240bb113b59c283b81a05a9b145e10f13170`
- GitHub Actions run: `36233494641`
- Ruff PASS
- Mypy PASS
- Pytest PASS

Exit gate: COMPLETE.

---

## PHASE 2 — Real sizing-path reconstruction

**Status: IN PROGRESS — source contracts implemented; observed submit coverage 1/7**

Primary dependency: PR #637 behavioral evidence.

Goal:

Reconstruct what actually created requested volume for each active DEMO Trader.

Required matrix:

- VT08 FOREX;
- R34 XAUUSD;
- R38 EURUSD;
- R43 GBPUSD;
- R38 GBPJPY;
- R42 AUDJPY;
- VT31 NAS100.

For every observed candidate/order:

- sizing path;
- requested volume;
- assigned capital;
- stop risk;
- margin;
- provider symbol economics;
- baseline utilization;
- theoretical static frontier;
- unused risk headroom;
- unused margin headroom.

Exit gate:

A chronological ledger proving baseline vs CE2I frontier without changing any executed order.

---

## PHASE 3 — Provider/contract economic normalization

**Status: PENDING**

Goal:

Build exact equivalent-exposure normalization.

Required:

- source contract size;
- provider contract size;
- tick size/value;
- volume step;
- min/max volume;
- margin per volume;
- commission;
- spread;
- session-specific execution conditions.

Target output:

```text
NORMALIZED ECONOMIC EXPOSURE
```

that is comparable across provider/contract expressions.

Exit gate:

No apparent margin-efficiency advantage can be explained by unit mismatch.

---

## PHASE 4 — Unused-capital forensics

**Status: PENDING**

Goal:

Quantify where current Trader sizing leaves safe capital capacity unused.

Segment by:

- Trader;
- market;
- session;
- side;
- sizing path;
- volatility regime;
- spread regime;
- stop distance;
- provider.

Research hypotheses:

- H1 unused stop-risk headroom;
- H2 unused margin headroom;
- H3 broker step/minimum inefficiency;
- H4 fixed sizing fails to adapt to valid structural geometry.

Exit gate:

Ranked evidence table of inefficiency families. No policy change yet.

---

## PHASE 5 — Structural Leverage Lab

**Status: PENDING**

Goal:

Determine whether more precise **verified** structural invalidation can increase exposure at constant
monetary loss without degrading strategy economics.

Must compare:

- original stop;
- candidate structural stop;
- stop frequency;
- MAE;
- post-stop afterlife;
- PF;
- Total R;
- DD;
- LS;
- costs;
- WFO;
- sealed holdout.

Hard gate:

```text
MORE EXPOSURE + WORSE EXPECTANCY/SURVIVABILITY
-> REJECT
```

---

## PHASE 6 — Execution-Efficient Sizing Curve

**Status: PENDING**

Goal:

Measure net expectancy versus volume.

For each market/provider:

```text
volume
-> spread cost
-> commission
-> slippage
-> latency/fill degradation
-> net expectancy
```

Exit gate:

Identify whether the economic optimum is below the stop-risk/margin maximum.

---

## PHASE 7 — Capital Velocity

**Status: PENDING**

Goal:

Measure productivity of risk through time.

Required:

- time-to-protection;
- time-to-partial;
- time-to-exit;
- time risk remains fully consumed;
- realized output per risk-time unit.

Exit gate:

Capital velocity shown to add information beyond PF/Total R alone.

---

## PHASE 8 — Capital Recycling Engine research

**Status: PENDING**

Goal:

Prove safe release and reuse of capacity.

Required integration evidence:

- exact position state;
- current worst-case loss;
- Risk reservation identity;
- broker reconciliation;
- released amount;
- no concurrent double spend.

Exit gate:

Adversarial tests prove the same capacity cannot be consumed twice.

No runtime integration before this gate.

---

## PHASE 9 — Profit-Funded Expansion research

**Status: PENDING**

Goal:

Study whether realized profit can finance additional exposure while protecting original capital.

Required accounting:

- realized PnL;
- fees;
- session/day attribution;
- provider/funded constraints;
- reset policy;
- loss-after-profit scenarios.

Exit gate:

Monte Carlo/stress evidence proves the mechanism does not merely amplify late-session drawdown.

---

## PHASE 10 — Portfolio / Factor Exposure Graph

**Status: PENDING**

Goal:

Build the first executable Capital Opportunity Graph.

Required edges:

- correlation;
- currency factor;
- index beta;
- commodity/macro factor;
- risk-capacity competition;
- margin competition;
- temporal overlap.

Exit gate:

Incremental portfolio exposure of a new opportunity is reproducible and chronological.

---

## PHASE 11 — Opportunity Competition Engine

**Status: PENDING**

Goal:

Compare combinations of valid opportunities under scarce capital.

Required outputs:

- feasible opportunity sets;
- total risk;
- total margin;
- factor concentration;
- expected economic output;
- future capacity remaining.

Authority ceiling:

Recommendation only.

Exit gate:

Historical replay demonstrates that opportunity competition improves capital productivity without
hiding a loss of density or increasing tail risk beyond gates.

---

## PHASE 12 — Drawdown Reserve / Capital Optionality

**Status: PENDING**

Goal:

Determine when intentionally unused capacity is economically superior to immediate deployment.

Research:

- current DD state;
- opportunity arrival process;
- future opportunity density;
- loss clustering;
- provider daily-loss envelope.

Exit gate:

Reserve policy must outperform always-deploy and fixed-reserve baselines out of sample.

---

## PHASE 13 — Regime-Adaptive Capitalization

**Status: PENDING**

Goal:

Map market state to the capitalization mechanism, not to arbitrary discretionary leverage.

Examples:

- high spread -> no expansion / execution-efficient cap;
- high correlation -> factor-constrained allocation;
- protected position -> possible recycling;
- low margin headroom -> margin-efficient expression;
- verified structural compression -> structural-efficiency candidate;
- drawdown stress -> reserve optionality.

Exit gate:

No regime branch may use future information or silently rewrite Trader methodology.

---

## PHASE 14 — Dynamic De-risking integration study

**Status: PENDING**

Goal:

Connect Trader-authorized position-management transitions to CE2I capacity accounting.

CE2I observes:

- partial;
- stop improvement;
- volume reduction;
- runner state;
- protected state.

CE2I does not independently invent those management actions.

Exit gate:

Capacity release is monotonic, reconciled and attributable.

---

## PHASE 15 — Hedging / Risk Transfer research

**Status: PENDING**

Goal:

Determine whether selected unwanted risk can be removed more cheaply than abandoning the opportunity.

Required:

- hedge instrument certification;
- basis risk;
- margin interaction;
- costs;
- regime instability;
- payoff impact.

Exit gate:

Net portfolio economics improve after all hedge costs.

---

## PHASE 16 — Convex / Limited-Downside structures

**Status: FUTURE / GATED**

Only begins after:

- supported instrument semantics;
- valuation/pricing;
- provider execution;
- Risk;
- settlement/reconciliation;
- certification.

No current authority is implied.

---

## PHASE 17 — CE2I unified research policy

**Status: PENDING**

Goal:

Combine proven tools into one deterministic recommendation framework.

The policy must explain:

- which tool was considered;
- why it was eligible;
- which evidence supported it;
- which constraints bound it;
- which alternatives were rejected;
- how much new risk/margin was introduced;
- how much future capacity remains.

No opaque "confidence -> leverage multiplier" is allowed.

---

## PHASE 18 — Historical integrated replay

**Status: PENDING**

Run all certified CE2I mechanisms chronologically across the supported Trader portfolio.

Must report:

- baseline vs CE2I;
- PF;
- Total R;
- DD;
- loss streak;
- risk utilization;
- margin utilization;
- exposure efficiency;
- capital velocity;
- next-opportunity capacity;
- concentration;
- costs;
- WFO;
- MC;
- temporal stability.

Exit gate:

Material economic improvement without tail-risk deterioration outside accepted gates.

---

## PHASE 19 — Freeze candidate

**Status: PENDING**

Freeze:

- CE2I policy;
- exact code;
- exact inputs;
- provider profiles;
- Trader versions;
- risk assumptions;
- execution assumptions;
- datasets;
- feature set.

No tuning after sealed validation begins.

---

## PHASE 20 — Sealed holdout / adversarial validation

**Status: PENDING**

Required:

- fresh/sealed holdout;
- provider stress;
- spread stress;
- slippage stress;
- correlation-break stress;
- rapid opportunity clustering;
- loss-cluster stress;
- reservation/reconciliation fault tests.

Failure sends the mechanism back to research. The holdout may not be repeatedly mined.

---

## PHASE 21 — Certification decision

**Status: PENDING**

Possible outcomes per CE2I tool:

- CERTIFIED_RESEARCH_TOOL;
- CERTIFIED_RECOMMENDATION_TOOL;
- REJECTED;
- NEEDS_MORE_EVIDENCE.

No CE2I tool becomes LIVE because another tool passes.

---

## PHASE 22 — DEMO shadow integration

**Status: FUTURE / OWNER-GATED**

CE2I runs alongside actual DEMO activity but does not alter size.

Compare:

```text
ACTUAL REQUESTED SIZE
vs
CE2I RECOMMENDED CAPITALIZATION
vs
REALIZED PATH
```

This phase measures counterfactual quality without execution authority.

---

## PHASE 23 — DEMO governed execution pilot

**Status: FUTURE / OWNER-GATED**

Only after explicit Owner authorization and independent Risk/execution integration certification.

CE2I may request a size/structure.

Risk may allow/reduce/reject.

Execution submits only Risk-authorized output.

---

## PHASE 24 — LIVE readiness

**Status: FUTURE / CLOSED**

Requires separate LIVE/real-capital authorization.

PR #651 by itself can never authorize LIVE.

---

# 8. Promotion gates

A tool cannot progress because it "looks promising".

Minimum promotion chain:

```text
THEORY
-> DETERMINISTIC CONTRACT
-> UNIT / ADVERSARIAL TESTS
-> HISTORICAL RECONSTRUCTION
-> CHRONOLOGICAL REPLAY
-> COST / PROVIDER STRESS
-> WFO
-> MONTE CARLO
-> FREEZE
-> SEALED HOLDOUT
-> SHADOW
-> SEPARATE EXECUTION AUTHORIZATION
```

---

# 9. CE2I failure modes that must remain visible

The research must explicitly report:

- higher exposure but higher absolute loss;
- higher exposure but worse PF;
- higher exposure but worse DD;
- better margin efficiency but worse execution cost;
- capital recycling that reduces next-opportunity safety;
- realized-profit expansion that amplifies giveback;
- correlation model failure;
- provider leverage/margin regime change;
- broker minimum preventing safe expression;
- risk reservation race;
- exposure normalization error;
- opportunity competition suppressing too much valid density.

No aggregate score may hide these failures.

---

# 10. Current checkpoint

At the time this roadmap is introduced:

## Completed

- PR #651 created as DRAFT research line.
- static risk/margin/exposure frontier implemented.
- Pareto research comparison implemented.
- structural-stop anti-cheating gate implemented.
- broker-minimum infeasibility implemented.
- focused CI established.
- Slice 001 GREEN.

## Immediate next work

```text
PHASE 2 — REAL SIZING-PATH RECONSTRUCTION
```

Use PR #637 and the cTrader DEMO behavioral evidence to reconstruct actual sizing paths for all
active Traders before adding a new sizing policy.

Then proceed to:

```text
PHASE 3 — PROVIDER/CONTRACT NORMALIZATION
PHASE 4 — UNUSED-CAPITAL FORENSICS
```

No later phase should be skipped merely because the mathematical model is already available.

---

# 11. Continuity protocol for future architects

Before doing any work on CE2I:

1. Open PR #651.
2. Verify current HEAD.
3. Read this roadmap completely.
4. Read the current PR body and latest continuity/checkpoint comments.
5. Read the Slice 001 research contract.
6. Inspect the current changed files.
7. Identify the first phase not marked complete.
8. Continue from that phase without reopening completed questions unless new evidence falsifies them.
9. Preserve Trader, Risk and Execution sovereignty.
10. Keep the PR DRAFT/UNMERGED until explicit Owner direction.

Every material research advance must update:

- current phase status;
- evidence produced;
- rejected hypotheses;
- current HEAD;
- CI/run evidence;
- exact next step.

The GitHub PR and this roadmap are the continuity source of truth.

---

# 12. Final target architecture

The intended future flow is:

```text
VALID TRADER OPPORTUNITY
        |
        v
MARKET / REGIME STATE
        |
        v
CAPITAL OPPORTUNITY GRAPH
        |
        +--> STRUCTURAL LEVERAGE
        +--> MARGIN EFFICIENCY
        +--> RISK EFFICIENCY
        +--> CAPITAL RECYCLING
        +--> PROFIT-FUNDED EXPANSION
        +--> PORTFOLIO NETTING
        +--> OPPORTUNITY COMPETITION
        +--> CAPITAL VELOCITY
        +--> EXECUTION-EFFICIENT EXPOSURE
        +--> DRAWDOWN RESERVE
        +--> CAPITAL OPTIONALITY
        +--> HEDGE / RISK TRANSFER (gated)
        +--> CONVEX EXPOSURE (future gated)
        |
        v
CE2I RECOMMENDATION
        |
        v
QORE RISK — FINAL CAPITAL AUTHORITY
        |
        v
EXECUTION — ONLY AUTHORIZED OUTPUT
```

The desired end state is not "CIBO uses more leverage".

The desired end state is:

> **CIBO understands multiple ways of capitalizing a valid opportunity and can prove which one uses
> the least truly committed capital for the greatest robust economic output, while preserving enough
> capacity to survive adverse paths and exploit the next opportunity.**
