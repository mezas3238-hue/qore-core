"""Canonical Architect-2 intake receipt for the CIBO Integrator.

The receipt summarizes only the current eight-workstream non-overlapping scope.
It derives from the executable active-frontier contract, so historical 43-front
artifacts cannot silently re-expand Architect-2 authority.

This is evidence/handoff metadata only:
- it does not mutate the canonical CIBO ledger;
- it does not consume Phase22 V2;
- it grants no production or merge authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from qore.infrastructure.cibo_arch2_active_frontier_v2 import (
    Architect2ActiveFront,
    Architect2ActiveState,
    architect2_active_frontier_v2,
)
from qore.infrastructure.cibo_arch2_active_scope_v2 import (
    ARCHITECT2_ACTIVE_OWNERSHIP,
)


@dataclass(frozen=True, slots=True)
class Architect2IntegratorIntakeReceipt:
    workstreams: tuple[Architect2ActiveFront, ...]
    scope_count: int
    terminal_recommendation_count: int
    nonterminal_count: int
    external_dependency_count: int
    integrator_receipt_dependency_count: int
    local_actionable_blocker_count: int
    canonical_ledger_modified: bool = False
    phase22_v2_consumed: bool = False
    merge_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if tuple(item.workstream_id for item in self.workstreams) != (
            ARCHITECT2_ACTIVE_OWNERSHIP
        ):
            raise ValueError("Architect-2 intake scope/order drift")
        if self.scope_count != len(self.workstreams) or self.scope_count != 8:
            raise ValueError("Architect-2 intake must cover exactly eight fronts")

        terminal = sum(
            item.state is Architect2ActiveState.TERMINAL_RECOMMENDATION_READY
            for item in self.workstreams
        )
        if self.terminal_recommendation_count != terminal:
            raise ValueError("Architect-2 intake terminal count drift")
        if self.nonterminal_count != self.scope_count - terminal:
            raise ValueError("Architect-2 intake nonterminal count drift")

        external = sum(
            item.state
            is Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE
            for item in self.workstreams
        )
        if self.external_dependency_count != external:
            raise ValueError("Architect-2 intake external dependency count drift")

        integrator = sum(
            item.state is Architect2ActiveState.WAITING_ON_INTEGRATOR_RECEIPT
            for item in self.workstreams
        )
        if self.integrator_receipt_dependency_count != integrator:
            raise ValueError("Architect-2 intake Integrator dependency count drift")

        local_actionable = sum(
            item.state
            not in {
                Architect2ActiveState.TERMINAL_RECOMMENDATION_READY,
                Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE,
                Architect2ActiveState.WAITING_ON_INTEGRATOR_RECEIPT,
            }
            for item in self.workstreams
        )
        if self.local_actionable_blocker_count != local_actionable:
            raise ValueError("Architect-2 intake local blocker count drift")

        if (
            self.canonical_ledger_modified
            or self.phase22_v2_consumed
            or self.merge_authority
            or self.productive_authority
        ):
            raise ValueError("Architect-2 intake exceeded authority boundary")

    def fingerprint(self) -> str:
        payload = asdict(self)
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_architect2_integrator_intake_receipt() -> Architect2IntegratorIntakeReceipt:
    rows = architect2_active_frontier_v2()
    terminal = sum(
        item.state is Architect2ActiveState.TERMINAL_RECOMMENDATION_READY
        for item in rows
    )
    external = sum(
        item.state
        is Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE
        for item in rows
    )
    integrator = sum(
        item.state is Architect2ActiveState.WAITING_ON_INTEGRATOR_RECEIPT
        for item in rows
    )
    local_actionable = sum(
        item.state
        not in {
            Architect2ActiveState.TERMINAL_RECOMMENDATION_READY,
            Architect2ActiveState.WAITING_ON_AUTHORITATIVE_FORWARD_LIFECYCLE,
            Architect2ActiveState.WAITING_ON_INTEGRATOR_RECEIPT,
        }
        for item in rows
    )
    return Architect2IntegratorIntakeReceipt(
        workstreams=rows,
        scope_count=len(rows),
        terminal_recommendation_count=terminal,
        nonterminal_count=len(rows) - terminal,
        external_dependency_count=external,
        integrator_receipt_dependency_count=integrator,
        local_actionable_blocker_count=local_actionable,
        canonical_ledger_modified=False,
        phase22_v2_consumed=False,
        merge_authority=False,
        productive_authority=False,
    )


ARCHITECT2_INTEGRATOR_INTAKE_RECEIPT = (
    build_architect2_integrator_intake_receipt()
)
