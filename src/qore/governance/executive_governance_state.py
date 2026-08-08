from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from typing import Protocol
from uuid import UUID

from qore.domain.events import CorrelationId
from qore.governance.executive_control import (
    ExecutiveControlTarget,
    ExecutiveControlTargetKind,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef, ExecutiveReceiptId
from qore.kernel.errors import DomainError
from qore.kernel.result import Result


class ExecutiveGovernanceStateError(DomainError):
    """Base error for canonical executive Governance materialized state."""

    __slots__ = ()


class ExecutiveGovernanceStateValidationError(ExecutiveGovernanceStateError):
    """A materialized Governance state value violates a deterministic invariant."""

    __slots__ = ()


def _validate_aware_datetime(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveGovernanceStateValidationError(
            f"{field_name} must be a datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveGovernanceStateValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_canonical_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z0-9][a-z0-9._-]*", value
    ) is None:
        raise ExecutiveGovernanceStateValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    lowered = value.lower()
    forbidden = (
        "password=",
        "secret=",
        "token=",
        "bearer",
        "api_key=",
        "apikey=",
        "authorization",
    )
    if any(fragment in lowered for fragment in forbidden):
        raise ExecutiveGovernanceStateValidationError(
            f"{field_name} must not contain secret material"
        )
    return value


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceStateSnapshotId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveGovernanceStateValidationError(
                "governance state snapshot id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceStateRequestId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveGovernanceStateValidationError(
                "governance state request id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveRestrictionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveGovernanceStateValidationError(
                "executive restriction id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceStateVersion:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_canonical_code(self.value, field_name="governance state version"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernancePolicyVersion:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_canonical_code(self.value, field_name="governance policy version"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ExecutiveSystemRunState(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class ExecutiveNewTradingState(StrEnum):
    PERMITTED = "permitted"
    HALTED = "halted"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveActiveRestriction:
    """One currently active market/account restriction with exact audit provenance."""

    restriction_id: ExecutiveRestrictionId
    target: ExecutiveControlTarget
    applied_at: datetime
    source_receipt_id: ExecutiveReceiptId
    policy_version: ExecutiveGovernancePolicyVersion
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.restriction_id, ExecutiveRestrictionId):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction requires ExecutiveRestrictionId"
            )
        if not isinstance(self.target, ExecutiveControlTarget):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction requires ExecutiveControlTarget"
            )
        if self.target.kind not in {
            ExecutiveControlTargetKind.MARKET,
            ExecutiveControlTargetKind.ACCOUNT,
        }:
            raise ExecutiveGovernanceStateValidationError(
                "active restriction target must be market or account"
            )
        _validate_aware_datetime(self.applied_at, field_name="restriction applied_at")
        if not isinstance(self.source_receipt_id, ExecutiveReceiptId):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction requires ExecutiveReceiptId provenance"
            )
        if self.restriction_id.value == self.source_receipt_id.value:
            raise ExecutiveGovernanceStateValidationError(
                "restriction and source receipt identities must differ"
            )
        if not isinstance(self.policy_version, ExecutiveGovernancePolicyVersion):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction requires governance policy version"
            )
        if not isinstance(self.reason_codes, tuple) or not self.reason_codes:
            raise ExecutiveGovernanceStateValidationError(
                "active restriction requires non-empty reason codes"
            )
        normalized_reasons = tuple(
            sorted(
                _validate_canonical_code(item, field_name="restriction reason code")
                for item in self.reason_codes
            )
        )
        if len(set(normalized_reasons)) != len(normalized_reasons):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction reason codes must not contain duplicates"
            )
        object.__setattr__(self, "reason_codes", normalized_reasons)
        if not isinstance(self.evidence_refs, tuple) or not self.evidence_refs:
            raise ExecutiveGovernanceStateValidationError(
                "active restriction requires non-empty evidence refs"
            )
        if any(not isinstance(item, ExecutiveEvidenceRef) for item in self.evidence_refs):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction evidence must contain ExecutiveEvidenceRef values"
            )
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction evidence refs must not contain duplicates"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.restriction_id.logical_values(),
            self.target.logical_values(),
            self.applied_at.isoformat(),
            self.source_receipt_id.logical_values(),
            self.policy_version.logical_values(),
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceStateSnapshot:
    """Canonical current Governance state; never reconstructed implicitly by readers."""

    snapshot_id: ExecutiveGovernanceStateSnapshotId
    state_version: ExecutiveGovernanceStateVersion
    observed_at: datetime
    system_run_state: ExecutiveSystemRunState
    new_trading_state: ExecutiveNewTradingState
    market_restrictions: tuple[ExecutiveActiveRestriction, ...]
    account_restrictions: tuple[ExecutiveActiveRestriction, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_id, ExecutiveGovernanceStateSnapshotId):
            raise ExecutiveGovernanceStateValidationError(
                "governance snapshot requires ExecutiveGovernanceStateSnapshotId"
            )
        if not isinstance(self.state_version, ExecutiveGovernanceStateVersion):
            raise ExecutiveGovernanceStateValidationError(
                "governance snapshot requires ExecutiveGovernanceStateVersion"
            )
        _validate_aware_datetime(self.observed_at, field_name="governance observed_at")
        if not isinstance(self.system_run_state, ExecutiveSystemRunState):
            raise ExecutiveGovernanceStateValidationError(
                "governance snapshot requires ExecutiveSystemRunState"
            )
        if not isinstance(self.new_trading_state, ExecutiveNewTradingState):
            raise ExecutiveGovernanceStateValidationError(
                "governance snapshot requires ExecutiveNewTradingState"
            )
        self._validate_restriction_collection(
            self.market_restrictions,
            expected_kind=ExecutiveControlTargetKind.MARKET,
            field_name="market_restrictions",
        )
        self._validate_restriction_collection(
            self.account_restrictions,
            expected_kind=ExecutiveControlTargetKind.ACCOUNT,
            field_name="account_restrictions",
        )
        all_restrictions = self.market_restrictions + self.account_restrictions
        restriction_ids = [item.restriction_id for item in all_restrictions]
        if len(set(restriction_ids)) != len(restriction_ids):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction ids must be globally unique"
            )
        receipt_ids = [item.source_receipt_id for item in all_restrictions]
        if len(set(receipt_ids)) != len(receipt_ids):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction source receipt ids must be globally unique"
            )
        if any(item.applied_at > self.observed_at for item in all_restrictions):
            raise ExecutiveGovernanceStateValidationError(
                "active restriction cannot be applied after snapshot observation"
            )
        object.__setattr__(
            self,
            "market_restrictions",
            tuple(sorted(self.market_restrictions, key=_restriction_sort_key)),
        )
        object.__setattr__(
            self,
            "account_restrictions",
            tuple(sorted(self.account_restrictions, key=_restriction_sort_key)),
        )

    @staticmethod
    def _validate_restriction_collection(
        values: tuple[ExecutiveActiveRestriction, ...],
        *,
        expected_kind: ExecutiveControlTargetKind,
        field_name: str,
    ) -> None:
        if not isinstance(values, tuple) or any(
            not isinstance(item, ExecutiveActiveRestriction) for item in values
        ):
            raise ExecutiveGovernanceStateValidationError(
                f"{field_name} must contain ExecutiveActiveRestriction values"
            )
        if any(item.target.kind is not expected_kind for item in values):
            raise ExecutiveGovernanceStateValidationError(
                f"{field_name} contains a restriction with the wrong target kind"
            )
        target_values = [item.target.value for item in values]
        if len(set(target_values)) != len(target_values):
            raise ExecutiveGovernanceStateValidationError(
                f"{field_name} must contain at most one active restriction per target"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_id.logical_values(),
            self.state_version.logical_values(),
            self.observed_at.isoformat(),
            self.system_run_state.value,
            self.new_trading_state.value,
            tuple(item.logical_values() for item in self.market_restrictions),
            tuple(item.logical_values() for item in self.account_restrictions),
        )


def _restriction_sort_key(
    restriction: ExecutiveActiveRestriction,
) -> tuple[str, str]:
    return (restriction.target.value, str(restriction.restriction_id.value))


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceStateRequest:
    request_id: ExecutiveGovernanceStateRequestId
    requested_at: datetime
    correlation_id: CorrelationId

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, ExecutiveGovernanceStateRequestId):
            raise ExecutiveGovernanceStateValidationError(
                "governance state request requires ExecutiveGovernanceStateRequestId"
            )
        _validate_aware_datetime(self.requested_at, field_name="governance requested_at")
        if not isinstance(self.correlation_id, CorrelationId):
            raise ExecutiveGovernanceStateValidationError(
                "governance state request requires CorrelationId"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.request_id.logical_values(),
            self.requested_at.isoformat(),
            str(self.correlation_id.value),
        )


class ExecutiveGovernanceStateSource(Protocol):
    """Explicit source of already-materialized current Governance state."""

    def read_current_state(
        self,
        request: ExecutiveGovernanceStateRequest,
    ) -> Result[ExecutiveGovernanceStateSnapshot, ExecutiveGovernanceStateError]:
        """Read current state without replaying receipts or inventing transitions."""
        ...
