from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from re import fullmatch
from typing import cast
from uuid import UUID

from qore.infrastructure.oanda_practice_operational_probe import (
    OandaPracticeOperationalEvidence,
)
from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success

_EVIDENCE_SCHEMA = "qore.oanda-practice.market-feed-evidence.v1"
_ALLOWED_INSTRUMENTS = ("EUR_USD", "GBP_USD")
_ALLOWED_KEYS = frozenset(
    {
        "account_fingerprint",
        "ask",
        "bid",
        "endpoint_host",
        "environment",
        "instrument",
        "observed_at",
        "provider_key",
        "run_key",
        "schema",
        "snapshot_id",
        "status",
    }
)


class OandaPracticeEvidenceAuditError(ExternalPortError):
    """Base error for deterministic audit of sanitized Practice evidence."""

    __slots__ = ()


class OandaPracticeEvidenceAuditValidationError(OandaPracticeEvidenceAuditError):
    """Operational evidence artifact violates the public audit contract."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise OandaPracticeEvidenceAuditValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise OandaPracticeEvidenceAuditValidationError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True, slots=True)
class OandaPracticeEvidenceAuditPolicy:
    """Explicit expectations for one future operational evidence artifact."""

    expected_run_key: str
    expected_instrument: str
    maximum_observation_age: timedelta

    def __post_init__(self) -> None:
        if not isinstance(self.expected_run_key, str) or fullmatch(
            r"[0-9]+-[0-9]+", self.expected_run_key
        ) is None:
            raise OandaPracticeEvidenceAuditValidationError(
                "expected_run_key must use '<run-id>-<attempt>' numeric syntax"
            )
        if self.expected_instrument not in _ALLOWED_INSTRUMENTS:
            raise OandaPracticeEvidenceAuditValidationError(
                "expected_instrument must be an approved OANDA Practice symbol"
            )
        if not isinstance(self.maximum_observation_age, timedelta):
            raise OandaPracticeEvidenceAuditValidationError(
                "maximum_observation_age must be a timedelta"
            )
        if self.maximum_observation_age <= timedelta(0):
            raise OandaPracticeEvidenceAuditValidationError(
                "maximum_observation_age must be positive"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.expected_run_key,
            self.expected_instrument,
            self.maximum_observation_age.total_seconds(),
        )


@dataclass(frozen=True, slots=True)
class OandaPracticeEvidenceAuditReport:
    """Typed acceptance of one sanitized artifact; not market-data certification."""

    policy: OandaPracticeEvidenceAuditPolicy
    evidence: OandaPracticeOperationalEvidence
    audited_at: datetime
    observation_age: timedelta

    def __post_init__(self) -> None:
        if not isinstance(self.policy, OandaPracticeEvidenceAuditPolicy):
            raise OandaPracticeEvidenceAuditValidationError(
                "audit report policy must be OandaPracticeEvidenceAuditPolicy"
            )
        if not isinstance(self.evidence, OandaPracticeOperationalEvidence):
            raise OandaPracticeEvidenceAuditValidationError(
                "audit report evidence must be OandaPracticeOperationalEvidence"
            )
        _validate_aware_datetime(self.audited_at, field_name="audit report audited_at")
        if not isinstance(self.observation_age, timedelta):
            raise OandaPracticeEvidenceAuditValidationError(
                "audit report observation_age must be timedelta"
            )
        if self.observation_age < timedelta(0):
            raise OandaPracticeEvidenceAuditValidationError(
                "audit report observation_age must not be negative"
            )
        if self.observation_age > self.policy.maximum_observation_age:
            raise OandaPracticeEvidenceAuditValidationError(
                "audit report observation_age exceeds policy"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.policy.logical_values(),
            self.evidence.run_key,
            self.evidence.provider_key,
            self.evidence.environment,
            self.evidence.endpoint_host,
            self.evidence.account_fingerprint,
            self.evidence.instrument,
            str(self.evidence.snapshot_id),
            self.evidence.observed_at.isoformat(),
            self.evidence.bid,
            self.evidence.ask,
            self.audited_at.isoformat(),
            self.observation_age.total_seconds(),
        )


def _reject_nonfinite_json_constant(_: str) -> object:
    raise ValueError("non-finite JSON constants are not permitted")


def _parse_artifact(payload: bytes) -> Result[dict[str, object], OandaPracticeEvidenceAuditError]:
    if not isinstance(payload, bytes) or not payload:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence artifact must be non-empty bytes"
            )
        )
    try:
        decoded: object = json.loads(
            payload.decode("utf-8"),
            parse_constant=_reject_nonfinite_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence artifact must be strict UTF-8 JSON"
            )
        )
    if not isinstance(decoded, dict) or any(not isinstance(key, str) for key in decoded):
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence artifact root must be a string-keyed object"
            )
        )
    return Success(cast(dict[str, object], decoded))


def _parse_observed_at(value: object) -> Result[datetime, OandaPracticeEvidenceAuditError]:
    if not isinstance(value, str) or not value:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence observed_at must be an ISO-8601 string"
            )
        )
    try:
        observed_at = datetime.fromisoformat(value)
        _validate_aware_datetime(observed_at, field_name="operational evidence observed_at")
    except ValueError:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence observed_at must be parseable and timezone-aware"
            )
        )
    except OandaPracticeEvidenceAuditError as error:
        return Failure(error)
    return Success(observed_at)


def _parse_snapshot_id(value: object) -> Result[UUID, OandaPracticeEvidenceAuditError]:
    if not isinstance(value, str) or not value:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence snapshot_id must be a UUID string"
            )
        )
    try:
        snapshot_id = UUID(value)
    except ValueError:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence snapshot_id must be a UUID string"
            )
        )
    return Success(snapshot_id)


def audit_oanda_practice_operational_evidence(
    payload: bytes,
    *,
    policy: OandaPracticeEvidenceAuditPolicy,
    audited_at: datetime,
) -> Result[OandaPracticeEvidenceAuditReport, OandaPracticeEvidenceAuditError]:
    """Audit one sanitized probe artifact without accepting arbitrary public fields."""

    if not isinstance(policy, OandaPracticeEvidenceAuditPolicy):
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence audit requires OandaPracticeEvidenceAuditPolicy"
            )
        )
    try:
        _validate_aware_datetime(audited_at, field_name="audited_at")
    except OandaPracticeEvidenceAuditError as error:
        return Failure(error)

    root = _parse_artifact(payload)
    if isinstance(root, Failure):
        return root
    data = root.value
    if frozenset(data) != _ALLOWED_KEYS:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence artifact must contain exactly the public schema keys"
            )
        )
    if data.get("schema") != _EVIDENCE_SCHEMA:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence artifact schema is not approved"
            )
        )
    if data.get("status") != "success":
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence artifact status must be success"
            )
        )
    if data.get("run_key") != policy.expected_run_key:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence run_key must match the audited workflow run"
            )
        )
    if data.get("instrument") != policy.expected_instrument:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence instrument must match audit policy"
            )
        )
    account_fingerprint = data.get("account_fingerprint")
    if not isinstance(account_fingerprint, str) or fullmatch(
        r"sha256:[0-9a-f]{24}", account_fingerprint
    ) is None:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence account fingerprint must be sanitized"
            )
        )

    snapshot_id = _parse_snapshot_id(data.get("snapshot_id"))
    if isinstance(snapshot_id, Failure):
        return snapshot_id
    observed_at = _parse_observed_at(data.get("observed_at"))
    if isinstance(observed_at, Failure):
        return observed_at

    bid = data.get("bid")
    ask = data.get("ask")
    if type(bid) is not float or type(ask) is not float:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence bid and ask must be JSON floating-point numbers"
            )
        )
    if not isfinite(bid) or not isfinite(ask):
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence prices must be finite"
            )
        )

    try:
        evidence = OandaPracticeOperationalEvidence(
            run_key=policy.expected_run_key,
            provider_key=cast(str, data.get("provider_key")),
            environment=cast(str, data.get("environment")),
            endpoint_host=cast(str, data.get("endpoint_host")),
            account_fingerprint=account_fingerprint,
            instrument=policy.expected_instrument,
            snapshot_id=snapshot_id.value,
            observed_at=observed_at.value,
            bid=bid,
            ask=ask,
        )
    except ExternalPortError:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence violates the canonical Practice evidence contract"
            )
        )

    observation_age = audited_at - evidence.observed_at
    if observation_age < timedelta(0):
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence observed_at must not be in the future"
            )
        )
    if observation_age > policy.maximum_observation_age:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence is older than audit policy permits"
            )
        )
    try:
        report = OandaPracticeEvidenceAuditReport(
            policy=policy,
            evidence=evidence,
            audited_at=audited_at,
            observation_age=observation_age,
        )
    except OandaPracticeEvidenceAuditError as error:
        return Failure(error)
    return Success(report)
