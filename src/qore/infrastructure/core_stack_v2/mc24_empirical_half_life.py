"""MC-24 empirical knowledge half-life measurement for frozen adaptations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

MINIMUM_SAMPLES_PER_BIN: Final = 500
MINIMUM_ELIGIBLE_BINS: Final = 4
HALF_LIFE_FRACTION_BPS: Final = 5_000
MAXIMUM_TARGET_REGRESSION_BPS: Final = 500


class HalfLifeStatus(StrEnum):
    MEASURED = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_MEASURED"
    LOWER_BOUND = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_LOWER_BOUND"
    INSUFFICIENT = "MC24_EMPIRICAL_KNOWLEDGE_HALF_LIFE_INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True, slots=True)
class KnowledgeHalfLifeBin:
    bin_index: int
    start_age_days: int
    end_age_days: int
    sample_count: int
    pooled_incremental_information_bps: int
    maximum_target_regression_bps: int

    def __post_init__(self) -> None:
        if self.bin_index < 0 or self.start_age_days < 0:
            raise ValueError("half-life bin indexes/ages cannot be negative")
        if self.end_age_days <= self.start_age_days:
            raise ValueError("half-life bin end must exceed start")
        if self.sample_count < 0:
            raise ValueError("half-life bin sample_count cannot be negative")
        if self.maximum_target_regression_bps < 0:
            raise ValueError("regression magnitude cannot be negative")


@dataclass(frozen=True, slots=True)
class KnowledgeHalfLifeAssessment:
    status: HalfLifeStatus
    eligible_bin_count: int
    reference_bin_index: int | None
    reference_incremental_information_bps: int | None
    half_life_threshold_bps: int | None
    half_life_days: int | None
    lower_bound_days: int | None
    catastrophic_forgetting_detected: bool
    empirical_half_life_validated: bool
    retained_knowledge_non_degradation_pass: bool


def measure_empirical_half_life(
    bins: tuple[KnowledgeHalfLifeBin, ...],
) -> KnowledgeHalfLifeAssessment:
    ordered = tuple(sorted(bins, key=lambda item: item.bin_index))
    if len({item.bin_index for item in ordered}) != len(ordered):
        raise ValueError("half-life bins must have unique indexes")
    eligible = tuple(
        item for item in ordered if item.sample_count >= MINIMUM_SAMPLES_PER_BIN
    )
    forgetting = any(
        item.maximum_target_regression_bps > MAXIMUM_TARGET_REGRESSION_BPS
        for item in eligible
    )
    if len(eligible) < MINIMUM_ELIGIBLE_BINS:
        return KnowledgeHalfLifeAssessment(
            status=HalfLifeStatus.INSUFFICIENT,
            eligible_bin_count=len(eligible),
            reference_bin_index=None,
            reference_incremental_information_bps=None,
            half_life_threshold_bps=None,
            half_life_days=None,
            lower_bound_days=None,
            catastrophic_forgetting_detected=forgetting,
            empirical_half_life_validated=False,
            retained_knowledge_non_degradation_pass=not forgetting,
        )

    reference = next(
        (
            item
            for item in eligible
            if item.pooled_incremental_information_bps > 0
        ),
        None,
    )
    if reference is None:
        return KnowledgeHalfLifeAssessment(
            status=HalfLifeStatus.INSUFFICIENT,
            eligible_bin_count=len(eligible),
            reference_bin_index=None,
            reference_incremental_information_bps=None,
            half_life_threshold_bps=None,
            half_life_days=None,
            lower_bound_days=None,
            catastrophic_forgetting_detected=forgetting,
            empirical_half_life_validated=False,
            retained_knowledge_non_degradation_pass=not forgetting,
        )

    threshold = (
        reference.pooled_incremental_information_bps * HALF_LIFE_FRACTION_BPS
        // 10_000
    )
    after_reference = tuple(
        item for item in eligible if item.bin_index >= reference.bin_index
    )
    for first, second in zip(after_reference, after_reference[1:], strict=False):
        consecutive = second.bin_index == first.bin_index + 1
        below = (
            first.pooled_incremental_information_bps <= threshold
            and second.pooled_incremental_information_bps <= threshold
        )
        if consecutive and below:
            return KnowledgeHalfLifeAssessment(
                status=HalfLifeStatus.MEASURED,
                eligible_bin_count=len(eligible),
                reference_bin_index=reference.bin_index,
                reference_incremental_information_bps=(
                    reference.pooled_incremental_information_bps
                ),
                half_life_threshold_bps=threshold,
                half_life_days=first.start_age_days,
                lower_bound_days=None,
                catastrophic_forgetting_detected=forgetting,
                empirical_half_life_validated=True,
                retained_knowledge_non_degradation_pass=not forgetting,
            )

    return KnowledgeHalfLifeAssessment(
        status=HalfLifeStatus.LOWER_BOUND,
        eligible_bin_count=len(eligible),
        reference_bin_index=reference.bin_index,
        reference_incremental_information_bps=(
            reference.pooled_incremental_information_bps
        ),
        half_life_threshold_bps=threshold,
        half_life_days=None,
        lower_bound_days=max(item.end_age_days for item in eligible),
        catastrophic_forgetting_detected=forgetting,
        empirical_half_life_validated=True,
        retained_knowledge_non_degradation_pass=not forgetting,
    )
