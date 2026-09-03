# QORE CIBO Cognitive Superarchitecture — Batch 008 (Complementary Cognitive Substrate)

Status: candidate (pending external FULL QG)
Package: `HARNESS-ENGINEER-QORE-CIBO-COGNITIVE-SUPERARCHITECTURE-001-BATCH-008`
Binding: `START=576803fbda76970a4bbfe2287b5f9ca101d0f6c3 TREE=11f35844670551ac4ab5be322272a3221e6b1c4b`

## Purpose

This package answers one bounded question:

> HOW CIBO THINKS, ORGANIZES COGNITION, PLANS, LEARNS, USES TOOLS, REPLAYS AND
> EVALUATES ITS COGNITION

It is a **complementary artifact** on the same immutable START as Batch 006. It
does **not** reconstruct Batch 006 cognitive contracts, epistemic state,
reasoning-mode enum, governed memory, journals, Council of Minds, adversarial
critic, or Executive Brain. It defines complementary provider-neutral contracts
with explicit future integration seams and **no duplicate semantic ownership**.

It does **not** implement CIBO Functions (#483), Trader Lab (#473/#481),
provider execution, Risk authority, Production authority, or real-capital
authority.

## Hard architecture laws honoured

1. `CIBO COGNITIVE SUPERARCHITECTURE = HOW CIBO THINKS`.
2. `CIBO FUNCTIONS = WHAT CIBO DOES` (out of scope).
3. `INTELLIGENCE != AUTHORITY`.
4. `REASONING != EXECUTION`.
5. `OPINION != FORMAL SIGNAL`.
6. `MODEL PROVIDER != CIBO SEMANTICS`.
7. `SUMMARY != SOURCE EVIDENCE`.
8. `COUNCIL != FAKE CONSENSUS`.
9. `UNCERTAINTY != FAILURE`.
10. `CIBO MEMORY != TRANSIENT LLM CONTEXT`.
11. `CIBO MEMORY != SILENT SELF-REWRITE`.
12. No concrete LLM/provider/model imports in semantic Core contracts.
13. No provider order, account, credential, execution, promotion, Risk approval
    or Production authority can emerge from cognitive output.
14. No hidden `datetime.now()`, `date.today()`, `uuid4()`, RNG, retry, sleep,
    scheduler, thread or network semantic side effect.
15. Exact runtime types; `bool != int`; no subclass laundering.
16. Frozen slots dataclasses where applicable.
17. All externally supplied nested material recursively revalidated.
18. Timestamps timezone-aware and explicit.
19. Deterministic canonical ordering and fingerprints.
20. Secret-bearing strings/metadata/evidence fail closed.
21. No global mutable registry/state.
22. No hindsight rewriting of beliefs, goals, lessons or counterfactuals.

### Exact-runtime-type boundary policy (Correction-001)

Concrete identity/value/authority-bearing semantics are validated with **exact**
runtime types: `UUID`, `CiboCognitiveFingerprint`, every frozen dataclass value
object, every `StrEnum` status/kind/domain value, `tuple` field collections,
timezone-aware `datetime`, `timedelta`, and exact `str`/`int`/`bool`. Subclasses
of any of these are rejected both at construction and at factory/builder entry
points (constructor/builder parity), so a subclass that overrides
`revalidate()` to bypass its own validation cannot be laundered into a trusted
canonical value. Intentional structural polymorphism is preserved only where the
contract is structural: `Sequence` inputs at factory boundaries and the
`logical_values()` duck-typed fingerprint-material seam.

## Component map (six lanes)

All files live under `src/qore/infrastructure/` with the `cibo_cognitive_`
prefix and share `cibo_cognitive_common.py` primitives.

### Lane 1 — `cibo_cognitive_world_model.py` (CA-04)
Typed financial/Core cognitive world-model substrate. Immutable, fingerprinted
`WorldModelSnapshot` over canonically ordered `WorldModelReference` values and
explicit `WorldModelContradiction` values. Enforces:
- caller-supplied, timezone-aware `as_of`;
- no fabricated future state (`reference.as_of` must not postdate snapshot);
- stale source cannot masquerade as current (per `staleness_threshold`);
- contradictory sources cannot collapse into one asserted truth
  (`resolved_reference` refuses with `Failure` on >1 non-missing reference or
  any open contradiction);
- secret-bearing evidence labels fail closed;
- recursive revalidation of nested material (rebuild on entry).

### Lane 2 — `cibo_cognitive_attention.py` (CA-05/06/09)
Deterministic, evidence-bound context selection. `AttentionSignal` must cite at
least one `AttentionEvidenceRef` (no invented evidence); bounded integer
severity/score; permutation-invariant ranking. Complementary reasoning routing
(`ReasoningRequest` -> `ReasoningRoutingOutcome`) abstains when evidence is
missing; `ReasoningDepthHint` is an allowlisted string token (`fast`, `high`,
`max`, `council_adversarial`) that binds to Batch 006 modes at the gate without
redefining the enum. `CalibrationNote` carries a bounded confidence band and an
explicit abstention flag without redefining uncertainty enums.

### Lane 3 — `cibo_cognitive_planning.py` (CA-10/11)
Replayable, revisioned goal graph: `CognitiveGoal -> CognitiveTask ->
dependencies -> required evidence -> status -> replan`. DAG cycle rejection,
deterministic topological order, evidence-gated `complete_task`, append-only
`PlanHistory`, and governed `PlanRequest` emission (research/work only — never
execution). `CognitiveLearningRecord` separates contemporaneous evidence from
later evidence, treats error attribution as hypothesis unless `proven`, keeps
counterfactuals distinct from the actual outcome, and carries a `supersedes`
lesson lineage. No hindsight rewriting, no silent self-modification.

### Lane 4 — `cibo_cognitive_tools.py` (CA-12/13/18)
Provider-neutral tool orchestration: `ToolRequest`/`ToolResult` with exact input
and output fingerprints, `bind_tool_result` exactness, a
`ToolResultStatus` boundary (`SUCCESS`/`FAILURE`/`INSUFFICIENT_EVIDENCE`), and a
retry-to-pass invariant (success requires `attempt == 1`). Specialist faculty
bus: `FacultyContribution` (observation/opinion/evidence only — no authority),
deterministic `order_contributions` (disagreement preserved), and an immutable,
versioned `FacultyRegistry` with duplicate identity/version rejection — no
global mutable plugin registry.

### Lane 5 — `cibo_cognitive_replay.py` (CA-16/14/15)
Deterministic replay/audit. `ReplayEpisode` records exact inputs (world snapshot
id, attention reasons, goal/plan state, tool call fingerprints, counterfactuals,
uncertainties, contradictions, evidence refs, changes-after, handoff reference)
and fingerprints them; `replay_episode` reconstructs without reading the clock
or network. Authority-free `CognitiveHandoff` envelope (recommendation/formal
request by reference, no credential/order/account/promotion/Risk authority), and
a `CognitiveUtterance` dialogue/opinion seam that never becomes a formal signal
implicitly.

### Lane 6 — `cibo_cognitive_evaluation.py` (CA-17)
Authority-free cognitive evaluation framework over ten dimensions, producing
`SUFFICIENT_FOR_EVALUATION`, `INSUFFICIENT_EVIDENCE`,
`CONTRADICTORY_EVIDENCE`, or `EVALUATION_NOT_APPLICABLE`. Evaluation is a
cognitive assessment only; it cannot confer execution/Risk/Production/promotion
authority.

## Integration seams with Batch 006 (Cognitive Integration Gate)

This package does not import or reference Batch 006 symbols (they are absent in
this checkout by design). Integration occurs later at a dedicated gate via
reference/fingerprint seams only. The exact remaining seams required to combine
certified Batch 006 with this completed Batch 008 are enumerated below; each is
a one-way reference/fingerprint/identity binding, and **none** transfers
authority, execution, or duplicate semantic ownership:

1. **Reasoning-mode enum (CA-06).** `ReasoningDepthHint.value`
   (`fast`/`high`/`max`/`council_adversarial`) maps one-to-one onto the Batch 006
   reasoning-mode enum. Batch 006 owns the enum and its admissible-modes policy;
   Batch 008 owns only the complementary allowlisted hint token.
2. **Evidence/provenance fabric (CA-02).** `WorldModelReference.evidence_fingerprint`
   and `ReplayToolCall.input_fingerprint`/`result_fingerprint` bind to Batch 006
   evidence-reference primitives by `sha256` fingerprint, never by type.
3. **Memory / world-model records (CA-03/CA-04).** `ReplayEpisode.world_snapshot_id`
   and `ReplayEpisode.evidence_refs` bind to Batch 006 memory and world-model
   records by identity (UUID/string reference).
4. **Council of Minds / specialist bus (CA-07).** `FacultyContribution` and
   `FacultyRegistry` bind to Batch 006 Council deliberation types without
   re-declaring deliberation, quorum, or consensus semantics.
5. **Uncertainty / calibration (CA-09).** `CalibrationNote.confidence_band` and
   `CalibrationNote.abstention_required` bind to Batch 006 uncertainty primitives
   without re-declaring the uncertainty enum.
6. **Dialogue / voice boundary (CA-14).** `CognitiveUtterance` binds to Batch 006
   dialogue boundaries as an opinion/dialogue-only seam; it never becomes a
   formal signal.
7. **Authority / action firewall (CA-15).** `CognitiveHandoff` binds to Batch 006
   formal recommendation/request types by `source_reference`; it carries no
   order/account/credential/promotion/Risk authority and cannot authorize action.
8. **Evaluation self-certification guard (CA-17).** `CognitiveEvaluation` binds
   to Batch 006 critic/adversarial evaluation only as an authority-free
   assessment; `SUFFICIENT_FOR_EVALUATION` never implies execution or promotion
   authority.

Integration is therefore reference/fingerprint/identity composition at the gate;
no Batch 008 module imports, subclasses, or duplicates a Batch 006 semantic type.

## Adversarial matrix coverage

| # | Invariant | Coverage |
|---|---|---|
| 1 | naive timestamp rejected | `test_naive_timestamp_rejected` |
| 2 | secret-bearing evidence rejected | `test_secret_bearing_evidence_rejected` |
| 3 | contradictory sources cannot collapse | `test_contradictory_sources_cannot_collapse` |
| 4 | stale source cannot masquerade as current | `test_stale_source_cannot_masquerade_as_current` |
| 5 | attention cannot invent evidence | `test_attention_priority_cannot_invent_evidence` |
| 6 | equal-priority ordering permutation-invariant | `test_equal_priority_ordering_is_permutation_invariant` |
| 7 | nested reflective corruption revalidated | `test_reflective_corruption_fails_recursive_revalidation`, `test_nested_reflective_corruption_fails` |
| 8 | bool cannot launder as int | `test_bool_is_not_int_for_fingerprint_canonical_material`, `test_exact_int_rejects_bool`, `test_severity_rejects_bool_laundering`, `test_calibration_rejects_bool_confidence_band`, `test_plan_revision_rejects_bool_laundering`, `test_tool_result_attempt_rejects_bool`, `test_dimension_score_rejects_bool` |
| 9 | str subclass laundering rejected | `test_exact_str_rejects_subclass`, `test_subclass_laundering_rejected` |
| 10 | goal graph cycle rejected | `test_goal_graph_cycle_rejected` |
| 11 | completion without evidence rejected | `test_task_completion_without_evidence_rejected` |
| 12 | replan cannot erase history | `test_replan_cannot_erase_old_history` |
| 13 | later evidence cannot rewrite contemporaneous | `test_later_evidence_cannot_rewrite_contemporaneous` |
| 14 | counterfactual cannot be asserted actual | `test_counterfactual_cannot_be_asserted_as_actual_outcome` |
| 15 | tool result binds exact fingerprint | `test_tool_result_must_bind_exact_request_and_input_fingerprint` |
| 16 | mismatched tool version rejected | `test_mismatched_tool_version_rejected` |
| 17 | retry-to-pass not success | `test_retry_to_pass_not_representable_as_success` |
| 18 | faculty contribution cannot carry authority | `test_faculty_contribution_cannot_carry_authority` |
| 19 | duplicate faculty identity/version rejected | `test_duplicate_faculty_identity_version_conflict_rejected` |
| 20 | faculty ordering deterministic | `test_faculty_ordering_is_deterministic` |
| 21 | replay with changed input rejected | `test_replay_with_changed_input_rejected` |
| 22 | replay cannot read clock/network | `test_no_clock_or_network_side_effects_in_semantic_contracts` |
| 23 | audit cannot omit source evidence | `test_audit_record_cannot_omit_source_evidence` |
| 24 | missing evidence => INSUFFICIENT_EVIDENCE | `test_missing_evidence_yields_insufficient_evidence` |
| 25 | contradictory evidence => CONTRADICTORY_EVIDENCE | `test_contradictory_evidence_yields_contradictory_evidence` |
| 26 | evaluation cannot confer authority | `test_evaluation_cannot_confer_authority` |
| 27 | handoff cannot contain order/account/credential | `test_handoff_is_authority_free` |
| 28 | dialogue/opinion cannot become formal signal | `test_dialogue_opinion_cannot_become_formal_signal_implicitly` |
| 29 | no global mutable registry | `test_no_global_mutable_registry` |
| 30 | no provider/model import | `test_no_provider_or_model_imports_in_semantic_contracts` |
| 31 | factory trust-boundary parity (no AttributeError/TypeError leak) | `test_evaluate_rejects_non_str_reference_without_leaking_exception`, `test_evaluate_rejects_non_score_dimensions_without_leaking_exception`, `test_build_plan_rejects_non_sequence_tasks_without_leaking_exception`, `test_build_plan_rejects_non_sequence_goals_without_leaking_exception`, `test_build_plan_rejects_non_task_items_without_leaking_exception`, `test_build_replay_rejects_non_sequence_tool_calls_without_leaking_exception`, `test_build_replay_rejects_non_call_items_without_leaking_exception`, `test_build_replay_rejects_non_datetime_recorded_at_without_leaking_exception` |
| 32 | routing reason/requested-evidence secret hygiene | `test_routing_reason_rejects_secret_bearing_material` |
| 33 | fingerprint (frozen value object) subclass laundering rejected at attention/replay/tool/world-model boundaries | `test_fingerprint_subclass_rejected_at_attention_boundary`, `test_fingerprint_subclass_rejected_at_replay_boundary`, `test_fingerprint_subclass_rejected_at_tool_input_boundary`, `test_fingerprint_subclass_rejected_at_world_model_boundary` |
| 34 | UUID subclass laundering rejected at attention/tool/plan/world-model boundaries | `test_uuid_subclass_rejected_at_attention_boundary`, `test_uuid_subclass_rejected_at_tool_request_boundary`, `test_uuid_subclass_rejected_at_plan_boundary`, `test_uuid_subclass_rejected_at_world_model_boundary` |
| 35 | concrete value-object subclass (bypassed `revalidate()`) rejected | `test_concrete_value_object_subclass_rejected` |
| 36 | factory/builder exact-type parity (constructor == builder rejection) | `test_factory_rejects_signal_subclass_like_constructor`, `test_factory_rejects_contribution_subclass`, `test_factory_rejects_replay_tool_call_subclass`, `test_exact_instance_versus_malicious_subclass` |

## Roadmap conformance ledger (CA-01..CA-18)

- CA-01 Cognitive Kernel — `PREDECESSOR_BATCH006`
- CA-02 Evidence / Provenance Fabric — `PREDECESSOR_BATCH006` (+ complementary provenance binding in Lane 1/4/5 fingerprints)
- CA-03 Persistent Memory Fabric — `PREDECESSOR_BATCH006`
- CA-04 Financial/Core World Model Architecture — `IMPLEMENTED_BATCH008`
- CA-05 Attention / Priority / Context Selection — `IMPLEMENTED_BATCH008`
- CA-06 Reasoning Modes — `INTEGRATION_GATE_REQUIRED` (enum predecessor; complementary routing seam implemented)
- CA-07 Council of Minds / Specialist Cognition Bus — `INTEGRATION_GATE_REQUIRED` (council predecessor; faculty bus seam implemented)
- CA-08 Critic / Skeptic / Contradiction Engine — `PREDECESSOR_BATCH006` (+ cross-component contradiction integration in Lane 1)
- CA-09 Uncertainty / Calibration Architecture — `INTEGRATION_GATE_REQUIRED` (primitives predecessor; calibration seam implemented)
- CA-10 Planning / Goal Graph — `IMPLEMENTED_BATCH008`
- CA-11 Learning / Reflection / Counterfactual Architecture — `IMPLEMENTED_BATCH008`
- CA-12 Quant / Tool Orchestration Substrate — `IMPLEMENTED_BATCH008`
- CA-13 Specialist Faculty Interface — `IMPLEMENTED_BATCH008`
- CA-14 Dialogue / Voice Cognitive Boundary — `INTEGRATION_GATE_REQUIRED` (boundary predecessor; typed utterance seam implemented)
- CA-15 Authority / Action Firewall — `INTEGRATION_GATE_REQUIRED` (negative boundary predecessor; authority-free handoff envelope implemented)
- CA-16 Cognitive Observability / Replay / Audit — `IMPLEMENTED_BATCH008`
- CA-17 Cognitive Evaluation Framework — `IMPLEMENTED_BATCH008`
- CA-18 Scale / Modularity / Evolution — `IMPLEMENTED_BATCH008`
