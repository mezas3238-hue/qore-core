"""Owner-authorized Phase20D historical-shadow population qualification.

This lane replaces the physical waiting component of Phase20D with a consumed
one-year historical shadow envelope. Historical evidence is never relabelled
as FORWARD_OBSERVED. The burned 2017H1 V1 window is never rehabilitated, and
the active V2 certification holdout is never read here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_holdout_registry import (
    ACTIVE_USD60_HOLDOUT_CANDIDATE,
    BURNED_USD60_HOLDOUT_2017H1_V1,
)

POLICY_ID = "CIBO_PHASE20D_HISTORICAL_SHADOW_HOLDOUT_1Y_V1"
SHADOW_CANDIDATE_ID = (
    "CIBO_PHASE20D_SHADOW_HOLDOUT_1Y_2021H2_2022H1_V1"
)
SHADOW_START = datetime(2021, 7, 1, tzinfo=UTC)
SHADOW_END_EXCLUSIVE = datetime(2022, 7, 1, tzinfo=UTC)
ACTIVE_HOLDOUT_START = ACTIVE_USD60_HOLDOUT_CANDIDATE.start_at
ACTIVE_HOLDOUT_END_EXCLUSIVE = ACTIVE_USD60_HOLDOUT_CANDIDATE.end_exclusive_at
EVIDENCE_KIND = "HISTORICAL_SHADOW_HOLDOUT"

MINIMUM_DECISION_EPOCHS = 80
MINIMUM_CANDIDATE_OUTCOMES = 200
MINIMUM_CALENDAR_SPAN_DAYS = 28
MINIMUM_DISTINCT_TRADING_DAYS = 20
FOLD_COUNT = 4
MINIMUM_FOLD_CANDIDATE_OUTCOMES = 40
MINIMUM_GLOBAL_LINEAGES = 7
MINIMUM_OUTCOMES_PER_LINEAGE = 8
MINIMUM_FOLD_LINEAGES = 4
MINIMUM_CANDIDATE_OUTCOME_COVERAGE = Decimal("0.95")

REQUIRED_LINEAGES = (
    TraderLineage.R38_GBPJPY,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R42_AUDJPY,
    TraderLineage.R38_EURUSD,
    TraderLineage.R34_XAUUSD,
    TraderLineage.VT08_FOREX,
    TraderLineage.VT31_NAS100,
)


@dataclass(frozen=True, slots=True)
class HistoricalShadowObservation:
    trader_id: TraderLineage
    signal_fingerprint: str
    entry_at: datetime
    exit_at: datetime

    def __post_init__(self) -> None:
        if self.trader_id not in REQUIRED_LINEAGES:
            raise CiboCapitalManagementError(
                "historical shadow Trader lineage is not governed"
            )
        if not self.signal_fingerprint:
            raise CiboCapitalManagementError(
                "historical shadow signal fingerprint is required"
            )
        for name in ("entry_at", "exit_at"):
            value = getattr(self, name)
            if value.tzinfo is None or value.utcoffset() is None:
                raise CiboCapitalManagementError(
                    f"historical shadow {name} must be timezone-aware"
                )
        if self.exit_at < self.entry_at:
            raise CiboCapitalManagementError(
                "historical shadow exit cannot predate entry"
            )
        if not SHADOW_START <= self.entry_at < SHADOW_END_EXCLUSIVE:
            raise CiboCapitalManagementError(
                "historical shadow entry outside preregistered 1Y envelope"
            )
        if self.exit_at >= SHADOW_END_EXCLUSIVE:
            raise CiboCapitalManagementError(
                "historical shadow exit outside preregistered 1Y envelope"
            )


@dataclass(frozen=True, slots=True)
class HistoricalShadowFold:
    fold_id: str
    decision_epochs: int
    candidate_outcomes: int
    represented_lineages: int
    outcomes_by_lineage: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class HistoricalShadowQualification:
    passed: bool
    blockers: tuple[str, ...]
    decision_epochs: int
    candidate_outcomes: int
    calendar_span_days: int
    distinct_trading_days: int
    represented_lineages: int
    minimum_outcomes_any_lineage: int
    candidate_outcome_coverage: Decimal
    folds: tuple[HistoricalShadowFold, ...]
    observed_start: datetime
    observed_end: datetime
    physical_forward_wait_required: bool = False
    selected_outcomes_gate_deferred: bool = True
    provider_usd_execution_claimed: bool = False
    evidence_relabelled_forward_observed: bool = False
    final_holdout_2017h1_read: bool = False
    active_holdout_v2_read: bool = False
    certification_ready: bool = False
    productive_authority: bool = False


def evaluate_historical_shadow_population(
    observations: tuple[HistoricalShadowObservation, ...],
) -> HistoricalShadowQualification:
    """Evaluate consumed historical population without USD fabrication."""

    if not observations:
        raise CiboCapitalManagementError(
            "historical shadow qualification requires observations"
        )
    ordered = tuple(
        sorted(
            observations,
            key=lambda item: (
                item.entry_at,
                item.trader_id.value,
                item.signal_fingerprint,
            ),
        )
    )
    fingerprints = tuple(item.signal_fingerprint for item in ordered)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "historical shadow signal fingerprints must be unique"
        )

    epochs = tuple(sorted({item.entry_at for item in ordered}))
    first = epochs[0]
    last = epochs[-1]
    calendar_span = (last - first).days
    trading_days = len({item.entry_at.date() for item in ordered})
    lineage_counts = {
        lineage: sum(1 for item in ordered if item.trader_id is lineage)
        for lineage in REQUIRED_LINEAGES
    }
    represented = sum(count > 0 for count in lineage_counts.values())
    minimum_lineage = min(lineage_counts.values())
    folds = _folds(ordered=ordered, epochs=epochs)
    coverage = Decimal(1)

    blockers: list[str] = []
    if len(epochs) < MINIMUM_DECISION_EPOCHS:
        blockers.append("SHADOW_DECISION_EPOCHS_BELOW_MINIMUM")
    if len(ordered) < MINIMUM_CANDIDATE_OUTCOMES:
        blockers.append("SHADOW_CANDIDATE_OUTCOMES_BELOW_MINIMUM")
    if calendar_span < MINIMUM_CALENDAR_SPAN_DAYS:
        blockers.append("SHADOW_CALENDAR_SPAN_BELOW_MINIMUM")
    if trading_days < MINIMUM_DISTINCT_TRADING_DAYS:
        blockers.append("SHADOW_TRADING_DAYS_BELOW_MINIMUM")
    if represented < MINIMUM_GLOBAL_LINEAGES:
        blockers.append("SHADOW_GLOBAL_LINEAGES_BELOW_MINIMUM")
    if minimum_lineage < MINIMUM_OUTCOMES_PER_LINEAGE:
        blockers.append("SHADOW_OUTCOMES_PER_LINEAGE_BELOW_MINIMUM")
    if coverage < MINIMUM_CANDIDATE_OUTCOME_COVERAGE:
        blockers.append("SHADOW_CANDIDATE_OUTCOME_COVERAGE_BELOW_MINIMUM")
    if len(folds) != FOLD_COUNT:
        blockers.append("SHADOW_FOLD_COUNT_INVALID")
    for fold in folds:
        if fold.candidate_outcomes < MINIMUM_FOLD_CANDIDATE_OUTCOMES:
            blockers.append(
                f"{fold.fold_id}_CANDIDATE_OUTCOMES_BELOW_MINIMUM"
            )
        if fold.represented_lineages < MINIMUM_FOLD_LINEAGES:
            blockers.append(f"{fold.fold_id}_LINEAGES_BELOW_MINIMUM")

    blockers = list(dict.fromkeys(blockers))
    return HistoricalShadowQualification(
        passed=not blockers,
        blockers=tuple(blockers),
        decision_epochs=len(epochs),
        candidate_outcomes=len(ordered),
        calendar_span_days=calendar_span,
        distinct_trading_days=trading_days,
        represented_lineages=represented,
        minimum_outcomes_any_lineage=minimum_lineage,
        candidate_outcome_coverage=coverage,
        folds=folds,
        observed_start=first,
        observed_end=last,
    )


def _folds(
    *,
    ordered: tuple[HistoricalShadowObservation, ...],
    epochs: tuple[datetime, ...],
) -> tuple[HistoricalShadowFold, ...]:
    base, remainder = divmod(len(epochs), FOLD_COUNT)
    cursor = 0
    result: list[HistoricalShadowFold] = []
    for index in range(FOLD_COUNT):
        count = base + (1 if index < remainder else 0)
        selected_epochs = epochs[cursor : cursor + count]
        cursor += count
        epoch_set = set(selected_epochs)
        rows = tuple(item for item in ordered if item.entry_at in epoch_set)
        by_lineage = tuple(
            (
                lineage.value,
                sum(1 for item in rows if item.trader_id is lineage),
            )
            for lineage in REQUIRED_LINEAGES
        )
        result.append(
            HistoricalShadowFold(
                fold_id=f"WF{index + 1}",
                decision_epochs=len(selected_epochs),
                candidate_outcomes=len(rows),
                represented_lineages=sum(
                    lineage_count > 0
                    for _lineage, lineage_count in by_lineage
                ),
                outcomes_by_lineage=by_lineage,
            )
        )
    return tuple(result)


def policy_invariants() -> dict[str, object]:
    """Return immutable governance facts for manifests/tests."""

    return {
        "policy_id": POLICY_ID,
        "shadow_candidate_id": SHADOW_CANDIDATE_ID,
        "shadow_start": SHADOW_START.isoformat(),
        "shadow_end_exclusive": SHADOW_END_EXCLUSIVE.isoformat(),
        "evidence_kind": EVIDENCE_KIND,
        "burned_v1_candidate_id": BURNED_USD60_HOLDOUT_2017H1_V1.candidate_id,
        "burned_v1_status": BURNED_USD60_HOLDOUT_2017H1_V1.status.value,
        "burned_v1_reused_as_fresh": False,
        "active_holdout_candidate_id": ACTIVE_USD60_HOLDOUT_CANDIDATE.candidate_id,
        "active_holdout_start": ACTIVE_HOLDOUT_START.isoformat(),
        "active_holdout_end_exclusive": ACTIVE_HOLDOUT_END_EXCLUSIVE.isoformat(),
        "windows_disjoint": SHADOW_START >= ACTIVE_HOLDOUT_END_EXCLUSIVE,
        "historical_relabelled_forward_observed": False,
        "provider_usd_execution_imputation_allowed": False,
        "selected_outcomes_gate_deferred": True,
        "active_holdout_v2_read": False,
        "productive_authority": False,
    }
