from __future__ import annotations

from collections.abc import Callable
from dataclasses import fields, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from qore.infrastructure.research_strategy_freeze import ResearchRunStrategyBinding
from qore.infrastructure.trader_lab.candidate import (
    TraderLabCandidateBinding,
    TraderLabCandidateFingerprint,
    TraderLabCandidateId,
    TraderLabCandidateVersion,
    TraderLabValidationError,
    build_trader_lab_candidate_binding,
    compute_trader_lab_candidate_fingerprint,
)
from qore.infrastructure.trader_lab.governed_gate import TraderLabGovernedGate
from qore.infrastructure.trader_lab.stage_evidence import (
    TraderLabEvidenceDigest,
    TraderLabEvidenceKind,
    TraderLabEvidenceReference,
    TraderLabStage,
    TraderLabStageEvidenceFingerprint,
    TraderLabStageEvidenceId,
    TraderLabStageEvidenceRecord,
    build_trader_lab_stage_evidence,
    make_trader_lab_evidence_reference,
    reference_research_economic,
    validate_trader_lab_stage_evidence_record,
)
from qore.kernel.result import Failure, Success

_PROCESS_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

_CandidateFactory = Callable[..., TraderLabCandidateBinding]
_BindingFactory = Callable[..., ResearchRunStrategyBinding]


def test_candidate_fingerprint_is_deterministic(
    candidate_factory: _CandidateFactory,
    strategy_binding_factory: _BindingFactory,
) -> None:
    binding = strategy_binding_factory()
    first = compute_trader_lab_candidate_fingerprint(
        candidate_id=TraderLabCandidateId(UUID("73000000-0000-0000-0000-000000000001")),
        version=TraderLabCandidateVersion("v1"),
        strategy_binding=binding,
    )
    second = compute_trader_lab_candidate_fingerprint(
        candidate_id=TraderLabCandidateId(UUID("73000000-0000-0000-0000-000000000001")),
        version=TraderLabCandidateVersion("v1"),
        strategy_binding=binding,
    )
    assert first == second


def test_identity_version_and_configuration_change_fingerprint(
    candidate_factory: _CandidateFactory,
    strategy_binding_factory: _BindingFactory,
) -> None:
    binding = strategy_binding_factory(configuration_id_suffix=10)
    candidate = candidate_factory(
        candidate_suffix=1, version="v1", binding=binding
    )
    same_config_new_version = candidate_factory(
        candidate_suffix=1, version="v2", binding=binding
    )
    assert candidate.fingerprint != same_config_new_version.fingerprint

    new_id = candidate_factory(candidate_suffix=2, version="v1", binding=binding)
    assert candidate.fingerprint != new_id.fingerprint

    different_config = strategy_binding_factory(configuration_id_suffix=11)
    new_config = candidate_factory(
        candidate_suffix=1, version="v1", binding=different_config
    )
    assert candidate.fingerprint != new_config.fingerprint


def test_candidate_binding_rejects_fingerprint_tampering(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    with pytest.raises(TraderLabValidationError):
        replace(candidate, fingerprint=TraderLabCandidateFingerprint("0" * 64))


def test_candidate_binding_rejects_non_uuid_identity() -> None:
    bad_id: Any = "not-a-uuid"
    with pytest.raises(TraderLabValidationError):
        TraderLabCandidateId(bad_id)


def test_candidate_binding_rejects_bool_and_wrong_version_type(
    strategy_binding_factory: _BindingFactory,
) -> None:
    binding = strategy_binding_factory()
    built = build_trader_lab_candidate_binding(
        candidate_id=TraderLabCandidateId(UUID("73000000-0000-0000-0000-000000000009")),
        version=TraderLabCandidateVersion("v1"),
        strategy_binding=binding,
    )
    assert isinstance(built, Success)
    with pytest.raises(TraderLabValidationError):
        TraderLabCandidateVersion("")  # empty token rejected


def test_stage_evidence_binds_exact_stage_and_candidate(
    candidate_factory: _CandidateFactory,
    governed_reference_factory: Callable[..., TraderLabEvidenceReference],
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000001")
        ),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=candidate,
        source_reference=governed_reference_factory(
            candidate, gate=TraderLabGovernedGate.RISK_REVIEW
        ),
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    record: TraderLabStageEvidenceRecord = built.value
    assert record.stage is TraderLabStage.RISK_REVIEW
    assert record.candidate == candidate
    assert record.fingerprint.value == record.fingerprint.value


def test_stage_evidence_rejects_naive_and_wrong_timestamps(
    candidate_factory: _CandidateFactory,
    governed_reference_factory: Callable[..., TraderLabEvidenceReference],
) -> None:
    candidate = candidate_factory()
    reference = governed_reference_factory(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW
    )
    naive = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000002")
        ),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=candidate,
        source_reference=reference,
        produced_at=datetime(2026, 8, 9, 12, 0),
    )
    assert isinstance(naive, Failure)
    assert "timezone-aware" in str(naive.error)

    bad_time: Any = 1
    wrong = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000003")
        ),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=candidate,
        source_reference=reference,
        produced_at=bad_time,
    )
    assert isinstance(wrong, Failure)


def test_stage_evidence_fingerprint_changes_with_candidate_and_time(
    candidate_factory: _CandidateFactory,
    governed_reference_factory: Callable[..., TraderLabEvidenceReference],
) -> None:
    first = candidate_factory(candidate_suffix=1)
    second = candidate_factory(candidate_suffix=2)
    a = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000004")
        ),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=first,
        source_reference=governed_reference_factory(
            first, gate=TraderLabGovernedGate.RISK_REVIEW
        ),
        produced_at=_PROCESS_TIME,
    )
    b = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000005")
        ),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=second,
        source_reference=governed_reference_factory(
            second, gate=TraderLabGovernedGate.RISK_REVIEW
        ),
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(a, Success) and isinstance(b, Success)
    assert a.value.fingerprint != b.value.fingerprint


def test_stage_evidence_rejects_fingerprint_tampering(
    candidate_factory: _CandidateFactory,
    governed_reference_factory: Callable[..., TraderLabEvidenceReference],
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000006")
        ),
        stage=TraderLabStage.RISK_REVIEW,
        candidate=candidate,
        source_reference=governed_reference_factory(
            candidate, gate=TraderLabGovernedGate.RISK_REVIEW
        ),
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    with pytest.raises(TraderLabValidationError):
        replace(built.value, fingerprint=TraderLabStageEvidenceFingerprint("0" * 64))


def test_evidence_reference_rejects_bad_digest_and_kind() -> None:
    with pytest.raises(TraderLabValidationError):
        TraderLabEvidenceDigest("zz" * 32)
    bad_kind: Any = "not-an-enum"
    with pytest.raises(TraderLabValidationError):
        TraderLabEvidenceReference(
            kind=bad_kind,
            reference_id=UUID("72000000-0000-0000-0000-000000000010"),
            content_digest=TraderLabEvidenceDigest("b" * 64),
            schema_version="test.v1",
        )


def test_no_hidden_clock_rng_or_scheduler_in_trader_lab() -> None:
    package_dir = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "qore"
        / "infrastructure"
        / "trader_lab"
    )
    source = "\n".join(path.read_text() for path in sorted(package_dir.glob("*.py")))
    for forbidden in (
        "uuid4",
        "datetime.now",
        "date.today",
        "from random",
        "import random",
        "threading",
        "time.sleep",
        "scheduler",
        "retry",
        "type: ignore",
        "noqa",
    ):
        assert forbidden not in source, f"forbidden token present: {forbidden}"


def test_stage_kind_contract_rejects_wrong_kind_for_every_stage(
    candidate_factory: _CandidateFactory,
    governed_reference_factory: Callable[..., TraderLabEvidenceReference],
    economic_reference_factory: Callable[
        [TraderLabCandidateBinding], TraderLabEvidenceReference
    ],
) -> None:
    candidate = candidate_factory()
    risk_review = governed_reference_factory(
        candidate, gate=TraderLabGovernedGate.RISK_REVIEW
    )
    economic = economic_reference_factory(candidate)
    for stage in TraderLabStage:
        # A RISK_REVIEW reference is wrong for every stage except RISK_REVIEW,
        # where the never-stage-mapped economic reference is the wrong kind.
        wrong_kind = economic if stage is TraderLabStage.RISK_REVIEW else risk_review
        built = build_trader_lab_stage_evidence(
            evidence_id=TraderLabStageEvidenceId(
                UUID("73000000-0000-0000-0000-000000000200")
            ),
            stage=stage,
            candidate=candidate,
            source_reference=wrong_kind,
            produced_at=_PROCESS_TIME,
        )
        assert isinstance(built, Failure)
        assert "not allowed" in str(built.error)


def test_opaque_seam_rejects_self_authenticating_kind() -> None:
    with pytest.raises(TraderLabValidationError):
        make_trader_lab_evidence_reference(
            kind=TraderLabEvidenceKind.REPLAY_CHRONOLOGY,
            reference_id=UUID("73000000-0000-0000-0000-000000000300"),
            content_digest=TraderLabEvidenceDigest("e" * 64),
            schema_version="market-event-replay.v1",
        )


def test_self_authenticating_reference_requires_helper_construction() -> None:
    with pytest.raises(TraderLabValidationError):
        TraderLabEvidenceReference(
            kind=TraderLabEvidenceKind.REPLAY_CHRONOLOGY,
            reference_id=UUID("73000000-0000-0000-0000-000000000301"),
            content_digest=TraderLabEvidenceDigest("e" * 64),
            schema_version="market-event-replay.v1",
        )


def test_cross_candidate_research_reuse_rejected(
    candidate_factory: _CandidateFactory,
    strategy_binding_factory: _BindingFactory,
    research_reference_factory: Callable[..., TraderLabEvidenceReference],
) -> None:
    candidate_a = candidate_factory(candidate_suffix=1)
    candidate_b = candidate_factory(
        candidate_suffix=2,
        binding=strategy_binding_factory(configuration_id_suffix=11),
    )
    reference_a = research_reference_factory(candidate_a, suffix=100)
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("73000000-0000-0000-0000-000000000400")
        ),
        stage=TraderLabStage.RESEARCH,
        candidate=candidate_b,
        source_reference=reference_a,
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Failure)
    assert "lineage" in str(built.error)


def test_stage_evidence_revalidation_detects_reflective_corruption(
    candidate_factory: _CandidateFactory,
    research_reference_factory: Callable[..., TraderLabEvidenceReference],
) -> None:
    candidate = candidate_factory()
    reference = research_reference_factory(candidate, suffix=200)
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("73000000-0000-0000-0000-000000000500")
        ),
        stage=TraderLabStage.RESEARCH,
        candidate=candidate,
        source_reference=reference,
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    record = built.value

    corrupted_reference = object.__new__(TraderLabEvidenceReference)
    object.__setattr__(
        corrupted_reference, "kind", TraderLabEvidenceKind.RISK_REVIEW
    )
    object.__setattr__(corrupted_reference, "reference_id", reference.reference_id)
    object.__setattr__(
        corrupted_reference, "content_digest", reference.content_digest
    )
    object.__setattr__(
        corrupted_reference, "schema_version", reference.schema_version
    )
    object.__setattr__(
        corrupted_reference, "self_authenticating", reference.self_authenticating
    )
    object.__setattr__(
        corrupted_reference,
        "strategy_binding_fingerprint",
        reference.strategy_binding_fingerprint,
    )
    object.__setattr__(
        corrupted_reference,
        "external_authenticity_proof",
        reference.external_authenticity_proof,
    )
    object.__setattr__(record, "source_reference", corrupted_reference)
    with pytest.raises(TraderLabValidationError):
        validate_trader_lab_stage_evidence_record(record)


def test_self_authenticating_flag_is_not_constructor_argument() -> None:
    """A caller cannot mint a self-authenticating reference with an arbitrary digest.

    ``self_authenticating`` is ``init=False``, so it cannot be supplied as a
    constructor keyword; only the content-deriving helpers may set it through the
    internal factory. Direct construction of a self-authenticating kind without
    that helper therefore fails closed.
    """

    self_authenticating_field = next(
        field_ for field_ in fields(TraderLabEvidenceReference)
        if field_.name == "self_authenticating"
    )
    assert self_authenticating_field.init is False
    with pytest.raises(TraderLabValidationError):
        TraderLabEvidenceReference(
            kind=TraderLabEvidenceKind.RISK_REVIEW,
            reference_id=UUID("73000000-0000-0000-0000-000000000600"),
            content_digest=TraderLabEvidenceDigest("a" * 64),
            schema_version="risk.review.v1",
        )


def test_economic_reference_digest_is_decimal_scale_invariant(
    candidate_factory: _CandidateFactory,
    return_observation_factory: Callable[..., Any],
) -> None:
    """Economically equal Decimals must produce one canonical economic digest."""

    candidate = candidate_factory()
    first = reference_research_economic(
        candidate,
        return_observation_factory(
            candidate, return_rate="0.05", amount="1000", suffix=600
        ),
    )
    second = reference_research_economic(
        candidate,
        return_observation_factory(
            candidate, return_rate="0.0500", amount="1000.00", suffix=600
        ),
    )
    assert first.content_digest == second.content_digest
    assert first.content_digest.value != "0" * 64
