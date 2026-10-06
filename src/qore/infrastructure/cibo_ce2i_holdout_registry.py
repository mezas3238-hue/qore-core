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
    SEALED_UNTOUCHED = "SEALED_UNTOUCHED"
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


CONFIRMED_CIBO_BURNS: tuple[CiboBurnedInterval, ...] = (
    CiboBurnedInterval(
        burn_id="vt31:r8:fresh-validation-2016-04-19_2018-05-19",
        lineage=TraderLineage.VT31_NAS100,
        start_at=datetime(2016, 4, 19, tzinfo=UTC),
        end_exclusive_at=datetime(2018, 5, 19, tzinfo=UTC),
        reason=(
            "VT31 R8 historical fresh validation consumed outcomes across the "
            "interval, including 2017H1; candidate rejection does not restore "
            "holdout freshness"
        ),
        evidence_ref="artifact:10402199719",
    ),
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
    CiboBurnedInterval(
        burn_id="phase22:v2:consumed",
        lineage=None,
        start_at=datetime(2015, 10, 19, tzinfo=UTC),
        end_exclusive_at=datetime(2016, 4, 19, tzinfo=UTC),
        reason="Phase22 V2 one-shot emitted fresh outcomes",
        evidence_ref="run:37007253157",
    ),
    CiboBurnedInterval(
        burn_id="phase22:v3:partial-fresh-execution",
        lineage=None,
        start_at=datetime(2015, 4, 19, tzinfo=UTC),
        end_exclusive_at=datetime(2015, 10, 19, tzinfo=UTC),
        reason=(
            "Phase22 V3 executed fresh Trader lanes before terminal ABI failure; "
            "partial fresh execution burns the integrated candidate"
        ),
        evidence_ref="run:37047009381",
    ),
    CiboBurnedInterval(
        burn_id="phase22:v4:consumed-invalid",
        lineage=None,
        start_at=datetime(2014, 10, 19, tzinfo=UTC),
        end_exclusive_at=datetime(2015, 4, 19, tzinfo=UTC),
        reason="Phase22 V4 emitted fresh lane outcomes before terminal failure",
        evidence_ref="run:37059089221",
    ),
)


BURNED_USD60_HOLDOUT_2017H1_V1 = CiboHoldoutCandidate(
    candidate_id="CIBO_USD60_6M_HOLDOUT_2017H1_V1",
    start_at=datetime(2017, 1, 1, tzinfo=UTC),
    end_exclusive_at=datetime(2017, 7, 1, tzinfo=UTC),
    status=CiboHoldoutCandidateStatus.BURNED,
    selection_rule=(
        "original latest six-calendar-month block ending at the then-known "
        "earliest burn boundary; later invalidated by prior VT31 R8 outcome use"
    ),
    outcome_data_inspected_at_selection=False,
    source_validation_complete=True,
)

# Backward-compatible identity for V1-specific audit/read-only code. It is
# intentionally burned and must fail burn-clean eligibility checks.
PREREGISTERED_USD60_HOLDOUT = BURNED_USD60_HOLDOUT_2017H1_V1

NEXT_PREREGISTERED_USD60_HOLDOUT = CiboHoldoutCandidate(
    candidate_id="CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2",
    start_at=datetime(2015, 10, 19, tzinfo=UTC),
    end_exclusive_at=datetime(2016, 4, 19, tzinfo=UTC),
    status=CiboHoldoutCandidateStatus.ELIGIBLE_FROZEN,
    selection_rule=(
        "latest exact six-calendar-month block ending at the earliest confirmed "
        "lineage burn boundary after incorporating VT31 R8; selected without "
        "inspecting candidate outcomes"
    ),
    outcome_data_inspected_at_selection=False,
    source_validation_complete=True,
)

# Legacy Phase22 V2 code imports ACTIVE_USD60_HOLDOUT_CANDIDATE.  Keep that
# alias stable so historical receipts remain readable, but never use it to
# authorize a new fresh cycle after the durable V2 consumption receipt.
ACTIVE_USD60_HOLDOUT_CANDIDATE = NEXT_PREREGISTERED_USD60_HOLDOUT

CURRENT_FRESH_USD60_HOLDOUT_CANDIDATE = CiboHoldoutCandidate(
    candidate_id="CIBO_USD60_6M_HOLDOUT_2013-10-19_2014-04-19_V6",
    start_at=datetime(2013, 10, 19, tzinfo=UTC),
    end_exclusive_at=datetime(2014, 4, 19, tzinfo=UTC),
    status=CiboHoldoutCandidateStatus.SOURCE_VALIDATION_PENDING,
    selection_rule=(
        "latest mechanically preceding exact six-calendar-month block after "
        "V2/V3/V4 fresh consumption and V5 read-only source unavailability; "
        "selected without inspecting V6 outcomes"
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
