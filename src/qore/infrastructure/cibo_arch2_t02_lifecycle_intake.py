"""Architect-2 intake from canonical QORE lifecycle into T02 terminal reason.

T02 structural-stop research must consume an explicit causal exit reason.  This
adapter binds one CLOSED ClientPositionLifecycle to the provider position and
settlement identity used by Phase20.  The provider-position binding itself must
already be independently verified; this module never infers it from price/PnL.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t02_terminal_reason_evidence import (
    T02TerminalReasonEvidence,
    t02_terminal_reason_from_qore_lifecycle,
)
from qore.infrastructure.client_position_lifecycle import (
    ClientPositionActionKind,
    ClientPositionLifecycle,
    ClientPositionState,
)


@dataclass(frozen=True, slots=True)
class T02LifecycleTerminalIntake:
    provider_position_id: int
    provider_position_binding_ref: str
    lifecycle_evidence: T02TerminalReasonEvidence
    provider_position_binding_verified: bool
    inferred_from_pnl: bool = False
    inferred_from_price: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.provider_position_id, int)
            or isinstance(self.provider_position_id, bool)
            or self.provider_position_id <= 0
        ):
            raise CiboCapitalManagementError(
                "T02 lifecycle intake provider position id invalid"
            )
        if not self.provider_position_binding_ref:
            raise CiboCapitalManagementError(
                "T02 lifecycle intake provider binding ref required"
            )
        if not isinstance(self.lifecycle_evidence, T02TerminalReasonEvidence):
            raise CiboCapitalManagementError(
                "T02 lifecycle intake requires canonical terminal evidence"
            )
        if not self.provider_position_binding_verified:
            raise CiboCapitalManagementError(
                "T02 lifecycle intake provider position binding unverified"
            )
        if (
            self.inferred_from_pnl
            or self.inferred_from_price
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T02 lifecycle intake cannot infer outcome or grant authority"
            )


def build_t02_lifecycle_terminal_intake(
    *,
    decision_evidence_sha256: str,
    signal_fingerprint: str,
    provider_position_id: int,
    settlement_deal_ids: tuple[int, ...],
    lifecycle: ClientPositionLifecycle,
    provider_position_binding_ref: str,
    provider_position_binding_verified: bool,
    observed_at: datetime,
) -> T02LifecycleTerminalIntake:
    """Extract only an explicit terminal EXIT reason from a bound lifecycle."""

    if not isinstance(lifecycle, ClientPositionLifecycle):
        raise CiboCapitalManagementError(
            "T02 lifecycle intake requires canonical ClientPositionLifecycle"
        )
    if lifecycle.state is not ClientPositionState.CLOSED:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake requires CLOSED lifecycle"
        )
    if lifecycle.closed_at is None:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake closed lifecycle lacks closed_at"
        )
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake observed_at must be timezone-aware"
        )
    if observed_at < lifecycle.closed_at:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake cannot be observed before lifecycle close"
        )
    if not provider_position_binding_ref or not provider_position_binding_verified:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake requires verified provider position binding"
        )
    if (
        not isinstance(provider_position_id, int)
        or isinstance(provider_position_id, bool)
        or provider_position_id <= 0
    ):
        raise CiboCapitalManagementError(
            "T02 lifecycle intake provider position id invalid"
        )
    if (
        not settlement_deal_ids
        or len(settlement_deal_ids) != len(set(settlement_deal_ids))
        or any(
            not isinstance(item, int)
            or isinstance(item, bool)
            or item <= 0
            for item in settlement_deal_ids
        )
    ):
        raise CiboCapitalManagementError(
            "T02 lifecycle intake settlement ids invalid"
        )

    terminal = lifecycle.actions[-1]
    if terminal.kind is not ClientPositionActionKind.EXIT:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake requires terminal EXIT action"
        )
    if terminal.exit_reason is None:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake terminal EXIT reason missing"
        )
    if terminal.occurred_at != lifecycle.closed_at:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake terminal EXIT/closed_at drift"
        )

    lifecycle_ref = str(terminal.evidence_ref.value)
    material = (
        f"{decision_evidence_sha256}|{signal_fingerprint}|"
        f"{provider_position_id}|{settlement_deal_ids}|"
        f"{lifecycle.position_id.value}|{terminal.action_id.value}|"
        f"{lifecycle_ref}|{provider_position_binding_ref}"
    )
    evidence_id = "t02-terminal:" + hashlib.sha256(material.encode()).hexdigest()
    source_ref = (
        f"qore-lifecycle:{lifecycle_ref}|"
        f"provider-binding:{provider_position_binding_ref}"
    )
    evidence = t02_terminal_reason_from_qore_lifecycle(
        evidence_id=evidence_id,
        decision_evidence_sha256=decision_evidence_sha256,
        signal_fingerprint=signal_fingerprint,
        position_id=provider_position_id,
        settlement_deal_ids=settlement_deal_ids,
        exit_reason=terminal.exit_reason,
        lifecycle_evidence_ref=source_ref,
        observed_at=observed_at,
    )
    return T02LifecycleTerminalIntake(
        provider_position_id=provider_position_id,
        provider_position_binding_ref=provider_position_binding_ref,
        lifecycle_evidence=evidence,
        provider_position_binding_verified=True,
        inferred_from_pnl=False,
        inferred_from_price=False,
        productive_authority=False,
    )
