from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from qore.infrastructure.trader_lab.chronological_holdout import (
    ChronologicalHoldoutError,
    partition_tail_days,
)


def _evidence(days: int = 760) -> dict[str, object]:
    start = datetime(2024, 8, 1, tzinfo=UTC)
    periods: dict[str, list[dict[str, object]]] = {}
    coverage: dict[str, object] = {}
    for period in ("M1", "M5", "M15", "H4"):
        rows: list[dict[str, object]] = []
        for index in range(days):
            opened = start + timedelta(days=index)
            closed = opened + timedelta(days=1)
            rows.append(
                {
                    "period": period,
                    "opened_at": opened.isoformat(timespec="microseconds"),
                    "closed_at": closed.isoformat(timespec="microseconds"),
                    "open": "1",
                    "high": "2",
                    "low": "0.5",
                    "close": "1.5",
                }
            )
        periods[period] = rows
        coverage[period] = {
            "bar_count": len(rows),
            "first_opened_at": rows[0]["opened_at"],
            "last_closed_at": rows[-1]["closed_at"],
            "maximum_observed_gap_seconds": 0,
            "observed_gap_count": 0,
            "observed_gap_seconds": 0,
            "span_days": days,
            "span_seconds": days * 86_400,
            "gap_policy": "fixture",
        }
    return {
        "schema": "qore.ctrader_demo.lab_market_evidence.v1",
        "environment": "demo",
        "read_only": True,
        "account_is_live": False,
        "trading_permission_verified": True,
        "account_fingerprint": "a" * 64,
        "checked_at": (start + timedelta(days=days)).isoformat(),
        "software_sha": "b" * 40,
        "symbol": {"symbol_name": "US30"},
        "requested_lookback_days": days,
        "required_coverage_days": 730,
        "periods": periods,
        "coverage": coverage,
    }


def test_tail_holdout_is_exhaustive_disjoint_and_keeps_730_day_development() -> None:
    raw = _evidence()
    development, holdout, manifest = partition_tail_days(raw, holdout_days=28)

    assert development["partition_role"] == "DEVELOPMENT"
    assert holdout["partition_role"] == "UNTOUCHED_HOLDOUT"
    assert holdout["holdout_consumption_prohibited"] is True
    assert manifest["development_may_consume_holdout"] is False
    for period in ("M1", "M5", "M15", "H4"):
        raw_periods = cast(dict[str, list[dict[str, object]]], raw["periods"])
        dev_periods = cast(
            dict[str, list[dict[str, object]]], development["periods"]
        )
        hold_periods = cast(
            dict[str, list[dict[str, object]]], holdout["periods"]
        )
        original = raw_periods[period]
        dev = dev_periods[period]
        sealed = hold_periods[period]
        assert len(dev) + len(sealed) == len(original)
        dev_coverage = cast(
            dict[str, dict[str, object]], development["coverage"]
        )
        assert cast(int, dev_coverage[period]["span_seconds"]) >= 730 * 86_400
        assert sealed
        dev_last_closed_at = dev[-1]["closed_at"]
        sealed_first_closed_at = sealed[0]["closed_at"]
        cutoff = manifest["cutoff"]
        assert isinstance(dev_last_closed_at, str)
        assert isinstance(sealed_first_closed_at, str)
        assert isinstance(cutoff, str)
        assert dev_last_closed_at <= cutoff
        assert sealed_first_closed_at > cutoff


def test_rejects_holdout_that_would_shrink_development_below_730_days() -> None:
    raw = _evidence(days=759)
    with pytest.raises(ChronologicalHoldoutError, match="less than 730 calendar days"):
        partition_tail_days(raw, holdout_days=30)


def test_policy_fingerprint_is_deterministic() -> None:
    raw = _evidence()
    first = partition_tail_days(raw, holdout_days=28)[2]
    second = partition_tail_days(raw, holdout_days=28)[2]
    assert first["policy_fingerprint"] == second["policy_fingerprint"]
    assert first["development_evidence_sha256"] == second[
        "development_evidence_sha256"
    ]
    assert first["holdout_evidence_sha256"] == second["holdout_evidence_sha256"]
