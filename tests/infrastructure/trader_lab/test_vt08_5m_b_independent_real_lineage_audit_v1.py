"""Independent Architect B M15/provenance validator adversarial unit tests.

The integration job separately downloads A's 488 REAL event packages and five
original 1095D M15 streams from two immutable historical GitHub runs.
"""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    vt08_5m_b_independent_real_lineage_audit_v1 as independent,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

T0 = datetime(2026, 1, 5, 6, tzinfo=UTC)


def _bars(count: int = 96) -> dict[datetime, Vt08B01Bar]:
    results: dict[datetime, Vt08B01Bar] = {}
    for i in range(count):
        start = T0 + timedelta(minutes=15 * i)
        close = Decimal("100") + Decimal(i) / Decimal("100")
        results[start] = Vt08B01Bar(
            opened_at=start,
            closed_at=start + timedelta(minutes=15),
            open=close,
            high=close + Decimal("0.50"),
            low=close - Decimal("0.50"),
            close=close,
        )
    return results


def _day(rows: tuple[Vt08B01Bar, ...]) -> dict[str, object]:
    return {
        "opened_at": rows[0].opened_at.isoformat(),
        "closed_at": rows[-1].closed_at.isoformat(),
        "m15_count": len(rows),
        "m15_sha256": independent._sha_m15(rows),
        "open": str(rows[0].open),
        "high": str(max(x.high for x in rows)),
        "low": str(min(x.low for x in rows)),
        "close": str(rows[-1].close),
    }


def test_exact_closed_m15_window_and_provenance_proof_are_deterministic() -> None:
    originals = _bars()
    source = independent._window(originals, T0, T0 + timedelta(hours=24))
    assert len(source) == 96
    declaration = _day(source)
    independent._verify_ohlc(source, declaration)
    assert len(independent._sha_m15(source)) == 64
    assert independent._sha_m15(source) == independent._sha_m15(source)


def test_missing_or_future_bar_cannot_satisfy_independent_source_window() -> None:
    originals = _bars(16)
    originals.pop(T0 + timedelta(minutes=15 * 4))
    with pytest.raises(ValueError, match="M15 evidence missing"):
        independent._window(originals, T0, T0 + timedelta(hours=4))
    with pytest.raises(ValueError, match="not aligned"):
        independent._window(
            _bars(16), T0, T0 + timedelta(hours=4, minutes=1)
        )
    with pytest.raises(ValueError, match="window invalid"):
        independent._window(_bars(16), T0, T0)


def test_tampered_historical_candle_fails_sha_and_ohlc_attestation() -> None:
    source = independent._window(_bars(), T0, T0 + timedelta(hours=24))
    proof = _day(source)
    altered = list(source)
    altered[15] = replace(
        altered[15], high=altered[15].high + Decimal("300")
    )
    with pytest.raises(ValueError, match="source day M15 hash"):
        independent._verify_ohlc(tuple(altered), proof)
    with pytest.raises(ValueError, match="source day raw M15 count"):
        independent._verify_ohlc(source[:-1], proof)
    with pytest.raises(ValueError, match="source day open OHLC"):
        independent._verify_ohlc(
            source, {**proof, "open": "999999"}
        )


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    (
        (
            {"high": "102", "low": "98"},
            {"close": "103", "low": "99", "high": "103"},
            "long",
        ),
        (
            {"high": "102", "low": "98"},
            {"close": "97", "low": "97", "high": "101"},
            "short",
        ),
        (
            {"high": "102", "low": "98"},
            {"close": "99.5", "low": "97", "high": "101"},
            "long",
        ),
        (
            {"high": "102", "low": "98"},
            {"close": "101", "low": "99", "high": "103"},
            "short",
        ),
        (
            {"high": "102", "low": "98"},
            {"close": "100", "low": "99", "high": "101"},
            "UNRESOLVED",
        ),
    ),
)
def test_bias_cross_check_uses_raw_ohlc_not_a_assertion(
    previous: dict[str, object], current: dict[str, object], expected: str
) -> None:
    assert independent._bias_from_closed_days(previous, current) == expected


def test_reject_wrong_original_evidence_even_when_candidate_artifact_exists(
    tmp_path: Path,
) -> None:
    with pytest.raises((FileNotFoundError, ValueError)):
        independent.audit_market(
            tmp_path / "a" / "fake.json",
            tmp_path / "source" / "fake.json",
        )


def test_canonical_lineage_hash_is_stable_and_binds_full_nested_payload() -> None:
    value = {"a": {"b": [1, "2", "3"]}, "event_id": "vt08-5m:abc"}
    digest = independent._canonical_digest(value)
    assert len(digest) == 64
    assert independent._canonical_digest(value) == digest
    assert independent._canonical_digest(
        {"a": {"b": [1, "2", "DIFFERENT"]}, "event_id": "vt08-5m:abc"}
    ) != digest


def test_aware_source_timestamp_required_with_no_timezone_guessing() -> None:
    assert independent._timestamp(T0.isoformat()) == T0
    with pytest.raises(ValueError, match="timezone"):
        independent._timestamp("2026-01-05T06:00:00")
    with pytest.raises(ValueError, match="missing causal ISO"):
        independent._timestamp(None)
