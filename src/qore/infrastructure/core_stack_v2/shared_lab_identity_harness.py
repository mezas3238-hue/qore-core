"""Canonical identity adversarial harness."""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.core_stack_v2.shared_lab_data_reality import CanonicalIdentity, DataFailure, resolve_identity


@dataclass(frozen=True, slots=True)
class IdentityRealityReceipt:
    provider_symbol: str
    canonical_economic_id: str | None
    failures: tuple[DataFailure, ...]

    @property
    def passed(self) -> bool:
        return self.canonical_economic_id is not None and not self.failures


def assess_identity(symbol: str, asset_class: str, aliases: dict[str, tuple[CanonicalIdentity, ...]]) -> IdentityRealityReceipt:
    identity, failures = resolve_identity(symbol, aliases, asset_class)
    return IdentityRealityReceipt(symbol, None if identity is None else identity.economic_id, failures)


def validate_contract_identity(identity: CanonicalIdentity, *, requires_maturity: bool, requires_venue: bool, requires_multiplier: bool) -> bool:
    if requires_maturity and not identity.maturity:
        return False
    if requires_venue and not identity.venue:
        return False
    if requires_multiplier and identity.multiplier is None:
        return False
    return True
