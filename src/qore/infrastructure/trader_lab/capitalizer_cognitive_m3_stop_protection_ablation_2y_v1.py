"""Current-identity M3 monotonic stop-protection ablation for Capitalizer 2Y 1R.

Consumes the frozen 1R ledger and immutable native M1. The diagnostic 31-trade
third-slot cohort is removed exactly as in the residual-DD research, leaving the
917-trade base.

Two position-management ablations are simulated without changing entries or 1R targets:
- M3_SWING_IMPROVE: once a fully confirmed M3 pivot can monotonically tighten
  the original stop, activate it from the next causally available M1 bar.
- M3_PROFITABLE_SWING_LOCK: same, but only when the confirmed M3 pivot is already
  beyond entry and therefore locks non-negative territory.

A pivot confirmed by an M3 close cannot protect that confirming bar. The stop
becomes active only for M1 bars whose opened_at is >= pivot.confirmed_at.
Stop-first ambiguity is preserved.

This is consumed-window ablation research only. No mode is selected/promoted.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v1 as binding_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_evidence_binding_audit_2y_v2 as binding_v2,
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

IDENTITY = "QORE_CAPITALIZER_COGNITIVE_M3_STOP_PROTECTION_ABLATION_2Y_V1"
MATRIX_IDENTITY = "QORE_CAPITALIZER_NINE_MARKET_COGNITIVE_M3_STOP_PROTECTION_ABLATION_2Y_V1"
SOURCE_BINDING_RUN_ID = 36065651404
SOURCE_BINDING_SHA = "1d910f5c3550ac481c28390671a86ceb011597e3"
SOURCE_TARGET_RUN_ID = 36055792484
SOURCE_TARGET_SHA = "a66ab11c22efbefb61756db3f0062c3c51a2a825"
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"


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
        raise ValueError("M3 stop ablation requires one V2 binding artifact")
    report = json.loads(report_paths[0].read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("identity") != binding_v2.IDENTITY:
        raise ValueError("unexpected V2 binding identity")
    if int(report.get("future_evidence_violations", -1)) != 0:
        raise ValueError("M3 stop ablation rejects future evidence")
    rows: list[dict[str, Any]] = []
    with row_paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("binding row must be object")
                rows.append(raw)
    return tuple(rows)


def _filtered_base(
    control: tuple[dict[str, Any], ...],
    binding_by_key: dict[tuple[str, str], dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    blocked = {
        _join_key(row)
        for row in control
        if int(binding_by_key[_join_key(row)]["prior_same_session_selected"]) == 2
        and int(binding_by_key[_join_key(row)]["baseline_active_positions"]) == 0
    }
    if len(blocked) != 31:
        raise ValueError("M3 stop ablation requires frozen 31-trade diagnostic cohort")
    filtered = tuple(row for row in control if _join_key(row) not in blocked)
    if len(filtered) != 917:
        raise ValueError("M3 stop ablation base must contain 917 trades")
    return filtered


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


def _simulate(
    trade: dict[str, Any],
    *,
    bars: tuple[CapitalizerM1Bar, ...],
    by_open: dict[datetime, int],
    pivots: tuple[Pivot, ...],
    close_by_at: dict[datetime, Decimal],
    mode: ProtectionMode,
) -> SimulatedTrade:
    entry_at = _aware(trade["entry_at"])
    deadline = _aware(trade["h1_deadline"])
    entry = Decimal(str(trade["entry_price"]))
    original_stop = Decimal(str(trade["stop_price"]))
    target = Decimal(str(trade["target_price"]))
    risk = abs(entry - original_stop)
    if risk <= 0:
        raise ValueError("M3 stop ablation requires positive risk")
    side = CapitalizerSide(str(trade["side"]))
    entry_index = by_open.get(entry_at)
    if entry_index is None:
        raise ValueError("M3 stop ablation entry missing from M1")

    active_stop = original_stop
    stop_updates = 0
    first_update: datetime | None = None
    last_close = entry
    held = 0
    pivot_index = 0
    eligible_pivots = tuple(
        pivot for pivot in pivots if pivot.occurred_at >= entry_at
    )

    for index in range(entry_index, len(bars)):
        bar = bars[index]
        if index > entry_index and bar.opened_at >= deadline:
            delta = (
                bar.open - entry
                if side is CapitalizerSide.LONG
                else entry - bar.open
            )
            return SimulatedTrade(
                symbol=str(trade["symbol"]),
                session=str(trade["session"]),
                operating_date=str(trade["operating_date"]),
                side=side.value,
                entry_at=entry_at.isoformat(),
                exit_at=bar.opened_at.isoformat(),
                entry_price=str(entry),
                original_stop_price=str(original_stop),
                final_stop_price=str(active_stop),
                target_price=str(target),
                realized_gross_r=str(delta / risk),
                exit_reason="TIME_EXIT",
                mode=mode.value,
                stop_updates=stop_updates,
                first_stop_update_at=(
                    None if first_update is None else first_update.isoformat()
                ),
                same_minute_stop_target_ambiguity=False,
            )

        # A pivot confirmed at t is known before an M1 bar opening at t.
        # It can therefore affect this bar, but never any earlier bar.
        while (
            mode is not ProtectionMode.ORIGINAL
            and pivot_index < len(eligible_pivots)
            and eligible_pivots[pivot_index].confirmed_at <= bar.opened_at
        ):
            pivot = eligible_pivots[pivot_index]
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

        held += 1
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
            return SimulatedTrade(
                symbol=str(trade["symbol"]),
                session=str(trade["session"]),
                operating_date=str(trade["operating_date"]),
                side=side.value,
                entry_at=entry_at.isoformat(),
                exit_at=bar.closed_at.isoformat(),
                entry_price=str(entry),
                original_stop_price=str(original_stop),
                final_stop_price=str(active_stop),
                target_price=str(target),
                realized_gross_r=str(realized),
                exit_reason="STOP",
                mode=mode.value,
                stop_updates=stop_updates,
                first_stop_update_at=(
                    None if first_update is None else first_update.isoformat()
                ),
                same_minute_stop_target_ambiguity=target_hit,
            )
        if target_hit:
            return SimulatedTrade(
                symbol=str(trade["symbol"]),
                session=str(trade["session"]),
                operating_date=str(trade["operating_date"]),
                side=side.value,
                entry_at=entry_at.isoformat(),
                exit_at=bar.closed_at.isoformat(),
                entry_price=str(entry),
                original_stop_price=str(original_stop),
                final_stop_price=str(active_stop),
                target_price=str(target),
                realized_gross_r="1",
                exit_reason="TARGET",
                mode=mode.value,
                stop_updates=stop_updates,
                first_stop_update_at=(
                    None if first_update is None else first_update.isoformat()
                ),
                same_minute_stop_target_ambiguity=False,
            )

    delta = (
        last_close - entry
        if side is CapitalizerSide.LONG
        else entry - last_close
    )
    return SimulatedTrade(
        symbol=str(trade["symbol"]),
        session=str(trade["session"]),
        operating_date=str(trade["operating_date"]),
        side=side.value,
        entry_at=entry_at.isoformat(),
        exit_at=bars[-1].closed_at.isoformat(),
        entry_price=str(entry),
        original_stop_price=str(original_stop),
        final_stop_price=str(active_stop),
        target_price=str(target),
        realized_gross_r=str(delta / risk),
        exit_reason="SESSION_EXIT",
        mode=mode.value,
        stop_updates=stop_updates,
        first_stop_update_at=(
            None if first_update is None else first_update.isoformat()
        ),
        same_minute_stop_target_ambiguity=False,
    )


def _metrics(rows: tuple[SimulatedTrade, ...]) -> dict[str, Any]:
    values = tuple(Decimal(row.realized_gross_r) for row in rows)
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
        "trades": len(rows),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "stops": sum(row.exit_reason == "STOP" for row in rows),
        "total_r": str(sum(values, Decimal("0"))),
        "profit_factor": None if gl == 0 else str(gp / gl),
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
    }


def build_market_report(
    binding_root: Path,
    target_root: Path,
    m1_root: Path,
) -> tuple[dict[str, Any], dict[str, tuple[SimulatedTrade, ...]]]:
    bindings = _load_binding(binding_root)
    control = binding_v1._load_control(target_root)
    binding_by_key = {_join_key(row): row for row in bindings}
    if {_join_key(row) for row in control} != set(binding_by_key):
        raise ValueError("M3 stop ablation binding/control identities differ")
    filtered = _filtered_base(control, binding_by_key)

    first = next(iter_cibo_m1(m1_root), None)
    if first is None:
        raise ValueError("M3 stop ablation M1 artifact empty")
    symbol = first.symbol
    market = tuple(row for row in filtered if str(row["symbol"]) == symbol)
    if not market:
        raise ValueError("M3 stop ablation found no market trades")

    start = min(_aware(row["entry_at"]) for row in market) - timedelta(hours=1)
    end = max(_aware(row["exit_at"]) for row in market) + timedelta(hours=1)
    bars = tuple(
        bar for bar in iter_cibo_m1(m1_root) if start <= bar.opened_at <= end
    )
    by_open = {bar.opened_at: index for index, bar in enumerate(bars)}
    close_by_at = {bar.closed_at: bar.close for bar in bars}
    pivots = _pivots(_aggregate_tf(bars, minutes=3))

    simulated: dict[str, tuple[SimulatedTrade, ...]] = {}
    for mode in ProtectionMode:
        simulated[mode.value] = tuple(
            _simulate(
                trade,
                bars=bars,
                by_open=by_open,
                pivots=pivots,
                close_by_at=close_by_at,
                mode=mode,
            )
            for trade in market
        )

    original = simulated[ProtectionMode.ORIGINAL.value]
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
            if before_r != after_r:
                changed += 1
            if before_r < 0 and after_r > before_r:
                improved_losses += 1
            if before_r > 0 and after_r < before_r:
                degraded_winners += 1
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
        "source_binding_run_id": SOURCE_BINDING_RUN_ID,
        "source_target_run_id": SOURCE_TARGET_RUN_ID,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "development_window_role": "CONSUMED_LABORATORY",
        "market_trades": len(market),
        "original_metrics": _metrics(original),
        "modes": modes,
        "m3_confirmation_causal": True,
        "stop_updates_monotonic_only": True,
        "stop_can_widen": False,
        "target_unchanged": True,
        "entry_unchanged": True,
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
    stem = f"capitalizer-{symbol}-cognitive-m3-stop-protection-ablation-2y-v1"
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
        root.rglob("capitalizer-*-cognitive-m3-stop-protection-ablation-2y-v1.json")
    )
    if len(paths) != 9:
        raise ValueError(f"M3 stop ablation matrix requires 9 reports, got {len(paths)}")
    return [dict(json.loads(path.read_text(encoding="utf-8"))) for path in paths]


def _load_mode(root: Path, *, mode: ProtectionMode) -> tuple[SimulatedTrade, ...]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-cognitive-m3-stop-protection-ablation-2y-v1-"
            f"{mode.value.lower()}-trades.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(f"M3 stop ablation requires 9 {mode.value} ledgers")
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
    reports = _load_reports(root)
    ledgers = {mode.value: _load_mode(root, mode=mode) for mode in ProtectionMode}
    original = ledgers[ProtectionMode.ORIGINAL.value]
    if len(original) != 917:
        raise ValueError("M3 stop ablation aggregate requires 917 original trades")

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
            if before_r != after_r:
                changed += 1
            if before_r < 0 and after_r > before_r:
                improved_losses += 1
            if before_r > 0 and after_r < before_r:
                degraded_winners += 1
        modes[mode.value] = {
            "metrics": _metrics(rows),
            "changed_outcomes": changed,
            "improved_losing_outcomes": improved_losses,
            "degraded_winning_outcomes": degraded_winners,
            "trades_with_stop_updates": sum(row.stop_updates > 0 for row in rows),
        }

    return {
        "identity": MATRIX_IDENTITY,
        "market_count": len(reports),
        "trades": len(original),
        "original_metrics": _metrics(original),
        "modes": modes,
        "m3_confirmation_causal": True,
        "stop_updates_monotonic_only": True,
        "stop_can_widen": False,
        "target_unchanged": True,
        "entry_unchanged": True,
        "mode_selected": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "ACCEPT_OR_REJECT_M3_PROTECTION_AS_POSITION_INTELLIGENCE_RESEARCH",
    }


def write_matrix(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output / "capitalizer-nine-market-cognitive-m3-stop-protection-ablation-2y-v1.json"
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
        report, simulated = build_market_report(
            args.binding_root,
            args.target_root,
            args.m1_root,
        )
        write_market(report, simulated, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report = build_matrix(args.input_root)
    write_matrix(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
