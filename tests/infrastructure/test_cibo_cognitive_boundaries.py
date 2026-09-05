"""Cross-cutting adversarial boundary tests (no clock/network, no global mutable
registry, no provider/model imports in semantic contracts)."""

from __future__ import annotations

import ast
import importlib
import inspect
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.cibo_cognitive_attention import (
    AttentionEvidenceRef,
    AttentionSignal,
    AttentionSignalKind,
    select_context,
)
from qore.infrastructure.cibo_cognitive_common import (
    CiboCognitiveFingerprint,
    CiboCognitiveValidationError,
    fingerprint_material,
)
from qore.infrastructure.cibo_cognitive_planning import (
    CognitiveGoal,
    CognitiveGoalId,
    CognitiveGoalStatus,
    CognitiveTask,
    CognitiveTaskId,
    CognitiveTaskStatus,
    EvidenceRequirement,
    build_cognitive_plan,
)
from qore.infrastructure.cibo_cognitive_replay import (
    ReplayToolCall,
    build_replay_episode,
)
from qore.infrastructure.cibo_cognitive_tools import (
    FacultyContribution,
    FacultyContributionKind,
    FacultyId,
    FacultyVersion,
    ToolId,
    ToolInput,
    ToolRequest,
    ToolVersion,
    order_contributions,
)
from qore.infrastructure.cibo_cognitive_world_model import (
    WorldModelDomain,
    WorldModelReference,
    WorldModelReferenceStatus,
    WorldModelSourceId,
    WorldModelSourceVersion,
    build_world_model_snapshot,
)
from qore.infrastructure.cibo_executive_journal import (
    CiboExecutiveJournalValidationError,
    CiboJournalEntry,
    CiboJournalEntryKind,
    CiboJournalStore,
)
from qore.infrastructure.cibo_executive_memory import (
    CiboExecutiveMemoryValidationError,
    CiboMemoryFreshness,
    CiboMemoryFreshnessState,
    CiboMemoryItem,
    CiboMemoryKind,
    CiboMemoryProvenance,
    CiboMemorySourceRef,
    CiboMemoryStore,
)
from qore.kernel.result import Failure
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboDeliberationRole,
    CiboEpistemicClaim,
    CiboEpistemicState,
    CiboReasoningMode,
    CiboUncertainty,
    CiboUncertaintyKind,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveValidationError as CiboContractsValidationError,
)

_SEMANTIC_MODULES = (
    "qore.infrastructure.cibo_cognitive_common",
    "qore.infrastructure.cibo_cognitive_world_model",
    "qore.infrastructure.cibo_cognitive_attention",
    "qore.infrastructure.cibo_cognitive_planning",
    "qore.infrastructure.cibo_cognitive_tools",
    "qore.infrastructure.cibo_cognitive_replay",
    "qore.infrastructure.cibo_cognitive_evaluation",
)

_PROVIDER_ROOTS = frozenset(
    {
        "openai",
        "anthropic",
        "cohere",
        "mistralai",
        "google",
        "transformers",
        "torch",
        "tensorflow",
        "keras",
        "langchain",
        "llama_index",
        "groq",
        "boto3",
        "vertexai",
        "azure",
        "huggingface",
        "vllm",
        "litellm",
    }
)

_FORBIDDEN_CALL_TOKENS = (
    "datetime.now",
    ".now(",
    "date.today",
    ".today(",
    "time.sleep",
    "sleep(",
    "uuid4(",
    "random.",
    "randint(",
    "getrandbits(",
    "socket.",
    "urllib",
    "httpx",
    "http.client",
    "Thread(",
    "threading.",
)


def _source(module_name: str) -> str:
    module = importlib.import_module(module_name)
    return inspect.getsource(module)


def _imported_module_names(source: str) -> list[str]:
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def test_no_provider_or_model_imports_in_semantic_contracts() -> None:
    for module_name in _SEMANTIC_MODULES:
        for imported in _imported_module_names(_source(module_name)):
            root = imported.split(".")[0]
            assert root not in _PROVIDER_ROOTS, f"{module_name} imports provider root {imported}"
            lowered = imported.lower()
            for token in ("provider", "adapter", "llm", "model"):
                assert token not in lowered, f"{module_name} imports {imported} ({token})"


def test_no_clock_or_network_side_effects_in_semantic_contracts() -> None:
    for module_name in _SEMANTIC_MODULES:
        source = _source(module_name)
        for token in _FORBIDDEN_CALL_TOKENS:
            assert token not in source, f"{module_name} references forbidden token {token}"


def test_no_global_mutable_registry() -> None:
    for module_name in _SEMANTIC_MODULES:
        module = importlib.import_module(module_name)
        for name, obj in vars(module).items():
            if name.startswith("__"):
                continue
            assert not isinstance(
                obj, (dict, list, set)
            ), f"{module_name}.{name} is a mutable module-level registry"


def test_integration_has_no_mutable_module_state() -> None:
    """The integration gate must expose no mutable module-level registry (law 21).

    The former ``_DEPTH_TO_MODE`` dict is replaced by a total ``match`` function,
    so there is no ``dict``/``list``/``set`` and no ``_DEPTH_TO_MODE`` attribute.
    """
    module = importlib.import_module("qore.infrastructure.cibo_cognitive_integration")
    assert not hasattr(module, "_DEPTH_TO_MODE")
    for name, obj in vars(module).items():
        if name.startswith("__"):
            continue
        assert not isinstance(
            obj, (dict, list, set)
        ), f"integration.{name} is a mutable module-level registry"


# ---------------------------------------------------------------------------
# Correction-001: exact-runtime-type / concrete-subclass-laundering witnesses.
# A concrete value/identity type must be rejected when a subclass is laundered
# through a semantic trust boundary, even if the subclass overrides revalidate()
# to bypass its own validation. Intentional structural polymorphism (Sequence
# inputs) remains accepted and is not asserted against here.
# ---------------------------------------------------------------------------

_AWARE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
_UUID_A = UUID("00000000-0000-0000-0000-0000000000aa")
_UUID_B = UUID("00000000-0000-0000-0000-0000000000ab")


class _EvilFingerprint(CiboCognitiveFingerprint):
    """Bypasses value validation; must still be rejected by exact-type checks."""

    def revalidate(self) -> None:
        pass


class _EvilUUID(UUID):
    """A UUID subclass that would pass ``isinstance(x, UUID)`` but is not exact."""


class _EvilToolId(ToolId):
    """A concrete value object whose token validation is bypassed."""

    def revalidate(self) -> None:
        pass


class _EvilSignal(AttentionSignal):
    """A concrete value object bypassing its own revalidation."""

    def revalidate(self) -> None:
        pass


class _EvilContribution(FacultyContribution):
    """A concrete value object bypassing its own revalidation."""

    def revalidate(self) -> None:
        pass


class _EvilToolCall(ReplayToolCall):
    """A concrete value object bypassing its own revalidation."""

    def revalidate(self) -> None:
        pass


def _reference() -> WorldModelReference:
    return WorldModelReference(
        domain=WorldModelDomain.MARKET,
        source_id=WorldModelSourceId("source-a"),
        source_version=WorldModelSourceVersion("1"),
        as_of=_AWARE,
        status=WorldModelReferenceStatus.CURRENT,
        evidence_fingerprint=fingerprint_material("source-a:1"),
        evidence_label="provider-neutral market evidence",
    )


def _tool_input(label: str = "x") -> ToolInput:
    return ToolInput(material=(label,), fingerprint=fingerprint_material((label,)))


def test_fingerprint_subclass_rejected_at_attention_boundary() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        AttentionEvidenceRef(reference_id="ev-1", fingerprint=_EvilFingerprint("a" * 64))


def test_fingerprint_subclass_rejected_at_replay_boundary() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        ReplayToolCall(
            request_id=_UUID_A,
            input_fingerprint=_EvilFingerprint("a" * 64),
            result_fingerprint=None,
        )


def test_fingerprint_subclass_rejected_at_tool_input_boundary() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        ToolInput(material=("x",), fingerprint=_EvilFingerprint("a" * 64))


def test_fingerprint_subclass_rejected_at_world_model_boundary() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        WorldModelReference(
            domain=WorldModelDomain.MARKET,
            source_id=WorldModelSourceId("source-a"),
            source_version=WorldModelSourceVersion("1"),
            as_of=_AWARE,
            status=WorldModelReferenceStatus.CURRENT,
            evidence_fingerprint=_EvilFingerprint("a" * 64),
            evidence_label="x",
        )


def test_uuid_subclass_rejected_at_attention_boundary() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        AttentionSignal(
            signal_id=_EvilUUID(str(_UUID_A)),
            kind=AttentionSignalKind.ANOMALY,
            summary="summary",
            evidence_refs=(AttentionEvidenceRef(reference_id="ev-1"),),
            severity=50,
            priority_reason="reason",
        )


def test_uuid_subclass_rejected_at_tool_request_boundary() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        ToolRequest(
            request_id=_EvilUUID(str(_UUID_A)),
            tool_id=ToolId("regime"),
            tool_version=ToolVersion("1"),
            input=_tool_input(),
        )


def test_uuid_subclass_rejected_at_plan_boundary() -> None:
    goal = CognitiveGoal(
        goal_id=CognitiveGoalId(_UUID_A), description="goal", status=CognitiveGoalStatus.PENDING
    )
    task = CognitiveTask(
        task_id=CognitiveTaskId(_UUID_B),
        goal_id=goal.goal_id,
        description="task",
        dependencies=(),
        required_evidence=(EvidenceRequirement(reference="ev-1"),),
        status=CognitiveTaskStatus.PENDING,
    )
    with pytest.raises(CiboCognitiveValidationError):
        build_cognitive_plan(plan_id=_EvilUUID(str(_UUID_A)), goals=[goal], tasks=[task])


def test_uuid_subclass_rejected_at_world_model_boundary() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        build_world_model_snapshot(
            snapshot_id=_EvilUUID(str(_UUID_A)), as_of=_AWARE, references=[_reference()]
        )


def test_concrete_value_object_subclass_rejected() -> None:
    with pytest.raises(CiboCognitiveValidationError):
        ToolRequest(
            request_id=_UUID_A,
            tool_id=_EvilToolId("regime"),
            tool_version=ToolVersion("1"),
            input=_tool_input(),
        )


def test_factory_rejects_signal_subclass_like_constructor() -> None:
    evil = _EvilSignal(
        signal_id=_UUID_A,
        kind=AttentionSignalKind.ANOMALY,
        summary="summary",
        evidence_refs=(),  # invalid, but bypassed by the overridden revalidate()
        severity=50,
        priority_reason="reason",
    )
    with pytest.raises(CiboCognitiveValidationError):
        select_context([evil])


def test_factory_rejects_contribution_subclass() -> None:
    evil = _EvilContribution(
        contribution_id=_UUID_A,
        faculty_id=FacultyId("markets"),
        faculty_version=FacultyVersion("1"),
        kind=FacultyContributionKind.OBSERVATION,
        content="",  # invalid, but bypassed by the overridden revalidate()
    )
    with pytest.raises(CiboCognitiveValidationError):
        order_contributions([evil])


def test_factory_rejects_replay_tool_call_subclass() -> None:
    evil = _EvilToolCall(
        request_id=_UUID_A,
        input_fingerprint=CiboCognitiveFingerprint("a" * 64),
        result_fingerprint=None,
    )
    with pytest.raises(CiboCognitiveValidationError):
        build_replay_episode(
            episode_id=_UUID_A,
            recorded_at=_AWARE,
            world_snapshot_id=_UUID_B,
            tool_calls=[evil],
            evidence_refs=("ev-1",),
        )


def test_exact_instance_versus_malicious_subclass() -> None:
    """Exact instances pass; a laundering subclass fails with the same error."""
    exact = ToolRequest(
        request_id=_UUID_A,
        tool_id=ToolId("regime"),
        tool_version=ToolVersion("1"),
        input=_tool_input(),
    )
    assert exact.tool_id.value == "regime"
    with pytest.raises(CiboCognitiveValidationError):
        ToolRequest(
            request_id=_UUID_A,
            tool_id=_EvilToolId("regime"),
            tool_version=ToolVersion("1"),
            input=_tool_input(),
        )


# ---------------------------------------------------------------------------
# IA-COG-FINAL-001/002: no Cognitive -> Functions/Trader-Manager implementation
# dependency, and exact-runtime-type/subclass-laundering rejection across the
# Batch 006 trust boundaries (UUID / datetime / enum / str / tuple / value object).
# ---------------------------------------------------------------------------

_COGNITIVE_MODULES = (
    "qore.modules.cibo.cognitive_contracts",
    "qore.infrastructure.cibo_executive_brain",
    "qore.infrastructure.cibo_executive_deliberation",
    "qore.infrastructure.cibo_executive_journal",
    "qore.infrastructure.cibo_executive_memory",
    "qore.infrastructure.cibo_cognitive_common",
    "qore.infrastructure.cibo_cognitive_world_model",
    "qore.infrastructure.cibo_cognitive_attention",
    "qore.infrastructure.cibo_cognitive_planning",
    "qore.infrastructure.cibo_cognitive_tools",
    "qore.infrastructure.cibo_cognitive_replay",
    "qore.infrastructure.cibo_cognitive_evaluation",
    "qore.infrastructure.cibo_cognitive_integration",
)

_FORBIDDEN_COGNITIVE_DEPS = (
    "cibo_trader_capability_profile",
    "cibo_trader_manager",
    "trader_manager",
    "cibo_trader_lab",
    "trader_lab",
    "specialized_trader",
    "specialized_traders",
)


def test_no_trader_functions_implementation_dependency_in_cognitive_paths() -> None:
    for module_name in _COGNITIVE_MODULES:
        for imported in _imported_module_names(_source(module_name)):
            for forbidden in _FORBIDDEN_COGNITIVE_DEPS:
                assert forbidden not in imported, (
                    f"{module_name} imports forbidden {imported}"
                )


class _HostileStr(str):
    pass


class _HostileTuple(tuple[object, ...]):
    pass


class _HostileDatetime(datetime):
    pass


class _EvilJournalEntry(CiboJournalEntry):
    def revalidate(self) -> None:
        pass


class _EvilMemoryItem(CiboMemoryItem):
    def revalidate(self) -> None:
        pass


def _memory_item(item_id: UUID = _UUID_A) -> CiboMemoryItem:
    return CiboMemoryItem(
        item_id=item_id,
        kind=CiboMemoryKind.DECISION,
        subject_code="subject-demo",
        content="retained observation",
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef("evidence:source"),
            effective_at=_AWARE,
        ),
        freshness=CiboMemoryFreshness(state=CiboMemoryFreshnessState.CURRENT, as_of=_AWARE),
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:demo"),),
    )


def test_batch006_uuid_subclass_rejected_at_journal_boundary() -> None:
    with pytest.raises(CiboExecutiveJournalValidationError):
        CiboJournalEntry(
            entry_id=_EvilUUID(str(_UUID_A)),
            episode_id=_UUID_B,
            kind=CiboJournalEntryKind.DECISION,
            subject_code="subject-demo",
            recorded_at=_AWARE,
            evidence_refs=(CiboCognitiveEvidenceRef("evidence:demo"),),
        )


def test_batch006_uuid_subclass_rejected_at_memory_boundary() -> None:
    with pytest.raises(CiboExecutiveMemoryValidationError):
        _memory_item(item_id=_EvilUUID(str(_UUID_A)))


def test_batch006_str_subclass_rejected_at_evidence_ref() -> None:
    with pytest.raises(CiboContractsValidationError):
        CiboCognitiveEvidenceRef(_HostileStr("evidence:demo"))


def test_batch006_strenum_member_laundered_as_str_rejected() -> None:
    with pytest.raises(CiboContractsValidationError):
        CiboDeliberationRole(CiboReasoningMode.FAST)


def test_batch006_tuple_subclass_rejected_at_journal_evidence() -> None:
    refs = cast(
        tuple[CiboCognitiveEvidenceRef, ...],
        _HostileTuple((CiboCognitiveEvidenceRef("evidence:demo"),)),
    )
    with pytest.raises(CiboExecutiveJournalValidationError):
        CiboJournalEntry(
            entry_id=_UUID_A,
            episode_id=_UUID_B,
            kind=CiboJournalEntryKind.DECISION,
            subject_code="subject-demo",
            recorded_at=_AWARE,
            evidence_refs=refs,
        )


def test_batch006_datetime_subclass_rejected_at_journal_recorded_at() -> None:
    hostile_dt = _HostileDatetime(2026, 8, 9, 0, 0, tzinfo=UTC)
    with pytest.raises(CiboExecutiveJournalValidationError):
        CiboJournalEntry(
            entry_id=_UUID_A,
            episode_id=_UUID_B,
            kind=CiboJournalEntryKind.DECISION,
            subject_code="subject-demo",
            recorded_at=hostile_dt,
            evidence_refs=(CiboCognitiveEvidenceRef("evidence:demo"),),
        )


def test_batch006_journal_store_rejects_value_object_subclass() -> None:
    evil = _EvilJournalEntry(
        entry_id=_UUID_A,
        episode_id=_UUID_B,
        kind=CiboJournalEntryKind.DECISION,
        subject_code="subject-demo",
        recorded_at=_AWARE,
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:demo"),),
    )
    result = CiboJournalStore().record(evil)
    assert isinstance(result, Failure)


def test_batch006_memory_store_rejects_value_object_subclass() -> None:
    evil = _EvilMemoryItem(
        item_id=_UUID_A,
        kind=CiboMemoryKind.DECISION,
        subject_code="subject-demo",
        content="retained observation",
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef("evidence:source"),
            effective_at=_AWARE,
        ),
        freshness=CiboMemoryFreshness(state=CiboMemoryFreshnessState.CURRENT, as_of=_AWARE),
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:demo"),),
    )
    result = CiboMemoryStore().record(evil)
    assert isinstance(result, Failure)


def test_batch006_epistemic_claim_requires_evidence() -> None:
    with pytest.raises(CiboContractsValidationError, match="evidence"):
        CiboEpistemicClaim(
            claim_id=_UUID_A,
            epistemic_state=CiboEpistemicState.OBSERVATION,
            reasoning_mode=CiboReasoningMode.HIGH,
            content_code="claim-demo",
            evidence_refs=(),
            uncertainty=CiboUncertainty(kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE),
        )


def test_batch006_reflective_corruption_fails_store_revalidation() -> None:
    entry = CiboJournalEntry(
        entry_id=_UUID_A,
        episode_id=_UUID_B,
        kind=CiboJournalEntryKind.DECISION,
        subject_code="subject-demo",
        recorded_at=_AWARE,
        evidence_refs=(CiboCognitiveEvidenceRef("evidence:demo"),),
    )
    object.__setattr__(entry.evidence_refs[0], "value", "secret=injected")
    result = CiboJournalStore().record(entry)
    assert isinstance(result, Failure)
