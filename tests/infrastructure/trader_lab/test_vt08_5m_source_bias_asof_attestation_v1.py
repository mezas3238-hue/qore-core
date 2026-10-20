"""Synthetic independent as-of checks for M15-reconstructed source bias."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from qore.infrastructure.trader_lab.vt08_5m_source_bias_asof_attestation_v1 import (
    _day_proof,
    attest_bias,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

NY = ZoneInfo("America/New_York")


def source_data() -> tuple[dict[datetime, Vt08B01Bar], datetime]:
    t = datetime(2026, 1, 5, 17, tzinfo=NY).astimezone(UTC)
    rows: dict[datetime, Vt08B01Bar] = {}
    for i in range(2 * 96):
        s = t + timedelta(minutes=15 * i)
        p = Decimal("100") if i < 96 else Decimal("101")
        rows[s] = Vt08B01Bar(
            opened_at=s,
            closed_at=s + timedelta(minutes=15),
            open=p,
            high=p + Decimal("0.25"),
            low=p - Decimal("0.25"),
            close=p,
        )
    decision = datetime(2026, 1, 8, 1, tzinfo=NY).astimezone(UTC)
    return rows, decision


def test_bias_cutoff_is_actual_closed_day_not_decision_time() -> None:
    rows, decision = source_data()
    proof = attest_bias(rows, decision_at=decision)
    assert proof is not None
    assert proof.bias is DemoTradingSetupSide.LONG
    assert proof.current_day.m15_count == 96
    assert proof.previous_day.m15_count == 96
    assert proof.payload()["bias_feature_cutoff"] == (
        datetime(2026, 1, 7, 17, tzinfo=NY).astimezone(UTC).isoformat()
    )
    assert proof.current_day.day.closed_at < decision


def test_future_bars_cannot_change_previous_day_bias_proof() -> None:
    rows, decision = source_data()
    original = attest_bias(rows, decision_at=decision)
    assert original is not None
    future = replace(
        next(iter(rows.values())),
        opened_at=decision,
        closed_at=decision + timedelta(minutes=15),
        open=Decimal("1000"),
        high=Decimal("1000"),
        low=Decimal("1000"),
        close=Decimal("1000"),
    )
    assert future.opened_at not in rows
    rows[future.opened_at] = future
    updated = attest_bias(rows, decision_at=decision)
    assert updated is not None
    assert updated.payload() == original.payload()


def test_mutating_actual_constituent_bar_mutates_hash() -> None:
    rows, decision = source_data()
    original = attest_bias(rows, decision_at=decision)
    assert original is not None
    t = datetime(2026, 1, 7, 16, 45, tzinfo=NY).astimezone(UTC)
    rows[t] = replace(
        rows[t],
        high=Decimal("103"),
    )
    altered = attest_bias(rows, decision_at=decision)
    assert altered is not None
    assert (
        altered.current_day.m15_sha256
        != original.current_day.m15_sha256
    )


def test_missing_one_15m_bar_means_no_full_provenance() -> None:
    rows, decision = source_data()
    t = datetime(2026, 1, 7, 15, 45, tzinfo=NY).astimezone(UTC)
    rows.pop(t)
    assert attest_bias(rows, decision_at=decision) is None


def test_no_future_source_day_at_midnight() -> None:
    rows, _ = source_data()
    decision = datetime(2026, 1, 7, 1, tzinfo=NY).astimezone(UTC)
    assert attest_bias(rows, decision_at=decision) is None


def test_individual_source_day_unavailable_before_close() -> None:
    rows, _ = source_data()
    proof = _day_proof(
        rows,
        end_date=datetime(2026, 1, 7, tzinfo=NY).date(),
        as_of=datetime(2026, 1, 7, 15, tzinfo=NY).astimezone(UTC),
    )
    assert proof is None


def test_naive_decision_fails_closed() -> None:
    rows, _ = source_data()
    with pytest.raises(ValueError, match="timezone"):
        attest_bias(rows, decision_at=datetime(2026, 1, 8, 1))
