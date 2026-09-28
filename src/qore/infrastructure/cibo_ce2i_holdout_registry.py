"""Burn registry and preregistered holdout candidate for CIBO certification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class CiboHoldoutCandidateStatus(StrEnum):
    SOURCE_VALIDATION_PENDING = "SOURCE_VALIDATION_PENDING"
    ELIGIBLE_FROZEN = "ELIGIBLE_FROZEN"
    BURNED = "BURNED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class CiboBurnedInterval:
    burn_id: str
    lineage: TraderLineage | None
    start_at: datetime
    end_exclusive_at: datetime
    reason: str
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.burn_id or not self.reason or not self.evidence_ref:
            raise CiboCapitalManagementError(
                "burn interval identity/reason/evidence are required"
            )
        _interval(self.start_at, self.end_exclusive_at)


@dataclass(frozen=True, slots=True)
class CiboHoldoutCandidate:
    candidate_id: str
    start_at: datetime
    end_exclusive_at: datetime
    status: CiboHoldoutCandidateStatus
    selection_rule: str
    outcome_data_inspected_at_selection: bool
    source_validation_complete: bool

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.selection_rule:
            raise CiboCapitalManagementError(
                "holdout candidate identity/selection rule are required"
            )
        _interval(self.start_at, self.end_exclusive_at)
        if not _six_calendar_months(self.start_at, self.end_exclusive_at):
            raise CiboCapitalManagementError(
                "holdout candidate must span exactly six calendar months"
            )
        if type(self.status) is not CiboHoldoutCandidateStatus:
            raise CiboCapitalManagementError(
                "holdout candidate status must use canonical enum"
            )
        for name in (
            "outcome_data_inspected_at_selection",
            "source_validation_complete",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(f"{name} must be bool")
        if self.outcome_data_inspected_at_selection:
            raise CiboCapitalManagementError(
                "holdout candidate cannot be selected after outcome inspection"
            )
        if (
            self.status is CiboHoldoutCandidateStatus.ELIGIBLE_FROZEN
            and not self.source_validation_complete
        ):
            raise CiboCapitalManagementError(
                "eligible holdout requires completed source validation"
            )


CONFIRMED_CIBO_BURNS: tuple[CiboBurnedInterval, ...] = (
    CiboBurnedInterval(
        burn_id="phase18:r34-xauusd:5y",
        lineage=TraderLineage.R34_XAUUSD,
        start_at=datetime(2021, 9, 17, tzinfo=UTC),
        end_exclusive_at=datetime(2026, 9, 17, tzinfo=UTC),
        reason="Phase18 authoritative geometry/baseline replay consumed interval",
        evidence_ref="artifact:10966524985",
    ),
    CiboBurnedInterval(
        burn_id="phase18:r43-gbpusd:5y",
        lineage=TraderLineage.R43_GBPUSD,
        start_at=datetime(2021, 9, 17, tzinfo=UTC),
        end_exclusive_at=datetime(2026, 9, 17, tzinfo=UTC),
        reason="Phase18 authoritative geometry/baseline replay consumed interval",
        evidence_ref="artifact:10965979677",
    ),
    CiboBurnedInterval(
        burn_id="phase18:r38-gbpjpy:5y",
        lineage=TraderLineage.R38_GBPJPY,
        start_at=datetime(2021, 9, 17, tzinfo=UTC),
        end_exclusive_at=datetime(2026, 9, 17, tzinfo=UTC),
        reason="Phase18 authoritative geometry/baseline replay consumed interval",
        evidence_ref="artifact:10967710012",
    ),
    CiboBurnedInterval(
        burn_id="phase18:r42-audjpy:5y",
        lineage=TraderLineage.R42_AUDJPY,
        start_at=datetime(2021, 9, 17, tzinfo=UTC),
        end_exclusive_at=datetime(2026, 9, 17, tzinfo=UTC),
        reason="Phase18 authoritative geometry/baseline replay consumed interval",
        evidence_ref="artifact:10965919857",
    ),
    CiboBurnedInterval(
        burn_id="phase18:r38-eurusd:5y",
        lineage=TraderLineage.R38_EURUSD,
        start_at=datetime(2021, 9, 17, tzinfo=UTC),
        end_exclusive_at=datetime(2026, 9, 17, tzinfo=UTC),
        reason="Phase18 authoritative geometry/baseline replay consumed interval",
        evidence_ref="artifact:10966899512",
    ),
    CiboBurnedInterval(
        burn_id="phase18:vt31-nas100:v4-5y",
        lineage=TraderLineage.VT31_NAS100,
        start_at=datetime(2017, 7, 1, tzinfo=UTC),
        end_exclusive_at=datetime(2022, 7, 1, tzinfo=UTC),
        reason="Phase18 V4 five-year replay consumed interval",
        evidence_ref="artifact:10967605286",
    ),
    CiboBurnedInterval(
        burn_id="phase18:vt08-forex:r315-holdout",
        lineage=TraderLineage.VT08_FOREX,
        start_at=datetime(2020, 7, 1, tzinfo=UTC),
        end_exclusive_at=datetime(2022, 7, 1, tzinfo=UTC),
        reason="Phase18 consumed the official R3.15 independent holdout",
        evidence_ref="artifact:10318827002",
    ),
    CiboBurnedInterval(
        burn_id="phase19:integrated-common-window",
        lineage=None,
        start_at=datetime(2021, 9, 23, 5, tzinfo=UTC),
        end_exclusive_at=datetime(2022, 6, 29, 9, tzinfo=UTC),
        reason="Phase19 integrated CIBO interaction/calibration research",
        evidence_ref="artifact:10966794619",
    ),
)


PREREGISTERED_USD60_HOLDOUT = CiboHoldoutCandidate(
    candidate_id="CIBO_USD60_6M_HOLDOUT_2017H1_V1",
    start_at=datetime(2017, 1, 1, tzinfo=UTC),
    end_exclusive_at=datetime(2017, 7, 1, tzinfo=UTC),
    status=CiboHoldoutCandidateStatus.SOURCE_VALIDATION_PENDING,
    selection_rule=(
        "latest complete six-calendar-month block ending at the earliest "
        "confirmed lineage burn boundary; selected without inspecting outcomes"
    ),
    outcome_data_inspected_at_selection=False,
    source_validation_complete=False,
)


def candidate_overlaps_confirmed_burn(
    candidate: CiboHoldoutCandidate,
    *,
    lineage: TraderLineage | None = None,
) -> bool:
    if not isinstance(candidate, CiboHoldoutCandidate):
        raise CiboCapitalManagementError("canonical holdout candidate required")
    for burn in CONFIRMED_CIBO_BURNS:
        if lineage is not None and burn.lineage not in (None, lineage):
            continue
        if _overlaps(
            candidate.start_at,
            candidate.end_exclusive_at,
            burn.start_at,
            burn.end_exclusive_at,
        ):
            return True
    return False


def candidate_is_burn_clean_for_all_lineages(
    candidate: CiboHoldoutCandidate,
) -> bool:
    return all(
        not candidate_overlaps_confirmed_burn(candidate, lineage=lineage)
        for lineage in (
            TraderLineage.VT08_FOREX,
            TraderLineage.R34_XAUUSD,
            TraderLineage.R38_EURUSD,
            TraderLineage.R43_GBPUSD,
            TraderLineage.R38_GBPJPY,
            TraderLineage.R42_AUDJPY,
            TraderLineage.VT31_NAS100,
        )
    )


def _overlaps(
    left_start: datetime,
    left_end: datetime,
    right_start: datetime,
    right_end: datetime,
) -> bool:
    return left_start < right_end and right_start < left_end


def _interval(start_at: datetime, end_at: datetime) -> None:
    for name, value in (("start_at", start_at), ("end_exclusive_at", end_at)):
        if value.tzinfo is None or value.utcoffset() is None:
            raise CiboCapitalManagementError(f"{name} must be timezone-aware")
    if end_at <= start_at:
        raise CiboCapitalManagementError("interval end must follow start")


def _six_calendar_months(start_at: datetime, end_at: datetime) -> bool:
    month = start_at.month - 1 + 6
    year = start_at.year + month // 12
    target_month = month % 12 + 1
    try:
        expected = start_at.replace(year=year, month=target_month)
    except ValueError:
        return False
    return end_at == expected
