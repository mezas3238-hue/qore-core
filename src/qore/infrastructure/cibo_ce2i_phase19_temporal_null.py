"""Phase 19E temporal-null evidence for seven-Trader overlap research.

The null model asks a narrow question:

    Is the observed cross-Trader overlap greater than expected if each
    opportunity keeps its weekday, UTC time-of-day and observed duration, but
    its calendar date is independently reassigned inside the common window?

No outcome, R, sizing, USD, provider economics, expected value or future market
state is consumed. The result is observational research evidence only and has
no sizing/allocation/Risk/execution authority.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)

_PAIR_KEYS = tuple(
    tuple(sorted((left, right), key=lambda trader: trader.value))
    for index, left in enumerate(PHASE19_REQUIRED_TRADERS)
    for right in PHASE19_REQUIRED_TRADERS[index + 1 :]
)


def _aware(value: datetime, *, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")


def _dates_between(start: date, end: date) -> tuple[date, ...]:
    days = (end - start).days
    return tuple(start + timedelta(days=offset) for offset in range(days + 1))


def _pair_overlap_count(
    left: tuple[tuple[datetime, datetime], ...],
    right: tuple[tuple[datetime, datetime], ...],
) -> int:
    ordered_left = tuple(sorted(left))
    ordered_right = tuple(sorted(right))
    count = 0
    start_index = 0
    for left_entry, left_exit in ordered_left:
        while (
            start_index < len(ordered_right)
            and ordered_right[start_index][1] <= left_entry
        ):
            start_index += 1
        index = start_index
        while index < len(ordered_right):
            right_entry, right_exit = ordered_right[index]
            if right_entry >= left_exit:
                break
            if right_exit > left_entry:
                count += 1
            index += 1
    return count


def _count_pairs(
    by_trader: dict[
        TraderLineage,
        tuple[tuple[datetime, datetime], ...],
    ],
) -> dict[tuple[TraderLineage, TraderLineage], int]:
    return {
        (left, right): _pair_overlap_count(by_trader[left], by_trader[right])
        for left, right in _PAIR_KEYS
    }


@dataclass(frozen=True, slots=True)
class Phase19TemporalNullPairEvidence:
    left_trader: TraderLineage
    right_trader: TraderLineage
    observed_overlap_pairs: int
    null_mean_overlap_pairs: Decimal
    null_p95_overlap_pairs: int
    upper_tail_probability: Decimal

    def __post_init__(self) -> None:
        for trader in (self.left_trader, self.right_trader):
            if trader not in PHASE19_REQUIRED_TRADERS:
                raise CiboCapitalManagementError(
                    "temporal null pair trader outside Phase 19"
                )
        if self.left_trader is self.right_trader:
            raise CiboCapitalManagementError(
                "temporal null pair requires distinct Traders"
            )
        if (
            type(self.observed_overlap_pairs) is not int
            or self.observed_overlap_pairs < 0
            or type(self.null_p95_overlap_pairs) is not int
            or self.null_p95_overlap_pairs < 0
        ):
            raise CiboCapitalManagementError(
                "temporal null overlap counts must be non-negative ints"
            )
        if (
            not isinstance(self.null_mean_overlap_pairs, Decimal)
            or not self.null_mean_overlap_pairs.is_finite()
            or self.null_mean_overlap_pairs < 0
        ):
            raise CiboCapitalManagementError(
                "temporal null mean must be finite non-negative Decimal"
            )
        if (
            not isinstance(self.upper_tail_probability, Decimal)
            or not self.upper_tail_probability.is_finite()
            or not Decimal(0) < self.upper_tail_probability <= Decimal(1)
        ):
            raise CiboCapitalManagementError(
                "temporal null tail probability must be in (0, 1]"
            )

    @property
    def unordered_key(self) -> tuple[TraderLineage, TraderLineage]:
        left, right = sorted(
            (self.left_trader, self.right_trader),
            key=lambda trader: trader.value,
        )
        return left, right


@dataclass(frozen=True, slots=True)
class Phase19TemporalNullEvidence:
    common_window_start: datetime
    common_window_end: datetime
    permutations: int
    random_seed: int
    observed_cross_trader_overlap_pairs: int
    null_mean_cross_trader_overlap_pairs: Decimal
    null_p95_cross_trader_overlap_pairs: int
    upper_tail_probability: Decimal
    pair_evidence: tuple[Phase19TemporalNullPairEvidence, ...]
    conditioning: tuple[str, ...]
    outcomes_used: bool = False
    sizing_used: bool = False
    provider_economics_used: bool = False
    allocation_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _aware(self.common_window_start, name="common_window_start")
        _aware(self.common_window_end, name="common_window_end")
        if self.common_window_end <= self.common_window_start:
            raise CiboCapitalManagementError(
                "temporal null common window is invalid"
            )
        if type(self.permutations) is not int or self.permutations < 100:
            raise CiboCapitalManagementError(
                "temporal null requires at least 100 permutations"
            )
        if type(self.random_seed) is not int:
            raise CiboCapitalManagementError(
                "temporal null random_seed must be int"
            )
        if (
            type(self.observed_cross_trader_overlap_pairs) is not int
            or self.observed_cross_trader_overlap_pairs < 0
            or type(self.null_p95_cross_trader_overlap_pairs) is not int
            or self.null_p95_cross_trader_overlap_pairs < 0
        ):
            raise CiboCapitalManagementError(
                "temporal null total overlap counts are invalid"
            )
        for name in (
            "null_mean_cross_trader_overlap_pairs",
            "upper_tail_probability",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"temporal null {name} must be finite Decimal"
                )
        if not Decimal(0) < self.upper_tail_probability <= Decimal(1):
            raise CiboCapitalManagementError(
                "temporal null total tail probability must be in (0, 1]"
            )
        if not self.conditioning:
            raise CiboCapitalManagementError(
                "temporal null conditioning must be explicit"
            )
        keys = tuple(item.unordered_key for item in self.pair_evidence)
        if len(keys) != len(set(keys)) or set(keys) != set(_PAIR_KEYS):
            raise CiboCapitalManagementError(
                "temporal null requires complete seven-Trader pair evidence"
            )
        if (
            self.outcomes_used
            or self.sizing_used
            or self.provider_economics_used
            or self.allocation_authority
            or self.risk_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "temporal null evidence governance drift"
            )


def _eligible_dates(
    *,
    opportunity: Phase19ChronologicalOpportunity,
    common_window_start: datetime,
    common_window_end: datetime,
    candidate_dates: tuple[date, ...],
) -> tuple[date, ...]:
    duration = opportunity.exit_at - opportunity.entry_at
    eligible: list[date] = []
    for candidate_date in candidate_dates:
        if candidate_date.weekday() != opportunity.entry_at.weekday():
            continue
        candidate_entry = opportunity.entry_at.replace(
            year=candidate_date.year,
            month=candidate_date.month,
            day=candidate_date.day,
        )
        candidate_exit = candidate_entry + duration
        if (
            candidate_entry >= common_window_start
            and candidate_exit <= common_window_end
        ):
            eligible.append(candidate_date)
    return tuple(eligible)


def measure_phase19_temporal_null(
    *,
    opportunities: tuple[Phase19ChronologicalOpportunity, ...],
    common_window_start: datetime,
    common_window_end: datetime,
    permutations: int,
    random_seed: int,
) -> Phase19TemporalNullEvidence:
    """Measure observed overlap against a calendar-conditioned independence null."""

    _aware(common_window_start, name="common_window_start")
    _aware(common_window_end, name="common_window_end")
    if common_window_end <= common_window_start:
        raise CiboCapitalManagementError(
            "temporal null common window is invalid"
        )
    if type(permutations) is not int or permutations < 100:
        raise CiboCapitalManagementError(
            "temporal null requires at least 100 permutations"
        )
    if type(random_seed) is not int:
        raise CiboCapitalManagementError(
            "temporal null random_seed must be int"
        )
    if not opportunities:
        raise CiboCapitalManagementError(
            "temporal null requires opportunities"
        )

    fingerprints = tuple(
        (item.trader_id, item.signal_fingerprint) for item in opportunities
    )
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "duplicate opportunity in temporal null evidence"
        )
    population = {item.trader_id for item in opportunities}
    if population != set(PHASE19_REQUIRED_TRADERS):
        raise CiboCapitalManagementError(
            "temporal null requires complete seven-Trader population"
        )
    for item in opportunities:
        if (
            item.entry_at < common_window_start
            or item.exit_at > common_window_end
        ):
            raise CiboCapitalManagementError(
                "temporal null opportunity outside common window"
            )

    candidate_dates = _dates_between(
        common_window_start.date(),
        common_window_end.date(),
    )
    eligible_by_signal: dict[str, tuple[date, ...]] = {}
    for item in opportunities:
        eligible = _eligible_dates(
            opportunity=item,
            common_window_start=common_window_start,
            common_window_end=common_window_end,
            candidate_dates=candidate_dates,
        )
        if not eligible:
            raise CiboCapitalManagementError(
                "temporal null opportunity has no eligible reassignment date"
            )
        eligible_by_signal[item.signal_fingerprint] = eligible

    observed_by_trader = {
        trader: tuple(
            (item.entry_at, item.exit_at)
            for item in opportunities
            if item.trader_id is trader
        )
        for trader in PHASE19_REQUIRED_TRADERS
    }
    observed_pairs = _count_pairs(observed_by_trader)
    observed_total = sum(observed_pairs.values())

    rng = random.Random(random_seed)
    pair_samples = {key: [] for key in _PAIR_KEYS}
    total_samples: list[int] = []

    for _ in range(permutations):
        simulated_by_trader: dict[
            TraderLineage,
            list[tuple[datetime, datetime]],
        ] = {trader: [] for trader in PHASE19_REQUIRED_TRADERS}
        for item in opportunities:
            chosen_date = rng.choice(
                eligible_by_signal[item.signal_fingerprint]
            )
            simulated_entry = item.entry_at.replace(
                year=chosen_date.year,
                month=chosen_date.month,
                day=chosen_date.day,
            )
            simulated_exit = simulated_entry + (
                item.exit_at - item.entry_at
            )
            simulated_by_trader[item.trader_id].append(
                (simulated_entry, simulated_exit)
            )

        simulated_pairs = _count_pairs(
            {
                trader: tuple(intervals)
                for trader, intervals in simulated_by_trader.items()
            }
        )
        for key, value in simulated_pairs.items():
            pair_samples[key].append(value)
        total_samples.append(sum(simulated_pairs.values()))

    def p95(values: list[int]) -> int:
        ordered = sorted(values)
        index = ((95 * len(ordered) + 99) // 100) - 1
        return ordered[max(0, min(index, len(ordered) - 1))]

    def tail_probability(values: list[int], observed: int) -> Decimal:
        exceedances = sum(value >= observed for value in values)
        return Decimal(exceedances + 1) / Decimal(len(values) + 1)

    pair_evidence = tuple(
        Phase19TemporalNullPairEvidence(
            left_trader=left,
            right_trader=right,
            observed_overlap_pairs=observed_pairs[(left, right)],
            null_mean_overlap_pairs=(
                Decimal(sum(pair_samples[(left, right)]))
                / Decimal(permutations)
            ),
            null_p95_overlap_pairs=p95(pair_samples[(left, right)]),
            upper_tail_probability=tail_probability(
                pair_samples[(left, right)],
                observed_pairs[(left, right)],
            ),
        )
        for left, right in _PAIR_KEYS
    )

    return Phase19TemporalNullEvidence(
        common_window_start=common_window_start,
        common_window_end=common_window_end,
        permutations=permutations,
        random_seed=random_seed,
        observed_cross_trader_overlap_pairs=observed_total,
        null_mean_cross_trader_overlap_pairs=(
            Decimal(sum(total_samples)) / Decimal(permutations)
        ),
        null_p95_cross_trader_overlap_pairs=p95(total_samples),
        upper_tail_probability=tail_probability(
            total_samples,
            observed_total,
        ),
        pair_evidence=pair_evidence,
        conditioning=(
            "same_trader",
            "same_weekday",
            "same_utc_time_of_day",
            "same_observed_duration",
            "independent_calendar_date_reassignment",
        ),
    )
