from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_preentry_cross_market_event_time_state_v42 as v42,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)


def _bar(symbol: str, closed_at: datetime) -> CapitalizerM1Bar:
    return CapitalizerM1Bar(
        symbol=symbol,
        opened_at=closed_at - timedelta(minutes=1),
        closed_at=closed_at,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=1,
        digits=2,
    )


def _snapshot(
    peer_symbol: str,
    *,
    candidate_symbol: str = "USDJPY",
    candidate_side: str = "LONG",
    available: bool = True,
    body: str = "0.5",
) -> v42.PeerEventSnapshot:
    return v42.PeerEventSnapshot(
        period="DEVELOPMENT_2024_2026",
        candidate_symbol=candidate_symbol,
        candidate_side=candidate_side,
        entry_at="2024-01-01T12:00:00+00:00",
        peer_symbol=peer_symbol,
        available=available,
        age_seconds=0 if available else 3600,
        signed_body_fraction=body if available else None,
        range_fraction="0.001" if available else None,
        wick_skew="0.1" if available else None,
    )


def test_snapshot_accepts_exact_one_minute_freshness() -> None:
    entry = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    bar = _bar("EURUSD", entry - timedelta(seconds=60))

    row = v42._snapshot_for_entry(
        period="DEVELOPMENT_2024_2026",
        candidate_symbol="USDJPY",
        candidate_side="LONG",
        entry_at=entry,
        peer_symbol="EURUSD",
        bars=(bar,),
        closed_times=(bar.closed_at,),
    )

    assert row.available is True
    assert row.age_seconds == 60
    assert row.signed_body_fraction is not None


def test_snapshot_excludes_stale_peer_without_imputation() -> None:
    entry = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    bar = _bar("XAUUSD", entry - timedelta(seconds=61))

    row = v42._snapshot_for_entry(
        period="DEVELOPMENT_2024_2026",
        candidate_symbol="USDJPY",
        candidate_side="LONG",
        entry_at=entry,
        peer_symbol="XAUUSD",
        bars=(bar,),
        closed_times=(bar.closed_at,),
    )

    assert row.available is False
    assert row.age_seconds == 61
    assert row.signed_body_fraction is None
    assert row.range_fraction is None
    assert row.wick_skew is None


def test_set_state_excludes_candidate_market_and_counts_stale_peer() -> None:
    rows = tuple(
        _snapshot(
            symbol,
            available=symbol != "XAUUSD",
            body="0.5",
        )
        for symbol in (
            "USDJPY",
            "AUDJPY",
            "AUDUSD",
            "GBPJPY",
            "EURUSD",
            "GBPUSD",
            "XAUUSD",
            "USDCAD",
            "NAS100",
        )
    )

    state = v42._build_set_state(
        period="DEVELOPMENT_2024_2026",
        symbol="USDJPY",
        side="LONG",
        entry_at="2024-01-01T12:00:00+00:00",
        snapshots=rows,
    )

    assert state.feature_count == 18
    assert len(state.vector) == 18
    assert state.available_peer_count == 7
    assert state.stale_peer_count == 1
    assert Decimal(state.vector[0]) == Decimal("0.875")
    assert state.candidate_market_excluded is True
    assert state.stale_peer_prices_excluded is True


def test_factor_alignment_contains_support_and_conflict_without_identity_bits() -> None:
    bodies = {
        "USDJPY": "0.9",
        "AUDJPY": "0.8",
        "AUDUSD": "0.6",
        "GBPJPY": "0.5",
        "EURUSD": "0.4",
        "GBPUSD": "0.7",
        "XAUUSD": "0.3",
        "USDCAD": "0.2",
        "NAS100": "0.1",
    }
    rows = tuple(_snapshot(symbol, body=bodies[symbol]) for symbol in bodies)

    state = v42._build_set_state(
        period="DEVELOPMENT_2024_2026",
        symbol="USDJPY",
        side="LONG",
        entry_at="2024-01-01T12:00:00+00:00",
        snapshots=rows,
    )

    support_fraction = Decimal(state.vector[11])
    conflict_fraction = Decimal(state.vector[12])
    assert support_fraction > 0
    assert conflict_fraction > 0
    assert state.symbol_identity_in_vector is False
    assert state.peer_symbol_identity_bits_in_vector is False
