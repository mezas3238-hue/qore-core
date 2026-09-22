"""Strict T2 ATTACK semantics for the frozen VT-08 Index CIBO study.

This module preserves the pre-registered T2 numerical contract and changes no
threshold. It tightens the implementation to the frozen semantic rule:
CIBO may label a posture ATTACK only when Risk can authorize the full ATTACK
envelope for the simultaneous group. Otherwise CIBO falls back to BASE
BUILD/PROTECT/BANK semantics rather than emitting a reduced pseudo-ATTACK.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date

from qore.infrastructure.trader_lab import vt08_index_c2_r1_cibo_capital_t1 as t1
from qore.infrastructure.trader_lab import vt08_index_c2_r1_cibo_capital_t2 as t2

_EPSILON = 1e-12


def run_sequence_t2(
    days: Sequence[date],
    mapped: Mapping[date, Mapping[int, Sequence[t1.ObservedTrade]]],
    *,
    full_guard: bool,
) -> t2.ControllerMetrics:
    """Run frozen T2 with ATTACK only when Risk can authorize it in full."""
    equity = t1.STARTING_EQUITY
    peak = t1.STARTING_EQUITY
    minimum_equity = t1.STARTING_EQUITY
    bank_reference = 0.0
    maximum_capital_drawdown = 0.0
    maximum_daily_drawdown = 0.0
    generated_signals = 0
    executed_trades = 0
    risk_reduced_groups = 0
    risk_rejected_signals = 0
    bank_decisions = 0
    attack_groups = 0
    attack_trades = 0
    cibo_reduce_groups = 0
    cibo_suspend_groups = 0
    cibo_lock_groups = 0
    cibo_reactivate_groups = 0
    touched_five_percent = False
    touched_ten_percent = False
    posture_counts: Counter[str] = Counter()
    previous_blocked = False

    for trading_day in days:
        day_start_equity = equity
        daily_floor = day_start_equity * (1.0 - t1.INTERNAL_DAILY_LIMIT)
        for anchor in sorted(mapped.get(trading_day, {})):
            group = tuple(mapped[trading_day][anchor])
            generated_signals += len(group)

            previous_bank = bank_reference
            bank_reference = t2._bank_reference(peak, bank_reference)
            new_bank = bank_reference > previous_bank + _EPSILON
            if new_bank:
                bank_decisions += 1

            capital_floor = t2._capital_floor(peak)
            daily_headroom = max(0.0, equity - daily_floor)
            capital_headroom = max(0.0, equity - capital_floor)
            absolute_headroom = min(daily_headroom, capital_headroom)

            base_scale = t2._authorization_scale(
                signal_risk=t1.BASE_SIGNAL_RISK,
                heat_ceiling=t1.BASE_HEAT,
                group_size=len(group),
                equity=equity,
                absolute_headroom=absolute_headroom,
            )
            if base_scale <= _EPSILON:
                if capital_headroom <= _EPSILON:
                    posture_counts["LOCK"] += 1
                    cibo_lock_groups += 1
                else:
                    posture_counts["SUSPEND"] += 1
                    cibo_suspend_groups += 1
                risk_rejected_signals += len(group)
                previous_blocked = True
                continue

            if previous_blocked:
                cibo_reactivate_groups += 1
                previous_blocked = False

            capital_drawdown_before = (peak - equity) / peak
            reduce_multiplier = (
                t1.full_guard_multiplier(capital_drawdown_before)
                if full_guard
                else 1.0
            )
            hard_cushion_fraction = absolute_headroom / max(equity, _EPSILON)
            bank_active = bank_reference > t1.STARTING_EQUITY + _EPSILON
            attack_scale = t2._authorization_scale(
                signal_risk=t1.ATTACK_SIGNAL_RISK,
                heat_ceiling=t1.ATTACK_HEAT,
                group_size=len(group),
                equity=equity,
                absolute_headroom=absolute_headroom,
            )
            attack_available = (
                bank_active
                and reduce_multiplier >= 1.0 - _EPSILON
                and hard_cushion_fraction >= t1.MINIMUM_FREE_CUSHION
                and attack_scale >= 1.0 - _EPSILON
            )

            if full_guard and reduce_multiplier < 1.0 - _EPSILON:
                posture = "REDUCE"
                requested_signal_risk = t1.BASE_SIGNAL_RISK * reduce_multiplier
                heat_ceiling = t1.BASE_HEAT * reduce_multiplier
                cibo_reduce_groups += 1
            elif attack_available:
                posture = "ATTACK"
                requested_signal_risk = t1.ATTACK_SIGNAL_RISK
                heat_ceiling = t1.ATTACK_HEAT
                attack_groups += 1
            elif new_bank:
                posture = "BANK"
                requested_signal_risk = t1.BASE_SIGNAL_RISK
                heat_ceiling = t1.BASE_HEAT
            elif bank_active or equity > t1.STARTING_EQUITY:
                posture = "PROTECT"
                requested_signal_risk = t1.BASE_SIGNAL_RISK
                heat_ceiling = t1.BASE_HEAT
            else:
                posture = "BUILD"
                requested_signal_risk = t1.BASE_SIGNAL_RISK
                heat_ceiling = t1.BASE_HEAT
            posture_counts[posture] += 1

            risk_scale = t2._authorization_scale(
                signal_risk=requested_signal_risk,
                heat_ceiling=heat_ceiling,
                group_size=len(group),
                equity=equity,
                absolute_headroom=absolute_headroom,
            )
            if posture == "ATTACK" and risk_scale < 1.0 - _EPSILON:
                raise t2.Vt08IndexCiboCapitalT2Error(
                    "ATTACK posture requires full Risk-authorizable envelope"
                )
            if risk_scale <= _EPSILON:
                risk_rejected_signals += len(group)
                previous_blocked = True
                continue
            if risk_scale < 1.0 - _EPSILON:
                risk_reduced_groups += 1

            pnl = 0.0
            for trade in group:
                authorized_risk = requested_signal_risk * risk_scale
                if authorized_risk <= _EPSILON:
                    risk_rejected_signals += 1
                    continue
                pnl += equity * authorized_risk * trade.r_multiple
                executed_trades += 1
                if posture == "ATTACK":
                    attack_trades += 1

            equity += pnl
            if equity <= 0.0 or not math.isfinite(equity):
                raise t2.Vt08IndexCiboCapitalT2Error("equity became invalid")
            peak = max(peak, equity)
            minimum_equity = min(minimum_equity, equity)
            capital_drawdown = (peak - equity) / peak
            daily_drawdown = max(0.0, (day_start_equity - equity) / day_start_equity)
            maximum_capital_drawdown = max(
                maximum_capital_drawdown,
                capital_drawdown,
            )
            maximum_daily_drawdown = max(maximum_daily_drawdown, daily_drawdown)
            touched_five_percent = touched_five_percent or peak >= 1.05
            touched_ten_percent = touched_ten_percent or peak >= 1.10

            if daily_drawdown >= t1.PROVIDER_LIMIT - _EPSILON:
                raise t2.Vt08IndexCiboCapitalT2Error(
                    "provider 5% daily boundary was touched"
                )
            if capital_drawdown >= t1.PROVIDER_LIMIT - _EPSILON:
                raise t2.Vt08IndexCiboCapitalT2Error(
                    "provider 5% capital boundary was touched"
                )
            if daily_drawdown > t1.INTERNAL_DAILY_LIMIT + _EPSILON:
                raise t2.Vt08IndexCiboCapitalT2Error(
                    "internal daily drawdown ceiling was violated"
                )
            if capital_drawdown > t1.INTERNAL_CAPITAL_LIMIT + _EPSILON:
                raise t2.Vt08IndexCiboCapitalT2Error(
                    "internal capital drawdown ceiling was violated"
                )

    return t2.ControllerMetrics(
        terminal_return=equity - t1.STARTING_EQUITY,
        peak_equity=peak,
        minimum_equity=minimum_equity,
        maximum_capital_drawdown=maximum_capital_drawdown,
        maximum_daily_drawdown=maximum_daily_drawdown,
        generated_signals=generated_signals,
        executed_trades=executed_trades,
        risk_reduced_groups=risk_reduced_groups,
        risk_rejected_signals=risk_rejected_signals,
        bank_decisions=bank_decisions,
        attack_groups=attack_groups,
        attack_trades=attack_trades,
        cibo_reduce_groups=cibo_reduce_groups,
        cibo_suspend_groups=cibo_suspend_groups,
        cibo_lock_groups=cibo_lock_groups,
        cibo_reactivate_groups=cibo_reactivate_groups,
        touched_five_percent=touched_five_percent,
        touched_ten_percent=touched_ten_percent,
        posture_counts=tuple(sorted(posture_counts.items())),
    )


# Patch the frozen T2 report machinery before it evaluates chronology or MC.
t2.run_sequence_t2 = run_sequence_t2


def main() -> None:
    t2.run_sequence_t2 = run_sequence_t2
    t2.main()


if __name__ == "__main__":
    main()
