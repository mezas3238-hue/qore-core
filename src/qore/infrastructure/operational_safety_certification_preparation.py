from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_EVIDENCE_SCHEMA = "qore.mission03.operational-safety-preparation.v1"
_SENSITIVE_PARTS = (
    "authorization:",
    "bearer ",
    "client_secret",
    "password",
    "secret=",
    "token=",
)


class OperationalSafetyCertificationPreparationError(ExternalPortError):
    """Base error for deterministic MISSION-03 safety-certification preparation."""

    __slots__ = ()


class OperationalSafetyCertificationPreparationValidationError(
    OperationalSafetyCertificationPreparationError
):
    """A safety-certification preparation value violates an invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class OperationalSafetyPreparationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety preparation id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class OperationalSafetyEvidenceRef:
    """Opaque sanitized reference to deterministic or future operational evidence."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9._:/-]*",
            self.value,
        ) is None:
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety evidence ref must use canonical lowercase syntax"
            )
        normalized = self.value.lower()
        if any(part in normalized for part in _SENSITIVE_PARTS):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety evidence ref must not contain sensitive material"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class OperationalSafetyPreparationCheck(StrEnum):
    AUTHORIZATION = "authorization"
    TEST_DEMO_ENVIRONMENT = "test-demo-environment"
    ACCOUNT_GUARD = "account-guard"
    INSTRUMENT_GUARD = "instrument-guard"
    QUANTITY_GUARD = "quantity-guard"
    KILL_SWITCH = "kill-switch"
    IDEMPOTENCY = "idempotency"
    PROVIDER_FAILURE_CONTAINMENT = "provider-failure-containment"
    AMBIGUOUS_EXECUTION_CONTAINMENT = "ambiguous-execution-containment"
    RECONCILIATION_CONTAINMENT = "reconciliation-containment"
    SECRET_SANITIZATION = "secret-sanitization"
    PRODUCTION_BLOCKED = "production-blocked"
    NO_AUTOMATIC_CORRECTIVE_TRADING = "no-automatic-corrective-trading"


_REQUIRED_CHECKS: tuple[OperationalSafetyPreparationCheck, ...] = (
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


class OperationalSafetyPreparationCheckStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"


class OperationalSafetyPreparationStatus(StrEnum):
    PREPARED = "prepared"
    BLOCKED = "blocked"


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise OperationalSafetyCertificationPreparationValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise OperationalSafetyCertificationPreparationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_code(value: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z][a-z0-9._-]*",
        value,
    ) is None:
        raise OperationalSafetyCertificationPreparationValidationError(
            "operational safety evidence code must use canonical lowercase syntax"
        )
    normalized = value.lower()
    if any(part in normalized for part in _SENSITIVE_PARTS):
        raise OperationalSafetyCertificationPreparationValidationError(
            "operational safety evidence code must not contain sensitive material"
        )
    return value


def _validate_account_fingerprint(value: str) -> str:
    if not isinstance(value, str) or fullmatch(r"sha256:[0-9a-f]{24}", value) is None:
        raise OperationalSafetyCertificationPreparationValidationError(
            "account fingerprint must be a truncated sha256 fingerprint"
        )
    return value


@dataclass(frozen=True, slots=True)
class OperationalSafetyPreparationRecord:
    check: OperationalSafetyPreparationCheck
    status: OperationalSafetyPreparationCheckStatus
    observed_at: datetime
    code: str
    evidence_refs: tuple[OperationalSafetyEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.check, OperationalSafetyPreparationCheck):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety record requires explicit check"
            )
        if not isinstance(self.status, OperationalSafetyPreparationCheckStatus):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety record requires explicit status"
            )
        _validate_timestamp(self.observed_at, field_name="record observed_at")
        object.__setattr__(self, "code", _validate_code(self.code))
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs:
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety record requires evidence refs"
            )
        if any(
            not isinstance(item, OperationalSafetyEvidenceRef)
            for item in self.evidence_refs
        ):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety evidence refs must use typed values"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.check.value,
            self.status.value,
            self.observed_at.isoformat(),
            self.code,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class OperationalSafetyCertificationPreparationEvidence:
    """Sanitized evidence package proving preparation only, never operational closure."""

    preparation_id: OperationalSafetyPreparationId
    provider_key: str
    environment: str
    account_fingerprint: str
    evaluated_at: datetime
    records: tuple[OperationalSafetyPreparationRecord, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.preparation_id, OperationalSafetyPreparationId):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety evidence requires preparation id"
            )
        if self.provider_key != "oanda-v20":
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety preparation provider must be oanda-v20"
            )
        if self.environment != "demo":
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety preparation environment must be demo"
            )
        object.__setattr__(
            self,
            "account_fingerprint",
            _validate_account_fingerprint(self.account_fingerprint),
        )
        _validate_timestamp(self.evaluated_at, field_name="evidence evaluated_at")
        if not isinstance(self.records, tuple):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety evidence records must be tuple"
            )
        if any(
            not isinstance(item, OperationalSafetyPreparationRecord)
            for item in self.records
        ):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety evidence records must use typed values"
            )
        checks = tuple(record.check for record in self.records)
        if checks != _REQUIRED_CHECKS:
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety evidence must contain every required check exactly once"
            )
        if any(record.observed_at > self.evaluated_at for record in self.records):
            raise OperationalSafetyCertificationPreparationValidationError(
                "operational safety record must not postdate evaluation"
            )

    @property
    def status(self) -> OperationalSafetyPreparationStatus:
        if all(
            record.status is OperationalSafetyPreparationCheckStatus.PASS
            for record in self.records
        ):
            return OperationalSafetyPreparationStatus.PREPARED
        return OperationalSafetyPreparationStatus.BLOCKED

    @property
    def operationally_certified(self) -> bool:
        """Preparation evidence can never close Gate #9 by itself."""
        return False

    def logical_values(self) -> tuple[object, ...]:
        return (
            _EVIDENCE_SCHEMA,
            self.preparation_id.logical_values(),
            self.status.value,
            self.provider_key,
            self.environment,
            self.account_fingerprint,
            self.evaluated_at.isoformat(),
            tuple(record.logical_values() for record in self.records),
            self.operationally_certified,
        )

    def public_payload(self) -> dict[str, object]:
        return {
            "schema": _EVIDENCE_SCHEMA,
            "status": self.status.value,
            "operationally_certified": False,
            "preparation_id": str(self.preparation_id.value),
            "provider": self.provider_key,
            "environment": self.environment,
            "account_fingerprint": self.account_fingerprint,
            "evaluated_at": self.evaluated_at.isoformat(),
            "records": [
                {
                    "check": record.check.value,
                    "status": record.status.value,
                    "observed_at": record.observed_at.isoformat(),
                    "code": record.code,
                    "evidence_refs": [item.value for item in record.evidence_refs],
                }
                for record in self.records
            ],
        }

    def to_json(self) -> str:
        return json.dumps(
            self.public_payload(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


def build_operational_safety_certification_preparation_evidence(
    preparation_id: OperationalSafetyPreparationId,
    records: tuple[OperationalSafetyPreparationRecord, ...],
    *,
    provider_key: str,
    environment: str,
    account_fingerprint: str,
    evaluated_at: datetime,
) -> Result[
    OperationalSafetyCertificationPreparationEvidence,
    OperationalSafetyCertificationPreparationError,
]:
    """Aggregate the exact fail-closed Gate #9 preparation matrix."""

    if not isinstance(records, tuple) or any(
        not isinstance(record, OperationalSafetyPreparationRecord)
        for record in records
    ):
        return Failure(
            OperationalSafetyCertificationPreparationValidationError(
                "operational safety preparation requires typed record tuple"
            )
        )
    by_check: dict[
        OperationalSafetyPreparationCheck,
        OperationalSafetyPreparationRecord,
    ] = {}
    for record in records:
        if record.check in by_check:
            return Failure(
                OperationalSafetyCertificationPreparationValidationError(
                    "duplicate operational safety preparation check is not allowed"
                )
            )
        by_check[record.check] = record
    if set(by_check) != set(_REQUIRED_CHECKS):
        return Failure(
            OperationalSafetyCertificationPreparationValidationError(
                "operational safety preparation evidence matrix is incomplete"
            )
        )
    ordered_records = tuple(by_check[check] for check in _REQUIRED_CHECKS)
    try:
        evidence = OperationalSafetyCertificationPreparationEvidence(
            preparation_id=preparation_id,
            provider_key=provider_key,
            environment=environment,
            account_fingerprint=account_fingerprint,
            evaluated_at=evaluated_at,
            records=ordered_records,
        )
    except OperationalSafetyCertificationPreparationError as error:
        return Failure(error)
    return Success(evidence)
