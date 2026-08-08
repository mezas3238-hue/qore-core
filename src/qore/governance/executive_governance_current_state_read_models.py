from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from re import fullmatch
from uuid import UUID

from qore.governance.executive_governance_state import (
    ExecutiveActiveRestriction,
    ExecutiveGovernanceStateSnapshot,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import ExecutiveReadModelValidationError


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ExecutiveReadModelValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutiveReadModelValidationError(f"{field_name} must be timezone-aware")


def _validate_code(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z0-9][a-z0-9._-]*", value) is None:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    return value


def _validate_opaque_ref(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(
        r"[a-z0-9][a-z0-9._:/-]*", value
    ) is None:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must use canonical lowercase reference syntax"
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
        raise ExecutiveReadModelValidationError(
            f"{field_name} must not contain secret material"
        )
    return value


def _validated_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not values:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be a non-empty immutable tuple"
        )
    normalized = tuple(_validate_code(item, field_name=field_name) for item in values)
    if len(set(normalized)) != len(normalized):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or not values or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be a non-empty tuple of ExecutiveEvidenceRef"
        )
    if len(set(values)) != len(values):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceStateSnapshotRef:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "governance current-state snapshot ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceStateVersionRef:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(self.value, field_name="governance current-state version"),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ExecutiveGovernanceSystemRunState(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    UNKNOWN = "unknown"


class ExecutiveGovernanceNewTradingState(StrEnum):
    PERMITTED = "permitted"
    HALTED = "halted"
    UNKNOWN = "unknown"


class ExecutiveGovernanceRestrictionTargetKind(StrEnum):
    MARKET = "market"
    ACCOUNT = "account"


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceRestrictionRef:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "governance restriction ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceRestrictionTargetRef:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_opaque_ref(
                self.value,
                field_name="governance restriction target ref",
            ),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceRestrictionSourceReceiptRef:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ExecutiveReadModelValidationError(
                "governance restriction source receipt ref requires UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernancePolicyVersionRef:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            _validate_code(
                self.value,
                field_name="governance current-state policy version",
            ),
        )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceActiveRestrictionSummary:
    restriction_ref: ExecutiveGovernanceRestrictionRef
    target_kind: ExecutiveGovernanceRestrictionTargetKind
    target_ref: ExecutiveGovernanceRestrictionTargetRef
    applied_at: datetime
    source_receipt_ref: ExecutiveGovernanceRestrictionSourceReceiptRef
    policy_version: ExecutiveGovernancePolicyVersionRef
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.restriction_ref, ExecutiveGovernanceRestrictionRef):
            raise ExecutiveReadModelValidationError(
                "governance restriction summary requires restriction ref"
            )
        if not isinstance(self.target_kind, ExecutiveGovernanceRestrictionTargetKind):
            raise ExecutiveReadModelValidationError(
                "governance restriction summary requires target kind"
            )
        if not isinstance(self.target_ref, ExecutiveGovernanceRestrictionTargetRef):
            raise ExecutiveReadModelValidationError(
                "governance restriction summary requires target ref"
            )
        _validate_timestamp(self.applied_at, field_name="governance restriction applied_at")
        if not isinstance(
            self.source_receipt_ref,
            ExecutiveGovernanceRestrictionSourceReceiptRef,
        ):
            raise ExecutiveReadModelValidationError(
                "governance restriction summary requires source receipt ref"
            )
        if self.restriction_ref.value == self.source_receipt_ref.value:
            raise ExecutiveReadModelValidationError(
                "governance restriction and source receipt refs must differ"
            )
        if not isinstance(self.policy_version, ExecutiveGovernancePolicyVersionRef):
            raise ExecutiveReadModelValidationError(
                "governance restriction summary requires policy version"
            )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="governance restriction reasons"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="governance restriction evidence",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.restriction_ref.logical_values(),
            self.target_kind.value,
            self.target_ref.logical_values(),
            self.applied_at.isoformat(),
            self.source_receipt_ref.logical_values(),
            self.policy_version.logical_values(),
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveGovernanceCurrentStateSummary:
    """Stable executive projection of one canonical materialized Governance snapshot."""

    snapshot_ref: ExecutiveGovernanceStateSnapshotRef
    state_version: ExecutiveGovernanceStateVersionRef
    observed_at: datetime
    system_run_state: ExecutiveGovernanceSystemRunState
    new_trading_state: ExecutiveGovernanceNewTradingState
    active_market_restrictions: tuple[ExecutiveGovernanceActiveRestrictionSummary, ...]
    active_account_restrictions: tuple[ExecutiveGovernanceActiveRestrictionSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot_ref, ExecutiveGovernanceStateSnapshotRef):
            raise ExecutiveReadModelValidationError(
                "governance current state requires snapshot ref"
            )
        if not isinstance(self.state_version, ExecutiveGovernanceStateVersionRef):
            raise ExecutiveReadModelValidationError(
                "governance current state requires state version"
            )
        _validate_timestamp(self.observed_at, field_name="governance current-state observed_at")
        if not isinstance(self.system_run_state, ExecutiveGovernanceSystemRunState):
            raise ExecutiveReadModelValidationError(
                "governance current state requires system run state"
            )
        if not isinstance(self.new_trading_state, ExecutiveGovernanceNewTradingState):
            raise ExecutiveReadModelValidationError(
                "governance current state requires new-trading state"
            )
        self._validate_restrictions(
            self.active_market_restrictions,
            expected_kind=ExecutiveGovernanceRestrictionTargetKind.MARKET,
            field_name="active_market_restrictions",
        )
        self._validate_restrictions(
            self.active_account_restrictions,
            expected_kind=ExecutiveGovernanceRestrictionTargetKind.ACCOUNT,
            field_name="active_account_restrictions",
        )
        all_restrictions = (
            self.active_market_restrictions + self.active_account_restrictions
        )
        refs = [item.restriction_ref for item in all_restrictions]
        if len(set(refs)) != len(refs):
            raise ExecutiveReadModelValidationError(
                "governance current state must not duplicate restriction refs"
            )
        receipt_refs = [item.source_receipt_ref for item in all_restrictions]
        if len(set(receipt_refs)) != len(receipt_refs):
            raise ExecutiveReadModelValidationError(
                "governance current state must not duplicate source receipt refs"
            )
        if any(item.applied_at > self.observed_at for item in all_restrictions):
            raise ExecutiveReadModelValidationError(
                "governance restriction cannot postdate current-state observation"
            )
        object.__setattr__(
            self,
            "active_market_restrictions",
            tuple(sorted(self.active_market_restrictions, key=_restriction_sort_key)),
        )
        object.__setattr__(
            self,
            "active_account_restrictions",
            tuple(sorted(self.active_account_restrictions, key=_restriction_sort_key)),
        )

    @staticmethod
    def _validate_restrictions(
        values: tuple[ExecutiveGovernanceActiveRestrictionSummary, ...],
        *,
        expected_kind: ExecutiveGovernanceRestrictionTargetKind,
        field_name: str,
    ) -> None:
        if not isinstance(values, tuple) or any(
            not isinstance(item, ExecutiveGovernanceActiveRestrictionSummary)
            for item in values
        ):
            raise ExecutiveReadModelValidationError(
                f"{field_name} must contain governance restriction summaries"
            )
        if any(item.target_kind is not expected_kind for item in values):
            raise ExecutiveReadModelValidationError(
                f"{field_name} contains the wrong target kind"
            )
        targets = [item.target_ref.value for item in values]
        if len(set(targets)) != len(targets):
            raise ExecutiveReadModelValidationError(
                f"{field_name} must contain at most one restriction per target"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.snapshot_ref.logical_values(),
            self.state_version.logical_values(),
            self.observed_at.isoformat(),
            self.system_run_state.value,
            self.new_trading_state.value,
            tuple(item.logical_values() for item in self.active_market_restrictions),
            tuple(item.logical_values() for item in self.active_account_restrictions),
        )


def _restriction_sort_key(
    restriction: ExecutiveGovernanceActiveRestrictionSummary,
) -> tuple[str, str]:
    return (restriction.target_ref.value, str(restriction.restriction_ref.value))


def _project_restriction(
    restriction: ExecutiveActiveRestriction,
) -> ExecutiveGovernanceActiveRestrictionSummary:
    target_kind = ExecutiveGovernanceRestrictionTargetKind(restriction.target.kind.value)
    return ExecutiveGovernanceActiveRestrictionSummary(
        restriction_ref=ExecutiveGovernanceRestrictionRef(restriction.restriction_id.value),
        target_kind=target_kind,
        target_ref=ExecutiveGovernanceRestrictionTargetRef(restriction.target.value),
        applied_at=restriction.applied_at,
        source_receipt_ref=ExecutiveGovernanceRestrictionSourceReceiptRef(
            restriction.source_receipt_id.value
        ),
        policy_version=ExecutiveGovernancePolicyVersionRef(
            restriction.policy_version.value
        ),
        reason_codes=restriction.reason_codes,
        evidence_refs=restriction.evidence_refs,
    )


def project_executive_governance_current_state(
    snapshot: ExecutiveGovernanceStateSnapshot,
) -> ExecutiveGovernanceCurrentStateSummary:
    """Purely project canonical state without exposing the state source or replaying receipts."""

    if not isinstance(snapshot, ExecutiveGovernanceStateSnapshot):
        raise ExecutiveReadModelValidationError(
            "governance current-state projection requires canonical snapshot"
        )
    system_run_state = ExecutiveGovernanceSystemRunState(snapshot.system_run_state.value)
    new_trading_state = ExecutiveGovernanceNewTradingState(snapshot.new_trading_state.value)
    return ExecutiveGovernanceCurrentStateSummary(
        snapshot_ref=ExecutiveGovernanceStateSnapshotRef(snapshot.snapshot_id.value),
        state_version=ExecutiveGovernanceStateVersionRef(snapshot.state_version.value),
        observed_at=snapshot.observed_at,
        system_run_state=system_run_state,
        new_trading_state=new_trading_state,
        active_market_restrictions=tuple(
            _project_restriction(item) for item in snapshot.market_restrictions
        ),
        active_account_restrictions=tuple(
            _project_restriction(item) for item in snapshot.account_restrictions
        ),
    )
