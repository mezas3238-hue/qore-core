from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from qore.governance.executive_control import (
    AuthorizedExecutiveControlIntent,
    ExecutiveControlAction,
)
from qore.governance.executive_governance_state import (
    ExecutiveActiveRestriction,
    ExecutiveGovernanceStateSnapshot,
    ExecutiveGovernanceStateSnapshotId,
    ExecutiveGovernanceStateVersion,
    ExecutiveNewTradingState,
    ExecutiveSystemRunState,
)
from qore.governance.executive_ports import ExecutiveReceiptId
from qore.kernel.errors import DomainError
from qore.kernel.result import Result


class ExecutiveGovernanceMutationError(DomainError):
    """Base error for explicit Governance state mutation contracts."""

    __slots__ = ()


class ExecutiveGovernanceMutationValidationError(ExecutiveGovernanceMutationError):
    """A governance mutation value violates a deterministic invariant."""

    __slots__ = ()


class ExecutiveGovernanceMutationUnavailableError(ExecutiveGovernanceMutationError):
    """The concrete mutation boundary is unavailable."""

    __slots__ = ()


class ExecutiveGovernanceMutationId:
    __slots__ = ("value",)

    def __init__(self, value: UUID) -> None:
        if not isinstance(value, UUID):
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation id must be UUID"
            )
        self.value = value

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ExecutiveGovernanceMutationId)
            and self.value == other.value
        )

    def __hash__(self) -> int:
        return hash(self.value)

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveGovernanceMutationValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveGovernanceMutationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _restriction_map(
    snapshot: ExecutiveGovernanceStateSnapshot,
) -> dict[str, ExecutiveActiveRestriction]:
    return {
        str(item.restriction_id.value): item
        for item in snapshot.market_restrictions + snapshot.account_restrictions
    }


def _require_unchanged_restrictions(
    expected: ExecutiveGovernanceStateSnapshot,
    next_state: ExecutiveGovernanceStateSnapshot,
) -> None:
    if (
        expected.market_restrictions != next_state.market_restrictions
        or expected.account_restrictions != next_state.account_restrictions
    ):
        raise ExecutiveGovernanceMutationValidationError(
            "global state mutation must not alter active restrictions"
        )


def _validate_restriction_history(
    expected: ExecutiveGovernanceStateSnapshot,
    next_state: ExecutiveGovernanceStateSnapshot,
) -> tuple[
    tuple[ExecutiveActiveRestriction, ...],
    tuple[ExecutiveActiveRestriction, ...],
]:
    before = _restriction_map(expected)
    after = _restriction_map(next_state)
    for restriction_id in before.keys() & after.keys():
        if before[restriction_id] != after[restriction_id]:
            raise ExecutiveGovernanceMutationValidationError(
                "existing active restriction history must be immutable"
            )
    added = tuple(after[key] for key in sorted(after.keys() - before.keys()))
    removed = tuple(before[key] for key in sorted(before.keys() - after.keys()))
    return added, removed


def _validate_action_transition(
    authorized: AuthorizedExecutiveControlIntent,
    expected: ExecutiveGovernanceStateSnapshot,
    next_state: ExecutiveGovernanceStateSnapshot,
    *,
    source_receipt_id: ExecutiveReceiptId,
) -> None:
    action = authorized.intent.action
    target = authorized.intent.target
    added, removed = _validate_restriction_history(expected, next_state)

    if action is ExecutiveControlAction.PAUSE_SYSTEM:
        if expected.system_run_state is ExecutiveSystemRunState.PAUSED:
            raise ExecutiveGovernanceMutationValidationError(
                "already-paused system requires NO_CHANGE rather than mutation"
            )
        if next_state.system_run_state is not ExecutiveSystemRunState.PAUSED:
            raise ExecutiveGovernanceMutationValidationError(
                "pause-system mutation must produce PAUSED state"
            )
        if next_state.new_trading_state is not expected.new_trading_state:
            raise ExecutiveGovernanceMutationValidationError(
                "pause-system mutation must preserve new-trading state"
            )
        _require_unchanged_restrictions(expected, next_state)
        return

    if action is ExecutiveControlAction.RESUME_SYSTEM:
        if expected.system_run_state is ExecutiveSystemRunState.ACTIVE:
            raise ExecutiveGovernanceMutationValidationError(
                "already-active system requires NO_CHANGE rather than mutation"
            )
        if next_state.system_run_state is not ExecutiveSystemRunState.ACTIVE:
            raise ExecutiveGovernanceMutationValidationError(
                "resume-system mutation must produce ACTIVE state"
            )
        if next_state.new_trading_state is not expected.new_trading_state:
            raise ExecutiveGovernanceMutationValidationError(
                "resume-system mutation must preserve new-trading state"
            )
        _require_unchanged_restrictions(expected, next_state)
        return

    if action is ExecutiveControlAction.HALT_NEW_TRADING:
        if expected.new_trading_state is ExecutiveNewTradingState.HALTED:
            raise ExecutiveGovernanceMutationValidationError(
                "already-halted trading requires NO_CHANGE rather than mutation"
            )
        if next_state.new_trading_state is not ExecutiveNewTradingState.HALTED:
            raise ExecutiveGovernanceMutationValidationError(
                "halt-new-trading mutation must produce HALTED state"
            )
        if next_state.system_run_state is not expected.system_run_state:
            raise ExecutiveGovernanceMutationValidationError(
                "halt-new-trading mutation must preserve system run state"
            )
        _require_unchanged_restrictions(expected, next_state)
        return

    if action in {
        ExecutiveControlAction.RESTRICT_MARKET,
        ExecutiveControlAction.RESTRICT_ACCOUNT,
    }:
        if target is None:
            raise ExecutiveGovernanceMutationValidationError(
                "restriction mutation requires an explicit target"
            )
        if next_state.system_run_state is not expected.system_run_state:
            raise ExecutiveGovernanceMutationValidationError(
                "restriction mutation must preserve system run state"
            )
        if next_state.new_trading_state is not expected.new_trading_state:
            raise ExecutiveGovernanceMutationValidationError(
                "restriction mutation must preserve new-trading state"
            )
        if removed or len(added) != 1:
            raise ExecutiveGovernanceMutationValidationError(
                "restriction mutation must add exactly one restriction"
            )
        restriction = added[0]
        if restriction.target != target:
            raise ExecutiveGovernanceMutationValidationError(
                "new restriction target must match authorized intent target"
            )
        if restriction.source_receipt_id != source_receipt_id:
            raise ExecutiveGovernanceMutationValidationError(
                "new restriction must reference the mutation source receipt"
            )
        return

    if action is ExecutiveControlAction.RESTORE_RESTRICTION:
        if target is None:
            raise ExecutiveGovernanceMutationValidationError(
                "restore-restriction mutation requires explicit target"
            )
        if next_state.system_run_state is not expected.system_run_state:
            raise ExecutiveGovernanceMutationValidationError(
                "restore mutation must preserve system run state"
            )
        if next_state.new_trading_state is not expected.new_trading_state:
            raise ExecutiveGovernanceMutationValidationError(
                "restore mutation must preserve new-trading state"
            )
        if added or len(removed) != 1:
            raise ExecutiveGovernanceMutationValidationError(
                "restore mutation must remove exactly one active restriction"
            )
        if str(removed[0].restriction_id.value) != target.value:
            raise ExecutiveGovernanceMutationValidationError(
                "removed restriction id must match authorized restore target"
            )
        return

    raise ExecutiveGovernanceMutationValidationError(
        "authorized action does not mutate the materialized Governance state"
    )


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceMutationRequest:
    mutation_id: ExecutiveGovernanceMutationId
    authorized: AuthorizedExecutiveControlIntent
    expected_state: ExecutiveGovernanceStateSnapshot
    next_state: ExecutiveGovernanceStateSnapshot
    source_receipt_id: ExecutiveReceiptId
    requested_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.mutation_id, ExecutiveGovernanceMutationId):
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation request requires ExecutiveGovernanceMutationId"
            )
        if not isinstance(self.authorized, AuthorizedExecutiveControlIntent):
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation request requires authorized control intent"
            )
        if not isinstance(self.expected_state, ExecutiveGovernanceStateSnapshot):
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation request requires expected state snapshot"
            )
        if not isinstance(self.next_state, ExecutiveGovernanceStateSnapshot):
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation request requires next state snapshot"
            )
        if not isinstance(self.source_receipt_id, ExecutiveReceiptId):
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation request requires ExecutiveReceiptId"
            )
        _validate_timestamp(self.requested_at, field_name="requested_at")
        if self.requested_at < self.authorized.authorized_at:
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation cannot predate authorization"
            )
        if self.next_state.observed_at < self.expected_state.observed_at:
            raise ExecutiveGovernanceMutationValidationError(
                "next governance state cannot predate expected state"
            )
        if self.next_state.observed_at < self.requested_at:
            raise ExecutiveGovernanceMutationValidationError(
                "next governance state cannot predate mutation request"
            )
        if self.next_state.snapshot_id == self.expected_state.snapshot_id:
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation must produce a new snapshot identity"
            )
        if self.next_state.state_version == self.expected_state.state_version:
            raise ExecutiveGovernanceMutationValidationError(
                "governance mutation must produce a new state version"
            )
        existing_receipt_ids = {
            item.source_receipt_id
            for item in (
                self.expected_state.market_restrictions
                + self.expected_state.account_restrictions
            )
        }
        if self.source_receipt_id in existing_receipt_ids:
            raise ExecutiveGovernanceMutationValidationError(
                "mutation source receipt must not reuse active restriction provenance"
            )
        _validate_action_transition(
            self.authorized,
            self.expected_state,
            self.next_state,
            source_receipt_id=self.source_receipt_id,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mutation_id.logical_values(),
            self.authorized.logical_values(),
            self.expected_state.logical_values(),
            self.next_state.logical_values(),
            self.source_receipt_id.logical_values(),
            self.requested_at.isoformat(),
        )


class ExecutiveGovernanceMutationStatus(StrEnum):
    APPLIED = "applied"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceMutationReceipt:
    mutation_id: ExecutiveGovernanceMutationId
    source_receipt_id: ExecutiveReceiptId
    expected_snapshot_id: ExecutiveGovernanceStateSnapshotId
    expected_state_version: ExecutiveGovernanceStateVersion
    requested_snapshot_id: ExecutiveGovernanceStateSnapshotId
    requested_state_version: ExecutiveGovernanceStateVersion
    observed_snapshot_id: ExecutiveGovernanceStateSnapshotId
    observed_state_version: ExecutiveGovernanceStateVersion
    completed_at: datetime
    status: ExecutiveGovernanceMutationStatus

    def __post_init__(self) -> None:
        if not isinstance(self.mutation_id, ExecutiveGovernanceMutationId):
            raise ExecutiveGovernanceMutationValidationError(
                "mutation receipt requires ExecutiveGovernanceMutationId"
            )
        if not isinstance(self.source_receipt_id, ExecutiveReceiptId):
            raise ExecutiveGovernanceMutationValidationError(
                "mutation receipt requires ExecutiveReceiptId"
            )
        for field_name, value in (
            ("expected_snapshot_id", self.expected_snapshot_id),
            ("requested_snapshot_id", self.requested_snapshot_id),
            ("observed_snapshot_id", self.observed_snapshot_id),
        ):
            if not isinstance(value, ExecutiveGovernanceStateSnapshotId):
                raise ExecutiveGovernanceMutationValidationError(
                    f"{field_name} must be ExecutiveGovernanceStateSnapshotId"
                )
        for field_name, value in (
            ("expected_state_version", self.expected_state_version),
            ("requested_state_version", self.requested_state_version),
            ("observed_state_version", self.observed_state_version),
        ):
            if not isinstance(value, ExecutiveGovernanceStateVersion):
                raise ExecutiveGovernanceMutationValidationError(
                    f"{field_name} must be ExecutiveGovernanceStateVersion"
                )
        _validate_timestamp(self.completed_at, field_name="completed_at")
        if not isinstance(self.status, ExecutiveGovernanceMutationStatus):
            raise ExecutiveGovernanceMutationValidationError(
                "mutation receipt requires ExecutiveGovernanceMutationStatus"
            )
        if self.status is ExecutiveGovernanceMutationStatus.APPLIED:
            if self.observed_snapshot_id != self.requested_snapshot_id:
                raise ExecutiveGovernanceMutationValidationError(
                    "applied mutation must observe requested snapshot identity"
                )
            if self.observed_state_version != self.requested_state_version:
                raise ExecutiveGovernanceMutationValidationError(
                    "applied mutation must observe requested state version"
                )
        else:
            if (
                self.observed_snapshot_id == self.expected_snapshot_id
                and self.observed_state_version == self.expected_state_version
            ):
                raise ExecutiveGovernanceMutationValidationError(
                    "conflict receipt requires observed state to differ from expectation"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mutation_id.logical_values(),
            self.source_receipt_id.logical_values(),
            self.expected_snapshot_id.logical_values(),
            self.expected_state_version.logical_values(),
            self.requested_snapshot_id.logical_values(),
            self.requested_state_version.logical_values(),
            self.observed_snapshot_id.logical_values(),
            self.observed_state_version.logical_values(),
            self.completed_at.isoformat(),
            self.status.value,
        )


class ExecutiveGovernanceMutationPort(Protocol):
    """Persistence-neutral compare-and-set boundary for Governance state."""

    def compare_and_set(
        self,
        request: ExecutiveGovernanceMutationRequest,
    ) -> Result[ExecutiveGovernanceMutationReceipt, ExecutiveGovernanceMutationError]: ...
