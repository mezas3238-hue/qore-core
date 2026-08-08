from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from qore.infrastructure.oanda_practice_evidence_audit_cli import (
    audit_oanda_practice_evidence_file,
    main,
)
from qore.infrastructure.oanda_practice_operational_probe import (
    OandaPracticeOperationalEvidence,
)
from qore.kernel.result import Failure, Success

_RUN_KEY = "31259200391-1"
_INSTRUMENT = "EUR_USD"
_OBSERVED_AT = datetime(2026, 8, 8, 13, 20, tzinfo=UTC)
_AUDITED_AT = datetime(2026, 8, 8, 13, 20, 10, tzinfo=UTC)
_SENSITIVE_MARKER = "must-not-surface-from-audit-file"


def _evidence_payload() -> bytes:
    evidence = OandaPracticeOperationalEvidence(
        run_key=_RUN_KEY,
        provider_key="oanda-v20",
        environment="demo",
        endpoint_host="api-fxpractice.oanda.com",
        account_fingerprint="sha256:0123456789abcdef01234567",
        instrument=_INSTRUMENT,
        snapshot_id=UUID("f2000000-0000-0000-0000-000000000001"),
        observed_at=_OBSERVED_AT,
        bid=1.1001,
        ask=1.1003,
    )
    return f"{evidence.to_json()}\n".encode()


def _write(path: Path, payload: bytes | None = None) -> Path:
    path.write_bytes(_evidence_payload() if payload is None else payload)
    return path


def test_file_audit_accepts_exact_sanitized_probe_artifact(tmp_path: Path) -> None:
    path = _write(tmp_path / "evidence.json")

    result = audit_oanda_practice_evidence_file(
        path,
        expected_run_key=_RUN_KEY,
        expected_instrument=_INSTRUMENT,
        audited_at=_AUDITED_AT,
        maximum_observation_age_seconds=60,
    )

    assert isinstance(result, Success)
    assert result.value.evidence.run_key == _RUN_KEY
    assert result.value.evidence.instrument == _INSTRUMENT
    assert result.value.observation_age.total_seconds() == 10.0


def test_file_audit_rejects_extra_sensitive_field_without_echo(tmp_path: Path) -> None:
    data = json.loads(_evidence_payload())
    assert isinstance(data, dict)
    data[_SENSITIVE_MARKER] = "secret-value"
    path = _write(tmp_path / "evidence.json", json.dumps(data).encode())

    result = audit_oanda_practice_evidence_file(
        path,
        expected_run_key=_RUN_KEY,
        expected_instrument=_INSTRUMENT,
        audited_at=_AUDITED_AT,
        maximum_observation_age_seconds=60,
    )

    assert isinstance(result, Failure)
    assert _SENSITIVE_MARKER not in str(result.error)
    assert "secret-value" not in str(result.error)


def test_file_audit_rejects_missing_file_and_invalid_age_type(tmp_path: Path) -> None:
    missing = audit_oanda_practice_evidence_file(
        tmp_path / "missing.json",
        expected_run_key=_RUN_KEY,
        expected_instrument=_INSTRUMENT,
        audited_at=_AUDITED_AT,
        maximum_observation_age_seconds=60,
    )
    wrong_type = audit_oanda_practice_evidence_file(
        tmp_path / "missing.json",
        expected_run_key=_RUN_KEY,
        expected_instrument=_INSTRUMENT,
        audited_at=_AUDITED_AT,
        maximum_observation_age_seconds=cast(int, True),
    )
    non_positive = audit_oanda_practice_evidence_file(
        tmp_path / "missing.json",
        expected_run_key=_RUN_KEY,
        expected_instrument=_INSTRUMENT,
        audited_at=_AUDITED_AT,
        maximum_observation_age_seconds=0,
    )

    assert isinstance(missing, Failure)
    assert "could not be read" in str(missing.error)
    assert isinstance(wrong_type, Failure)
    assert "must be an int" in str(wrong_type.error)
    assert isinstance(non_positive, Failure)
    assert "must be positive" in str(non_positive.error)


def test_cli_accepts_artifact_and_prints_only_sanitized_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path / "evidence.json")

    exit_code = main(
        [
            "--evidence-file",
            str(path),
            "--expected-run-key",
            _RUN_KEY,
            "--expected-instrument",
            _INSTRUMENT,
            "--audited-at",
            _AUDITED_AT.isoformat(),
            "--maximum-observation-age-seconds",
            "60",
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "evidence audit accepted" in captured.out
    assert _RUN_KEY in captured.out
    assert _INSTRUMENT in captured.out
    assert "account_fingerprint" not in captured.out
    assert "authorization" not in captured.out


def test_cli_fails_closed_for_naive_audit_time(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path / "evidence.json")

    exit_code = main(
        [
            "--evidence-file",
            str(path),
            "--expected-run-key",
            _RUN_KEY,
            "--expected-instrument",
            _INSTRUMENT,
            "--audited-at",
            "2026-08-08T13:20:10",
            "--maximum-observation-age-seconds",
            "60",
        ]
    )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "timezone-aware" in captured.out
