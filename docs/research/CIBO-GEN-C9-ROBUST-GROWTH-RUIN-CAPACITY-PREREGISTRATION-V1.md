# QORE CORE — GEN-C9 ROBUST GROWTH / RUIN / CAPACITY PREREGISTRATION V1

Status: PREREGISTERED / RESEARCH-ONLY / SHADOW / UNMERGED

Research identity:

CIBO_GENC9_ROBUST_GROWTH_RUIN_CAPACITY_RESEARCH_V1

Primary PR: #651

This program is part of the Sovereign Compounding Program and is governed by
the CIBO Absolute Closure Amendment. It does not modify current CIBO V3, C5,
C6, C7, C8, the protected 2017H1 holdout, QORE Risk, Execution, DEMO-governed,
LIVE, VPS or real capital.

## Research question

How fast can account-local Core capital compound before growth becomes
self-destructive under declared plausible paths, tail stress, provider
constraints and capital-capacity limits?

GEN-C9 does not ask:

MAXIMIZE HISTORICAL RETURN

and does not use the World Cup +491 / +1473 / +1964 / ~+2000 figures as fitting
targets.

## Candidate families

Permitted preregistered research families:

- CURRENT_CONTROL
- FRACTIONAL_GROWTH
- DRAWDOWN_CONSTRAINED_GROWTH
- RISK_SENSITIVE_GROWTH
- DISTRIBUTIONALLY_ROBUST_GROWTH
- CAPACITY_SATURATION

A family name is not authority to implement an arbitrary formula. Each tested
candidate must have a unique candidate_id and immutable
parameterization_sha256 produced before the evaluated outcome/scenario set is
opened for candidate comparison.

No candidate may be created because a prior candidate's evaluation outcomes
suggested a favorable parameter.

## Comparison law

Every candidate in one GEN-C9 report must be evaluated on exactly the same
scenario IDs.

Exactly one candidate is CONTROL.

Candidate outputs are descriptive scientific evidence. GEN-C9 V1 does not
select a production winner, allocate capital or change sizing.

No weighted score may collapse all dimensions into one scalar winner.

## Required path evidence

Each path must declare:

- candidate_id;
- scenario_id;
- scenario_evidence_sha256;
- initial realized capital;
- ending realized capital;
- minimum realized capital;
- maximum drawdown;
- maximum time underwater;
- maximum recovery duration;
- peak plausible loss;
- capacity breach status;
- ruin status under the explicitly declared ruin boundary;
- horizon duration;
- provider-economics evidence SHA where USD claims are made;
- causal/replay evidence SHA;
- no future leakage;
- no market-probability claim.

A scenario path is not a statement about its probability in the real market.

## Required summary metrics

For each candidate report at minimum:

- path count;
- ending-capital multiple distribution;
- minimum ending capital;
- median ending capital;
- p95 maximum drawdown;
- p99 maximum drawdown;
- maximum drawdown;
- maximum time underwater;
- p95 recovery duration;
- empirical scenario ruin count/frequency;
- capacity-breach count/frequency;
- positive-ending-delta count;
- minimum realized capital;
- peak plausible loss;
- return / peak plausible loss where interpretable.

Empirical scenario frequency must always be labelled as simulation/scenario
frequency, never market probability.

## Capacity / saturation research

Capacity probes must preserve the same causal opportunity/scenario surface and
change only the preregistered capital-capacity expression being tested.

GEN-C9 may identify saturation evidence such as:

- additional capacity no longer improves robust ending capital;
- tail drawdown rises faster than robust growth;
- capacity breaches appear;
- margin/provider constraints bind;
- original-capital dependence stops falling;
- capital-time productivity deteriorates.

GEN-C9 V1 reports those frontiers. It does not automatically promote a
capacity level.

## Mandatory model-risk dimensions

Evidence must explicitly represent or declare absence/unavailability for:

- estimation error;
- fat tails;
- serial dependence;
- regime shift;
- execution cost;
- provider limits.

Missing mandatory model-risk evidence blocks scientific closure.

## Reuse of existing engines

GEN-C9 must reuse rather than duplicate:

- CiboRobustCapacityEnvelope;
- Phase20 capital-state Monte Carlo where its evidence domain is valid;
- robust constrained allocator;
- Compound Engine / Compound Portfolio chronology;
- GEN-C8 speed state where preregistered;
- T19/T20 capacity reservation/release evidence;
- provider-normalized economics.

R-denominated historical research remains R-denominated. It cannot be promoted
to provider-valid USD evidence by conversion assumptions.

## Falsification and closure

Valid terminal scientific outcomes include:

- COMPLETED_AND_PROVEN;
- FALSIFIED_AND_CLOSED;
- SUPERSEDED_WITH_PROVEN_LINEAGE;
- EXTERNAL_DEPENDENCY_BLOCKED.

GEN-C9 may be falsified by, among other things:

- growth improvement accompanied by unacceptable ruin/tail deterioration under
  the preregistered gate;
- fragility to scenario ordering;
- capacity saturation before economically useful amplification;
- provider constraints destroying the hypothesized advantage;
- no marginal benefit over control;
- unstable temporal replication.

No hypothesis will be rescued by post-hoc parameter search.

## Certification separation

ENGINE_IMPLEMENTED != VALUE_DEMONSTRATED.

ALL CI GREEN != GEN-C9 CLOSED.

GEN-C9 cannot reach scientific closure without:

- real-data/scenario binding;
- causal replay;
- preregistered economic gate;
- path-dependent Monte Carlo;
- adversarial stress;
- fresh OOS;
- temporal replication.

This preregistration creates no production authority and consumes no protected
final holdout.
