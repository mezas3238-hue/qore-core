"""Online first-CISD must not backdate a late-discovered witness."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_thirteenth_cisd_stream_pairs_v1 as forensic,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_a2_cisd_prefix_causality_v1 import (
    RouteWitness,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceDirection,
)


def _bars(n: int) -> tuple[CapitalizerM1Bar, ...]:
    base = datetime(2026, 1, 10, 10, tzinfo=UTC)
    return tuple(
        CapitalizerM1Bar(
            symbol="EURUSD", opened_at=base+timedelta(minutes=i),
            closed_at=base+timedelta(minutes=i+1),
            open=Decimal("1.10"),high=Decimal("1.12"),
            low=Decimal("1.08"),close=Decimal("1.11"),
            volume=None,digits=5,
        )
        for i in range(n)
    )


def test_first_online_witness_is_never_backdated() -> None:
    bars=_bars(3)
    start=bars[0].opened_at
    evidence=RouteWitness(
        first_family="LIQUIDITY_SWEEP_CISD",
        first_at=bars[0].closed_at.isoformat(),
        sweep_confirmed_at=bars[0].closed_at.isoformat(),
        fvg_cisd_confirmed_at=None,
    )
    missing=RouteWitness(None,None,None,None)
    with patch.object(
        forensic,"observe_route_pair",side_effect=[missing,missing,evidence]
    ):
        row=forensic.stream_first(
            bars,thesis_at=start,direction=CapitalizerSourceDirection.BULLISH
        )
    assert row is not None
    assert row["detected_at"]==bars[2].closed_at.isoformat()
    assert row["witness_confirmed_at"]==bars[0].closed_at.isoformat()
    assert row["late_witness_discovery"]=="true"


def test_causal_online_does_not_observe_future() -> None:
    bars=_bars(1)
    future=RouteWitness(
        first_family="FVG_RETRACE_CISD",
        first_at=(bars[0].closed_at+timedelta(minutes=1)).isoformat(),
        sweep_confirmed_at=None,fvg_cisd_confirmed_at=None,
    )
    with patch.object(forensic,"observe_route_pair",return_value=future):
        with pytest.raises(ValueError,match="unseen future"):
            forensic.stream_first(
                bars,thesis_at=bars[0].opened_at,
                direction=CapitalizerSourceDirection.BULLISH,
            )


def test_label_uses_full_consecutive_closed_minutes_not_partial() -> None:
    bars=_bars(61)
    closed=tuple(x.closed_at for x in bars)
    valid=forensic.post_entry_labels(
        bars,closed,at=bars[0].closed_at,
        direction="BULLISH",original_risk_price=Decimal("0.10"),minutes=15,
    )
    assert valid["covered"] and not valid["positive"]
    assert valid["mfe_observed_r"]=="0.1"
    assert valid["risk_reference_is_original_v49_not_new_trade"]
    assert not forensic.post_entry_labels(
        bars,closed,at=bars[55].closed_at,
        direction="BULLISH",original_risk_price=Decimal("0.10"),minutes=15,
    )["covered"]


def test_closed_prefix_and_nine_market_denominator_fail_closed(tmp_path:Path) -> None:
    with pytest.raises(ValueError,match="nine markets"):
        forensic.aggregate(tmp_path)
    bars=_bars(1)
    with pytest.raises(ValueError,match="after M15 thesis"):
        forensic.stream_first(
            bars,thesis_at=bars[0].closed_at,
            direction=CapitalizerSourceDirection.BULLISH,
        )
