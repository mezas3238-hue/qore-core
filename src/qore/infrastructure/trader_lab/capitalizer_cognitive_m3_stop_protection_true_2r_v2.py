"""True-2R M3 structural stop-protection ablation for Capitalizer.

This supersedes the earlier 1R-path M3 protection experiment for economic
interpretation. It consumes the corrected Target Sensitivity V2 ledgers, keeps
the exact frozen MAX3 population (948 trades), entries, original stops, 2R
targets and H1 deadlines, and changes only monotonic stop protection after
causally confirmed M3 pivots.

No trade is removed. No admission rule is added. No target is changed. A pivot
confirmed at time t can affect only an M1 bar opening at or after t. Same-minute
stop/target ambiguity remains stop-first, matching the frozen lifecycle.

Research only: no mode is selected or promoted.
"""

from __future__ import annotations

import argparse
import bisect
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v1 as target_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_target_sensitivity_2y_v2 as target_v2,
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

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_M3_STOP_PROTECTION_TRUE_2R_V2"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_COGNITIVE_M3_STOP_PROTECTION_TRUE_2R_V2"
SOURCE_TARGET_V2_RUN_ID = 36077843102
SOURCE_TARGET_V2_SHA = "a47de3b491b4468527c945d6eff3afbbaec82d4e"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
TARGET_R = Decimal("2.00")
EXPECTED_TRADES = 948
DD_CEILING_R = Decimal("6")


class ProtectionMode(StrEnum):
    ORIGINAL = "ORIGINAL"
    M3_SWING_IMPROVE = "M3_SWING_IMPROVE"
    M3_PROFITABLE_SWING_LOCK = "M3_PROFITABLE_SWING_LOCK"


@dataclass(frozen=True, slots=True)
class SimulatedTrade:
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    exit_at: str
    entry_price: str
    original_stop_price: str
    final_stop_price: str
    target_price: str
    realized_gross_r: str
    exit_reason: str
    mode: str
    stop_updates: int
    first_stop_update_at: str | None
    same_minute_stop_target_ambiguity: bool


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _load_control(root: Path) -> tuple[target_v1.TargetOutcome, ...]:
    raw = target_v2._load_outcomes(root)
    two_r = tuple(item for item in raw if Decimal(item.target_r) == TARGET_R)
    selected = target_v1._max3(two_r)
    if len(selected) != EXPECTED_TRADES:
        raise ValueError("true-2R stop protection requires frozen 948 MAX3 trades")
    return tuple(
        sorted(
            selected,
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
    )


def _candidate_stop(
    *,
    pivot: Pivot,
    side: CapitalizerSide,
    entry: Decimal,
    active_stop: Decimal,
    confirmation_close: Decimal,
    profitable_only: bool,
) -> Decimal | None:
    if side is CapitalizerSide.LONG:
        usable = pivot.kind == "LOW" and active_stop < pivot.price < confirmation_close
        profitable = pivot.price > entry
    else:
        usable = pivot.kind == "HIGH" and active_stop > pivot.price > confirmation_close
        profitable = pivot.price < entry
    if not usable:
        return None
    if profitable_only and not profitable:
        return None
    return pivot.price


def _finish(
    trade: target_v1.TargetOutcome,
    *,
    mode: ProtectionMode,
    exit_at: datetime,
    active_stop: Decimal,
    realized: Decimal,
    reason: str,
    stop_updates: int,
    first_update: datetime | None,
    ambiguity: bool,
) -> SimulatedTrade:
    return SimulatedTrade(
        symbol=trade.symbol,
        session=trade.session,
        operating_date=trade.operating_date,
        side=trade.side,
        entry_at=trade.entry_at,
        exit_at=exit_at.isoformat(),
        entry_price=trade.entry_price,
        original_stop_price=trade.stop_price,
        final_stop_price=str(active_stop),
        target_price=trade.target_price,
        realized_gross_r=str(realized),
        exit_reason=reason,
        mode=mode.value,
        stop_updates=stop_updates,
        first_stop_update_at=None if first_update is None else first_update.isoformat(),
        same_minute_stop_target_ambiguity=ambiguity,
    )


def _simulate(
    trade: target_v1.TargetOutcome,
    *,
    bars: tuple[CapitalizerM1Bar, ...],
    by_open: dict[datetime, int],
    pivots: tuple[Pivot, ...],
    pivot_confirmed: tuple[datetime, ...],
    close_by_at: dict[datetime, Decimal],
    mode: ProtectionMode,
) -> SimulatedTrade:
    entry_at = _aware(trade.entry_at)
    deadline = _aware(trade.h1_deadline)
    entry = Decimal(trade.entry_price)
    original_stop = Decimal(trade.stop_price)
    target = Decimal(trade.target_price)
    risk = abs(entry - original_stop)
    if risk <= 0:
        raise ValueError("true-2R stop protection requires positive risk")
    side = CapitalizerSide(trade.side)

    target_realized = (
        (target - entry) / risk
        if side is CapitalizerSide.LONG
        else (entry - target) / risk
    )
    if target_realized != TARGET_R:
        raise ValueError("true-2R target geometry drift")

    entry_index = by_open.get(entry_at)
    if entry_index is None:
        raise ValueError("true-2R stop protection entry missing from native M1")

    active_stop = original_stop
    stop_updates = 0
    first_update: datetime | None = None
    last_close = entry

    pivot_start = bisect.bisect_left(pivot_confirmed, entry_at)
    pivot_end = bisect.bisect_right(pivot_confirmed, deadline)
    eligible = tuple(
        pivot
        for pivot in pivots[pivot_start:pivot_end]
        if pivot.occurred_at >= entry_at
    )
    pivot_index = 0

    for index in range(entry_index, len(bars)):
        bar = bars[index]
        if index > entry_index and bar.opened_at >= deadline:
            delta = (
                bar.open - entry
                if side is CapitalizerSide.LONG
                else entry - bar.open
            )
            return _finish(
                trade,
                mode=mode,
                exit_at=bar.opened_at,
                active_stop=active_stop,
                realized=delta / risk,
                reason="TIME_EXIT",
                stop_updates=stop_updates,
                first_update=first_update,
                ambiguity=False,
            )

        while (
            mode is not ProtectionMode.ORIGINAL
            and pivot_index < len(eligible)
            and eligible[pivot_index].confirmed_at <= bar.opened_at
        ):
            pivot = eligible[pivot_index]
            confirmation_close = close_by_at.get(pivot.confirmed_at)
            if confirmation_close is not None:
                candidate = _candidate_stop(
                    pivot=pivot,
                    side=side,
                    entry=entry,
                    active_stop=active_stop,
                    confirmation_close=confirmation_close,
                    profitable_only=(
                        mode is ProtectionMode.M3_PROFITABLE_SWING_LOCK
                    ),
                )
                if candidate is not None:
                    active_stop = candidate
                    stop_updates += 1
                    if first_update is None:
                        first_update = pivot.confirmed_at
            pivot_index += 1

        last_close = bar.close
        stop_hit = (
            bar.low <= active_stop
            if side is CapitalizerSide.LONG
            else bar.high >= active_stop
        )
        target_hit = (
            bar.high >= target
            if side is CapitalizerSide.LONG
            else bar.low <= target
        )
        if stop_hit:
            realized = (
                (active_stop - entry) / risk
                if side is CapitalizerSide.LONG
                else (entry - active_stop) / risk
            )
            return _finish(
                trade,
                mode=mode,
                exit_at=bar.closed_at,
                active_stop=active_stop,
                realized=realized,
                reason="STOP",
                stop_updates=stop_updates,
                first_update=first_update,
                ambiguity=target_hit,
            )
        if target_hit:
            return _finish(
                trade,
                mode=mode,
                exit_at=bar.closed_at,
                active_stop=active_stop,
                realized=target_realized,
                reason="TARGET",
                stop_updates=stop_updates,
                first_update=first_update,
                ambiguity=False,
            )

    delta = (
        last_close - entry
        if side is CapitalizerSide.LONG
        else entry - last_close
    )
    return _finish(
        trade,
        mode=mode,
        exit_at=bars[-1].closed_at,
        active_stop=active_stop,
        realized=delta / risk,
        reason="SESSION_EXIT",
        stop_updates=stop_updates,
        first_update=first_update,
        ambiguity=False,
    )


def _metrics(rows: tuple[SimulatedTrade, ...]) -> dict[str, Any]:
    ordered = tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at), row.symbol))
    )
    values = tuple(Decimal(row.realized_gross_r) for row in ordered)
    gp = sum((value for value in values if value > 0), Decimal("0"))
    gl = -sum((value for value in values if value < 0), Decimal("0"))
    equity = Decimal("0")
    peak = Decimal("0")
    dd = Decimal("0")
    streak = 0
    max_streak = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        if value < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0
    return {
        "trades": len(ordered),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(row.exit_reason == "STOP" for row in ordered),
        "targets": sum(row.exit_reason == "TARGET" for row in ordered),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def _reproduction_mismatches(
    control: tuple[target_v1.TargetOutcome, ...],
    original: tuple[SimulatedTrade, ...],
) -> int:
    frozen = {
        (item.symbol, item.entry_at): item
        for item in control
    }
    mismatches = 0
    for row in original:
        source = frozen[(row.symbol, row.entry_at)]
        if (
            Decimal(row.realized_gross_r) != Decimal(source.realized_gross_r)
            or row.exit_reason != source.exit_reason
            or row.exit_at != source.exit_at
            or row.same_minute_stop_target_ambiguity
            != source.same_minute_stop_target_ambiguity
        ):
            mismatches += 1
    return mismatches


def build_market_report(
    target_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], dict[str, tuple[SimulatedTrade, ...]]]:
    control_all = _load_control(target_root)
    market = tuple(item for item in control_all if item.symbol == symbol)
    if not market:
        raise ValueError("true-2R stop protection found no market trades")

    start = min(_aware(item.entry_at) for item in market) - timedelta(hours=3)
    end = max(_aware(item.exit_at) for item in market) + timedelta(hours=3)
    bars = tuple(
        bar for bar in iter_cibo_m1(m1_root) if start <= bar.opened_at <= end
    )
    if not bars:
        raise ValueError("true-2R stop protection native M1 is empty")
    if {bar.symbol for bar in bars} != {symbol}:
        raise ValueError("true-2R stop protection M1 symbol mismatch")

    by_open = {bar.opened_at: index for index, bar in enumerate(bars)}
    close_by_at = {bar.closed_at: bar.close for bar in bars}
    pivots = _pivots(_aggregate_tf(bars, minutes=3))
    pivot_confirmed = tuple(pivot.confirmed_at for pivot in pivots)
    if tuple(sorted(pivot_confirmed)) != pivot_confirmed:
        raise ValueError("M3 pivots must be chronological")

    simulated: dict[str, tuple[SimulatedTrade, ...]] = {}
    for mode in ProtectionMode:
        simulated[mode.value] = tuple(
            _simulate(
                trade,
                bars=bars,
                by_open=by_open,
                pivots=pivots,
                pivot_confirmed=pivot_confirmed,
                close_by_at=close_by_at,
                mode=mode,
            )
            for trade in market
        )

    original = simulated[ProtectionMode.ORIGINAL.value]
    mismatches = _reproduction_mismatches(market, original)
    modes: dict[str, dict[str, Any]] = {}
    for mode in (
        ProtectionMode.M3_SWING_IMPROVE,
        ProtectionMode.M3_PROFITABLE_SWING_LOCK,
    ):
        rows = simulated[mode.value]
        changed = 0
        improved_losses = 0
        degraded_winners = 0
        for before, after in zip(original, rows, strict=True):
            before_r = Decimal(before.realized_gross_r)
            after_r = Decimal(after.realized_gross_r)
            changed += int(before_r != after_r)
            improved_losses += int(before_r < 0 and after_r > before_r)
            degraded_winners += int(before_r > 0 and after_r < before_r)
        modes[mode.value] = {
            "metrics": _metrics(rows),
            "changed_outcomes": changed,
            "improved_losing_outcomes": improved_losses,
            "degraded_winning_outcomes": degraded_winners,
            "trades_with_stop_updates": sum(row.stop_updates > 0 for row in rows),
        }

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_target_v2_run_id": SOURCE_TARGET_V2_RUN_ID,
        "source_target_v2_sha": SOURCE_TARGET_V2_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "market_trades": len(market),
        "original_metrics": _metrics(original),
        "original_reproduction_mismatches": mismatches,
        "modes": modes,
        "full_948_population_preserved_in_matrix": True,
        "m3_confirmation_causal": True,
        "stop_updates_monotonic_only": True,
        "stop_can_widen": False,
        "target_unchanged": True,
        "entry_unchanged": True,
        "admission_changed": False,
        "density_changed": False,
        "mode_selected": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, simulated


def write_market(
    report: dict[str, Any],
    simulated: dict[str, tuple[SimulatedTrade, ...]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-cognitive-m3-stop-protection-true-2r-v2"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for mode, rows in simulated.items():
        with (output / f"{stem}-{mode.lower()}-trades.jsonl").open(
            "w", encoding="utf-8"
        ) as handle:
            for row in rows:
                handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_reports(root: Path) -> list[dict[str, Any]]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-m3-stop-protection-true-2r-v2.json"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"true-2R stop matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_mode(
    root: Path,
    *,
    mode: ProtectionMode,
) -> tuple[SimulatedTrade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-m3-stop-protection-true-2r-v2-"
            f"{mode.value.lower()}-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"true-2R stop matrix requires 9 {mode.value} ledgers")
    rows: list[SimulatedTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(SimulatedTrade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at), row.symbol))
    )


def _by_bucket(
    rows: tuple[SimulatedTrade, ...],
    *,
    field: str,
) -> dict[str, dict[str, Any]]:
    keys = sorted({str(getattr(row, field)) for row in rows})
    return {
        key: _metrics(tuple(row for row in rows if str(getattr(row, field)) == key))
        for key in keys
    }


def build_matrix(root: Path) -> dict[str, Any]:
    reports = _load_reports(root)
    if any(int(report["original_reproduction_mismatches"]) != 0 for report in reports):
        raise ValueError("true-2R stop protection failed frozen lifecycle reproduction")

    ledgers = {
        mode.value: _load_mode(root, mode=mode)
        for mode in ProtectionMode
    }
    original = ledgers[ProtectionMode.ORIGINAL.value]
    if len(original) != EXPECTED_TRADES:
        raise ValueError("true-2R stop matrix requires 948 trades")

    original_metrics = _metrics(original)
    modes: dict[str, dict[str, Any]] = {}
    for mode in (
        ProtectionMode.M3_SWING_IMPROVE,
        ProtectionMode.M3_PROFITABLE_SWING_LOCK,
    ):
        rows = ledgers[mode.value]
        changed = 0
        improved_losses = 0
        degraded_winners = 0
        for before, after in zip(original, rows, strict=True):
            before_r = Decimal(before.realized_gross_r)
            after_r = Decimal(after.realized_gross_r)
            changed += int(before_r != after_r)
            improved_losses += int(before_r < 0 and after_r > before_r)
            degraded_winners += int(before_r > 0 and after_r < before_r)
        metrics = _metrics(rows)
        modes[mode.value] = {
            "metrics": metrics,
            "changed_outcomes": changed,
            "improved_losing_outcomes": improved_losses,
            "degraded_winning_outcomes": degraded_winners,
            "trades_with_stop_updates": sum(row.stop_updates > 0 for row in rows),
            "dd_at_or_below_6r": (
                Decimal(str(metrics["max_drawdown_r"])) <= DD_CEILING_R
            ),
            "pf_at_least_control": (
                metrics["profit_factor"] is not None
                and original_metrics["profit_factor"] is not None
                and Decimal(str(metrics["profit_factor"]))
                >= Decimal(str(original_metrics["profit_factor"]))
            ),
            "total_r_at_least_control": (
                Decimal(str(metrics["total_r"]))
                >= Decimal(str(original_metrics["total_r"]))
            ),
            "by_market": _by_bucket(rows, field="symbol"),
            "by_session": _by_bucket(rows, field="session"),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "source_target_v2_run_id": SOURCE_TARGET_V2_RUN_ID,
        "source_target_v2_sha": SOURCE_TARGET_V2_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_LABORATORY",
        "target_r": "2.00",
        "market_count": len(reports),
        "trades": len(original),
        "density_retention": "1",
        "original_metrics": original_metrics,
        "original_by_market": _by_bucket(original, field="symbol"),
        "original_by_session": _by_bucket(original, field="session"),
        "modes": modes,
        "m3_confirmation_causal": True,
        "stop_updates_monotonic_only": True,
        "stop_can_widen": False,
        "target_unchanged": True,
        "entry_unchanged": True,
        "admission_changed": False,
        "density_changed": False,
        "mode_selected": False,
        "automatic_promotion_allowed": False,
        "fresh_holdout_required_after_selection": True,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "EVALUATE_TRUE_2R_POSITION_PROTECTION_THEN_FRESH_HOLDOUT",
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-nine-market-cognitive-m3-stop-protection-true-2r-v2.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    market = sub.add_parser("market")
    market.add_argument("target_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True)
    matrix = sub.add_parser("matrix")
    matrix.add_argument("input_root", type=Path)
    matrix.add_argument("output", type=Path)
    args = parser.parse_args()

    if args.command == "market":
        report, simulated = build_market_report(
            args.target_root,
            args.m1_root,
            symbol=args.symbol,
        )
        write_market(report, simulated, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
