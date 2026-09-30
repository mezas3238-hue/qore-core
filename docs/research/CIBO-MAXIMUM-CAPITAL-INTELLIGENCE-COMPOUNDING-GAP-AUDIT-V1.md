# CIBO MAXIMUM CAPITAL INTELLIGENCE + COMPOUNDING GAP AUDIT V1

> **CURRENT-STATE NOTE — 29-SEP-2026:** This file is retained as the original
> gap-audit provenance. Several `ABSENT/PARTIAL` rows below describe the state
> at audit creation and are no longer the current implementation truth.
> Current requirement routing and maturity are maintained in
> `CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md` and the
> current GitHub HEAD/CI. Do not use historical rows below to downgrade or
> duplicate capabilities already implemented in GEN-C1–GEN-C7.
>
> The governing mission is
> `CIBO-SOVEREIGN-CAPITAL-AMPLIFICATION-WORLD-CUP-MISSION-V1.md`.


Owner directive: 29-SEP-2026
Primary PR: #651 — [DRAFT] CIBO Capital Management Authority + CE2I V1
Branch: agent/cibo-capital-efficiency-sizing-lab-001
GitHub checkpoint audited: 0c77be5f09d50d1531bfbb57c99b560a2875b76a
Governance: OPEN / DRAFT / UNMERGED / RESEARCH ONLY
Holdout: CIBO_USD60_6M_HOLDOUT_2017H1_V1 — SEALED_UNTOUCHED
Frozen Phase20 candidate: CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3

## 0. Audit conclusion

The current CIBO already contains substantial capital-management primitives, but it does not yet constitute the Owner-directed QORE SOVEREIGN CAPITAL INTELLIGENCE & COMPOUNDING ENGINE.

Current GitHub already contains sole CIBO sizing authority, account-scoped capital missions, minimum-seed entry, economic-floor/base-recovery logic, durable source accounting, realized settlement accounting, released-capacity recycling, realized-profit/protected-capacity expansion, multi-source expansion, portfolio competition/reservations, T12 regime tool eligibility, T13 reserve research, T15 optionality research, T08 factor-risk research, T11 execution economics, provider uncertainty, chronological replay, capital-state Monte Carlo mechanics, fresh-forward evidence, and Phase21/22 lineage protection.

Those are necessary foundations. They do not yet answer how realized profit becomes protected profit, compoundable capital or reserve; how the protected floor ratchets upward; how fast compounding should proceed; whether the next dollar belongs here, elsewhere or in reserve; how capital generations are tracked; or whether growth comes from true compounding rather than higher leverage.

Central gap:

CURRENT CIBO = capital authority + CE2I mechanisms + causal certification program
OWNER TARGET = current CIBO + compound-capital constitution + Core Compound Portfolio + protected-floor ratchet + profit preservation + marginal-capital utility + multi-period robust growth control + capital digital twin + crisis/ruin science + compound-specific certification.

## 1. Non-contamination law

This audit grants no authority to mutate V3. The following remain immutable for the active certification lineage:

- CIBO_PHASE20_FULL_SURFACE_FORWARD_CANDIDATE_V3
- frozen Phase20D thresholds
- Phase21 promotion contract
- Phase22 holdout lineage contract
- CIBO_USD60_6M_HOLDOUT_2017H1_V1

The compounding program must start as a parallel research lineage. Recommended identity: CIBO_SOVEREIGN_CAPITAL_COMPOUNDING_RESEARCH_V1.

It must never open 2017H1 for development, rewrite V3 outcomes, backdate decisions, reuse burned evidence as fresh OOS, treat synthetic fixtures as economic proof, or relabel leverage as compound growth.

## 2. Maturity vocabulary

ABSENT / ARCHITECTURE_ONLY / CONTRACT_ONLY / PROTOTYPE / PARTIAL / RESEARCH / FALSIFIED / IMPLEMENTED / VALIDATED / REPLICATED / CERTIFICATION_READY

IMPLEMENTED means mechanics exist and are tested for the stated contract. VALIDATED requires legitimate empirical evidence for the economic claim. REPLICATED requires temporal/regime replication. CERTIFICATION_READY means the declared OOS/stress/provenance gates are complete.

## 3. Capability gap matrix

| Capability | Current status | Current module / contract | Economic maturity | Real data | Causality | OOS | Stress | Certification | Missing work | Dependencies | Priority |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Sole CIBO sizing/capital authority | IMPLEMENTED | ADR-002, TraderOpportunityEnvelope, CiboRiskRequest chain | Strong architecture | yes | explicit authority split | current CIBO pending | failure contracts | not certified | preserve boundary | current CMA | P0 |
| Account-local capital domains | IMPLEMENTED | cibo_account_capital_mission.py | strong mechanics | yes | account-bound | not compound-specific | provider/risk tests | foundation | extend all compound ledgers by account identity | GEN-C1 | P0 |
| Realized settlement accounting | IMPLEMENTED | cibo_cma_settlement_ledger.py/store | strong mechanics | DEMO supported | lifecycle-bound | compound effect untested | restart/idempotency | foundation | settlement-to-compound source creation | GEN-C1 | P0 |
| Capital source ledger / no double-spend | IMPLEMENTED | cibo_capital_source_ledger.py/store | strong mechanics | yes | source-bound | accounting law | CAS/restart/failure | foundation | extend source states without duplicating value | GEN-C1 | P0 |
| Base vs realized-profit separation | IMPLEMENTED | CapitalSource | strong foundation | yes | explicit | not a compound policy | n/a | foundation | add protected profit / compoundable / reserve constitution | GEN-C1 | P0 |
| Floating PnL exclusion from cash | IMPLEMENTED | ADR-002, cibo_economic_floor.py | strong | yes | conservative | n/a | fail-closed | foundation | preserve absolutely | all | P0 |
| Economic floor / base recovery | IMPLEMENTED | cibo_economic_floor.py | strong mechanics | yes | reconciled | incremental value unproven | partial | foundation | account-level protected floor ratchet | GEN-C2 | P0 |
| Protected capital floor ratchet | ABSENT | none canonical | none | no | no | no | no | none | define mechanics and separate policy | GEN-C1/2 | P0 |
| CMA COMPOUND_OR_RESERVE stage | IMPLEMENTED | cibo_capital_state_machine.py | structural | yes | current-state | policy utility unproven | transition tests | not certified | create explicit portfolio compound lifecycle | GEN-C1/3 | P0 |
| Realized-profit expansion | IMPLEMENTED | T06, multi-source expansion | mechanism | yes | source-constrained | fresh OOS pending | contract tests | not certified | distinguish trade expansion from portfolio compounding | GEN-C3/5 | P0 |
| Protected-capacity expansion | IMPLEMENTED | T07 | mechanism | yes | reconciled floor | fresh OOS pending | contract tests | not certified | preserve distinction from cash | GEN-C2/5 | P0 |
| Released-capacity recycling | IMPLEMENTED | T05, cibo_ce2i_recycling.py | mechanism | yes | release-bound | incremental utility pending | restart tests | not certified | integrate generations/opportunity cost | GEN-C3/5 | P1 |
| Multi-source economic funding | IMPLEMENTED | cibo_ce2i_multi_source.py | strong mechanics | yes | atomic provenance | utility pending | accounting tests | not certified | portfolio-level source allocation | GEN-C3 | P0 |
| QORE_COMPOUNDING_INTELLIGENCE_ENGINE | ABSENT | none | none | no | no | no | no | none | create research-only engine constitution | GEN-C1-5 | P0 |
| QORE_CORE_COMPOUND_PORTFOLIO | ABSENT | none | none | no | no | no | no | none | account-local portfolio + global logical view | GEN-C3 | P0 |
| Compound portfolio durable ledger | ABSENT | existing source ledger is narrower | none | no | no | no | no | none | origin trade/trader/account/generation/floor/reserve/deployed/released | GEN-C1/3 | P0 |
| Compound capital state constitution | ABSENT | ReservationState insufficient | none | no | no | no | no | none | realized/protected/compoundable/reserved/deployed/released/retired states | GEN-C1 | P0 |
| Attribution != ownership | PARTIAL | provenance lots and source IDs | structural | partial | possible | no portfolio proof | n/a | no | Core ownership with origin attribution | GEN-C3 | P0 |
| Capital generations GEN-0..N | ABSENT | none | none | no | no | no | no | none | descendant capital lineage | GEN-C1/3 | P1 |
| Profit preservation intelligence | ABSENT | T13 is not equivalent | none | no | no | no | no | none | protect/compound/reserve/harvest policy | GEN-C2/7 | P0 |
| Profit harvesting | ABSENT | none | none | no | no | no | no | none | policy-neutral mechanics first, policy later | GEN-C2/7 | P0 |
| Compound reserve | ABSENT | T13 general reserve exists | none | no | no | no | no | none | compound-specific reserve state and evidence | GEN-C3/7 | P1 |
| Opportunity reserve | PARTIAL | T13/T15 | research | forward architecture | bound provenance | causal benefit unresolved | partial | not certified | preregistered treatment/control | T15 + GEN-C5 | P1 |
| Compounding speed control | ABSENT | none | none | no | no | no | no | none | accelerate/normal/cautious/defensive/survival/paused research policy | GEN-C5/8 | P0 |
| Drawdown-adaptive compounding | PARTIAL | T13 + regime posture | research | architecture yes | pre-outcome shadow | empirical population needed | partial | not certified | map reserve evidence to compound speed | GEN-C8 | P0 |
| Marginal Capital Utility Engine | ABSENT | T11 is only execution component | none | no | no | no | no | none | incremental return/risk/margin/cost/concentration/DD/optionality/duration | GEN-C4 | P0 |
| Capital opportunity cost | PARTIAL | T15 + T09 | research | opportunity sets | causal option evidence | reservation utility unresolved | limited | not certified | explicit DEPLOY_NOW vs KEEP_AVAILABLE ablation | GEN-C4/5 | P0 |
| Internal capital market | PARTIAL | T09/T18 + portfolio allocation ledger | research | scarcity collection designed | exact epoch binding | fresh scarcity utility required | portfolio tests | not certified | compound-specific marginal bidding | GEN-C6 | P0 |
| Cross-Trader allocation | PARTIAL | T09/T18 | research | Phase19 exact competition 0; forward required | strong | scorer exists | limited | not certified | real scarcity + compound treatment | T09/T18 + GEN-C6 | P0 |
| Shared to CIBO intelligence contract | ABSENT | no canonical read-only compound contract | none | no | no | no | no | none | certified fact schema; no Shared sizing authority | Shared + GEN-C4 | P0 |
| Positive-tail capitalization | PARTIAL | T06/T07 mechanics | low | no certified tail input | incomplete | no | no | none | Shared tail contract + marginal expansion ablation | Shared + GEN-C5 | P1 |
| Sequential capital control | PARTIAL | CMA lifecycle | structural | yes | causal current-state | no compound utility | some failures | not certified | add portfolio HARVEST/RECYCLE/COMPOUND loop | GEN-C5 | P0 |
| Multi-period capital intelligence | PARTIAL | current MPC horizon=2 | prototype | forward options | causal | no compound proof | synthetic mechanics | not certified | robust multi-horizon planning | GEN-C10/11 | P1 |
| Capital duration / time-to-release | PARTIAL | T10 + capital_minutes | research | realized duration | causal at settlement | policy incomplete | little | not certified | causal duration forecasting and allocation use | GEN-C4/11 | P1 |
| Execution-aware compounding | PARTIAL | T11 | research | forward fills/slippage | causal | policy unresolved | provider stress | not certified | require certified execution economics for expansion | T11 + GEN-C4 | P0 |
| Capital saturation / diminishing returns | ABSENT | none beyond T11 execution cap | none | no | no | no | no | none | edge capacity vs incremental capital | GEN-C4/9 | P1 |
| Factor/latent concentration | PARTIAL | T08 factor/correlation/risk mapping | research | architecture yes | conservative | OOS utility required | partial | not certified | latent/tail factor state | T08 + GEN-C6/12 | P0 |
| Crisis correlation / tail dependence | ABSENT | none canonical | none | no | no | no | no | none | stress-correlation and tail-dependence contract | GEN-C12 | P1 |
| Extreme-regime capital intelligence | ABSENT | generic regime insufficient | none | no | no | no | generic stress only | none | crisis taxonomy and selective response set | GEN-C12 | P1 |
| Risk-of-ruin constrained growth | ABSENT | Risk hard limits are not growth optimization | none | no | no | no | no | none | ruin/survival-horizon research | GEN-C9 | P0 |
| Robust growth / Kelly research | ABSENT | none | none | no | no | no | no | none | estimation-error/fat-tail/serial/provider-aware research | GEN-C9 | P1 |
| Epistemic uncertainty to compound speed | ABSENT | no calibrated mapping | none | no | no | no | no | none | uncertainty calibration with no score-to-size shortcut | Shared + GEN-C8/9 | P0 |
| Capital confidence calibration | PARTIAL | cibo_ce2i_calibration_registry.py | research | mixed | strong anti-holdout law | many tools pending | mixed | not certified | extend to every compound signal/score | GEN-C4+ | P0 |
| Profit giveback intelligence | ABSENT | none | none | no | no | no | no | none | realized/protected peak and causal giveback attribution | GEN-C7 | P0 |
| Base DD vs compound DD | ABSENT | current DD aggregate | none | no | no | no | no | none | lineage-aware DD without house-money bias | GEN-C1/7 | P0 |
| Capital maturity | ABSENT | none | none | no | no | no | no | none | test delay before full redeployment | GEN-C7/9 | P2 |
| Multi-horizon compounding | ABSENT | none | none | no | no | no | no | none | trade/session/week/month/multi-month hierarchy | GEN-C11 | P1 |
| Compound curve quality | PARTIAL | Phase20/21 delta/DD/productivity | research | inputs exist | causal | not compound-specific | MC mechanics | not certified | underwater/recovery/retention/ruin/floor growth | GEN-C7/9 | P0 |
| Capital digital twin | PROTOTYPE | Phase20 capital-state Monte Carlo mechanics | low | synthetic + normalized history | mechanics only | no compound OOS | synthetic | none | account state twin with floors/reserves/generations/options | GEN-C10 | P1 |
| Capital world model | ABSENT | none | none | no | no | no | no | none | alternative capital worlds + uncertainty bounds | GEN-C10/11 | P2 |
| Robust multi-period capital MPC | PROTOTYPE | current forecastless horizon-2 MPC | low | current forward architecture | causal | no compound value proof | limited | none | floor/reserve/DD/optionality/future arrivals | GEN-C11 | P1 |
| Compound memory | ABSENT | accounting ledgers are not learning memory | none | no | no | no | no | none | episodic/DD/expansion/reserve/opportunity-cost/stress memory | GEN-C13 | P2 |
| Capital counterfactual lab | PARTIAL | ablation + Monte Carlo foundations | research | synthetic/burned | post-outcome only | no compound OOS | partial | none | less/more/reserve/earlier-floor experiments with leakage firewall | GEN-C9/13 | P1 |
| Compound failure phenotypes | ABSENT | generic failures only | none | no | no | no | generic | none | over/under-compounding, premature/late expansion, reserve errors, giveback | GEN-C7/13 | P1 |
| Meta-capital intelligence | ABSENT | calibration registry is a seed | none | no | no | no | no | none | trust/evidence weakness/regime coverage/calibration debt | GEN-C13 | P2 |
| Capital skeptic | ABSENT | none | none | no | no | no | no | none | challenger contract against double-counting/overconfidence | GEN-C13/14 | P2 |
| Governed self-improvement | PARTIAL | existing PR/phase governance | process mature | n/a | n/a | n/a | n/a | no auto promotion | formal IDEA→SANDBOX→OOS→STRESS→REPLICATION→OWNER | GEN-C14 | P2 |
| CIBO/Risk requested→authorized→executed separation | IMPLEMENTED | CiboRiskRequest + Risk + execution | strong | yes | explicit | compound actions untested | failures | foundation | reuse unchanged | all | P0 |
| Protected-capital classification | PARTIAL | protected economic floor | structural | yes | conservative | no ratchet OOS | limited | none | ACCOUNTING/POLICY/BROKER-guaranteed distinction | GEN-C2 | P0 |
| Compound dashboard/evidence model | ABSENT | scattered metrics | none | partial inputs | n/a | no | no | none | canonical evidence schema | GEN-C3/7 | P1 |
| Compound economic attribution | PARTIAL | capital provenance | structural | partial | possible | no decomposition | no | none | Trader edge vs allocation vs recycling vs compounding | GEN-C3/9 | P1 |
| CIBO value baseline comparison | PARTIAL | Phase20 policy vs minimal-seed baseline | research | architecture yes | strong | fresh population missing | Phase21 planned | not certified | current-CIBO vs CIBO+Compound treatment | compound certification | P0 |
| Compound efficiency metrics | ABSENT as canonical set | ingredients exist | none | partial | n/a | no | no | none | gain/base$, gain/risk$, gain/risk-minute, retention, floor growth | GEN-C7/9 | P1 |
| Scalability ceiling / capital capacity | ABSENT | provider max is not edge capacity | none | no | no | no | no | none | identify saturation point | GEN-C4/9 | P1 |
| Capital overflow policy | ABSENT | generic reserve only | none | no | no | no | no | none | reserve/protect/wait when capital exceeds edge capacity | GEN-C7/9 | P1 |
| True compounding vs leverage | PARTIAL | source ledger distinguishes sources | structural | yes | causal source identity | no generation metric | no | none | realized descendant lineage required for compound claim | GEN-C1/3 | P0 |
| Compounding-specific certification | ABSENT | current Phase20/21/22 is V3 certification | none | no | must be separate | no | no | none | CONTROL=current certified CIBO; TREATMENT=CIBO+Compounding | dedicated lineage | P0 |

## 4. Current T01-T20 relevance

Direct foundations: T01 Minimal Seed; T05 Recycling; T06 Profit-Funded Expansion; T07 Protected-Capacity Expansion; T09 Competition; T10 Capital Velocity; T11 Execution-Efficient Exposure; T12 Regime-Adaptive Capitalization; T13 Drawdown Reserve; T14 Dynamic De-risking; T15 Optionality; T18 Cross-Trader Allocation; T19 Reservation; T20 Release.

Critical dependencies: T03 because margin efficiency changes reusable capacity; T08 because compounding can amplify common-factor concentration; T16/T17 remain fail-closed and must never be used to invent hedge or limited-downside capacity.

## 5. Current-state findings at audited HEAD

1. V3 remains frozen and protected.
2. Since earlier checkpoint 3459e3b8, the branch advanced 18 commits before this audit.
3. T12 now has fresh OOS readiness, frozen OOS utility analysis, runtime-shadow binding, causal-readiness integration and qualification integration.
4. T12 is not empirically READY because the required fresh population does not yet exist.
5. T13 now has an OOS utility module, but existence of the scorer is not empirical promotion; the canonical registry still correctly requires fresh OOS reserve utility.
6. Holdout CIBO_USD60_6M_HOLDOUT_2017H1_V1 remains SEALED_UNTOUCHED and outcome_data_inspected_at_selection=false.

## 6. Required compound-capital constitution

Recommended account-local economic states:

- PROFIT_PENDING_RECONCILIATION
- REALIZED_PROFIT
- PROTECTED_PROFIT
- COMPOUNDABLE
- STRATEGIC_RESERVE
- OPPORTUNITY_RESERVE
- ACTIVE_COMPOUND_CAPACITY
- DEPLOYED_COMPOUND_CAPITAL
- RELEASED_COMPOUND_CAPITAL
- RETIRED_TO_PROTECTED_FLOOR

Invariant: every economically realized compound dollar has exactly one current economic state inside one account domain. No transition may create value. Changes in value must be explained by reconciled gain/loss, execution cost, provider fee or economic consumption.

## 7. Core Compound Portfolio target

The portfolio must be account-local for money and Core-wide only for logical intelligence. It must contain original base, protected floor, realized profit, protected profit, strategic reserve, opportunity reserve, active compound capacity and deployed compound capital. It must also preserve attribution to origin Trader, signal, account, settlement, generation and CIBO action lineage.

Attribution never grants future ownership or allocation rights to the originating Trader.

## 8. Capital generations

GEN-0 = original base capital.
GEN-1 = realized economic profit generated by deployment funded wholly or partly by GEN-0.
GEN-2 = realized profit generated by deployment containing eligible GEN-1 capital.
GEN-N = later descendants with complete source lineage.

Generation is provenance, not a license to gamble. All realized generations remain real Core capital and remain subject to Risk.

## 9. Protected floor ratchet

The ratchet must be account-local and distinguish ACCOUNTING_PROTECTED, POLICY_PROTECTED and BROKER_GUARANTEED. A policy floor may constrain CIBO internally but must never be described as a broker guarantee. No arbitrary fixed protection percentage is authorized.

## 10. Four decisions that must remain separate

1. Profit reconciliation.
2. Profit protection / floor ratchet.
3. Compound eligibility.
4. Marginal deployment.

Profit exists does not imply profit is compoundable, and compoundable does not imply deploy now.

## 11. Separate compounding certification lineage

CONTROL = the exact CIBO policy that ultimately earns the current certification.
TREATMENT = same Trader opportunities + same Shared facts + same provider/Risk facts + same execution constraints + Compounding Intelligence + Core Compound Portfolio.

The treatment may alter only legal CIBO capital actions. It may not alter Trader setup, side, technical entry, stop, target, validity or Risk hard constraints.

## 12. Minimum future certification gates

Compare ending realized capital, robust growth rate, settlement-cash DD, time underwater, recovery duration, profit retention, protected-floor growth, capital productivity, capital-risk-time productivity, optionality preservation, tail loss and declared-model risk of ruin.

No performance compensation: more ending capital cannot offset an unacceptable survival/DD/tail breach.

Stress must include block/order variation, loss clusters, opportunity-arrival variation, correlation convergence, provider-cost stress, capital-release timing, margin shock, spread explosion, simultaneous Trader losses, opportunity scarcity, opportunity abundance and rapid regime reversals.

## 13. Dependency-ordered roadmap proposal

GEN-C0 Constitutional separation / research lineage.
GEN-C1 Compound accounting + generations + provenance.
GEN-C2 Protected floor mechanics + profit-protection evidence.
GEN-C3 Core Compound Portfolio + reserves + account-local ownership.
GEN-C4 Marginal Capital Utility + duration + opportunity-cost inputs.
GEN-C5 Sequential Compounding Controller.
GEN-C6 Cross-Trader Internal Capital Market for compound capital.
GEN-C7 Profit Preservation / Harvesting / Giveback intelligence.
GEN-C8 Drawdown- and uncertainty-adaptive compound speed.
GEN-C9 Robust growth / ruin / capacity / saturation science.
GEN-C10 Capital Digital Twin.
GEN-C11 Robust Multi-Period Capital MPC.
GEN-C12 Crisis / extreme-regime compound intelligence.
GEN-C13 Meta-capital memory / counterfactual / skeptic.
GEN-C14 Governed Autonomous Capital Science.

## 14. First implementation boundary

The first code after this audit should not be a sizing formula. It should be the QORE_CORE_COMPOUND_PORTFOLIO accounting foundation with zero runtime authority.

Recommended first modules: cibo_compound_capital.py, cibo_compound_portfolio_ledger.py, cibo_compound_portfolio_store.py, cibo_compound_generation.py, cibo_compound_floor.py.

Initial tests should prove account isolation, no cross-account fungibility, no floating-PnL funding, no double-spend, settlement-before-compoundability, exact source conservation, attribution != ownership, generation lineage, floor retirement not simultaneously deployable, reserve not simultaneously deployed, restart persistence and idempotent settlement ingestion.

No economic-performance claim belongs in GEN-C1.

## 15. Relationship to current certification

Current V3 certification continues independently: V3 Phase20D → causal tools → Phase21 → Phase22 → final CIBO certification.

The compounding program must not hold the current lineage hostage by retrospectively changing it. Once an exact CIBO control policy is legitimately certified, the new program can test CERTIFIED CIBO versus CERTIFIED CIBO + COMPOUNDING.

## 16. Final audit statement

CIBO is already much more than a position sizer, but it is not yet a sovereign compounding operating system.

The correct next step is not BALANCE UP → SIZE UP. It is to build a new account-conserved, provenance-complete economic layer in which realized value becomes identifiable capital, may become protected, may become compoundable, may compete for deployment, may remain reserve, may be retired into a higher floor and may create later capital generations.

That is the minimum architecture required before QORE can legitimately claim that CIBO has learned not merely how to size capital, but how capital grows.