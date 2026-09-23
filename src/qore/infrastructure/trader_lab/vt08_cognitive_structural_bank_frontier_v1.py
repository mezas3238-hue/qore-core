"""VT08-specific structural banking frontier inspired by Core/VT31 architecture.

This research layer does NOT copy NAS100 target definitions. VT08 derives its
own structural path from the frozen source H4:

- intermediate structural equilibrium = midpoint of VT08 reference H4;
- structural destination = opposite reference-H4 extreme in trade direction;
- candidate applies only when entry -> equilibrium -> destination is ordered
  forward in the trade direction;
- 50% banks at equilibrium;
- remaining 50% banks at the VT08 structural destination if reached on a later
  M15, otherwise it preserves the original VT08 terminal path;
- initial stop is unchanged and can never widen;
- same-M15 stop has precedence over favorable events;
- no future label or terminal PnL is a runtime input.

The 50/50 arm is a single predeclared research mechanism, not a parameter scan.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    load_market_evidence,
    metrics,
    model_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    evaluate_expansion_at_entry_indexed,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
    program_fingerprint,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_structural_bank_frontier.v1"
TRAIN_FRACTION: Final = Decimal("0.70")
EQ_FRACTION: Final = Decimal("0.50")
DESTINATION_FRACTION: Final = Decimal("0.50")
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class StructuralBankTrade:
    baseline: ExpansionTrade
    structural_r: Decimal
    status: str
    equilibrium_r: Decimal | None
    destination_r: Decimal | None

    def as_trade(self) -> ExpansionTrade:
        return ExpansionTrade(
            symbol=self.baseline.symbol,
            signal_at=self.baseline.signal_at,
            exited_at=self.baseline.exited_at,
            anchor_hour_ny=self.baseline.anchor_hour_ny,
            side=self.baseline.side,
            entry=self.baseline.entry,
            stop=self.baseline.stop,
            target=self.baseline.target,
            exit_price=self.baseline.exit_price,
            exit_reason=f"structural-bank:{self.status}",
            r_multiple=self.structural_r,
        )

    def payload(self) -> dict[str, object]:
        return {
            "symbol": self.baseline.symbol,
            "signal_at": self.baseline.signal_at.astimezone(UTC).isoformat(),
            "anchor_hour_ny": self.baseline.anchor_hour_ny,
            "side": self.baseline.side.value,
            "baseline_r": format(self.baseline.r_multiple, "f"),
            "structural_r": format(self.structural_r, "f"),
            "status": self.status,
            "equilibrium_r": (
                None if self.equilibrium_r is None else format(self.equilibrium_r, "f")
            ),
            "destination_r": (
                None if self.destination_r is None else format(self.destination_r, "f")
            ),
        }


def _forward(side: DemoTradingSetupSide, *, entry: Decimal, level: Decimal) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return level > entry
    return level < entry


def _ordered_path(
    side: DemoTradingSetupSide,
    *,
    entry: Decimal,
    equilibrium: Decimal,
    destination: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return entry < equilibrium < destination
    return entry > equilibrium > destination


def _touches(
    bar: Vt08B01Bar,
    *,
    side: DemoTradingSetupSide,
    level: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return bar.high >= level
    return bar.low <= level


def _stop_touched(
    bar: Vt08B01Bar,
    *,
    side: DemoTradingSetupSide,
    stop: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return bar.low <= stop
    return bar.high >= stop


def _r(
    side: DemoTradingSetupSide,
    *,
    entry: Decimal,
    stop: Decimal,
    level: Decimal,
) -> Decimal:
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        raise ValueError("VT08 structural bank requires positive risk")
    if side is DemoTradingSetupSide.LONG:
        return (level - entry) / risk
    return (entry - level) / risk


def _window(
    candidate: Vt08ExpansionCandidate,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> tuple[Vt08B01Bar, ...] | None:
    start = candidate.decision_at.astimezone(UTC)
    end = (start.astimezone(_NY) + timedelta(hours=4)).astimezone(UTC)
    if end - start != timedelta(hours=4):
        return None
    rows: list[Vt08B01Bar] = []
    cursor = start
    while cursor < end:
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at != cursor + timedelta(minutes=15):
            return None
        rows.append(bar)
        cursor += timedelta(minutes=15)
    return tuple(rows) if cursor == end else None


def simulate_structural_bank(
    candidate: Vt08ExpansionCandidate,
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> StructuralBankTrade | None:
    baseline = model_trade(candidate, bars_by_open=bars_by_open)
    if baseline is None:
        return None

    reference = candidate.reference_h4
    equilibrium = (reference.high + reference.low) / Decimal("2")
    destination = (
        reference.high
        if candidate.side is DemoTradingSetupSide.LONG
        else reference.low
    )
    if not (
        _forward(candidate.side, entry=baseline.entry, level=equilibrium)
        and _forward(candidate.side, entry=baseline.entry, level=destination)
        and _ordered_path(
            candidate.side,
            entry=baseline.entry,
            equilibrium=equilibrium,
            destination=destination,
        )
    ):
        return StructuralBankTrade(
            baseline=baseline,
            structural_r=baseline.r_multiple,
            status="NO_FORWARD_STRUCTURAL_LADDER",
            equilibrium_r=None,
            destination_r=None,
        )

    eq_r = _r(
        candidate.side,
        entry=baseline.entry,
        stop=baseline.stop,
        level=equilibrium,
    )
    dest_r = _r(
        candidate.side,
        entry=baseline.entry,
        stop=baseline.stop,
        level=destination,
    )
    rows = _window(candidate, bars_by_open)
    if rows is None:
        return None

    eq_index: int | None = None
    for index, bar in enumerate(rows):
        if _stop_touched(
            bar,
            side=candidate.side,
            stop=baseline.stop,
        ):
            if eq_index is None:
                return StructuralBankTrade(
                    baseline=baseline,
                    structural_r=Decimal("-1"),
                    status="INITIAL_STOP_BEFORE_EQ",
                    equilibrium_r=eq_r,
                    destination_r=dest_r,
                )
            value = EQ_FRACTION * eq_r + DESTINATION_FRACTION * Decimal("-1")
            return StructuralBankTrade(
                baseline=baseline,
                structural_r=value,
                status="EQ_BANK_THEN_INITIAL_STOP",
                equilibrium_r=eq_r,
                destination_r=dest_r,
            )

        target_touched = _touches(
            bar,
            side=candidate.side,
            level=baseline.target,
        )

        if eq_index is None:
            eq_touched = _touches(
                bar,
                side=candidate.side,
                level=equilibrium,
            )
            if not eq_touched:
                if target_touched:
                    return StructuralBankTrade(
                        baseline=baseline,
                        structural_r=Decimal("2"),
                        status="BASELINE_TARGET_BEFORE_EQ",
                        equilibrium_r=eq_r,
                        destination_r=dest_r,
                    )
                continue
            eq_index = index
            if target_touched:
                # EQ is necessarily the nearer forward level when target lies beyond it.
                target_r = Decimal("2")
                value = EQ_FRACTION * eq_r + DESTINATION_FRACTION * target_r
                return StructuralBankTrade(
                    baseline=baseline,
                    structural_r=value,
                    status="EQ_AND_BASELINE_TARGET_SAME_M15",
                    equilibrium_r=eq_r,
                    destination_r=dest_r,
                )
            continue

        # Structural destination must be on a strictly later M15 than EQ.
        destination_touched = _touches(
            bar,
            side=candidate.side,
            level=destination,
        )
        if destination_touched and target_touched:
            remaining_r = min(dest_r, Decimal("2"))
            value = EQ_FRACTION * eq_r + DESTINATION_FRACTION * remaining_r
            return StructuralBankTrade(
                baseline=baseline,
                structural_r=value,
                status="EQ_BANK_THEN_NEAREST_DESTINATION",
                equilibrium_r=eq_r,
                destination_r=dest_r,
            )
        if destination_touched:
            value = EQ_FRACTION * eq_r + DESTINATION_FRACTION * dest_r
            return StructuralBankTrade(
                baseline=baseline,
                structural_r=value,
                status="EQ50_STRUCTURAL_DESTINATION50",
                equilibrium_r=eq_r,
                destination_r=dest_r,
            )
        if target_touched:
            value = EQ_FRACTION * eq_r + DESTINATION_FRACTION * Decimal("2")
            return StructuralBankTrade(
                baseline=baseline,
                structural_r=value,
                status="EQ_BANK_THEN_BASELINE_TARGET",
                equilibrium_r=eq_r,
                destination_r=dest_r,
            )

    last = rows[-1]
    close_r = _r(
        candidate.side,
        entry=baseline.entry,
        stop=baseline.stop,
        level=last.close,
    )
    if eq_index is None:
        return StructuralBankTrade(
            baseline=baseline,
            structural_r=close_r,
            status="H4_CLOSE_WITHOUT_EQ",
            equilibrium_r=eq_r,
            destination_r=dest_r,
        )
    value = EQ_FRACTION * eq_r + DESTINATION_FRACTION * close_r
    return StructuralBankTrade(
        baseline=baseline,
        structural_r=value,
        status="EQ_BANK_PLUS_H4_CLOSE_REMAINDER",
        equilibrium_r=eq_r,
        destination_r=dest_r,
    )


def structural_rows(path: Path) -> tuple[StructuralBankTrade, ...]:
    _, symbol, _, _, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside VT08 5M structural-bank universe")
    bars_by_open = {bar.opened_at: bar for bar in bars}
    candidates_by_day: dict[date, list[Vt08ExpansionCandidate]] = defaultdict(list)

    for bar in bars:
        local = bar.opened_at.astimezone(_NY)
        if local.minute != 0 or local.hour not in ANCHORS_NY:
            continue
        evaluation = evaluate_expansion_at_entry_indexed(
            symbol=symbol,
            bars_by_open=bars_by_open,
            decision_at=bar.opened_at,
        )
        if evaluation.candidate is not None:
            candidates_by_day[local.date()].append(evaluation.candidate)

    result: list[StructuralBankTrade] = []
    for local_day in sorted(candidates_by_day):
        candidates = candidates_by_day[local_day]
        if len(candidates) != 1:
            continue
        modeled = simulate_structural_bank(
            candidates[0],
            bars_by_open=bars_by_open,
        )
        if modeled is not None:
            result.append(modeled)
    return tuple(sorted(result, key=lambda item: item.baseline.signal_at))


def _segment(
    rows: tuple[StructuralBankTrade, ...],
) -> dict[str, object]:
    baseline = tuple(row.baseline for row in rows)
    structural = tuple(row.as_trade() for row in rows)
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row.status] += 1
    return {
        "baseline": metrics(baseline),
        "structural_bank": metrics(structural),
        "status_counts": dict(sorted(counts.items())),
    }


def replay(path: Path) -> dict[str, object]:
    rows = structural_rows(path)
    if len(rows) < 2:
        raise ValueError("VT08 structural-bank frontier requires terminal trades")
    split = int(Decimal(len(rows)) * TRAIN_FRACTION)
    split = max(1, min(split, len(rows) - 1))
    train = rows[:split]
    oos = rows[split:]
    return {
        "schema": SCHEMA,
        "program_fingerprint": program_fingerprint(),
        "market": rows[0].baseline.symbol,
        "research_only": True,
        "policy": {
            "equilibrium": "VT08_REFERENCE_H4_MIDPOINT",
            "destination": "VT08_REFERENCE_H4_OPPOSITE_EXTREME",
            "equilibrium_bank_fraction": format(EQ_FRACTION, "f"),
            "destination_fraction": format(DESTINATION_FRACTION, "f"),
            "destination_requires_later_m15_than_equilibrium": True,
            "same_m15_precedence": "ACTIVE_STOP_FIRST",
            "initial_stop_changed": False,
            "trade_admission_changed": False,
        },
        "split": {
            "train_fraction": format(TRAIN_FRACTION, "f"),
            "train_count": len(train),
            "oos_count": len(oos),
            "split_signal_at": oos[0].baseline.signal_at.isoformat(),
        },
        "train": _segment(train),
        "oos": _segment(oos),
        "rows": [row.payload() for row in rows],
        "governance": {
            "single_predeclared_management_arm": True,
            "parameter_scan": False,
            "uses_terminal_pnl_at_runtime": False,
            "uses_future_bar_at_runtime": False,
            "vt31_nas100_levels_copied": False,
            "trade_count_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(replay(path), sort_keys=True, separators=(",", ":"))
