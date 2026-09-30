"""Causal R-milestone position protection for Capitalizer true-2R.

This laboratory attacks the observed stop-loss anatomy directly. It preserves
all 948 frozen entries, original structural stops, fixed 2R targets, H1
deadlines, and MAX3 selection. Only monotonic post-entry protection changes.

A protection update is authorized only after a completed M1 bar has already
shown the required favorable excursion. The update becomes effective on the
NEXT M1 bar. The bar that creates the milestone is always evaluated first with
the previously active stop and the frozen stop-first ambiguity rule.

This makes the ablation causal and fail-conservative. No future pivot, terminal
outcome, MFE label, or current-bar ordering is used.
"""

from __future__ import annotations

import argparse
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
from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_strict_htf_gate_1y_v1 import (
    _index_day_inputs,
)

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_R_MILESTONE_PROTECTION_2R_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_COGNITIVE_R_MILESTONE_PROTECTION_2R_V1"
SOURCE_TARGET_RUN_ID = 36077843102
SOURCE_TARGET_SHA = "a47de3b491b4468527c945d6eff3afbbaec82d4e"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"
TARGET_R = Decimal("2.00")
EXPECTED_TRADES = 948


class ProtectionMode(StrEnum):
    ORIGINAL = "ORIGINAL"
    BE_AFTER_050 = "BE_AFTER_050"
    BE_AFTER_075 = "BE_AFTER_075"
    BE_AFTER_100 = "BE_AFTER_100"
    LOCK025_AFTER_075 = "LOCK025_AFTER_075"
    LOCK025_AFTER_100 = "LOCK025_AFTER_100"
    LOCK050_AFTER_100 = "LOCK050_AFTER_100"
    STAGED_050_100_150 = "STAGED_050_100_150"
    STAGED_075_125_150 = "STAGED_075_125_150"


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
    protection_updates: int
    first_protection_at: str | None
    max_milestone_r_seen_before_exit: str
    same_minute_stop_target_ambiguity: bool


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _load_control(root: Path) -> tuple[target_v1.TargetOutcome, ...]:
    outcomes = target_v2._load_outcomes(root)
    two_r = tuple(item for item in outcomes if Decimal(item.target_r) == TARGET_R)
    selected = target_v1._max3(two_r)
    ordered = tuple(
        sorted(
            selected,
            key=lambda item: (_aware(item.entry_at), item.symbol),
        )
    )
    if len(ordered) != EXPECTED_TRADES:
        raise ValueError("R-milestone protection requires frozen 948-trade 2R set")
    return ordered


def _favorable_r(
    bar: CapitalizerM1Bar,
    *,
    side: CapitalizerSide,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    favorable = (
        bar.high - entry
        if side is CapitalizerSide.LONG
        else entry - bar.low
    )
    return max(Decimal("0"), favorable / risk)


def _stop_for_lock(
    *,
    side: CapitalizerSide,
    entry: Decimal,
    risk: Decimal,
    lock_r: Decimal,
) -> Decimal:
    return (
        entry + lock_r * risk
        if side is CapitalizerSide.LONG
        else entry - lock_r * risk
    )


def _desired_lock(mode: ProtectionMode, milestone: Decimal) -> Decimal | None:
    if mode is ProtectionMode.ORIGINAL:
        return None
    if mode is ProtectionMode.BE_AFTER_050:
        return Decimal("0") if milestone >= Decimal("0.50") else None
    if mode is ProtectionMode.BE_AFTER_075:
        return Decimal("0") if milestone >= Decimal("0.75") else None
    if mode is ProtectionMode.BE_AFTER_100:
        return Decimal("0") if milestone >= Decimal("1.00") else None
    if mode is ProtectionMode.LOCK025_AFTER_075:
        return Decimal("0.25") if milestone >= Decimal("0.75") else None
    if mode is ProtectionMode.LOCK025_AFTER_100:
        return Decimal("0.25") if milestone >= Decimal("1.00") else None
    if mode is ProtectionMode.LOCK050_AFTER_100:
        return Decimal("0.50") if milestone >= Decimal("1.00") else None
    if mode is ProtectionMode.STAGED_050_100_150:
        if milestone >= Decimal("1.50"):
            return Decimal("0.75")
        if milestone >= Decimal("1.00"):
            return Decimal("0.25")
        if milestone >= Decimal("0.50"):
            return Decimal("0")
        return None
    if mode is ProtectionMode.STAGED_075_125_150:
        if milestone >= Decimal("1.50"):
            return Decimal("0.50")
        if milestone >= Decimal("1.25"):
            return Decimal("0.25")
        if milestone >= Decimal("0.75"):
            return Decimal("0")
        return None
    raise ValueError(f"unknown protection mode {mode}")


def _is_improvement(
    *,
    side: CapitalizerSide,
    candidate: Decimal,
    active: Decimal,
) -> bool:
    return candidate > active if side is CapitalizerSide.LONG else candidate < active


def _finish(
    trade: target_v1.TargetOutcome,
    *,
    mode: ProtectionMode,
    exit_at: datetime,
    active_stop: Decimal,
    realized: Decimal,
    reason: str,
    updates: int,
    first_update: datetime | None,
    milestone: Decimal,
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
        protection_updates=updates,
        first_protection_at=(
            None if first_update is None else first_update.isoformat()
        ),
        max_milestone_r_seen_before_exit=str(milestone),
        same_minute_stop_target_ambiguity=ambiguity,
    )


def _simulate(
    trade: target_v1.TargetOutcome,
    *,
    bars: tuple[CapitalizerM1Bar, ...],
    by_open: dict[datetime, int],
    mode: ProtectionMode,
) -> SimulatedTrade:
    entry_at = _aware(trade.entry_at)
    deadline = _aware(trade.h1_deadline)
    entry = Decimal(trade.entry_price)
    original_stop = Decimal(trade.stop_price)
    target = Decimal(trade.target_price)
    risk = abs(entry - original_stop)
    if risk <= 0:
        raise ValueError("R-milestone protection requires positive risk")
    side = CapitalizerSide(trade.side)
    entry_index = by_open.get(entry_at)
    if entry_index is None:
        raise ValueError("R-milestone entry missing from native M1")

    active_stop = original_stop
    pending_stop: Decimal | None = None
    updates = 0
    first_update: datetime | None = None
    milestone = Decimal("0")
    last_close = entry

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
                updates=updates,
                first_update=first_update,
                milestone=milestone,
                ambiguity=False,
            )

        if pending_stop is not None and _is_improvement(
            side=side,
            candidate=pending_stop,
            active=active_stop,
        ):
            active_stop = pending_stop
            updates += 1
            if first_update is None:
                first_update = bar.opened_at
        pending_stop = None

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
                updates=updates,
                first_update=first_update,
                milestone=milestone,
                ambiguity=target_hit,
            )
        if target_hit:
            return _finish(
                trade,
                mode=mode,
                exit_at=bar.closed_at,
                active_stop=active_stop,
                realized=TARGET_R,
                reason="TARGET",
                updates=updates,
                first_update=first_update,
                milestone=max(milestone, TARGET_R),
                ambiguity=False,
            )

        milestone = max(
            milestone,
            _favorable_r(bar, side=side, entry=entry, risk=risk),
        )
        lock_r = _desired_lock(mode, milestone)
        if lock_r is not None:
            candidate = _stop_for_lock(
                side=side,
                entry=entry,
                risk=risk,
                lock_r=lock_r,
            )
            if _is_improvement(side=side, candidate=candidate, active=active_stop):
                pending_stop = candidate

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
        updates=updates,
        first_update=first_update,
        milestone=milestone,
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
    by_key = {(item.symbol, item.entry_at): item for item in control}
    mismatches = 0
    for row in original:
        source = by_key[(row.symbol, row.entry_at)]
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
        raise ValueError("R-milestone protection found no market trades")

    start = min(_aware(item.entry_at) for item in market) - timedelta(hours=1)
    end = max(_aware(item.exit_at) for item in market) + timedelta(hours=1)
    bars = tuple(
        bar for bar in iter_cibo_m1(m1_root) if start <= bar.opened_at <= end
    )
    if not bars:
        raise ValueError("R-milestone protection native M1 empty")
    if {bar.symbol for bar in bars} != {symbol}:
        raise ValueError("R-milestone M1 symbol mismatch")
    sessions = {CapitalizerSession(item.session) for item in market}
    if len(sessions) != 1:
        raise ValueError("R-milestone market must have one session")
    session = next(iter(sessions))
    execution_by_day, _ = _index_day_inputs(bars, session=session)

    simulated_lists: dict[str, list[SimulatedTrade]] = {
        mode.value: [] for mode in ProtectionMode
    }
    for trade in market:
        execution = execution_by_day.get(trade.operating_date, ())
        if not execution:
            raise ValueError("R-milestone missing execution day")
        by_open = {
            bar.opened_at: index for index, bar in enumerate(execution)
        }
        for mode in ProtectionMode:
            simulated_lists[mode.value].append(
                _simulate(
                    trade,
                    bars=execution,
                    by_open=by_open,
                    mode=mode,
                )
            )
    ledgers = {
        mode: tuple(rows) for mode, rows in simulated_lists.items()
    }
    original = ledgers[ProtectionMode.ORIGINAL.value]
    mismatches = _reproduction_mismatches(market, original)

    modes: dict[str, dict[str, Any]] = {}
    for mode in ProtectionMode:
        rows = ledgers[mode.value]
        modes[mode.value] = {
            "metrics": _metrics(rows),
            "trades_with_protection_updates": sum(
                row.protection_updates > 0 for row in rows
            ),
            "changed_outcomes_vs_original": sum(
                Decimal(before.realized_gross_r) != Decimal(after.realized_gross_r)
                for before, after in zip(original, rows, strict=True)
            ),
        }

    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_POSITION_RESEARCH",
        "target_r": "2.00",
        "market_trades": len(market),
        "original_reproduction_mismatches": mismatches,
        "modes": modes,
        "entries_changed": False,
        "original_stop_changed_at_entry": False,
        "target_changed": False,
        "max3_changed": False,
        "protection_next_bar_only": True,
        "same_bar_order_inferred": False,
        "stop_can_widen": False,
        "mode_selected": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
    }, ledgers


def write_market(
    report: dict[str, Any],
    ledgers: dict[str, tuple[SimulatedTrade, ...]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-cognitive-r-milestone-protection-2r-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for mode, rows in ledgers.items():
        with (output / f"{stem}-{mode.lower()}-trades.jsonl").open(
            "w", encoding="utf-8"
        ) as handle:
            for row in rows:
                handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_mode(
    root: Path,
    *,
    mode: ProtectionMode,
) -> tuple[SimulatedTrade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-r-milestone-protection-2r-v1-"
            f"{mode.value.lower()}-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"R-milestone matrix requires 9 {mode.value} ledgers")
    rows: list[SimulatedTrade] = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(SimulatedTrade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at), row.symbol))
    )


def build_matrix(root: Path) -> dict[str, Any]:
    reports = sorted(root.rglob("capitalizer-*-cognitive-r-milestone-protection-2r-v1.json"))
    if len(reports) != 9:
        raise ValueError("R-milestone matrix requires 9 market reports")
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in reports]
    if any(int(item["original_reproduction_mismatches"]) != 0 for item in payloads):
        raise ValueError("R-milestone baseline reproduction failed")

    ledgers = {mode.value: _load_mode(root, mode=mode) for mode in ProtectionMode}
    original = ledgers[ProtectionMode.ORIGINAL.value]
    if len(original) != EXPECTED_TRADES:
        raise ValueError("R-milestone matrix requires 948 trades")
    control = _metrics(original)

    modes: dict[str, dict[str, Any]] = {}
    for mode in ProtectionMode:
        rows = ledgers[mode.value]
        metrics = _metrics(rows)
        modes[mode.value] = {
            "metrics": metrics,
            "trades_with_protection_updates": sum(
                row.protection_updates > 0 for row in rows
            ),
            "changed_outcomes_vs_original": sum(
                Decimal(before.realized_gross_r) != Decimal(after.realized_gross_r)
                for before, after in zip(original, rows, strict=True)
            ),
            "pf_at_least_control": (
                metrics["profit_factor"] is not None
                and control["profit_factor"] is not None
                and Decimal(str(metrics["profit_factor"]))
                >= Decimal(str(control["profit_factor"]))
            ),
            "total_r_at_least_control": (
                Decimal(str(metrics["total_r"])) >= Decimal(str(control["total_r"]))
            ),
            "dd_at_or_below_6r": Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6"),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_target_sha": SOURCE_TARGET_SHA,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "development_window_role": "CONSUMED_POSITION_RESEARCH",
        "market_count": 9,
        "trades": EXPECTED_TRADES,
        "density_retention": "1",
        "control_metrics": control,
        "modes": modes,
        "entries_changed": False,
        "original_stop_changed_at_entry": False,
        "target_changed": False,
        "max3_changed": False,
        "protection_next_bar_only": True,
        "same_bar_order_inferred": False,
        "stop_can_widen": False,
        "mode_selected": False,
        "automatic_promotion_allowed": False,
        "fresh_holdout_required_after_selection": True,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "EVALUATE_CAUSAL_BE_AND_LOCK_FRONTIER",
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-nine-market-cognitive-r-milestone-protection-2r-v1.json"
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
        report, ledgers = build_market_report(
            args.target_root,
            args.m1_root,
            symbol=args.symbol,
        )
        write_market(report, ledgers, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
