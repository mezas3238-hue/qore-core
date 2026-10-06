"""Provider/account instrument capability registry for CIBO.

This registry supports T02/T03/T11/T16/T17 financial-expression research.
It never infers provider capability from platform names and never treats
missing evidence as support.

Research-only: no sizing, Risk, execution, broker, LIVE or capital authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError


class InstrumentCapability(StrEnum):
    CFD = "CFD"
    FUTURE = "FUTURE"
    MICRO_FUTURE = "MICRO_FUTURE"
    OPTION = "OPTION"
    DEFINED_RISK_SPREAD = "DEFINED_RISK_SPREAD"
    HEDGE = "HEDGE"
    NETTING = "NETTING"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    PYRAMID = "PYRAMID"


class CapabilityStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONDITIONALLY_SUPPORTED = "CONDITIONALLY_SUPPORTED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"instrument capability {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCompoundCapitalError(
            f"instrument capability {name} must be canonical SHA-256"
        )


def _account_payload(
    identity: CiboAccountCapitalIdentity,
) -> dict[str, object]:
    return {
        "provider_key": identity.provider_key,
        "account_ref": identity.account_ref,
        "environment": identity.environment.value,
        "provider_program": identity.provider_program,
    }


@dataclass(frozen=True, slots=True)
class ProviderCapabilityEvidence:
    evidence_id: str
    account_identity: CiboAccountCapitalIdentity
    capability: InstrumentCapability
    status: CapabilityStatus
    observed_at: datetime
    produced_at: datetime
    source: str
    source_ref: str
    evidence_sha256: str
    policy_version: str
    qore_symbol: str | None = None
    provider_symbol: str | None = None
    conditions: tuple[str, ...] = ()
    expires_at: datetime | None = None
    provider_verified: bool = False
    outcome_present: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.source or not self.source_ref:
            raise CiboCompoundCapitalError(
                "instrument capability evidence identity/source is required"
            )
        if not self.policy_version:
            raise CiboCompoundCapitalError(
                "instrument capability policy_version is required"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "instrument capability account identity is invalid"
            )
        if type(self.capability) is not InstrumentCapability:
            raise CiboCompoundCapitalError(
                "instrument capability kind is invalid"
            )
        if type(self.status) is not CapabilityStatus:
            raise CiboCompoundCapitalError(
                "instrument capability status is invalid"
            )
        _aware(self.observed_at, "observed_at")
        _aware(self.produced_at, "produced_at")
        if self.produced_at < self.observed_at:
            raise CiboCompoundCapitalError(
                "instrument capability cannot be produced before observation"
            )
        if self.expires_at is not None:
            _aware(self.expires_at, "expires_at")
            if self.expires_at <= self.observed_at:
                raise CiboCompoundCapitalError(
                    "instrument capability expiry must follow observation"
                )
        _sha(self.evidence_sha256, "evidence_sha256")
        if (self.qore_symbol is None) != (self.provider_symbol is None):
            raise CiboCompoundCapitalError(
                "instrument capability symbol binding must be complete"
            )
        if self.qore_symbol is not None and (
            not self.qore_symbol.strip()
            or self.provider_symbol is None
            or not self.provider_symbol.strip()
        ):
            raise CiboCompoundCapitalError(
                "instrument capability symbols cannot be blank"
            )
        if len(self.conditions) != len(set(self.conditions)):
            raise CiboCompoundCapitalError(
                "instrument capability conditions must be unique"
            )
        if any(not isinstance(item, str) or not item.strip() for item in self.conditions):
            raise CiboCompoundCapitalError(
                "instrument capability conditions are invalid"
            )
        for name in (
            "provider_verified",
            "outcome_present",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"instrument capability {name} must be bool"
                )
        if self.status in {
            CapabilityStatus.SUPPORTED,
            CapabilityStatus.CONDITIONALLY_SUPPORTED,
            CapabilityStatus.UNAVAILABLE,
        } and not self.provider_verified:
            raise CiboCompoundCapitalError(
                "non-UNKNOWN capability status requires provider-verified evidence"
            )
        if (
            self.status is CapabilityStatus.CONDITIONALLY_SUPPORTED
            and not self.conditions
        ):
            raise CiboCompoundCapitalError(
                "conditional capability requires explicit conditions"
            )
        if (
            self.status is CapabilityStatus.SUPPORTED
            and self.conditions
        ):
            raise CiboCompoundCapitalError(
                "unconditional SUPPORTED capability cannot carry conditions"
            )
        if (
            self.status is CapabilityStatus.UNKNOWN
            and self.provider_verified
        ):
            raise CiboCompoundCapitalError(
                "UNKNOWN capability cannot claim provider verification"
            )
        if self.outcome_present or self.productive_authority:
            raise CiboCompoundCapitalError(
                "instrument capability evidence cannot carry outcome/authority"
            )

    @property
    def symbol_key(self) -> tuple[str, str] | None:
        if self.qore_symbol is None or self.provider_symbol is None:
            return None
        return (self.qore_symbol, self.provider_symbol)

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["account_identity"] = _account_payload(self.account_identity)
        payload["capability"] = self.capability.value
        payload["status"] = self.status.value
        payload["observed_at"] = self.observed_at.isoformat()
        payload["produced_at"] = self.produced_at.isoformat()
        payload["expires_at"] = (
            None if self.expires_at is None else self.expires_at.isoformat()
        )
        payload["conditions"] = list(self.conditions)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ProviderInstrumentCapabilityRegistry:
    account_identity: CiboAccountCapitalIdentity
    entries: tuple[ProviderCapabilityEvidence, ...]
    captured_at: datetime
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCompoundCapitalError(
                "instrument capability registry account identity is invalid"
            )
        _aware(self.captured_at, "captured_at")
        if any(
            not isinstance(item, ProviderCapabilityEvidence)
            for item in self.entries
        ):
            raise CiboCompoundCapitalError(
                "instrument capability registry entries are invalid"
            )
        if any(
            item.account_identity != self.account_identity
            for item in self.entries
        ):
            raise CiboCompoundCapitalError(
                "instrument capability registry cannot mix account domains"
            )
        keys = tuple(
            (item.capability, item.symbol_key)
            for item in self.entries
        )
        if len(keys) != len(set(keys)):
            raise CiboCompoundCapitalError(
                "instrument capability registry duplicate capability scope"
            )
        if any(item.produced_at > self.captured_at for item in self.entries):
            raise CiboCompoundCapitalError(
                "instrument capability registry cannot include future evidence"
            )
        if type(self.runtime_authority) is not bool:
            raise CiboCompoundCapitalError(
                "instrument capability runtime_authority must be bool"
            )
        if self.runtime_authority:
            raise CiboCompoundCapitalError(
                "instrument capability registry is research evidence only"
            )

    def resolve(
        self,
        *,
        capability: InstrumentCapability,
        at: datetime,
        qore_symbol: str | None = None,
        provider_symbol: str | None = None,
    ) -> ProviderCapabilityEvidence | None:
        _aware(at, "resolve at")
        if type(capability) is not InstrumentCapability:
            raise CiboCompoundCapitalError(
                "instrument capability resolve kind is invalid"
            )
        if (qore_symbol is None) != (provider_symbol is None):
            raise CiboCompoundCapitalError(
                "instrument capability resolve symbol binding incomplete"
            )
        symbol_key = (
            None
            if qore_symbol is None or provider_symbol is None
            else (qore_symbol, provider_symbol)
        )
        scoped = tuple(
            item
            for item in self.entries
            if item.capability is capability and item.symbol_key == symbol_key
        )
        if not scoped and symbol_key is not None:
            scoped = tuple(
                item
                for item in self.entries
                if item.capability is capability and item.symbol_key is None
            )
        if len(scoped) > 1:
            raise CiboCompoundCapitalError(
                "instrument capability resolve is ambiguous"
            )
        if not scoped:
            return None
        entry = scoped[0]
        if entry.observed_at > at:
            return None
        if entry.expires_at is not None and at >= entry.expires_at:
            return None
        return entry

    def status(
        self,
        *,
        capability: InstrumentCapability,
        at: datetime,
        qore_symbol: str | None = None,
        provider_symbol: str | None = None,
    ) -> CapabilityStatus:
        entry = self.resolve(
            capability=capability,
            at=at,
            qore_symbol=qore_symbol,
            provider_symbol=provider_symbol,
        )
        return CapabilityStatus.UNKNOWN if entry is None else entry.status

    def fingerprint(self) -> str:
        payload = {
            "account_identity": _account_payload(self.account_identity),
            "captured_at": self.captured_at.isoformat(),
            "entries": [
                {
                    "evidence_sha256": item.fingerprint(),
                    "capability": item.capability.value,
                    "symbol_key": (
                        None if item.symbol_key is None else list(item.symbol_key)
                    ),
                }
                for item in sorted(
                    self.entries,
                    key=lambda item: (
                        item.capability.value,
                        "" if item.qore_symbol is None else item.qore_symbol,
                        "" if item.provider_symbol is None else item.provider_symbol,
                    ),
                )
            ],
            "runtime_authority": self.runtime_authority,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()
