from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_preentry_provider_quote_microstructure_v41 as v41,
)


@dataclass(frozen=True)
class Tick:
    timestamp: int
    tick: int


def _raw(
    target: datetime,
    *,
    absolute: int,
) -> tuple[Tick, ...]:
    return (
        Tick(int((target - timedelta(seconds=1)).timestamp() * 1000), absolute),
        Tick(-1000, -10),
        Tick(-1000, 5),
        Tick(-1000, 5),
    )


def test_decode_provider_ticks_cumulatively_and_chronologically() -> None:
    target = datetime(2023, 10, 2, 15, 0, tzinfo=UTC)
    rows = v41.decode_tick_stream(
        _raw(target, absolute=100000),
        target_at=target,
        digits=5,
        quote_name="BID",
        has_more=False,
    )

    assert [row.observed_at for row in rows] == [
        target - timedelta(seconds=4),
        target - timedelta(seconds=3),
        target - timedelta(seconds=2),
        target - timedelta(seconds=1),
    ]
    assert [row.price for row in rows] == [
        Decimal("1.00000"),
        Decimal("0.99995"),
        Decimal("0.99990"),
        Decimal("1.00000"),
    ]


def test_decode_rejects_truncated_response() -> None:
    target = datetime(2023, 10, 2, 15, 0, tzinfo=UTC)
    with pytest.raises(ValueError, match="truncated"):
        v41.decode_tick_stream(
            _raw(target, absolute=100000),
            target_at=target,
            digits=5,
            quote_name="BID",
            has_more=True,
        )


def test_build_state_is_frozen_18d_and_causal() -> None:
    target = datetime(2023, 10, 2, 15, 0, tzinfo=UTC)
    row = v41.build_state(
        symbol="EURUSD",
        side="LONG",
        entry_at=target,
        structural_risk_price=Decimal("0.00100"),
        bid_ticks=_raw(target, absolute=100000),
        ask_ticks=_raw(target, absolute=100020),
        digits=5,
        bid_has_more=False,
        ask_has_more=False,
    )

    assert row.feature_names == v41.FEATURE_NAMES
    assert row.feature_count == len(v41.FEATURE_NAMES) == 18
    assert row.bid_tick_count == 4
    assert row.ask_tick_count == 4
    assert Decimal(row.vector[14]) == Decimal("0.2")
    assert row.provider_native is True
    assert row.future_quote_used is False
    assert row.interpolation_used is False
    assert row.synthetic_quote_used is False
    assert row.outcome_used is False
    assert row.exit_used is False
    assert row.mae_mfe_used is False


def test_json_roundtrip_restores_tuple_contract() -> None:
    target = datetime(2023, 10, 2, 15, 0, tzinfo=UTC)
    row = v41.build_state(
        symbol="EURUSD",
        side="SHORT",
        entry_at=target,
        structural_risk_price=Decimal("0.00100"),
        bid_ticks=_raw(target, absolute=100000),
        ask_ticks=_raw(target, absolute=100020),
        digits=5,
        bid_has_more=False,
        ask_has_more=False,
    )
    payload = json.loads(json.dumps(asdict(row)))

    assert v41.from_json_dict(payload) == row
