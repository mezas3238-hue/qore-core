"""Transfer pre-existing VT08 CIBO stop-protection families to 5M research.

The thresholds are not tuned here. They are imported from the existing VT08
Index CIBO stop-protection lab and applied to the immutable five-market signal
stream. Evidence is consumed development only.
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

SCHEMA: Final = "qore.trader_lab.vt08_cognitive_cibo_stop_protection.v1"
TRAIN_FRACTION: Final = Decimal("0.70")
_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class ProtectedTrade:
    baseline: ExpansionTrade
    policy: str
    managed_r: Decimal
    exit_reason: str

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


def _target_touched(
    bar: Vt08B01Bar,
    *,
    side: DemoTradingSetupSide,
    target: Decimal,
) -> bool:
    if side is DemoTradingSetupSide.LONG:
        return bar.high >= target
    return bar.low <= target


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


def _close_r(
    close: Decimal,
    *,
    side: DemoTradingSetupSide,
    entry: Decimal,
    risk: Decimal,
) -> Decimal:
    if side is DemoTradingSetupSide.LONG:
        return (close - entry) / risk
    return (entry - close) / risk


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


def replay_policy_trade(
    candidate: Vt08ExpansionCandidate,
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
    policy: StopPolicy,
) -> ProtectedTrade | None:
    baseline = model_trade(candidate, bars_by_open=bars_by_open)
    if baseline is None:
        return None
    risk = abs(baseline.entry - baseline.stop)
    if risk <= 0:
        raise ValueError("VT08 CIBO protection requires positive initial risk")
    rows = _window(candidate, bars_by_open)
    if rows is None:
        return None

    current_stop_r = Decimal("-1")
    last = rows[-1]
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
            reason = "stop" if current_stop_r <= Decimal("-1") else "cibo_protected_stop"
            return ProtectedTrade(
                baseline=baseline,
                policy=policy.name,
                managed_r=current_stop_r,
                exit_reason=reason,
            )

        if _target_touched(
            bar,
            side=baseline.side,
            target=baseline.target,
        ):
            return ProtectedTrade(
                baseline=baseline,
                policy=policy.name,
                managed_r=Decimal("2"),
                exit_reason="target",
            )

        favorable = _favorable_r(
            bar,
            side=baseline.side,
            entry=baseline.entry,
            risk=risk,
        )
        for trigger_r, lock_r in policy.ratchets:
            if favorable >= trigger_r and lock_r > current_stop_r:
                current_stop_r = lock_r

    return ProtectedTrade(
        baseline=baseline,
        policy=policy.name,
        managed_r=_close_r(
            last.close,
            side=baseline.side,
            entry=baseline.entry,
            risk=risk,
        ),
        exit_reason="h4_containment_exit",
    )


def _candidate_rows(
    path: Path,
) -> tuple[
    tuple[Vt08ExpansionCandidate, ...],
    dict[datetime, Vt08B01Bar],
]:
    _, symbol, _, _, bars = load_market_evidence(path)
    if symbol not in EXPANSION_MARKETS:
        raise ValueError("market outside VT08 5M CIBO protection universe")
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

    retained = tuple(
        items[0]
        for day in sorted(candidates_by_day)
        if len(items := candidates_by_day[day]) == 1
    )
    return retained, bars_by_open


def _policy_rows(
    candidates: tuple[Vt08ExpansionCandidate, ...],
    *,
    bars_by_open: dict[datetime, Vt08B01Bar],
    policy: StopPolicy,
) -> tuple[ProtectedTrade, ...]:
    rows: list[ProtectedTrade] = []
    for candidate in candidates:
        item = replay_policy_trade(
            candidate,
            bars_by_open=bars_by_open,
            policy=policy,
        )
        if item is not None:
            rows.append(item)
    return tuple(rows)


def _summary(rows: tuple[ProtectedTrade, ...]) -> dict[str, object]:
    return metrics(tuple(item.as_trade() for item in rows))


def replay(path: Path) -> dict[str, object]:
    candidates, bars_by_open = _candidate_rows(path)
    if len(candidates) < 2:
        raise ValueError("VT08 CIBO stop-protection frontier requires trades")

    results: dict[str, tuple[ProtectedTrade, ...]] = {
        policy.name: _policy_rows(
            candidates,
            bars_by_open=bars_by_open,
            policy=policy,
        )
        for policy in STOP_POLICIES
    }
    lengths = {len(rows) for rows in results.values()}
    if len(lengths) != 1:
        raise AssertionError("stop policies changed VT08 trade cardinality")

    off = results["off"]
    for item in off:
        if item.managed_r != item.baseline.r_multiple:
            raise AssertionError("OFF policy failed exact VT08 baseline R reconciliation")
        if item.exit_reason != item.baseline.exit_reason:
            raise AssertionError(
                "OFF policy failed exact VT08 baseline exit-reason reconciliation"
            )

    count = len(off)
    split = int(Decimal(count) * TRAIN_FRACTION)
    split = max(1, min(split, count - 1))

    payload: dict[str, object] = {}
    for policy in STOP_POLICIES:
        rows = results[policy.name]
        payload[policy.name] = {
            "ratchets": [
                {
                    "trigger_r": format(trigger, "f"),
                    "lock_r": format(lock, "f"),
                }
                for trigger, lock in policy.ratchets
            ],
            "full_consumed": _summary(rows),
            "train_consumed": _summary(rows[:split]),
            "temporal_consumed": _summary(rows[split:]),
            "protected_stop_count": sum(
                item.exit_reason == "cibo_protected_stop"
                for item in rows[split:]
            ),
        }

    return {
        "schema": SCHEMA,
        "program_fingerprint": program_fingerprint(),
        "market": off[0].baseline.symbol,
        "evidence_status": "CONSUMED_DEVELOPMENT",
        "research_only": True,
        "trade_count": count,
        "split": {
            "train_fraction": format(TRAIN_FRACTION, "f"),
            "train_count": split,
            "temporal_consumed_count": count - split,
        },
        "off_reconciles_baseline_exactly": True,
        "policies": payload,
        "governance": {
            "pre_existing_vt08_cibo_policies_only": True,
            "new_threshold_search": False,
            "trade_identity_changed": False,
            "entry_changed": False,
            "initial_stop_changed": False,
            "target_changed": False,
            "h4_lifecycle_changed": False,
            "stop_widened": False,
            "policy_selection_authorized": False,
            "fresh_validation_required_for_selection": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
        },
    }


def to_json(path: Path) -> str:
    return json.dumps(replay(path), sort_keys=True, separators=(",", ":"))
