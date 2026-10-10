"""Falsification checks for offline CISD full-window vs M1-prefix forensic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_a2_cisd_prefix_causality_v1 import (
    RouteWitness,
    aggregate,
    observe_route_pair,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)

START = datetime(2026, 5, 4, 10, tzinfo=UTC)


def _bar(i: int) -> CapitalizerM1Bar:
    t = START + timedelta(minutes=i)
    return CapitalizerM1Bar(
        symbol="EURUSD",
        opened_at=t,
        closed_at=t + timedelta(minutes=1),
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        volume=1,
        digits=5,
    )


def test_offline_pair_empty_signal_never_authorizes_execution() -> None:
    bars = tuple(_bar(i) for i in range(7))
    witness = observe_route_pair(
        bars,
        thesis_at=START,
        deadline_at=START + timedelta(minutes=7),
        direction=CapitalizerSourceDirection.BULLISH,
    )
    assert witness.first_at is None and witness.first_family is None
    assert witness.sweep_confirmed_at is None
    assert witness.fvg_cisd_confirmed_at is None
    assert not witness.authorizes_entry


def test_route_forensic_cannot_be_promoted_to_trading_authority() -> None:
    with pytest.raises(ValueError, match="cannot authorize"):
        RouteWitness(None, None, None, None, authorizes_entry=True)


def test_missing_any_nine_market_reports_is_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="9 distinct"):
        aggregate(tmp_path)
