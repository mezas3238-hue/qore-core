"""Policy-neutral protected-capital floor mechanics for CIBO GEN-C2.

GEN-C2 does not choose how much profit should be protected. It records only
capital that the GEN-C1 portfolio has already retired from deployable compound
capacity, and then tracks the strength of the protection claim.

Protection is intentionally hierarchical:

ACCOUNTING_PROTECTED -> POLICY_PROTECTED -> BROKER_GUARANTEED

A policy-protected floor is not represented as a broker guarantee. A broker
guarantee requires separate canonical evidence. Floor value can ratchet upward
through new retired lots; it cannot be reduced or made deployable by this
module. Research-only: no sizing, Risk, execution or broker authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalLot,
    CompoundCapitalState,
    CompoundProtectionClass,
)

_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ProtectedFloorEventType(StrEnum):
    ADMIT_RETIRED_CAPITAL = "ADMIT_RETIRED_CAPITAL"
    UPGRADE_TO_POLICY_PROTECTED = "UPGRADE_TO_POLICY_PROTECTED"
    UPGRADE_TO_BROKER_GUARANTEED = "UPGRADE_TO_BROKER_GUARANTEED"


@dataclass(frozen=True, slots=True)
class ProtectedFloorTranche:
    tranche_id: str
    account_identity: CiboAccountCapitalIdentity
    source_compound_lot_id: str
    amount_usd: Decimal
    protection_class: CompoundProtectionClass
    admitted_at: datetime
    policy_id: str | None = None
    policy_sha256: str | None = None
    broker_guarantee_evidence_id: str | None = None
    broker_guarantee_sha256: str | None = None
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if not self.tranche_id or not self.source_compound_lot_id:
            raise CiboCompoundCapitalError(
                "protected floor tranche identity/source is required"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "protected floor account identity is invalid"
            )
        if (
            not isinstance(self.amount_usd, Decimal)
            or not self.amount_usd.is_finite()
            or self.amount_usd <= 0
        ):
            raise CiboCompoundCapitalError(
                "protected floor amount must be finite positive Decimal"
            )
        if type(self.protection_class) is not CompoundProtectionClass:
            raise CiboCompoundCapitalError(
                "protected floor classification is invalid"
            )
        _aware(self.admitted_at, "floor admitted_at")
        if type(self.runtime_authority) is not bool:
            raise CiboCompoundCapitalError(
                "protected floor runtime_authority must be bool"
            )
        if self.runtime_authority:
            raise CiboCompoundCapitalError(
                "GEN-C2 protected floor has no runtime authority"
            )

        if self.protection_class is CompoundProtectionClass.ACCOUNTING_PROTECTED:
            if any(
                value is not None
                for value in (
                    self.policy_id,
                    self.policy_sha256,
                    self.broker_guarantee_evidence_id,
                    self.broker_guarantee_sha256,
                )
            ):
                raise CiboCompoundCapitalError(
                    "accounting-protected floor cannot claim policy/broker evidence"
                )
            return

        if not self.policy_id:
            raise CiboCompoundCapitalError(
                "policy-protected floor requires policy identity"
            )
        _sha(self.policy_sha256, "policy_sha256")

        if self.protection_class is CompoundProtectionClass.POLICY_PROTECTED:
            if (
                self.broker_guarantee_evidence_id is not None
                or self.broker_guarantee_sha256 is not None
            ):
                raise CiboCompoundCapitalError(
                    "policy-protected floor cannot claim broker guarantee"
                )
            return

        if not self.broker_guarantee_evidence_id:
            raise CiboCompoundCapitalError(
                "broker-guaranteed floor requires evidence identity"
            )
        _sha(
            self.broker_guarantee_sha256,
            "broker_guarantee_sha256",
        )


@dataclass(frozen=True, slots=True)
class ProtectedFloorEvent:
    event_id: str
    event_type: ProtectedFloorEventType
    tranche_id: str
    occurred_at: datetime
    floor_before_usd: Decimal
    floor_after_usd: Decimal
    from_class: CompoundProtectionClass | None
    to_class: CompoundProtectionClass
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.event_id or not self.tranche_id or not self.evidence_ref:
            raise CiboCompoundCapitalError(
                "protected floor event identity/evidence is required"
            )
        if type(self.event_type) is not ProtectedFloorEventType:
            raise CiboCompoundCapitalError(
                "protected floor event type is invalid"
            )
        _aware(self.occurred_at, "floor event occurred_at")
        for name in ("floor_before_usd", "floor_after_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCompoundCapitalError(
                    f"protected floor {name} must be finite non-negative"
                )
        if self.floor_after_usd < self.floor_before_usd:
            raise CiboCompoundCapitalError(
                "protected capital floor cannot ratchet downward"
            )
        if type(self.to_class) is not CompoundProtectionClass:
            raise CiboCompoundCapitalError(
                "protected floor target class is invalid"
            )
        if self.from_class is not None and type(
            self.from_class
        ) is not CompoundProtectionClass:
            raise CiboCompoundCapitalError(
                "protected floor source class is invalid"
            )


@dataclass(frozen=True, slots=True)
class ProtectedCapitalFloorLedger:
    account_identity: CiboAccountCapitalIdentity
    tranches: tuple[ProtectedFloorTranche, ...] = ()
    events: tuple[ProtectedFloorEvent, ...] = ()
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "protected floor ledger account identity is invalid"
            )
        if type(self.runtime_authority) is not bool:
            raise CiboCompoundCapitalError(
                "protected floor ledger runtime_authority must be bool"
            )
        if self.runtime_authority:
            raise CiboCompoundCapitalError(
                "GEN-C2 floor ledger has no runtime authority"
            )
        tranche_ids = tuple(item.tranche_id for item in self.tranches)
        source_ids = tuple(
            item.source_compound_lot_id for item in self.tranches
        )
        event_ids = tuple(item.event_id for item in self.events)
        if len(tranche_ids) != len(set(tranche_ids)):
            raise CiboCompoundCapitalError(
                "protected floor tranche ids must be unique"
            )
        if len(source_ids) != len(set(source_ids)):
            raise CiboCompoundCapitalError(
                "retired compound lot cannot fund floor twice"
            )
        if len(event_ids) != len(set(event_ids)):
            raise CiboCompoundCapitalError(
                "protected floor event ids must be unique"
            )
        if any(
            item.account_identity != self.account_identity
            for item in self.tranches
        ):
            raise CiboCompoundCapitalError(
                "protected floor cannot mix account domains"
            )

    @property
    def total_floor_usd(self) -> Decimal:
        return sum(
            (item.amount_usd for item in self.tranches),
            Decimal(0),
        )

    @property
    def policy_protected_floor_usd(self) -> Decimal:
        return sum(
            (
                item.amount_usd
                for item in self.tranches
                if item.protection_class
                in {
                    CompoundProtectionClass.POLICY_PROTECTED,
                    CompoundProtectionClass.BROKER_GUARANTEED,
                }
            ),
            Decimal(0),
        )

    @property
    def broker_guaranteed_floor_usd(self) -> Decimal:
        return sum(
            (
                item.amount_usd
                for item in self.tranches
                if item.protection_class
                is CompoundProtectionClass.BROKER_GUARANTEED
            ),
            Decimal(0),
        )

    def tranche(self, tranche_id: str) -> ProtectedFloorTranche:
        rows = tuple(
            item for item in self.tranches if item.tranche_id == tranche_id
        )
        if len(rows) != 1:
            raise CiboCompoundCapitalError(
                "protected floor tranche not found"
            )
        return rows[0]

    def admit_retired_lot(
        self,
        lot: CompoundCapitalLot,
        *,
        tranche_id: str,
        event_id: str,
        admitted_at: datetime,
    ) -> ProtectedCapitalFloorLedger:
        """Admit one already non-deployable compound lot into the floor."""

        if not isinstance(lot, CompoundCapitalLot):
            raise CiboCompoundCapitalError(
                "protected floor requires canonical compound lot"
            )
        if lot.account_identity != self.account_identity:
            raise CiboCompoundCapitalError(
                "protected floor cannot cross account domains"
            )
        if (
            lot.state
            is not CompoundCapitalState.RETIRED_TO_PROTECTED_FLOOR
        ):
            raise CiboCompoundCapitalError(
                "protected floor source must already be retired from deployment"
            )
        _aware(admitted_at, "floor admitted_at")
        if admitted_at < lot.created_at:
            raise CiboCompoundCapitalError(
                "protected floor admission cannot predate retired lot"
            )
        if any(
            item.source_compound_lot_id == lot.lot_id
            for item in self.tranches
        ):
            raise CiboCompoundCapitalError(
                "retired compound lot already admitted to floor"
            )
        self._new_tranche_id(tranche_id)
        self._new_event_id(event_id)

        before = self.total_floor_usd
        tranche = ProtectedFloorTranche(
            tranche_id=tranche_id,
            account_identity=self.account_identity,
            source_compound_lot_id=lot.lot_id,
            amount_usd=lot.amount_usd,
            protection_class=(
                CompoundProtectionClass.ACCOUNTING_PROTECTED
            ),
            admitted_at=admitted_at,
            runtime_authority=False,
        )
        after = before + lot.amount_usd
        event = ProtectedFloorEvent(
            event_id=event_id,
            event_type=ProtectedFloorEventType.ADMIT_RETIRED_CAPITAL,
            tranche_id=tranche_id,
            occurred_at=admitted_at,
            floor_before_usd=before,
            floor_after_usd=after,
            from_class=None,
            to_class=CompoundProtectionClass.ACCOUNTING_PROTECTED,
            evidence_ref=lot.lot_id,
        )
        return ProtectedCapitalFloorLedger(
            account_identity=self.account_identity,
            tranches=self.tranches + (tranche,),
            events=self.events + (event,),
            runtime_authority=False,
        )

    def upgrade_to_policy_protected(
        self,
        *,
        tranche_id: str,
        event_id: str,
        occurred_at: datetime,
        policy_id: str,
        policy_sha256: str,
    ) -> ProtectedCapitalFloorLedger:
        target = self.tranche(tranche_id)
        if (
            target.protection_class
            is not CompoundProtectionClass.ACCOUNTING_PROTECTED
        ):
            raise CiboCompoundCapitalError(
                "policy protection requires accounting-protected source"
            )
        if not policy_id:
            raise CiboCompoundCapitalError(
                "policy protection requires policy identity"
            )
        _sha(policy_sha256, "policy_sha256")
        _aware(occurred_at, "policy protection occurred_at")
        if occurred_at < target.admitted_at:
            raise CiboCompoundCapitalError(
                "policy protection cannot predate floor admission"
            )
        self._new_event_id(event_id)
        upgraded = replace(
            target,
            protection_class=CompoundProtectionClass.POLICY_PROTECTED,
            policy_id=policy_id,
            policy_sha256=policy_sha256,
        )
        event = ProtectedFloorEvent(
            event_id=event_id,
            event_type=(
                ProtectedFloorEventType.UPGRADE_TO_POLICY_PROTECTED
            ),
            tranche_id=tranche_id,
            occurred_at=occurred_at,
            floor_before_usd=self.total_floor_usd,
            floor_after_usd=self.total_floor_usd,
            from_class=target.protection_class,
            to_class=upgraded.protection_class,
            evidence_ref=policy_sha256,
        )
        return self._replace_tranche(upgraded, event)

    def upgrade_to_broker_guaranteed(
        self,
        *,
        tranche_id: str,
        event_id: str,
        occurred_at: datetime,
        broker_guarantee_evidence_id: str,
        broker_guarantee_sha256: str,
    ) -> ProtectedCapitalFloorLedger:
        target = self.tranche(tranche_id)
        if (
            target.protection_class
            is not CompoundProtectionClass.POLICY_PROTECTED
        ):
            raise CiboCompoundCapitalError(
                "broker guarantee requires policy-protected source"
            )
        if not broker_guarantee_evidence_id:
            raise CiboCompoundCapitalError(
                "broker guarantee requires evidence identity"
            )
        _sha(
            broker_guarantee_sha256,
            "broker_guarantee_sha256",
        )
        _aware(occurred_at, "broker guarantee occurred_at")
        if occurred_at < target.admitted_at:
            raise CiboCompoundCapitalError(
                "broker guarantee cannot predate floor admission"
            )
        self._new_event_id(event_id)
        upgraded = replace(
            target,
            protection_class=(
                CompoundProtectionClass.BROKER_GUARANTEED
            ),
            broker_guarantee_evidence_id=(
                broker_guarantee_evidence_id
            ),
            broker_guarantee_sha256=broker_guarantee_sha256,
        )
        event = ProtectedFloorEvent(
            event_id=event_id,
            event_type=(
                ProtectedFloorEventType.UPGRADE_TO_BROKER_GUARANTEED
            ),
            tranche_id=tranche_id,
            occurred_at=occurred_at,
            floor_before_usd=self.total_floor_usd,
            floor_after_usd=self.total_floor_usd,
            from_class=target.protection_class,
            to_class=upgraded.protection_class,
            evidence_ref=broker_guarantee_sha256,
        )
        return self._replace_tranche(upgraded, event)

    def _replace_tranche(
        self,
        upgraded: ProtectedFloorTranche,
        event: ProtectedFloorEvent,
    ) -> ProtectedCapitalFloorLedger:
        return ProtectedCapitalFloorLedger(
            account_identity=self.account_identity,
            tranches=tuple(
                upgraded if item.tranche_id == upgraded.tranche_id else item
                for item in self.tranches
            ),
            events=self.events + (event,),
            runtime_authority=False,
        )

    def _new_tranche_id(self, tranche_id: str) -> None:
        if not tranche_id:
            raise CiboCompoundCapitalError(
                "protected floor tranche id is required"
            )
        if any(item.tranche_id == tranche_id for item in self.tranches):
            raise CiboCompoundCapitalError(
                "protected floor tranche id already exists"
            )

    def _new_event_id(self, event_id: str) -> None:
        if not event_id:
            raise CiboCompoundCapitalError(
                "protected floor event id is required"
            )
        if any(item.event_id == event_id for item in self.events):
            raise CiboCompoundCapitalError(
                "protected floor event id already exists"
            )


def _sha(value: str | None, name: str) -> None:
    if (
        not isinstance(value, str)
        or _SHA256_RE.fullmatch(value) is None
    ):
        raise CiboCompoundCapitalError(
            f"protected floor {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"protected floor {name} must be timezone-aware"
        )
