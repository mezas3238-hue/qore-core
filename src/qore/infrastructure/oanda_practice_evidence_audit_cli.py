from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

from qore.infrastructure.oanda_practice_evidence_audit import (
    OandaPracticeEvidenceAuditError,
    OandaPracticeEvidenceAuditPolicy,
    OandaPracticeEvidenceAuditReport,
    OandaPracticeEvidenceAuditValidationError,
    audit_oanda_practice_operational_evidence,
)
from qore.kernel.result import Failure, Result


def audit_oanda_practice_evidence_file(
    path: Path,
    *,
    expected_run_key: str,
    expected_instrument: str,
    audited_at: datetime,
    maximum_observation_age_seconds: int,
) -> Result[OandaPracticeEvidenceAuditReport, OandaPracticeEvidenceAuditError]:
    """Audit one local sanitized artifact using explicit workflow expectations."""

    if not isinstance(path, Path):
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence path must be a Path"
            )
        )
    if type(maximum_observation_age_seconds) is not int:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "maximum observation age seconds must be an int"
            )
        )
    if maximum_observation_age_seconds <= 0:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "maximum observation age seconds must be positive"
            )
        )
    try:
        payload = path.read_bytes()
    except OSError:
        return Failure(
            OandaPracticeEvidenceAuditValidationError(
                "operational evidence artifact file could not be read"
            )
        )
    try:
        policy = OandaPracticeEvidenceAuditPolicy(
            expected_run_key=expected_run_key,
            expected_instrument=expected_instrument,
            maximum_observation_age=timedelta(
                seconds=maximum_observation_age_seconds
            ),
        )
    except OandaPracticeEvidenceAuditError as error:
        return Failure(error)
    return audit_oanda_practice_operational_evidence(
        payload,
        policy=policy,
        audited_at=audited_at,
    )


def _parse_audited_at(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise OandaPracticeEvidenceAuditValidationError(
            "audited_at must be ISO-8601"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OandaPracticeEvidenceAuditValidationError(
            "audited_at must be timezone-aware"
        )
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit one sanitized QORE OANDA Practice probe artifact."
    )
    parser.add_argument("--evidence-file", required=True)
    parser.add_argument("--expected-run-key", required=True)
    parser.add_argument("--expected-instrument", required=True)
    parser.add_argument("--audited-at", required=True)
    parser.add_argument(
        "--maximum-observation-age-seconds",
        required=True,
        type=int,
    )
    args = parser.parse_args(argv)
    try:
        audited_at = _parse_audited_at(args.audited_at)
        result = audit_oanda_practice_evidence_file(
            Path(args.evidence_file),
            expected_run_key=args.expected_run_key,
            expected_instrument=args.expected_instrument,
            audited_at=audited_at,
            maximum_observation_age_seconds=args.maximum_observation_age_seconds,
        )
        if isinstance(result, Failure):
            print(
                "QORE OANDA Practice evidence audit failed: "
                f"{type(result.error).__name__}: {result.error}"
            )
            return 1
        print(
            "QORE OANDA Practice evidence audit accepted: "
            f"run_key={result.value.evidence.run_key} "
            f"instrument={result.value.evidence.instrument} "
            f"observation_age_seconds={result.value.observation_age.total_seconds()}"
        )
        return 0
    except OandaPracticeEvidenceAuditError as error:
        print(
            "QORE OANDA Practice evidence audit blocked: "
            f"{type(error).__name__}: {error}"
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
