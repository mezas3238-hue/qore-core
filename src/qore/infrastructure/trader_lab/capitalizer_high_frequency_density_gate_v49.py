"""V49 high-frequency density mandate.

V48 produced 159 source-complete opportunities in one year across all nine markets and
three sessions. The Owner rejected that density as incompatible with the intended Scalper.

V49 therefore treats density as a first-class PRE-ECONOMIC engineering gate. The numeric
floor below is a QORE/Owner product requirement, not an ICT/TTrades source rule. It is
deliberately checked before any P&L so the research cannot tune density to outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

IDENTITY = "QORE_CAPITALIZER_V49_HIGH_FREQUENCY_DENSITY_GATE"
V48_REJECTED_ANNUAL_REFERENCE = 159
MIN_ANNUAL_SOURCE_COMPLETE_OPPORTUNITIES = 500
MIN_SESSION_SOURCE_COMPLETE_OPPORTUNITIES = 100


class V49DensityDecision(StrEnum):
    HIGH_FREQUENCY_CAPACITY_PASS = "HIGH_FREQUENCY_CAPACITY_PASS"
    INSUFFICIENT_DENSITY = "INSUFFICIENT_DENSITY"


@dataclass(frozen=True, slots=True)
class V49DensityAssessment:
    annual_total: int
    asia_total: int
    london_total: int
    new_york_total: int
    decision: V49DensityDecision
    outcome_used: bool = False
    economics_used: bool = False
    quota_imposed: bool = False

    def __post_init__(self) -> None:
        if min(
            self.annual_total,
            self.asia_total,
            self.london_total,
            self.new_york_total,
        ) < 0:
            raise ValueError("density counts cannot be negative")
        passes = (
            self.annual_total >= MIN_ANNUAL_SOURCE_COMPLETE_OPPORTUNITIES
            and self.asia_total >= MIN_SESSION_SOURCE_COMPLETE_OPPORTUNITIES
            and self.london_total >= MIN_SESSION_SOURCE_COMPLETE_OPPORTUNITIES
            and self.new_york_total >= MIN_SESSION_SOURCE_COMPLETE_OPPORTUNITIES
        )
        if (
            self.decision is V49DensityDecision.HIGH_FREQUENCY_CAPACITY_PASS
        ) != passes:
            raise ValueError("density decision/payload mismatch")
        if self.outcome_used or self.economics_used:
            raise ValueError("density gate must run before economics")
        if self.quota_imposed:
            raise ValueError("density research cannot force trades")


def assess_v49_density(
    *,
    annual_total: int,
    asia_total: int,
    london_total: int,
    new_york_total: int,
) -> V49DensityAssessment:
    passes = (
        annual_total >= MIN_ANNUAL_SOURCE_COMPLETE_OPPORTUNITIES
        and asia_total >= MIN_SESSION_SOURCE_COMPLETE_OPPORTUNITIES
        and london_total >= MIN_SESSION_SOURCE_COMPLETE_OPPORTUNITIES
        and new_york_total >= MIN_SESSION_SOURCE_COMPLETE_OPPORTUNITIES
    )
    return V49DensityAssessment(
        annual_total=annual_total,
        asia_total=asia_total,
        london_total=london_total,
        new_york_total=new_york_total,
        decision=(
            V49DensityDecision.HIGH_FREQUENCY_CAPACITY_PASS
            if passes
            else V49DensityDecision.INSUFFICIENT_DENSITY
        ),
    )


@dataclass(frozen=True, slots=True)
class V49DensityMandate:
    identity: str = IDENTITY
    rejected_v48_reference: int = V48_REJECTED_ANNUAL_REFERENCE
    minimum_annual_source_complete: int = MIN_ANNUAL_SOURCE_COMPLETE_OPPORTUNITIES
    minimum_per_session_source_complete: int = MIN_SESSION_SOURCE_COMPLETE_OPPORTUNITIES
    source_rule: bool = False
    owner_qore_engineering_requirement: bool = True
    fresh_holdout_authorized: bool = False
    economics_authorized: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("V49 density mandate identity is frozen")
        if self.rejected_v48_reference != 159:
            raise ValueError("V48 rejected density reference is historical evidence")
        if self.minimum_annual_source_complete <= self.rejected_v48_reference:
            raise ValueError("V49 density floor must materially exceed rejected V48")
        if self.minimum_per_session_source_complete <= 0:
            raise ValueError("all three sessions must contribute meaningful capacity")
        if self.source_rule:
            raise ValueError("density floor is a QORE engineering requirement, not source")
        if not self.owner_qore_engineering_requirement:
            raise ValueError("V49 density mandate must preserve authority provenance")
        if self.fresh_holdout_authorized or self.economics_authorized:
            raise ValueError("density mandate grants no Fresh/economic authority")


V49_DENSITY_MANDATE = V49DensityMandate()
