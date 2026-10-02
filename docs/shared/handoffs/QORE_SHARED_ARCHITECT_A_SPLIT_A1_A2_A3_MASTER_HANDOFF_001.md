# QORE CORE — SHARED MASTER HANDOFF

## ARCHITECT A → ARCHITECTS 1, 2, 3 + PAIR-INTEGRATOR TOPOLOGY

**Owner:** Sergio Meza  
**Repository source of truth:** `mezas3238-hue/qore-core`  
**Parent Shared PR:** `#635` — OPEN / DRAFT / UNMERGED  
**Purpose:** divide every remaining Architect-A responsibility into three non-overlapping producer lanes and define the integration contract for Integrator 1 and the A-side contract for Integrator 2.

---

# 0. ABSOLUTE GOVERNANCE

GitHub is the source of truth.

This handoff does **not** authorize:

- merging PR #635 or any producer/integrator PR;
- production, LIVE, real-capital or Funded execution;
- VPS changes;
- broker mutation;
- opening/closing/modifying orders or positions;
- Shared sizing, capital, Risk, order or execution authority;
- opening the protected final Shared certification holdout;
- outcome-aware threshold rescue;
- retuning a falsified mechanism after looking at its failure population;
- silently converting UNKNOWN/INSUFFICIENT evidence into PASS;
- producer-architect modification of the Integrator-owned master zero-open-work ledger.

Shared remains cognition/science/epistemics. Trader methodology remains Trader-owned. Capital/sizing remains CIBO-owned. Hard risk remains QORE Risk-owned. Broker mutation remains Execution-owned.

A failed scientific mechanism must be terminalized honestly as `FALSIFIED_AND_CLOSED` or the closest existing canonical terminal disposition. The mandatory capability remains open and must be attacked with a genuinely new mechanism or new information.

---

# 1. OBSERVED CHECKPOINT — REVALIDATE BEFORE ANY WORK

Observed while freezing this handoff:

- Shared master branch: `agent/qore-core-stack-v2-shared-001`
- Shared master HEAD: `519447cb70e01702b76fc0520efee9a6839ce6d4`
- PR #635: OPEN / DRAFT / UNMERGED / mergeable at observation
- Architect A branch: `agent/shared-a-cognitive-science-001`
- Architect A pre-handoff HEAD: `bca01bedbe03b8a7ba012dba35acfd9c2ba633c8`
- Architect B branch: `agent/shared-b-global-world-perception-001`
- Architect B observed HEAD: `fbf40f35f2c662dbe55930e59ac4dab4937f5b6a`
- existing Shared integration branch observed: `agent/shared-integration-a-mc22-001`
- existing integration HEAD: `2f201447069762436a378db002ce7d598c276172`

These SHAs are checkpoints, **not permanent bases**.

Every Architect and Integrator must, before editing:

1. fetch the current repository state;
2. revalidate the current branch HEADs;
3. identify work already completed since this handoff;
4. skip work already proven by newer canonical evidence;
5. never reset or force-push over concurrent work.

---

# 2. NEW TEAM TOPOLOGY

The old two-producer topology:

`Architect A + Architect B`

is being expanded into six producer architects:

- Architect 1 — from Architect A
- Architect 2 — from Architect A
- Architect 3 — from Architect A
- Architect 4 — from Architect B
- Architect 5 — from Architect B
- Architect 6 — from Architect B

Pair integrators:

- **Integrator 1 = Architect 1 + Architect 2**
- **Integrator 2 = Architect 3 + Architect 4**
- **Integrator 3 = Architect 5 + Architect 6**

This document assigns only the A-side work: Architects 1, 2 and 3, plus Integrator 1 responsibilities and the exact A3→Integrator-2 interface. Architect B must publish the independent B4/B5/B6 handoff.

Recommended producer branch names:

- `agent/shared-a1-causal-trajectory-001`
- `agent/shared-a2-learning-governance-001`
- `agent/shared-a3-cross-system-closure-001`

Recommended pair-integration branch names:

- `agent/shared-integrator-1-a1-a2-001`
- `agent/shared-integrator-2-a3-b4-001`
- `agent/shared-integrator-3-b5-b6-001`

Producer branches should start from the final handoff commit containing this document. Integrator branches must rebase their intake logic on the **current Shared master** at the time integration starts and ingest only producer commits after the shared producer baseline.

---

# 3. DO NOT REDO THESE PROVEN GREEN RESULTS

The following latest relevant A results were GREEN at handoff time. Older RED attempts are superseded unless a newer canonical run explicitly invalidates them.

- MC05 Hierarchical World Foundation — run `36774921202` SUCCESS.
- MC06 Latent State Temporal Stability — run `36774921220` SUCCESS.
- MC20 Operational Stability Binding — run `36775872235` SUCCESS.
- MC21 Real Engine Scientific Society — run `36778113321` SUCCESS.
- MC22 V18 Full Reject Loop — run `36782306980` SUCCESS.
- MC23 Real Novelty Detection — run `36782458472` SUCCESS.
- MC24 Real Regression Suite — run `36781874072` SUCCESS.
- MC25 WP04 V3B Lineage-Integrity Stress — run `36783028642` SUCCESS.
- MC26 Real All-Facet Arbitration — run `36778113179` SUCCESS.
- MC27 Prospective Research Cycle preregistration — run `36782066174` SUCCESS.
- MC28 Mapping Error Diagnostic — run `36784125359` SUCCESS.
- MC28 Model/Runtime Instability Diagnostic — run `36784322253` SUCCESS.
- MC28 Broker↔Provider Mismatch Diagnostic — run `36796674458` SUCCESS.
- WP08 governed epistemic layer — run `36783534368` SUCCESS.
- WP09 Scientific Society / Lab integration — run `36783367625` SUCCESS.
- WP10 Prospective Autonomous Lab infrastructure — run `36783698654` SUCCESS, but WP10 remains scientifically open.
- WP11 Exact Blocker Audit — run `36783872714` SUCCESS, but WP11 remains open.
- WP12 Exact Blocker Audit V2 — run `36784663346` SUCCESS, but its blocker inventory predates the later Broker↔Provider closure and must eventually be refreshed.
- STI3 Real Attention Integration — run `36785002617` SUCCESS.

A successful workflow can prove infrastructure/audit correctness while the capability itself remains OPEN. Never equate workflow GREEN with terminal scientific certification unless the evidence payload explicitly says completed-and-proven.

---

# 4. CURRENT NON-GREEN / NOT-YET-EXECUTED ENGINEERING

These are not scientific falsifications unless an actual scientific evaluation reached that disposition.

## MC28 runtime CLOCK_DRIFT

Recent runs:

- `36805294495` FAILURE
- `36806044876` FAILURE
- `36806291534` FAILURE

All failed during implementation validation before the real DEMO clock experiment completed. The latest observed failure was still in the validation step. Later commits repaired lint/type surfaces, including:

- `1577273e2de1827fdd721f33b592c32ac6b2f005`
- `547005a0ac591e510e1555b3f7e8c88815c32a9c`
- current A head also contains strict-typing hardening.

Therefore:

`CLOCK_DRIFT = ENGINEERING_RED / SCIENTIFIC_OUTCOME_NOT_YET_OBSERVED`

Do not classify it as scientific FAIL.

## MC14 B04 new-information replay

Run `36805916935` failed before any job executed. The workflow syntax was subsequently repaired and strict typing was further hardened, but no later successful governed replay was observed before this handoff.

Therefore:

`MC14_B04 = STAGED / SCIENTIFIC_OUTCOME_NOT_YET_OBSERVED`

## MC25 WP04 V3B performance stress

The preregistration, implementation and workflow have been staged. The workflow is manual `workflow_dispatch` and no successful performance-stress run was observed before this handoff.

Therefore:

`MC25_PERFORMANCE_STRESS = READY_FOR_GOVERNED_EXECUTION_AFTER_REVALIDATION`

Do not spam Actions. One canonical run per frozen experiment is the objective.

---

# 5. ARCHITECT 1 — CAUSAL, TRAJECTORY & POSITION INTELLIGENCE

## Mission

Architect 1 owns remaining A-side causal mechanism science and trajectory/position intelligence.

Architect 1 must **not** touch Architect 2 knowledge-lifecycle files, Architect 3 cross-system closure files, B producer surfaces, or Integrator master ledgers.

## Owned workstreams

### A1-01 — MC14 B04 new-information temporal causal replay

Canonical preregistration:

`docs/shared/evidence/QORE_SHARED_MC14_B04_NEW_INFORMATION_TEMPORAL_CAUSAL_PREREGISTRATION_001.json`

Implementation contract:

`docs/shared/evidence/QORE_SHARED_MC14_B04_REPLAY_IMPLEMENTATION_CONTRACT_001.json`

Current implementation surfaces include:

- `src/qore/infrastructure/core_stack_v2/mc14_b04_cross_asset_causal.py`
- `scripts/shared_mc14_b04_new_information_causal_replay.py`
- `tests/infrastructure/test_core_stack_v2_mc14_b04_cross_asset_causal.py`
- `.github/workflows/qore-shared-a-mc14-b04-new-information.yml`

Required action:

1. revalidate current syntax/types/tests;
2. prove immutable B04 lineage:
   - B04 run `36765098842`
   - B04 SHA `aec788d073aedc31f609c1609af3f7d4d8e5ae30`
   - global artifact `11129732922`;
3. preserve the frozen discovery/validation/replication split;
4. preserve target-blind source-feature construction;
5. execute exactly one governed replay when Actions capacity permits;
6. accept replicated, falsified or insufficient result without gate rescue;
7. never open R6/R5 or protected final Shared holdout for this mechanism.

### A1-02 — STI5 Regime Transition Intelligence

STI5 V1 is not a final capability closure. Its failed mechanism must remain closed.

Required action:

- use genuinely new information/mechanism where scientifically justified, including B04 cross-asset microstructure only if its provenance and temporal semantics fit;
- preregister any new mechanism before outcome evaluation;
- no lowering V1 gates;
- no relabeling consumed evidence as fresh;
- terminalize each failed attempt cleanly.

### A1-03 — STI6 Positive-tail / continuation intelligence

Prior STI6 V1/V2/V3 mechanisms are falsified and must not be resurrected through threshold edits.

Required action:

- formulate a genuinely new mechanism from new information;
- prioritize trajectory acceleration/persistence, failure-hazard veto and new cross-asset microstructure only if not outcome-selected;
- preserve winner/tail-protection semantics;
- no direct exit/stop/target authority;
- no Trader methodology mutation.

### A1-04 — STI8 position intelligence V4

Canonical preregistration:

`docs/shared/evidence/QORE_SHARED_STI8_ECONOMIC_RESPONSE_V4_PREREGISTRATION_001.json`

V4 uses a one-step recovery veto and awaits a future temporally disjoint research OOS population.

Required action:

- keep engineering ready;
- do not manufacture maturity;
- do not reuse burned V2/V3 datasets to demonstrate V4 value;
- do not freeze/open the one-shot V4 value window until the preregistered population rule is satisfied;
- preserve same entry/stop/target/sizing control geometry;
- Shared still has no exit authority.

### A1-05 — MC17 Market Agency Model

Required action:

- replace unsupported actor stories with probabilistic mechanism hypotheses;
- seek new evidence, including B04/world evidence when valid;
- preserve explicit uncertainty;
- never claim unobserved actor identity or intent as fact;
- bind any successful mechanism into Shared cognition only after replication/falsification gates.

### A1-06 — MC18 Counterfactual World Engine

Current foundation is real-data-bound but probability calibration and independent value proof remain open.

Required action:

- build/freeze calibration using consumed development evidence only;
- no future-OOS fitting;
- preserve UNKNOWN_SHOCK coverage;
- prepare the candidate consumed by MC27 prospective OOS;
- no productive authority.

### A1-07 — MC19 Trajectory Intelligence

Required action:

- keep current trajectory foundation intact;
- bind eventual STI8 V4 evidence when mature;
- prove discrimination among normal adversity, recoverable deterioration and structural failure;
- preserve winner retention and no direct trade-control authority.

## Architect 1 completion condition

Architect 1 is done only when every owned item is one of:

- `COMPLETED_AND_PROVEN`;
- `FALSIFIED_AND_CLOSED_FOR_THIS_MECHANISM` with the capability handed forward to a genuinely new preregistered mechanism;
- `EXTERNAL_OR_FUTURE_EVIDENCE_BLOCKED` with exact dependency, evidence needed and no hidden local work remaining.

Architect 1 must produce an evidence manifest for Integrator 1 listing exact commits, runs, artifacts, dispositions and remaining external dependencies.

---

# 6. ARCHITECT 2 — META-LEARNING, CONTINUAL LEARNING & KNOWLEDGE GOVERNANCE

## Mission

Architect 2 owns the full adaptation → regression → stress → governed-knowledge lifecycle.

Architect 2 must not touch Architect 1 causal/trajectory implementation surfaces, Architect 3 cross-system MC27/MC28 surfaces, B producer surfaces or Integrator master ledgers.

## Owned workstreams

### A2-01 — MC11 Neural-Symbolic completion

Required action:

- revalidate the existing neural-symbolic binding;
- close any remaining evidence freshness / independent-validation gap without reusing an overlapping population as fresh;
- preserve symbolic constraints, causal traceability and uncertainty;
- do not treat a representation improvement alone as certified trading value.

### A2-02 — MC23 validated real novel-regime adaptation

Current GREEN run `36782458472` proves real novelty detection, not completed adaptation.

Open requirement:

`MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION`

Required action:

- choose a real NOVEL/NEAR_KNOWN population prospectively;
- generate an adaptation/representation hypothesis without pretending the regime is already known;
- validate on independent evidence;
- reject or promote through governed evidence;
- no silent rewrite of certified knowledge.

### A2-03 — MC24 continual learning closure

Current GREEN run `36781874072` proves regression infrastructure.

Open requirements include:

- bind validated MC23 real-regime adaptation;
- measure empirical knowledge half-life;
- demonstrate regression non-degradation across retained certified knowledge.

No adaptation may erase or silently overwrite prior certified knowledge.

### A2-04 — MC25 same-lineage performance stress

Canonical preregistration:

`docs/shared/evidence/QORE_SHARED_MC25_WP04_V3B_PERFORMANCE_STRESS_PREREGISTRATION_001.json`

Current prior proof:

- lineage-integrity stress run `36783028642` SUCCESS.

Required next sequence:

1. revalidate current staged workflow;
2. execute exactly one governed performance-stress run;
3. preserve the frozen six stress scenarios and unchanged 100-bps incremental-information gate;
4. if PASS, advance the same proposal through formal STRESS;
5. then same-lineage SHADOW;
6. then CERTIFICATION evidence;
7. only then governed PROMOTION;
8. any failure terminalizes that stage/configuration and must not be rescued by post-outcome gate edits.

### A2-05 — WP11 exact closure

Last exact audit identified eight blockers:

- `MC23_VALIDATED_REAL_NOVEL_REGIME_ADAPTATION`
- `MC24_BIND_REAL_MC23_ADAPTATION`
- `MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE`
- `MC25_SAME_LINEAGE_PERFORMANCE_STRESS`
- `MC25_FORMAL_STRESS_STAGE`
- `MC25_SAME_LINEAGE_SHADOW`
- `MC25_CERTIFICATION`
- `MC25_GOVERNED_PROMOTION`

Required action:

- refresh WP11 audit only from sealed evidence;
- reduce blockers monotonically;
- do not edit the Integrator-owned Shared master zero-open-work ledger.

## Architect 2 completion condition

Architect 2 is done when MC11 and the MC23→MC24→MC25→WP11 chain have no local unexecuted step, and every remaining dependency is explicit, externally owned or future-evidence-bound.

Produce one canonical evidence manifest for Integrator 1.

---

# 7. ARCHITECT 3 — CROSS-SYSTEM CLOSURE, GLOBAL COVERAGE & META-COGNITION

## Mission

Architect 3 owns A work whose completion materially depends on Architect-B world/perception evidence or cross-system operational evidence.

**Architect 3 does not integrate Architect 4.** Architect 3 produces a clean A-side package. **Integrator 2** is the only pair integrator for Architect 3 + Architect 4.

## Owned workstreams

### A3-01 — STI3 global attention/opportunity-board closure

Current run `36785002617` is GREEN and proves:

- real board replay;
- source stress;
- scarcity exercised;
- deterministic scarce epochs;
- dropped signals remain observable;
- no downstream authority.

Still open:

- global multi-family coverage;
- 7-Trader coverage.

Architect 3 must consume Architect-4/B global evidence through explicit contracts, never duplicate B acquisition.

### A3-02 — STI10 global 7/7 projection

VT31 projection evidence is not equivalent to global 7/7 multi-family completion.

Required action:

- bind all current Trader families only when B supplies canonical world/perception identities;
- preserve each Trader's methodology sovereignty;
- no hidden Trader logic inside Shared.

### A3-03 — MC05 Hierarchical World / Temporal Brain completion

Run `36774921202` is GREEN for the foundation.

Remaining capability gaps include missing/broader clocks where evidence exists, including microstructure/seconds and higher/macro scales not yet globally bound.

Architect 3 coordinates the A-side hierarchy contracts; Architect 4 supplies B-side observable world coverage. Integrator 2 reconciles them.

### A3-04 — MC12 QORE Market Foundation Model completion

Existing work is partial and cannot be called global foundation-model completion from one equity-index family.

Required action:

- bind multiple legitimate market families/modalities from B evidence;
- preserve source provenance and point-in-time semantics;
- no protected holdout access;
- no representation auto-promotion.

### A3-05 — MC27 Meta-Cognitive Scientific Intelligence

Canonical prospective preregistration:

`docs/shared/evidence/QORE_SHARED_MC27_PROSPECTIVE_META_COGNITIVE_RESEARCH_CYCLE_001.json`

Future research OOS is frozen:

- start: `2026-10-01T00:00:00Z`
- end: `2026-11-01T00:00:00Z`
- minimum trading days: 20
- minimum scored observations: 500
- not the protected final certification holdout.

At this handoff date the full future window is not mature. Architect 3 may prepare collection/validation infrastructure but must not fabricate completion.

Open requirements:

- future OOS improvement demonstrated;
- MC27 completed-and-proven.

### A3-06 — MC28 remaining Standard 006 diagnostics

Already proven:

- mapping errors — run `36784125359`;
- model/runtime instability — run `36784322253`;
- broker/provider mismatch — run `36796674458`.

Remaining:

#### CLOCK_DRIFT

Canonical preregistration:

`docs/shared/evidence/QORE_SHARED_MC28_RUNTIME_CLOCK_DRIFT_PREREGISTRATION_001.json`

The experiment is read-only cTrader DEMO spot-timestamp observation. Recent failures are engineering validation failures, not scientific outcomes.

Required action:

- repair current validation/lint/type issues;
- preserve the frozen limits;
- execute one real read-only governed run;
- retain injected drift falsification tests;
- no order submission and no broker mutation.

#### EXECUTION_QUALITY_DETERIORATION

Canonical preregistration:

`docs/shared/evidence/QORE_SHARED_MC28_EXECUTION_QUALITY_DETERIORATION_PREREGISTRATION_001.json`

Required dimensions:

- median executable spread;
- P90 adverse slippage;
- provider rejection rate.

Closure requires an existing **real sealed DEMO execution population** with sufficient attempts/fills. Synthetic evidence cannot close it.

Rules:

- do not create new orders merely to populate this diagnostic;
- first recensus current GitHub evidence because CIBO/provider work may have advanced after this preregistration;
- if sufficient sealed evidence exists, bind it read-only;
- otherwise remain `INSUFFICIENT` with exact dependency.

### A3-07 — WP10 / WP12 closure

WP10 infrastructure is GREEN but waits on prospective OOS/scientific maturation.

WP12 last audit is stale relative to the later Broker↔Provider closure. After CLOCK_DRIFT and/or EXECUTION_QUALITY evidence changes:

- refresh the A-side exact blocker audit;
- remove only blockers proven closed by sealed artifacts;
- keep MC27 future-OOS blockers until actually mature;
- do not mutate the Integrator master zero-open-work ledger.

## Architect 3 completion condition

Architect 3 is done when all A-side global/cross-system code is complete and every unresolved item is either:

- waiting on Architect 4/B evidence;
- waiting on genuinely future evidence;
- waiting on an already-preregistered external real DEMO population.

Architect 3 then emits a strict A3 integration manifest to Integrator 2.

---

# 8. INTEGRATOR 1 — ARCHITECT 1 + ARCHITECT 2

## Mission

Integrator 1 is not a passive cherry-picker.

Integrator 1 must:

`INTEGRATE → RECONCILE → REPAIR → VALIDATE → ADVANCE`

for Architect 1 and Architect 2.

## Responsibilities

1. Revalidate Shared master and A1/A2 heads before each intake.
2. Ingest only producer commits after the common producer baseline.
3. Detect duplicate implementations, stale evidence refs, interface divergence and contradictory dispositions.
4. Repair:
   - import/API mismatches;
   - workflow syntax;
   - lint/mypy/test regressions;
   - stale artifact/run references;
   - duplicated science surfaces;
   - governance violations;
   - outcome-aware accidental coupling.
5. Re-run only the minimum canonical CI needed after repair; do not flood Actions.
6. Preserve falsified mechanisms as historical evidence; do not delete inconvenient failures.
7. Advance remaining A1/A2 work when integration exposes a small missing cross-lane step. Integrator 1 is authorized to finish integration glue and scientific wiring, but must not silently redefine either architect's frozen hypothesis.
8. Maintain one pair-level intake/reconciliation manifest.
9. Deliver a GREEN or explicitly scientifically terminal A1+A2 package to the Shared integration chain.
10. Never merge PR #635 or any base/production branch without Owner authorization.

## Integrator 1 ownership boundary

Integrator 1 owns **compatibility and combined correctness**, not Architect 3/B global acquisition.

If A1/A2 require B evidence, Integrator 1 records the dependency and hands it to Integrator 2 only when it belongs to A3+B4 cross-system closure.

Integrator 1 must not compete with Integrator 2 for A3/B4 files.

---

# 9. INTEGRATOR 2 — A-SIDE CONTRACT FOR ARCHITECT 3 + ARCHITECT 4

Integrator 2 will combine:

- Architect 3 — this document's cross-system A lane;
- Architect 4 — to be defined by Architect B's own B4/B5/B6 handoff.

Integrator 2 must:

`INTEGRATE → RECONCILE → REPAIR → VALIDATE → ADVANCE`

The principal expected intersections are:

- canonical identity;
- world/perception coverage;
- temporal semantics;
- sensor/data provenance;
- global multi-family coverage;
- 7-Trader Shared projections;
- MC05 multi-clock evidence;
- MC12 multi-modal foundation-model evidence;
- MC28 Core/Broker/provider/execution observational evidence.

Architect 3 must never directly rewrite Architect 4's acquisition/perception implementation to make A tests pass. Integrator 2 owns that compatibility boundary.

If B4 evidence is insufficient, the correct output is an explicit external dependency, not fabricated completion.

---

# 10. INTEGRATOR 3 — TOPOLOGY ONLY

Integrator 3 is reserved for:

- Architect 5
- Architect 6

No A1/A2/A3 producer should send work directly to Integrator 3 unless a later Owner directive changes topology.

B owns the future definition of Architect 5 and Architect 6.

---

# 11. SHARED FILE-OWNERSHIP FIREWALL

Producer Architects 1/2/3 must not edit the Integrator-owned master zero-open-work surfaces:

- `src/qore/infrastructure/core_stack_v2/shared_zero_open_work.py`
- `tests/infrastructure/test_core_stack_v2_shared_zero_open_work.py`
- `scripts/shared_master_open_work_ledger_v1.py`
- `.github/workflows/qore-shared-maximum-zero-open-work.yml`

They must also avoid rewriting master Owner directives, the Shared maximum ceiling, or PR #635 body as a substitute for evidence.

Pair integrators may reconcile master-owned files only if that responsibility is explicitly assigned in the active integration lane. Otherwise they emit evidence to the sovereign master integration step.

---

# 12. ANTI-CONFLICT RULES

1. **One workstream, one producer owner.**
2. No architect modifies another architect's scientific implementation without handing the issue to the pair integrator.
3. Shared interfaces may be consumed read-only across lanes.
4. Cross-lane contract changes go through the appropriate pair integrator.
5. No duplicated workflows for the same experiment.
6. No rerunning obsolete failed SHAs when a repaired successor exists.
7. No deleting or hiding old RED evidence.
8. No post-outcome gate edits.
9. No “density for density”; scientific value and robustness are primary.
10. No final holdout before pre-certification readiness and Owner authorization.

---

# 13. CI / ACTIONS POLICY

GitHub Actions has recently suffered severe queue saturation.

Every producer and integrator must:

- inspect queued/in-progress runs before dispatch;
- avoid push-trigger storms;
- prefer `workflow_dispatch` for expensive one-shot scientific experiments;
- use path filters for validation workflows;
- never create multiple duplicate runs because a runner is delayed;
- never cancel other project lanes without explicit authority;
- distinguish technical RED from scientific FALSIFIED.

A technical lint/type/workflow failure never authorizes scientific conclusions.

---

# 14. INTEGRATION MANIFEST REQUIRED FROM EVERY PRODUCER

Every Architect 1/2/3 handoff to its Integrator must include:

- producer branch;
- exact head SHA;
- common baseline SHA;
- commits to intake;
- files owned/changed;
- canonical workflow runs;
- artifact IDs;
- scientific disposition per workstream;
- GREEN technical gates;
- known RED technical gates;
- falsified mechanisms;
- exact external/future blockers;
- proof protected final holdout remained closed;
- proof no LIVE/production/real-capital/broker mutation authority was introduced;
- explicit list of master-ledger files not touched.

No prose-only “finished” claim is sufficient.

---

# 15. PAIR-INTEGRATOR ACCEPTANCE GATE

A pair package is eligible for handoff only when:

- all producer commits are reconciled;
- no duplicate scientific mechanisms remain active accidentally;
- imports/types/tests pass for the integrated surface;
- evidence refs resolve to exact sealed runs/artifacts;
- stale blockers are reconciled;
- every failure has a terminal or technical disposition;
- all authority booleans remain false where Shared sovereignty requires false;
- protected final certification holdout remains unopened;
- no pair-owned mandatory work remains silently OPEN.

“GREEN CI” alone is not enough. Scientific status and governance status must also be explicit.

---

# 16. PRIORITY ORDER

## Architect 1

1. MC14 B04 staged replay → obtain real scientific disposition.
2. STI5 new-information mechanism.
3. STI6 new mechanism.
4. MC18 calibration candidate.
5. MC17 mechanism evidence.
6. STI8 V4 readiness / future OOS maturation.
7. MC19 trajectory closure.

## Architect 2

1. MC25 staged same-lineage performance stress.
2. MC23 real novel-regime validated adaptation.
3. MC24 adaptation binding + empirical half-life.
4. MC11 remaining neural-symbolic evidence gap.
5. WP11 exact blocker reconciliation.
6. Continue MC25 formal STRESS → SHADOW → CERTIFICATION → governed PROMOTION if evidence permits.

## Architect 3

1. Repair and execute MC28 CLOCK_DRIFT.
2. Recensus/bind real sealed execution-quality evidence or remain INSUFFICIENT.
3. Refresh MC28/WP12 A-side blocker truth.
4. STI3 global multi-family / 7-Trader closure with B4.
5. STI10 global 7/7 projection with B4.
6. MC05 missing clock-scale binding with B4.
7. MC12 multi-family/modality binding with B4.
8. Prepare, then only when mature evaluate MC27 prospective future OOS.
9. Close WP10/WP12 only from real evidence.

---

# 17. CURRENT A-SIDE TERMINAL TARGET

Architect A is fully decomposed when the three new lanes plus pair integrators can drive all A-owned requirements to one of:

- completed-and-proven;
- scientifically falsified at the mechanism level with successor research explicitly owned;
- exact external dependency on B/provider/future evidence;
- future-evidence waiting state with no local engineering debt.

The final Shared target remains:

`ZERO MANDATORY OPEN WORK → PRE_CERTIFICATION_READY → Owner-authorized final certification path`

This handoff does **not** declare Shared pre-certification ready.

---

# 18. FIRST ACTION FOR EACH NEW CHAT / AGENT

Before doing any work, the new Architect/Integrator must read this file directly from GitHub and then revalidate current branch heads and latest workflow outcomes.

Do not ask the Owner to restate this distribution unless GitHub evidence is contradictory.

Proceed continuously within the assigned lane, commit durable progress to GitHub, and hand off exact evidence to the assigned pair integrator.
