# CIBO SOVEREIGN CAPITAL INTELLIGENCE + COMPOUNDING — MASTER ROADMAP V3

Primary PR: #651
Canonical base ADR: CIBO-CE2I-ADR-002-CAPITAL-MANAGEMENT-AUTHORITY.md
Compounding ADR: CIBO-CE2I-ADR-003-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING.md
Gap audit: CIBO-MAXIMUM-CAPITAL-INTELLIGENCE-COMPOUNDING-GAP-AUDIT-V1.md
Governance: OPEN / DRAFT / UNMERGED / RESEARCH ONLY

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