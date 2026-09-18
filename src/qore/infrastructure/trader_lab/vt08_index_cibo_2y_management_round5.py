"""VT08 Index CIBO 2Y fixed-density journey management — Round 5.

Round 5 freezes the 657 one-active-position-per-symbol admissions discovered by
Round 4 at the 2.5R baseline. It does NOT solve drawdown by abstaining from
trades. Every policy is evaluated on exactly the same 657 entries.

The research question is whether causal post-entry management can reshape the
loss distribution enough to produce high profit factor and approximately 5-6R
max drawdown while preserving density.

All management decisions use only information observable by the close of the
current M15 bar. A stop tightened from a milestone only becomes active on the
next M15 bar, avoiding favorable intrabar ordering assumptions.
"""

from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.trader_lab import vt08_index_cibo_2y_density_round4 as r4
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round1 as r1
from qore.infrastructure.trader_lab import vt08_index_cibo_2y_tuning_round2 as r2
from qore.infrastructure.trader_lab import vt08_index_v6_ttrades_source_faithful as v6
from qore.infrastructure.trader_lab.vt08_index_v2_candidate import (
    _gap_exit,
    _intrabar_exit,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar

SCHEMA = "qore.trader_lab.vt08_index_cibo_2y_management_round5.v1"
IDENTITY = "VT08_INDEX_CIBO_2Y_MANAGEMENT_ROUND5_FIXED_657"
FIXED_DENSITY = 657
BASELINE_TARGET_R = Decimal("2.5")
PRIMARY_STRESS = Decimal("0.05")
SECONDARY_STRESS = Decimal("0.10")
PF_GOAL = Decimal("1.50")
DD_GOAL = Decimal("6")
SECONDARY_PF_GOAL = Decimal("1.30")
SECONDARY_DD_GOAL = Decimal("8")


@dataclass(frozen=True, slots=True)
class Policy:
    target_r: Decimal
    soft_close_loss_r: Decimal | None
    soft_close_until_mfe_r: Decimal | None
    deadline_bars: int | None
    deadline_min_mfe_r: Decimal | None
    trail_name: str
    trail_steps: tuple[tuple[Decimal, Decimal], ...]

    @property
    def policy_id(self) -> str:
        material = {
            "target_r": str(self.target_r),
            "soft_close_loss_r": (
                str(self.soft_close_loss_r)
                if self.soft_close_loss_r is not None
                else None
            ),
            "soft_close_until_mfe_r": (
                str(self.soft_close_until_mfe_r)
                if self.soft_close_until_mfe_r is not None
                else None
            ),
            "deadline_bars": self.deadline_bars,
            "deadline_min_mfe_r": (
                str(self.deadline_min_mfe_r)
                if self.deadline_min_mfe_r is not None
                else None
            ),
            "trail_name": self.trail_name,
            "trail_steps": [
                [str(trigger), str(lock)] for trigger, lock in self.trail_steps
            ],
        }
        digest = sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16]
        return f"R5-{digest}"

    def payload(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "target_r": str(self.target_r),
            "soft_close_loss_r": (
                str(self.soft_close_loss_r)
                if self.soft_close_loss_r is not None
                else None
            ),
            "soft_close_until_mfe_r": (
                str(self.soft_close_until_mfe_r)
                if self.soft_close_until_mfe_r is not None
                else None
            ),
            "deadline_bars": self.deadline_bars,
            "deadline_min_mfe_r": (
                str(self.deadline_min_mfe_r)
                if self.deadline_min_mfe_r is not None
                else None
            ),
            "trail_name": self.trail_name,
            "trail_steps": [
                {"trigger_r": str(trigger), "lock_r": str(lock)}
                for trigger, lock in self.trail_steps
            ],
        }


@dataclass(frozen=True, slots=True)
class ManagedTrade:
    symbol: str
    signal_at: datetime
    exited_at: datetime
    r_multiple: Decimal
    exit_reason: str

    def as_v6(self, signal: v6.CandidateSignal) -> v6.ModeledV6Trade:
        risk = abs(signal.entry - signal.stop)
        exit_price = (
            signal.entry + self.r_multiple * risk
            if signal.side is DemoTradingSetupSide.LONG
            else signal.entry - self.r_multiple * risk
        )
        return v6.ModeledV6Trade(
            signal=signal,
            exited_at=self.exited_at,
            exit_price=exit_price,
            exit_reason=self.exit_reason,
            r_multiple=self.r_multiple,
        )


def _favorable_r(
    signal: v6.CandidateSignal,
    bar: Vt08IndexC2R1Bar,
) -> Decimal:
    risk = abs(signal.entry - signal.stop)
    if signal.side is DemoTradingSetupSide.LONG:
        return (bar.high - signal.entry) / risk
    return (signal.entry - bar.low) / risk


def _close_r(
    signal: v6.CandidateSignal,
    bar: Vt08IndexC2R1Bar,
) -> Decimal:
    risk = abs(signal.entry - signal.stop)
    if signal.side is DemoTradingSetupSide.LONG:
        return (bar.close - signal.entry) / risk
    return (signal.entry - bar.close) / risk


def _price_at_r(signal: v6.CandidateSignal, level: Decimal) -> Decimal:
    risk = abs(signal.entry - signal.stop)
    if signal.side is DemoTradingSetupSide.LONG:
        return signal.entry + level * risk
    return signal.entry - level * risk


def _stop_r(signal: v6.CandidateSignal, stop: Decimal) -> Decimal:
    risk = abs(signal.entry - signal.stop)
    if signal.side is DemoTradingSetupSide.LONG:
        return (stop - signal.entry) / risk
    return (signal.entry - stop) / risk


def _bars_from(
    bars: Sequence[Vt08IndexC2R1Bar],
    opened: Sequence[datetime],
    signal_at: datetime,
) -> Sequence[Vt08IndexC2R1Bar]:
    return bars[bisect_left(opened, signal_at.astimezone(UTC)) :]


def _manage_trade(
    signal: v6.CandidateSignal,
    *,
    bars: Sequence[Vt08IndexC2R1Bar],
    opened: Sequence[datetime],
    policy: Policy,
) -> ManagedTrade:
    current_stop = signal.stop
    target = _price_at_r(signal, policy.target_r)
    max_mfe = Decimal()
    last: Vt08IndexC2R1Bar | None = None

    for bar_number, bar in enumerate(
        _bars_from(bars, opened, signal.signal_at),
        start=1,
    ):
        last = bar
        gap = _gap_exit(
            side=signal.side,
            bar=bar,
            stop=current_stop,
            target=target,
        )
        resolved = gap or _intrabar_exit(
            bar=bar,
            stop=current_stop,
            target=target,
        )
        if resolved is not None:
            exit_price, reason = resolved
            risk = abs(signal.entry - signal.stop)
            pnl = (
                exit_price - signal.entry
                if signal.side is DemoTradingSetupSide.LONG
                else signal.entry - exit_price
            )
            return ManagedTrade(
                symbol=signal.symbol,
                signal_at=signal.signal_at,
                exited_at=bar.closed_at,
                r_multiple=pnl / risk,
                exit_reason=reason,
            )

        max_mfe = max(max_mfe, _favorable_r(signal, bar))
        close_r = _close_r(signal, bar)

        soft_active = policy.soft_close_loss_r is not None and (
            policy.soft_close_until_mfe_r is None
            or max_mfe < policy.soft_close_until_mfe_r
        )
        if soft_active and close_r <= -cast(Decimal, policy.soft_close_loss_r):
            return ManagedTrade(
                symbol=signal.symbol,
                signal_at=signal.signal_at,
                exited_at=bar.closed_at,
                r_multiple=close_r,
                exit_reason="soft-close-loss",
            )

        if (
            policy.deadline_bars is not None
            and policy.deadline_min_mfe_r is not None
            and bar_number >= policy.deadline_bars
            and max_mfe < policy.deadline_min_mfe_r
        ):
            return ManagedTrade(
                symbol=signal.symbol,
                signal_at=signal.signal_at,
                exited_at=bar.closed_at,
                r_multiple=close_r,
                exit_reason="no-progress-deadline",
            )

        desired_lock: Decimal | None = None
        for trigger, lock in policy.trail_steps:
            if max_mfe >= trigger:
                desired_lock = lock
        if desired_lock is not None:
            desired_stop = _price_at_r(signal, desired_lock)
            if signal.side is DemoTradingSetupSide.LONG:
                current_stop = max(current_stop, desired_stop)
            else:
                current_stop = min(current_stop, desired_stop)

    if last is None:
        return ManagedTrade(
            signal.symbol,
            signal.signal_at,
            signal.signal_at,
            Decimal(),
            "no-bars",
        )
    return ManagedTrade(
        symbol=signal.symbol,
        signal_at=signal.signal_at,
        exited_at=last.closed_at,
        r_multiple=_close_r(signal, last),
        exit_reason="boundary-mark",
    )


def _policy_grid() -> tuple[Policy, ...]:
    trails = {
        "OFF": (),
        "BE050": ((Decimal("0.5"), Decimal("0")),),
        "LOCK025_075": ((Decimal("0.75"), Decimal("0.25")),),
        "STAIR_A": (
            (Decimal("0.5"), Decimal("0")),
            (Decimal("1.0"), Decimal("0.5")),
            (Decimal("1.5"), Decimal("1.0")),
            (Decimal("2.0"), Decimal("1.5")),
        ),
        "STAIR_B": (
            (Decimal("0.5"), Decimal("0.25")),
            (Decimal("0.75"), Decimal("0.5")),
            (Decimal("1.0"), Decimal("0.75")),
            (Decimal("1.25"), Decimal("1.0")),
            (Decimal("1.5"), Decimal("1.25")),
            (Decimal("2.0"), Decimal("1.75")),
        ),
        "STAIR_C": (
            (Decimal("0.75"), Decimal("0")),
            (Decimal("1.25"), Decimal("0.5")),
            (Decimal("1.75"), Decimal("1.0")),
            (Decimal("2.25"), Decimal("1.5")),
        ),
    }
    softs: tuple[tuple[Decimal | None, Decimal | None], ...] = (
        (None, None),
        (Decimal("0.25"), Decimal("0.5")),
        (Decimal("0.25"), Decimal("1.0")),
        (Decimal("0.5"), Decimal("0.5")),
        (Decimal("0.5"), Decimal("1.0")),
        (Decimal("0.75"), Decimal("1.0")),
    )
    deadlines: tuple[tuple[int | None, Decimal | None], ...] = (
        (None, None),
        (4, Decimal("0.25")),
        (4, Decimal("0.5")),
        (8, Decimal("0.25")),
        (8, Decimal("0.5")),
        (12, Decimal("0.5")),
    )
    policies: list[Policy] = []
    for target in (Decimal("2.0"), Decimal("2.5"), Decimal("3.0")):
        for soft_loss, soft_until in softs:
            for deadline_bars, deadline_mfe in deadlines:
                for trail_name, trail_steps in trails.items():
                    policies.append(
                        Policy(
                            target_r=target,
                            soft_close_loss_r=soft_loss,
                            soft_close_until_mfe_r=soft_until,
                            deadline_bars=deadline_bars,
                            deadline_min_mfe_r=deadline_mfe,
                            trail_name=trail_name,
                            trail_steps=trail_steps,
                        )
                    )
    return tuple(policies)


def _fixed_admissions(
    *,
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]],
) -> tuple[v6.CandidateSignal, ...]:
    selected: list[v6.CandidateSignal] = []
    baseline_policy = Policy(
        target_r=BASELINE_TARGET_R,
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="OFF",
        trail_steps=(),
    )
    for symbol in r1.SYMBOLS:
        bars = bars_by_symbol[symbol]
        opened = tuple(bar.opened_at.astimezone(UTC) for bar in bars)
        surface = r4._build_variant_surface(
            variant=r4.ExpansionVariant.MULTI_POI_REARM,
            symbol=symbol,
            bars=bars,
        )
        candidates = [
            (
                item.signal,
                _manage_trade(
                    item.signal,
                    bars=bars,
                    opened=opened,
                    policy=baseline_policy,
                ),
            )
            for item in surface.opportunities
        ]
        last_exit: datetime | None = None
        for signal, outcome in sorted(
            candidates,
            key=lambda item: item[0].signal_at,
        ):
            if last_exit is not None and signal.signal_at < last_exit:
                continue
            selected.append(signal)
            last_exit = outcome.exited_at
    selected.sort(key=lambda signal: (signal.signal_at, signal.symbol))
    if len(selected) != FIXED_DENSITY:
        raise ValueError(
            f"Round4 fixed-density drift: expected {FIXED_DENSITY}, got {len(selected)}"
        )
    return tuple(selected)


def _metrics(
    signals: Sequence[v6.CandidateSignal],
    outcomes: Sequence[ManagedTrade],
    *,
    stress: Decimal,
) -> dict[str, Any]:
    values = tuple(item.r_multiple - stress for item in outcomes)
    total = sum(values, Decimal())
    gains = sum((value for value in values if value > 0), Decimal())
    losses = -sum((value for value in values if value < 0), Decimal())
    equity = Decimal()
    peak = Decimal()
    dd = Decimal()
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
    reasons: dict[str, int] = {}
    for item in outcomes:
        reasons[item.exit_reason] = reasons.get(item.exit_reason, 0) + 1
    by_market: dict[str, dict[str, str | int | None]] = {}
    for symbol in r1.SYMBOLS:
        symbol_values = tuple(
            outcome.r_multiple - stress
            for signal, outcome in zip(signals, outcomes, strict=True)
            if signal.symbol == symbol
        )
        sg = sum((value for value in symbol_values if value > 0), Decimal())
        sl = -sum((value for value in symbol_values if value < 0), Decimal())
        by_market[symbol] = {
            "sample": len(symbol_values),
            "total_r": str(sum(symbol_values, Decimal())),
            "profit_factor": str(sg / sl) if sl else None,
        }
    return {
        "sample": len(values),
        "wins": sum(value > 0 for value in values),
        "losses": sum(value < 0 for value in values),
        "flats": sum(value == 0 for value in values),
        "total_r": str(total),
        "mean_r": str(total / len(values)) if values else "0",
        "profit_factor": str(gains / losses) if losses else None,
        "max_drawdown_r": str(dd),
        "max_losing_streak": max_streak,
        "stress_r_per_trade": str(stress),
        "exit_reasons": reasons,
        "by_market": by_market,
    }


def _passes_goal(row: dict[str, Any]) -> bool:
    p = cast(dict[str, Any], row["primary"])
    s = cast(dict[str, Any], row["secondary"])
    return (
        int(p["sample"]) == FIXED_DENSITY
        and Decimal(str(p["profit_factor"] or "0")) >= PF_GOAL
        and Decimal(str(p["max_drawdown_r"])) <= DD_GOAL
        and Decimal(str(s["profit_factor"] or "0")) >= SECONDARY_PF_GOAL
        and Decimal(str(s["max_drawdown_r"])) <= SECONDARY_DD_GOAL
    )


def _rank(row: dict[str, Any]) -> tuple[int, Decimal, Decimal, Decimal]:
    p = cast(dict[str, Any], row["primary"])
    s = cast(dict[str, Any], row["secondary"])
    return (
        int(_passes_goal(row)),
        Decimal(str(p["profit_factor"] or "0")),
        -Decimal(str(p["max_drawdown_r"])),
        Decimal(str(s["profit_factor"] or "0")),
    )


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    bars_by_symbol: dict[str, Sequence[Vt08IndexC2R1Bar]] = {}
    opened_by_symbol: dict[str, tuple[datetime, ...]] = {}
    provenance: dict[str, Any] = {}
    for symbol in r1.SYMBOLS:
        bars, source = r2._load_cibo_m15_available(roots[symbol], symbol=symbol)
        bars_by_symbol[symbol] = bars
        opened_by_symbol[symbol] = tuple(
            bar.opened_at.astimezone(UTC) for bar in bars
        )
        provenance[symbol] = source

    signals = _fixed_admissions(bars_by_symbol=bars_by_symbol)
    reports: list[dict[str, Any]] = []
    for policy in _policy_grid():
        outcomes = tuple(
            _manage_trade(
                signal,
                bars=bars_by_symbol[signal.symbol],
                opened=opened_by_symbol[signal.symbol],
                policy=policy,
            )
            for signal in signals
        )
        row: dict[str, Any] = {
            "policy": policy.payload(),
            "primary": _metrics(
                signals,
                outcomes,
                stress=PRIMARY_STRESS,
            ),
            "secondary": _metrics(
                signals,
                outcomes,
                stress=SECONDARY_STRESS,
            ),
        }
        row["goal_pass"] = _passes_goal(row)
        reports.append(row)

    reports.sort(key=_rank, reverse=True)
    goal = [row for row in reports if bool(row["goal_pass"])]
    baseline_policy = Policy(
        target_r=BASELINE_TARGET_R,
        soft_close_loss_r=None,
        soft_close_until_mfe_r=None,
        deadline_bars=None,
        deadline_min_mfe_r=None,
        trail_name="OFF",
        trail_steps=(),
    )
    baseline = next(
        row
        for row in reports
        if cast(dict[str, Any], row["policy"])["policy_id"]
        == baseline_policy.policy_id
    )
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "window": {
            "window_id": r1.WINDOW_ID,
            "start_date": r1.START_DATE.isoformat(),
            "end_date_exclusive": r1.END_DATE_EXCLUSIVE.isoformat(),
            "status": "CONSUMED_TUNING",
            "fresh_certification_holdout": False,
        },
        "fixed_admission_contract": {
            "source_round": "ROUND4_MULTI_POI_REARM_2_5R",
            "sample": len(signals),
            "required_sample": FIXED_DENSITY,
            "admission_changes_allowed": False,
            "all_entries_preserved": len(signals) == FIXED_DENSITY,
        },
        "owner_goal": {
            "profit_factor_minimum": str(PF_GOAL),
            "max_drawdown_r": str(DD_GOAL),
            "secondary_profit_factor_minimum": str(SECONDARY_PF_GOAL),
            "secondary_max_drawdown_r": str(SECONDARY_DD_GOAL),
        },
        "policy_count": len(reports),
        "goal_candidate_count": len(goal),
        "baseline": baseline,
        "best": reports[0] if reports else None,
        "top_20": reports[:20],
        "goal_candidates": goal[:20],
        "provenance": provenance,
        "governance": {
            "research_only": True,
            "tuning_window_consumed": True,
            "fresh_holdout_claim": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    best = cast(dict[str, Any] | None, report["best"])
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "fixed_density": FIXED_DENSITY,
                "policy_count": report["policy_count"],
                "goal_candidate_count": report["goal_candidate_count"],
                "best": best,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
