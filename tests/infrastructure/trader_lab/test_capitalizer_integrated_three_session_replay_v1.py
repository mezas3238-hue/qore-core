from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_contract import (
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_integrated_three_session_replay_v1 import (
    CELL_IDENTITY,
    IDENTITY,
    build_integrated_report,
)


def _metrics(*, trades: int) -> dict[str, object]:
    return {
        "trades": trades,
        "wins": trades,
        "losses": 0,
        "flats": 0,
        "total_gross_r": str(trades),
        "mean_gross_r": "1",
        "gross_profit_r": str(trades),
        "gross_loss_r": "0",
        "profit_factor": None,
        "max_drawdown_r": "0",
        "max_losing_streak": 0,
        "median_planned_reward_r": "1",
        "median_bars_held": "1",
        "stop_exits": 0,
        "target_exits": trades,
        "session_exits": 0,
        "ambiguous_stop_first_exits": 0,
    }


def _write_cell(
    root: Path,
    *,
    symbol: str,
    session: CapitalizerSession,
    trade_count: int,
    base: datetime,
) -> None:
    cell = root / symbol
    cell.mkdir(parents=True)
    report = {
        "identity": CELL_IDENTITY,
        "symbol": symbol,
        "session": session.value,
        "metrics": _metrics(trades=trade_count),
        "geometry_candidate_count": trade_count,
        "entry_probe": "NEXT_CONTIGUOUS_M5_OPEN",
        "stop_probe": "SOURCE_M5_DIRECTIONAL_EXTREME",
        "target_probe": "NEAREST_CAUSAL_TARGET_V2",
        "lifecycle_probe": "INTRASESSION_STOP_FIRST",
        "source_faithful_entry_confirmed": False,
        "source_faithful_pre_risk_ready": 0,
        "m1_evidence_required": True,
        "m1_evidence_present": False,
        "source_strategy_status": "WAIT_M1_EVIDENCE",
        "cognitive_scope": "CONTEXT_AND_GOVERNANCE_ONLY",
        "evidence_status": "CONSUMED_RESEARCH_EVIDENCE",
        "geometry_proxy_only": True,
        "economic_candidate": False,
        "rule_promotion_allowed": False,
    }
    (cell / f"capitalizer-{symbol.lower()}-three-session-replay-cell-v1.json").write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    ledger = (
        cell
        / f"capitalizer-{symbol.lower()}-three-session-replay-cell-v1-trades.jsonl"
    )
    with ledger.open("w", encoding="utf-8") as handle:
        for index in range(trade_count):
            entry_at = base + timedelta(minutes=index)
            row = {
                "symbol": symbol,
                "session": session.value,
                "side": "LONG",
                "signal_at": (entry_at - timedelta(minutes=5)).isoformat(),
                "entry_at": entry_at.isoformat(),
                "exit_at": (entry_at + timedelta(minutes=5)).isoformat(),
                "event_labels": ["TEST"],
                "entry_price": "100",
                "stop_price": "99",
                "target_price": "101",
                "initial_risk_price": "1",
                "planned_reward_r": "1",
                "realized_gross_r": "1",
                "exit_reason": "TARGET",
                "bars_held": 1,
                "same_bar_stop_target_ambiguity": False,
                "entry_probe": "NEXT_CONTIGUOUS_M5_OPEN",
                "stop_probe": "SOURCE_M5_DIRECTIONAL_EXTREME",
                "target_probe": "NEAREST_CAUSAL_TARGET_V2",
                "source_faithful_entry_confirmed": False,
                "source_strategy_status": "WAIT_M1_EVIDENCE",
                "outcome_used_for_selection": False,
            }
            handle.write(json.dumps(row) + "\n")


def test_integrated_three_session_replay_covers_nine_markets_and_detects_max3(
    tmp_path: Path,
) -> None:
    base = datetime(2026, 1, 5, 1, 0, tzinfo=UTC)
    first = True
    expected_trades = 0

    for session in CapitalizerSession:
        for symbol in sorted(allowed_markets(session)):
            trade_count = 4 if first else 1
            first = False
            expected_trades += trade_count
            _write_cell(
                tmp_path,
                symbol=symbol,
                session=session,
                trade_count=trade_count,
                base=base,
            )

    report = build_integrated_report(tmp_path)

    assert report.identity == IDENTITY
    assert report.full_nine_market_universe is True
    assert report.full_three_session_coverage is True
    assert report.proxy_trades == expected_trades
    assert report.source_faithful_simulated_executions == 0
    assert report.source_faithful_replay_complete is False
    assert report.source_strategy_status == "WAIT_M1_EVIDENCE"
    assert report.master_cognitive_frame_replayed is False
    assert report.max3_selection_applied_to_proxy_economics is False
    assert report.outcome_aware_ranking_used is False
    assert report.operating_sessions_over_max3 >= 1
    assert report.max_proxy_candidates_in_one_operating_session >= 4
    assert report.trader_certified is False
    assert report.rule_promotion_allowed is False
