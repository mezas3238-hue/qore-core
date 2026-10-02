"""Fail-closed Architect-2 adapter from forward economics to T11 gross edge.

The Architect-B forward manifest already binds decision, provider economics,
Risk/execution, settlement and T20 release lineage.  This adapter converts only
scientifically consumable, policy-selected rows into the frozen T11 gross-edge
observation contract.

It never creates or consumes a Phase22 V2 outcome.  The caller must present an
explicit authorization for the fresh outcome population being consumed; the
adapter refuses to infer that authorization from a green workflow or from the
manifest itself.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t11_gross_edge_oos import (
    T11GrossEdgeFreshObservation,
)
from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    FROZEN_AT,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


@dataclass(frozen=True, slots=True)
class T11GrossEdgeForwardIntake:
    manifest_sha256: str
    fresh_population_authorization_id: str
    selected_row_count: int
    observations: tuple[T11GrossEdgeFreshObservation, ...]
    phase22_v2_consumed: bool = False
    model_refit_performed: bool = False
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not self.manifest_sha256.startswith("sha256:")
            or len(self.manifest_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge intake manifest digest invalid"
            )
        if not self.fresh_population_authorization_id:
            raise CiboCapitalManagementError(
                "T11 gross-edge intake authorization identity required"
            )
        if self.selected_row_count != len(self.observations):
            raise CiboCapitalManagementError(
                "T11 gross-edge intake selected-row count drift"
            )
        if not self.observations:
            raise CiboCapitalManagementError(
                "T11 gross-edge intake requires selected observations"
            )
        if (
            self.phase22_v2_consumed
            or self.model_refit_performed
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge intake exceeded Architect-2 authority"
            )


def build_t11_gross_edge_forward_intake(
    *,
    manifest: ArchBForwardEconomicManifest,
    fresh_population_authorization_id: str,
    fresh_population_authorized: bool,
) -> T11GrossEdgeForwardIntake:
    """Bind complete forward rows into T11 without inferring authorization."""

    if not isinstance(manifest, ArchBForwardEconomicManifest):
        raise CiboCapitalManagementError(
            "T11 gross-edge intake requires canonical forward manifest"
        )
    if not fresh_population_authorization_id:
        raise CiboCapitalManagementError(
            "T11 gross-edge fresh population authorization id required"
        )
    if not fresh_population_authorized:
        raise CiboCapitalManagementError(
            "T11 gross-edge fresh population is not explicitly authorized"
        )
    if not manifest.ready_for_scientific_consumption:
        raise CiboCapitalManagementError(
            "T11 gross-edge manifest is not ready for scientific consumption"
        )
    if manifest.gaps:
        raise CiboCapitalManagementError(
            "T11 gross-edge manifest cannot contain unresolved evidence gaps"
        )

    manifest_sha = manifest.fingerprint()
    selected = tuple(
        row
        for row in manifest.rows
        if row.policy_selected
    )
    if not selected:
        raise CiboCapitalManagementError(
            "T11 gross-edge manifest has no selected outcomes"
        )

    observations: list[T11GrossEdgeFreshObservation] = []
    for row in selected:
        if row.outcome_observed_at <= FROZEN_AT:
            raise CiboCapitalManagementError(
                "T11 gross-edge manifest contains pre-freeze selected outcome"
            )
        if (
            row.executed_initial_stop_risk_usd <= 0
            or row.executed_source_volume <= 0
        ):
            raise CiboCapitalManagementError(
                "T11 gross-edge row has invalid executed risk/volume"
            )
        try:
            lineage = TraderLineage(row.trader_id)
        except ValueError as error:
            raise CiboCapitalManagementError(
                "T11 gross-edge manifest trader lineage is not canonical"
            ) from error

        structural_r = (
            row.realized_net_pnl_usd
            / row.executed_initial_stop_risk_usd
        )
        stop_risk_per_volume = (
            row.executed_initial_stop_risk_usd
            / row.executed_source_volume
        )
        material = (
            f"{manifest_sha}|{fresh_population_authorization_id}|"
            f"{row.decision_evidence_sha256}|{row.signal_fingerprint}|"
            f"{row.execution_risk_evidence_id}|{row.settlement_sha256}|"
            f"{row.release_evidence_sha256}"
        )
        evidence_id = "t11-gross-edge:" + hashlib.sha256(
            material.encode()
        ).hexdigest()

        observations.append(
            T11GrossEdgeFreshObservation(
                evidence_id=evidence_id,
                signal_fingerprint=row.signal_fingerprint,
                trader_id=lineage,
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

    return T11GrossEdgeForwardIntake(
        manifest_sha256=manifest_sha,
        fresh_population_authorization_id=fresh_population_authorization_id,
        selected_row_count=len(selected),
        observations=tuple(observations),
        phase22_v2_consumed=False,
        model_refit_performed=False,
        canonical_ledger_modified=False,
        productive_authority=False,
    )
