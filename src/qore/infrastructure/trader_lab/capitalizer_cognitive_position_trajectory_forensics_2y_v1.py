"""Current-identity position trajectory forensics for Capitalizer 2Y 1R.

The frozen 1R portfolio is preserved. This laboratory uses the immutable native
M1 clone to ask whether losing positions exposed *causal post-entry information*
before their original stop:

- strict-prior favorable excursion (exit/stop bar excluded);
- a fully confirmed M3 swing that could monotonically improve the original stop;
- a fully confirmed M3 swing beyond entry that could protect non-negative territory.

No stop is moved in this lab. No break-even/trailing threshold is selected.
The 31-trade third-slot diagnostic cohort is excluded only to inspect the
remaining 917-trade path whose DD is 6.5896R. The six STOPs inside that exact
residual DD episode are tagged separately.
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
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_residual_drawdown_forensics_2y_v1 as residual,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    Pivot,
    _aggregate_tf,
    _pivots,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_POSITION_TRAJECTORY_FORENSICS_2Y_V1"
MATRIX_IDENTITY = (
    "QORE_CAPITALIZER_NINE_MARKET_COGNITIVE_POSITION_TRAJECTORY_FORENSICS_2Y_V1"
)
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"


@dataclass(frozen=True, slots=True)
class PositionTrajectoryRow:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    entry_price: str
    stop_price: str
    realized_gross_r: str
    exit_reason: str
    strict_prior_mfe_r: str
    strict_prior_mae_r: str
    confirmed_improving_m3_swing: bool
    confirmed_profitable_m3_swing: bool
    first_improving_m3_confirmed_at: str | None
    first_profitable_m3_confirmed_at: str | None
    in_residual_drawdown_segment: bool
    current_outcome_used_to_discover_pivot: bool = False


def _join_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["symbol"]), str(row["entry_at"])


def _aware(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _load_binding(root: Path) -> tuple[dict[str, Any], ...]:
    report_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2.json")
    )
    row_paths = sorted(
        root.rglob("capitalizer-cognitive-evidence-binding-audit-2y-v2-rows.jsonl")
    )
    if len(report_paths) != 1 or len(row_paths) != 1:
        raise ValueError("position trajectory requires one V2 binding artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected V2 binding identity")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("position trajectory rejects future evidence")
    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("binding row must be object")
                rows.append(raw)
    return tuple(rows)


def _diagnostic_filtered(
    control: tuple[dict[str, Any], ...],
    binding_by_key: dict[tuple[str, str], dict[str, Any]],
) -> tuple[tuple[dict[str, Any], ...], frozenset[tuple[str, str]]]:
    blocked = {
        _join_key(row)
        for row in control
        if int(binding_by_key[_join_key(row)]["prior_same_session_selected"]) == 2
        and int(binding_by_key[_join_key(row)]["baseline_active_positions"]) == 0
    }
    if len(blocked) != 31:
        raise ValueError("position trajectory requires frozen 31-trade diagnostic cohort")
    filtered = tuple(row for row in control if _join_key(row) not in blocked)
    if len(filtered) != 917:
        raise ValueError("position trajectory diagnostic base must contain 917 trades")
    return filtered, frozenset(blocked)


def _residual_segment_keys(
    filtered: tuple[dict[str, Any], ...],
) -> frozenset[tuple[str, str]]:
    episode = residual._max_drawdown_episode(filtered)
    start = episode.segment_start_index
    end = episode.segment_end_index
    if start is None or end is None:
        raise ValueError("position trajectory requires residual DD segment")
    segment = filtered[start : end + 1]
    if len(segment) != 13:
        raise ValueError("position trajectory requires frozen 13-trade residual segment")
    return frozenset(_join_key(row) for row in segment)


def _bars_for_window(
    root: Path,
    *,
    start: datetime,
    end: datetime,
) -> tuple[CapitalizerM1Bar, ...]:
    bars = tuple(
        bar
        for bar in iter_cibo_m1(root)
        if start <= bar.opened_at <= end
    )
    if not bars:
        raise ValueError("position trajectory found no native M1 bars")
    return bars


def _strict_prior_path(
    trade: dict[str, Any],
    *,
    bars: tuple[CapitalizerM1Bar, ...],
    by_open: dict[datetime, int],
    by_close: dict[datetime, int],
) -> tuple[tuple[CapitalizerM1Bar, ...], int]:
    entry_at = _aware(trade["entry_at"])
    exit_at = _aware(trade["exit_at"])
    entry_index = by_open.get(entry_at)
    if entry_index is None:
        raise ValueError("position trajectory entry missing from M1")

    reason = str(trade["exit_reason"])
    if reason in {"STOP", "TARGET", "SESSION_EXIT"}:
        exit_index = by_close.get(exit_at)
    elif reason == "TIME_EXIT":
        exit_index = by_open.get(exit_at)
    else:
        raise ValueError(f"unsupported trajectory exit reason: {reason}")
    if exit_index is None or exit_index < entry_index:
        raise ValueError("position trajectory exit missing or precedes entry")

    # Exit/stop bar is excluded. It contains outcome information that was not
    # available strictly before the event.
    return tuple(bars[entry_index:exit_index]), exit_index


def _excursions(
    trade: dict[str, Any],
    prior: tuple[CapitalizerM1Bar, ...],
) -> tuple[Decimal, Decimal]:
    entry = Decimal(str(trade["entry_price"]))
    stop = Decimal(str(trade["stop_price"]))
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("position trajectory requires positive initial risk")
    if not prior:
        return Decimal("0"), Decimal("0")

    side = CapitalizerSide(str(trade["side"]))
    if side is CapitalizerSide.LONG:
        favorable = max(bar.high for bar in prior) - entry
        adverse = entry - min(bar.low for bar in prior)
    else:
        favorable = entry - min(bar.low for bar in prior)
        adverse = max(bar.high for bar in prior) - entry
    return (
        max(favorable, Decimal("0")) / risk,
        max(adverse, Decimal("0")) / risk,
    )


def _usable_pivots(
    trade: dict[str, Any],
    *,
    pivots: tuple[Pivot, ...],
    close_by_at: dict[datetime, Decimal],
) -> tuple[datetime | None, datetime | None]:
    entry_at = _aware(trade["entry_at"])
    exit_at = _aware(trade["exit_at"])
    entry = Decimal(str(trade["entry_price"]))
    stop = Decimal(str(trade["stop_price"]))
    side = CapitalizerSide(str(trade["side"]))

    improving: datetime | None = None
    profitable: datetime | None = None
    for pivot in pivots:
        if pivot.occurred_at < entry_at:
            continue
        if pivot.confirmed_at >= exit_at:
            continue
        current_close = close_by_at.get(pivot.confirmed_at)
        if current_close is None:
            continue

        if side is CapitalizerSide.LONG:
            usable = (
                pivot.kind == "LOW"
                and stop < pivot.price < current_close
            )
            locks_profit = usable and pivot.price > entry
        else:
            usable = (
                pivot.kind == "HIGH"
                and stop > pivot.price > current_close
            )
            locks_profit = usable and pivot.price < entry

        if usable and improving is None:
            improving = pivot.confirmed_at
        if locks_profit and profitable is None:
            profitable = pivot.confirmed_at
        if improving is not None and profitable is not None:
            break
    return improving, profitable


def _trajectory_row(
    trade: dict[str, Any],
    *,
    bars: tuple[CapitalizerM1Bar, ...],
    by_open: dict[datetime, int],
    by_close: dict[datetime, int],
    pivots: tuple[Pivot, ...],
    close_by_at: dict[datetime, Decimal],
    residual_keys: frozenset[tuple[str, str]],
) -> PositionTrajectoryRow:
    prior, _ = _strict_prior_path(
        trade,
        bars=bars,
        by_open=by_open,
        by_close=by_close,
    )
    mfe, mae = _excursions(trade, prior)
    improving, profitable = _usable_pivots(
        trade,
        pivots=pivots,
        close_by_at=close_by_at,
    )
    return PositionTrajectoryRow(
        symbol=str(trade["symbol"]),
        session=str(trade["session"]),
        operating_date=str(trade["operating_date"]),
        side=str(trade["side"]),
        entry_at=str(trade["entry_at"]),
        exit_at=str(trade["exit_at"]),
        entry_price=str(trade["entry_price"]),
        stop_price=str(trade["stop_price"]),
        realized_gross_r=str(trade["realized_gross_r"]),
        exit_reason=str(trade["exit_reason"]),
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
        in_residual_drawdown_segment=_join_key(trade) in residual_keys,
    )


def build_market_report(
    binding_root: Path,
    target_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], tuple[PositionTrajectoryRow, ...]]:
    bindings = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    binding_by_key = {_join_key(row): row for row in bindings}
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("position trajectory binding/control identities differ")

    filtered, _ = _diagnostic_filtered(control, binding_by_key)
    residual_keys = _residual_segment_keys(filtered)

    first_bar = next(iter_cibo_m1(m1_root), None)
    if first_bar is None:
        raise ValueError("position trajectory M1 artifact empty")
    symbol = first_bar.symbol
    market_trades = tuple(row for row in filtered if str(row["symbol"]) == symbol)
    if not market_trades:
        raise ValueError("position trajectory found no frozen market trades")

    start = min(_aware(row["entry_at"]) for row in market_trades) - timedelta(hours=1)
    end = max(_aware(row["exit_at"]) for row in market_trades) + timedelta(hours=1)
    bars = _bars_for_window(m1_root, start=start, end=end)
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("position trajectory M1 symbol drift")

    by_open = {bar.opened_at: index for index, bar in enumerate(bars)}
    by_close = {bar.closed_at: index for index, bar in enumerate(bars)}
    close_by_at = {bar.closed_at: bar.close for bar in bars}
    m3 = _aggregate_tf(bars, minutes=3)
    pivots = _pivots(m3)

    losses = tuple(
        row
        for row in market_trades
        if Decimal(str(row["realized_gross_r"])) < 0
    )
    trajectory_rows = tuple(
        _trajectory_row(
            row,
            bars=bars,
            by_open=by_open,
            by_close=by_close,
            pivots=pivots,
            close_by_at=close_by_at,
            residual_keys=residual_keys,
        )
        for row in losses
    )

    stops = tuple(row for row in trajectory_rows if row.exit_reason == "STOP")
    residual_stops = tuple(
        row
        for row in stops
        if row.in_residual_drawdown_segment
    )
    mfe_values = tuple(Decimal(row.strict_prior_mfe_r) for row in stops)

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_binding_run_id": SOURCE_BINDING_RUN_ID,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "development_window_role": "CONSUMED_LABORATORY",
        "filtered_market_trades": len(market_trades),
        "losing_trades": len(trajectory_rows),
        "stop_losses": len(stops),
        "stop_losses_with_strict_prior_favorable_excursion": sum(
            Decimal(row.strict_prior_mfe_r) > 0 for row in stops
        ),
        "stop_losses_with_confirmed_improving_m3_swing": sum(
            row.confirmed_improving_m3_swing for row in stops
        ),
        "stop_losses_with_confirmed_profitable_m3_swing": sum(
            row.confirmed_profitable_m3_swing for row in stops
        ),
        "median_strict_prior_mfe_r": (
            "0" if not mfe_values else str(median(mfe_values))
        ),
        "residual_drawdown_stop_losses": len(residual_stops),
        "residual_stop_losses_with_confirmed_improving_m3_swing": sum(
            row.confirmed_improving_m3_swing for row in residual_stops
        ),
        "residual_stop_losses_with_confirmed_profitable_m3_swing": sum(
            row.confirmed_profitable_m3_swing for row in residual_stops
        ),
        "exit_bar_excluded_from_trajectory_features": True,
        "m3_pivot_confirmation_required": True,
        "stop_policy_simulated": False,
        "break_even_policy_selected": False,
        "trailing_policy_selected": False,
        "target_changed": False,
        "entry_changed": False,
        "current_outcome_used_to_discover_pivot": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, trajectory_rows


def write_market(
    report: dict[str, Any],
    rows: tuple[PositionTrajectoryRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-cognitive-position-trajectory-forensics-2y-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob("capitalizer-*-cognitive-position-trajectory-forensics-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"position trajectory matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    return {
        "identity": MATRIX_IDENTITY,
        "market_count": len(reports),
        "filtered_trades": sum(int(row["filtered_market_trades"]) for row in reports),
        "losing_trades": sum(int(row["losing_trades"]) for row in reports),
        "stop_losses": sum(int(row["stop_losses"]) for row in reports),
        "stop_losses_with_strict_prior_favorable_excursion": sum(
            int(row["stop_losses_with_strict_prior_favorable_excursion"])
            for row in reports
        ),
        "stop_losses_with_confirmed_improving_m3_swing": sum(
            int(row["stop_losses_with_confirmed_improving_m3_swing"])
            for row in reports
        ),
        "stop_losses_with_confirmed_profitable_m3_swing": sum(
            int(row["stop_losses_with_confirmed_profitable_m3_swing"])
            for row in reports
        ),
        "residual_drawdown_stop_losses": sum(
            int(row["residual_drawdown_stop_losses"]) for row in reports
        ),
        "residual_stop_losses_with_confirmed_improving_m3_swing": sum(
            int(row["residual_stop_losses_with_confirmed_improving_m3_swing"])
            for row in reports
        ),
        "residual_stop_losses_with_confirmed_profitable_m3_swing": sum(
            int(row["residual_stop_losses_with_confirmed_profitable_m3_swing"])
            for row in reports
        ),
        "by_market": {
            str(row["symbol"]): {
                "filtered_trades": row["filtered_market_trades"],
                "stop_losses": row["stop_losses"],
                "improving_m3": row[
                    "stop_losses_with_confirmed_improving_m3_swing"
                ],
                "profitable_m3": row[
                    "stop_losses_with_confirmed_profitable_m3_swing"
                ],
                "residual_stops": row["residual_drawdown_stop_losses"],
                "residual_improving_m3": row[
                    "residual_stop_losses_with_confirmed_improving_m3_swing"
                ],
                "residual_profitable_m3": row[
                    "residual_stop_losses_with_confirmed_profitable_m3_swing"
                ],
            }
            for row in sorted(reports, key=lambda item: str(item["symbol"]))
        },
        "exit_bar_excluded_from_trajectory_features": True,
        "m3_pivot_confirmation_required": True,
        "stop_policy_simulated": False,
        "break_even_policy_selected": False,
        "trailing_policy_selected": False,
        "target_changed": False,
        "entry_changed": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "SIMULATE_ONLY_IF_CAUSAL_PROTECTION_CAPACITY_IS_MATERIAL",
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-nine-market-cognitive-position-trajectory-forensics-2y-v1.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("binding_root", type=Path)
    market.add_argument("target_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, rows = build_market_report(
            args.binding_root,
            args.target_root,
            args.m1_root,
        )
        write_market(report, rows, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
