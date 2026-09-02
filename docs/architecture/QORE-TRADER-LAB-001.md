# QORE-TRADER-LAB-001 — Trader Lab Qualification Foundation

## Status

**FIRST-CLASS GOVERNED COMPONENT — NOT A CERTIFICATION SCRIPT — NOT EXECUTION AUTHORITY**

The Trader Lab is a governed qualification component that must exist before any Trader
(VT-01..VT-31) can be admitted to DEMO. It binds an exact Trader candidate, enforces the
mandatory qualification lifecycle, qualifies Fast-Forward without a parallel replay engine,
orchestrates Stress/Monte-Carlo robustness through the existing deterministic research
resampling machinery, and gates `DEMO_ELIGIBLE` on Risk + CIBO + independent validation plus
economic evidence.

It does not implement any concrete Trader methodology, does not authorize DEMO or Production
by itself, and grants no execution authority.

## Permanent laws

```text
CODE_GREEN                != DEMO_ELIGIBLE
BACKTEST_PROFITABLE       != DEMO_ELIGIBLE
MONTE_CARLO_PASS          != PROFITABILITY_PROOF
CIBO_REVIEW               != PROMOTION_AUTHORITY
TRADER_LAB                != EXECUTION_AUTHORITY
TRADER_LAB                != RISK_BYPASS
DEMO_ELIGIBLE             != PROFITABLE
```

Hard admission law:

```text
NO VALID TRADER LAB PROMOTION EVIDENCE
  -> NO DEMO_ELIGIBLE
  -> NO DEMO ADMISSION
```

Every VT-01..VT-31 traverses the Lab individually. No cohort-level shortcut, no inherited
qualification, no CIBO override, no Risk bypass.

## Canonical path

```text
31 TRADERS || CIBO || TRADER LAB -> EXACT VERSION QUALIFICATION -> DEMO A/B
```

## Concurrency / non-overlap law

CIBO Batch 004 concurrently edits broad `src/qore/infrastructure` surfaces. This package is
isolated to:

- `src/qore/infrastructure/trader_lab/`
- `tests/infrastructure/trader_lab/`
- `docs/architecture/QORE-TRADER-LAB-001.md`

Existing Research/OOS/Replay/Bootstrap/Risk/CIBO files are reused by imports, protocols,
composition, or exact evidence references — never mutated. Required shared-file changes are
documented as REMAINS.

## Candidate binding

`TraderLabCandidateBinding` binds one exact candidate to the existing frozen research
strategy/run/config identity via `ResearchRunStrategyBinding` (which already proves exact
frozen strategy content bound to one research run). It adds:

- `TraderLabCandidateId` — opaque identity (one per VT-xx).
- `TraderLabCandidateVersion` — re-qualification generation.
- `TraderLabCandidateFingerprint` — SHA-256 over identity + version + `binding_fingerprint` +
  `content_digest`.

Changing identity, version, or configuration changes the fingerprint by construction, which
invalidates any previously derived eligibility chain. A suspended/degraded/rejected candidate
can only resume through a new version (a new binding and fingerprint), never by mutating the
old chain.

## Lifecycle state model

States (exact, no inferred promotion from names):

```text
DRAFT
RESEARCH_READY
REPLAY_QUALIFIED
FAST_FORWARD_QUALIFIED
OOS_QUALIFIED
STRESS_QUALIFIED
MONTE_CARLO_QUALIFIED
RISK_REVIEWED
CIBO_REVIEWED
DEMO_ELIGIBLE
REJECTED
DEGRADED
SUSPENDED
```

Mandatory stage chain (no stage may be skipped):

```text
RESEARCH -> REPLAY -> FAST_FORWARD -> OOS -> STRESS -> MONTE_CARLO
  -> RISK_REVIEW -> CIBO_REVIEW -> INDEPENDENT_VALIDATION
```

Transition table:

```text
DRAFT               --(RESEARCH)-->              RESEARCH_READY
RESEARCH_READY      --(REPLAY)-->                REPLAY_QUALIFIED
REPLAY_QUALIFIED    --(FAST_FORWARD)-->          FAST_FORWARD_QUALIFIED
FAST_FORWARD_QUALIFIED --(OOS)-->                OOS_QUALIFIED
OOS_QUALIFIED       --(STRESS)-->                STRESS_QUALIFIED
STRESS_QUALIFIED    --(MONTE_CARLO)-->           MONTE_CARLO_QUALIFIED
MONTE_CARLO_QUALIFIED --(RISK_REVIEW)-->         RISK_REVIEWED
RISK_REVIEWED       --(CIBO_REVIEW)-->           CIBO_REVIEWED
CIBO_REVIEWED       --(INDEPENDENT_VALIDATION)--> DEMO_ELIGIBLE
* (non-terminal)    --(reject/degrade/suspend)--> REJECTED | DEGRADED | SUSPENDED
```

Transitions are pure, deterministic, evidence-backed, and fail closed. Each qualification is
an immutable `TraderLabStageQualification` (stage + evidence + prior/next state). The
lifecycle re-derives its state from the chain on every construction, so reflective corruption
or a mutated chain fails closed.

## Immutable stage evidence

`TraderLabStageEvidenceRecord` binds exactly one stage and one candidate binding, with:

- explicit `produced_at` (timezone-aware, never a hidden clock);
- a `source_reference` (`TraderLabEvidenceReference` = kind + reference_id + content digest +
  schema version);
- optional `supplementary` references;
- a SHA-256 fingerprint over stage + candidate + references + time.

Reference helpers digest the exact existing evidence (frozen-OOS fingerprint, sampling-frame,
block-bootstrap distribution, resampling envelope, replay chronology) without fabricating
their conclusions. Risk/CIBO/economic/independent-validation attach through opaque typed
seams — the Lab invents none of their implementations. Duplicate, stale, mismatched, or
post-hoc mutated evidence is rejected.

## Fast-Forward qualification

`qualify_trader_lab_fast_forward` is a seam over the existing replay chronology, not a second
replay engine. It proves:

- acceleration changes wall-clock execution speed only (`base_wall == accelerated_wall *
  factor`, factor >= 2, all advances explicit);
- simulated chronology and ordering remain exact (schedule visits every availability instant
  exactly once, in order);
- `available_at`/visibility semantics are preserved;
- no future event becomes visible before its availability instant;
- identical candidate + evidence + schedule reproduce identical qualification evidence.

If the existing replay evidence cannot certify a property, it fails closed.

## Stress + Monte Carlo orchestration

`TraderLabExperimentRegistration` freezes algorithm/family/version/seed/simulation-count/
min-sample-size/thresholds BEFORE outcome inspection. Post-hoc seed substitution, threshold
replacement, or simulation-count mutation changes the registration fingerprint and therefore
the experiment identity, so a prior qualification cannot be reused.

`TraderLabMonteCarloExperimentEvidence` composes `ResearchBlockBootstrapPolicy`,
`ResearchBlockBootstrapDistribution`, and `ResearchResamplingEnvelope` (existing deterministic
machinery — no new RNG). Its status is derived fail-closed: insufficient sample or unsupported
dependence can never yield `QUALIFIED`. Monte Carlo is a descriptive resampling envelope, not
a calibrated probability or edge claim.

Parameter-neighborhood evidence is a separate candidate-neighbor binding and can never promote
the original candidate (candidate fingerprint mismatch). Cost/spread/slippage perturbation is
declared specification data (`TraderLabCostPerturbationSpec`), not hidden assumptions.

## Promotion gate

`evaluate_demo_eligibility` requires a fully re-validated lifecycle in `DEMO_ELIGIBLE` (i.e. the
complete chain ending in independent validation) plus, when mandated, explicit economic
evaluation evidence. CIBO may recommend but cannot self-promote; Risk review cannot be skipped;
independent validation is a distinct final gate.

## Reuse map (imports, not reimplementation)

| Concern | Reused surface |
| --- | --- |
| Candidate config identity | `ResearchRunStrategyBinding`, `ResearchStrategyConfigurationManifest` |
| Run/input identity | `ResearchRunEvidence`, `ResearchStrategyConfigurationId` |
| OOS evidence | `ResearchFrozenOosEvidence`, `ResearchOosPerformanceEvidence` |
| Sampling | `ResearchSamplingFrame`, `ResearchSerialDependenceDiagnostic` |
| Resampling | `ResearchBlockBootstrapPolicy`/`Distribution`, `ResearchResamplingEnvelope` |
| Replay chronology | `RetainedMarketEventObservation`, `order_market_event_observations`, `visible_market_event_observations`, `derive_market_event_availability_instants` |
| Kernel idioms | `Result`/`Success`/`Failure`, timezone-aware datetime, frozen+slots dataclasses, canonical SHA-256 fingerprints |

Risk and CIBO are read-only architectural context; they are attached only through typed opaque
reference seams, never imported as promotion authority.

## REMAINS (integration seams after concurrent CIBO build)

- Risk review and CIBO review evidence production remains owned by their existing systems; the
  Lab only carries typed content-bound references.
- Actual cost-perturbation and start/sub-window perturbed economic evidence must come from the
  existing economic evaluation machinery; the Lab declares the spec and references the result.
- The exact wording of issue #473's economic-evaluation mandate is represented as an optional
  but enabled-by-default promotion-gate requirement (`require_economic_evidence=True`) without
  fabricating metrics.
