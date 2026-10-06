"""Architect-2 binding from complete forward lineage into T02 structural OOS.

This bridge combines three independently authoritative planes:
1. Architect-B provider/Risk/settlement/release manifest row;
2. canonical Phase20 terminal outcome;
3. explicit T02 terminal-reason intake from the QORE position lifecycle.

It creates the exact T02ForwardStructuralOutcome consumed by the frozen T02 OOS
audit.  No terminal reason is inferred from PnL or price.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_arch2_t02_lifecycle_intake import (
    T02LifecycleTerminalIntake,
)
from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifestRow,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardOutcomeSeal,
)
from qore.infrastructure.cibo_ce2i_phase20_t02_structural_oos import (
    T02ForwardStructuralOutcome,
)


@dataclass(frozen=True, slots=True)
class T02StructuralLineageBinding:
    structural_outcome: T02ForwardStructuralOutcome
    provider_position_binding_ref: str
    manifest_decision_sha256: str
    manifest_settlement_sha256: str
    outcome_position_id: int
    lineage_reconciled: bool = True
    inferred_from_pnl: bool = False
    inferred_from_price: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.structural_outcome,
            T02ForwardStructuralOutcome,
        ):
            raise CiboCapitalManagementError(
                "T02 structural binding requires canonical structural outcome"
            )
        if not self.provider_position_binding_ref:
            raise CiboCapitalManagementError(
                "T02 structural binding provider position ref required"
            )
        if (
            not self.manifest_decision_sha256.startswith("sha256:")
            or len(self.manifest_decision_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "T02 structural binding manifest decision SHA invalid"
            )
        if (
            not self.manifest_settlement_sha256.startswith("sha256:")
            or len(self.manifest_settlement_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "T02 structural binding manifest settlement SHA invalid"
            )
        if (
            not isinstance(self.outcome_position_id, int)
            or isinstance(self.outcome_position_id, bool)
            or self.outcome_position_id <= 0
        ):
            raise CiboCapitalManagementError(
                "T02 structural binding outcome position invalid"
            )
        if (
            not self.lineage_reconciled
            or self.inferred_from_pnl
            or self.inferred_from_price
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T02 structural binding governance/lineage incomplete"
            )


def bind_t02_structural_outcome(
    *,
    manifest_row: ArchBForwardEconomicManifestRow,
    source_outcome: Phase20ForwardOutcomeSeal,
    terminal_intake: T02LifecycleTerminalIntake,
) -> T02StructuralLineageBinding:
    """Require exact decision/signal/position/settlement/execution lineage."""

    if not isinstance(manifest_row, ArchBForwardEconomicManifestRow):
        raise CiboCapitalManagementError(
            "T02 structural binding requires canonical manifest row"
        )
    if not isinstance(source_outcome, Phase20ForwardOutcomeSeal):
        raise CiboCapitalManagementError(
            "T02 structural binding requires canonical Phase20 outcome"
        )
    if not isinstance(terminal_intake, T02LifecycleTerminalIntake):
        raise CiboCapitalManagementError(
            "T02 structural binding requires lifecycle terminal intake"
        )

    terminal = terminal_intake.lifecycle_evidence
    if manifest_row.decision_evidence_sha256 != source_outcome.decision_evidence_sha256:
        raise CiboCapitalManagementError(
            "T02 structural manifest/outcome decision drift"
        )
    if manifest_row.signal_fingerprint != source_outcome.signal_fingerprint:
        raise CiboCapitalManagementError(
            "T02 structural manifest/outcome signal drift"
        )
    if terminal.decision_evidence_sha256 != manifest_row.decision_evidence_sha256:
        raise CiboCapitalManagementError(
            "T02 structural terminal/manifest decision drift"
        )
    if terminal.signal_fingerprint != manifest_row.signal_fingerprint:
        raise CiboCapitalManagementError(
            "T02 structural terminal/manifest signal drift"
        )
    if terminal.position_id != source_outcome.position_id:
        raise CiboCapitalManagementError(
            "T02 structural terminal/outcome position drift"
        )
    if terminal_intake.provider_position_id != source_outcome.position_id:
        raise CiboCapitalManagementError(
            "T02 structural provider/outcome position drift"
        )
    if terminal.settlement_deal_ids != source_outcome.settlement_deal_ids:
        raise CiboCapitalManagementError(
            "T02 structural terminal/outcome settlement drift"
        )
    if manifest_row.settlement_deal_ids != source_outcome.settlement_deal_ids:
        raise CiboCapitalManagementError(
            "T02 structural manifest/outcome settlement drift"
        )
    if (
        manifest_row.execution_risk_evidence_id
        != source_outcome.execution_risk_evidence_id
    ):
        raise CiboCapitalManagementError(
            "T02 structural manifest/outcome execution-risk drift"
        )
    if manifest_row.outcome_observed_at != source_outcome.observed_at:
        raise CiboCapitalManagementError(
            "T02 structural manifest/outcome observation-time drift"
        )
    if manifest_row.realized_net_pnl_usd != source_outcome.realized_net_pnl_usd:
        raise CiboCapitalManagementError(
            "T02 structural manifest/outcome realized-PnL drift"
        )
    if (
        manifest_row.executed_initial_stop_risk_usd
        != source_outcome.executed_initial_stop_risk_usd
    ):
        raise CiboCapitalManagementError(
            "T02 structural manifest/outcome executed-risk amount drift"
        )
    if not terminal_intake.provider_position_binding_verified:
        raise CiboCapitalManagementError(
            "T02 structural provider-position binding is unverified"
        )
    try:
        lineage = TraderLineage(manifest_row.trader_id)
    except ValueError as error:
        raise CiboCapitalManagementError(
            "T02 structural manifest trader lineage invalid"
        ) from error

    structural = T02ForwardStructuralOutcome(
        decision_evidence_sha256=manifest_row.decision_evidence_sha256,
        signal_fingerprint=manifest_row.signal_fingerprint,
        trader_id=lineage,
        source_outcome_evidence_id=source_outcome.evidence_id,
        provider_economics_evidence_id=manifest_row.provider_evidence_id,
        execution_risk_evidence_id=manifest_row.execution_risk_evidence_id,
        terminal_reason_evidence=terminal,
    )
    return T02StructuralLineageBinding(
        structural_outcome=structural,
        provider_position_binding_ref=(
            terminal_intake.provider_position_binding_ref
        ),
        manifest_decision_sha256=manifest_row.decision_evidence_sha256,
        manifest_settlement_sha256=manifest_row.settlement_sha256,
        outcome_position_id=source_outcome.position_id,
        lineage_reconciled=True,
        inferred_from_pnl=False,
        inferred_from_price=False,
        productive_authority=False,
    )
