"""VT08 Cognitive Core Stack DEV V1.

Development-only composition selected after consumed evidence:
- VT08-native EQ50 / structural-destination banking;
- pre-existing VT08 CIBO aggressive stop ratchets;
- original VT08 entry, initial stop, 2R target and H4 lifecycle.

No runner is included. The current evidence is consumed development only.
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
from qore.infrastructure.trader_lab.vt08_index_c2_r1_cibo_stop_protection import (
    STOP_POLICIES,
    StopPolicy,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_core_stack_dev_v1"
TRAIN_FRACTION: Final = Decimal("0.70")
EQ_BANK_FRACTION: Final = Decimal("0.50")
_NY = ZoneInfo("America/New_York")


def aggressive_policy() -> StopPolicy:
    matches = tuple(policy for policy in STOP_POLICIES if policy.name == "aggressive")
    if len(matches) != 1:
        raise AssertionError("exact pre-existing VT08 CIBO aggressive policy required")
    return matches[0]


@dataclass(frozen=True, slots=True)
class CoreStackTrade:
    baseline: ExpansionTrade
    managed_r: Decimal
    exit_reason: str
    eq_banked: bool
    destination_banked: bool
    protected_stop_used: bool

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
            exit_reason=self.exit_reason,
            r_multiple=self.managed_r,
        )


def _r(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    stop: Decimal,
    level: Decimal,
) -> Decimal:
    risk = entry - stop if side is DemoTradingSetupSide.LONG else stop - entry
    if risk <= 0:
        raise ValueError("VT08 Core Stack requires positive initial risk")
    if side is DemoTradingSetupSide.LONG:
        return (level - entry) / risk
    return (entry - level) / risk


def _touch(
    bar: Vt08B01Bar,
    *,
    side: DemoTradingSetupSide,
    level: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return bar.high >= level
    return bar.low <= level


def _stop_price(
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    risk: Decimal,
    stop_r: Decimal,
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return entry + stop_r * risk
    return entry - stop_r * risk


def _stop_touched(
    bar: Vt08B01Bar,
    *,
    side: DemoTradingSetupSide,
    stop_price: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return bar.low <= stop_price
    return bar.high >= stop_price


def _favorable_r(
    bar: Vt08B01Bar,
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return (bar.high - entry) / risk
    return (entry - bar.low) / risk


def _window(
    candidate: Vt08ExpansionCandidate,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> tuple[Vt08B01Bar, ...] | None:
    start = candidate.decision_at.astimezone(UTC)
    end = (start.astimezone(_NY) + timedelta(hours=4)).astimezone(UTC)
    rows: list[Vt08B01Bar] = []
    cursor = start
    while cursor < end:
        bar = bars_by_open.get(cursor)
        if bar is None or bar.closed_at != cursor + timedelta(minutes=15):
            return None
        rows.append(bar)
        cursor += timedelta(minutes=15)
    return tuple(rows) if rows and cursor == end else None


def _forward_ladder(
    candidate: Vt08ExpansionCandidate,
    *,
    equilibrium: Decimal,
    destination: Decimal,
) -> bool:
    entry = candidate.setup.entry_price
    if candidate.side is DemoTradingSetupSide.LONG:
        return entry < equilibrium < destination
    return entry > equilibrium > destination


def simulate_core_stack(
    candidate: Vt08ExpansionCandidate,
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> CoreStackTrade | None:
    baseline = model_trade(candidate, bars_by_open=bars_by_open)
    if baseline is None:
        return None
    rows = _window(candidate, bars_by_open)
    if rows is None:
        return None

    risk = abs(baseline.entry - baseline.stop)
    if risk <= 0:
        raise ValueError("VT08 Core Stack requires positive risk")

    reference = candidate.reference_h4
    equilibrium = (reference.high + reference.low) / Decimal("2")
    destination = (
        reference.high
        if candidate.side is DemoTradingSetupSide.LONG
        else reference.low
    )
    ladder = _forward_ladder(
        candidate,
        equilibrium=equilibrium,
        destination=destination,
    )
    eq_r = (
        _r(
            side=candidate.side,
            entry=baseline.entry,
            stop=baseline.stop,
            level=equilibrium,
        )
        if ladder
        else None
    )
    destination_r = (
        _r(
            side=candidate.side,
            entry=baseline.entry,
            stop=baseline.stop,
            level=destination,
        )
        if ladder
        else None
    )

    current_stop_r = Decimal("-1")
    remaining = Decimal("1")
    realized = Decimal("0")
    eq_banked = False
    destination_banked = False
    protected_stop_used = False
    policy = aggressive_policy()

    for bar in rows:
        stop_price = _stop_price(
            side=baseline.side,
            entry=baseline.entry,
            risk=risk,
            stop_r=current_stop_r,
        )
        if _stop_touched(
            bar,
            side=baseline.side,
            stop_price=stop_price,
        ):
            realized += remaining * current_stop_r
            protected_stop_used = current_stop_r > Decimal("-1")
            return CoreStackTrade(
                baseline=baseline,
                managed_r=realized,
                exit_reason=(
                    "core_stack_protected_stop"
                    if protected_stop_used
                    else "core_stack_initial_stop"
                ),
                eq_banked=eq_banked,
                destination_banked=destination_banked,
                protected_stop_used=protected_stop_used,
            )

        target_touched = _touch(
            bar,
            side=baseline.side,
            level=baseline.target,
        )

        if ladder and not eq_banked:
            assert eq_r is not None
            eq_touched = _touch(
                bar,
                side=baseline.side,
                level=equilibrium,
            )
            if target_touched and Decimal("2") < eq_r:
                realized += remaining * Decimal("2")
                return CoreStackTrade(
                    baseline,
                    realized,
                    "core_stack_target_before_eq",
                    False,
                    False,
                    False,
                )
            if eq_touched:
                bank = min(EQ_BANK_FRACTION, remaining)
                realized += bank * eq_r
                remaining -= bank
                eq_banked = True
                if target_touched and remaining > 0:
                    realized += remaining * Decimal("2")
                    remaining = Decimal("0")
                    return CoreStackTrade(
                        baseline,
                        realized,
                        "core_stack_eq_then_target_same_m15",
                        True,
                        False,
                        False,
                    )
            elif target_touched:
                realized += remaining * Decimal("2")
                return CoreStackTrade(
                    baseline,
                    realized,
                    "core_stack_target_before_eq",
                    False,
                    False,
                    False,
                )

        elif ladder and eq_banked and not destination_banked:
            assert destination_r is not None
            destination_touched = _touch(
                bar,
                side=baseline.side,
                level=destination,
            )
            if destination_touched and target_touched:
                terminal_r = min(destination_r, Decimal("2"))
                realized += remaining * terminal_r
                destination_banked = destination_r <= Decimal("2")
                return CoreStackTrade(
                    baseline,
                    realized,
                    "core_stack_nearest_destination_or_target",
                    True,
                    destination_banked,
                    False,
                )
            if destination_touched:
                realized += remaining * destination_r
                remaining = Decimal("0")
                destination_banked = True
                return CoreStackTrade(
                    baseline,
                    realized,
                    "core_stack_structural_destination",
                    True,
                    True,
                    False,
                )
            if target_touched:
                realized += remaining * Decimal("2")
                remaining = Decimal("0")
                return CoreStackTrade(
                    baseline,
                    realized,
                    "core_stack_eq_then_target",
                    True,
                    False,
                    False,
                )

        elif target_touched:
            realized += remaining * Decimal("2")
            remaining = Decimal("0")
            return CoreStackTrade(
                baseline,
                realized,
                "core_stack_target",
                eq_banked,
                destination_banked,
                False,
            )

        if remaining <= 0:
            break

        favorable = _favorable_r(
            bar,
            side=baseline.side,
            entry=baseline.entry,
            risk=risk,
        )
        for trigger_r, lock_r in policy.ratchets:
            if favorable >= trigger_r and lock_r > current_stop_r:
                current_stop_r = lock_r

    last = rows[-1]
    close_r = _r(
        side=baseline.side,
        entry=baseline.entry,
        stop=baseline.stop,
        level=last.close,
    )
    realized += remaining * close_r
    return CoreStackTrade(
        baseline=baseline,
        managed_r=realized,
        exit_reason="core_stack_h4_close",
        eq_banked=eq_banked,
        destination_banked=destination_banked,
        protected_stop_used=False,
    )


def stack_rows(path: Path) -> tuple[CoreStackTrade, ...]:
    _, symbol, _, _, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside VT08 Core Stack 5M universe")
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

    result: list[CoreStackTrade] = []
    for local_day in sorted(candidates_by_day):
        candidates = candidates_by_day[local_day]
        if len(candidates) != 1:
            continue
        item = simulate_core_stack(
            candidates[0],
            bars_by_open=bars_by_open,
        )
        if item is not None:
            result.append(item)
    return tuple(sorted(result, key=lambda item: item.baseline.signal_at))


def _segment(rows: tuple[CoreStackTrade, ...]) -> dict[str, object]:
    return {
        "baseline": metrics(tuple(item.baseline for item in rows)),
        "core_stack": metrics(tuple(item.as_trade() for item in rows)),
        "eq_banked_count": sum(item.eq_banked for item in rows),
        "destination_banked_count": sum(item.destination_banked for item in rows),
        "protected_stop_count": sum(item.protected_stop_used for item in rows),
    }


def replay(path: Path) -> dict[str, object]:
    rows = stack_rows(path)
    if len(rows) < 2:
        raise ValueError("VT08 Core Stack requires at least two terminal trades")
    split = int(Decimal(len(rows)) * TRAIN_FRACTION)
    split = max(1, min(split, len(rows) - 1))
    return {
        "schema": SCHEMA,
        "program_fingerprint": program_fingerprint(),
        "market": rows[0].baseline.symbol,
        "research_only": True,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "selected_from_consumed_evidence": True,
        "stack": {
            "structural_bank": "VT08_REFERENCE_H4_EQ50_DESTINATION50",
            "stop_policy": "PRE_EXISTING_VT08_CIBO_AGGRESSIVE",
            "runner": "OFF",
            "entry_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "h4_lifecycle_changed": False,
        },
        "split": {
            "train_fraction": format(TRAIN_FRACTION, "f"),
            "train_count": split,
            "temporal_consumed_count": len(rows) - split,
        },
        "train_consumed": _segment(rows[:split]),
        "temporal_consumed": _segment(rows[split:]),
        "full_consumed": _segment(rows),
        "governance": {
            "fresh_holdout_passed": False,
            "fresh_evidence_required": True,
            "fresh_boundary_before": "2024-08-25T21:00:00Z",
            "trade_count_changed": False,
            "market_filtering_authorized": False,
            "anchor_filtering_authorized": False,
            "side_filtering_authorized": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(replay(path), sort_keys=True, separators=(",", ":"))
