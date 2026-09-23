"""Post-outcome deep forensics over the exact frozen V3 2Y MAX3 ledger.

Reuses the existing CORE market_deep_falsification cohort/drawdown engines. This module
never replays or selects strategy opportunities and grants no runtime/promotion authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_market_deep_falsification_v1 import (
    CapitalizerDrawdownEpisode,
    CapitalizerForensicCohort,
    _drawdown,
    _group,
    _holding_band,
    _profit_factor,
)
from qore.infrastructure.trader_lab.capitalizer_v3_m5_directional_state_v1 import (
    classify_m5_directional_state,
)

IDENTITY = "QORE_CAPITALIZER_V3_MAX3_DEEP_FORENSICS_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_V3_MAX3_DEEP_FORENSICS_2Y_V1"
EXPECTED_MAX3_TRADES = 474
NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class V3Max3DeepReport:
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
    by_m5_state: tuple[CapitalizerForensicCohort, ...]
    by_ny_hour: tuple[CapitalizerForensicCohort, ...]
    by_weekday: tuple[CapitalizerForensicCohort, ...]
    by_calendar_year: tuple[CapitalizerForensicCohort, ...]
    by_holding_band: tuple[CapitalizerForensicCohort, ...]
    source_max3_ledger: bool = True
    outcome_aware_forensics: bool = True
    decision_time_feature_allowed: bool = False
    rule_promotion_allowed: bool = False
    economic_candidate: bool = False
    source_methodology_modified: bool = False
    fresh_holdout_claimed: bool = False


def _load_state_lookup(root: Path) -> dict[tuple[str, str], str]:
    paths = sorted(
        root.rglob("capitalizer-*-v3-m3-microstructure-context-2y-v1-rows.jsonl")
    )
    if len(paths) != 1:
        raise ValueError("deep forensics requires one microstructure row ledger")
    result: dict[tuple[str, str], str] = {}
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("microstructure row must be object")
            key = (str(raw["closeback_at"]), str(raw["side"]))
            state = classify_m5_directional_state(
                side=CapitalizerSide(str(raw["side"])),
                microstructure_signature=str(raw["microstructure_signature"]),
            ).value
            if key in result:
                raise ValueError(f"duplicate M5 state key: {key}")
            result[key] = state
    return result


def _load_rows(
    replay_root: Path,
    micro_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], ...]:
    paths = sorted(
        replay_root.rglob(
            "capitalizer-nine-market-v3-frozen-replay-2y-v1-max3-trades.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError(f"deep forensics requires one MAX3 ledger, got {len(paths)}")
    state_lookup = _load_state_lookup(micro_root)
    rows: list[dict[str, Any]] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("MAX3 row must be object")
            if str(raw["symbol"]) != symbol:
                continue
            if raw.get("outcome_used_for_selection") is not False:
                raise ValueError("forensics cannot consume outcome-selected input")
            key = (str(raw["m5_closeback_at"]), str(raw["side"]))
            state = state_lookup.get(key)
            if state is None:
                raise ValueError(f"missing M5 state for MAX3 trade: {key}")
            row = dict(raw)
            row["bars_held"] = int(row["m1_bars_held"])
            row["planned_reward_r"] = "2"
            row["same_bar_stop_target_ambiguity"] = bool(
                row["same_minute_stop_target_ambiguity"]
            )
            row["m5_directional_state"] = state
            rows.append(row)
    if not rows:
        raise ValueError(f"no MAX3 trades for {symbol}")
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                datetime.fromisoformat(str(row["entry_at"])),
                str(row["symbol"]),
            ),
        )
    )


def _freshness(row: dict[str, Any]) -> str:
    closeback = datetime.fromisoformat(str(row["m5_closeback_at"]))
    mss = datetime.fromisoformat(str(row["m3_mss_at"]))
    minutes = int((mss - closeback).total_seconds() // 60)
    return "FRESH_LE_30M" if minutes <= 30 else "STALE_GT_30M"


def build_market_report(
    replay_root: Path,
    micro_root: Path,
    *,
    symbol: str,
) -> V3Max3DeepReport:
    rows = _load_rows(replay_root, micro_root, symbol=symbol)
    sessions = {str(row["session"]) for row in rows}
    if len(sessions) != 1:
        raise ValueError("one market report requires one session")
    session = next(iter(sessions))
    values = tuple(Decimal(str(row["realized_gross_r"])) for row in rows)
    max_dd, max_streak, dd_episode = _drawdown(rows)

    return V3Max3DeepReport(
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
        by_m5_state=_group(rows, lambda row: str(row["m5_directional_state"])),
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


def write_market(report: V3Max3DeepReport, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-v3-max3-deep-forensics-2y-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.rglob("capitalizer-*-v3-max3-deep-forensics-2y-v1.json"))
    if len(paths) != 9:
        raise ValueError(f"deep matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    trades = sum(int(item["trades"]) for item in reports)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "trades": trades,
        "expected_max3_trades": EXPECTED_MAX3_TRADES,
        "max3_control_reproduced": trades == EXPECTED_MAX3_TRADES,
        "markets": sorted(reports, key=lambda item: str(item["symbol"])),
        "source_max3_ledger": True,
        "outcome_aware_forensics": True,
        "decision_time_feature_allowed": False,
        "rule_promotion_allowed": False,
        "economic_candidate": False,
        "source_methodology_modified": False,
        "fresh_holdout_claimed": False,
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / "capitalizer-nine-market-v3-max3-deep-forensics-2y-v1.json"
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("replay_root", type=Path)
    market.add_argument("micro_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report = build_market_report(
            args.replay_root,
            args.micro_root,
            symbol=args.symbol,
        )
        write_market(report, args.output)
        print(json.dumps(asdict(report), sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
