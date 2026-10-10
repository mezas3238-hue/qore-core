"""Adaptive protection V2 for CADJPY and NZDUSD research.

The candidate changes only whether the pre-existing aggressive CIBO ratchets
are active. Structural banking, signal admission, initial stop, target and H4
lifecycle remain identical to Core Stack DEV V1.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_cognitive_core_stack_dev_v1 import (
    EQ_BANK_FRACTION,
    _favorable_r,
    _forward_ladder,
    _r,
    _stop_price,
    _stop_touched,
    _touch,
    _window,
    aggressive_policy,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    ExpansionTrade,
    load_market_evidence,
    model_trade,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    Vt08ExpansionCandidate,
    evaluate_expansion_at_entry_indexed,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
)
from qore.infrastructure.trader_lab.vt08_index_c2_r1_cibo_stop_protection import (
    STOP_POLICIES,
    StopPolicy,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_adaptive_protection_v2.v1"
MARKETS: Final = ("CADJPY", "NZDUSD")
FRESH_BOUNDARY: Final = datetime(2023, 9, 24, 23, 45, tzinfo=UTC)
LOW_RISK_REF_THRESHOLD: Final = Decimal("0.25")
_NY = ZoneInfo("America/New_York")


def off_policy() -> StopPolicy:
    matches = tuple(policy for policy in STOP_POLICIES if policy.name == "off")
    if len(matches) != 1:
        raise AssertionError("exact pre-existing OFF policy required")
    return matches[0]


def risk_reference_ratio(candidate: Vt08ExpansionCandidate) -> Decimal:
    risk = abs(
        candidate.setup.entry_price - candidate.setup.invalidation_price
    )
    reference_range = candidate.reference_h4.high - candidate.reference_h4.low
    if risk <= 0 or reference_range <= 0:
        raise ValueError("adaptive protection requires positive source geometry")
    return risk / reference_range


def policy_for_candidate(candidate: Vt08ExpansionCandidate) -> StopPolicy:
    if candidate.symbol == "CADJPY":
        return (
            off_policy()
            if candidate.entry_anchor_hour == 9
            else aggressive_policy()
        )
    if candidate.symbol == "NZDUSD":
        return (
            off_policy()
            if risk_reference_ratio(candidate) < LOW_RISK_REF_THRESHOLD
            else aggressive_policy()
        )
    raise ValueError("adaptive protection market outside frozen V2 scope")


@dataclass(frozen=True, slots=True)
class AdaptiveProtectionTrade:
    baseline: ExpansionTrade
    managed_r: Decimal
    exit_reason: str
    policy_name: str
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


def simulate_adaptive(
    candidate: Vt08ExpansionCandidate,
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
) -> AdaptiveProtectionTrade | None:
    baseline = model_trade(candidate, bars_by_open=bars_by_open)
    if baseline is None:
        return None
    rows = _window(candidate, bars_by_open)
    if rows is None:
        return None

    risk = abs(baseline.entry - baseline.stop)
    if risk <= 0:
        raise ValueError("adaptive protection requires positive initial risk")
    reference = candidate.reference_h4
    equilibrium = (reference.high + reference.low) / Decimal("2")
    destination = (
        reference.high
        if candidate.side.value == "long"
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

    policy = policy_for_candidate(candidate)
    current_stop_r = Decimal("-1")
    remaining = Decimal("1")
    realized = Decimal("0")
    eq_banked = False
    destination_banked = False

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
            protected = current_stop_r > Decimal("-1")
            return AdaptiveProtectionTrade(
                baseline=baseline,
                managed_r=realized,
                exit_reason=(
                    "adaptive_protected_stop"
                    if protected
                    else "adaptive_initial_stop"
                ),
                policy_name=policy.name,
                eq_banked=eq_banked,
                destination_banked=destination_banked,
                protected_stop_used=protected,
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
                return AdaptiveProtectionTrade(
                    baseline,
                    realized,
                    "adaptive_target_before_eq",
                    policy.name,
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
                    return AdaptiveProtectionTrade(
                        baseline,
                        realized,
                        "adaptive_eq_then_target_same_m15",
                        policy.name,
                        True,
                        False,
                        False,
                    )
            elif target_touched:
                realized += remaining * Decimal("2")
                return AdaptiveProtectionTrade(
                    baseline,
                    realized,
                    "adaptive_target_before_eq",
                    policy.name,
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
                return AdaptiveProtectionTrade(
                    baseline,
                    realized,
                    "adaptive_nearest_destination_or_target",
                    policy.name,
                    True,
                    destination_banked,
                    False,
                )
            if destination_touched:
                realized += remaining * destination_r
                return AdaptiveProtectionTrade(
                    baseline,
                    realized,
                    "adaptive_structural_destination",
                    policy.name,
                    True,
                    True,
                    False,
                )
            if target_touched:
                realized += remaining * Decimal("2")
                return AdaptiveProtectionTrade(
                    baseline,
                    realized,
                    "adaptive_eq_then_target",
                    policy.name,
                    True,
                    False,
                    False,
                )

        elif target_touched:
            realized += remaining * Decimal("2")
            return AdaptiveProtectionTrade(
                baseline,
                realized,
                "adaptive_target",
                policy.name,
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
    realized += remaining * _r(
        side=baseline.side,
        entry=baseline.entry,
        stop=baseline.stop,
        level=last.close,
    )
    return AdaptiveProtectionTrade(
        baseline,
        realized,
        "adaptive_h4_close",
        policy.name,
        eq_banked,
        destination_banked,
        False,
    )


def adaptive_rows(path: Path) -> tuple[AdaptiveProtectionTrade, ...]:
    _, symbol, _, _, bars = load_market_evidence(path)
    if symbol not in MARKETS:
        raise ValueError("adaptive protection market outside V2 scope")
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

    result: list[AdaptiveProtectionTrade] = []
    for local_day in sorted(candidates_by_day):
        candidates = candidates_by_day[local_day]
        if len(candidates) != 1:
            continue
        trade = simulate_adaptive(
            candidates[0],
            bars_by_open=bars_by_open,
        )
        if trade is not None:
            result.append(trade)
    return tuple(sorted(result, key=lambda item: item.baseline.signal_at))


def to_json(path: Path) -> str:
    rows = adaptive_rows(path)
    return json.dumps(
        {
            "schema": SCHEMA,
            "market": rows[0].baseline.symbol if rows else None,
            "trade_count": len(rows),
            "research_only": True,
            "fresh_boundary": FRESH_BOUNDARY.isoformat(),
            "governance": {
                "trade_filtering": False,
                "initial_stop_changed": False,
                "target_changed": False,
                "h4_lifecycle_changed": False,
                "fresh_validation_required": True,
                "live_authorized": False,
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )
