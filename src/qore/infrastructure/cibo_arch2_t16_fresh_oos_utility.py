"""Frozen Architect-2 T16 fresh-OOS hedge-utility protocol.

The provider hedge universe was pre-registered earlier.  This protocol fixes the
economic test before its utility population is consumed.  It treats the existing
post-declaration 48-observation pair study as calibration/structure evidence only,
never as fresh-OOS utility.

A candidate passes only if every contiguous fold shows strictly positive net
downside-protection after charging one conservative observed round-trip hedge
cost per fold.  No pooled rescue and no universe expansion are permitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

PROTOCOL_ID = "CIBO_ARCH2_T16_FRESH_OOS_HEDGE_UTILITY_V1"
FROZEN_AT = datetime(2026, 10, 1, 22, 20, tzinfo=UTC)
CALIBRATION_RUN_ID = 36817089026
CALIBRATION_ARTIFACT_ID = 11141752922
CALIBRATION_ARTIFACT_DIGEST = (
    "sha256:2c49af854547486de58c358289a7e2db5f8128be4421ad58eb04a0cd06ce90a8"
)
MINIMUM_OOS_OBSERVATIONS = 32
REQUIRED_FOLDS = 4

# Fixed from the already-sealed structural calibration artifact.  Both
# pre-registered candidates remain eligible; neither is selected by this file.
FROZEN_HEDGE_BETA = (
    ("US30", Decimal("0.9870327967452153507332036422")),
    ("US500", Decimal("2.124695637073923294021473707")),
)


@dataclass(frozen=True, slots=True)
class T16UtilityObservation:
    market_at: datetime
    target_return: Decimal
    hedge_return: Decimal

    def __post_init__(self) -> None:
        if self.market_at.tzinfo is None or self.market_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "T16 utility observation market_at must be timezone-aware"
            )
        if self.market_at <= FROZEN_AT:
            raise CiboCapitalManagementError(
                "T16 fresh-OOS observation must postdate frozen utility protocol"
            )
        for name in ("target_return", "hedge_return"):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"T16 utility {name} must be finite Decimal"
                )


@dataclass(frozen=True, slots=True)
class T16UtilityFoldResult:
    fold_index: int
    observations: int
    control_downside_semideviation: Decimal
    hedged_downside_semideviation: Decimal
    conservative_round_trip_cost_fraction: Decimal
    net_protection_fraction: Decimal
    pass_gate: bool


@dataclass(frozen=True, slots=True)
class T16FreshOOSUtilityResult:
    hedge_symbol: str
    hedge_beta: Decimal
    observation_count: int
    fold_results: tuple[T16UtilityFoldResult, ...]
    four_of_four_pass: bool
    net_economic_benefit_proven: bool
    fresh_oos_utility_proven: bool
    t16_candidate_pass: bool
    productive_authority: bool = False


def evaluate_t16_fresh_oos_utility(
    *,
    hedge_symbol: str,
    observations: tuple[T16UtilityObservation, ...],
    conservative_round_trip_cost_bps: Decimal,
) -> T16FreshOOSUtilityResult:
    beta = dict(FROZEN_HEDGE_BETA).get(hedge_symbol)
    if beta is None:
        raise CiboCapitalManagementError(
            "T16 utility candidate outside pre-registered frozen universe"
        )
    if (
        not isinstance(conservative_round_trip_cost_bps, Decimal)
        or not conservative_round_trip_cost_bps.is_finite()
        or conservative_round_trip_cost_bps < 0
    ):
        raise CiboCapitalManagementError(
            "T16 utility round-trip cost must be finite non-negative Decimal"
        )
    if len(observations) < MINIMUM_OOS_OBSERVATIONS:
        raise CiboCapitalManagementError(
            "T16 utility fresh-OOS minimum observation count not met"
        )
    ordered = tuple(sorted(observations, key=lambda item: item.market_at))
    if len({item.market_at for item in ordered}) != len(ordered):
        raise CiboCapitalManagementError(
            "T16 utility fresh-OOS timestamps must be unique"
        )
    folds = _folds(ordered)
    if len(folds) != REQUIRED_FOLDS:
        raise CiboCapitalManagementError(
            "T16 utility exact four-fold partition required"
        )
    cost_fraction = conservative_round_trip_cost_bps / Decimal("10000")
    results: list[T16UtilityFoldResult] = []
    for index, fold in enumerate(folds, start=1):
        control = tuple(item.target_return for item in fold)
        treatment = tuple(
            item.target_return - beta * item.hedge_return
            for item in fold
        )
        control_downside = _downside_semideviation(control)
        hedged_downside = _downside_semideviation(treatment)
        net_protection = control_downside - hedged_downside - cost_fraction
        passed = net_protection > 0
        results.append(
            T16UtilityFoldResult(
                fold_index=index,
                observations=len(fold),
                control_downside_semideviation=control_downside,
                hedged_downside_semideviation=hedged_downside,
                conservative_round_trip_cost_fraction=cost_fraction,
                net_protection_fraction=net_protection,
                pass_gate=passed,
            )
        )
    four = all(item.pass_gate for item in results)
    return T16FreshOOSUtilityResult(
        hedge_symbol=hedge_symbol,
        hedge_beta=beta,
        observation_count=len(ordered),
        fold_results=tuple(results),
        four_of_four_pass=four,
        net_economic_benefit_proven=four,
        fresh_oos_utility_proven=four,
        t16_candidate_pass=four,
        productive_authority=False,
    )


def _folds(
    observations: tuple[T16UtilityObservation, ...],
) -> tuple[tuple[T16UtilityObservation, ...], ...]:
    base = len(observations) // REQUIRED_FOLDS
    extra = len(observations) % REQUIRED_FOLDS
    rows: list[tuple[T16UtilityObservation, ...]] = []
    cursor = 0
    for index in range(REQUIRED_FOLDS):
        size = base + (1 if index < extra else 0)
        rows.append(observations[cursor : cursor + size])
        cursor += size
    return tuple(rows)


def _downside_semideviation(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError(
            "T16 utility downside requires observations"
        )
    downside = tuple(min(Decimal(0), item) for item in values)
    return (
        sum((item * item for item in downside), Decimal(0))
        / Decimal(len(downside))
    ).sqrt()
