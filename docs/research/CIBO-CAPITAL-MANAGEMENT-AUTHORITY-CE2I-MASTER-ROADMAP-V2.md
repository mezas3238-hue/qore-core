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

**Status: COMPLETE — CAUSAL REPLAY CONTRACT GREEN / ALL SEVEN CMA TRADER LINEAGES EVIDENCE-BOUND (7/7) / HISTORICAL USD PROVIDER CALIBRATION REMAINS SEPARATE**

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
R38 GBPJPY, R43 GBPUSD, R42 AUDJPY and R38 EURUSD.

### XAUUSD R34 Phase-18 checkpoint — 26-SEP-2026

The fifth independent Trader replay now reproduces the frozen R34 five-year validation directly from
the exact immutable XAUUSD source code and retained Raw M5 / Target Destination V2 / Cognitive V3 /
R33 freeze artifacts.

```text
workflow_run: 36256317379  SUCCESS
head_sha:     9a729d1fd5ee5b4bfa783656a45c58f4581bfd7b
artifact_id:  10910328640
artifact:     qore-cibo-phase18-xauusd-r34-geometry-9a729d1fd5ee5b4bfa783656a45c58f4581bfd7b
digest:       sha256:aade958d597032bad08c56043a6c48c145b8ab263f032f2b65c147fd3db7aadd
rows:         921
source_code:  56ef138ee5ea1cde6d0bcf4c9e25e8b661c04e84
```

The first workflow attempt was rejected only by Ruff E501 formatting. Commit
`9a729d1fd5ee5b4bfa783656a45c58f4581bfd7b` corrected that technical defect without changing
the replay mechanism, geometry, evidence or economics. The successful run then completed:

```text
focused quality:                    GREEN
immutable source SHA verification:  GREEN
R34 exact replay:                   GREEN
R34 row-for-row parity:             GREEN
same causal signal/entry/stop/target GREEN
risk arithmetic reproduction:       GREEN
generic Phase-18 scorer parity:     GREEN
artifact SHA256 manifest:           GREEN
```

Generic Phase-18 scoring reproduces the authoritative XAUUSD R34 5Y baseline exactly:

```text
trades:          921
profit_factor:   1.529741881717934130030753380
total_r:         103.6427513069166048428626309
max_drawdown_r:  9.19605447572090219358745533
positive annual: 4/5
```

XAUUSD remains fail-closed for the USD CIBO sizing comparison:

```text
R_DENOMINATED_ONLY
CALIBRATION_REQUIRED
USD_CIBO_SIZING_COMPARISON_AUTHORIZED = FALSE
```

No historical spread, commission, slippage, margin-per-volume or tick-value value was fabricated.

Phase 18 now has exact causal replay evidence for **7/7 CMA Trader lineages**:
R38 GBPJPY, R43 GBPUSD, R42 AUDJPY, R38 EURUSD, R34 XAUUSD, VT08 FOREX and VT31 NAS100.
Each lineage passed independently; no Trader inherited acceptance from another.

### VT08 FOREX R3.15 Phase-18 checkpoint — 26-SEP-2026

The final independent VT08 replay authenticates the frozen B_COMBINED holdout and R3.12
capital-policy source, proves exact legacy risk-formula parity, preserves the 124 certified
opportunities, and keeps broker execution economics separate from the pre-broker capital policy.

```text
workflow_run: 36261289169  SUCCESS
head_sha:     251f7e282417dbbf5eb820b42da7ae3de3b1d5e4
artifact_id:  10913050112
artifact:     qore-cibo-phase18-vt08-r315-251f7e282417dbbf5eb820b42da7ae3de3b1d5e4
digest:       sha256:8543a33962d24d3f5346981328df78d145286fc8af9387d73eca85519922f568
rows:         124
```

Generic legacy-policy scoring:

```text
trades:                    124
profit_factor:             1.188909111149905336636134137
total_r25:                 9.288150320501074848855803027
max_drawdown_r25:          5.901218670573083195516115149
max_loss_streak:           7
provider_economics_status: R_DENOMINATED_ONLY
```

The FundedNext and FTMO profile replays produce the same causal risk sequence. Decimal accounting
residue is explicitly measured and bounded rather than silently rounded. Historical broker
spread/slippage/quantity economics remain unproven, so:

```text
CALIBRATION_REQUIRED
USD_CIBO_SIZING_COMPARISON_AUTHORIZED = FALSE
```

### VT31 NAS100 V4 Phase-18 checkpoint — 26-SEP-2026

VT31 is now bound to the immutable V4 execution source and authoritative five-year artifact.
A serialization defect was resolved without touching the historical row pipeline: missing REARM
geometry is captured in a side channel while the causal setup exists, then merged only into the
separate Phase-18 serialization after the original historical physicalization completes.

```text
workflow_run: 36261289233  SUCCESS
head_sha:     251f7e282417dbbf5eb820b42da7ae3de3b1d5e4
artifact_id:  10912945588
artifact:     qore-cibo-phase18-vt31-v4-251f7e282417dbbf5eb820b42da7ae3de3b1d5e4
digest:       sha256:2200392deeb081525720430a816e8f82b18d7333c61a05eb197632ed24849e15
rows:         806
source_sha:   cac38ed14f20e066536910145027426fd23f5939
```

Authoritative V4 parity and metrics:

```text
authoritative JSON exact without serialized rows: TRUE
same signals/entry/stop/target/path:              TRUE
same legacy capital-weighted result:              TRUE
profit_factor:                                    3.455321118486999415676978877
total_r:                                          61.38049535416448786455402411
max_drawdown_r:                                   3.70898490728154195122908861
max_loss_streak:                                  11
```

VT31 likewise remains:

```text
R_DENOMINATED_ONLY
CALIBRATION_REQUIRED
USD_CIBO_SIZING_COMPARISON_AUTHORIZED = FALSE
```

**Phase-18 closure rule:** the seven Trader histories are now independently reproducible and
causally serializable. This closes the per-Trader evidence-binding phase. It does **not** authorize
cross-Trader R summation and does **not** claim historical USD provider economics that are absent
from retained evidence.

---

## PHASE 19 — Integrated portfolio replay

**Status: IN PROGRESS — PHASE 19C-H EMPIRICAL GREEN / PHASE 19I NEXT / USD CAPITAL REPLAY BLOCKED_PROVIDER_ECONOMICS**

The Phase-19 readiness and chronology contract now exists in:

```text
src/qore/infrastructure/cibo_ce2i_phase19_portfolio_replay.py
```

Phase 19 is deliberately split into two scientific depths:

1. **Integrated chronology/concurrency replay** — authorized once all seven Phase-18 lineages are
   independently bound. This may merge timestamps, detect simultaneous positions, measure overlap
   and build competition structure.
2. **Integrated USD capital replay** — authorized only when every lineage has provider economics
   sufficient for comparable historical USD risk, margin and execution-cost arithmetic.

Current invariant:

```text
PHASE18_POPULATION_COMPLETE                    = TRUE
CHRONOLOGY_REPLAY_AUTHORIZED                   = TRUE

HISTORICAL_USD_REPLAY_AUTHORIZED               = FALSE
HISTORICAL_PROVIDER_REPLAY_AUTHORIZED          = FALSE
CROSS_TRADER_RAW_R_AGGREGATION_AUTHORIZED      = FALSE

NORMALIZED_CAPITAL_REPLAY_CONTRACT_IMPLEMENTED = TRUE
NORMALIZED_CAPITAL_REPLAY_AUTHORIZED           = TRUE_RESEARCH_ONLY_7_OF_7

PARTIAL_PROVIDER_IDENTIFICATION_AUTHORIZED      = PENDING_PHASE20_ENVELOPES
COUNTERFACTUAL_PROVIDER_STRESS_AUTHORIZED       = TRUE
COUNTERFACTUAL_PROVIDER_STRESS_LABEL            = COUNTERFACTUAL

FORWARD_PROVIDER_ECONOMIC_CAPTURE_REQUIRED      = TRUE
LIVE_PROVIDER_CERTIFICATION                     = REQUIRES_FORWARD_OBSERVED_ECONOMICS

HISTORICAL_USD_BLOCKER                          = PROVIDER_ECONOMICS
```

### Phase 19C — CIBO normalized capital numeraire

The first dimensionless capital-policy contract now exists in:

```text
src/qore/infrastructure/cibo_ce2i_phase19_normalized_capital.py
tests/infrastructure/test_cibo_ce2i_phase19_normalized_capital.py
```

Scientific purpose:

- continue CIBO capital-policy science without fabricating historical USD;
- preserve the ban on summing heterogeneous Trader R directly;
- express every accepted opportunity through an ex-ante CIBO-owned normalized
  risk-capacity budget;
- apply the post-trade R outcome only when the historical exit event is reached;
- reserve/release normalized capacity chronologically;
- reject an allocation when normalized capacity is insufficient rather than
  silently clipping the requested budget;
- forbid same-timestamp exit recycling because provider settlement ordering is
  not proven historically;
- surface a capacity breach when realized loss exceeds the intended structural
  risk budget instead of manufacturing recapitalization.

The contract makes no USD, margin or historical-provider claim and has no
allocation, Risk or execution authority.


### Phase 19D mechanics baseline

The sealed-evidence workflow now runs a deliberately non-optimized 7/7 mechanics
baseline:

```text
initial normalized capital: 100 NCU
risk budget per opportunity: 1 NCU
training used:               FALSE
outcome-aware ranking:        FALSE
allocator policy certified:   FALSE
```

This baseline exists only to prove normalized reservation, settlement and
capital accounting across the 855 common-window opportunities. Its performance
must not be used to choose a production sizing policy.

### Phase 19E temporal coincidence null

The workflow also runs a 1,000-permutation deterministic null model with a
frozen seed. Each opportunity preserves Trader identity, weekday, UTC
time-of-day and observed duration while its calendar date is independently
reassigned inside the common window.

The null answers only whether observed cross-Trader temporal overlap exceeds
calendar/session coincidence under that explicit null. It consumes no outcomes,
sizing, provider economics or USD and has zero allocation/Risk/execution
authority.



### Phase 19F overlap-conditioned dependence

The sealed workflow now measures, separately in the frozen 60% TRAIN segment
and the 40% VALIDATION segment:

- overlap-pair count;
- left/right loss frequency inside overlap pairs;
- joint-loss frequency;
- independence-implied joint-loss frequency;
- joint-loss excess;
- same-nonzero-sign frequency.

This layer uses post-trade outcomes only after chronology has fixed the overlap
pairs. It never consumes historical sizing, USD PnL or provider economics, and
it remains descriptive-only with zero allocation/Risk/execution authority.

No threshold such as "correlation > X" is frozen here. Phase 19F exists to
measure whether adverse dependence is present and whether it survives temporal
validation before Phase 19G may study actual capital collisions.


### Phase 19G capital collision and marginal-capacity evidence

Temporal coexistence is now separated from actual normalized-capital scarcity.

A `capital collision` exists only when:

- a frozen normalized policy rejects an opportunity for insufficient capacity;
- one or more previously accepted opportunities still reserve normalized
  capacity at that exact entry event;
- the rejection has a positive normalized-capacity shortfall.

Insufficient-capacity rejection with no active reservation blocker is classified
separately as realized-capital depletion, not collision.

The empirical workflow runs the unchanged Phase-19D one-NCU mechanics policy on
predeclared normalized-capacity scenarios:

```text
2 / 3 / 4 / 5 / 10 / 100 NCU
```

The 2-5 NCU region brackets the observed maximum concurrency of five positions;
10 and 100 NCU are loose-capacity references. The grid is frozen by structural
reasoning, not outcome tuning.

For adjacent capacity scenarios the workflow reports a finite-difference
`marginal_realized_delta_per_ncu`. This is explicitly **ex-post evaluation**,
not a causal forecast and not a claimed mathematical dual/shadow price. More
initial capacity is allowed to have negative marginal realized value because
the system is path-dependent: extra capacity may admit an additional losing
trade and reduce later feasible capacity.

TRAIN and VALIDATION are replayed separately with the Phase-19B split and
capital reset at each segment boundary for stability research only.

No Phase-19G output has sizing/allocation/QORE-Risk/execution authority.

### Phase 19H resource / dependence hypergraph

Pairwise overlap is no longer the only representation of concurrent portfolio
structure.

Phase 19H introduces two explicitly distinct hyperedge families:

```text
TEMPORAL_CONCURRENCY
NORMALIZED_CAPITAL_COLLISION
```

A temporal hyperedge represents a positive-duration active set with at least two
distinct Traders. It is pure chronology and makes no correlation or harmful
interaction claim.

A resource-collision hyperedge exists only under a predeclared normalized
capacity scenario when one rejected opportunity collides with one or more
active reservations. It retains the rejected opportunity, all blockers and the
normalized capacity shortfall.

The empirical workflow measures the full-window temporal hypergraph and
TRAIN/VALIDATION temporal/resource structures separately. Collision hyperedges
are evaluated on the same 2/3/4/5/10/100 NCU scenarios used by Phase 19G.

Hypergraph centrality, clique size or membership has **no automatic sizing
meaning**. Phase 19H has zero sizing-penalty, allocation, QORE-Risk or execution
authority. Later WFO must demonstrate incremental capital relevance before any
hypergraph feature can become actionable.

Current Phase-19 scientific sequence is therefore:

```text
19A  INTEGRATED CHRONOLOGY                  GREEN
19B  TEMPORAL STABILITY                     MEASURED / OBSERVATIONAL ONLY
19C  CAPITAL NUMERAIRE CONTRACT              GREEN / RESEARCH ONLY
19D  NORMALIZED CAPITAL LEDGER 7/7           EMPIRICAL GREEN
19E  TEMPORAL NULL MODEL                     EMPIRICAL GREEN
19F  OVERLAP DEPENDENCE TRAIN/VALIDATION     EMPIRICAL GREEN / DESCRIPTIVE
19G  CAPITAL COLLISION + MARGINAL CAPACITY   EMPIRICAL GREEN / ZERO COLLISIONS IN TESTED GRID
19H  RESOURCE / DEPENDENCE HYPERGRAPH        EMPIRICAL GREEN / DESCRIPTIVE
19I  SIMPLE CAPITAL POLICY BASELINES          EMPIRICAL GREEN / TRAIN ONLY
19J  CAUSAL NORMALIZED WFO                    FALSIFIED / 0 OF 6 SURVIVED
```

The chronology-only motor sorts opportunities causally, validates all seven Trader populations,
detects duplicate signal identities, computes maximum concurrent positions and overlapping
position pairs, and returns an object that is constitutionally unable to perform USD arithmetic or
cross-Trader R aggregation.

### Phase-19 integrated chronology empirical checkpoint — 26-SEP-2026

The first seven-Trader integrated replay is now independently GREEN in both push and PR workflows.
It consumes only the seven sealed Phase-18 artifacts and verifies each artifact ZIP digest plus its
internal SHA256 manifest before replay.

```text
head_sha:        e0cddeefab144a49c48de9df0d7c117e1456f3b0
push_run:        36262706237  SUCCESS
pr_run:          36262709115  SUCCESS
artifact_id:     10912847765
artifact:        qore-cibo-phase19-integrated-chronology-e0cddeefab144a49c48de9df0d7c117e1456f3b0
artifact_digest: sha256:208d5ca523735273e9f40026bab1a0da041147a610f7c3af50d82c9873ff4072
report_sha256:   18dfde3bc8975db3604d20aff3b61d73d29ea7bec76dfd2b640f5bc92b5b9fb6
```

Strict fully-observed seven-Trader common window:

```text
start: 2021-09-23T05:00:00+00:00
end:   2022-06-29T09:00:00+00:00

R34_XAUUSD: 132
R38_EURUSD: 130
R38_GBPJPY: 152
R42_AUDJPY: 133
R43_GBPUSD: 147
VT08_FOREX:  45
VT31_NAS100: 116
TOTAL:       855
```

Observed chronology/concurrency evidence:

```text
max_concurrent_positions:          5
overlapping_position_pairs:        254
cross_trader_overlapping_pairs:    250
same_trader_overlapping_pairs:       4
multi_trader_entry_days:           183
```

Largest observed pair overlaps in the common window include:

```text
R38_GBPJPY | R42_AUDJPY  30
R34_XAUUSD | R43_GBPUSD  22
R38_EURUSD | R43_GBPUSD  22
R34_XAUUSD | R42_AUDJPY  19
R42_AUDJPY | R43_GBPUSD  19
R38_EURUSD | R38_GBPJPY  17
R38_GBPJPY | R43_GBPUSD  17
```

This proves temporal competition is material and gives Phase 13/19 an empirical interaction graph,
but it **does not** prove common USD risk, correlation-adjusted capital weights or portfolio
expectancy. Those remain separate claims.

### Phase-19C-H sealed empirical checkpoint — 27-SEP-2026

After repairing the quality gate, exact normalized-capital accounting and order-dependent Decimal
rounding in the temporal-stability metric, the integrated Phase-19 workflow is now GREEN through
the 19H evidence layer.

```text
evidence_head:    4dad367d7bf334710554e6ea5feca9b478984aaf
main_push_run:    36284404971  SUCCESS
phase19_push_run: 36284404972  SUCCESS
artifact_id:      10919742007
artifact:         qore-cibo-phase19-integrated-chronology-4dad367d7bf334710554e6ea5feca9b478984aaf
artifact_digest:  sha256:4636bd06e9e9df7fbb5edb45091e345a2df8e427cdf5bdb13395a5333a942016
manifest:         SHA256SUMS 15/15 VERIFIED
```

The 19D mechanics baseline is deliberately non-optimized and exists to validate capital-policy
plumbing, not to certify a sizing policy:

```text
initial_capital_ncu:        100
opportunities:              855
accepted:                   855
rejected:                     0
ending_capital_ncu:         194.7729926484665552874887110
total_realized_delta_ncu:   +94.77299264846655528748871100
max_drawdown_ncu:            27.25008452475013116475627789
peak_reserved_risk_ncu:       5
capacity_breach_observed:    FALSE
```

Phase 19E shows that the observed 250 cross-Trader overlap pairs are above the conditioned
calendar/session null under the frozen 1,000-permutation experiment:

```text
observed_cross_trader_overlaps: 250
null_mean:                      217.784
null_p95:                       241
upper_tail_probability:         0.01798201798201798201798201798
seed:                           19019
```

This is evidence that timing structure is not explained entirely by the explicit null. It is **not**
evidence that overlap is economically harmful, and it grants no sizing penalty.

Phase 19F measured overlap-conditioned dependence separately in TRAIN and VALIDATION. The
strongest joint-loss excess did not preserve the same pair across the split, so no fixed pairwise
dependence penalty is certified from this evidence.

Phase 19G produced an important falsification under the frozen one-NCU mechanics policy and the
predeclared 2/3/4/5/10/100 NCU grid:

```text
NORMALIZED_CAPITAL_COLLISIONS: 0
```

All low-capacity insufficient-capacity rejections were classified as
`DEPLETION_ONLY_REJECTION`, not as blocking by concurrent active reservations. Therefore temporal
coexistence must not be silently converted into a scarcity or concentration penalty.

Phase 19H still confirms material multi-opportunity temporal structure:

```text
full_window_temporal_hyperedges: 230
max_hyperedge_cardinality:         5
max_distinct_traders:              4
cardinality_distribution:
  2 -> 198
  3 ->  26
  4 ->   5
  5 ->   1
```

But normalized-capital collision hyperedges remained zero across every tested capacity scenario.
The hypergraph remains descriptive evidence only.

The temporal-stability metric is now computed from integer overlap counts with a common denominator
instead of summing already-rounded pair shares. This removes pair-order dependence without changing
the split, populations or overlap counts. Canonical evidence is:

```text
training_opportunities:              523
validation_opportunities:            332
training_cross_trader_overlaps:       155
validation_cross_trader_overlaps:      95
boundary_crossing_excluded:             0
total_variation_distance: 0.2258064516129032258064516129
weighted_jaccard:         0.6315789473684210526315789474
```

Historical USD replay remains blocked because exact retained provider economics are still missing.
Phase 19I must therefore compare only causal, transparent normalized-capital policy baselines and
must not use Phase-19 validation outcomes to choose or tune a winner.

### Phase-19I simple capital policy baseline checkpoint — 27-SEP-2026

Phase 19I is now GREEN in both the main CI and the integrated Phase-19 scientific workflow.

```text
evidence_head:      53601a1a8f9fcc3710b84bde432cc858fcce4641
main_push_run:      36285318899  SUCCESS
main_pr_run:        36285322859  SUCCESS
phase19_push_run:   36285318903  SUCCESS
phase19_pr_run:     36285322835  SUCCESS
artifact_id:        10920601351
artifact:           qore-cibo-phase19-integrated-chronology-53601a1a8f9fcc3710b84bde432cc858fcce4641
artifact_digest:    sha256:17e0fdf1ba0793304be52577ff91f3df82685caabcffffc6ada46f0fefbf6a8e
internal_manifest:  SHA256SUMS 22/22 VERIFIED
```

The suite was frozen before empirical execution and used only the 523-opportunity TRAIN segment.
Validation rows were checked for split integrity but validation outcomes were not used for policy
evaluation, ranking or tuning.

The frozen suite uses 10 gross NCU, already predeclared in Phase 19G as a loose-capacity reference.
It deliberately contains no Trader-specific weights, dependence threshold, overlap penalty,
hypergraph penalty or advanced optimizer.

```text
POLICY                         ACCEPT  REJECT   TOTAL DELTA NCU    MAX DD NCU
P19I_EQUAL_100_NO_RESERVE       295     228    -9.2929368294      24.2509655820
P19I_EQUAL_075_NO_RESERVE       523       0   +68.7933581243      20.4375633936
P19I_EQUAL_050_NO_RESERVE       523       0   +45.8622387495      13.6250422624
P19I_EQUAL_025_NO_RESERVE       523       0   +22.9311193748       6.81252113119
P19I_EQUAL_050_RESERVE_2        523       0   +45.8622387495      13.6250422624
P19I_EQUAL_025_RESERVE_2        523       0   +22.9311193748       6.81252113119
```

Training evidence therefore exposes a material **capacity cliff** between the 0.75-NCU and
1.00-NCU fixed-budget baselines. At 1.00 NCU, normalized-capacity rejections become path-changing:
228 opportunities are rejected and the replay finishes below its 10-NCU start. At 0.75 NCU and
below, all 523 TRAIN opportunities are accepted.

When every opportunity is accepted, the 0.75/0.50/0.25 baselines scale linearly in absolute
realized delta and drawdown. That is expected from the fixed normalized-risk budget and is not an
independent edge claim.

The 2-NCU fixed reserve is empirically inert at 0.50 and 0.25 NCU in TRAIN: it does not change
accepted population, realized delta or absolute drawdown. Therefore Phase 19I does **not**
demonstrate incremental value from fixed reserve/optionality under those two policies.

No policy is selected or certified from TRAIN. All six predeclared policies advance unchanged to
Phase 19J. In particular, 0.75 NCU must not be called optimal merely because it avoids the TRAIN
capacity cliff; Phase 19J must test whether that behavior survives strictly later evidence.

Phase 19J is therefore required to run a frozen causal forward comparison after the 60% TRAIN
cutoff, with no parameter changes inside validation and no use of future outcomes for allocation.

### Phase-19J causal normalized walk-forward falsification — 27-SEP-2026

Phase 19J completed with its survival rule frozen before validation. The result is a material
scientific falsification of the Phase-19I fixed-budget/fixed-reserve family as a temporally stable
capital policy.

```text
evidence_head:      9cb8bd22ec2cff7f9f113f084820c077b2c8a495
main_push_run:      36285850063  SUCCESS
main_pr_run:        36285852552  SUCCESS
phase19_push_run:   36285849972  SUCCESS
phase19_pr_run:     36285852475  SUCCESS
artifact_id:        10920422891
artifact_digest:    sha256:7c7a8c1f6d5d48fb27c916f9c4c45b6d11c5af83b0db51cdf0826768025e6074
internal_manifest:  SHA256SUMS 24/24 VERIFIED
```

Causal validation population:

```text
training_rows_before_freeze:       523
entry_based_validation_rows:       332
causal_decision_validation_rows:   332
pre_freeze_decision_exclusions:      0
midpoint_crossing_exclusions:        0

WF1: 2022-03-09T17:00Z -> 2022-05-04T13:00Z   170 opportunities
WF2: 2022-05-04T13:00Z -> 2022-06-29T09:00Z   162 opportunities
```

Survival rule was predeclared and not modified after observing validation:

- combined post-freeze realized delta > 0;
- each forward fold realized delta > 0;
- no capacity breach;
- no insolvent rejection;
- no magnitude threshold;
- no policy ranking;
- no refit between folds.

Result:

```text
surviving_policy_count: 0
surviving_policy_ids:   []
```

All six policies fail the same temporal-stability gate:

`FOLD_2_REALIZED_DELTA_NOT_POSITIVE`

Forward evidence:

```text
POLICY                         COMBINED DELTA      WF1 DELTA          WF2 DELTA
P19I_EQUAL_100_NO_RESERVE      +3.0485151494      +10.7710520287     -9.0456780230
P19I_EQUAL_075_NO_RESERVE      +2.2863863620       +8.0782890215     -9.7520319547
P19I_EQUAL_050_NO_RESERVE      +1.5242575747       +5.3855260144     -3.8612684397
P19I_EQUAL_025_NO_RESERVE      +0.7621287873       +2.6927630072     -1.9306342198
P19I_EQUAL_050_RESERVE_2       +1.5242575747       +5.3855260144     -3.8612684397
P19I_EQUAL_025_RESERVE_2       +0.7621287873       +2.6927630072     -1.9306342198
```

Important interpretation:

1. The combined 40% validation remains positive for all six policies, but that is insufficient under
   the predeclared temporal-stability gate.
2. WF2 is negative for every candidate.
3. At 0.50 and 0.25 NCU all 162 WF2 opportunities are accepted, so the negative second fold cannot
   be explained solely by normalized-capital scarcity/rejection.
4. The 1.00 and 0.75 NCU policies additionally suffer path-dependent capacity starvation in WF2,
   but relaxing their size would not solve the deeper sign instability demonstrated by 0.50/0.25.
5. Fixed reserve remains non-incremental in the tested policies.

Therefore:

```text
PHASE19I_FIXED_POLICY_FAMILY_CERTIFIED = FALSE
PHASE19J_VALIDATION_BURNED             = TRUE
PHASE20_POLICY_CERTIFICATION_BLOCKED   = TRUE
```

The 332-row post-freeze interval must not be reused as OOS evidence for a redesigned policy. Any
new policy family designed after this result requires genuinely fresh forward evidence for
qualification. Reusing this validation and changing thresholds/budgets until it passes would be
validation mining.

This falsification does **not** invalidate the CMA accounting architecture, the normalized capital
ledger, the source ledger, Risk sovereignty, or the CE2I tool contracts. It falsifies this specific
simple fixed-budget/fixed-reserve policy family as a stable final allocator.

Work may continue on Phase-20 components that are policy-independent (provider ambiguity,
partial-identification machinery, counterfactual provider stress, failure engineering primitives),
but Phase 21 policy freeze and Phase 22 sealed holdout remain blocked until a new policy family is
developed without mining the burned Phase-19J validation and obtains fresh validation evidence.

The provider-economic evidence gate is also hardened with explicit evidence classes:

```text
EXACT_HISTORICAL
PERIOD_STATIC_VERIFIED
CURRENT_SNAPSHOT_ONLY
MISSING
```

A current snapshot cannot be promoted to historical replay evidence. Historical spread must be
EXACT_HISTORICAL before Phase 19 can authorize integrated USD capital arithmetic.

This allows immediate study of:

- simultaneous opportunities;
- temporal opportunity clustering;
- cross-Trader overlap;
- candidate competition windows;
- opportunity starvation structure;
- factor/correlation research hooks;
- reservation ordering;

without fabricating:

- historical spread;
- historical commission;
- historical slippage;
- historical margin-per-volume;
- historical tick value;
- or a false common R unit.

USD-dependent study remains fail-closed until provider-economic evidence is calibrated:

- risk/margin reservations in real USD;
- capital recycling in real USD;
- aggregate USD drawdown;
- peak original capital at risk;
- minimum executable quantity and broker granularity under historical conditions.

---

## PHASE 20 — Robust capital-policy validation under uncertainty

**Status: IN PROGRESS — 20A/B CONTRACT GREEN / 20C COUNTERFACTUAL CONTRACT GREEN / EMPIRICAL CALIBRATION PENDING / POLICY VALIDATION BLOCKED**

Required sequence:

- 20A provider ambiguity sets;
- 20B partial-identification bounds;
- 20C permanently-labelled counterfactual provider stress;
- 20D causal WFO;
- 20E capital-state Monte Carlo;
- 20F independent CE2I mechanism certification;
- 20G ablation / interaction studies;
- 20H robust constrained allocator candidates;
- 20I receding-horizon optionality / MPC research;
- 20J failure engineering: execution cost, margin, spread/slippage,
  correlation break, opportunity clustering, loss clusters,
  reservation/reconciliation faults, stale state and restart.

Phase 20 may use current observed provider facts plus explicit adverse scenarios,
but must never relabel them as historical economics.

### Phase 20A/B — Provider ambiguity + partial identification checkpoint — 27-SEP-2026

The uncertainty engine now exists independently of any allocator candidate. This work is valid even
though the Phase-19I fixed-policy family was falsified, because it does not choose, rank or tune a
capital policy.

```text
evidence_head:       da5514fb2ddfa3a5c8cf4c9e58d3e7a4407474c0
phase20_push_run:    36286285129  SUCCESS
phase20_pr_run:      36286287508  SUCCESS
main_pr_run:         36286287480  SUCCESS
artifact_id:         10920388754
artifact_digest:     sha256:ded11006611d0ad6f02fb2359635d6a256a0876cfb611b4af0f3d5283abd67c2
internal_manifest:   SHA256SUMS 3/3 VERIFIED
```

Phase 20A now has a typed rectangular ambiguity-set contract over:

- tick size;
- tick value;
- spread ticks;
- commission per volume;
- slippage reserve per volume;
- margin per volume;
- minimum volume;
- maximum volume;
- volume step;
- available liquidity volume;
- execution delay.

Every set carries explicit evidence provenance and fails closed if it attempts to claim exact
historical economics, outcome tuning, policy-pass tuning, allocation authority, QORE Risk authority
or execution authority.

Phase 20B now computes conservative lower/upper bounds for:

- minimum executable volume;
- stop loss per volume;
- minimum stop risk;
- minimum margin;
- guaranteed/possible maximum volume;
- guaranteed/possible liquidity;
- execution delay.

It returns exactly one of:

```text
ROBUSTLY_FEASIBLE
ROBUSTLY_INFEASIBLE
PARTIALLY_IDENTIFIED
```

The sealed artifact uses **synthetic contract fixtures only** and proves all three classifications.
It explicitly states:

```text
provider_calibration_claimed = FALSE
historical_economics_claimed = FALSE
outcome_tuned                = FALSE
policy_pass_tuned            = FALSE
```

Therefore the implementation status is:

```text
PHASE20A_AMBIGUITY_CONTRACT_IMPLEMENTED      = TRUE
PHASE20A_EMPIRICAL_PROVIDER_BOUNDS_CALIBRATED = FALSE
PHASE20B_PARTIAL_IDENTIFICATION_ENGINE_GREEN = TRUE
PHASE20B_HISTORICAL_USD_POINT_ESTIMATE       = FORBIDDEN
```

Actual provider ambiguity ranges must be supplied later by documented bounds, forward observed
data, or explicitly labelled counterfactual assumptions. They must not be chosen to make a policy
pass.

### Phase 20C — Counterfactual provider stress matrix checkpoint — 27-SEP-2026

Phase 20C is now contract-GREEN as a permanently non-historical robustness/failure experiment.

Evidence:

```text
evidence_head:       c64681881a7562b6474e414a6e82d9682f4ade5d
main_push_run:       36287014945  SUCCESS
main_pr_run:         36287017591  SUCCESS
phase20_pr_run:      36287017589  SUCCESS
artifact_id:         10920926070
artifact_digest:     sha256:16ae530f0ac4fec03c1bb66176ae9c5bfc98a132e501251d9e35001d423d1190
internal_manifest:   SHA256SUMS 5/5 VERIFIED
```

The frozen synthetic matrix has nine explicit scenarios:

- current-snapshot counterfactual baseline;
- spread x2;
- commission x2;
- slippage-reserve floor;
- margin x2;
- 2000 ms execution-delay floor;
- unavailable-liquidity failure;
- minimum-volume cliff failure;
- combined adverse provider economics.

The engine now returns an explicit result for provider infeasibility rather than silently dropping
the opportunity. In particular, unavailable liquidity and a minimum-volume/maximum-volume cliff are
represented as `FAIL_CLOSED_PROVIDER_CONSTRAINT` with an auditable reason.

For every executable adverse scenario the contract enforces:

- Trader entry / structural stop / technical target geometry is unchanged;
- execution cost cannot improve relative to the frozen baseline;
- margin economics cannot improve relative to the frozen baseline;
- stop-loss-per-volume cannot improve relative to the frozen baseline;
- counterfactual current-provider economics are never promoted to historical truth.

The sealed artifact uses **synthetic contract fixtures only**. Phase 19J burned validation is not
consumed by Phase 20C.

```text
PHASE20C_COUNTERFACTUAL_STRESS_CONTRACT_GREEN = TRUE
PHASE20C_PROVIDER_CALIBRATION_CLAIMED         = FALSE
PHASE20C_HISTORICAL_ECONOMICS_CLAIMED         = FALSE
PHASE20C_PHASE19J_VALIDATION_REUSED            = FALSE
PHASE20C_POLICY_CERTIFIED                      = FALSE
```

Phase 20C therefore hardens the provider-uncertainty/failure machinery but does not rescue the
falsified Phase-19I allocator family and does not unblock Phase 21/22.

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
1. Preserve the sealed PHASE 18 7/7 causal geometry evidence unchanged.
2. Complete PHASE 19C/19D: bind all seven lineages to the CIBO normalized capital numeraire and normalized transactional ledger.
3. Build PHASE 19E/19F: temporal null models plus dependence/tail evidence without historical sizing contamination.
4. Build PHASE 19G/19H: capital-collision/shadow-price evidence and the resource/dependence hypergraph.
5. Compare simple frozen capital-policy baselines before introducing advanced optimizers.
6. Run PHASE 20 partial identification, counterfactual provider stress, WFO, capital-state Monte Carlo, ablations and failure engineering.
7. Freeze the surviving CMA/CE2I policy in PHASE 21.
8. Run one genuinely fresh sealed PHASE 22 holdout before any Owner-gated DEMO execution change.
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
