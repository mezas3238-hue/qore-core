# CIBO CAPITAL MANAGEMENT AUTHORITY + CE2I — MASTER ROADMAP V2

**Primary PR:** #651  
**Branch:** `agent/cibo-capital-efficiency-sizing-lab-001`  
**Governance:** OPEN / DRAFT / UNMERGED / RESEARCH ONLY  
**Canonical architecture ADR:** `CIBO-CE2I-ADR-002-CAPITAL-MANAGEMENT-AUTHORITY.md`

---

# 0. Mission

CIBO becomes the capital-management authority for every Trader opportunity.

The Trader discovers/defines the market opportunity.

CIBO decides how capital is used around that opportunity.

The entry starts with the lowest viable executable exposure. After entry, CIBO uses its capital
technology and the CE2I toolbox to protect base capital, recover capacity, recycle it, reserve it or
expand exposure when evidence supports doing so.

The objective is not "maximum leverage".

The objective is:

```text
MINIMUM NECESSARY BASE CAPITAL EXPOSURE
+
MAXIMUM ROBUST CAPITAL PRODUCTIVITY
+
MAXIMUM REUSABLE/FUTURE CAPACITY
```

No deterministic guarantee of profit is assumed.

---

# 1. Canonical authority model

## Trader authority

Trader owns market methodology:

- valid setup;
- side;
- technical entry;
- structural stop/invalidation;
- technical target/objective;
- market/session/timeframe facts;
- signal validity/expiry;
- methodology state.

Trader does not own final volume.

Legacy Trader risk scales are diagnostic evidence only.

## Account-aware mission layer

Before CIBO selects capital actions, it derives a capital mission from the authoritative account
binding.

Current canonical missions:

- `FUNDED_SURVIVAL_COMPOUND` — external funded/production capital;
- `PRODUCTION_SURVIVAL_COMPOUND` — other production capital;
- `DEMO_CAPABILITY_DISCOVERY` — DEMO account used to measure full CIBO capability;
- `TEST_VALIDATION` — validation environment;
- `SANDBOX_SIMULATION` — simulation only.

Mission selection is automatic from account/provider/environment facts and **must not depend on
issues, Trader sizing, per-trade flags or manual operator choices**.

DEMO capability discovery permits all implemented non-rejected CE2I tools to be studied/exercised,
while Risk/provider/accounting/anti-cheating constraints remain active.

## CIBO CMA authority

CIBO Capital Management Authority owns:

- initial exposure;
- sizing;
- capital allocation;
- margin allocation;
- protection of base capital;
- capital recovery accounting;
- scaling/de-scaling;
- capital recycling;
- realized/protected profit redeployment;
- opportunity competition;
- portfolio allocation;
- concentration-aware capital allocation;
- reserve policy;
- capital velocity;
- optionality;
- selection and combination of CE2I tools.

## QORE Risk role

Risk is the independent survivability governor.

Risk owns hard limits, not economic strategy.

Risk can ALLOW / REDUCE / REJECT CIBO capital requests when required by:

- maximum loss;
- margin headroom;
- provider/funded-account restrictions;
- aggregate account risk;
- concentration ceilings;
- reservation integrity;
- emergency survival constraints.

## Execution role

Execution mutates the broker only after an authorized CIBO capital action passes Risk.

---

# 2. Capital lifecycle

```text
TRADER OPPORTUNITY
      |
      v
CIBO MINIMAL SEED
      |
      v
OBSERVE
      |
      v
PROTECT BASE CAPITAL
      |
      v
BASE CAPITAL RECOVERED?
   NO | YES
      |  |
      |  +--> CAPITALIZE WITH CE2I TOOLS
      |           |
      |           +--> EXPAND
      |           +--> RECYCLE
      |           +--> RESERVE
      |           +--> REALLOCATE
      |           +--> DE-RISK
      |
      +--> KEEP MINIMAL / REDUCE / RELEASE
```

CIBO may choose not to expand.

Capital not used is itself an asset because it preserves future optionality.

---

# 3. CE2I toolbox

CIBO must have many tools, not one leverage multiplier.

## T01 Minimal Seed
Start with the lowest broker/methodology-compatible exposure.

## T02 Structural Leverage
Exploit verified structural precision without manufacturing stops.

## T03 Margin Efficiency
Maximize normalized exposure per margin dollar.

## T04 Risk Efficiency
Maximize robust economic output per dollar of true stop risk.

## T05 Capital Recycling
Reuse capacity only after authoritative release/reconciliation.

## T06 Profit-Funded Expansion
Redeploy realized net profit under explicit accounting.

## T07 Protected-Capacity Expansion
Use a reconciled protected economic floor, after reserves/costs, as bounded funding capacity.

## T08 Portfolio Netting
Measure true factor/net exposure instead of counting nominal positions.

## T09 Opportunity Competition
Allocate scarce capital among simultaneous valid Trader opportunities.

## T10 Capital Velocity
Optimize output per unit of capital-at-risk time.

## T11 Execution-Efficient Exposure
Stop adding size when slippage/spread/commission destroy marginal edge.

## T12 Regime-Adaptive Capitalization
Select capital tools based on current market/account conditions.

## T13 Drawdown Reserve
Keep capital unused when reserve has greater survival/optionality value.

## T14 Dynamic De-risking
Reduce consumed risk while retaining valid opportunity participation.

## T15 Capital Optionality
Measure capacity preserved for the next opportunity.

## T16 Hedged Exposure / Risk Transfer
Transfer selected risks only when net economics improve after costs/basis risk.

## T17 Convex / Limited-Downside Exposure
Future gated structures with explicitly bounded downside.

## T18 Cross-Trader Capital Allocation
Move available capital capacity toward the best current use without giving Traders sizing authority.

## T19 Capacity Reservation
Reserve risk/margin atomically so the same dollar cannot be consumed twice.

## T20 Capital Release
Release reservations immediately and correctly after reconciliation.

---

# 4. Capital source ledger

Every CIBO deployment must identify where its capital capacity comes from.

Canonical source types:

```text
ORIGINAL_BASE_CAPITAL
REALIZED_PROFIT
PROTECTED_ECONOMIC_FLOOR
RELEASED_RISK_CAPACITY
RELEASED_MARGIN_CAPACITY
TRUE_PORTFOLIO_NETTING
REDUCED_OTHER_EXPOSURE
CERTIFIED_LIMITED_DOWNSIDE_CAPACITY
```

Every source needs:

- source_id;
- original amount;
- currently available amount;
- reserved amount;
- consumed amount;
- released amount;
- reconciliation timestamp;
- evidence references.

Hard stock invariant:

```text
AVAILABLE + RESERVED + DEPLOYED = PROVEN_AMOUNT
```

`CUMULATIVE_RELEASED` is a historical flow counter only and is never added back into that stock
identity. A release moves capacity from RESERVED/DEPLOYED back to AVAILABLE and increments the
historical release counter.

No double-spend.

---

# 5. Core metrics

## Capital preservation

- BASE_CAPITAL_AT_RISK_USD
- TIME_TO_BASE_RECOVERY
- ORIGINAL_CAPITAL_LOSS_RATE
- PEAK_ORIGINAL_CAPITAL_AT_RISK
- CAPITAL_RELEASE_LATENCY

## Capital efficiency

- EXPOSURE_PER_STOP_RISK_DOLLAR
- EXPOSURE_PER_MARGIN_DOLLAR
- NET_RETURN_PER_BASE_CAPITAL_DOLLAR
- NET_RETURN_PER_RISK_TIME
- CAPITAL_VELOCITY
- MARGIN_UTILIZATION
- RISK_UTILIZATION

## Growth

- REALIZED_PROFIT_REDEPLOYMENT
- PROTECTED_CAPACITY_REDEPLOYMENT
- SELF_FINANCED_EXPOSURE
- SELF_FINANCED_RETURN
- COMPOUNDING_EFFICIENCY

## Optionality

- NEXT_OPPORTUNITY_CAPACITY
- UNUSED_SAFE_CAPACITY
- CAPITAL_BLOCK_TIME
- OPPORTUNITY_MISSED_FOR_CAPACITY
- RESERVE_VALUE

## Portfolio safety

- PEAK_SIMULTANEOUS_STOP_RISK
- PEAK_SIMULTANEOUS_MARGIN
- FACTOR_CONCENTRATION
- CORRELATION_CONCENTRATION
- PROVIDER_CONCENTRATION

## Strategy outcomes

Still report:

- trades;
- PF;
- Total R;
- drawdown;
- loss streak;
- MAE/MFE;
- stop frequency;
- WFO;
- Monte Carlo;
- temporal stability;
- sealed holdout;
- execution stress.

No CE2I metric may hide worse strategy outcomes.

---

# 6. Hard anti-cheating laws

Reject any result based on:

- future information;
- outcome-aware sizing;
- martingale/loss recovery;
- adverse-price averaging purely to reduce average entry;
- floating PnL treated as cash;
- double-spent risk/margin;
- invented released capacity;
- arbitrary stop tightening to create leverage;
- stop widening to permit more capital;
- ignoring broker granularity;
- ignoring execution costs;
- inconsistent contract normalization;
- hidden correlated exposure;
- increasing hard account loss ceiling and calling it efficiency;
- selecting only winning regimes after outcome is known.

---

# 7. Engineering roadmap

## PHASE 0 — Authority architecture freeze

**Status: ACTIVE / ADR-002 COMMITTED**

Deliverables:

- CMA authority split;
- CE2I toolbox role;
- Trader no-sizing law;
- Risk hard-governor law;
- capital lifecycle;
- source accounting;
- anti-cheating laws.

Exit gate:

Architecture represented in docs + deterministic research contracts.

---

## PHASE 1 — Static capital-efficiency frontier

**Status: COMPLETE / GREEN**

Existing Slice 001:

- risk bound;
- margin bound;
- broker min/max/step;
- Pareto frontier;
- structural-stop anti-cheating.

This becomes a CE2I primitive, not the central authority.

---

## PHASE 2 — Legacy sizing reconstruction

**Status: IN PROGRESS**

Purpose:

Understand what current Traders did before removing their sizing authority.

Current evidence:

- seven legacy sizing source contracts reconstructed;
- 2 historical real cTrader DEMO submits observed;
- both VT31;
- existing submit coverage 1/7;
- historical rows PARTIAL under richer CE2I schema.

Outputs:

- legacy requested volume;
- legacy risk budget;
- risk/margin utilization;
- quantization effects;
- sizing provenance.

Legacy sizing is a baseline, never the target.

Exit gate:

Sufficient chronological baseline evidence to compare CMA against the old architecture.

---

## PHASE 3 — Provider economic normalization

**Status: COMMON CTRADER-DEMO + FUNDEDNEXT CONTRACT GREEN / EMPIRICAL COST CALIBRATION PENDING**

Normalize:

- contract size;
- tick size/value;
- lot/unit conversion;
- min/max/step;
- margin;
- spread;
- commission;
- slippage;
- provider-specific economics.

Exit gate:

Equivalent economic exposure is comparable across all supported markets/providers.

---

## PHASE 4 — TraderOpportunityEnvelope migration

**Status: COMPLETE / RUNTIME AUTHORITY SWITCH GREEN 7/7**

Goal:

Every Trader outputs opportunity facts with **no final volume authority**.

Contract contains:

- Trader identity/version;
- signal fingerprint;
- side;
- entry;
- stop;
- target;
- provider symbol;
- risk-per-volume;
- margin-per-volume;
- execution constraints;
- methodology constraints.

Explicitly absent:

- final volume;
- risk multiplier as authority;
- final monetary risk allocation.

Current direct builders:

- VT08 FOREX: `build_ctrader_demo_vt08_opportunity`
- R34 XAUUSD: `build_r34_opportunity`
- R38 EURUSD: `build_r38_opportunity`
- R43 GBPUSD: `build_r43_opportunity`
- R38 GBPJPY: `build_r38_gbpjpy_opportunity`
- R42 AUDJPY: `build_r42_audjpy_opportunity`
- VT31 NAS100: `build_vt31_opportunity`

These builders preserve market/broker geometry and deliberately do not consume Trader risk scale,
risk BPS or certified-risk-R as volume authority.

Runtime authority switch is now complete in the PR #651 research branch: all seven DEMO Trader paths build volume-free opportunities and final requested volume is produced by CIBO CMA minimal-seed planning. Legacy sizing builders remain only as baseline/reconstruction code and are no longer called by the switched runtime path.

Exit gate:

Runtime adapters call these opportunity builders before any sizing and final requested volume is
produced only by CIBO CMA.

---

## PHASE 5 — Minimal Seed Engine

**Status: RUNTIME-WIRED 7/7 / HISTORICAL-CROSS-PROVIDER VALIDATION PENDING**

Goal:

CIBO produces the minimum viable executable entry for each opportunity.

Must support:

- broker minimum;
- volume step;
- methodology indivisibility constraints;
- hard risk headroom;
- margin headroom.

Initial seed is not chosen from Trader risk scale.

Exit gate:

All Traders can be represented with minimum viable capital without corrupting opportunity geometry.

---

## PHASE 6 — Capital Source Ledger

**Status: DURABLE CAS + ATOMIC RESERVATION + REQUEST/FILL SOURCE-PROVENANCE GREEN / SETTLEMENT FEED COMPLETION PENDING**

Implement atomic accounting of:

- original base capital;
- realized profit;
- protected economic floor;
- released risk;
- released margin;
- portfolio netting;
- reduced other exposure.

Exit gate:

Adversarial concurrency/restart tests prove no capacity can be double-spent.

---


### CIBO provenance checkpoint — 26-SEP-2026

CI-gated provenance now preserves capital-source identity through:

```text
CIBO CAPITAL PLAN
-> CiboRiskRequest capital provenance lots
-> QORE Risk ALLOW/REDUCE
-> proportional provenance scaling on REDUCE
-> durable Risk reservation ledger (FundedNext)
-> durable DEMO trade registry / broker position binding
```

The provenance metadata is fingerprinted but non-authoritative: it cannot choose volume or bypass
Risk. Single-source expansion preserves the exact durable ledger source id; multi-source expansion
preserves every funding slice. Legacy registry rows without provenance remain readable.

## PHASE 7 — Economic Floor / Base Recovery Engine

**Status: REAL-POSITION BINDING + DURABLE SETTLEMENT EVIDENCE GREEN / BROKER SETTLEMENT FEED COMPLETION PENDING**

Compute the worst reconciled economic outcome if the position were to continue/close according to
current protection state.

Inputs:

- realized PnL;
- remaining volume;
- current stop/protection;
- commissions;
- swap;
- conversion fee;
- slippage reserve;
- pending management mutations.

Output:

- BASE_CAPITAL_AT_RISK;
- PROTECTED_ECONOMIC_FLOOR;
- BASE_RECOVERED;
- AVAILABLE_SELF_FINANCING_CAPACITY.

Exit gate:

Position-state faults cannot create fictitious recovered capital.

---

## PHASE 8 — CMA State Machine

**Status: DURABLE LIFECYCLE + FAIL-CLOSED DE-ESCALATION GREEN / PASSIVE RUNTIME OBSERVER WIRED**

States:

- MINIMAL_SEED;
- OBSERVE;
- PROTECT_BASE;
- BASE_RECOVERED;
- CAPITALIZE;
- COMPOUND_OR_RESERVE;
- RELEASE.

Every transition requires explicit evidence.

No outcome-aware transition.

---

### Current implementation notes

Phase 4 runtime authority switch is complete in the research branch: all seven active Trader paths
produce volume-free opportunity facts and CIBO CMA owns requested volume before QORE Risk.

The transitional legacy-request bridge is retained only for reconstruction/baseline compatibility
and is not the target authority path.

The CMA-to-Risk handoff is implemented as a research contract:

```text
TraderOpportunityEnvelope
-> CIBO CapitalActionPlan
-> CiboRiskRequest(requested_volume = CIBO plan volume)
-> QORE Risk
```

The Capital Source Ledger now distinguishes:

- unused reservation release;
- deployed-capital settlement;
- returned capacity;
- consumed/lost capacity.

A deployed loss is **not** automatically recycled back into available capital.

The Economic Floor engine fails closed on:

- unresolved mutation outcome;
- unreconciled broker position;
- unreconciled protection state.

Only a reconciled non-negative worst-case economic floor can mark base capital as recovered.

## PHASE 9 — CE2I Tool Registry

**Status: IMPLEMENTATION STARTED — 20 canonical tool contracts registered**

Each tool declares:

- eligibility;
- evidence requirements;
- capital source;
- expected risk delta;
- expected margin delta;
- execution cost model;
- portfolio interaction;
- exit/de-risk semantics;
- certification status.

Exit gate:

No tool can be invoked without a deterministic eligibility contract.

---

## PHASE 10 — Capital Recycling

**Status: DIMENSION-SAFE CONTRACT IMPLEMENTED / REPLAY + RUNTIME RELEASE EVIDENCE PENDING**

Use only reconciled released risk/margin.

Must survive:

- partial fills;
- delayed settlement;
- restart;
- stale broker state;
- concurrent opportunities.

---

## PHASE 11 — Profit / Protected-Capacity Expansion

**Status: SINGLE + ATOMIC MULTI-SOURCE FUNDING GREEN / BROKER EXPANSION EXECUTION NOT ENABLED**

Research scaling from:

- realized profit;
- protected economic floor.

Compare policies:

- no redeployment;
- realized-only;
- realized + protected;
- reserve-first;
- opportunity-competition allocation.

Hard gate:

Original base capital cannot silently become expansion funding.

---

## PHASE 12 — Execution-Efficient Capitalization

**Status: MARGINAL EXECUTION-COST CURVE + PRE-RESERVATION VOLUME CAP GREEN / EMPIRICAL CALIBRATION PENDING**

Build volume -> execution cost -> net expectancy curves.

Find where marginal exposure stops being economically useful.

---

## PHASE 13 — Capital Opportunity Graph

**Status: CAUSAL FACTOR/CORRELATION/PROVIDER/TEMPORAL/HEDGE EDGES CONTRACT GREEN / EMPIRICAL EDGE FEEDS PENDING**

Represent all simultaneous opportunities, capital sources and interactions.

Nodes:

- Trader opportunities;
- open positions;
- capital sources;
- reserves;
- provider constraints;
- CE2I tool candidates.

Edges:

- correlation;
- factor exposure;
- margin competition;
- risk competition;
- temporal overlap;
- hedging/offset;
- capital-source dependency.

---

## PHASE 14 — Opportunity Competition / Cross-Trader Allocation

**Status: DETERMINISTIC COMPETITION + DURABLE CAS PORTFOLIO RESERVATION V1 GREEN / RUNTIME BATCH INTEGRATION PENDING**

CIBO decides where scarce capital produces the best portfolio-level use.

Trader identity does not reserve a fixed risk fraction merely because an opportunity exists.

Must preserve fairness/anti-starvation evidence and density reporting.

---

### CE2I portfolio checkpoint — 26-SEP-2026

Implemented and CI-gated:

- atomic `reserve_many` across capital-source slices;
- single-source and multi-source self-financing expansion;
- proportional multi-source settlement without false recycling;
- non-fungible capital dimensions for profit/risk-headroom/margin/offset;
- T05 released-capacity recycling contracts;
- T11 marginal execution-efficiency cap applied before capital reservation;
- CE2I policy pipeline `T11 -> T06/T07 -> T19 -> QORE Risk request`;
- Capital Opportunity Graph V1;
- T09/T18 deterministic cross-Trader opportunity competition;
- portfolio allocation ledger reserving stop-risk, margin and concentration capacity;
- restart-safe portfolio allocation reservations with generation CAS + writer lock.

Current V1 opportunity competition is deterministic and causal but explicitly **not claimed to be a
globally optimal portfolio solver**. It is a research baseline for later graph-based optimization.

No expansion broker mutation, DEMO expansion execution or LIVE authorization is granted by these
contracts.

## PHASE 15 — Regime-Adaptive Capital Management

**Status: ACCOUNT-MISSION + CAUSAL MARKET/ACCOUNT REGIME SELECTOR GREEN / REPLAY CALIBRATION PENDING**

Market/account state selects capital tools, not Trader size.

Account mission is now a first-class input:

- FundedNext production -> survival/robust-compounding posture;
- cTrader DEMO -> capability-discovery posture;
- unknown production -> conservative production-survival fallback.

Inputs may include:

- spread/liquidity;
- volatility;
- session;
- trend/compression;
- correlation regime;
- provider condition;
- current DD;
- opportunity density;
- position path.

---

## PHASE 16 — Reserve / Optionality Intelligence

**Status: CAUSAL KNOWN-OPTION RESERVE CONTRACT GREEN / CHRONOLOGICAL VALUE VALIDATION PENDING**

Research when **not using capital** is optimal.

Measure value of maintaining capacity for future opportunities and survival.

---

## PHASE 17 — Dynamic De-risking / Risk Transfer

**Status: T14 STEP-ALIGNED DE-RISKING CONTRACT GREEN / T16 HEDGE + T17 CONVEXITY REMAIN GATED**

Research:

- partial reductions;
- capital-preserving exits;
- hedging;
- risk transfer;
- margin release;
- bounded downside.

Each mechanism requires separate evidence/certification.

---

## PHASE 18 — Per-Trader chronological replay

**Status: IN PROGRESS — CAUSAL REPLAY CONTRACT GREEN / GBPJPY + GBPUSD + AUDJPY + EURUSD EVIDENCE BOUND (4/7)**

The shared replay primitive now exists in:

```text
src/qore/infrastructure/cibo_ce2i_chronological_replay.py
```

It enforces:

- strict separation of PRE-TRADE causal evidence from POST-TRADE outcome;
- no outcome object is accepted by the CIBO sizing-input builder;
- deterministic replay-only signal fingerprints when the historical Trader did not persist one;
- explicit evidence IDs;
- exact technical geometry;
- legacy risk scale retained as baseline evidence only;
- R-denominated replay may proceed without fabricated provider economics;
- USD/CIBO sizing replay fails closed until exact provider economics are calibrated.

The first pilot is R38 GBPJPY. The final R38 artifact has been re-located directly in GitHub Actions:

```text
run_id:      35374273535
artifact_id: 10559826734
artifact:    qore-turtle-soup-gbpjpy-r38-5y-fragility-dda5ab344a122b875e68548cb4e9825acb7b1c27
digest:      sha256:a999feaf90c5fbf2c23a006faff6d591d7f3ede697c34f11dafa510afa5d5846
source_sha:  dda5ab344a122b875e68548cb4e9825acb7b1c27
```

Final R38 5Y evidence:

```text
trades:                 897
profit_factor:          1.852918712035185462516517131
total_scaled_net_010_r: +92.83988286566161467727272231R
max_drawdown:           5.06150896610739539086014902R
positive_annual_blocks: 5/5
acceptance_pass:        true
```

This is distinct from the R37 source artifact and must not be replaced by R37 metrics.
R38 preserves the 897-trade source population and applies its pre-entry structural-fragility risk
overlay.

The exact frozen GBPJPY geometry replay is now GREEN. GitHub Actions reproduced the historical
path from the immutable Raw M5 + Target Destination V2 + R27 memory + R36 freeze inputs, then
verified every generated row against the retained R37 ledger and bound the same population to the
final R38 corrected ledger.

Phase 18 GBPJPY replay evidence:

```text
workflow_run: 36252780843
head_sha:     743291bb6fe02c90831bf9104fa195dba6381e65
artifact_id:  10909937201
artifact:     qore-cibo-phase18-gbpjpy-r38-geometry-743291bb6fe02c90831bf9104fa195dba6381e65
digest:       sha256:b59d8c045a0e86f0e22fb0044dc04eb6dff0f17de4c9f7c7389b903adc443956
rows:         897
```

The bound replay proves:

```text
R37 row-for-row parity:       TRUE
R38 population row parity:    TRUE
same signals:                 TRUE
same entry:                   TRUE
same structural stop:         TRUE
same technical target:        TRUE
same market path:             TRUE
```

Each row now retains exact:

- causal signal timestamp;
- entry timestamp and entry price;
- exact protected-swing structural stop;
- active CIBO DOL technical target;
- R37 baseline risk scale;
- final R38 corrected risk scale;
- pre-entry setup context;
- pre-entry regime state;
- final post-trade outcome kept separately for scoring/baseline comparison.

The Phase 18 artifact checksum manifest has been independently revalidated after download.

### Generic Phase-18 scoring checkpoint — 26-SEP-2026

The shared replay primitive now also produces reusable, Trader-agnostic metrics for:

- legacy baseline PF / Total R / max drawdown / loss streak / stop count;
- peak original base capital at risk;
- peak margin in use;
- base-recovery latency;
- base-capital block time;
- self-financing capacity;
- ending future capacity / optionality;
- cumulative released capacity;
- risk/margin utilization;
- explicit false-recovery incidents.

A precision defect was falsified during binding: recomputing an already-observed legacy result as
`raw R * risk scale` can differ from the authoritative historical ledger because the historical
Trader stored a corrected/scaled Decimal result. Phase 18 therefore preserves an authoritative
`legacy_net_outcome_r` when retained evidence provides it, and only reconstructs from raw R and
risk scale when that authoritative value is absent.

The generic scorer is now bound to the real 897-row R38 artifact in GitHub Actions and reproduces:

```text
trades:          897
profit_factor:   1.852918712035185462516517131
total_r:         92.83988286566161467727272231
max_drawdown_r:  5.06150896610739539086014902
max_loss_streak: 7
```

Current evidence checkpoint:

```text
head_sha:      7cbfe9ab6b0e37d49411f6b722b02274311af664
main_ci_push:  36253442660  SUCCESS
main_ci_pr:    36253445694  SUCCESS
replay_push:   36253442514  SUCCESS
replay_pr:     36253445726  SUCCESS
artifact_id:   10909537936
artifact:      qore-cibo-phase18-gbpjpy-r38-geometry-7cbfe9ab6b0e37d49411f6b722b02274311af664
digest:        sha256:b508feb4fcedcfd5c4e5ef6eeb0fd027c20373ad061c06443687215b63507039
```

Provider-economics search also inspected the retained 10Y GBPJPY Raw M5 GitHub Actions artifact:

```text
run_id:      35166210458
artifact_id: 10475453293
digest:      sha256:b68e74b2afa54295f891c11cde19e12e92db4192930496036c7ebb372474e415
```

Its historical Raw M5 schema carries OHLC, volume, digits, pip position, provider symbol/id and
timestamps, but does not carry historical bid/ask spread, commission, slippage, margin-per-volume or
tick-value evidence. Therefore it cannot be promoted into provider-economic calibration and the
USD CIBO comparison remains correctly fail-closed.

GBPJPY provider-economic status remains deliberately:

```text
R_DENOMINATED_ONLY
CALIBRATION_REQUIRED
USD_CIBO_SIZING_COMPARISON_AUTHORIZED = FALSE
```

No historical spread, commission, slippage, margin or tick-value value has been fabricated.
The next GBPJPY research step is to locate and bind retained provider-economic evidence; if exact
historical economics are unavailable, the USD replay remains incomplete while the exact
R-denominated strategy/geometry replay stays valid.

### GBPUSD R43 Phase-18 checkpoint — 26-SEP-2026

The second per-Trader replay is now bound end-to-end to retained GitHub Actions evidence.

```text
workflow_run: 36254251565  SUCCESS
head_sha:     ee98f0250e0475ee98f4be8236f5451c3bde542d
artifact_id:  10910093452
artifact:     qore-cibo-phase18-gbpusd-r43-geometry-ee98f0250e0475ee98f4be8236f5451c3bde542d
digest:       sha256:93c9c4872543938571eb6ab12e242bde4ec9e7682f056593efde59f88b4579c9
rows:         907
```

The geometry reproducer rebuilds the exact frozen R39 opportunity path from immutable Raw M5,
Target Destination V2, Cognitive V2 R27 and R38 freeze evidence, then binds that population
row-for-row to the final R43 risk-correction ledger.

Bound parity:

```text
R39 row-for-row parity:                    TRUE
R43 population row parity:                 TRUE
same signals:                              TRUE
same entry:                                TRUE
same structural stop:                      TRUE
same technical target:                     TRUE
same market path:                          TRUE
same frozen structural scale:              TRUE
same capital policy as R39:                FALSE (EXPECTED)
R43 drawdown recomputed on corrected equity TRUE
```

The R43 policy binding was explicitly corrected after a falsification: R43 does not inherit the R39
drawdown scale. For every trade it causally computes:

```text
pretrade_overlay = min(short_scale, rank_scale)
drawdown_scale   = DD governor(current corrected R43 equity)
corrected_scale  = frozen_structural_scale * pretrade_overlay * drawdown_scale
corrected_result = raw_net_010_r * corrected_scale
```

This is the exact retained R43 logic and is verified against all 907 authoritative corrected rows.

Generic Phase-18 scoring reproduces the final R43 5Y baseline exactly:

```text
trades:          907
profit_factor:   1.713624514596208498825398640
total_r:         35.40396721533287699752413575
max_drawdown_r:  4.401231922815307849576052766
max_loss_streak: 7
positive annual: 5/5
```

GBPUSD remains deliberately fail-closed for the USD CIBO sizing comparison:

```text
R_DENOMINATED_ONLY
CALIBRATION_REQUIRED
USD_CIBO_SIZING_COMPARISON_AUTHORIZED = FALSE
```

No provider spread, commission, slippage, margin-per-volume or tick-value value is fabricated.

### AUDJPY R42 Phase-18 checkpoint — 26-SEP-2026

The third independent Trader replay is now bound end-to-end without importing the AUDJPY research
branch into CIBO authority code. The workflow checks out the exact immutable R40 source commit only
as historical research evidence, instruments serialization-only technical geometry, then verifies the
result against the retained R40 and final R41/R42 ledgers before scoring through the generic CIBO
Phase-18 primitive.

```text
workflow_run: 36255646543  SUCCESS
head_sha:     9483aada1f5798843450877e002e760725df00ff
artifact_id:  10910875686
artifact:     qore-cibo-phase18-audjpy-r42-geometry-9483aada1f5798843450877e002e760725df00ff
digest:       sha256:7b40e1be53ce0508106b036c68ce4ebb3155bc5c14875144634e365cfb988de5
rows:         1039
```

Immutable AUDJPY research bindings:

```text
R40 source SHA: a332b077598e070a42b2497b3766d55e731f7dca
Raw M5 run:     35166210458
Target V2 run:  35204892665
Cognitive R27:  35383377176
R39 freeze:     35397198837
R40 baseline:   35397390781
R41 correction: 35399430491
```

Bound replay invariants:

```text
R40 row-for-row parity:                    TRUE
R41/R42 population row parity:             TRUE
same signals:                              TRUE
same entry:                                TRUE
same structural stop:                      TRUE
same technical target:                     TRUE
same market path:                          TRUE
same R40 base risk scale:                  TRUE
R41 second-layer overlay reproduced:       TRUE
generic CIBO Phase-18 scoring:             TRUE
artifact checksum manifest:                TRUE
```

Generic Phase-18 scoring reproduces the final R42 5Y baseline exactly:

```text
trades:          1039
profit_factor:   1.957251590510384151212372667
total_r:         68.02344279137424925740640205
max_drawdown_r:  5.293573269867727808258117465
positive annual: 5/5
```

AUDJPY remains deliberately fail-closed for the USD CIBO sizing comparison:

```text
R_DENOMINATED_ONLY
CALIBRATION_REQUIRED
USD_CIBO_SIZING_COMPARISON_AUTHORIZED = FALSE
```

The retained evidence does not prove exact historical provider spread, commission, slippage,
margin-per-volume or tick-value. Those economics are therefore not fabricated or inferred.

Phase 18 now has exact R-denominated geometry/baseline replay evidence for **3/7 Traders**:
R38 GBPJPY, R43 GBPUSD and R42 AUDJPY.

### EURUSD R38 Phase-18 checkpoint — 26-SEP-2026

The fourth independent Trader replay is now bound directly to the authoritative final R38
structural-risk correction. PR #651 does not vendor the EURUSD research lineage: the workflow
checks out the exact immutable source SHA and adds only serialization-only geometry fields before
replaying the original source program.

```text
workflow_run: 36256063185  SUCCESS
head_sha:     12dae850fac23a92c73a7c4dbf6097afe45f0c6b
artifact_id:  10910397898
artifact:     qore-cibo-phase18-eurusd-r38-geometry-12dae850fac23a92c73a7c4dbf6097afe45f0c6b
digest:       sha256:71bb5ce12b7cfc8f2d17b89dcf907b8b74f4a2257f2055adbe9e9d619c324774
rows:         863
source_code:  324fb91d44a6fa328e66de2e22ace7386630c7aa
```

Every independent replay gate completed GREEN:

```text
focused quality:                    GREEN
immutable source SHA verification:  GREEN
R38 exact replay:                   GREEN
R38 row-for-row parity:             GREEN
same causal signal/entry/stop/target GREEN
risk arithmetic reproduction:       GREEN
generic Phase-18 scorer parity:     GREEN
artifact SHA256 manifest:           GREEN
```

Generic Phase-18 scoring reproduces the authoritative EURUSD R38 5Y baseline exactly:

```text
trades:          863
profit_factor:   2.958703779880710298093151891
total_r:         294.8274112858301220583196574
max_drawdown_r:  5.824645307409961208739068649
```

EURUSD also remains deliberately fail-closed for the USD CIBO sizing comparison:

```text
R_DENOMINATED_ONLY
CALIBRATION_REQUIRED
USD_CIBO_SIZING_COMPARISON_AUTHORIZED = FALSE
```

No historical spread, commission, slippage, margin-per-volume or tick-value value was fabricated.

Phase 18 now has exact R-denominated geometry/baseline replay evidence for **4/7 Traders**:
R38 GBPJPY, R43 GBPUSD, R42 AUDJPY and R38 EURUSD. The remaining three Traders still require
independent evidence binding and cannot inherit acceptance from the first four.

Replay each Trader with:

```text
same signals
same technical geometry
legacy sizing baseline
vs
CIBO CMA
```

Measure:

- initial base capital risk;
- time to base recovery;
- self-financed expansion;
- PF;
- Total R;
- DD;
- capital velocity;
- future capacity.

No Trader is accepted because another Trader passes.

---

## PHASE 19 — Integrated portfolio replay

**Status: PENDING**

All supported Traders compete for one coherent capital pool.

Study:

- simultaneous opportunities;
- factor concentration;
- risk/margin reservations;
- capital recycling;
- opportunity starvation;
- aggregate DD;
- peak original capital at risk.

---

## PHASE 20 — WFO / Monte Carlo / Stress

**Status: PENDING**

Required:

- WFO;
- temporal segmentation;
- execution cost stress;
- margin stress;
- spread/slippage stress;
- correlation break;
- rapid opportunity clustering;
- loss clusters;
- reservation/reconciliation faults;
- Monte Carlo survivability.

---

## PHASE 21 — Policy freeze

**Status: PENDING**

Freeze:

- CMA state machine;
- tool registry;
- eligibility;
- source ledger;
- Trader adapters;
- provider profiles;
- all parameters.

No tuning after sealed validation begins.

---

## PHASE 22 — Sealed holdout

**Status: PENDING**

Fresh evidence only.

Failure sends the mechanism back to research.

Do not mine the holdout repeatedly.

---

## PHASE 23 — DEMO shadow

**Status: OWNER-GATED**

CMA calculates actions alongside actual DEMO activity without changing orders.

Compare:

- legacy/actual action;
- CMA action;
- realized path.

---

## PHASE 24 — DEMO governed capital execution

**Status: OWNER-GATED**

CIBO CMA may become the actual capital manager in DEMO only after prior gates pass.

Risk remains hard governor.

Execution applies only authorized actions.

---

## PHASE 25 — LIVE readiness

**Status: CLOSED / FUTURE OWNER AUTHORIZATION**

Requires separate real-capital certification and explicit authorization.

PR #651 alone never authorizes LIVE.

---

# 8. Immediate work order

Current sequence:

```text
1. Build and run PHASE 18 per-Trader chronological replay from retained evidence.
2. Build and run PHASE 19 integrated portfolio replay with one coherent capital pool.
3. Feed empirical replay evidence back into PHASE 3 cost calibration and PHASE 13 interaction edges.
4. Validate PHASE 15/16/17 policies chronologically; reject any policy that improves one metric by hiding worse strategy outcomes.
5. Run PHASE 20 WFO / Monte Carlo / execution-margin-correlation stress.
6. Freeze the surviving CMA/CE2I policy in PHASE 21.
7. Run one sealed PHASE 22 holdout before any Owner-gated DEMO execution change.
```

Do not spend research time optimizing legacy Trader sizing. It is deprecated as authority.

---

# 9. Continuity protocol

Every future architect must:

1. open PR #651;
2. verify current HEAD;
3. read ADR-002;
4. read this roadmap V2;
5. read latest checkpoint comments;
6. identify the first incomplete phase;
7. preserve Trader market-methodology sovereignty;
8. preserve CIBO capital-management sovereignty;
9. preserve Risk hard-governor independence;
10. update phase status, evidence, HEAD, CI and next step after material work.

The GitHub PR, ADR-002 and this roadmap V2 are the continuity source of truth.
