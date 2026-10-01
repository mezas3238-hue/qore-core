"""Frozen evaluator for Architect-2 T11 provider-bound market impact.

The experiment compares matched minimum-volume micro-bundles:
- level 1: one provider-minimum child order;
- level 2: two provider-minimum child orders.

The observed metric is the realized round-trip settlement cost in the cTrader
DEMO account's USD deposit asset. Calibration identifies C(v)=a*v+b*v^2 from
the two frozen levels. Fresh validation is split into four explicit temporal
folds. The quadratic model is admitted only when it is no worse than the
linear-only model in every fold.

Level order must alternate across matched pairs (L1->L2, then L2->L1, ...).
This removes a systematic first/second execution bias. A validated b=0 remains
valid evidence: nonlinear impact must never be invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
    MARKET_IMPACT_AGGREGATE_CHILD_COUNTS,
    MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    MARKET_IMPACT_REQUIRED_TEMPORAL_FOLDS,
    MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    REQUIRED_SYMBOLS,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_CALIBRATION = "CALIBRATION"
_VALIDATION = "VALIDATION"


@dataclass(frozen=True, slots=True)
class T11MarketImpactEpisode:
    evidence_id: str
    qore_symbol: str
    pair_id: str
    phase: str
    fold_index: int
    side: str
    child_count: int
    level_order_position: int
    minimum_volume: Decimal
    aggregate_volume: Decimal
    realized_settlement_cost_total_usd: Decimal
    deposit_asset: str
    observed_at: datetime
    provider_bound: bool
    every_child_order_minimum_volume: bool
    holdout_outcomes_used: bool = False
    target_aware: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.pair_id:
            raise CiboCapitalManagementError(
                "T11 market-impact episode identity required"
            )
        if self.qore_symbol not in REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "T11 market-impact symbol outside frozen universe"
            )
        if self.phase not in {_CALIBRATION, _VALIDATION}:
            raise CiboCapitalManagementError(
                "T11 market-impact episode phase invalid"
            )
        if self.phase == _CALIBRATION and self.fold_index != 0:
            raise CiboCapitalManagementError(
                "T11 calibration episode fold index must be zero"
            )
        if self.phase == _VALIDATION and self.fold_index not in range(
            1, MARKET_IMPACT_REQUIRED_TEMPORAL_FOLDS + 1
        ):
            raise CiboCapitalManagementError(
                "T11 validation episode fold index invalid"
            )
        if self.side not in {"long", "short"}:
            raise CiboCapitalManagementError(
                "T11 market-impact side invalid"
            )
        if self.child_count not in MARKET_IMPACT_AGGREGATE_CHILD_COUNTS:
            raise CiboCapitalManagementError(
                "T11 market-impact child count outside frozen levels"
            )
        if self.level_order_position not in {1, 2}:
            raise CiboCapitalManagementError(
                "T11 market-impact level-order position must be 1 or 2"
            )
        for name in ("minimum_volume", "aggregate_volume"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value <= 0
            ):
                raise CiboCapitalManagementError(
                    f"T11 market-impact {name} must be positive finite Decimal"
                )
        if self.aggregate_volume != self.minimum_volume * self.child_count:
            raise CiboCapitalManagementError(
                "T11 market-impact aggregate volume/child identity drift"
            )
        if (
            not isinstance(self.realized_settlement_cost_total_usd, Decimal)
            or not self.realized_settlement_cost_total_usd.is_finite()
            or self.realized_settlement_cost_total_usd < 0
        ):
            raise CiboCapitalManagementError(
                "T11 market-impact realized settlement cost invalid"
            )
        if self.deposit_asset != "USD":
            raise CiboCapitalManagementError(
                "T11 market-impact deposit asset must be USD"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "T11 market-impact observed_at must be timezone-aware"
            )
        if self.observed_at <= FROZEN_AT:
            raise CiboCapitalManagementError(
                "T11 market-impact observation must postdate freeze"
            )
        if not self.provider_bound or not self.every_child_order_minimum_volume:
            raise CiboCapitalManagementError(
                "T11 market-impact provider/minimum-volume binding required"
            )
        if self.holdout_outcomes_used or self.target_aware or self.productive_authority:
            raise CiboCapitalManagementError(
                "T11 market-impact governance contamination"
            )


@dataclass(frozen=True, slots=True)
class T11MarketImpactFoldResult:
    fold_index: int
    quadratic_mae_usd: Decimal
    linear_only_mae_usd: Decimal
    quadratic_nonworse: bool


@dataclass(frozen=True, slots=True)
class T11MarketImpactSymbolResult:
    qore_symbol: str
    minimum_volume: Decimal
    linear_cost_per_volume_usd: Decimal
    impact_cost_per_volume_squared_usd: Decimal
    calibration_pairs: int
    validation_pairs: int
    fold_results: tuple[T11MarketImpactFoldResult, ...]
    four_of_four_validated: bool
    calibrated: bool
    fresh_oos_validated: bool

    def __post_init__(self) -> None:
        if self.qore_symbol not in REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "T11 market-impact result symbol drift"
            )
        if self.minimum_volume <= 0:
            raise CiboCapitalManagementError(
                "T11 market-impact result minimum volume invalid"
            )
        for name in (
            "linear_cost_per_volume_usd",
            "impact_cost_per_volume_squared_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise CiboCapitalManagementError(
                    f"T11 market-impact result {name} invalid"
                )
        if self.calibration_pairs != (
            MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL
        ):
            raise CiboCapitalManagementError(
                "T11 market-impact calibration pair count drift"
            )
        if self.validation_pairs != (
            MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL
        ):
            raise CiboCapitalManagementError(
                "T11 market-impact validation pair count drift"
            )
        if tuple(item.fold_index for item in self.fold_results) != (1, 2, 3, 4):
            raise CiboCapitalManagementError(
                "T11 market-impact exact validation folds required"
            )
        expected = all(item.quadratic_nonworse for item in self.fold_results)
        if self.four_of_four_validated != expected:
            raise CiboCapitalManagementError(
                "T11 market-impact four-fold result drift"
            )
        if self.calibrated is not True:
            raise CiboCapitalManagementError(
                "T11 market-impact result must be calibrated"
            )
        if self.fresh_oos_validated != expected:
            raise CiboCapitalManagementError(
                "T11 market-impact fresh-OOS validation drift"
            )


@dataclass(frozen=True, slots=True)
class T11MarketImpactEvaluation:
    symbols: tuple[T11MarketImpactSymbolResult, ...]
    required_symbol_coverage_complete: bool
    market_impact_model_ready: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        names = tuple(item.qore_symbol for item in self.symbols)
        if names != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError(
                "T11 market-impact evaluation exact symbol surface required"
            )
        if not self.required_symbol_coverage_complete:
            raise CiboCapitalManagementError(
                "T11 market-impact evaluation incomplete symbol coverage"
            )
        expected = all(item.fresh_oos_validated for item in self.symbols)
        if self.market_impact_model_ready != expected:
            raise CiboCapitalManagementError(
                "T11 market-impact readiness drift"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "T11 market-impact evaluation grants no authority"
            )


def evaluate_t11_market_impact(
    episodes: tuple[T11MarketImpactEpisode, ...],
) -> T11MarketImpactEvaluation:
    if not episodes:
        raise CiboCapitalManagementError(
            "T11 market-impact episode population required"
        )
    ids = tuple(item.evidence_id for item in episodes)
    if len(ids) != len(set(ids)):
        raise CiboCapitalManagementError(
            "T11 market-impact evidence ids must be unique"
        )

    results = tuple(
        _evaluate_symbol(
            symbol=symbol,
            episodes=tuple(item for item in episodes if item.qore_symbol == symbol),
        )
        for symbol in REQUIRED_SYMBOLS
    )
    return T11MarketImpactEvaluation(
        symbols=results,
        required_symbol_coverage_complete=True,
        market_impact_model_ready=all(
            item.fresh_oos_validated for item in results
        ),
        productive_authority=False,
    )


def _evaluate_symbol(
    *,
    symbol: str,
    episodes: tuple[T11MarketImpactEpisode, ...],
) -> T11MarketImpactSymbolResult:
    if not episodes:
        raise CiboCapitalManagementError(
            f"T11 market-impact symbol population missing: {symbol}"
        )
    minimums = {item.minimum_volume for item in episodes}
    if len(minimums) != 1:
        raise CiboCapitalManagementError(
            "T11 market-impact minimum volume drift inside symbol"
        )
    minimum_volume = next(iter(minimums))

    calibration = tuple(item for item in episodes if item.phase == _CALIBRATION)
    validation = tuple(item for item in episodes if item.phase == _VALIDATION)
    calibration_pairs = _paired(
        calibration,
        expected_pairs=MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
        label=f"{symbol}:calibration",
    )
    validation_pairs = _paired(
        validation,
        expected_pairs=MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
        label=f"{symbol}:validation",
    )

    _validate_balanced_sides(calibration_pairs, f"{symbol}:calibration")
    _validate_balanced_sides(validation_pairs, f"{symbol}:validation")
    _validate_alternating_level_order(calibration_pairs, f"{symbol}:calibration")
    _validate_alternating_level_order(validation_pairs, f"{symbol}:validation")

    level1 = tuple(
        pair[0].realized_settlement_cost_total_usd
        for pair in calibration_pairs
    )
    level2 = tuple(
        pair[1].realized_settlement_cost_total_usd
        for pair in calibration_pairs
    )
    mean1 = _mean(level1)
    mean2 = _mean(level2)
    m = minimum_volume
    impact = max(
        Decimal(0),
        (mean2 - Decimal(2) * mean1) / (Decimal(2) * m * m),
    )
    linear = max(Decimal(0), (mean1 - impact * m * m) / m)
    linear_only = mean1 / m

    fold_results: list[T11MarketImpactFoldResult] = []
    by_fold: dict[
        int,
        list[tuple[T11MarketImpactEpisode, T11MarketImpactEpisode]],
    ] = {fold: [] for fold in range(1, 5)}
    for pair in validation_pairs:
        by_fold[pair[0].fold_index].append(pair)
    if any(len(rows) != 1 for rows in by_fold.values()):
        raise CiboCapitalManagementError(
            "T11 market-impact validation requires one matched pair per fold"
        )

    for fold in range(1, 5):
        pair = by_fold[fold][0]
        errors_quad: list[Decimal] = []
        errors_linear: list[Decimal] = []
        for item in pair:
            v = item.aggregate_volume
            observed = item.realized_settlement_cost_total_usd
            predicted_quad = linear * v + impact * v * v
            predicted_linear = linear_only * v
            errors_quad.append(abs(observed - predicted_quad))
            errors_linear.append(abs(observed - predicted_linear))
        quad_mae = _mean(tuple(errors_quad))
        linear_mae = _mean(tuple(errors_linear))
        fold_results.append(
            T11MarketImpactFoldResult(
                fold_index=fold,
                quadratic_mae_usd=quad_mae,
                linear_only_mae_usd=linear_mae,
                quadratic_nonworse=quad_mae <= linear_mae,
            )
        )

    four = all(item.quadratic_nonworse for item in fold_results)
    return T11MarketImpactSymbolResult(
        qore_symbol=symbol,
        minimum_volume=minimum_volume,
        linear_cost_per_volume_usd=linear,
        impact_cost_per_volume_squared_usd=impact,
        calibration_pairs=len(calibration_pairs),
        validation_pairs=len(validation_pairs),
        fold_results=tuple(fold_results),
        four_of_four_validated=four,
        calibrated=True,
        fresh_oos_validated=four,
    )


def _paired(
    episodes: tuple[T11MarketImpactEpisode, ...],
    *,
    expected_pairs: int,
    label: str,
) -> tuple[tuple[T11MarketImpactEpisode, T11MarketImpactEpisode], ...]:
    by_pair: dict[str, list[T11MarketImpactEpisode]] = {}
    for item in episodes:
        by_pair.setdefault(item.pair_id, []).append(item)
    if len(by_pair) != expected_pairs:
        raise CiboCapitalManagementError(
            f"T11 market-impact {label} pair count mismatch"
        )
    pairs: list[tuple[T11MarketImpactEpisode, T11MarketImpactEpisode]] = []
    for pair_id in sorted(by_pair):
        rows = tuple(sorted(by_pair[pair_id], key=lambda item: item.child_count))
        if len(rows) != 2 or tuple(item.child_count for item in rows) != (1, 2):
            raise CiboCapitalManagementError(
                f"T11 market-impact {label} pair level surface invalid"
            )
        if (
            rows[0].side != rows[1].side
            or rows[0].fold_index != rows[1].fold_index
            or rows[0].minimum_volume != rows[1].minimum_volume
            or rows[0].deposit_asset != rows[1].deposit_asset
            or {rows[0].level_order_position, rows[1].level_order_position}
            != {1, 2}
        ):
            raise CiboCapitalManagementError(
                f"T11 market-impact {label} matched-pair identity drift"
            )
        pairs.append((rows[0], rows[1]))
    return tuple(pairs)


def _validate_balanced_sides(
    pairs: tuple[tuple[T11MarketImpactEpisode, T11MarketImpactEpisode], ...],
    label: str,
) -> None:
    sides = tuple(pair[0].side for pair in pairs)
    if sides.count("long") != len(pairs) // 2 or sides.count("short") != (
        len(pairs) // 2
    ):
        raise CiboCapitalManagementError(
            f"T11 market-impact {label} sides must be balanced"
        )


def _validate_alternating_level_order(
    pairs: tuple[tuple[T11MarketImpactEpisode, T11MarketImpactEpisode], ...],
    label: str,
) -> None:
    for index, pair in enumerate(pairs):
        first_level = next(
            item.child_count for item in pair if item.level_order_position == 1
        )
        second_level = next(
            item.child_count for item in pair if item.level_order_position == 2
        )
        expected_first = 1 if index % 2 == 0 else 2
        if first_level != expected_first or second_level == expected_first:
            raise CiboCapitalManagementError(
                f"T11 market-impact {label} level order must alternate"
            )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError(
            "T11 market-impact mean requires observations"
        )
    return sum(values, Decimal(0)) / Decimal(len(values))
