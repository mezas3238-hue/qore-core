"""Research-only protected-original-base overlay for CIBO Track B.

The overlay binds an exact CapitalSourceLedger snapshot and classifies part of
available ORIGINAL_BASE_CAPITAL without mutating the frozen current-CIBO/V3
capital ledger. It exists to keep PROTECTED_BASE distinct from protected profit,
economic reserves and broker guarantees.

No runtime, sizing, Risk, execution, LIVE or real-capital authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger


class ProtectedBaseClass(StrEnum):
    ACCOUNTING_PROTECTED = "ACCOUNTING_PROTECTED"
    ECONOMICALLY_RESERVED = "ECONOMICALLY_RESERVED"
    POLICY_PROTECTED = "POLICY_PROTECTED"
    BROKER_GUARANTEED = "BROKER_GUARANTEED"


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"protected base {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"protected base {name} must be canonical SHA-256"
        )


def capital_source_ledger_sha256(ledger: CapitalSourceLedger) -> str:
    if not isinstance(ledger, CapitalSourceLedger):
        raise CiboCapitalManagementError(
            "protected base requires canonical CapitalSourceLedger"
        )
    payload = {
        "accounts": [
            {
                "source_id": item.source_id,
                "source": item.source.value,
                "proven_amount_usd": format(item.proven_amount_usd, "f"),
                "reserved_usd": format(item.reserved_usd, "f"),
                "deployed_usd": format(item.deployed_usd, "f"),
                "consumed_usd": format(item.consumed_usd, "f"),
                "cumulative_released_usd": format(
                    item.cumulative_released_usd,
                    "f",
                ),
            }
            for item in sorted(
                ledger.accounts,
                key=lambda row: row.source_id,
            )
        ],
        "reservations": [
            {
                "reservation_id": item.reservation_id,
                "source_id": item.source_id,
                "amount_usd": format(item.amount_usd, "f"),
                "state": item.state.value,
                "returned_capacity_usd": format(
                    item.returned_capacity_usd,
                    "f",
                ),
                "consumed_capacity_usd": format(
                    item.consumed_capacity_usd,
                    "f",
                ),
            }
            for item in sorted(
                ledger.reservations,
                key=lambda row: row.reservation_id,
            )
        ],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ProtectedBaseSnapshot:
    account_identity: CiboAccountCapitalIdentity
    captured_at: datetime
    source_id: str
    source_ledger_sha256: str
    original_base_proven_usd: Decimal
    original_base_available_usd: Decimal
    protected_base_usd: Decimal
    protection_class: ProtectedBaseClass
    evidence_sha256: str
    policy_id: str | None = None
    policy_sha256: str | None = None
    broker_guarantee_evidence_sha256: str | None = None
    provider_guaranteed: bool = False
    source_ledger_mutated: bool = False
    runtime_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCapitalManagementError(
                "protected base account identity is invalid"
            )
        if not self.source_id:
            raise CiboCapitalManagementError(
                "protected base source_id is required"
            )
        _aware(self.captured_at, "captured_at")
        _sha(self.source_ledger_sha256, "source_ledger_sha256")
        _sha(self.evidence_sha256, "evidence_sha256")
        for name in (
            "original_base_proven_usd",
            "original_base_available_usd",
            "protected_base_usd",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"protected base {name} must be finite non-negative"
                )
        if self.original_base_proven_usd <= 0:
            raise CiboCapitalManagementError(
                "protected base requires positive original capital"
            )
        if self.protected_base_usd > self.original_base_available_usd:
            raise CiboCapitalManagementError(
                "protected base exceeds available original base"
            )
        if type(self.protection_class) is not ProtectedBaseClass:
            raise CiboCapitalManagementError(
                "protected base class is invalid"
            )
        for name in (
            "provider_guaranteed",
            "source_ledger_mutated",
            "runtime_authority",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"protected base {name} must be bool"
                )
        if self.source_ledger_mutated:
            raise CiboCapitalManagementError(
                "protected base overlay must not mutate source ledger"
            )
        if any(
            (
                self.runtime_authority,
                self.sizing_authority,
                self.risk_authority,
                self.execution_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "protected base overlay has no productive authority"
            )

        if self.protection_class is ProtectedBaseClass.POLICY_PROTECTED:
            if not self.policy_id or self.policy_sha256 is None:
                raise CiboCapitalManagementError(
                    "policy-protected base requires policy evidence"
                )
            _sha(self.policy_sha256, "policy_sha256")
        elif self.protection_class is ProtectedBaseClass.BROKER_GUARANTEED:
            if (
                not self.policy_id
                or self.policy_sha256 is None
                or self.broker_guarantee_evidence_sha256 is None
                or not self.provider_guaranteed
            ):
                raise CiboCapitalManagementError(
                    "broker-guaranteed base requires policy/provider evidence"
                )
            _sha(self.policy_sha256, "policy_sha256")
            _sha(
                self.broker_guarantee_evidence_sha256,
                "broker_guarantee_evidence_sha256",
            )
        else:
            if self.provider_guaranteed:
                raise CiboCapitalManagementError(
                    "non-broker protected base cannot claim provider guarantee"
                )
            if self.broker_guarantee_evidence_sha256 is not None:
                raise CiboCapitalManagementError(
                    "non-broker protected base cannot carry guarantee evidence"
                )

    @property
    def unprotected_available_base_usd(self) -> Decimal:
        return self.original_base_available_usd - self.protected_base_usd

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["account_identity"] = {
            "provider_key": self.account_identity.provider_key,
            "account_ref": self.account_identity.account_ref,
            "environment": self.account_identity.environment.value,
            "provider_program": self.account_identity.provider_program,
        }
        payload["captured_at"] = self.captured_at.isoformat()
        payload["protection_class"] = self.protection_class.value
        for name in (
            "original_base_proven_usd",
            "original_base_available_usd",
            "protected_base_usd",
        ):
            payload[name] = format(getattr(self, name), "f")
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def build_protected_base_snapshot(
    *,
    account_identity: CiboAccountCapitalIdentity,
    ledger: CapitalSourceLedger,
    captured_at: datetime,
    source_id: str,
    protected_base_usd: Decimal,
    protection_class: ProtectedBaseClass,
    evidence_sha256: str,
    policy_id: str | None = None,
    policy_sha256: str | None = None,
    broker_guarantee_evidence_sha256: str | None = None,
    provider_guaranteed: bool = False,
) -> ProtectedBaseSnapshot:
    """Create a non-authoritative GEN-0 protection view from exact source truth."""

    if not isinstance(ledger, CapitalSourceLedger):
        raise CiboCapitalManagementError(
            "protected base requires canonical source ledger"
        )
    _aware(captured_at, "captured_at")
    rows = tuple(
        item for item in ledger.accounts if item.source_id == source_id
    )
    if len(rows) != 1:
        raise CiboCapitalManagementError(
            "protected base source account not found exactly once"
        )
    source = rows[0]
    if source.source is not CapitalSource.ORIGINAL_BASE_CAPITAL:
        raise CiboCapitalManagementError(
            "protected base may only classify ORIGINAL_BASE_CAPITAL"
        )
    return ProtectedBaseSnapshot(
        account_identity=account_identity,
        captured_at=captured_at,
        source_id=source_id,
        source_ledger_sha256=capital_source_ledger_sha256(ledger),
        original_base_proven_usd=source.proven_amount_usd,
        original_base_available_usd=source.available_usd,
        protected_base_usd=protected_base_usd,
        protection_class=protection_class,
        evidence_sha256=evidence_sha256,
        policy_id=policy_id,
        policy_sha256=policy_sha256,
        broker_guarantee_evidence_sha256=(
            broker_guarantee_evidence_sha256
        ),
        provider_guaranteed=provider_guaranteed,
        source_ledger_mutated=False,
        runtime_authority=False,
        sizing_authority=False,
        risk_authority=False,
        execution_authority=False,
    )
