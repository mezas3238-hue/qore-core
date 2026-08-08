from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.operational_safety_certification_preparation import (
    OperationalSafetyCertificationPreparationError,
    OperationalSafetyCertificationPreparationEvidence,
    OperationalSafetyCertificationPreparationValidationError,
    OperationalSafetyEvidenceRef,
    OperationalSafetyPreparationCheck,
    OperationalSafetyPreparationCheckStatus,
    OperationalSafetyPreparationId,
    OperationalSafetyPreparationRecord,
    OperationalSafetyPreparationStatus,
    build_operational_safety_certification_preparation_evidence,
)
from qore.kernel.result import Failure, Result, Success

_NOW = datetime(2026, 8, 8, 23, 45, tzinfo=UTC)
_PREPARATION_ID = OperationalSafetyPreparationId(
    UUID("33000000-0000-0000-0000-000000000001")
)
_FINGERPRINT = "sha256:0123456789abcdef01234567"

_CHECKS = (
    OperationalSafetyPreparationCheck.AUTHORIZATION,
    OperationalSafetyPreparationCheck.TEST_DEMO_ENVIRONMENT,
    OperationalSafetyPreparationCheck.ACCOUNT_GUARD,
    OperationalSafetyPreparationCheck.INSTRUMENT_GUARD,
    OperationalSafetyPreparationCheck.QUANTITY_GUARD,
    OperationalSafetyPreparationCheck.KILL_SWITCH,
    OperationalSafetyPreparationCheck.IDEMPOTENCY,
    OperationalSafetyPreparationCheck.PROVIDER_FAILURE_CONTAINMENT,
    OperationalSafetyPreparationCheck.AMBIGUOUS_EXECUTION_CONTAINMENT,
    OperationalSafetyPreparationCheck.RECONCILIATION_CONTAINMENT,
    OperationalSafetyPreparationCheck.SECRET_SANITIZATION,
    OperationalSafetyPreparationCheck.PRODUCTION_BLOCKED,
    OperationalSafetyPreparationCheck.NO_AUTOMATIC_CORRECTIVE_TRADING,
)


def _record(
    check: OperationalSafetyPreparationCheck,
    *,
    status: OperationalSafetyPreparationCheckStatus = (
        OperationalSafetyPreparationCheckStatus.PASS
    ),
) -> OperationalSafetyPreparationRecord:
    return OperationalSafetyPreparationRecord(
        check=check,
        status=status,
        observed_at=_NOW - timedelta(seconds=1),
        code=f"mission03.{check.value}.verified",
        evidence_refs=(
            OperationalSafetyEvidenceRef(f"dryrun:safety/{check.value}"),
        ),
    )


def _records(
    *,
    failed_check: OperationalSafetyPreparationCheck | None = None,
) -> tuple[OperationalSafetyPreparationRecord, ...]:
    return tuple(
        _record(
            check,
            status=(
                OperationalSafetyPreparationCheckStatus.FAIL
                if check is failed_check
                else OperationalSafetyPreparationCheckStatus.PASS
            ),
        )
        for check in _CHECKS
    )


def _build(
    records: tuple[OperationalSafetyPreparationRecord, ...],
) -> Result[
    OperationalSafetyCertificationPreparationEvidence,
    OperationalSafetyCertificationPreparationError,
]:
    return build_operational_safety_certification_preparation_evidence(
        _PREPARATION_ID,
        records,
        provider_key="oanda-v20",
        environment="demo",
        account_fingerprint=_FINGERPRINT,
        evaluated_at=_NOW,
    )


def test_complete_pass_matrix_is_prepared_but_never_operationally_certified() -> None:
    result = _build(tuple(reversed(_records())))

    assert isinstance(result, Success)
    evidence = result.value
    assert evidence.status is OperationalSafetyPreparationStatus.PREPARED
    assert evidence.operationally_certified is False
    assert tuple(record.check for record in evidence.records) == _CHECKS
    assert evidence.logical_values() == evidence.logical_values()

    payload = evidence.public_payload()
    assert payload["status"] == "prepared"
    assert payload["operationally_certified"] is False
    assert payload["provider"] == "oanda-v20"
    assert payload["environment"] == "demo"
    assert payload["account_fingerprint"] == _FINGERPRINT
    assert "practice-" not in evidence.to_json()


def test_one_failed_check_blocks_preparation() -> None:
    result = _build(
        _records(
            failed_check=(
                OperationalSafetyPreparationCheck.AMBIGUOUS_EXECUTION_CONTAINMENT
            )
        )
    )

    assert isinstance(result, Success)
    assert result.value.status is OperationalSafetyPreparationStatus.BLOCKED
    assert result.value.operationally_certified is False


def test_incomplete_matrix_fails_closed() -> None:
    result = _build(_records()[:-1])

    assert isinstance(result, Failure)
    assert isinstance(
        result.error,
        OperationalSafetyCertificationPreparationValidationError,
    )
    assert "incomplete" in str(result.error)


def test_duplicate_check_fails_closed() -> None:
    records = _records()
    duplicate = (*records, records[0])

    result = _build(duplicate)

    assert isinstance(result, Failure)
    assert isinstance(
        result.error,
        OperationalSafetyCertificationPreparationValidationError,
    )
    assert "duplicate" in str(result.error)


def test_evidence_ref_and_code_reject_sensitive_material() -> None:
    with pytest.raises(OperationalSafetyCertificationPreparationValidationError):
        OperationalSafetyEvidenceRef("dryrun:safety/token=abc")

    with pytest.raises(OperationalSafetyCertificationPreparationValidationError):
        OperationalSafetyPreparationRecord(
            check=OperationalSafetyPreparationCheck.AUTHORIZATION,
            status=OperationalSafetyPreparationCheckStatus.PASS,
            observed_at=_NOW,
            code="token=abc",
            evidence_refs=(OperationalSafetyEvidenceRef("dryrun:safety/auth"),),
        )


def test_evidence_refs_are_deterministically_sorted_and_unique() -> None:
    record = OperationalSafetyPreparationRecord(
        check=OperationalSafetyPreparationCheck.AUTHORIZATION,
        status=OperationalSafetyPreparationCheckStatus.PASS,
        observed_at=_NOW,
        code="mission03.authorization.verified",
        evidence_refs=(
            OperationalSafetyEvidenceRef("dryrun:safety/z"),
            OperationalSafetyEvidenceRef("dryrun:safety/a"),
        ),
    )

    assert tuple(item.value for item in record.evidence_refs) == (
        "dryrun:safety/a",
        "dryrun:safety/z",
    )

    with pytest.raises(OperationalSafetyCertificationPreparationValidationError):
        OperationalSafetyPreparationRecord(
            check=OperationalSafetyPreparationCheck.AUTHORIZATION,
            status=OperationalSafetyPreparationCheckStatus.PASS,
            observed_at=_NOW,
            code="mission03.authorization.verified",
            evidence_refs=(
                OperationalSafetyEvidenceRef("dryrun:safety/a"),
                OperationalSafetyEvidenceRef("dryrun:safety/a"),
            ),
        )


def test_only_selected_provider_demo_environment_and_fingerprint_are_allowed() -> None:
    for provider, environment, fingerprint in (
        ("other-provider", "demo", _FINGERPRINT),
        ("oanda-v20", "production", _FINGERPRINT),
        ("oanda-v20", "demo", "practice-001"),
    ):
        result = build_operational_safety_certification_preparation_evidence(
            _PREPARATION_ID,
            _records(),
            provider_key=provider,
            environment=environment,
            account_fingerprint=fingerprint,
            evaluated_at=_NOW,
        )
        assert isinstance(result, Failure)
        assert isinstance(
            result.error,
            OperationalSafetyCertificationPreparationValidationError,
        )


def test_record_cannot_postdate_evaluation() -> None:
    records = list(_records())
    records[0] = OperationalSafetyPreparationRecord(
        check=OperationalSafetyPreparationCheck.AUTHORIZATION,
        status=OperationalSafetyPreparationCheckStatus.PASS,
        observed_at=_NOW + timedelta(seconds=1),
        code="mission03.authorization.verified",
        evidence_refs=(OperationalSafetyEvidenceRef("dryrun:safety/auth"),),
    )

    result = _build(tuple(records))

    assert isinstance(result, Failure)
    assert isinstance(
        result.error,
        OperationalSafetyCertificationPreparationValidationError,
    )
    assert "postdate" in str(result.error)


def test_direct_constructor_requires_exact_canonical_record_order() -> None:
    with pytest.raises(OperationalSafetyCertificationPreparationValidationError):
        OperationalSafetyCertificationPreparationEvidence(
            preparation_id=_PREPARATION_ID,
            provider_key="oanda-v20",
            environment="demo",
            account_fingerprint=_FINGERPRINT,
            evaluated_at=_NOW,
            records=tuple(reversed(_records())),
        )


def test_public_json_is_deterministic_and_contains_no_operational_claim() -> None:
    result = _build(_records())
    assert isinstance(result, Success)

    first = result.value.to_json()
    second = result.value.to_json()
    payload = json.loads(first)

    assert first == second
    assert payload["schema"] == "qore.mission03.operational-safety-preparation.v1"
    assert payload["operationally_certified"] is False
    assert "certified" not in payload["status"]
    assert "token" not in first.lower()
    assert "authorization:" not in first.lower()
