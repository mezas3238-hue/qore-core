"""Architect-2 intake from canonical QORE lifecycle into T02 terminal reason.

T02 structural-stop research must consume an explicit causal exit reason and
must not trust a caller-provided boolean for provider-position binding.

The lifecycle/provider bridge is supplied only through the immutable
T02ProviderPositionBindingReceipt.  Architect-2 verifies the exact QORE
position UUID and entry/exit execution-receipt UUIDs before projecting the
explicit lifecycle exit reason onto the provider position.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo_arch2_t02_provider_position_binding import (
    T02ProviderPositionBindingReceipt,
)
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
    provider_position_binding_sha256: str
    execution_risk_evidence_id: str
    executed_risk_sha256: str
    settlement_sha256: str
    lifecycle_evidence: T02TerminalReasonEvidence
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
        for name in (
            "provider_position_binding_sha256",
            "executed_risk_sha256",
            "settlement_sha256",
        ):
            _sha(getattr(self, name), name)
        if not self.execution_risk_evidence_id:
            raise CiboCapitalManagementError(
                "T02 lifecycle intake execution-risk evidence id required"
            )
        if not isinstance(self.lifecycle_evidence, T02TerminalReasonEvidence):
            raise CiboCapitalManagementError(
                "T02 lifecycle intake requires canonical terminal evidence"
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
    binding: T02ProviderPositionBindingReceipt,
    lifecycle: ClientPositionLifecycle,
    observed_at: datetime,
) -> T02LifecycleTerminalIntake:
    """Project an explicit EXIT only after exact lifecycle/provider binding."""

    if not isinstance(binding, T02ProviderPositionBindingReceipt):
        raise CiboCapitalManagementError(
            "T02 lifecycle intake requires canonical provider-position binding"
        )
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
    if str(lifecycle.position_id.value) != binding.client_position_id:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake client/provider binding position drift"
        )

    opening = lifecycle.actions[0]
    terminal = lifecycle.actions[-1]
    if opening.kind is not ClientPositionActionKind.OPEN:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake requires opening OPEN action"
        )
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
    if opening.execution_receipt_id is None or terminal.execution_receipt_id is None:
        raise CiboCapitalManagementError(
            "T02 lifecycle intake requires entry/exit execution receipts"
        )
    if (
        str(opening.execution_receipt_id.value)
        != binding.entry_execution_receipt_id
    ):
        raise CiboCapitalManagementError(
            "T02 lifecycle intake entry execution receipt drift"
        )
    if (
        str(terminal.execution_receipt_id.value)
        != binding.exit_execution_receipt_id
    ):
        raise CiboCapitalManagementError(
            "T02 lifecycle intake exit execution receipt drift"
        )

    binding_sha = binding.fingerprint()
    lifecycle_ref = str(terminal.evidence_ref.value)
    material = (
        f"{binding.decision_evidence_sha256}|{binding.signal_fingerprint}|"
        f"{binding.provider_position_id}|{binding.settlement_deal_ids}|"
        f"{lifecycle.position_id.value}|{terminal.action_id.value}|"
        f"{lifecycle_ref}|{binding_sha}"
    )
    evidence_id = "t02-terminal:" + hashlib.sha256(material.encode()).hexdigest()
    source_ref = (
        f"qore-lifecycle:{lifecycle_ref}|"
        f"provider-binding:{binding_sha}"
    )
    evidence = t02_terminal_reason_from_qore_lifecycle(
        evidence_id=evidence_id,
        decision_evidence_sha256=binding.decision_evidence_sha256,
        signal_fingerprint=binding.signal_fingerprint,
        position_id=binding.provider_position_id,
        settlement_deal_ids=binding.settlement_deal_ids,
        exit_reason=terminal.exit_reason,
        lifecycle_evidence_ref=source_ref,
        observed_at=observed_at,
    )
    return T02LifecycleTerminalIntake(
        provider_position_id=binding.provider_position_id,
        provider_position_binding_ref=source_ref,
        provider_position_binding_sha256=binding_sha,
        execution_risk_evidence_id=binding.execution_risk_evidence_id,
        executed_risk_sha256=binding.executed_risk_sha256,
        settlement_sha256=binding.settlement_sha256,
        lifecycle_evidence=evidence,
        inferred_from_pnl=False,
        inferred_from_price=False,
        productive_authority=False,
    )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"T02 lifecycle intake {name} must be canonical SHA-256"
        )
