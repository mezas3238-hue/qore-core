import json
from dataclasses import asdict
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    IDENTITY as CAPACITY_IDENTITY,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v49_holdout_contract import (
    HOLDOUT_END,
    HOLDOUT_START,
)
from qore.infrastructure.trader_lab.capitalizer_v49_holdout_replay import (
    IDENTITY,
    build_holdout_report,
)


def _opportunity(
    *,
    symbol: str,
    session: str,
    day: str,
    minute: int,
) -> V49Opportunity:
    return V49Opportunity(
        symbol=symbol,
        session=session,
        operating_date=day,
        h1_state_direction="BULLISH",
        h1_state_from=f"{day}T09:00:00+00:00",
        h1_state_until=f"{day}T13:00:00+00:00",
        h1_state_basis="H1_STATE",
        m15_setup_confirmed_at=f"{day}T10:00:00+00:00",
        m15_protected_swing_price="99",
        m1_trigger_confirmed_at=f"{day}T10:{minute:02d}:00+00:00",
        m1_trigger_family="LIQUIDITY_SWEEP_CISD",
        decision_reference_price="100",
        structural_target_witness_price="101",
    )


def _write_market(
    root: Path,
    *,
    symbol: str,
    session: str,
    opportunities: tuple[V49Opportunity, ...],
) -> None:
    report = {
        "identity": CAPACITY_IDENTITY,
        "symbol": symbol,
        "session": session,
        "window_start": HOLDOUT_START.isoformat(),
        "window_end_exclusive": HOLDOUT_END.isoformat(),
        "source_complete_opportunities": len(opportunities),
        "fresh_holdout_used": False,
        "outcome_used": False,
        "economics_used": False,
        "daily_used": False,
        "h4_used": False,
    }
    (root / f"capitalizer-{symbol.lower()}-v49-hf-capacity.json").write_text(
        json.dumps(report),
        encoding="utf-8",
    )
    ledger = root / f"capitalizer-{symbol.lower()}-v49-hf-capacity-opportunities.jsonl"
    with ledger.open("w", encoding="utf-8") as handle:
        for item in opportunities:
            handle.write(json.dumps(asdict(item)) + "\n")


def test_holdout_counts_portfolio_trades_after_max3(tmp_path: Path) -> None:
    universe = (
        ("USDJPY", "ASIA"),
        ("AUDJPY", "ASIA"),
        ("AUDUSD", "ASIA"),
        ("GBPJPY", "ASIA"),
        ("EURUSD", "LONDON"),
        ("GBPUSD", "LONDON"),
        ("XAUUSD", "NEW_YORK"),
        ("USDCAD", "NEW_YORK"),
        ("NAS100", "NEW_YORK"),
    )
    for symbol, session in universe:
        day = "2025-01-02"
        rows = tuple(
            _opportunity(
                symbol=symbol,
                session=session,
                day=day,
                minute=index,
            )
            for index in range(2)
        )
        _write_market(
            tmp_path,
            symbol=symbol,
            session=session,
            opportunities=rows,
        )

    report, trades = build_holdout_report(
        tmp_path,
        methodology_git_sha="abcdef1234567890",
    )
    assert report.identity == IDENTITY
    assert report.candidate_opportunities == 18
    assert report.executed_trades == 9
    assert len(trades) == 9
    assert report.max_trades_one_day == 9
    assert report.fresh_holdout_used is False
    assert report.outcome_used is False
    assert report.economics_used is False
