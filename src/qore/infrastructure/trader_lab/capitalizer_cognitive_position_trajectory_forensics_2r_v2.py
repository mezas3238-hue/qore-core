"""True-2R position-trajectory forensics for QORE Capitalizer.

This supersedes the economic interpretation of the older 1R position trajectory
work that depended on the invalid non-2R target-accounting ledger. It consumes
only the corrected Target Sensitivity V2 2R outcomes selected by the frozen
true-2R 948-trade rebase and immutable provider-native M1.

The lab is descriptive and causal:
- the exit/stop bar is excluded from trajectory features;
- M3 pivots must be fully confirmed strictly before exit;
- no stop, target, entry, MAX3 or cognitive rule is changed;
- current outcome labels are used only after the trajectory facts are built.

It measures whether true-2R stop losses, especially the exact 12.9358R maximum
drawdown episode, exposed protectable structure before their original stop.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_economic_rebase_2r_v1 as rebase,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_position_trajectory_forensics_2y_v1 as legacy,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v1 as target_v1,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    _aggregate_tf,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_POSITION_TRAJECTORY_FORENSICS_2R_V2"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_COGNITIVE_POSITION_TRAJECTORY_FORENSICS_2R_V2"
)
SOURCE_REBASE_RUN_ID = 36078677895
SOURCE_REBASE_SHA = "cfc04849c8bbfd6565310d89456f5e367ea880f7"
SOURCE_TARGET_V2_RUN_ID = 36077843102
SOURCE_TARGET_V2_SHA = "a47de3b491b4468527c945d6eff3afbbaec82d4e"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
TARGET_R = Decimal("2.00")
EXPECTED_DD = rebase.EXPECTED_DD_R


@dataclass(frozen=True, slots=True)
class True2RTrajectoryRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    target_price: str
    realized_gross_r: str
    exit_reason: str
    strict_prior_mfe_r: str
    strict_prior_mae_r: str
    confirmed_improving_m3_swing: bool
    confirmed_profitable_m3_swing: bool
    first_improving_m3_confirmed_at: str | None
    first_profitable_m3_confirmed_at: str | None
    in_true2r_max_drawdown_segment: bool
    current_outcome_used_to_discover_trajectory: bool = False


def _aware(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _key(row: dict[str, Any] | target_v1.TargetOutcome) -> tuple[str, str]:
    if isinstance(row, target_v1.TargetOutcome):
        return row.symbol, row.entry_at
    return str(row["symbol"]), str(row["entry_at"])


def _load_rebase(
    root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    reports = sorted(root.rglob("capitalizer-cognitive-economic-rebase-2r-v1.json"))
    ledgers = sorted(
        root.rglob("capitalizer-cognitive-economic-rebase-2r-v1-rows.jsonl")
    )
    if len(reports) != 1 or len(ledgers) != 1:
        raise ValueError("true-2R trajectory requires one economic rebase artifact")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != rebase.IDENTITY:
        raise ValueError("unexpected true-2R rebase identity")
    if Decimal(str(report["control_metrics"]["max_drawdown_r"])) != EXPECTED_DD:
        raise ValueError("true-2R rebase DD control drift")

    rows: list[dict[str, Any]] = []
    with ledgers[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("true-2R rebase row must be object")
                rows.append(raw)
    if len(rows) != rebase.EXPECTED_TRADES:
        raise ValueError("true-2R rebase population mismatch")
    return report, tuple(
        sorted(rows, key=lambda row: (_aware(row["entry_at"]), str(row["symbol"])))
    )


def _max_drawdown_segment(
    rows: tuple[dict[str, Any], ...],
) -> tuple[frozenset[tuple[str, str]], Decimal]:
    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    start = 0
    end = -1
    maximum = Decimal("0")
    for index, row in enumerate(rows):
        equity += Decimal(str(row["post_audit_realized_gross_r"]))
        if equity > peak:
            peak = equity
            peak_index = index
        drawdown = peak - equity
        if drawdown > maximum:
            maximum = drawdown
            start = peak_index + 1
            end = index
    if end < start:
        raise ValueError("true-2R trajectory found no drawdown segment")
    segment = rows[start : end + 1]
    return frozenset(_key(row) for row in segment), maximum


def _load_market_outcomes(
    root: Path,
    *,
    symbol: str,
    selected_keys: frozenset[tuple[str, str]],
) -> tuple[target_v1.TargetOutcome, ...]:
    paths = sorted(
        root.rglob(
            f"capitalizer-{symbol.lower()}-max-recovery-"
            "target-sensitivity-2y-v2-outcomes.jsonl"
        )
    )
    if len(paths) != 1:
        raise ValueError("true-2R trajectory requires one market V2 outcome ledger")
    selected: list[target_v1.TargetOutcome] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = target_v1.TargetOutcome(**json.loads(line))
            if Decimal(item.target_r) != TARGET_R:
                continue
            if _key(item) in selected_keys:
                selected.append(item)
    if not selected:
        raise ValueError("true-2R trajectory found no selected market outcomes")
    return tuple(sorted(selected, key=lambda item: _aware(item.entry_at)))


def _bars_for_market(
    root: Path,
    *,
    outcomes: tuple[target_v1.TargetOutcome, ...],
) -> tuple[CapitalizerM1Bar, ...]:
    start = min(_aware(item.entry_at) for item in outcomes) - timedelta(hours=1)
    end = max(_aware(item.exit_at) for item in outcomes) + timedelta(hours=1)
    bars = tuple(
        bar for bar in iter_cibo_m1(root) if start <= bar.opened_at <= end
    )
    if not bars:
        raise ValueError("true-2R trajectory found no native M1")
    if any(bar.symbol != outcomes[0].symbol for bar in bars):
        raise ValueError("true-2R trajectory M1 symbol drift")
    return bars


def _as_trade(item: target_v1.TargetOutcome) -> dict[str, Any]:
    return {
        "symbol": item.symbol,
        "session": item.session,
        "operating_date": item.operating_date,
        "side": item.side,
        "entry_at": item.entry_at,
        "exit_at": item.exit_at,
        "entry_price": item.entry_price,
        "stop_price": item.stop_price,
        "target_price": item.target_price,
        "realized_gross_r": item.realized_gross_r,
        "exit_reason": item.exit_reason,
    }


def _trajectory_row(
    item: target_v1.TargetOutcome,
    *,
    bars: tuple[CapitalizerM1Bar, ...],
    by_open: dict[datetime, int],
    by_close: dict[datetime, int],
    pivots: tuple[Pivot, ...],
    close_by_at: dict[datetime, Decimal],
    dd_keys: frozenset[tuple[str, str]],
) -> True2RTrajectoryRow:
    trade = _as_trade(item)
    prior, _exit_index = legacy._strict_prior_path(
        trade,
        bars=bars,
        by_open=by_open,
        by_close=by_close,
    )
    mfe, mae = legacy._excursions(trade, prior)
    improving, profitable = legacy._usable_pivots(
        trade,
        pivots=pivots,
        close_by_at=close_by_at,
    )
    return True2RTrajectoryRow(
        symbol=item.symbol,
        session=item.session,
        operating_date=item.operating_date,
        side=item.side,
        entry_at=item.entry_at,
        exit_at=item.exit_at,
        entry_price=item.entry_price,
        stop_price=item.stop_price,
        target_price=item.target_price,
        realized_gross_r=item.realized_gross_r,
        exit_reason=item.exit_reason,
        strict_prior_mfe_r=str(mfe),
        strict_prior_mae_r=str(mae),
        confirmed_improving_m3_swing=improving is not None,
        confirmed_profitable_m3_swing=profitable is not None,
        first_improving_m3_confirmed_at=(
            None if improving is None else improving.isoformat()
        ),
        first_profitable_m3_confirmed_at=(
            None if profitable is None else profitable.isoformat()
        ),
        in_true2r_max_drawdown_segment=_key(item) in dd_keys,
    )


def _mfe_count(rows: tuple[True2RTrajectoryRow, ...], threshold: Decimal) -> int:
    return sum(Decimal(row.strict_prior_mfe_r) >= threshold for row in rows)


def build_market_report(
    rebase_root: Path,
    target_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], tuple[True2RTrajectoryRow, ...]]:
    rebase_report, rebase_rows = _load_rebase(rebase_root)
    selected_keys = frozenset(_key(row) for row in rebase_rows)
    dd_keys, maximum_dd = _max_drawdown_segment(rebase_rows)
    outcomes = _load_market_outcomes(
        target_root,
        symbol=symbol,
        selected_keys=selected_keys,
    )
    expected_market = sum(str(row["symbol"]) == symbol for row in rebase_rows)
    if len(outcomes) != expected_market:
        raise ValueError("true-2R market selection does not reproduce rebase")

    bars = _bars_for_market(m1_root, outcomes=outcomes)
    by_open = {bar.opened_at: index for index, bar in enumerate(bars)}
    by_close = {bar.closed_at: index for index, bar in enumerate(bars)}
    close_by_at = {bar.closed_at: bar.close for bar in bars}
    pivots = _pivots(_aggregate_tf(bars, minutes=3))

    losses = tuple(
        item for item in outcomes if Decimal(item.realized_gross_r) < 0
    )
    trajectory = tuple(
        _trajectory_row(
            item,
            bars=bars,
            by_open=by_open,
            by_close=by_close,
            pivots=pivots,
            close_by_at=close_by_at,
            dd_keys=dd_keys,
        )
        for item in losses
    )
    stops = tuple(row for row in trajectory if row.exit_reason == "STOP")
    dd_stops = tuple(
        row for row in stops if row.in_true2r_max_drawdown_segment
    )
    mfe_values = tuple(Decimal(row.strict_prior_mfe_r) for row in stops)

    report: dict[str, Any] = {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_rebase_run_id": SOURCE_REBASE_RUN_ID,
        "source_rebase_sha": SOURCE_REBASE_SHA,
        "source_target_v2_run_id": SOURCE_TARGET_V2_RUN_ID,
        "source_target_v2_sha": SOURCE_TARGET_V2_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": str(TARGET_R),
        "market_trades": len(outcomes),
        "losing_trades": len(trajectory),
        "stop_losses": len(stops),
        "stop_losses_with_strict_prior_favorable_excursion": _mfe_count(
            stops, Decimal("0.000000000000000000000000001")
        ),
        "stop_losses_prior_mfe_ge_0_25r": _mfe_count(stops, Decimal("0.25")),
        "stop_losses_prior_mfe_ge_0_50r": _mfe_count(stops, Decimal("0.50")),
        "stop_losses_prior_mfe_ge_1_00r": _mfe_count(stops, Decimal("1.00")),
        "stop_losses_with_confirmed_improving_m3_swing": sum(
            row.confirmed_improving_m3_swing for row in stops
        ),
        "stop_losses_with_confirmed_profitable_m3_swing": sum(
            row.confirmed_profitable_m3_swing for row in stops
        ),
        "median_strict_prior_mfe_r": (
            "0" if not mfe_values else str(median(mfe_values))
        ),
        "true2r_max_drawdown_r": str(maximum_dd),
        "max_drawdown_stop_losses": len(dd_stops),
        "max_drawdown_stop_losses_prior_mfe_ge_0_25r": _mfe_count(
            dd_stops, Decimal("0.25")
        ),
        "max_drawdown_stop_losses_prior_mfe_ge_0_50r": _mfe_count(
            dd_stops, Decimal("0.50")
        ),
        "max_drawdown_stop_losses_prior_mfe_ge_1_00r": _mfe_count(
            dd_stops, Decimal("1.00")
        ),
        "max_drawdown_stop_losses_with_improving_m3_swing": sum(
            row.confirmed_improving_m3_swing for row in dd_stops
        ),
        "max_drawdown_stop_losses_with_profitable_m3_swing": sum(
            row.confirmed_profitable_m3_swing for row in dd_stops
        ),
        "rebase_control_reproduced": int(rebase_report["control_trades"])
        == rebase.EXPECTED_TRADES,
        "exit_bar_excluded_from_trajectory_features": True,
        "m3_pivot_confirmation_required": True,
        "stop_policy_simulated": False,
        "break_even_policy_selected": False,
        "trailing_policy_selected": False,
        "current_outcome_used_to_discover_trajectory": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    return report, trajectory


def write_market(
    report: dict[str, Any],
    rows: tuple[True2RTrajectoryRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-cognitive-position-trajectory-forensics-2r-v2"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def build_matrix(root: Path) -> dict[str, Any]:
    reports = sorted(
        root.rglob(
            "capitalizer-*-cognitive-position-trajectory-forensics-2r-v2.json"
        )
    )
    if len(reports) != 9:
        raise ValueError("true-2R trajectory matrix requires nine reports")
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in reports]
    if len({str(item["symbol"]) for item in payloads}) != 9:
        raise ValueError("true-2R trajectory matrix requires nine unique markets")

    dd_rows = 0
    row_paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-position-trajectory-forensics-2r-v2-rows.jsonl"
        )
    )
    if len(row_paths) != 9:
        raise ValueError("true-2R trajectory matrix requires nine row ledgers")
    for path in row_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    raw = json.loads(line)
                    if raw.get("in_true2r_max_drawdown_segment") is True:
                        dd_rows += 1

    report = {
        "identity": MATRIX_IDENTITY,
        "market_count": 9,
        "target_r": str(TARGET_R),
        "trades": sum(int(item["market_trades"]) for item in payloads),
        "losing_trades": sum(int(item["losing_trades"]) for item in payloads),
        "stop_losses": sum(int(item["stop_losses"]) for item in payloads),
        "stop_losses_with_strict_prior_favorable_excursion": sum(
            int(item["stop_losses_with_strict_prior_favorable_excursion"])
            for item in payloads
        ),
        "stop_losses_prior_mfe_ge_0_25r": sum(
            int(item["stop_losses_prior_mfe_ge_0_25r"]) for item in payloads
        ),
        "stop_losses_prior_mfe_ge_0_50r": sum(
            int(item["stop_losses_prior_mfe_ge_0_50r"]) for item in payloads
        ),
        "stop_losses_prior_mfe_ge_1_00r": sum(
            int(item["stop_losses_prior_mfe_ge_1_00r"]) for item in payloads
        ),
        "stop_losses_with_confirmed_improving_m3_swing": sum(
            int(item["stop_losses_with_confirmed_improving_m3_swing"])
            for item in payloads
        ),
        "stop_losses_with_confirmed_profitable_m3_swing": sum(
            int(item["stop_losses_with_confirmed_profitable_m3_swing"])
            for item in payloads
        ),
        "true2r_max_drawdown_r": str(EXPECTED_DD),
        "max_drawdown_losing_trades": dd_rows,
        "max_drawdown_stop_losses": sum(
            int(item["max_drawdown_stop_losses"]) for item in payloads
        ),
        "max_drawdown_stop_losses_prior_mfe_ge_0_25r": sum(
            int(item["max_drawdown_stop_losses_prior_mfe_ge_0_25r"])
            for item in payloads
        ),
        "max_drawdown_stop_losses_prior_mfe_ge_0_50r": sum(
            int(item["max_drawdown_stop_losses_prior_mfe_ge_0_50r"])
            for item in payloads
        ),
        "max_drawdown_stop_losses_prior_mfe_ge_1_00r": sum(
            int(item["max_drawdown_stop_losses_prior_mfe_ge_1_00r"])
            for item in payloads
        ),
        "max_drawdown_stop_losses_with_improving_m3_swing": sum(
            int(item["max_drawdown_stop_losses_with_improving_m3_swing"])
            for item in payloads
        ),
        "max_drawdown_stop_losses_with_profitable_m3_swing": sum(
            int(item["max_drawdown_stop_losses_with_profitable_m3_swing"])
            for item in payloads
        ),
        "by_market": {
            str(item["symbol"]): {
                "trades": item["market_trades"],
                "stop_losses": item["stop_losses"],
                "m3_improving": item[
                    "stop_losses_with_confirmed_improving_m3_swing"
                ],
                "m3_profitable": item[
                    "stop_losses_with_confirmed_profitable_m3_swing"
                ],
                "dd_stops": item["max_drawdown_stop_losses"],
                "dd_m3_improving": item[
                    "max_drawdown_stop_losses_with_improving_m3_swing"
                ],
                "dd_m3_profitable": item[
                    "max_drawdown_stop_losses_with_profitable_m3_swing"
                ],
            }
            for item in sorted(payloads, key=lambda row: str(row["symbol"]))
        },
        "exit_bar_excluded_from_trajectory_features": True,
        "m3_pivot_confirmation_required": True,
        "stop_policy_simulated": False,
        "break_even_policy_selected": False,
        "trailing_policy_selected": False,
        "current_outcome_used_to_discover_trajectory": False,
        "strategy_rules_changed": False,
        "cognitive_rules_changed": False,
        "entry_changed": False,
        "stop_changed": False,
        "target_changed": False,
        "max3_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "SIMULATE_ONLY_CAUSALLY_SUPPORTED_TRUE2R_PROTECTION_MECHANISMS",
    }
    return report


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = (
        output
        / "capitalizer-nine-market-cognitive-position-trajectory-forensics-2r-v2.json"
    )
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("rebase_root", type=Path)
    market.add_argument("target_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, rows = build_market_report(
            args.rebase_root,
            args.target_root,
            args.m1_root,
            symbol=str(args.symbol).upper(),
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
