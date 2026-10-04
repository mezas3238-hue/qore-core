"""Causal Maximum Capability Frontier for CIBO research replays.

The frontier is a non-certifying counterfactual research lane. Every admission,
allocation and leverage choice is made from information available at the decision
clock. Future bars/outcomes are used only after a choice has been frozen to
evaluate the chosen action and position-lifecycle rules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_FLOOR, Decimal
from enum import StrEnum
from itertools import product

from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboObservedEconomicTwin,
    observed_twin_constraints,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Bar


class CiboMaximumCapabilityError(ValueError):
    """The maximum-capability research surface is invalid."""


class LifecycleFeature(StrEnum):
    BREAKEVEN = "BREAKEVEN"
    PROFIT_LOCK = "PROFIT_LOCK"
    TRAILING = "TRAILING"
    PARTIAL_REALIZATION = "PARTIAL_REALIZATION"
    EXTENDED_TARGET = "EXTENDED_TARGET"


FULL_LIFECYCLE_FEATURES = frozenset(LifecycleFeature)
POLICY_ID = "CIBO_MAXIMUM_CAPABILITY_FRONTIER_V1"


@dataclass(frozen=True, slots=True)
class CausalFrontierOpportunity:
    signal_fingerprint: str
    trader_id: str
    qore_symbol: str
    decision_at: datetime
    entry_at: datetime
    horizon_at: datetime
    side: str
    entry_price: Decimal
    structural_stop: Decimal
    technical_target: Decimal
    base_volume: Decimal
    volume_step: Decimal
    maximum_volume: Decimal
    stop_risk_per_volume_usd: Decimal
    margin_per_volume_usd: Decimal
    provider_cost_per_volume_usd: Decimal
    expected_net_value_usd: Decimal
    expected_capital_minutes: Decimal
    context_allowed: bool
    cognitive_multiplier_cap: int
    fallback_gross_r: Decimal

    def __post_init__(self) -> None:
        if not self.signal_fingerprint or not self.trader_id or not self.qore_symbol:
            raise CiboMaximumCapabilityError("frontier opportunity identity required")
        if (
            self.decision_at.tzinfo is None
            or self.entry_at.tzinfo is None
            or self.horizon_at.tzinfo is None
        ):
            raise CiboMaximumCapabilityError(
                "frontier timestamps must be timezone-aware"
            )
        if not (self.decision_at <= self.entry_at < self.horizon_at):
            raise CiboMaximumCapabilityError(
                "frontier opportunity chronology invalid"
            )
        if self.side not in {"long", "short"}:
            raise CiboMaximumCapabilityError(
                "frontier side must be long/short"
            )
        for name in (
            "entry_price",
            "structural_stop",
            "technical_target",
            "base_volume",
            "volume_step",
            "maximum_volume",
            "stop_risk_per_volume_usd",
            "margin_per_volume_usd",
            "provider_cost_per_volume_usd",
            "expected_net_value_usd",
            "expected_capital_minutes",
            "fallback_gross_r",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboMaximumCapabilityError(
                    f"{name} must be finite Decimal"
                )
        if (
            self.base_volume <= 0
            or self.volume_step <= 0
            or self.maximum_volume < self.base_volume
            or self.stop_risk_per_volume_usd <= 0
            or self.margin_per_volume_usd <= 0
            or self.provider_cost_per_volume_usd < 0
            or self.expected_capital_minutes <= 0
        ):
            raise CiboMaximumCapabilityError(
                "frontier economic geometry invalid"
            )
        if self.cognitive_multiplier_cap not in {0, 1, 2, 3, 4}:
            raise CiboMaximumCapabilityError(
                "cognitive multiplier cap must be 0..4"
            )

    @property
    def base_stop_risk_usd(self) -> Decimal:
        return self.base_volume * self.stop_risk_per_volume_usd

    @property
    def base_margin_usd(self) -> Decimal:
        return self.base_volume * self.margin_per_volume_usd

    @property
    def provider_multiplier_cap(self) -> int:
        raw = (
            self.maximum_volume / self.base_volume
        ).to_integral_value(rounding=ROUND_FLOOR)
        return max(0, min(4, int(raw)))


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    occurred_at: datetime
    action: str
    realized_r_delta: Decimal
    remaining_volume_fraction: Decimal
    risk_fraction_remaining: Decimal
    margin_fraction_remaining: Decimal

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            raise CiboMaximumCapabilityError(
                "lifecycle event time must be aware"
            )
        for name in (
            "realized_r_delta",
            "remaining_volume_fraction",
            "risk_fraction_remaining",
            "margin_fraction_remaining",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboMaximumCapabilityError(
                    f"lifecycle {name} must be finite Decimal"
                )
        if not (
            Decimal(0) <= self.remaining_volume_fraction <= Decimal(1)
        ):
            raise CiboMaximumCapabilityError(
                "remaining volume fraction invalid"
            )
        if not (
            Decimal(0) <= self.risk_fraction_remaining <= Decimal(1)
        ):
            raise CiboMaximumCapabilityError("risk fraction invalid")
        if not (
            Decimal(0) <= self.margin_fraction_remaining <= Decimal(1)
        ):
            raise CiboMaximumCapabilityError("margin fraction invalid")


@dataclass(frozen=True, slots=True)
class PositionLifecycleResult:
    signal_fingerprint: str
    data_available: bool
    gross_r: Decimal
    exit_at: datetime
    events: tuple[LifecycleEvent, ...]
    risk_released_before_exit_fraction: Decimal
    margin_released_before_exit_fraction: Decimal
    actions: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.signal_fingerprint:
            raise CiboMaximumCapabilityError(
                "lifecycle signal required"
            )
        if self.exit_at.tzinfo is None:
            raise CiboMaximumCapabilityError(
                "lifecycle exit must be aware"
            )
        for name in (
            "gross_r",
            "risk_released_before_exit_fraction",
            "margin_released_before_exit_fraction",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboMaximumCapabilityError(f"{name} invalid")
        for name in (
            "risk_released_before_exit_fraction",
            "margin_released_before_exit_fraction",
        ):
            value = getattr(self, name)
            if not (Decimal(0) <= value <= Decimal(1)):
                raise CiboMaximumCapabilityError(
                    f"{name} outside [0,1]"
                )


@dataclass(frozen=True, slots=True)
class EpochOption:
    signal_fingerprint: str
    multiplier_cap: int
    expected_net_value_usd: Decimal
    expected_capital_minutes: Decimal
    risk_per_multiplier_usd: Decimal
    margin_per_multiplier_usd: Decimal

    def __post_init__(self) -> None:
        if self.multiplier_cap not in {0, 1, 2, 3, 4}:
            raise CiboMaximumCapabilityError(
                "epoch multiplier cap invalid"
            )
        if self.expected_capital_minutes <= 0:
            raise CiboMaximumCapabilityError(
                "epoch expected minutes invalid"
            )
        if (
            self.risk_per_multiplier_usd <= 0
            or self.margin_per_multiplier_usd <= 0
        ):
            raise CiboMaximumCapabilityError(
                "epoch capacity geometry invalid"
            )


def cognitive_multiplier_cap(
    cognitive_orchestration: Mapping[str, object],
) -> tuple[int, tuple[str, ...], str]:
    """Turn the CF predecision surface into a capital-intensity ceiling.

    The function consumes only CF input/status information. It never reads
    realized P/L or later market path.
    """

    raw_receipts = cognitive_orchestration.get("faculty_receipts")
    if not isinstance(raw_receipts, list) or len(raw_receipts) != 19:
        return 0, (), "CF01-CF19 consultation incomplete"
    by_code: dict[str, Mapping[str, object]] = {}
    for raw in raw_receipts:
        if not isinstance(raw, Mapping):
            return 0, (), "invalid cognitive receipt"
        code = str(raw.get("function_code", ""))
        output = raw.get("output_payload")
        if not isinstance(output, Mapping):
            return 0, (), "cognitive output missing"
        status = str(output.get("native_engine_status", ""))
        if status not in {"SUCCESS", "JUSTIFIED_NOT_APPLICABLE"}:
            return 0, (), f"{code} native status not usable"
        by_code[code] = raw
    expected_codes = tuple(f"CF{index:02d}" for index in range(1, 20))
    if tuple(sorted(by_code)) != expected_codes:
        return 0, (), "CF01-CF19 identity surface incomplete"

    consumed = ("CF02", "CF06", "CF07", "CF10", "CF12")
    for code in consumed:
        if code not in by_code:
            return 0, (), f"{code} missing from economic synthesis"

    def input_payload(code: str) -> Mapping[str, object]:
        payload = by_code[code].get("input_payload")
        if not isinstance(payload, Mapping):
            raise CiboMaximumCapabilityError(
                f"{code} input payload missing"
            )
        return payload

    cf02 = input_payload("CF02")
    cf06 = input_payload("CF06")
    cf07 = input_payload("CF07")
    cf10 = input_payload("CF10")
    cf12 = input_payload("CF12")

    regime = cf02.get("regime")
    if not isinstance(regime, Mapping):
        raise CiboMaximumCapabilityError("CF02 regime missing")
    utilization = cf10.get("utilization")
    if not isinstance(utilization, Mapping):
        raise CiboMaximumCapabilityError(
            "CF10 utilization missing"
        )
    if (
        cf06.get("utilization") != utilization
        or cf12.get("utilization") != utilization
    ):
        raise CiboMaximumCapabilityError(
            "cognitive utilization surfaces disagree"
        )
    if cf07.get("provider_condition") != regime.get(
        "provider_condition"
    ):
        raise CiboMaximumCapabilityError(
            "cognitive provider condition drift"
        )

    values = tuple(
        Decimal(str(utilization.get(name, "1")))
        for name in (
            "risk_utilization",
            "margin_utilization",
            "drawdown_utilization",
        )
    )
    if any(
        not value.is_finite()
        or value < 0
        or value > 1
        for value in values
    ):
        raise CiboMaximumCapabilityError(
            "cognitive utilization outside [0,1]"
        )
    max_util = max(values)
    if max_util >= Decimal("0.75"):
        utilization_cap = 1
    elif max_util >= Decimal("0.50"):
        utilization_cap = 2
    elif max_util >= Decimal("0.25"):
        utilization_cap = 3
    else:
        utilization_cap = 4

    liquidity = str(regime.get("liquidity", "STRESSED"))
    volatility = str(regime.get("volatility", "DISLOCATED"))
    correlation = str(regime.get("correlation", "BREAK"))
    provider = str(
        regime.get("provider_condition", "UNAVAILABLE")
    )
    regime_cap = 4
    if (
        provider == "UNAVAILABLE"
        or volatility == "DISLOCATED"
        or correlation == "BREAK"
    ):
        regime_cap = 1
    elif provider == "DEGRADED" or liquidity == "STRESSED":
        regime_cap = 2
    elif (
        liquidity == "THIN"
        or volatility == "ELEVATED"
        or correlation == "CONCENTRATED"
    ):
        regime_cap = 3

    opportunity_count = int(cf06.get("opportunity_count", 0))
    competition_cap = 3 if opportunity_count >= 3 else 4
    cap = min(utilization_cap, regime_cap, competition_cap)
    return (
        cap,
        consumed,
        (
            f"cognitive cap={cap}; "
            f"utilization={utilization_cap}; "
            f"regime={regime_cap}; "
            f"competition={competition_cap}"
        ),
    )


def optimize_epoch_multipliers(
    options: Sequence[EpochOption],
    *,
    risk_headroom_usd: Decimal,
    margin_headroom_usd: Decimal,
    fixed_multiplier: int | None = None,
    portfolio_competition: bool = True,
) -> tuple[int, ...]:
    """Solve the causal per-epoch discrete 0x..4x allocation surface."""

    if risk_headroom_usd < 0 or margin_headroom_usd < 0:
        raise CiboMaximumCapabilityError(
            "negative frontier headroom"
        )
    if (
        fixed_multiplier is not None
        and fixed_multiplier not in {1, 2, 3, 4}
    ):
        raise CiboMaximumCapabilityError(
            "fixed frontier multiplier must be 1..4"
        )
    if not options:
        return ()

    ranges: list[range] = []
    for item in options:
        cap = item.multiplier_cap
        if item.expected_net_value_usd <= 0:
            cap = 0
        if fixed_multiplier is not None:
            cap = min(cap, fixed_multiplier)
            ranges.append(
                range(cap, cap + 1) if cap > 0 else range(1)
            )
        else:
            ranges.append(range(cap + 1))

    if not portfolio_competition:
        result = []
        remaining_risk = risk_headroom_usd
        remaining_margin = margin_headroom_usd
        for item, choices in zip(
            options, ranges, strict=True
        ):
            cap = max(choices)
            chosen = 0
            for value in range(cap, -1, -1):
                risk = (
                    item.risk_per_multiplier_usd * value
                )
                margin = (
                    item.margin_per_multiplier_usd * value
                )
                if (
                    risk <= remaining_risk
                    and margin <= remaining_margin
                ):
                    chosen = value
                    break
            result.append(chosen)
            remaining_risk -= (
                item.risk_per_multiplier_usd * chosen
            )
            remaining_margin -= (
                item.margin_per_multiplier_usd * chosen
            )
        return tuple(result)

    best: tuple[
        Decimal,
        Decimal,
        Decimal,
        Decimal,
        tuple[int, ...],
    ] | None = None
    for combo in product(*ranges):
        risk = sum(
            (
                item.risk_per_multiplier_usd * mult
                for item, mult in zip(
                    options, combo, strict=True
                )
            ),
            Decimal(0),
        )
        margin = sum(
            (
                item.margin_per_multiplier_usd * mult
                for item, mult in zip(
                    options, combo, strict=True
                )
            ),
            Decimal(0),
        )
        if (
            risk > risk_headroom_usd
            or margin > margin_headroom_usd
        ):
            continue
        velocity_utility = sum(
            (
                item.expected_net_value_usd
                * mult
                / item.expected_capital_minutes
                for item, mult in zip(
                    options, combo, strict=True
                )
            ),
            Decimal(0),
        )
        expected_value = sum(
            (
                item.expected_net_value_usd * mult
                for item, mult in zip(
                    options, combo, strict=True
                )
            ),
            Decimal(0),
        )
        key = (
            velocity_utility,
            expected_value,
            -risk,
            -margin,
            tuple(-value for value in combo),
        )
        if best is None or key > best:
            best = key
    if best is None:
        return tuple(0 for _ in options)
    return tuple(-value for value in best[4])


def optimize_epoch_from_economic_twin(
    twin: CiboObservedEconomicTwin,
    *,
    fixed_multiplier: int | None = None,
    portfolio_competition: bool = True,
) -> tuple[tuple[str, int], ...]:
    """Optimize the current causal opportunity surface from the canonical Twin.

    This is a research frontier consumer only.  It does not mutate the Twin,
    authorize capital, bypass QORE Risk or use realized future outcomes.
    """

    if not isinstance(twin, CiboObservedEconomicTwin):
        raise CiboMaximumCapabilityError(
            "frontier requires canonical Full Economic Twin"
        )
    constraints = observed_twin_constraints(twin)
    cognitive = dict(twin.cognitive_constraints)
    raw_cap = cognitive.get("capital_intensity_cap", "4")
    try:
        cognitive_cap = int(raw_cap)
    except (TypeError, ValueError) as error:
        raise CiboMaximumCapabilityError(
            "Full Economic Twin capital_intensity_cap must be integer 0..4"
        ) from error
    if cognitive_cap not in {0, 1, 2, 3, 4}:
        raise CiboMaximumCapabilityError(
            "Full Economic Twin capital_intensity_cap outside 0..4"
        )

    options: list[EpochOption] = []
    ordered = tuple(
        sorted(
            twin.opportunities,
            key=lambda item: (
                item.earliest_action_at,
                item.option_id,
            ),
        )
    )
    for item in ordered:
        eligible = (
            item.known_at <= twin.captured_at
            and item.earliest_action_at <= twin.captured_at
            and item.expires_at > twin.captured_at
            and item.context_allowed
            and item.provider_viable
            and item.capital_source_eligible
        )
        cap = min(item.maximum_multiplier, cognitive_cap) if eligible else 0
        # Uncertainty is an ex-ante penalty, not an outcome filter.
        net_value = (
            item.expected_net_value_usd
            - item.provider_cost_usd
            - item.uncertainty_penalty
        )
        options.append(
            EpochOption(
                signal_fingerprint=item.option_id,
                multiplier_cap=cap,
                expected_net_value_usd=net_value,
                expected_capital_minutes=item.expected_capital_minutes,
                risk_per_multiplier_usd=item.stop_risk_usd,
                margin_per_multiplier_usd=item.margin_usd,
            )
        )

    multipliers = optimize_epoch_multipliers(
        tuple(options),
        risk_headroom_usd=constraints["stop_risk_headroom_usd"],
        margin_headroom_usd=constraints["margin_headroom_usd"],
        fixed_multiplier=fixed_multiplier,
        portfolio_competition=portfolio_competition,
    )
    return tuple(
        (item.option_id, multiplier)
        for item, multiplier in zip(ordered, multipliers, strict=True)
    )


def simulate_position_lifecycle(
    opportunity: CausalFrontierOpportunity,
    bars: Sequence[Bar],
    *,
    features: frozenset[
        LifecycleFeature
    ] = FULL_LIFECYCLE_FEATURES,
) -> PositionLifecycleResult:
    """Apply causal closed-bar lifecycle rules inside the original horizon.

    The original settlement timestamp is the evaluation horizon.  Lifecycle
    state derived from bar N becomes executable protection only from bar N+1.
    When lifecycle is disabled, or when the remaining position reaches the
    original horizon, the original structural settlement is reused exactly
    instead of synthesizing a mark-to-market outcome.
    """

    risk_distance = abs(
        opportunity.entry_price
        - opportunity.structural_stop
    )
    if risk_distance <= 0:
        raise CiboMaximumCapabilityError(
            "position lifecycle requires nonzero stop distance"
        )
    target_r = (
        abs(
            opportunity.technical_target
            - opportunity.entry_price
        )
        / risk_distance
    )
    cost_r = (
        opportunity.provider_cost_per_volume_usd
        / opportunity.stop_risk_per_volume_usd
    )

    causal_bars = tuple(
        bar
        for bar in bars
        if (
            bar.opened_at >= opportunity.entry_at
            and bar.closed_at <= opportunity.horizon_at
        )
    )

    def original_settlement(
        *,
        data_available: bool,
        action: str,
    ) -> PositionLifecycleResult:
        close = LifecycleEvent(
            occurred_at=opportunity.horizon_at,
            action=action,
            realized_r_delta=opportunity.fallback_gross_r,
            remaining_volume_fraction=Decimal(0),
            risk_fraction_remaining=Decimal(0),
            margin_fraction_remaining=Decimal(0),
        )
        return PositionLifecycleResult(
            signal_fingerprint=opportunity.signal_fingerprint,
            data_available=data_available,
            gross_r=opportunity.fallback_gross_r,
            exit_at=opportunity.horizon_at,
            events=(close,),
            risk_released_before_exit_fraction=Decimal(0),
            margin_released_before_exit_fraction=Decimal(0),
            actions=(close.action,),
        )

    if not causal_bars:
        return original_settlement(
            data_available=False,
            action="FALLBACK_ORIGINAL_SETTLEMENT",
        )

    # Settlement identity is a hard invariant.  Turning lifecycle off must
    # reproduce the original outcome exactly, irrespective of M5 geometry.
    if not features:
        return original_settlement(
            data_available=True,
            action="LIFECYCLE_OFF_ORIGINAL_SETTLEMENT",
        )

    remaining = Decimal(1)
    # -1R is the original structural stop.  It is not re-simulated as a new
    # lifecycle decision; the original settlement remains authoritative at
    # horizon.  Only a protection stricter than the original stop can create
    # an earlier lifecycle exit.
    stop_r = Decimal(-1)
    partial_done = False
    be_done = False
    lock_done = False
    trail_active = False
    realized_r = Decimal(0)
    events: list[LifecycleEvent] = []
    risk_fraction = Decimal(1)
    margin_fraction = Decimal(1)

    def favorable_and_adverse(
        bar: Bar,
    ) -> tuple[Decimal, Decimal, Decimal]:
        if opportunity.side == "long":
            favorable = (
                bar.high - opportunity.entry_price
            ) / risk_distance
            adverse = (
                bar.low - opportunity.entry_price
            ) / risk_distance
            close_r = (
                bar.close - opportunity.entry_price
            ) / risk_distance
        else:
            favorable = (
                opportunity.entry_price - bar.low
            ) / risk_distance
            adverse = (
                opportunity.entry_price - bar.high
            ) / risk_distance
            close_r = (
                opportunity.entry_price - bar.close
            ) / risk_distance
        return favorable, adverse, close_r

    def append_event(
        at: datetime,
        action: str,
        realized_delta: Decimal = Decimal(0),
        *,
        force_close: bool = False,
    ) -> None:
        nonlocal realized_r
        nonlocal risk_fraction
        nonlocal margin_fraction
        realized_r += realized_delta
        next_margin = (
            Decimal(0) if force_close else remaining
        )
        next_risk = (
            Decimal(0)
            if force_close
            else remaining * max(Decimal(0), -stop_r)
        )
        risk_fraction = min(risk_fraction, next_risk)
        margin_fraction = min(
            margin_fraction, next_margin
        )
        events.append(
            LifecycleEvent(
                occurred_at=at,
                action=action,
                realized_r_delta=realized_delta,
                remaining_volume_fraction=(
                    Decimal(0)
                    if force_close
                    else remaining
                ),
                risk_fraction_remaining=risk_fraction,
                margin_fraction_remaining=margin_fraction,
            )
        )

    for bar in causal_bars:
        favorable, adverse, _close_r = favorable_and_adverse(bar)

        # Only protection that existed at BAR N START may stop the position
        # inside BAR N.  A protection first derived from this bar cannot be
        # compared retroactively against this bar's LOW/HIGH.
        active_stop_r = stop_r
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

        # Partial realization is an action at the closed-bar decision clock.
        if (
            LifecycleFeature.PARTIAL_REALIZATION
            in features
            and not partial_done
            and favorable >= Decimal(1)
            and target_r > Decimal(1)
            and bar.closed_at < opportunity.horizon_at
        ):
            close_fraction = min(
                Decimal("0.25"), remaining
            )
            remaining -= close_fraction
            partial_done = True
            append_event(
                bar.closed_at,
                "PARTIAL_REALIZATION_1R",
                close_fraction,
            )

        # Build the next-bar protection from information frozen at BAR N
        # close.  Do not evaluate the new stop against BAR N extremes.
        next_stop_r = stop_r
        actions_at_close: list[tuple[str, Decimal]] = []

        if (
            LifecycleFeature.BREAKEVEN in features
            and not be_done
            and favorable >= Decimal(1)
            and bar.closed_at < opportunity.horizon_at
        ):
            proposed = max(next_stop_r, cost_r)
            if proposed > next_stop_r:
                next_stop_r = proposed
                actions_at_close.append(
                    ("MOVE_TO_BREAKEVEN", next_stop_r)
                )
            be_done = True

        if (
            LifecycleFeature.PROFIT_LOCK in features
            and not lock_done
            and favorable >= Decimal("1.5")
            and bar.closed_at < opportunity.horizon_at
        ):
            proposed = max(
                next_stop_r, Decimal("0.5")
            )
            if proposed > next_stop_r:
                next_stop_r = proposed
                actions_at_close.append(
                    ("PROFIT_LOCK", next_stop_r)
                )
            lock_done = True

        if (
            LifecycleFeature.TRAILING in features
            and favorable >= Decimal(2)
            and bar.closed_at < opportunity.horizon_at
        ):
            proposed = max(
                next_stop_r, favorable - Decimal(1)
            )
            if proposed > next_stop_r:
                next_stop_r = proposed
                actions_at_close.append(
                    ("TRAIL_STOP", next_stop_r)
                )
            trail_active = True

        # EXTENDED_TARGET cannot be truthfully executed from this M5-only
        # surface because horizon_at is the original settlement time and no
        # post-horizon path is supplied.  The feature therefore remains
        # available but intentionally makes no fabricated same-bar extension.
        # A future universal lifecycle engine may actuate it only with
        # pre-target evidence plus real post-horizon path coverage.

        if actions_at_close:
            stop_r = next_stop_r
            for action, _new_stop in actions_at_close:
                append_event(
                    bar.closed_at,
                    action,
                )

    if remaining > 0:
        # Preserve the exact original settlement for the still-open fraction.
        # Outcome is consumed only now, after all lifecycle decisions in the
        # original trade horizon have been frozen.
        delta = remaining * opportunity.fallback_gross_r
        remaining = Decimal(0)
        append_event(
            opportunity.horizon_at,
            "HORIZON_ORIGINAL_SETTLEMENT",
            delta,
            force_close=True,
        )

    return PositionLifecycleResult(
        signal_fingerprint=opportunity.signal_fingerprint,
        data_available=True,
        gross_r=realized_r,
        exit_at=events[-1].occurred_at,
        events=tuple(events),
        risk_released_before_exit_fraction=max(
            Decimal(0),
            max(
                (
                    Decimal(1)
                    - item.risk_fraction_remaining
                    for item in events[:-1]
                ),
                default=Decimal(0),
            ),
        ),
        margin_released_before_exit_fraction=max(
            Decimal(0),
            max(
                (
                    Decimal(1)
                    - item.margin_fraction_remaining
                    for item in events[:-1]
                ),
                default=Decimal(0),
            ),
        ),
        actions=tuple(
            item.action for item in events
        ),
    )
