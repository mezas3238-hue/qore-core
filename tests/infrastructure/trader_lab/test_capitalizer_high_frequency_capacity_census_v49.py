import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    IDENTITY,
    MATRIX_IDENTITY,
    V49Opportunity,
    _portfolio_max3,
    build_matrix,
)


def _opportunity(
    *,
    symbol: str,
    session: str,
    day: str,
    minute: int,
) -> V49Opportunity:
    at = datetime(2026, 1, 5, 10, 0, tzinfo=UTC) + timedelta(minutes=minute)
    return V49Opportunity(
        symbol=symbol,
        session=session,
        operating_date=day,
        h1_state_direction="BULLISH",
        h1_state_from=at.isoformat(),
        h1_state_until=(at + timedelta(hours=2)).isoformat(),
        h1_state_basis="H1_STATE",
        m15_setup_confirmed_at=at.isoformat(),
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=at.isoformat(),
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )


def test_portfolio_max3_is_across_markets_not_per_market() -> None:
    rows = tuple(
        _opportunity(
            symbol=("EURUSD" if index % 2 == 0 else "GBPUSD"),
            session="LONDON",
            day="2026-01-05",
            minute=index,
        )
        for index in range(6)
    )
    selected = _portfolio_max3(rows)
    assert len(selected) == 3


def _write_market(
    root: Path,
    *,
    symbol: str,
    session: str,
    count: int,
    start_minute: int,
) -> None:
    report = {
        "identity": IDENTITY,
        "symbol": symbol,
        "session": session,
        "source_complete_opportunities": count,
    }
    (root / f"capitalizer-{symbol.lower()}-v49-hf-capacity.json").write_text(
        json.dumps(report),
        encoding="utf-8",
    )
    path = root / f"capitalizer-{symbol.lower()}-v49-hf-capacity-opportunities.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for offset in range(count):
            row = _opportunity(
                symbol=symbol,
                session=session,
                day=f"2026-01-{1 + (offset // 3):02d}",
                minute=start_minute + offset,
            )
            handle.write(json.dumps(asdict(row)) + "\n")


def test_matrix_passes_high_frequency_density_when_all_sessions_are_dense(
    tmp_path: Path,
) -> None:
    rows = (
        ("USDJPY", "ASIA", 60),
        ("AUDJPY", "ASIA", 60),
        ("AUDUSD", "ASIA", 60),
        ("GBPJPY", "ASIA", 60),
        ("EURUSD", "LONDON", 90),
        ("GBPUSD", "LONDON", 90),
        ("XAUUSD", "NEW_YORK", 70),
        ("USDCAD", "NEW_YORK", 70),
        ("NAS100", "NEW_YORK", 70),
    )
    minute = 0
    for symbol, session, count in rows:
        _write_market(
            tmp_path,
            symbol=symbol,
            session=session,
            count=count,
            start_minute=minute,
        )
        minute += count

    result = build_matrix(tmp_path)
    assert result["identity"] == MATRIX_IDENTITY
    assert result["decision_timeframes"] == ["H1", "M15", "M1"]
    assert result["daily_used"] is False
    assert result["h4_used"] is False
    assert result["source_complete_opportunities"] == 630
    assert result["density_decision"] == "HIGH_FREQUENCY_CAPACITY_PASS"
    assert result["outcome_used"] is False
    assert result["economics_used"] is False
