"""Deterministic Architect-B manifest intake for T11 gross-edge fresh OOS.

Only policy-selected rows whose terminal outcome occurs strictly after the
T11 freeze are admitted. Filtering is therefore fixed by policy-selection and
time, never by outcome value. The source manifest fingerprint is retained so
the exact population subset is replayable.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t11_gross_edge_oos import (
    T11GrossEdgeFreshObservation,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID,
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class T11GrossEdgeManifestIntake:
    manifest_id: str
    manifest_sha256: str
    source_row_count: int
    selected_row_count: int
    admitted_post_freeze_count: int
    excluded_pre_freeze_selected_count: int
    excluded_unselected_count: int
    observations: tuple[T11GrossEdgeFreshObservation, ...]
    filtering_rule: str = "POLICY_SELECTED_AND_OUTCOME_OBSERVED_AT_GT_T11_FREEZE"
    outcome_aware_filtering_used: bool = False
    model_refit_performed: bool = False
    phase22_v2_consumed: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.manifest_id != ARCH_B_FORWARD_ECONOMIC_MANIFEST_ID:
            raise CiboCapitalManagementError(
                "T11 gross-edge intake manifest identity drift"
            )
        if (
            not self.manifest_sha256.startswith("sha256:")
            or len(self.manifest_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge intake manifest digest invalid"
            )
        if self.source_row_count < 0 or self.selected_row_count < 0:
            raise CiboCapitalManagementError(
                "T11 gross-edge intake source counts invalid"
            )
        if self.admitted_post_freeze_count != len(self.observations):
            raise CiboCapitalManagementError(
                "T11 gross-edge intake admitted count drift"
            )
        if (
            self.admitted_post_freeze_count
            + self.excluded_pre_freeze_selected_count
            != self.selected_row_count
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge selected population accounting drift"
            )
        if self.selected_row_count + self.excluded_unselected_count != (
            self.source_row_count
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge total population accounting drift"
            )
        if self.filtering_rule != (
            "POLICY_SELECTED_AND_OUTCOME_OBSERVED_AT_GT_T11_FREEZE"
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge intake filtering rule drift"
            )
        if (
            self.outcome_aware_filtering_used
            or self.model_refit_performed
            or self.phase22_v2_consumed
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge intake governance contamination"
            )


def intake_t11_gross_edge_from_arch_b_manifest(
    manifest: ArchBForwardEconomicManifest,
) -> T11GrossEdgeManifestIntake:
    if not isinstance(manifest, ArchBForwardEconomicManifest):
        raise CiboCapitalManagementError(
            "T11 gross-edge intake requires canonical Architect-B manifest"
        )
    if not manifest.ready_for_scientific_consumption:
        raise CiboCapitalManagementError(
            "T11 gross-edge intake requires scientific-ready forward manifest"
        )
    if any(gap.blocking for gap in manifest.gaps):
        raise CiboCapitalManagementError(
            "T11 gross-edge intake rejects blocking manifest gaps"
        )

    selected = tuple(row for row in manifest.rows if row.policy_selected)
    admitted = tuple(
        row for row in selected if row.outcome_observed_at > FROZEN_AT
    )
    pre_freeze = len(selected) - len(admitted)
    observations: list[T11GrossEdgeFreshObservation] = []

    for row in admitted:
        if row.executed_source_volume <= 0:
            raise CiboCapitalManagementError(
                "T11 gross-edge intake executed volume must be positive"
            )
        if row.executed_initial_stop_risk_usd <= 0:
            raise CiboCapitalManagementError(
                "T11 gross-edge intake executed stop risk must be positive"
            )
        structural_r = (
            row.realized_net_pnl_usd / row.executed_initial_stop_risk_usd
        )
        stop_risk_per_volume = (
            row.executed_initial_stop_risk_usd / row.executed_source_volume
        )
        try:
            trader = TraderLineage(row.trader_id)
        except ValueError as error:
            raise CiboCapitalManagementError(
                "T11 gross-edge intake trader lineage is not canonical"
            ) from error

        observations.append(
            T11GrossEdgeFreshObservation(
                evidence_id=(
                    "arch-b-forward:"
                    + row.decision_evidence_sha256[7:23]
                    + ":"
                    + row.signal_fingerprint
                ),
                signal_fingerprint=row.signal_fingerprint,
                trader_id=trader,
                qore_symbol=row.qore_symbol,
                observed_at=row.outcome_observed_at,
                structural_outcome_r=structural_r,
                stop_risk_per_volume_usd=stop_risk_per_volume,
                outcome_reconciled=True,
                provider_bound=True,
                fresh_oos_source_authorized=True,
                model_refit_performed=False,
                productive_authority=False,
            )
        )

    return T11GrossEdgeManifestIntake(
        manifest_id=manifest.manifest_id,
        manifest_sha256=manifest.fingerprint(),
        source_row_count=len(manifest.rows),
        selected_row_count=len(selected),
        admitted_post_freeze_count=len(observations),
        excluded_pre_freeze_selected_count=pre_freeze,
        excluded_unselected_count=len(manifest.rows) - len(selected),
        observations=tuple(observations),
    )
