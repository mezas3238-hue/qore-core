"""Universal causal CIBO position lifecycle engine.

This module owns temporal lifecycle semantics.  It is environment-neutral and
non-authoritative: replay, TEST, DEMO and future productive adapters may all
consume the same proposals, while QORE Risk / execution remain external.

A protection derived from closed BAR N becomes active only after BAR N.  The
engine never invents M5 intrabar ordering.  If no lifecycle intervention closes
the position, the original structural settlement remains authoritative.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
class CiboLifecycleBar(Protocol):
    """Minimal sovereign bar contract consumed by CIBO lifecycle cognition."""

    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


class CiboLifecycleFeature(StrEnum):
    BREAKEVEN = "BREAKEVEN"
    PROFIT_LOCK = "PROFIT_LOCK"
    TRAILING = "TRAILING"
    PARTIAL_REALIZATION = "PARTIAL_REALIZATION"
    EXTENDED_TARGET = "EXTENDED_TARGET"
    ADVERSE_LOSS_CUT = "ADVERSE_LOSS_CUT"
    ADVERSE_PARTIAL_REDUCTION = "ADVERSE_PARTIAL_REDUCTION"
    BOOTSTRAP_PARTIAL_REDUCTION = "BOOTSTRAP_PARTIAL_REDUCTION"
    ADVERSE_STOP_TIGHTEN = "ADVERSE_STOP_TIGHTEN"


# Keep the established lifecycle baseline stable while the adverse-loss
# feature is experimentally swept in Trader Lab. Promotion into the default
# lifecycle set requires causal frontier evidence.
FULL_CIBO_LIFECYCLE_FEATURES = frozenset(
    item
    for item in CiboLifecycleFeature
    if item not in {
        CiboLifecycleFeature.ADVERSE_LOSS_CUT,
        CiboLifecycleFeature.ADVERSE_PARTIAL_REDUCTION,
        CiboLifecycleFeature.BOOTSTRAP_PARTIAL_REDUCTION,
        CiboLifecycleFeature.ADVERSE_STOP_TIGHTEN,
    }
)


@dataclass(frozen=True, slots=True)
class CiboPositionLifecycleInput:
    signal_fingerprint: str
    side: str
    entry_at: datetime
    horizon_at: datetime
    entry_price: Decimal
    structural_stop: Decimal
    technical_target: Decimal
    provider_cost_per_volume_usd: Decimal
    stop_risk_per_volume_usd: Decimal
    original_settlement_gross_r: Decimal

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "Lifecycle signal identity required"
            )
        if self.side not in {"long", "short"}:
            raise CiboCapitalManagementError(
                "Lifecycle side must be long/short"
            )
        for name in ("entry_at", "horizon_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"Lifecycle {name} must be timezone-aware"
                )
        if self.entry_at >= self.horizon_at:
            raise CiboCapitalManagementError(
                "Lifecycle horizon must follow entry"
            )
        for name in (
            "entry_price",
            "structural_stop",
            "technical_target",
            "provider_cost_per_volume_usd",
            "stop_risk_per_volume_usd",
            "original_settlement_gross_r",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"Lifecycle {name} must be finite Decimal"
                )
        if self.stop_risk_per_volume_usd <= 0:
            raise CiboCapitalManagementError(
                "Lifecycle stop risk per volume must be positive"
            )
        if self.provider_cost_per_volume_usd < 0:
            raise CiboCapitalManagementError(
                "Lifecycle provider cost cannot be negative"
            )
        if self.entry_price == self.structural_stop:
            raise CiboCapitalManagementError(
                "Lifecycle structural stop distance must be nonzero"
            )


@dataclass(frozen=True, slots=True)
class CiboLifecycleEvent:
    occurred_at: datetime
    action: str
    realized_r_delta: Decimal
    remaining_volume_fraction: Decimal
    risk_fraction_remaining: Decimal
    margin_fraction_remaining: Decimal


@dataclass(frozen=True, slots=True)
class CiboPositionLifecycleResult:
    signal_fingerprint: str
    data_available: bool
    gross_r: Decimal
    exit_at: datetime
    events: tuple[CiboLifecycleEvent, ...]
    risk_released_before_exit_fraction: Decimal
    margin_released_before_exit_fraction: Decimal
    actions: tuple[str, ...]


def run_cibo_position_lifecycle(
    position: CiboPositionLifecycleInput,
    bars: Sequence[CiboLifecycleBar],
    *,
    features: frozenset[CiboLifecycleFeature] = FULL_CIBO_LIFECYCLE_FEATURES,
    adverse_loss_cut_r: Decimal = Decimal("-0.50"),
    adverse_partial_fraction: Decimal = Decimal("0.25"),
    bootstrap_partial_fraction: Decimal = Decimal("0.50"),
    adverse_tightened_stop_r: Decimal = Decimal("-0.50"),
) -> CiboPositionLifecycleResult:
    """Evaluate one position using causal closed-bar lifecycle semantics."""

    if not isinstance(position, CiboPositionLifecycleInput):
        raise CiboCapitalManagementError(
            "Lifecycle requires canonical input"
        )
    if (
        not isinstance(adverse_loss_cut_r, Decimal)
        or not adverse_loss_cut_r.is_finite()
        or adverse_loss_cut_r <= Decimal("-1")
        or adverse_loss_cut_r >= Decimal(0)
    ):
        raise CiboCapitalManagementError(
            "Lifecycle adverse loss cut must be Decimal strictly between -1R and 0R"
        )
    if (
        not isinstance(adverse_partial_fraction, Decimal)
        or not adverse_partial_fraction.is_finite()
        or adverse_partial_fraction <= 0
        or adverse_partial_fraction >= 1
    ):
        raise CiboCapitalManagementError(
            "Lifecycle adverse partial fraction must be Decimal strictly between 0 and 1"
        )
    if (
        not isinstance(bootstrap_partial_fraction, Decimal)
        or not bootstrap_partial_fraction.is_finite()
        or bootstrap_partial_fraction <= 0
        or bootstrap_partial_fraction >= 1
    ):
        raise CiboCapitalManagementError(
            "Lifecycle bootstrap partial fraction must be Decimal strictly between 0 and 1"
        )
    if (
        not isinstance(adverse_tightened_stop_r, Decimal)
        or not adverse_tightened_stop_r.is_finite()
        or adverse_tightened_stop_r <= Decimal("-1")
        or adverse_tightened_stop_r >= Decimal(0)
    ):
        raise CiboCapitalManagementError(
            "Lifecycle adverse tightened stop must be Decimal strictly between -1R and 0R"
        )
    if (
        CiboLifecycleFeature.ADVERSE_STOP_TIGHTEN in features
        and adverse_tightened_stop_r >= adverse_loss_cut_r
    ):
        raise CiboCapitalManagementError(
            "Lifecycle tightened stop must remain below its adverse close trigger"
        )

    risk_distance = abs(position.entry_price - position.structural_stop)
    target_r = abs(
        position.technical_target - position.entry_price
    ) / risk_distance
    cost_r = (
        position.provider_cost_per_volume_usd
        / position.stop_risk_per_volume_usd
    )
    causal_bars = tuple(
        bar
        for bar in bars
        if (
            bar.opened_at >= position.entry_at
            and bar.closed_at <= position.horizon_at
        )
    )

    def original_settlement(
        *, data_available: bool, action: str
    ) -> CiboPositionLifecycleResult:
        event = CiboLifecycleEvent(
            occurred_at=position.horizon_at,
            action=action,
            realized_r_delta=position.original_settlement_gross_r,
            remaining_volume_fraction=Decimal(0),
            risk_fraction_remaining=Decimal(0),
            margin_fraction_remaining=Decimal(0),
        )
        return CiboPositionLifecycleResult(
            signal_fingerprint=position.signal_fingerprint,
            data_available=data_available,
            gross_r=position.original_settlement_gross_r,
            exit_at=position.horizon_at,
            events=(event,),
            risk_released_before_exit_fraction=Decimal(0),
            margin_released_before_exit_fraction=Decimal(0),
            actions=(event.action,),
        )

    if not causal_bars:
        return original_settlement(
            data_available=False,
            action="FALLBACK_ORIGINAL_SETTLEMENT",
        )
    if not features:
        return original_settlement(
            data_available=True,
            action="LIFECYCLE_OFF_ORIGINAL_SETTLEMENT",
        )

    remaining = Decimal(1)
    stop_r = Decimal(-1)
    partial_done = False
    be_done = False
    lock_done = False
    realized_r = Decimal(0)
    events: list[CiboLifecycleEvent] = []
    risk_fraction = Decimal(1)
    margin_fraction = Decimal(1)
    best_favorable_seen = Decimal("-Infinity")
    pending_adverse_loss_cut = False
    pending_adverse_partial_reduction = False
    adverse_partial_done = False
    bootstrap_partial_done = False
    adverse_stop_tightened = False

    def favorable_adverse_close(
        bar: CiboLifecycleBar,
    ) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        if position.side == "long":
            return (
                (bar.open - position.entry_price) / risk_distance,
                (bar.high - position.entry_price) / risk_distance,
                (bar.low - position.entry_price) / risk_distance,
                (bar.close - position.entry_price) / risk_distance,
            )
        return (
            (position.entry_price - bar.open) / risk_distance,
            (position.entry_price - bar.low) / risk_distance,
            (position.entry_price - bar.high) / risk_distance,
            (position.entry_price - bar.close) / risk_distance,
        )

    def append_event(
        at: datetime,
        action: str,
        realized_delta: Decimal = Decimal(0),
        *,
        force_close: bool = False,
    ) -> None:
        nonlocal realized_r, risk_fraction, margin_fraction
        realized_r += realized_delta
        next_margin = Decimal(0) if force_close else remaining
        next_risk = (
            Decimal(0)
            if force_close
            else remaining * max(Decimal(0), -stop_r)
        )
        risk_fraction = min(risk_fraction, next_risk)
        margin_fraction = min(margin_fraction, next_margin)
        events.append(
            CiboLifecycleEvent(
                occurred_at=at,
                action=action,
                realized_r_delta=realized_delta,
                remaining_volume_fraction=(
                    Decimal(0) if force_close else remaining
                ),
                risk_fraction_remaining=risk_fraction,
                margin_fraction_remaining=margin_fraction,
            )
        )

    for bar in causal_bars:
        open_r, favorable, adverse, close_r = favorable_adverse_close(bar)

        if (
            CiboLifecycleFeature.BOOTSTRAP_PARTIAL_REDUCTION in features
            and not bootstrap_partial_done
            and bar.opened_at > position.entry_at
            and remaining > 0
        ):
            close_fraction = min(bootstrap_partial_fraction, remaining)
            remaining -= close_fraction
            append_event(
                bar.opened_at,
                "BOOTSTRAP_PARTIAL_REDUCTION_NEXT_OPEN",
                close_fraction * open_r,
            )
            bootstrap_partial_done = True

        # A deterioration signal is known only after BAR N closes. Both
        # defensive actions execute at BAR N+1 open, never retroactively.
        if pending_adverse_partial_reduction:
            close_fraction = min(adverse_partial_fraction, remaining)
            remaining -= close_fraction
            append_event(
                bar.opened_at,
                "ADVERSE_PARTIAL_REDUCTION_NEXT_OPEN",
                close_fraction * open_r,
            )
            pending_adverse_partial_reduction = False
            adverse_partial_done = True

        if pending_adverse_loss_cut:
            delta = remaining * open_r
            remaining = Decimal(0)
            append_event(
                bar.opened_at,
                "ADVERSE_LOSS_CUT_NEXT_OPEN",
                delta,
                force_close=True,
            )
            break

        # A protection armed on a prior closed bar is executable from this
        # bar's open. If price gaps through that stop, use the observable open
        # rather than granting an impossible fill at the protected stop.
        active_stop_r = stop_r
        if (
            active_stop_r > Decimal("-1")
            and open_r <= active_stop_r
        ):
            delta = remaining * open_r
            remaining = Decimal(0)
            append_event(
                bar.opened_at,
                "PROTECTED_STOP_GAP_OPEN",
                delta,
                force_close=True,
            )
            break

        # If BAR N crosses the original structural stop while also
        # containing favorable lifecycle triggers, M5 alone cannot establish
        # which path occurred first.  Do not invent intrabar ordering or apply
        # lifecycle actions that may have occurred after the position ceased.
        # Preserve the original structural settlement as the authoritative
        # outcome and stop lifecycle evaluation for this position.
        if active_stop_r == Decimal(-1) and adverse <= Decimal(-1):
            break

        # Only protection active before BAR N may execute inside BAR N.
        if active_stop_r > Decimal(-1) and adverse <= active_stop_r:
            delta = remaining * active_stop_r
            remaining = Decimal(0)
            append_event(
                bar.closed_at,
                "STOP_OR_PROTECTED_STOP",
                delta,
                force_close=True,
            )
            break

        best_favorable_seen = max(best_favorable_seen, favorable)

        if (
            CiboLifecycleFeature.PARTIAL_REALIZATION in features
            and not partial_done
            and close_r >= Decimal(1)
            and target_r > Decimal(1)
            and bar.closed_at < position.horizon_at
        ):
            close_fraction = min(Decimal("0.25"), remaining)
            remaining -= close_fraction
            partial_done = True
            append_event(
                bar.closed_at,
                "PARTIAL_REALIZATION_AT_CLOSE",
                close_fraction * close_r,
            )

        next_stop_r = stop_r
        close_actions: list[str] = []

        if (
            CiboLifecycleFeature.BREAKEVEN in features
            and not be_done
            and favorable >= Decimal(1)
            and bar.closed_at < position.horizon_at
        ):
            proposed = max(next_stop_r, cost_r)
            if proposed > next_stop_r:
                next_stop_r = proposed
                close_actions.append("MOVE_TO_BREAKEVEN")
            be_done = True

        if (
            CiboLifecycleFeature.PROFIT_LOCK in features
            and not lock_done
            and favorable >= Decimal("1.5")
            and bar.closed_at < position.horizon_at
        ):
            proposed = max(next_stop_r, Decimal("0.5"))
            if proposed > next_stop_r:
                next_stop_r = proposed
                close_actions.append("PROFIT_LOCK")
            lock_done = True

        if (
            CiboLifecycleFeature.TRAILING in features
            and favorable >= Decimal(2)
            and bar.closed_at < position.horizon_at
        ):
            proposed = max(next_stop_r, favorable - Decimal(1))
            if proposed > next_stop_r:
                next_stop_r = proposed
                close_actions.append("TRAIL_STOP")

        if (
            CiboLifecycleFeature.ADVERSE_STOP_TIGHTEN in features
            and not adverse_stop_tightened
            and best_favorable_seen < Decimal(1)
            and close_r <= adverse_loss_cut_r
            and bar.closed_at < position.horizon_at
        ):
            proposed = max(next_stop_r, adverse_tightened_stop_r)
            if proposed > next_stop_r:
                next_stop_r = proposed
                close_actions.append("ADVERSE_STOP_TIGHTEN")
            adverse_stop_tightened = True

        # Direct-to-stop losers are the DD surface that winner-protection
        # features do not address.  Only positions that have never reached
        # +1R may arm this cut; this avoids amputating trades that already
        # demonstrated material favorable excursion.
        if (
            CiboLifecycleFeature.ADVERSE_PARTIAL_REDUCTION in features
            and not adverse_partial_done
            and best_favorable_seen < Decimal(1)
            and close_r <= adverse_loss_cut_r
            and bar.closed_at < position.horizon_at
        ):
            pending_adverse_partial_reduction = True

        if (
            CiboLifecycleFeature.ADVERSE_LOSS_CUT in features
            and best_favorable_seen < Decimal(1)
            and close_r <= adverse_loss_cut_r
            and bar.closed_at < position.horizon_at
        ):
            pending_adverse_loss_cut = True

        # EXTENDED_TARGET remains non-actuating unless path beyond the
        # original structural settlement is supplied by a future adapter.
        if close_actions:
            stop_r = next_stop_r
            for action in close_actions:
                append_event(bar.closed_at, action)

    if remaining > 0:
        delta = remaining * position.original_settlement_gross_r
        remaining = Decimal(0)
        append_event(
            position.horizon_at,
            "HORIZON_ORIGINAL_SETTLEMENT",
            delta,
            force_close=True,
        )

    return CiboPositionLifecycleResult(
        signal_fingerprint=position.signal_fingerprint,
        data_available=True,
        gross_r=realized_r,
        exit_at=events[-1].occurred_at,
        events=tuple(events),
        risk_released_before_exit_fraction=max(
            Decimal(0),
            max(
                (
                    Decimal(1) - item.risk_fraction_remaining
                    for item in events[:-1]
                ),
                default=Decimal(0),
            ),
        ),
        margin_released_before_exit_fraction=max(
            Decimal(0),
            max(
                (
                    Decimal(1) - item.margin_fraction_remaining
                    for item in events[:-1]
                ),
                default=Decimal(0),
            ),
        ),
        actions=tuple(item.action for item in events),
    )
