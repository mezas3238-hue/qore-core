import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import CapitalizerM1Bar
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_generic_scalp_census_v48 import (
    IDENTITY,
    MATRIX_IDENTITY,
    _aggregate,
    build_matrix,
)


def _bar(minute: int) -> CapitalizerM1Bar:
    opened = datetime(2026, 1, 2, 10, 0, tzinfo=UTC) + timedelta(minutes=minute)
    base = Decimal("100") + Decimal(minute) / Decimal("100")
    return CapitalizerM1Bar(
        symbol="XAUUSD",
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=base,
        high=base + Decimal("0.05"),
        low=base - Decimal("0.05"),
        close=base + Decimal("0.01"),
        volume=1,
        digits=2,
    )


def test_m15_and_h1_aggregation_use_safe_intraday_boundaries_only() -> None:
    bars = tuple(_bar(i) for i in range(60))
    m15 = _aggregate(bars, minutes=15)
    h1 = _aggregate(bars, minutes=60)
    assert len(m15) == 4
    assert len(h1) == 1
    assert h1[0].minute_count == 60


def test_generic_scalp_aggregation_rejects_unbound_h4() -> None:
    bars = tuple(_bar(i) for i in range(60))
    try:
        _aggregate(bars, minutes=240)
    except ValueError as exc:
        assert "M15/H1" in str(exc)
    else:
        raise AssertionError("unbound H4 aggregation must fail closed")


def _market_payload(symbol: str, session: str, count: int) -> dict[str, object]:
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "source_complete_opportunities": count,
        "max3_chronological_selected": count,
    }


def _write_market(
    root: Path,
    *,
    symbol: str,
    session: str,
    count: int,
) -> None:
    report = root / f"capitalizer-{symbol.lower()}-v48-scalp-pre-economic-census.json"
    report.write_text(
        json.dumps(_market_payload(symbol, session, count)),
        encoding="utf-8",
    )
    ledger = root / (
        f"capitalizer-{symbol.lower()}-v48-scalp-pre-economic-census-opportunities.jsonl"
    )
    with ledger.open("w", encoding="utf-8") as handle:
        for index in range(count):
            at = datetime(2026, 1, 2, 12, index, tzinfo=UTC).isoformat()
            handle.write(
                json.dumps(
                    {
                        "symbol": symbol,
                        "session": session,
                        "operating_date": "2026-01-02",
                        "direction": "BULLISH",
                        "h1_bias_confirmed_at": at,
                        "h1_closure_kind": "CANDLE2_REVERSAL",
                        "h1_poi_kind": "SWING_LOW",
                        "m15_cisd_confirmed_at": at,
                        "m15_protected_swing_price": "99",
                        "m1_continuation_confirmed_at": at,
                        "m1_continuation_family": "LIQUIDITY_SWEEP_CISD",
                        "decision_reference_price": "100",
                        "structural_target_witness_price": "101",
                    }
                )
                + "\n"
            )


def test_matrix_requires_nine_markets_and_reports_three_session_coverage(tmp_path: Path) -> None:
    rows = (
        ("USDJPY", "ASIA", 2),
        ("AUDJPY", "ASIA", 0),
        ("AUDUSD", "ASIA", 1),
        ("GBPJPY", "ASIA", 0),
        ("EURUSD", "LONDON", 1),
        ("GBPUSD", "LONDON", 1),
        ("XAUUSD", "NEW_YORK", 1),
        ("USDCAD", "NEW_YORK", 0),
        ("NAS100", "NEW_YORK", 2),
    )
    for symbol, session, count in rows:
        _write_market(tmp_path, symbol=symbol, session=session, count=count)

    report = build_matrix(tmp_path)
    assert report["identity"] == MATRIX_IDENTITY
    assert report["market_count"] == 9
    assert report["session_count"] == 3
    assert report["coverage_decision"] == "COMPLETE_PRE_ECONOMIC"
    assert report["by_session"] == {"ASIA": 3, "LONDON": 2, "NEW_YORK": 3}
    assert report["portfolio_max3_chronological_selected"] == 8
    assert report["outcome_used"] is False
    assert report["economics_calculated"] is False
    assert report["census_is_lower_bound"] is True
    assert report["h4_routes_included"] is False


def test_matrix_fails_session_operability_when_one_session_is_empty(tmp_path: Path) -> None:
    rows = (
        ("USDJPY", "ASIA", 2),
        ("AUDJPY", "ASIA", 0),
        ("AUDUSD", "ASIA", 1),
        ("GBPJPY", "ASIA", 0),
        ("EURUSD", "LONDON", 0),
        ("GBPUSD", "LONDON", 0),
        ("XAUUSD", "NEW_YORK", 1),
        ("USDCAD", "NEW_YORK", 0),
        ("NAS100", "NEW_YORK", 2),
    )
    for symbol, session, count in rows:
        _write_market(tmp_path, symbol=symbol, session=session, count=count)

    report = build_matrix(tmp_path)
    assert report["coverage_decision"] == "INCOMPLETE"
    assert report["empty_sessions"] == [CapitalizerSession.LONDON.value]
