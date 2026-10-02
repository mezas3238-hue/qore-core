"""Architect-2 empirical qualification for CE2I T20 capital release.

The mechanical T20 primitive already proves the request -> Risk -> execution ->
settlement -> release identity.  This module answers only whether the real
forward population is large and complete enough to recommend terminal T20
closure.

Thresholds are inherited unchanged from the frozen Phase20D qualification plan.
No new threshold is tuned from the observed population.  The Architect-2 lane
does not mutate the canonical ledger and grants no productive authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)

TERMINAL_RECOMMENDATION = "COMPLETED_AND_PROVEN"
WAITING_RECOMMENDATION = "WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE"

_REQUIRED_TRADER_IDS = frozenset(
    {
        TraderLineage.R38_GBPJPY.value,
        TraderLineage.R43_GBPUSD.value,
        TraderLineage.R42_AUDJPY.value,
        TraderLineage.R38_EURUSD.value,
        TraderLineage.R34_XAUUSD.value,
        TraderLineage.VT08_FOREX.value,
        TraderLineage.VT31_NAS100.value,
    }
)
_REQUIRED_FOLDS = frozenset({"WF1", "WF2", "WF3", "WF4"})


@dataclass(frozen=True, slots=True)
class T20ForwardReleaseQualification:
    manifest_candidate_rows: int
    complete_release_lifecycles: int
    blocking_gap_count: int
    t20_release_gap_count: int
    release_coverage: Decimal
    minimum_candidate_outcomes: int
    required_candidate_coverage: Decimal
    all_complete_rows_capacity_reconciled: bool
    four_fold_coverage_complete: bool
    seven_lineage_coverage_complete: bool
    population_minimum_met: bool
    source_manifest_scientific_ready: bool
    empirical_t20_ready: bool
    recommendation: str
    canonical_ledger_modified: bool = False
    phase22_v2_consumed: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "manifest_candidate_rows",
            "complete_release_lifecycles",
            "blocking_gap_count",
            "t20_release_gap_count",
            "minimum_candidate_outcomes",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"T20 qualification {name} must be non-negative int"
                )
        for name in ("release_coverage", "required_candidate_coverage"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
                or value > 1
            ):
                raise CiboCapitalManagementError(
                    f"T20 qualification {name} must be Decimal in [0,1]"
                )
        for name in (
            "all_complete_rows_capacity_reconciled",
            "four_fold_coverage_complete",
            "seven_lineage_coverage_complete",
            "population_minimum_met",
            "source_manifest_scientific_ready",
            "empirical_t20_ready",
            "canonical_ledger_modified",
            "phase22_v2_consumed",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T20 qualification {name} must be bool"
                )
        if self.recommendation not in {
            TERMINAL_RECOMMENDATION,
            WAITING_RECOMMENDATION,
        }:
            raise CiboCapitalManagementError(
                "T20 qualification recommendation invalid"
            )
        expected_ready = all(
            (
                self.population_minimum_met,
                self.source_manifest_scientific_ready,
                self.release_coverage >= self.required_candidate_coverage,
                self.blocking_gap_count == 0,
                self.t20_release_gap_count == 0,
                self.all_complete_rows_capacity_reconciled,
                self.four_fold_coverage_complete,
                self.seven_lineage_coverage_complete,
            )
        )
        if self.empirical_t20_ready != expected_ready:
            raise CiboCapitalManagementError(
                "T20 qualification readiness drift"
            )
        expected_recommendation = (
            TERMINAL_RECOMMENDATION
            if expected_ready
            else WAITING_RECOMMENDATION
        )
        if self.recommendation != expected_recommendation:
            raise CiboCapitalManagementError(
                "T20 qualification recommendation/readiness drift"
            )
        if (
            self.canonical_ledger_modified
            or self.phase22_v2_consumed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T20 qualification exceeded Architect-2 authority"
            )


def qualify_t20_forward_release_population(
    manifest: ArchBForwardEconomicManifest,
) -> T20ForwardReleaseQualification:
    """Assess authoritative T20 population using only frozen Phase20D gates."""

    if not isinstance(manifest, ArchBForwardEconomicManifest):
        raise CiboCapitalManagementError(
            "T20 qualification requires canonical Architect-B forward manifest"
        )

    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    candidate_rows = manifest.candidate_rows
    complete = manifest.complete_lineage_rows
    coverage = (
        Decimal(complete) / Decimal(candidate_rows)
        if candidate_rows
        else Decimal(0)
    )
    blocking = tuple(gap for gap in manifest.gaps if gap.blocking)
    release_gaps = tuple(
        gap
        for gap in manifest.gaps
        if "T20_RELEASE_EVIDENCE_MISSING" in gap.reasons
    )

    rows = manifest.rows
    reconciled = bool(rows) and all(
        row.released_stop_risk_capacity_usd
        == row.executed_initial_stop_risk_usd
        and row.released_margin_capacity_usd > 0
        and row.release_evidence_sha256.startswith("sha256:")
        and row.release_chain_sha256.startswith("sha256:")
        and row.terminal_release_at <= row.outcome_observed_at
        and row.capital_minutes > 0
        for row in rows
    )
    fold_rows = {
        fold: tuple(row for row in rows if row.fold_id == fold)
        for fold in _REQUIRED_FOLDS
    }
    four_folds = (
        {row.fold_id for row in rows} == _REQUIRED_FOLDS
        and all(
            len(items) >= plan.minimum_fold_candidate_outcomes
            and len({row.trader_id for row in items})
            >= plan.minimum_fold_lineages
            for items in fold_rows.values()
        )
    )

    lineage_counts: dict[str, int] = {}
    for row in rows:
        lineage_counts[row.trader_id] = lineage_counts.get(row.trader_id, 0) + 1
    seven_lineages = (
        set(lineage_counts) == _REQUIRED_TRADER_IDS
        and len(lineage_counts) == plan.minimum_global_lineages
        and all(
            lineage_counts[lineage] >= plan.minimum_outcomes_per_lineage
            for lineage in _REQUIRED_TRADER_IDS
        )
    )

    population_minimum = candidate_rows >= plan.minimum_candidate_outcomes
    ready = all(
        (
            population_minimum,
            manifest.ready_for_scientific_consumption,
            coverage >= plan.minimum_candidate_outcome_coverage,
            not blocking,
            not release_gaps,
            reconciled,
            four_folds,
            seven_lineages,
        )
    )
    return T20ForwardReleaseQualification(
        manifest_candidate_rows=candidate_rows,
        complete_release_lifecycles=complete,
        blocking_gap_count=len(blocking),
        t20_release_gap_count=len(release_gaps),
        release_coverage=coverage,
        minimum_candidate_outcomes=plan.minimum_candidate_outcomes,
        required_candidate_coverage=plan.minimum_candidate_outcome_coverage,
        all_complete_rows_capacity_reconciled=reconciled,
        four_fold_coverage_complete=four_folds,
        seven_lineage_coverage_complete=seven_lineages,
        population_minimum_met=population_minimum,
        source_manifest_scientific_ready=manifest.ready_for_scientific_consumption,
        empirical_t20_ready=ready,
        recommendation=(
            TERMINAL_RECOMMENDATION if ready else WAITING_RECOMMENDATION
        ),
        canonical_ledger_modified=False,
        phase22_v2_consumed=False,
        productive_authority=False,
    )
