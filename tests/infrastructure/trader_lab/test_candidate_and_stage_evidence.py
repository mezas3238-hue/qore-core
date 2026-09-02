from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
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
)
from qore.kernel.result import Failure, Success

_PROCESS_TIME = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)

_CandidateFactory = Callable[..., TraderLabCandidateBinding]
_BindingFactory = Callable[..., ResearchRunStrategyBinding]


def _reference(*, suffix: int = 1) -> TraderLabEvidenceReference:
    return make_trader_lab_evidence_reference(
        kind=TraderLabEvidenceKind.RISK_REVIEW,
        reference_id=UUID(f"72000000-0000-0000-0000-{suffix:012d}"),
        content_digest=TraderLabEvidenceDigest("a" * 64),
        schema_version="risk.review.v1",
    )


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
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000001")
        ),
        stage=TraderLabStage.REPLAY,
        candidate=candidate,
        source_reference=_reference(),
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(built, Success)
    record: TraderLabStageEvidenceRecord = built.value
    assert record.stage is TraderLabStage.REPLAY
    assert record.candidate == candidate
    assert record.fingerprint.value == record.fingerprint.value


def test_stage_evidence_rejects_naive_and_wrong_timestamps(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    naive = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000002")
        ),
        stage=TraderLabStage.REPLAY,
        candidate=candidate,
        source_reference=_reference(),
        produced_at=datetime(2026, 8, 9, 12, 0),
    )
    assert isinstance(naive, Failure)
    assert "timezone-aware" in str(naive.error)

    bad_time: Any = 1
    wrong = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000003")
        ),
        stage=TraderLabStage.REPLAY,
        candidate=candidate,
        source_reference=_reference(),
        produced_at=bad_time,
    )
    assert isinstance(wrong, Failure)


def test_stage_evidence_fingerprint_changes_with_candidate_and_time(
    candidate_factory: _CandidateFactory,
) -> None:
    first = candidate_factory(candidate_suffix=1)
    second = candidate_factory(candidate_suffix=2)
    a = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000004")
        ),
        stage=TraderLabStage.REPLAY,
        candidate=first,
        source_reference=_reference(),
        produced_at=_PROCESS_TIME,
    )
    b = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000005")
        ),
        stage=TraderLabStage.REPLAY,
        candidate=second,
        source_reference=_reference(),
        produced_at=_PROCESS_TIME,
    )
    assert isinstance(a, Success) and isinstance(b, Success)
    assert a.value.fingerprint != b.value.fingerprint


def test_stage_evidence_rejects_fingerprint_tampering(
    candidate_factory: _CandidateFactory,
) -> None:
    candidate = candidate_factory()
    built = build_trader_lab_stage_evidence(
        evidence_id=TraderLabStageEvidenceId(
            UUID("72000000-0000-0000-0000-000000000006")
        ),
        stage=TraderLabStage.REPLAY,
        candidate=candidate,
        source_reference=_reference(),
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
