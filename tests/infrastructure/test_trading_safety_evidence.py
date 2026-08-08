from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.execution_orchestration import ExecutionOrchestrationId
from qore.infrastructure.order_intent import OrderIntentId
from qore.infrastructure.trading_safety_evidence import (
    TradingSafetyCheck,
    TradingSafetyCheckStatus,
    TradingSafetyEvidenceRecord,
    TradingSafetyEvidenceValidationError,
    TradingSafetyVerdict,
    aggregate_trading_safety_evidence,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 9, 50, tzinfo=UTC)
_ORCHESTRATION_ID = ExecutionOrchestrationId(
    UUID("b2000000-0000-0000-0000-000000000001")
)
_INTENT_ID = OrderIntentId(UUID("b2000000-0000-0000-0000-000000000002"))


def _record(
    check: TradingSafetyCheck,
    *,
    status: TradingSafetyCheckStatus = TradingSafetyCheckStatus.PASS,
) -> TradingSafetyEvidenceRecord:
    return TradingSafetyEvidenceRecord(
        check=check,
        status=status,
        observed_at=_NOW,
        code=f"{check.value}.{status.value}",
    )


def _complete_records() -> tuple[TradingSafetyEvidenceRecord, ...]:
    return tuple(_record(check) for check in TradingSafetyCheck)


def test_complete_passing_evidence_produces_pass_verdict() -> None:
    result = aggregate_trading_safety_evidence(
        _ORCHESTRATION_ID,
        _INTENT_ID,
        _complete_records(),
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.verdict is TradingSafetyVerdict.PASS
    assert result.value.passed is True
    assert tuple(record.check for record in result.value.records) == (
        TradingSafetyCheck.AUTHORIZATION,
        TradingSafetyCheck.SWITCH,
        TradingSafetyCheck.IDEMPOTENCY,
        TradingSafetyCheck.RECONCILIATION,
        TradingSafetyCheck.CONTAINMENT,
    )


def test_any_failed_check_forces_bundle_failure() -> None:
    records = tuple(
        _record(
            check,
            status=(
                TradingSafetyCheckStatus.FAIL
                if check is TradingSafetyCheck.RECONCILIATION
                else TradingSafetyCheckStatus.PASS
            ),
        )
        for check in TradingSafetyCheck
    )

    result = aggregate_trading_safety_evidence(
        _ORCHESTRATION_ID,
        _INTENT_ID,
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert result.value.verdict is TradingSafetyVerdict.FAIL
    assert result.value.passed is False


def test_missing_required_check_is_rejected() -> None:
    records = tuple(
        _record(check)
        for check in TradingSafetyCheck
        if check is not TradingSafetyCheck.CONTAINMENT
    )

    result = aggregate_trading_safety_evidence(
        _ORCHESTRATION_ID,
        _INTENT_ID,
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, TradingSafetyEvidenceValidationError)


def test_duplicate_check_is_rejected() -> None:
    records = _complete_records() + (_record(TradingSafetyCheck.AUTHORIZATION),)

    result = aggregate_trading_safety_evidence(
        _ORCHESTRATION_ID,
        _INTENT_ID,
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, TradingSafetyEvidenceValidationError)


def test_evidence_record_cannot_postdate_bundle_evaluation() -> None:
    records = tuple(
        TradingSafetyEvidenceRecord(
            check=check,
            status=TradingSafetyCheckStatus.PASS,
            observed_at=(
                _NOW + timedelta(seconds=2)
                if check is TradingSafetyCheck.CONTAINMENT
                else _NOW
            ),
            code=f"{check.value}.pass",
        )
        for check in TradingSafetyCheck
    )

    result = aggregate_trading_safety_evidence(
        _ORCHESTRATION_ID,
        _INTENT_ID,
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, TradingSafetyEvidenceValidationError)


def test_safety_code_rejects_sensitive_material() -> None:
    with pytest.raises(TradingSafetyEvidenceValidationError):
        TradingSafetyEvidenceRecord(
            check=TradingSafetyCheck.AUTHORIZATION,
            status=TradingSafetyCheckStatus.FAIL,
            observed_at=_NOW,
            code="authorization.secret",
        )


def test_input_order_is_normalized_deterministically() -> None:
    records = tuple(reversed(_complete_records()))

    result = aggregate_trading_safety_evidence(
        _ORCHESTRATION_ID,
        _INTENT_ID,
        records,
        evaluated_at=_NOW + timedelta(seconds=1),
    )

    assert isinstance(result, Success)
    assert tuple(record.check for record in result.value.records) == (
        TradingSafetyCheck.AUTHORIZATION,
        TradingSafetyCheck.SWITCH,
        TradingSafetyCheck.IDEMPOTENCY,
        TradingSafetyCheck.RECONCILIATION,
        TradingSafetyCheck.CONTAINMENT,
    )
