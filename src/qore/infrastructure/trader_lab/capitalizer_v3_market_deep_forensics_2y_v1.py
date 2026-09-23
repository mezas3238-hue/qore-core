"""Deep market forensics for frozen V3 2Y trades using existing CORE engines."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_market_deep_falsification_v1 import (
    CapitalizerDrawdownEpisode,
    CapitalizerForensicCohort,
    _drawdown,
    _group,
    _holding_band,
    _profit_factor,
)

IDENTITY = "QORE_CAPITALIZER_V3_MARKET_DEEP_FORENSICS_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_MARKET_DEEP_FORENSICS_2Y_V1"
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class V3MarketDeepReport:
    identity: str
    symbol: str
    session: str
    trades: int
    total_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    max_drawdown_episode: CapitalizerDrawdownEpisode
    stop_exits: int
    target_exits: int
    time_exits: int
    session_exits: int
    by_side: tuple[CapitalizerForensicCohort, ...]
    by_liquidity_source: tuple[CapitalizerForensicCohort, ...]
    by_entry_mode: tuple[CapitalizerForensicCohort, ...]
    by_freshness: tuple[CapitalizerForensicCohort, ...]
    by_ny_hour: tuple[CapitalizerForensicCohort, ...]
    by_weekday: tuple[CapitalizerForensicCohort, ...]
    by_calendar_year: tuple[CapitalizerForensicCohort, ...]
    by_holding_band: tuple[CapitalizerForensicCohort, ...]
    diagnostic_only: bool = True
    reused_core_deep_forensics_engine: bool = True
    strategy_mutated: bool = False
    outcome_used_for_selection: bool = False
    market_removed: bool = False
    session_removed: bool = False
    rule_promotion_allowed: bool = False
    fresh_holdout_claimed: bool = False


def _load_rows(root: Path) -> tuple[dict[str, Any], ...]:
    paths = sorted(root.rglob("capitalizer-*-v3-frozen-replay-2y-v1-trades.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"V3 deep forensics requires one market ledger, got {len(paths)}")
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("V3 trade row must be object")
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("V3 forensic input cannot be outcome-selected")
            row = dict(raw)
            row["bars_held"] = int(row["m1_bars_held"])
            row["same_bar_stop_target_ambiguity"] = bool(
                row["same_minute_stop_target_ambiguity"]
            )
            row["planned_reward_r"] = "2"
            rows.append(row)
    if not rows:
        raise ValueError("V3 deep forensics requires trades")
    return tuple(
        sorted(rows, key=lambda item: datetime.fromisoformat(str(item["entry_at"])))
    )


def _freshness(row: dict[str, Any]) -> str:
    closeback = datetime.fromisoformat(str(row["m5_closeback_at"]))
    mss = datetime.fromisoformat(str(row["m3_mss_at"]))
    minutes = int((mss - closeback).total_seconds() // 60)
    return "FRESH_LE_30M" if minutes <= 30 else "STALE_GT_30M"


def build_market_report(root: Path) -> V3MarketDeepReport:
    rows = _load_rows(root)
    symbols = {str(row["symbol"]) for row in rows}
    sessions = {str(row["session"]) for row in rows}
    if len(symbols) != 1 or len(sessions) != 1:
        raise ValueError("V3 market forensics requires one symbol/session")

    symbol = next(iter(symbols))
    session = next(iter(sessions))
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    max_dd, max_streak, dd_episode = _drawdown(rows)

    return V3MarketDeepReport(
        identity=IDENTITY,
        symbol=symbol,
        session=session,
        trades=len(rows),
        total_r=str(sum(values, Decimal("0"))),
        profit_factor=_profit_factor(values),
        max_drawdown_r=str(max_dd),
        max_losing_streak=max_streak,
        max_drawdown_episode=dd_episode,
        stop_exits=sum(row["exit_reason"] == "STOP" for row in rows),
        target_exits=sum(row["exit_reason"] == "TARGET" for row in rows),
        time_exits=sum(row["exit_reason"] == "TIME_EXIT" for row in rows),
        session_exits=sum(row["exit_reason"] == "SESSION_EXIT" for row in rows),
        by_side=_group(rows, lambda row: str(row["side"])),
        by_liquidity_source=_group(rows, lambda row: str(row["liquidity_source"])),
        by_entry_mode=_group(rows, lambda row: str(row["entry_mode"])),
        by_freshness=_group(rows, _freshness),
        by_ny_hour=_group(
            rows,
            lambda row: (
                f"{datetime.fromisoformat(str(row['entry_at'])).astimezone(NEW_YORK).hour:02d}"
            ),
        ),
        by_weekday=_group(
            rows,
            lambda row: (
                datetime.fromisoformat(str(row["entry_at"]))
                .astimezone(NEW_YORK)
                .strftime("%A")
                .upper()
            ),
        ),
        by_calendar_year=_group(
            rows,
            lambda row: datetime.fromisoformat(str(row["entry_at"])).year,
        ),
        by_holding_band=_group(rows, _holding_band),
    )


def write_market(report: V3MarketDeepReport, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-v3-market-deep-forensics-2y-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-v3-market-deep-forensics-2y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"V3 deep matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "trades_across_market_ledgers": sum(int(item["trades"]) for item in reports),
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "diagnostic_only": True,
        "reused_core_deep_forensics_engine": True,
        "strategy_mutated": False,
        "outcome_used_for_selection": False,
        "market_removed": False,
        "session_removed": False,
        "rule_promotion_allowed": False,
        "fresh_holdout_claimed": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-market-deep-forensics-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("output", type=Path)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report = build_market_report(args.replay_root)
        write_market(report, args.output)
        print(json.dumps(asdict(report), sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
