# CIBO SOVEREIGN CAPITAL INTELLIGENCE + COMPOUNDING — MASTER ROADMAP V3

Primary PR: #651
Canonical base ADR: CIBO-CE2I-ADR-002-CAPITAL-MANAGEMENT-AUTHORITY.md
Compounding ADR: CIBO-CE2I-ADR-003-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING.md
Gap audit: CIBO-MAXIMUM-CAPITAL-INTELLIGENCE-COMPOUNDING-GAP-AUDIT-V1.md
Governance: OPEN / DRAFT / UNMERGED / RESEARCH ONLY


## CURRENT SOURCE-OF-TRUTH RECONCILIATION — 30-SEP-2026

This section supersedes older current-state wording while preserving every historical checkpoint below.

Common checkpoint:

`1460435615a663a614cd5ee8873f719d08086200`

Canonical machine ledger at that checkpoint:

```text
MANDATORY WORKSTREAMS = 64
TERMINAL              = 7
OPEN                  = 57
ZERO_OPEN WORK PASS   = FALSE
FINAL CERT CANDIDATE  = FALSE
```

Current engineering frontier:

```text
GEN-C0   = COMPLETED_AND_PROVEN
GEN-C1   = ENGINE_IMPLEMENTED / MATHEMATICAL RECONCILIATION CLOSURE IN PROGRESS
GEN-C2   = ENGINE_IMPLEMENTED / SCIENTIFIC VALUE CLOSURE OPEN
GEN-C3   = ENGINE_IMPLEMENTED / END-TO-END ECONOMIC CYCLE OPEN
GEN-C4   = ENGINE_IMPLEMENTED / REAL-DATA CAUSAL VALUE OPEN
GEN-C5   = ENGINE_IMPLEMENTED / FRESH OOS-STRESS-REPLICATION OPEN
GEN-C6   = ENGINE_IMPLEMENTED / TRUE-SCARCITY OOS-STRESS-REPLICATION OPEN
GEN-C7   = ENGINE_IMPLEMENTED / GIVEBACK-RETENTION OOS-STRESS-REPLICATION OPEN
GEN-C8   = ENGINE_IMPLEMENTED / CI GREEN / SCIENTIFIC CLOSURE OPEN
GEN-C9   = ENGINE IMPLEMENTED + PATH MC + NON-COMPENSATORY GATE / CI GREEN
GEN-C10  = ENGINE_IMPLEMENTED / CI GREEN / REAL TWIN + CALIBRATION OPEN
GEN-C11  = ENGINE_IMPLEMENTED / CI GREEN / FRESH MULTI-PERIOD UTILITY OPEN
GEN-C12  = ENGINE_IMPLEMENTED / CI GREEN / REAL CRISIS EVIDENCE OPEN
GEN-C13  = ENGINE_IMPLEMENTED / CI GREEN / IDENTIFICATION + REPLICATION OPEN
GEN-C14  = ENGINE_IMPLEMENTED / CI GREEN / REAL HYPOTHESIS PIPELINE OPEN
```

Current shared scientific infrastructure also includes:

- dependency-aware Compound Monte Carlo;
- GEN-C9 non-compensatory economic gate;
- preregistered Compound adversarial stress matrix;
- Compound temporal-replication harness;
- integrated Compound Engine cycle;
- Protected Base research overlay.

None of those engineering completions is economic certification.

The frozen V3 candidate remains unchanged and the 2017H1 holdout remains SEALED_UNTOUCHED.

Two common-checkpoint red workflows are integration-side defects assigned to Architect B under the certification split. Architect A must not edit those B-owned files.

Canonical reconciliation artifact:

`docs/research/CIBO-SOURCE-OF-TRUTH-RECONCILIATION-V1.md`


## 0. Dual-track law

The current CIBO V3 certification program and the new compounding research program run in parallel.

Track A — current CIBO certification:
V3 Phase20D -> causal tool gates -> Phase21 -> Phase22 -> final CIBO certification.

Track B — maximum capital intelligence:
GEN-C0 -> GEN-C14.

Track B must not mutate Track A retrospectively.

## GEN-C0 — Constitutional separation

Objective: create a clean research lineage for compounding without contaminating V3.

Deliverables:
- ADR-003.
- Gap Audit V1.
- Master Roadmap V3.
- lineage identity CIBO_SOVEREIGN_CAPITAL_COMPOUNDING_RESEARCH_V1.
- explicit zero runtime/LIVE/real-capital/merge authority.
- explicit holdout exclusion.

Exit gate:
- all governance invariants documented.
- V3 candidate unchanged.
- 2017H1 unchanged.

Status at roadmap creation: COMPLETE FOR DOCUMENTATION.

## GEN-C1 — Compound accounting foundation

Objective: make every realized compound dollar conserved, account-local, attributable and generation-aware before any intelligent compounding policy exists.

Required modules:
- cibo_compound_capital.py
- cibo_compound_generation.py
- cibo_compound_portfolio_ledger.py
- cibo_compound_portfolio_store.py

Required concepts:
- CompoundCapitalState.
- CompoundCapitalLot.
- account identity binding.
- origin trade/signal/Trader/account.
- realized settlement provenance.
- capital generation.
- Core ownership.
- Trader attribution.
- protected amount.
- reserve amount.
- deployable amount.
- deployed amount.
- released amount.
- retired-to-floor amount.

Hard invariants:
- no cross-account fungibility.
- no floating-PnL funding.
- no double-spend.
- settlement before compoundability.
- exact source conservation.
- one economic state per dollar.
- attribution does not grant ownership.
- reserve is not deployable.
- retired floor is not deployable.
- deployed capital is not simultaneously available.
- idempotent settlement ingestion.
- append-only persistence.
- hash-chain integrity.
- generation CAS.
- writer lock.
- restart persistence.

Economic claim allowed: NONE.

Exit gate: contract-green accounting invariants only.

## GEN-C2 — Protected capital floor mechanics

Objective: create policy-neutral mechanics for converting realized capital into a protected capital floor.

Required concepts:
- ACCOUNTING_PROTECTED.
- POLICY_PROTECTED.
- BROKER_GUARANTEED.
- ProtectedFloorEvent.
- account-local floor history.
- monotonic policy-floor mechanics where the policy demands monotonicity.
- reversible distinction between accounting observation and policy commitment.

Forbidden:
- arbitrary protect-X-percent policy.
- calling policy protection a broker guarantee.

Exit gate:
- conservation and classification tests.
- no optimization yet.

## GEN-C3 — Core Compound Portfolio

Objective: create the account-local economic portfolio for the fruits of Core.

Portfolio buckets:
- protected floor.
- strategic reserve.
- opportunity reserve.
- active compound capacity.
- deployed compound capital.
- pending settlement.

Required read-only global view:
- aggregate attribution across accounts.
- no capital transfer authority.

Exit gate:
- exact portfolio conservation.
- account isolation.
- provenance from settlement to current state.

## GEN-C4 — Marginal Capital Utility evidence contract

Objective: define the evidence needed to judge the next unit of capital before building an optimizer.

Required dimensions:
- expected incremental return.
- incremental stop risk.
- incremental margin.
- incremental execution cost.
- incremental concentration.
- incremental factor/tail exposure.
- incremental drawdown contribution.
- incremental optionality consumed.
- capital duration.
- provider constraints.
- epistemic uncertainty.
- Shared certified facts.

Required interfaces:
- Shared -> CIBO read-only intelligence contract.
- T08 factor facts.
- T10 duration/velocity facts.
- T11 execution economics.
- T15 optionality facts.

Exit gate:
- causal timestamped evidence schema.
- no outcome-aware score.
- no automatic size authority.

## GEN-C5 — Sequential Compounding Controller

Objective: research the sequence SEED -> OBSERVE -> PROTECT -> RECOVER -> EXPAND -> DE-RISK -> HARVEST -> RECYCLE -> COMPOUND.

Initial posture vocabulary may include:
- ACCELERATED_COMPOUND.
- NORMAL_COMPOUND.
- CAUTIOUS_COMPOUND.
- DEFENSIVE.
- SURVIVAL.
- COMPOUND_PAUSED.

Thresholds must be preregistered or learned only through legal research splits.

Exit gate:
- shadow-only controller.
- pre-outcome durable decisions.
- no runtime authority.

## GEN-C6 — Internal Capital Market

Objective: extend T09/T18 into compound-capital competition across Traders.

Candidate comparison must include:
- expected value.
- uncertainty.
- failure hazard.
- capital duration.
- margin.
- execution economics.
- factor concentration.
- positive-tail potential.
- Shared facts.
- optionality cost.

Forbidden:
- equal 1/N budgets.
- Trader identity priority.
- cross-account fictitious transfer.

Exit gate:
- fresh scarcity population.
- preregistered control/treatment.
- OOS utility.

## GEN-C7 — Profit Preservation, Harvesting and Giveback

Objective: reduce return of conquered capital without house-money bias.

Required evidence:
- peak realized profit.
- peak protected profit.
- subsequent giveback.
- causal CIBO action lineage.
- floor changes.
- reserve decisions.
- compound decisions.

Required outputs:
- ProfitRetentionRatio.
- GivebackAmount.
- GivebackCause.
- FloorGrowthRate.
- BaseDD.
- CompoundDD.

Exit gate:
- fresh OOS policy utility.
- no unacceptable growth sacrifice under frozen criteria.

## GEN-C8 — Drawdown- and uncertainty-adaptive compound speed

Objective: make compounding accelerate or decelerate from calibrated evidence.

Inputs:
- drawdown.
- loss clusters.
- edge calibration.
- Shared uncertainty.
- regime stability.
- provider degradation.
- factor concentration.
- margin state.
- Risk headroom.

Exit gate:
- calibrated score/state mapping.
- OOS stability.
- no score-to-size shortcut.

## GEN-C9 — Robust growth / ruin / capacity science

Objective: optimize long-term robust growth instead of historical maximum compounding.

Research candidates:
- fractional Kelly.
- drawdown-constrained Kelly.
- risk-sensitive utility.
- robust growth optimality.
- distributionally robust allocation.
- capacity/saturation models.

Mandatory model risks:
- estimation error.
- fat tails.
- serial dependence.
- regime shift.
- execution cost.
- provider limits.

Required metrics:
- growth.
- DD.
- tail loss.
- time underwater.
- recovery duration.
- risk of ruin under declared assumptions.
- scalability ceiling.

Exit gate:
- no automatic production authority.
- falsification on stress and replication.

## GEN-C10 — Capital Digital Twin

Objective: maintain a causal state twin of current capital and possible future capital states.

State includes:
- base capital.
- protected floor.
- realized profit.
- reserves.
- compound generations.
- active deployments.
- risk/margin headroom.
- known future options.
- provider constraints.

Worlds may include:
- aggressive growth.
- balanced.
- defensive.
- crisis.
- opportunity scarcity.
- opportunity abundance.

Exit gate:
- state conservation.
- calibrated transition uncertainty.

## GEN-C11 — Robust Multi-Period Capital MPC

Objective: extend current horizon-2 mechanics to robust multi-period compound planning.

Must consider:
- future opportunities.
- uncertainty.
- floor.
- reserve.
- DD.
- margin.
- factor interactions.
- capital duration.
- optionality.

Forbidden:
- future leakage.
- oracle opportunity arrivals.

Exit gate:
- preregistered shadow policy.
- fresh OOS utility.
- stress robustness.

## GEN-C12 — Crisis / extreme-regime capital intelligence

Objective: survive and remain selectively productive under extreme regimes.

Taxonomy:
- survival event.
- liquidity event.
- systemic deleveraging.
- extreme opportunity.
- broker degradation.
- margin event.
- correlation convergence.

Response set:
- reduce.
- reserve.
- minimal seed.
- selective expansion.
- aggressive protection.
- no deployment.

Stress worlds:
- depression-like.
- credit collapse.
- liquidity shock.
- currency crisis.
- bond crisis.
- hyper-volatility.
- deflationary shock.
- inflationary shock.

Exit gate:
- scenario robustness without synthetic claims of probability.

## GEN-C13 — Meta-capital memory, counterfactual lab and skeptic

Objective: make capital decisions scientifically inspectable and learnable.

Memory classes:
- capital episodic memory.
- drawdown memory.
- compounding memory.
- expansion failure memory.
- reserve value memory.
- opportunity cost memory.
- portfolio stress memory.

Failure phenotypes:
- OVERCOMPOUNDING.
- UNDERCOMPOUNDING.
- PREMATURE_EXPANSION.
- LATE_EXPANSION.
- EXCESS_RESERVE.
- INSUFFICIENT_RESERVE.
- CAPITAL_CONCENTRATION.
- OPTIONALITY_DESTRUCTION.
- PROFIT_GIVEBACK.

Counterfactual lab questions:
- deploy less.
- deploy more.
- reserve.
- compound earlier/later.
- ratchet floor earlier/later.

All counterfactual analysis is post-outcome research and cannot rewrite historical decisions.

Exit gate:
- leakage firewall.
- immutable decision provenance.

## GEN-C14 — Governed Autonomous Capital Science

Objective: allow CIBO to propose, test and reject capital hypotheses without self-promoting.

Pipeline:
CAPITAL PROBLEM -> HYPOTHESIS -> PREREGISTRATION -> SIMULATION/BURNED -> OOS -> STRESS -> REPLICATION -> OWNER/GOVERNANCE -> PROMOTION.

Possible specialist research functions:
- Compounding Mind.
- Portfolio Allocation Mind.
- Drawdown Mind.
- Optionality Mind.
- Marginal Utility Mind.
- Execution Economics Mind.
- Crisis Capital Mind.
- Skeptic Capital Mind.

These functions are allowed only when they add falsifiable scientific value.

## Certification program for the compounding layer

The compound program receives no economic authority merely because GEN-C1..C14 code exists.

Future certification identity should be separate from the current V3 certification.

Minimum comparison:
CONTROL = exact certified CIBO policy.
TREATMENT = exact certified CIBO policy + frozen compounding layer.

Required gates:
- ending realized capital improvement under the declared test.
- growth-rate improvement or justified non-degradation under the frozen objective.
- no unacceptable DD increase.
- profit retention improvement.
- risk-of-ruin non-degradation.
- optionality preservation.
- stress robustness.
- multi-regime robustness.
- complete provenance.
- no leakage.
- no outcome refit.

## Immediate engineering order

1. Preserve current V3 and current Phase20/21/22 work.
2. Implement GEN-C1 accounting contracts only.
3. Add dedicated tests and CI for compound conservation.
4. Keep all new compound outputs research-only and non-mutating.
5. After GEN-C1 green, implement GEN-C2 policy-neutral floor mechanics.
6. Then build GEN-C3 portfolio buckets and global read-only view.
7. Only after accounting foundations are stable begin marginal utility and compounding-policy research.

## Final objective

Build CIBO so that valid Trader edge can become realized profit, protected profit, compound capital, better future capital allocation, higher protected floors and additional generations of productive capital — without martingale, double-spend, leakage, fabricated capacity, hidden concentration or survival compromise.

---

# WORLD CUP SOVEREIGN CAPITAL AMPLIFICATION GOVERNING LAYER — 29-SEP-2026

Canonical mission document:

`docs/research/CIBO-SOVEREIGN-CAPITAL-AMPLIFICATION-WORLD-CUP-MISSION-V1.md`

This layer does not replace CE2I T01–T20 or GEN-C0–GEN-C14. It changes the
definition of successful completion from "capital mechanics exist" to
"capital amplification value is causally demonstrated under survival
constraints."

Binding identity:

```text
CIBO != POSITION SIZER
CIBO != LEVERAGE MANAGER
CIBO != SECOND RISK ENGINE

CIBO = QORE SOVEREIGN CAPITAL AMPLIFICATION INTELLIGENCE
```

Binding research question:

```text
HOW MUCH ROBUST ECONOMIC UPSIDE
CAN THE NEXT UNIT OF PLAUSIBLE LOSS CONTROL?
```

## Current implementation frontier

At this governing checkpoint:

```text
GEN-C0  constitutional separation                  = CLOSED
GEN-C1  compound accounting / generations          = ENGINE_IMPLEMENTED
GEN-C2  protected capital floor                     = ENGINE_IMPLEMENTED
GEN-C3  Core Compound Portfolio                     = ENGINE_IMPLEMENTED
GEN-C4  marginal capital utility evidence           = ENGINE_IMPLEMENTED
GEN-C5  sequential compounding shadow               = ENGINE_IMPLEMENTED
GEN-C6  Internal Capital Market                     = ENGINE_IMPLEMENTED
GEN-C7  profit preservation / giveback shadow       = ENGINE_IMPLEMENTED
GEN-C8  adaptive compound speed                     = ARCHITECTURE_DEFINED
GEN-C9  robust growth / ruin / capacity              = ARCHITECTURE_DEFINED
GEN-C10 capital digital twin                        = ARCHITECTURE_DEFINED
GEN-C11 robust multi-period MPC                     = ARCHITECTURE_DEFINED
GEN-C12 crisis intelligence                         = ARCHITECTURE_DEFINED
GEN-C13 meta-capital memory / skeptic                = ARCHITECTURE_DEFINED
GEN-C14 governed autonomous capital science          = ARCHITECTURE_DEFINED
```

ENGINE_IMPLEMENTED does not mean VALUE_DEMONSTRATED, OOS_PASS,
STRESS_PASS, TEMPORAL_REPLICATION_PASS or CERTIFIED.

GEN-C5, GEN-C6 and GEN-C7 remain research/shadow until fresh causal economic
evidence exists. Current V3 certification remains a separate frozen lineage.

## Canonical maturity vocabulary

All future CIBO capability reporting must use:

```text
ARCHITECTURE_DEFINED
CONTRACT_IMPLEMENTED
ENGINE_IMPLEMENTED
REAL_DATA_BOUND
CAUSAL_REPLAY_EXECUTED
VALUE_DEMONSTRATED
OOS_PASS
STRESS_PASS
TEMPORAL_REPLICATION_PASS
CERTIFICATION_CANDIDATE
CERTIFIED
```

For failure or blocked work, use an explicit terminal or dependency state such
as FALSIFIED, NO_VALUE, INSUFFICIENT, TOO_FRAGILE, TOO_EXPENSIVE,
NO_PROVIDER_ADVANTAGE, NO_MARGINAL_BENEFIT or
BLOCKED_EXTERNAL_DEPENDENCY:<reason>.

## Updated engineering order

The earlier "GEN-C1 next" sequence above is retained as historical provenance.
The active order is now:

1. Keep V3 and 2017H1 frozen.
2. Keep CI green; no red CIBO workflow may be ignored.
3. Maintain the World Cup requirement→CE2I/GEN-C GAP matrix.
4. Finish existing C5/C6/C7 real-data/OOS/stress work.
5. Deepen T01, T04, T05, T06, T07, T09, T10, T15, T20 around capital
   amplification per unit of plausible loss.
6. Implement GEN-C8.
7. Implement GEN-C9.
8. Implement GEN-C10.
9. Implement GEN-C11.
10. Implement GEN-C12.
11. Implement GEN-C13.
12. Implement GEN-C14.
13. Close T08/T09/T12/T13/T14/T15/T18 economic gates and explicit T16/T17
    provider-universe terminal states.
14. Build ablation, chronological replay, path-dependent Monte Carlo, stress
    and temporal replication.
15. Preserve the final holdout until all prerequisite mechanisms are frozen.
16. Certify ordinary CIBO first.
17. Execute the separate World Cup Maximum-Capability Exam afterward.

The +2,000% World Cup aspiration is an experimental North Star only. It must
never become a tuning target or excuse for proportional risk expansion.


---

# ABSOLUTE CLOSURE GOVERNING AMENDMENT — 30-SEP-2026

Canonical amendment:

CIBO-ABSOLUTE-CLOSURE-AMENDMENT-V1.md

Canonical machine-readable open-work inventory:

CIBO-MASTER-OPEN-WORK-LEDGER-V1.json

Canonical machine gate:

scripts/cibo_zero_open_work_gate.py

## Binding closure law

CIBO cannot become FINAL CERTIFICATION CANDIDATE while any mandatory CIBO
workstream lacks a terminal disposition.

Allowed terminal dispositions:

- COMPLETED_AND_PROVEN
- FALSIFIED_AND_CLOSED
- SUPERSEDED_WITH_PROVEN_LINEAGE
- EXTERNAL_DEPENDENCY_BLOCKED

A certification-critical EXTERNAL_DEPENDENCY_BLOCKED row keeps global
certification blocked.

## Non-compensatory critical path

The following are mandatory and non-compensatory:

- Compound Intelligence Engine;
- Core Compound Portfolio;
- Internal Capital Market;
- Capital Generations;
- Protected Capital Floor;
- Sequential Compounding;
- Profit Preservation;
- Marginal Capital Utility;
- GEN-C8 through GEN-C14;
- CE2I T01–T20 closure;
- provider economics;
- forward qualification;
- path-dependent Monte Carlo;
- adversarial stress;
- fresh OOS;
- temporal replication;
- final integrated CIBO exam.

Great return cannot compensate for failure or incompleteness of any required
capability.

## Current ledger checkpoint

The machine ledger now contains 62 mandatory workstreams after explicit separation of PROTECTED_BASE_CAPITAL, Phase18/Phase19 evidence, CMA foundation, CE2I calibration/cross-tool, legacy cognitive/executive and USD60 capability programs.

Only GEN-C0 is currently recorded as terminally COMPLETED_AND_PROVEN; 61 mandatory workstreams remain open pending further terminal dispositions.

All other rows remain certification-blocking until their scientific or
engineering closure evidence is produced.

This statement is intentionally stricter than ENGINE_IMPLEMENTED or green CI.

## GEN-C8 update

GEN-C8 now has:

- preregistration;
- adaptive-speed shadow engine;
- durable pre-outcome store;
- descriptive population;
- tests;
- dedicated CI workflow.

Its current state is ENGINE_IMPLEMENTED pending CI revalidation and fresh
economic/OOS/stress/replication evidence. It is not certified and may not be
counted as economic value.

## Certification invocation

Routine CI:

    python scripts/cibo_zero_open_work_gate.py

Final certification enforcement:

    python scripts/cibo_zero_open_work_gate.py --enforce-certification

The final command must exit successfully before CIBO may be considered a final
certification candidate.

ALL CI GREEN != CIBO CERTIFIED.


## Full-file inventory checkpoint

At the current absolute-closure audit, the CIBO inventory contains 575 files
across source, scripts, tests, workflows and CIBO research documents.

The zero-open-work classifier currently assigns 575/575 files to explicit
workstreams and reports zero unclassified orphan candidates.

Classification is not closure. Legacy/historical/supporting families remain
open until their own workstream receives a terminal scientific disposition.
