"""Architect B5 governed dispositions for agricultural and commodity worlds."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class B5AssetWorldError(ValueError):
    """Asset-world evidence is inconsistent or overclaims authority."""


class AgriculturalWorldDisposition(StrEnum):
    KNOWN_BLINDSPOT = "KNOWN_BLINDSPOT"
    PROVIDER_CANDIDATES_REQUIRE_REVIEW = "PROVIDER_CANDIDATES_REQUIRE_REVIEW"


class CommodityWorldDisposition(StrEnum):
    GOVERNED_UNKNOWN = "GOVERNED_UNKNOWN"
    AUTHORITY_EVIDENCE_READY = "AUTHORITY_EVIDENCE_READY"


@dataclass(frozen=True, slots=True)
class AgriculturalWorldReceipt:
    authorized_provider_count: int
    agricultural_candidate_count: int
    soft_candidate_count: int
    livestock_candidate_count: int
    secondary_provider_owner_authorized: bool
    secondary_provider_scientifically_admitted: bool
    proxy_agriculture_used: bool
    disposition: AgriculturalWorldDisposition
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    execution_authority: bool = False
    productive_authority: bool = False

    def fingerprint(self) -> str:
        return _fingerprint(asdict(self))


@dataclass(frozen=True, slots=True)
class CommodityWorldReceipt:
    metal_reference_object_count: int
    metal_provider_neutral_identity_count: int
    energy_reference_object_count: int
    energy_provider_neutral_identity_count: int
    dated_gc_contract_count: int
    expired_gc_contract_count: int
    current_front_contract_verified_count: int
    roll_semantics_verified: bool
    continuous_series_verified: bool
    venue_identity_verified: bool
    disposition: CommodityWorldDisposition
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    inference_used: bool = False
    execution_authority: bool = False
    productive_authority: bool = False

    def fingerprint(self) -> str:
        return _fingerprint(asdict(self))


def _fingerprint(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _canonical_refs(refs: tuple[str, ...]) -> None:
    if not refs or refs != tuple(sorted(set(refs))):
        raise B5AssetWorldError("evidence_refs must be non-empty, unique and canonical")


def assess_agricultural_world(
    *,
    authorized_provider_count: int,
    agricultural_candidate_count: int,
    soft_candidate_count: int,
    livestock_candidate_count: int,
    secondary_provider_owner_authorized: bool,
    secondary_provider_scientifically_admitted: bool,
    proxy_agriculture_used: bool,
    evidence_refs: tuple[str, ...],
) -> AgriculturalWorldReceipt:
    """Preserve B-14 as an explicit blindspot when no real source exists."""

    _canonical_refs(evidence_refs)
    counts = (
        authorized_provider_count,
        agricultural_candidate_count,
        soft_candidate_count,
        livestock_candidate_count,
    )
    if any(type(value) is not int or value < 0 for value in counts):
        raise B5AssetWorldError("agricultural counts must be non-negative integers")
    if proxy_agriculture_used:
        raise B5AssetWorldError("agricultural proxy fabrication is forbidden")
    if secondary_provider_scientifically_admitted and not secondary_provider_owner_authorized:
        raise B5AssetWorldError(
            "secondary provider cannot be scientifically admitted before Owner authorization"
        )

    candidates = (
        agricultural_candidate_count + soft_candidate_count + livestock_candidate_count
    )
    blockers: list[str] = []
    if candidates == 0:
        blockers.append("ZERO_AGRICULTURAL_SOFT_LIVESTOCK_CANDIDATES")
    if not secondary_provider_owner_authorized:
        blockers.append("NO_OWNER_AUTHORIZED_SECONDARY_PROVIDER")
    if not secondary_provider_scientifically_admitted:
        blockers.append("NO_SCIENTIFICALLY_ADMITTED_SECONDARY_PROVIDER")

    disposition = (
        AgriculturalWorldDisposition.KNOWN_BLINDSPOT
        if candidates == 0
        else AgriculturalWorldDisposition.PROVIDER_CANDIDATES_REQUIRE_REVIEW
    )
    return AgriculturalWorldReceipt(
        authorized_provider_count=authorized_provider_count,
        agricultural_candidate_count=agricultural_candidate_count,
        soft_candidate_count=soft_candidate_count,
        livestock_candidate_count=livestock_candidate_count,
        secondary_provider_owner_authorized=secondary_provider_owner_authorized,
        secondary_provider_scientifically_admitted=secondary_provider_scientifically_admitted,
        proxy_agriculture_used=False,
        disposition=disposition,
        blocker_codes=tuple(sorted(set(blockers))),
        evidence_refs=evidence_refs,
    )


def assess_commodity_world(
    *,
    metal_reference_object_count: int,
    metal_provider_neutral_identity_count: int,
    energy_reference_object_count: int,
    energy_provider_neutral_identity_count: int,
    dated_gc_contract_count: int,
    expired_gc_contract_count: int,
    current_front_contract_verified_count: int,
    roll_semantics_verified: bool,
    continuous_series_verified: bool,
    venue_identity_verified: bool,
    evidence_refs: tuple[str, ...],
    inference_used: bool = False,
) -> CommodityWorldReceipt:
    """Report B-15 truth without guessing product/venue/front/roll/continuous."""

    _canonical_refs(evidence_refs)
    counts = (
        metal_reference_object_count,
        metal_provider_neutral_identity_count,
        energy_reference_object_count,
        energy_provider_neutral_identity_count,
        dated_gc_contract_count,
        expired_gc_contract_count,
        current_front_contract_verified_count,
    )
    if any(type(value) is not int or value < 0 for value in counts):
        raise B5AssetWorldError("commodity counts must be non-negative integers")
    if metal_provider_neutral_identity_count > metal_reference_object_count:
        raise B5AssetWorldError("metal identity count exceeds observed references")
    if energy_provider_neutral_identity_count > energy_reference_object_count:
        raise B5AssetWorldError("energy identity count exceeds observed references")
    if expired_gc_contract_count > dated_gc_contract_count:
        raise B5AssetWorldError("expired GC count exceeds observed contracts")
    if current_front_contract_verified_count > dated_gc_contract_count:
        raise B5AssetWorldError("front count exceeds observed GC contracts")
    if inference_used:
        raise B5AssetWorldError(
            "commodity identity/front/roll/continuous inference is forbidden"
        )

    blockers: list[str] = []
    if metal_provider_neutral_identity_count < metal_reference_object_count:
        blockers.append("METALS_PROVIDER_NEUTRAL_IDENTITY_UNRESOLVED")
    if energy_provider_neutral_identity_count < energy_reference_object_count:
        blockers.append("ENERGY_PROVIDER_NEUTRAL_IDENTITY_UNRESOLVED")
    if current_front_contract_verified_count == 0:
        blockers.append("CURRENT_FRONT_CONTRACT_UNVERIFIED")
    if not venue_identity_verified:
        blockers.append("VENUE_IDENTITY_UNVERIFIED")
    if not roll_semantics_verified:
        blockers.append("ROLL_SEMANTICS_UNVERIFIED")
    if not continuous_series_verified:
        blockers.append("CONTINUOUS_SERIES_UNVERIFIED")
    if dated_gc_contract_count and expired_gc_contract_count == dated_gc_contract_count:
        blockers.append("OBSERVED_GC_SET_EXPIRED")

    disposition = (
        CommodityWorldDisposition.AUTHORITY_EVIDENCE_READY
        if not blockers
        else CommodityWorldDisposition.GOVERNED_UNKNOWN
    )
    return CommodityWorldReceipt(
        metal_reference_object_count=metal_reference_object_count,
        metal_provider_neutral_identity_count=metal_provider_neutral_identity_count,
        energy_reference_object_count=energy_reference_object_count,
        energy_provider_neutral_identity_count=energy_provider_neutral_identity_count,
        dated_gc_contract_count=dated_gc_contract_count,
        expired_gc_contract_count=expired_gc_contract_count,
        current_front_contract_verified_count=current_front_contract_verified_count,
        roll_semantics_verified=roll_semantics_verified,
        continuous_series_verified=continuous_series_verified,
        venue_identity_verified=venue_identity_verified,
        disposition=disposition,
        blocker_codes=tuple(sorted(set(blockers))),
        evidence_refs=evidence_refs,
        inference_used=False,
    )
