"""Integrated three-session replay diagnostics for QORE Capitalizer.

This replay deliberately keeps two evidence layers separate:

1. M5 geometry characterization
   - entry proxy: next contiguous M5 open;
   - stop proxy: directional extreme of the causal source M5;
   - target proxy: nearest causal Target V2 destination;
   - lifecycle: same-session, STOP_FIRST on M5 ambiguity.

2. Frozen source-faithful execution
   - still requires causal M1 confirmation;
   - consumed CIBO M5 may provide context but cannot be promoted to M1;
   - therefore this diagnostic never claims PRE_RISK_READY, economic candidate,
     certification, LIVE authority, or source-faithful execution.

The output is intended to expose where entries/stops/targets and session density fail before the
nine market families are studied and falsified individually.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_contract import (
    MAX_EXECUTIONS_PER_SESSION,
    CapitalizerSession,
    allowed_markets,
)
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    build_r0_trades,
    summarize_r0,
)

IDENTITY = "QORE_CAPITALIZER_INTEGRATED_THREE_SESSION_REPLAY_V1"
CELL_IDENTITY = "QORE_CAPITALIZER_THREE_SESSION_REPLAY_CELL_V1"
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class CapitalizerReplayCellReport:
    identity: str
    symbol: str
    session: str
    metrics: CapitalizerR0Metrics
    geometry_candidate_count: int
    entry_probe: str = "NEXT_CONTIGUOUS_M5_OPEN"
    stop_probe: str = "SOURCE_M5_DIRECTIONAL_EXTREME"
    target_probe: str = "NEAREST_CAUSAL_TARGET_V2"
    lifecycle_probe: str = "INTRASESSION_STOP_FIRST"
    source_faithful_entry_confirmed: bool = False
    source_faithful_pre_risk_ready: int = 0
    m1_evidence_required: bool = True
    m1_evidence_present: bool = False
    source_strategy_status: str = "WAIT_M1_EVIDENCE"
    cognitive_scope: str = "CONTEXT_AND_GOVERNANCE_ONLY"
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    geometry_proxy_only: bool = True
    economic_candidate: bool = False
    rule_promotion_allowed: bool = False


@dataclass(frozen=True, slots=True)
class CapitalizerReplaySessionSummary:
    session: str
    markets: tuple[str, ...]
    proxy_trades: int
    wins: int
    losses: int
    flats: int
    total_gross_r: str
    gross_profit_r: str
    gross_loss_r: str
    profit_factor: str | None
    stop_exits: int
    target_exits: int
    session_exits: int
    ambiguous_stop_first_exits: int
    operating_sessions_over_max3: int
    max_proxy_candidates_in_one_operating_session: int


@dataclass(frozen=True, slots=True)
class CapitalizerIntegratedReplayReport:
    identity: str
    cells: tuple[CapitalizerReplayCellReport, ...]
    sessions: tuple[CapitalizerReplaySessionSummary, ...]
    full_nine_market_universe: bool
    full_three_session_coverage: bool
    proxy_trades: int
    wins: int
    losses: int
    flats: int
    total_gross_r: str
    gross_profit_r: str
    gross_loss_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    stop_exits: int
    target_exits: int
    session_exits: int
    ambiguous_stop_first_exits: int
    operating_sessions_over_max3: int
    max_proxy_candidates_in_one_operating_session: int
    source_faithful_simulated_executions: int = 0
    source_faithful_replay_complete: bool = False
    m1_evidence_required: bool = True
    m1_evidence_present: bool = False
    source_strategy_status: str = "WAIT_M1_EVIDENCE"
    master_cognitive_frame_replayed: bool = False
    cognitive_status: str = "FULL_MASTER_FRAME_NOT_YET_REPLAYED"
    max3_selection_applied_to_proxy_economics: bool = False
    outcome_aware_ranking_used: bool = False
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    geometry_proxy_only: bool = True
    economic_candidate: bool = False
    fresh_holdout_claimed: bool = False
    trader_certified: bool = False
    rule_promotion_allowed: bool = False

    def __post_init__(self) -> None:
        if self.source_faithful_simulated_executions != 0:
            raise ValueError("M5 diagnostic cannot claim source-faithful executions")
        if (
            self.source_faithful_replay_complete
            or self.master_cognitive_frame_replayed
            or self.max3_selection_applied_to_proxy_economics
            or self.outcome_aware_ranking_used
            or self.economic_candidate
            or self.fresh_holdout_claimed
            or self.trader_certified
            or self.rule_promotion_allowed
        ):
            raise ValueError("diagnostic replay cannot claim promotion/certification authority")
        if not self.geometry_proxy_only:
            raise ValueError("integrated three-session V1 is explicitly geometry-proxy only")
        if self.m1_evidence_present:
            raise ValueError("this consumed CIBO replay does not contain native/finer M1 evidence")


def _trade_payload(trade: CapitalizerR0Trade, *, session: CapitalizerSession) -> dict[str, Any]:
    return {
        "symbol": trade.symbol,
        "session": session.value,
        "side": trade.side.value,
        "signal_at": trade.signal_at.isoformat(),
        "entry_at": trade.entry_at.isoformat(),
        "exit_at": trade.exit_at.isoformat(),
        "event_labels": list(trade.event_labels),
        "entry_price": str(trade.entry_price),
        "stop_price": str(trade.stop_price),
        "target_price": str(trade.target_price),
        "initial_risk_price": str(trade.initial_risk_price),
        "planned_reward_r": str(trade.planned_reward_r),
        "realized_gross_r": str(trade.realized_gross_r),
        "exit_reason": trade.exit_reason,
        "bars_held": trade.bars_held,
        "same_bar_stop_target_ambiguity": trade.same_bar_stop_target_ambiguity,
        "entry_probe": "NEXT_CONTIGUOUS_M5_OPEN",
        "stop_probe": "SOURCE_M5_DIRECTIONAL_EXTREME",
        "target_probe": "NEAREST_CAUSAL_TARGET_V2",
        "source_faithful_entry_confirmed": False,
        "source_strategy_status": "WAIT_M1_EVIDENCE",
        "outcome_used_for_selection": False,
    }


def write_cell_replay(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
    output: Path,
) -> CapitalizerReplayCellReport:
    trades = build_r0_trades(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    if not trades:
        raise ValueError("three-session replay cell requires at least one geometry candidate")
    r0 = summarize_r0(trades)
    session = CapitalizerSession(r0.session)
    report = CapitalizerReplayCellReport(
        identity=CELL_IDENTITY,
        symbol=r0.symbol,
        session=r0.session,
        metrics=r0.metrics,
        geometry_candidate_count=len(trades),
    )

    output.mkdir(parents=True, exist_ok=True)
    report_path = output / f"capitalizer-{r0.symbol.lower()}-three-session-replay-cell-v1.json"
    report_path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    ledger_path = (
        output / f"capitalizer-{r0.symbol.lower()}-three-session-replay-cell-v1-trades.jsonl"
    )
    with ledger_path.open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(
                json.dumps(
                    _trade_payload(trade, session=session),
                    sort_keys=True,
                )
                + "\n"
            )
    return report


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("replay cell JSON must be an object")
    return payload


def _load_cells(root: Path) -> tuple[CapitalizerReplayCellReport, ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"integrated replay requires exactly 9 cell reports, got {len(paths)}")

    cells: list[CapitalizerReplayCellReport] = []
    for path in paths:
        raw = _read_json(path)
        if raw.get("identity") != CELL_IDENTITY:
            raise ValueError("unexpected replay cell identity")
        metrics_raw = raw.get("metrics")
        if not isinstance(metrics_raw, dict):
            raise ValueError("replay cell metrics must be object")
        cells.append(
            CapitalizerReplayCellReport(
                identity=str(raw["identity"]),
                symbol=str(raw["symbol"]),
                session=str(raw["session"]),
                metrics=CapitalizerR0Metrics(**metrics_raw),
                geometry_candidate_count=int(raw["geometry_candidate_count"]),
            )
        )
    return tuple(sorted(cells, key=lambda item: item.symbol))


def _load_trade_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-three-session-replay-cell-v1-trades.jsonl"))
    if len(paths) != 9:
        raise ValueError(f"integrated replay requires exactly 9 trade ledgers, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("trade ledger row must be an object")
                if raw.get("source_faithful_entry_confirmed") is not False:
                    raise ValueError("M5 proxy row cannot claim source-faithful entry")
                if raw.get("outcome_used_for_selection") is not False:
                    raise ValueError("proxy replay cannot use outcome-aware selection")
                rows.append(raw)
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                datetime.fromisoformat(str(row["entry_at"])),
                str(row["symbol"]),
            ),
        )
    )


def _operating_date(entry_at: datetime, session: CapitalizerSession) -> str:
    local = entry_at.astimezone(NEW_YORK)
    if session is CapitalizerSession.ASIA and local.hour < 2:
        return (local.date() - timedelta(days=1)).isoformat()
    return local.date().isoformat()


def _profit_factor(gross_profit: Decimal, gross_loss: Decimal) -> str | None:
    if gross_loss == 0:
        return None
    return str(gross_profit / gross_loss)


def _session_summary(
    *,
    session: CapitalizerSession,
    cells: tuple[CapitalizerReplayCellReport, ...],
    rows: tuple[dict[str, Any], ...],
) -> CapitalizerReplaySessionSummary:
    session_rows = tuple(row for row in rows if row["session"] == session.value)
    returns = tuple(Decimal(str(row["realized_gross_r"])) for row in session_rows)
    gross_profit = sum((value for value in returns if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in returns if value < 0), Decimal("0"))

    counts: dict[str, int] = defaultdict(int)
    for row in session_rows:
        entry_at = datetime.fromisoformat(str(row["entry_at"]))
        counts[_operating_date(entry_at, session)] += 1

    market_symbols = tuple(
        sorted(cell.symbol for cell in cells if cell.session == session.value)
    )
    return CapitalizerReplaySessionSummary(
        session=session.value,
        markets=market_symbols,
        proxy_trades=len(session_rows),
        wins=sum(value > 0 for value in returns),
        losses=sum(value < 0 for value in returns),
        flats=sum(value == 0 for value in returns),
        total_gross_r=str(sum(returns, Decimal("0"))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=_profit_factor(gross_profit, gross_loss),
        stop_exits=sum(row["exit_reason"] == "STOP" for row in session_rows),
        target_exits=sum(row["exit_reason"] == "TARGET" for row in session_rows),
        session_exits=sum(row["exit_reason"] == "SESSION_EXIT" for row in session_rows),
        ambiguous_stop_first_exits=sum(
            bool(row["same_bar_stop_target_ambiguity"]) for row in session_rows
        ),
        operating_sessions_over_max3=sum(
            count > MAX_EXECUTIONS_PER_SESSION for count in counts.values()
        ),
        max_proxy_candidates_in_one_operating_session=max(counts.values(), default=0),
    )


def build_integrated_report(root: Path) -> CapitalizerIntegratedReplayReport:
    cells = _load_cells(root)
    rows = _load_trade_rows(root)

    observed = {cell.symbol for cell in cells}
    expected = {
        symbol
        for session in CapitalizerSession
        for symbol in allowed_markets(session)
    }
    full_universe = observed == expected
    if not full_universe:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise ValueError(f"replay universe mismatch missing={missing} extra={extra}")

    for cell in cells:
        session = CapitalizerSession(cell.session)
        if cell.symbol not in allowed_markets(session):
            raise ValueError("replay cell symbol/session assignment drifted")

    summaries = tuple(
        _session_summary(session=session, cells=cells, rows=rows)
        for session in CapitalizerSession
    )
    full_sessions = {item.session for item in summaries} == {
        item.value for item in CapitalizerSession
    }

    returns = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    gross_profit = sum((value for value in returns if value > 0), Decimal("0"))
    gross_loss = -sum((value for value in returns if value < 0), Decimal("0"))

    equity = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in returns:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return CapitalizerIntegratedReplayReport(
        identity=IDENTITY,
        cells=cells,
        sessions=summaries,
        full_nine_market_universe=full_universe,
        full_three_session_coverage=full_sessions,
        proxy_trades=len(rows),
        wins=sum(value > 0 for value in returns),
        losses=sum(value < 0 for value in returns),
        flats=sum(value == 0 for value in returns),
        total_gross_r=str(sum(returns, Decimal("0"))),
        gross_profit_r=str(gross_profit),
        gross_loss_r=str(gross_loss),
        profit_factor=_profit_factor(gross_profit, gross_loss),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        stop_exits=sum(row["exit_reason"] == "STOP" for row in rows),
        target_exits=sum(row["exit_reason"] == "TARGET" for row in rows),
        session_exits=sum(row["exit_reason"] == "SESSION_EXIT" for row in rows),
        ambiguous_stop_first_exits=sum(
            bool(row["same_bar_stop_target_ambiguity"]) for row in rows
        ),
        operating_sessions_over_max3=sum(
            item.operating_sessions_over_max3 for item in summaries
        ),
        max_proxy_candidates_in_one_operating_session=max(
            (
                item.max_proxy_candidates_in_one_operating_session
                for item in summaries
            ),
            default=0,
        ),
    )


def write_integrated_report(report: CapitalizerIntegratedReplayReport, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "capitalizer-integrated-three-session-replay-v1.json"
    json_path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# QORE Capitalizer — Integrated Three-Session Replay V1",
        "",
        "## Evidence boundary",
        "",
        "- Geometry is a consumed-M5 diagnostic proxy, not the frozen source-faithful M1 entry.",
        "- Source-faithful strategy remains WAIT_M1_EVIDENCE.",
        "- Master Cognitive Frame replay is not yet claimed by this artifact.",
        "- MAX3 is not outcome-ranked or forced onto proxy economics.",
        "",
        "## Aggregate",
        "",
        f"- Proxy trades: {report.proxy_trades}",
        f"- Wins / losses / flats: {report.wins} / {report.losses} / {report.flats}",
        f"- Gross PF: {report.profit_factor}",
        f"- Total gross R: {report.total_gross_r}",
        f"- Max chronological proxy DD: {report.max_drawdown_r}R",
        f"- Max losing streak: {report.max_losing_streak}",
        f"- STOP / TARGET / SESSION_EXIT: {report.stop_exits} / {report.target_exits} / {report.session_exits}",
        f"- Same-M5 STOP_FIRST ambiguities: {report.ambiguous_stop_first_exits}",
        f"- Operating sessions with >MAX3 proxy candidates: {report.operating_sessions_over_max3}",
        "",
        "## Sessions",
        "",
        "| Session | Markets | Proxy trades | PF | Gross R | Stops | Targets | Session exits | >MAX3 instances |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in report.sessions:
        lines.append(
            "| "
            f"{item.session} | {', '.join(item.markets)} | {item.proxy_trades} | "
            f"{item.profit_factor} | {item.total_gross_r} | {item.stop_exits} | "
            f"{item.target_exits} | {item.session_exits} | "
            f"{item.operating_sessions_over_max3} |"
        )
    lines.extend(
        [
            "",
            "## Next evidence gate",
            "",
            "Acquire native/finer <=60s evidence, replay the full frozen Master Cognitive Frame, "
            "then bind the source-faithful H1 -> M15 -> M1 / FTM routes before economic selection.",
        ]
    )
    (output / "capitalizer-integrated-three-session-replay-v1.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="QORE Capitalizer three-session replay")
    subparsers = parser.add_subparsers(dest="command", required=True)

    cell = subparsers.add_parser("cell")
    cell.add_argument("m5_root", type=Path)
    cell.add_argument("journey_root", type=Path)
    cell.add_argument("target_root", type=Path)
    cell.add_argument("output", type=Path)

    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("input_root", type=Path)
    aggregate.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "cell":
        report = write_cell_replay(
            m5_root=args.m5_root,
            journey_root=args.journey_root,
            target_root=args.target_root,
            output=args.output,
        )
        print(json.dumps(asdict(report), sort_keys=True))
        return

    report = build_integrated_report(args.input_root)
    write_integrated_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "proxy_trades": report.proxy_trades,
                "profit_factor": report.profit_factor,
                "total_gross_r": report.total_gross_r,
                "max_drawdown_r": report.max_drawdown_r,
                "source_strategy_status": report.source_strategy_status,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
