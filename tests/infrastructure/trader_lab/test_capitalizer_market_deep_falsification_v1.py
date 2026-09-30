from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.capitalizer_market_deep_falsification_v1 import (
    IDENTITY,
    MATRIX_IDENTITY,
    build_market_report,
    build_matrix,
    write_market_report,
)


def _row(
    *,
    symbol: str,
    session: str,
    entry_at: datetime,
    side: str,
    realized_r: str,
    exit_reason: str,
    event: str,
    planned_reward_r: str = "2",
    ambiguity: bool = False,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "session": session,
        "side": side,
        "signal_at": (entry_at - timedelta(minutes=5)).isoformat(),
        "entry_at": entry_at.isoformat(),
        "exit_at": (entry_at + timedelta(minutes=5)).isoformat(),
        "event_labels": [event],
        "entry_price": "100",
        "stop_price": "99",
        "target_price": "102",
        "initial_risk_price": "1",
        "planned_reward_r": planned_reward_r,
        "realized_gross_r": realized_r,
        "exit_reason": exit_reason,
        "bars_held": 1,
        "same_bar_stop_target_ambiguity": ambiguity,
        "source_faithful_entry_confirmed": False,
        "source_strategy_status": "WAIT_M1_EVIDENCE",
        "outcome_used_for_selection": False,
    }


def _write_ledger(root: Path, symbol: str, rows: tuple[dict[str, object], ...]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"capitalizer-{symbol.lower()}-three-session-replay-cell-v1-trades.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_market_forensics_falsifies_dd_session_exit_ambiguity_and_max3(tmp_path: Path) -> None:
    base = datetime(2024, 1, 8, 1, 0, tzinfo=UTC)
    rows = (
        _row(
            symbol="USDJPY",
            session="ASIA",
            entry_at=base,
            side="LONG",
            realized_r="5",
            exit_reason="TARGET",
            event="A",
        ),
        _row(
            symbol="USDJPY",
            session="ASIA",
            entry_at=base + timedelta(minutes=5),
            side="SHORT",
            realized_r="-4",
            exit_reason="STOP",
            event="B",
            ambiguity=True,
        ),
        _row(
            symbol="USDJPY",
            session="ASIA",
            entry_at=base + timedelta(minutes=10),
            side="SHORT",
            realized_r="-4",
            exit_reason="STOP",
            event="B",
        ),
        _row(
            symbol="USDJPY",
            session="ASIA",
            entry_at=base + timedelta(minutes=15),
            side="LONG",
            realized_r="-1",
            exit_reason="SESSION_EXIT",
            event="A",
        ),
    )
    _write_ledger(tmp_path, "USDJPY", rows)

    report = build_market_report(tmp_path)

    assert report.identity == IDENTITY
    assert report.symbol == "USDJPY"
    assert report.session == "ASIA"
    assert report.trades == 4
    assert report.max_drawdown_r == "9"
    assert report.operating_sessions_over_max3 == 1
    assert report.max_candidates_one_operating_session == 4
    assert report.session_exits == 1
    assert report.ambiguous_stop_first_exits == 1

    claims = {item.claim_id: item for item in report.falsification_claims}
    assert claims["OWNER_DD_ENVELOPE_LE_6R"].status == "FALSIFIED_IN_PROXY"
    assert (
        claims["ALL_CANDIDATES_RESOLVE_STRUCTURALLY_INTRASESSION"].status
        == "FALSIFIED_IN_PROXY"
    )
    assert claims["NO_SAME_M5_PRECEDENCE_AMBIGUITY"].status == "FALSIFIED_IN_PROXY"
    assert claims["MAX3_NEVER_BINDS_WITHIN_MARKET"].status == "FALSIFIED_IN_PROXY"
    assert report.rule_promotion_allowed is False
    assert report.economic_candidate is False


def test_nine_market_matrix_requires_and_preserves_exact_universe(tmp_path: Path) -> None:
    mapping = {
        "USDJPY": "ASIA",
        "AUDJPY": "ASIA",
        "AUDUSD": "ASIA",
        "GBPJPY": "ASIA",
        "EURUSD": "LONDON",
        "GBPUSD": "LONDON",
        "XAUUSD": "NEW_YORK",
        "USDCAD": "NEW_YORK",
        "NAS100": "NEW_YORK",
    }
    base = datetime(2024, 1, 8, 12, 0, tzinfo=UTC)
    reports_root = tmp_path / "reports"

    for index, (symbol, session) in enumerate(mapping.items()):
        source = tmp_path / "source" / symbol
        rows = (
            _row(
                symbol=symbol,
                session=session,
                entry_at=base + timedelta(days=index),
                side="LONG",
                realized_r="1",
                exit_reason="TARGET",
                event="A",
            ),
        )
        _write_ledger(source, symbol, rows)
        report = build_market_report(source)
        write_market_report(report, reports_root / symbol)

    matrix = build_matrix(reports_root)

    assert matrix.identity == MATRIX_IDENTITY
    assert matrix.complete_nine_market_universe is True
    assert len(matrix.markets) == 9
    assert matrix.rule_promotion_allowed is False
    assert matrix.economic_candidate is False
    assert matrix.trader_certified is False
