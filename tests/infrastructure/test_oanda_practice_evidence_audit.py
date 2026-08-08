from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.oanda_practice_evidence_audit import (
    OandaPracticeEvidenceAuditPolicy,
    OandaPracticeEvidenceAuditValidationError,
    audit_oanda_practice_operational_evidence,
)
from qore.infrastructure.oanda_practice_operational_probe import (
    OandaPracticeOperationalEvidence,
)
from qore.kernel.result import Failure, Success

_OBSERVED_AT = datetime(2026, 8, 8, 13, 0, tzinfo=UTC)
_AUDITED_AT = _OBSERVED_AT + timedelta(seconds=10)
_RUN_KEY = "31258480798-1"
_INSTRUMENT = "EUR_USD"
_FINGERPRINT = "sha256:0123456789abcdef01234567"


def _policy(
    *,
    run_key: str = _RUN_KEY,
    instrument: str = _INSTRUMENT,
    maximum_age_seconds: int = 60,
) -> OandaPracticeEvidenceAuditPolicy:
    return OandaPracticeEvidenceAuditPolicy(
        expected_run_key=run_key,
        expected_instrument=instrument,
        maximum_observation_age=timedelta(seconds=maximum_age_seconds),
    )


def _evidence() -> OandaPracticeOperationalEvidence:
    return OandaPracticeOperationalEvidence(
        run_key=_RUN_KEY,
        provider_key="oanda-v20",
        environment="demo",
        endpoint_host="api-fxpractice.oanda.com",
        account_fingerprint=_FINGERPRINT,
        instrument=_INSTRUMENT,
        snapshot_id=UUID("f1000000-0000-0000-0000-000000000001"),
        observed_at=_OBSERVED_AT,
        bid=1.1001,
        ask=1.1003,
    )


def _payload(**overrides: object) -> bytes:
    data = _evidence().public_payload()
    data.update(overrides)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def test_valid_probe_artifact_audits_deterministically() -> None:
    first = audit_oanda_practice_operational_evidence(
        _payload(),
        policy=_policy(),
        audited_at=_AUDITED_AT,
    )
    second = audit_oanda_practice_operational_evidence(
        _payload(),
        policy=_policy(),
        audited_at=_AUDITED_AT,
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.evidence.provider_key == "oanda-v20"
    assert first.value.evidence.environment == "demo"
    assert first.value.evidence.endpoint_host == "api-fxpractice.oanda.com"
    assert first.value.evidence.account_fingerprint == _FINGERPRINT
    assert first.value.evidence.instrument == _INSTRUMENT
    assert first.value.observation_age == timedelta(seconds=10)
    assert first.value.logical_values() == second.value.logical_values()


@pytest.mark.parametrize(
    "overrides",
    (
        {"schema": "unapproved.schema"},
        {"status": "failure"},
        {"run_key": "999-1"},
        {"instrument": "GBP_USD"},
        {"account_fingerprint": "101-001-1234567-001"},
        {"snapshot_id": "not-a-uuid"},
        {"observed_at": "2026-08-08T13:00:00"},
        {"provider_key": "other-provider"},
        {"environment": "production"},
        {"endpoint_host": "api-fxtrade.oanda.com"},
        {"bid": 1.2, "ask": 1.1},
    ),
)
def test_invalid_public_evidence_contract_fails_closed(
    overrides: dict[str, object],
) -> None:
    result = audit_oanda_practice_operational_evidence(
        _payload(**overrides),
        policy=_policy(),
        audited_at=_AUDITED_AT,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeEvidenceAuditValidationError)


def test_extra_fields_are_rejected_without_echoing_sensitive_content() -> None:
    sensitive_marker = "do-not-echo-practice-secret-material"
    data = _evidence().public_payload()
    data[sensitive_marker] = "value"
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    result = audit_oanda_practice_operational_evidence(
        payload,
        policy=_policy(),
        audited_at=_AUDITED_AT,
    )

    assert isinstance(result, Failure)
    assert sensitive_marker not in str(result.error)
    assert sensitive_marker not in repr(result.error)


def test_authorization_or_full_account_fields_cannot_enter_public_artifact() -> None:
    for forbidden_key in ("authorization", "account_id", "token"):
        data = _evidence().public_payload()
        data[forbidden_key] = "forbidden"
        payload = json.dumps(data, separators=(",", ":")).encode("utf-8")

        result = audit_oanda_practice_operational_evidence(
            payload,
            policy=_policy(),
            audited_at=_AUDITED_AT,
        )

        assert isinstance(result, Failure)
        assert isinstance(result.error, OandaPracticeEvidenceAuditValidationError)


def test_nonfinite_json_prices_are_rejected() -> None:
    payload = _payload().replace(b'"bid":1.1001', b'"bid":NaN')

    result = audit_oanda_practice_operational_evidence(
        payload,
        policy=_policy(),
        audited_at=_AUDITED_AT,
    )

    assert isinstance(result, Failure)
    assert isinstance(result.error, OandaPracticeEvidenceAuditValidationError)
    assert "strict UTF-8 JSON" in str(result.error)


def test_future_and_stale_evidence_are_rejected_by_explicit_audit_time() -> None:
    future = audit_oanda_practice_operational_evidence(
        _payload(observed_at=(_AUDITED_AT + timedelta(seconds=1)).isoformat()),
        policy=_policy(),
        audited_at=_AUDITED_AT,
    )
    stale = audit_oanda_practice_operational_evidence(
        _payload(observed_at=(_AUDITED_AT - timedelta(seconds=61)).isoformat()),
        policy=_policy(maximum_age_seconds=60),
        audited_at=_AUDITED_AT,
    )

    assert isinstance(future, Failure)
    assert "must not be in the future" in str(future.error)
    assert isinstance(stale, Failure)
    assert "older than audit policy" in str(stale.error)


def test_audit_policy_and_runtime_types_fail_closed() -> None:
    with pytest.raises(
        OandaPracticeEvidenceAuditValidationError,
        match="numeric syntax",
    ):
        _policy(run_key="manual")

    with pytest.raises(
        OandaPracticeEvidenceAuditValidationError,
        match="approved OANDA Practice symbol",
    ):
        _policy(instrument="USD_JPY")

    with pytest.raises(
        OandaPracticeEvidenceAuditValidationError,
        match="must be positive",
    ):
        _policy(maximum_age_seconds=0)

    wrong_policy = audit_oanda_practice_operational_evidence(
        _payload(),
        policy=cast(OandaPracticeEvidenceAuditPolicy, "not-a-policy"),
        audited_at=_AUDITED_AT,
    )
    naive_time = audit_oanda_practice_operational_evidence(
        _payload(),
        policy=_policy(),
        audited_at=datetime(2026, 8, 8, 13, 0),
    )

    assert isinstance(wrong_policy, Failure)
    assert isinstance(wrong_policy.error, OandaPracticeEvidenceAuditValidationError)
    assert isinstance(naive_time, Failure)
    assert isinstance(naive_time.error, OandaPracticeEvidenceAuditValidationError)
