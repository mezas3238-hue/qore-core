"""Position/lifecycle forensics for QORE Capitalizer Structural V2.

This development-only layer deliberately keeps ENTRY COGNITION frozen at the Structural V2
selection and asks a different question: once a structurally eligible trade exists, can a
strictly causal, monotonic structural stop reduce loss clustering without target fitting?

Two ablations are diagnostic only:
- SWING_IMPROVE: after a three-bar pivot is fully confirmed, move the stop to any newly
  confirmed swing that improves risk. The stop may improve or hold, never widen.
- PROFITABLE_SWING_LOCK: same, but only when the confirmed swing is beyond entry and therefore
  locks non-negative economic territory.
- RECLAIM_FRESH_PROFITABLE_SWING_LOCK: apply profitable swing protection only to the causal
  RECLAIM_ALL_FRESH route, while continuation-without-reclaim and rejection routes remain
  untouched.

A pivot is known only after the following M5 bar closes. The stop update becomes eligible for
the *next* M5 bar, never the bar that confirms it. This prevents intrabar lookahead.

Future path data is used only for outcome labeling/simulation. Nothing in this module is an
entry feature, candidate freeze, promotion decision, execution authorization, or fresh holdout.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from statistics import median, quantiles

from qore.infrastructure.trader_lab.capitalizer_atlas_m5_reader import (
    BAR_DURATION,
    CapitalizerM5Bar,
    iter_atlas_m5,
)
from qore.infrastructure.trader_lab.capitalizer_cognitive_v2_development import (
    _asia_session_day,
    _root_state_index,
    select_development_trades,
)
from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_r0_gross_characterization import (
    CapitalizerR0Metrics,
    CapitalizerR0Trade,
    build_r0_trades,
    summarize_r0,
)
from qore.infrastructure.trader_lab.capitalizer_session_clock import capitalizer_session_at

IDENTITY = "QORE_CAPITALIZER_POSITION_LIFECYCLE_FORENSICS_V1"


class CapitalizerLifecycleMode(StrEnum):
    ORIGINAL = "ORIGINAL"
    SWING_IMPROVE = "SWING_IMPROVE"
    PROFITABLE_SWING_LOCK = "PROFITABLE_SWING_LOCK"


@dataclass(frozen=True, slots=True)
class CapitalizerLifecycleLossDiagnostic:
    structural_v2_losses: int
    stop_losses: int
    stop_losses_with_strict_prior_favorable_excursion: int
    stop_losses_with_confirmed_improving_swing: int
    stop_losses_with_confirmed_profitable_swing: int
    median_strict_prior_mfe_r: str
    p25_strict_prior_mfe_r: str
    p75_strict_prior_mfe_r: str


@dataclass(frozen=True, slots=True)
class CapitalizerLifecycleAblation:
    mode: str
    metrics: CapitalizerR0Metrics
    changed_outcomes: int
    improved_losing_outcomes: int
    degraded_winning_outcomes: int


@dataclass(frozen=True, slots=True)
class CapitalizerLifecycleAnnual:
    year: int
    mode: str
    metrics: CapitalizerR0Metrics


@dataclass(frozen=True, slots=True)
class CapitalizerPositionLifecycleReport:
    identity: str
    symbol: str
    structural_v2_metrics: CapitalizerR0Metrics
    loss_diagnostic: CapitalizerLifecycleLossDiagnostic
    state_family_counts: dict[str, int]
    ablations: tuple[CapitalizerLifecycleAblation, ...]
    annual: tuple[CapitalizerLifecycleAnnual, ...]
    evidence_status: str = "CONSUMED_RESEARCH_EVIDENCE"
    development_only: bool = True
    entry_cognition_changed: bool = False
    causal_stop_updates_only: bool = True
    stop_can_widen: bool = False
    target_changed: bool = False
    numeric_profit_threshold_optimized: bool = False
    costs_applied: bool = False
    candidate_frozen: bool = False
    fresh_holdout_claimed: bool = False
    rule_selected: bool = False
    promotion_allowed: bool = False


def _bar_indices(
    bars: tuple[CapitalizerM5Bar, ...],
) -> tuple[dict[datetime, int], dict[datetime, int]]:
    by_open = {bar.opened_at: index for index, bar in enumerate(bars)}
    by_close = {bar.closed_at: index for index, bar in enumerate(bars)}
    return by_open, by_close


def _directional_stop_r(
    *,
    side: CapitalizerSide,
    entry: Decimal,
    stop: Decimal,
    risk: Decimal,
) -> Decimal:
    delta = stop - entry if side is CapitalizerSide.LONG else entry - stop
    return delta / risk


def _pivot_candidate(
    previous: CapitalizerM5Bar,
    middle: CapitalizerM5Bar,
    current: CapitalizerM5Bar,
    *,
    side: CapitalizerSide,
) -> Decimal | None:
    if (
        middle.opened_at - previous.opened_at != BAR_DURATION
        or current.opened_at - middle.opened_at != BAR_DURATION
    ):
        return None
    if side is CapitalizerSide.LONG:
        if middle.low < previous.low and middle.low < current.low:
            return middle.low
        return None
    if middle.high > previous.high and middle.high > current.high:
        return middle.high
    return None


def _can_improve_stop(
    *,
    side: CapitalizerSide,
    active_stop: Decimal,
    candidate: Decimal,
    current_close: Decimal,
) -> bool:
    if side is CapitalizerSide.LONG:
        return active_stop < candidate < current_close
    return active_stop > candidate > current_close


def _profitable_side(
    *,
    side: CapitalizerSide,
    entry: Decimal,
    candidate: Decimal,
) -> bool:
    if side is CapitalizerSide.LONG:
        return candidate > entry
    return candidate < entry


def _simulate_trade(
    trade: CapitalizerR0Trade,
    *,
    bars: tuple[CapitalizerM5Bar, ...],
    by_open: dict[datetime, int],
    mode: CapitalizerLifecycleMode,
) -> CapitalizerR0Trade:
    if mode is CapitalizerLifecycleMode.ORIGINAL:
        return trade

    entry_index = by_open.get(trade.entry_at)
    if entry_index is None:
        raise ValueError("trade entry must map to exact M5 open")
    session = capitalizer_session_at(bars[entry_index].opened_at)
    if session is None:
        raise ValueError("trade entry must belong to Capitalizer session")

    active_stop = trade.stop_price
    last_close = trade.entry_price
    bars_held = 0

    for offset in range(entry_index, len(bars)):
        bar = bars[offset]
        if offset > entry_index:
            previous_bar = bars[offset - 1]
            if bar.opened_at - previous_bar.opened_at != BAR_DURATION:
                break
        if capitalizer_session_at(bar.opened_at) is not session:
            break

        bars_held += 1
        last_close = bar.close
        if trade.side is CapitalizerSide.LONG:
            stop_hit = bar.low <= active_stop
            target_hit = bar.high >= trade.target_price
        else:
            stop_hit = bar.high >= active_stop
            target_hit = bar.low <= trade.target_price

        # Preserve R0 STOP_FIRST ambiguity handling. A stop confirmed before this bar
        # is actionable during this bar; a pivot confirmed by this bar is not.
        if stop_hit:
            return replace(
                trade,
                exit_at=bar.closed_at,
                realized_gross_r=_directional_stop_r(
                    side=trade.side,
                    entry=trade.entry_price,
                    stop=active_stop,
                    risk=trade.initial_risk_price,
                ),
                exit_reason="STOP",
                bars_held=bars_held,
                same_bar_stop_target_ambiguity=target_hit,
            )
        if target_hit:
            return replace(
                trade,
                exit_at=bar.closed_at,
                realized_gross_r=trade.planned_reward_r,
                exit_reason="TARGET",
                bars_held=bars_held,
                same_bar_stop_target_ambiguity=False,
            )

        # Update only *after* the confirming bar closes, so the improved stop can
        # become active no earlier than the next M5 bar.
        if offset >= entry_index + 2:
            candidate = _pivot_candidate(
                bars[offset - 2],
                bars[offset - 1],
                bar,
                side=trade.side,
            )
            if (
                candidate is not None
                and _can_improve_stop(
                    side=trade.side,
                    active_stop=active_stop,
                    candidate=candidate,
                    current_close=bar.close,
                )
                and (
                    mode is CapitalizerLifecycleMode.SWING_IMPROVE
                    or _profitable_side(
                        side=trade.side,
                        entry=trade.entry_price,
                        candidate=candidate,
                    )
                )
            ):
                active_stop = candidate

    final_bar = bars[entry_index + bars_held - 1]
    delta = (
        last_close - trade.entry_price
        if trade.side is CapitalizerSide.LONG
        else trade.entry_price - last_close
    )
    return replace(
        trade,
        exit_at=final_bar.closed_at,
        realized_gross_r=delta / trade.initial_risk_price,
        exit_reason="SESSION_EXIT",
        bars_held=bars_held,
        same_bar_stop_target_ambiguity=False,
    )


def _strict_prior_mfe_r(
    trade: CapitalizerR0Trade,
    *,
    bars: tuple[CapitalizerM5Bar, ...],
    by_open: dict[datetime, int],
    by_close: dict[datetime, int],
) -> Decimal:
    entry_index = by_open.get(trade.entry_at)
    exit_index = by_close.get(trade.exit_at)
    if entry_index is None or exit_index is None or exit_index < entry_index:
        raise ValueError("trade lifecycle must map to exact M5 indices")
    prior = bars[entry_index:exit_index]
    if not prior:
        return Decimal("0")
    if trade.side is CapitalizerSide.LONG:
        favorable = max(bar.high for bar in prior) - trade.entry_price
    else:
        favorable = trade.entry_price - min(bar.low for bar in prior)
    return max(favorable, Decimal("0")) / trade.initial_risk_price


def _confirmed_swing_before_exit(
    trade: CapitalizerR0Trade,
    *,
    bars: tuple[CapitalizerM5Bar, ...],
    by_open: dict[datetime, int],
    by_close: dict[datetime, int],
    profitable_only: bool,
) -> bool:
    entry_index = by_open.get(trade.entry_at)
    exit_index = by_close.get(trade.exit_at)
    if entry_index is None or exit_index is None or exit_index < entry_index:
        raise ValueError("trade lifecycle must map to exact M5 indices")

    active_stop = trade.stop_price
    # exit_index is excluded: a pivot confirmed by the stop bar is too late.
    for offset in range(entry_index + 2, exit_index):
        candidate = _pivot_candidate(
            bars[offset - 2],
            bars[offset - 1],
            bars[offset],
            side=trade.side,
        )
        if candidate is None:
            continue
        if not _can_improve_stop(
            side=trade.side,
            active_stop=active_stop,
            candidate=candidate,
            current_close=bars[offset].close,
        ):
            continue
        active_stop = candidate
        if not profitable_only or _profitable_side(
            side=trade.side,
            entry=trade.entry_price,
            candidate=candidate,
        ):
            return True
    return False


def _loss_diagnostic(
    trades: tuple[CapitalizerR0Trade, ...],
    *,
    bars: tuple[CapitalizerM5Bar, ...],
    by_open: dict[datetime, int],
    by_close: dict[datetime, int],
) -> CapitalizerLifecycleLossDiagnostic:
    losing = tuple(item for item in trades if item.realized_gross_r < 0)
    stop_losses = tuple(item for item in losing if item.exit_reason == "STOP")
    if not stop_losses:
        raise ValueError("lifecycle forensics require stop losses")
    mfe = tuple(
        _strict_prior_mfe_r(
            item,
            bars=bars,
            by_open=by_open,
            by_close=by_close,
        )
        for item in stop_losses
    )
    quartiles = quantiles(mfe, n=4)
    return CapitalizerLifecycleLossDiagnostic(
        structural_v2_losses=len(losing),
        stop_losses=len(stop_losses),
        stop_losses_with_strict_prior_favorable_excursion=sum(
            value > 0 for value in mfe
        ),
        stop_losses_with_confirmed_improving_swing=sum(
            _confirmed_swing_before_exit(
                item,
                bars=bars,
                by_open=by_open,
                by_close=by_close,
                profitable_only=False,
            )
            for item in stop_losses
        ),
        stop_losses_with_confirmed_profitable_swing=sum(
            _confirmed_swing_before_exit(
                item,
                bars=bars,
                by_open=by_open,
                by_close=by_close,
                profitable_only=True,
            )
            for item in stop_losses
        ),
        median_strict_prior_mfe_r=str(median(mfe)),
        p25_strict_prior_mfe_r=str(quartiles[0]),
        p75_strict_prior_mfe_r=str(quartiles[2]),
    )


def _ablation(
    *,
    name: str,
    original: tuple[CapitalizerR0Trade, ...],
    simulated: tuple[CapitalizerR0Trade, ...],
) -> CapitalizerLifecycleAblation:
    if len(original) != len(simulated):
        raise ValueError("lifecycle ablation trade counts must match")
    changed = 0
    improved_losses = 0
    degraded_wins = 0
    for before, after in zip(original, simulated, strict=True):
        if before.realized_gross_r != after.realized_gross_r:
            changed += 1
        if before.realized_gross_r < 0 and after.realized_gross_r > before.realized_gross_r:
            improved_losses += 1
        if before.realized_gross_r > 0 and after.realized_gross_r < before.realized_gross_r:
            degraded_wins += 1
    return CapitalizerLifecycleAblation(
        mode=name,
        metrics=summarize_r0(simulated).metrics,
        changed_outcomes=changed,
        improved_losing_outcomes=improved_losses,
        degraded_winning_outcomes=degraded_wins,
    )


def _state_family(
    trade: CapitalizerR0Trade,
    state_index: dict[tuple[str, CapitalizerSide], str],
) -> str:
    key = (trade.signal_at.isoformat(), trade.side)
    state = state_index.get(key)
    if state is not None:
        return state
    if any("ACCEPTANCE" in label for label in trade.event_labels):
        raise ValueError("acceptance trade requires causal state family")
    return "REJECTION_ROUTE"


def _year(trade: CapitalizerR0Trade) -> int:
    return int(_asia_session_day(trade)[:4])


def build_position_lifecycle_report(
    *,
    m5_root: Path,
    journey_root: Path,
    target_root: Path,
) -> CapitalizerPositionLifecycleReport:
    all_trades = build_r0_trades(
        m5_root=m5_root,
        journey_root=journey_root,
        target_root=target_root,
    )
    if not all_trades:
        raise ValueError("position lifecycle forensics require R0 trades")
    state_index = _root_state_index(
        m5_root=m5_root,
        journey_root=journey_root,
        trades=all_trades,
    )
    structural, _, _, _ = select_development_trades(
        trades=all_trades,
        state_index=state_index,
        block_late_acceptance_repeat=True,
        block_journey_conflict=True,
        apply_session_ceiling=False,
    )
    if not structural:
        raise ValueError("Structural V2 selection cannot be empty")

    bars = tuple(iter_atlas_m5(m5_root))
    by_open, by_close = _bar_indices(bars)
    simulated_by_mode: dict[str, tuple[CapitalizerR0Trade, ...]] = {
        CapitalizerLifecycleMode.ORIGINAL.value: structural
    }
    for mode in (
        CapitalizerLifecycleMode.SWING_IMPROVE,
        CapitalizerLifecycleMode.PROFITABLE_SWING_LOCK,
    ):
        simulated_by_mode[mode.value] = tuple(
            _simulate_trade(
                trade,
                bars=bars,
                by_open=by_open,
                mode=mode,
            )
            for trade in structural
        )

    selective_name = "RECLAIM_FRESH_PROFITABLE_SWING_LOCK"
    simulated_by_mode[selective_name] = tuple(
        _simulate_trade(
            trade,
            bars=bars,
            by_open=by_open,
            mode=CapitalizerLifecycleMode.PROFITABLE_SWING_LOCK,
        )
        if _state_family(trade, state_index) == "RECLAIM_ALL_FRESH"
        else trade
        for trade in structural
    )

    ablations = tuple(
        _ablation(
            name=name,
            original=structural,
            simulated=simulated,
        )
        for name, simulated in simulated_by_mode.items()
        if name != CapitalizerLifecycleMode.ORIGINAL.value
    )

    annual: list[CapitalizerLifecycleAnnual] = []
    years = sorted({_year(item) for item in structural})
    for mode_name, simulated in simulated_by_mode.items():
        for year in years:
            subset = tuple(item for item in simulated if _year(item) == year)
            if not subset:
                continue
            annual.append(
                CapitalizerLifecycleAnnual(
                    year=year,
                    mode=mode_name,
                    metrics=summarize_r0(subset).metrics,
                )
            )

    return CapitalizerPositionLifecycleReport(
        identity=IDENTITY,
        symbol=structural[0].symbol,
        structural_v2_metrics=summarize_r0(structural).metrics,
        loss_diagnostic=_loss_diagnostic(
            structural,
            bars=bars,
            by_open=by_open,
            by_close=by_close,
        ),
        state_family_counts=dict(
            sorted(
                Counter(
                    _state_family(trade, state_index)
                    for trade in structural
                ).items()
            )
        ),
        ablations=ablations,
        annual=tuple(annual),
    )


def write_position_lifecycle_report(
    report: CapitalizerPositionLifecycleReport,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"capitalizer-{report.symbol.lower()}-position-lifecycle-v1.json"
    path.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capitalizer Structural V2 position/lifecycle forensics"
    )
    parser.add_argument("m5_root", type=Path)
    parser.add_argument("journey_root", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_position_lifecycle_report(
        m5_root=args.m5_root,
        journey_root=args.journey_root,
        target_root=args.target_root,
    )
    write_position_lifecycle_report(report, args.output)
    print(
        json.dumps(
            {
                "identity": report.identity,
                "symbol": report.symbol,
                "structural_v2": asdict(report.structural_v2_metrics),
                "loss_diagnostic": asdict(report.loss_diagnostic),
                "ablations": [
                    {
                        "mode": item.mode,
                        "metrics": asdict(item.metrics),
                        "changed_outcomes": item.changed_outcomes,
                        "improved_losing_outcomes": item.improved_losing_outcomes,
                        "degraded_winning_outcomes": item.degraded_winning_outcomes,
                    }
                    for item in report.ablations
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
