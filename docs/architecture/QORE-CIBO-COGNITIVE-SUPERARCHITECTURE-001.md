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
23. `MARKET KNOWLEDGE != CLAIM OF PERFECT CERTAINTY`.
24. `PROFIT AFTER INTERVENTION != PROOF THAT CIBO CAUSED IMPROVEMENT`.

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

The recovered `src/qore/infrastructure/cibo_cognitive_integration.py` closes the
Cognitive Integration Gate for CA-06/CA-07/CA-09 by importing Batch 006 executive
symbols (`CiboReasoningMode`, `CiboCognitiveEvidenceRef`, `CiboDeliberationRole`,
`CiboUncertaintyKind`, `CiboCouncilOutcome`) and binding them by reference/
fingerprint/identity only. The CA-14 (utterance) and CA-15 (handoff → formal
recommendation) binding seams remain open. The exact remaining seams required to combine
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
| 37 | unified secret detector (sk-/AKIA/ghp_/xox/JWT/userinfo) | `test_contains_secret_material_union_semantics`, `test_recommendation_rejects_structural_secret_summary`, `test_content_rejects_structural_secrets`, `test_summary_rejects_structural_secrets` |
| 38 | reflective corruption fails construction (rebuild-on-entry) | `test_synthesize_rejects_reflectively_corrupted_uncertainty`, `test_deliberation_rejects_corrupted_participant_role`, `test_item_rejects_corrupted_nested_provenance` |
| 39 | hostile `logical_values()` object rejected at canonical layer | `test_canonical_material_rejects_hostile_logical_values_object`, `test_canonical_material_rejects_nondeterministic_logical_values_object` |
| 40 | dangling replay fingerprint rejected | `test_no_dangling_replay_fingerprint_field`, `test_replay_reference_requires_matching_episode_id` |
| 41 | swapped UUID + wrong fingerprint rejected | `test_world_snapshot_reference_rejects_swapped_content`, `test_content_binding_rejects_wrong_fingerprint_type` |
| 42 | disagreement cannot collapse to bounded confidence | `test_disagreement_forbids_bounded_confidence`, `test_disagreement_preserved_with_non_bounded_uncertainty` |
| 43 | all six uncertainty kinds representable | `test_covers_all_six_kinds`, `test_zero_confidence_is_not_positive_bounded_confidence` |
| 44 | no mutable module mapping; integration gate has no `_DEPTH_TO_MODE` | `test_integration_has_no_mutable_module_state`, `test_no_global_mutable_registry` |

## Strategic roadmap amendment (Market Mastery / Trader Development)

`CIBO MARKET MASTERY -> MARKET × REGIME × INSTRUMENT × EXACT TRADER UNDERSTANDING -> INDIVIDUAL TRADER DEVELOPMENT -> TRADER LAB EVIDENCE -> CIBO EVALUATES WHETHER THE TRADER ACTUALLY IMPROVED`

Hard laws:

- `MARKET KNOWLEDGE != CLAIM OF PERFECT CERTAINTY`
- `PROFIT AFTER INTERVENTION != PROOF THAT CIBO CAUSED IMPROVEMENT`

This amendment adds two typed families:

- `MarketTrader` suitability (CA-04 world model): typed MARKET × REGIME ×
  INSTRUMENT × EXACT TRADER understanding; a `FAVORABLE` disposition is the only
  positive assertion and is admissible only with current, uncontradicted evidence
  plus explicit limitations — it can never assert perfect certainty.
- Trader-development intervention attribution (CA-17 evaluation): typed
  attribution where post-intervention economic profit is retained as evidence but
  is never, on its own, treated as proof that CIBO caused the improvement.

## Roadmap conformance ledger (CA-01..CA-18)

- CA-01 Cognitive Kernel — `PREDECESSOR_BATCH006`
- CA-02 Evidence / Provenance Fabric — `PREDECESSOR_BATCH006` (+ complementary provenance binding in Lane 1/4/5 fingerprints)
- CA-03 Persistent Memory Fabric — `PREDECESSOR_BATCH006`
- CA-04 Financial/Core World Model Architecture — `IMPLEMENTED_BATCH008` (+ `MarketTrader` suitability family: typed MARKET × REGIME × INSTRUMENT × EXACT TRADER understanding; never a claim of perfect certainty)
- CA-05 Attention / Priority / Context Selection — `IMPLEMENTED_BATCH008`
- CA-06 Reasoning Modes — `INTEGRATION_GATE_CLOSED` (`bind_reasoning_mode`; enum predecessor `CiboReasoningMode` owned by Batch 006)
- CA-07 Council of Minds / Specialist Cognition Bus — `INTEGRATION_GATE_CLOSED` (`bind_deliberation_role` + disagreement-outcome firewall; council predecessor owned by Batch 006)
- CA-08 Critic / Skeptic / Contradiction Engine — `PREDECESSOR_BATCH006` (+ cross-component contradiction integration in Lane 1)
- CA-09 Uncertainty / Calibration Architecture — `INTEGRATION_GATE_CLOSED` (`bind_uncertainty_kind`; primitives predecessor `CiboUncertaintyKind` owned by Batch 006)
- CA-10 Planning / Goal Graph — `IMPLEMENTED_BATCH008`
- CA-11 Learning / Reflection / Counterfactual Architecture — `IMPLEMENTED_BATCH008`
- CA-12 Quant / Tool Orchestration Substrate — `IMPLEMENTED_BATCH008`
- CA-13 Specialist Faculty Interface — `IMPLEMENTED_BATCH008`
- CA-14 Dialogue / Voice Cognitive Boundary — `INTEGRATION_GATE_REQUIRED` (OPEN seam: the gate does not bind `CognitiveUtterance`; typed utterance seam implemented only)
- CA-15 Authority / Action Firewall — `INTEGRATION_GATE_REQUIRED` (OPEN seam: the gate does not bind `CognitiveHandoff` -> formal recommendation; authority-free envelope implemented only)
- CA-16 Cognitive Observability / Replay / Audit — `IMPLEMENTED_BATCH008`
- CA-17 Cognitive Evaluation Framework — `IMPLEMENTED_BATCH008` (+ Trader-development intervention-attribution family: `PROFIT AFTER INTERVENTION != PROOF THAT CIBO CAUSED IMPROVEMENT`)
- CA-18 Scale / Modularity / Evolution — `IMPLEMENTED_BATCH008`

## Residual Root-Family Closure (Correction-003)

Four residual root families (IA-COG-FINAL-004/005/006/007) are closed by Correction-003;
each is witnessed by dedicated adversarial tests and recorded against its hard law:

- **IA-COG-FINAL-004 — Secret-hygiene unification (law 20).** A single canonical,
  provider-neutral `_SECRET_PATTERNS` + `contains_secret_material` now lives in the
  domain leaf `cognitive_contracts.py` (re-exported from `cibo_cognitive_common.py`)
  and replaces the weak literal `_SENSITIVE_PARTS` on every Batch 006 free-text/
  reference surface (`CiboFormalRecommendation.summary`, `CiboMemoryItem.content`,
  `CiboMemorySourceRef.value`, `CiboCouncilSynthesis.summary`,
  `CiboCognitiveEvidenceRef.value`). The union detector rejects `sk-`/`AKIA`/`gh*_`/
  `xox*`/JWT/URL-userinfo/`client_secret`/`bearer`/auth-header/private-key-block and
  legacy `token=`/`secret=` markers at construction and recursive revalidation.
  Boundary semantics are structural, never naive substrings: credential labels
  (`client_secret`, `private_key`, `api_key`, `token`, ...) are rejected only in
  assignment form (`label[=:] value`) or as a PEM block, so a bare field-name mention
  (e.g. "the client_secret field must be configured") is accepted and not over-rejected.
  Witnesses: `test_recommendation_rejects_structural_secret_summary`,
  `test_content_rejects_structural_secrets`, `test_summary_rejects_structural_secrets`,
  `test_contains_secret_material_union_semantics`,
  `test_contains_secret_material_re_export_is_canonical`,
  `test_evidence_ref_accepts_bare_field_name_mention`.
- **IA-COG-FINAL-005 — Constructor-boundary recursive revalidation (law 17).** Every
  affected `__post_init__` now ends with `self.revalidate()` (reusing the existing
  contract) so reflectively corrupted nested uncertainty/confidence/evidence/role/
  recommendation/participant material fails before a `Success`/object can escape.
  Witnesses: `test_synthesize_rejects_reflectively_corrupted_uncertainty`,
  `test_synthesize_rejects_corrupted_nested_recommendation`,
  `test_deliberation_rejects_corrupted_participant_role`,
  `test_item_rejects_corrupted_nested_provenance`.
- **IA-COG-FINAL-006 — Integration seam semantic completeness (CA-02/04/06/07/09/10/12/16/17).**
  `replay_fingerprint` (dangling) is removed; bare `world_snapshot_id`/`synthesis_ref`/
  `evaluation_ref` UUID links are replaced with exact `CiboIntegratedContentBinding`
  `(id, fingerprint)` references; disagreement can no longer coexist with bounded
  confidence; `bind_uncertainty_kind` preserves all six `CiboUncertaintyKind` states and
  zero confidence never becomes positive bounded confidence; nested `CiboUncertainty`
  is recursively revalidated at the gate; plan/tool/replay bindings complete the CA
  replay surface; the double-construction builder hazard is removed (single construction
  with a versioned fingerprint schema `cibo-integrated-episode:v2`). Witnesses:
  `test_no_dangling_replay_fingerprint_field`, `test_world_snapshot_reference_rejects_swapped_content`,
  `test_disagreement_forbids_bounded_confidence`, `test_covers_all_six_kinds`,
  `test_builder_round_trips_every_field`.
- **IA-COG-FINAL-007 — Global mutability / canonical-material trust boundary (law 21).**
  The module-level mutable `_DEPTH_TO_MODE` dict is replaced by a total `match` function
  `_reasoning_mode_for_hint` (no mapping attribute); `canonical_material` is now a closed
  scalar allowlist that rejects any duck-typed `logical_values()` object and secret-bearing
  strings before hashing. Witnesses:
  `test_integration_has_no_mutable_module_state`,
  `test_canonical_material_rejects_hostile_logical_values_object`,
  `test_canonical_material_rejects_nondeterministic_logical_values_object`,
  `test_canonical_material_rejects_secret_bearing_string`.
