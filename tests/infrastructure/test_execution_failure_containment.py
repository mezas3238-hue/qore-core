from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.execution_failure_containment import (
    ExecutionContainmentDecision,
    ExecutionFailureContainmentValidationError,
    ExecutionFailureKind,
    ExecutionFailureSignal,
    ExecutionFailureStage,
    contain_execution_failure,
    evaluate_reconciliation_containment,
)
from qore.infrastructure.execution_reconciliation import (
    ExecutionReconciliationSnapshot,
    ExecutionReconciliationStatus,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 9, 40, tzinfo=UTC)


def test_explicit_pretrade_failure_is_always_contained() -> None:
    signal = ExecutionFailureSignal(
        stage=ExecutionFailureStage.PRE_TRADE,
        kind=ExecutionFailureKind.SAFETY_BLOCKED,
        observed_at=_NOW,
        code="pretrade.authorization.blocked",
    )

    result = contain_execution_failure(
        signal,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.decision is ExecutionContainmentDecision.CONTAIN
    assert result.value.contained is True
    assert result.value.requires_manual_action is True


def test_failure_kind_must_match_stage() -> None:
    with pytest.raises(ExecutionFailureContainmentValidationError):
        ExecutionFailureSignal(
            stage=ExecutionFailureStage.SUBMIT,
            kind=ExecutionFailureKind.SAFETY_BLOCKED,
            observed_at=_NOW,
            code="submit.safety.blocked",
        )


def test_failure_code_rejects_sensitive_material() -> None:
    with pytest.raises(ExecutionFailureContainmentValidationError):
        ExecutionFailureSignal(
            stage=ExecutionFailureStage.SUBMIT,
            kind=ExecutionFailureKind.SUBMISSION_FAILURE,
            observed_at=_NOW,
            code="submit.secret",
        )


def test_matched_reconciliation_allows_continue() -> None:
    reconciliation = ExecutionReconciliationSnapshot(
        status=ExecutionReconciliationStatus.MATCHED,
        reconciled_at=_NOW,
        issues=(),
    )

    result = evaluate_reconciliation_containment(
        reconciliation,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.decision is ExecutionContainmentDecision.ALLOW_CONTINUE
    assert result.value.reasons == ()
    assert result.value.requires_manual_action is False


def test_diverged_reconciliation_is_contained_without_correction() -> None:
    reconciliation = ExecutionReconciliationSnapshot(
        status=ExecutionReconciliationStatus.DIVERGED,
        reconciled_at=_NOW,
        issues=("status_mismatch",),
    )

    result = evaluate_reconciliation_containment(
        reconciliation,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.decision is ExecutionContainmentDecision.CONTAIN
    assert result.value.source_stage is ExecutionFailureStage.RECONCILIATION
    assert "reconciliation.issue.status_mismatch" in result.value.reasons


def test_missing_reconciliation_is_contained() -> None:
    reconciliation = ExecutionReconciliationSnapshot(
        status=ExecutionReconciliationStatus.MISSING,
        reconciled_at=_NOW,
        issues=("expected_execution_missing_observation",),
    )

    result = evaluate_reconciliation_containment(
        reconciliation,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.contained is True


def test_evaluation_cannot_predate_failure() -> None:
    signal = ExecutionFailureSignal(
        stage=ExecutionFailureStage.OBSERVATION,
        kind=ExecutionFailureKind.OBSERVATION_FAILURE,
        observed_at=_NOW,
        code="observation.invalid",
    )

    result = contain_execution_failure(
        signal,
        evaluated_at=_NOW - timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, ExecutionFailureContainmentValidationError)


def test_containment_surface_has_no_corrective_execution_method() -> None:
    reconciliation = ExecutionReconciliationSnapshot(
        status=ExecutionReconciliationStatus.UNEXPECTED,
        reconciled_at=_NOW,
        issues=("unexpected_execution_observation",),
    )
    result = evaluate_reconciliation_containment(
        reconciliation,
        evaluated_at=_NOW + timedelta(seconds=1),
    )
    assert isinstance(result, Success)

    snapshot = result.value
    assert not hasattr(snapshot, "retry")
    assert not hasattr(snapshot, "resubmit")
    assert not hasattr(snapshot, "correct")
    assert not hasattr(snapshot, "cancel")
