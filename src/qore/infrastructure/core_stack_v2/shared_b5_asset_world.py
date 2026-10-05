"""Architect B5 asset-world truth for agriculture and commodities.

The module intentionally preserves UNKNOWN/UNRESOLVED states.  Provider labels,
reference objects and dated contract names are never promoted into front,
rolling or continuous-series semantics without explicit authority evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class B5AssetWorldError(ValueError):
    """Asset-world evidence violated fail-closed B5 governance."""


class AssetWorldState(StrEnum):
    KNOWN_BLINDSPOT = "KNOWN_BLINDSPOT"
    REFERENCE_OBJECT = "REFERENCE_OBJECT"
    UNRESOLVED = "UNRESOLVED"
    QUALIFIED = "QUALIFIED"


@dataclass(frozen=True, slots=True)
class AgriculturalWorldReceipt:
    as_of: datetime
    conceptual_market_count: int
    provider_candidate_count: int
    provider_count: int
    state: AssetWorldState
    reason_codes: tuple[str, ...]
    secondary_provider_scientifically_admitted: bool
    synthetic_proxy_used: bool = False
    relational_claims_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        _require_aware(self.as_of)
        if self.conceptual_market_count < 1:
            raise B5AssetWorldError("conceptual agricultural universe is required")
        if self.provider_candidate_count < 0 or self.provider_count < 1:
            raise B5AssetWorldError("invalid agricultural provider counts")
        if self.reason_codes != tuple(sorted(set(self.reason_codes))):
            raise B5AssetWorldError("agricultural reason codes must be canonical")
        if self.synthetic_proxy_used:
            raise B5AssetWorldError("synthetic agricultural proxy is forbidden")
        if self.relational_claims_authorized or self.productive_authority:
            raise B5AssetWorldError("agricultural blindspot cannot grant authority")
        if self.provider_candidate_count == 0:
            if self.state is not AssetWorldState.KNOWN_BLINDSPOT:
                raise B5AssetWorldError(
                    "zero agricultural candidates must remain KNOWN_BLINDSPOT"
                )
        elif self.state is AssetWorldState.KNOWN_BLINDSPOT:
            raise B5AssetWorldError(
                "discovered candidates require unresolved identity review"
            )

    def fingerprint(self) -> str:
        return _fingerprint(
            {
                **asdict(self),
                "as_of": self.as_of.astimezone(UTC).isoformat(),
                "state": self.state.value,
            }
        )


@dataclass(frozen=True, slots=True)
class CommodityReferenceObject:
    provider_symbol: str
    reference_identity: str
    tradable_product_identity_status: str
    venue_status: str
    contract_month_status: str
    roll_semantics_status: str
    authority_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.provider_symbol.strip() or not self.reference_identity.strip():
            raise B5AssetWorldError("commodity reference identity required")
        if not self.authority_refs:
            raise B5AssetWorldError("commodity reference requires authority evidence")
        if self.authority_refs != tuple(sorted(set(self.authority_refs))):
            raise B5AssetWorldError("commodity authority refs must be canonical")

    @property
    def state(self) -> AssetWorldState:
        required = (
            self.tradable_product_identity_status == "VERIFIED"
            and self.venue_status == "VERIFIED"
            and self.contract_month_status in {"NOT_APPLICABLE", "VERIFIED"}
            and self.roll_semantics_status in {"NOT_APPLICABLE", "VERIFIED"}
        )
        return AssetWorldState.QUALIFIED if required else AssetWorldState.REFERENCE_OBJECT


@dataclass(frozen=True, slots=True)
class DatedCommodityContract:
    provider_symbol: str
    canonical_product: str
    venue: str
    contract_year: int
    contract_month: int
    front_contract_authority_ref: str | None = None
    roll_authority_ref: str | None = None
    continuous_series_authority_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.provider_symbol.strip() or not self.canonical_product.strip():
            raise B5AssetWorldError("dated commodity contract identity required")
        if not self.venue.strip():
            raise B5AssetWorldError("dated commodity venue required")
        if not 1 <= self.contract_month <= 12:
            raise B5AssetWorldError("contract_month must be 1..12")
        if self.contract_year < 1900:
            raise B5AssetWorldError("contract_year invalid")

    def expired_by_month(self, *, as_of: datetime) -> bool:
        _require_aware(as_of)
        return (self.contract_year, self.contract_month) < (as_of.year, as_of.month)

    @property
    def front_semantics_verified(self) -> bool:
        return self.front_contract_authority_ref is not None

    @property
    def roll_semantics_verified(self) -> bool:
        return self.roll_authority_ref is not None

    @property
    def continuous_semantics_verified(self) -> bool:
        return self.continuous_series_authority_ref is not None


@dataclass(frozen=True, slots=True)
class CommodityWorldReceipt:
    as_of: datetime
    metal_reference_object_count: int
    energy_reference_object_count: int
    dated_contract_count: int
    expired_dated_contract_count: int
    qualified_reference_count: int
    front_contract_verified_count: int
    roll_semantics_verified_count: int
    continuous_semantics_verified_count: int
    state: AssetWorldState
    blockers: tuple[str, ...]
    provider_symbol_implies_front: bool = False
    provider_symbol_implies_roll: bool = False
    provider_symbol_implies_continuous: bool = False
    relational_claims_authorized: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        _require_aware(self.as_of)
        for field_name in (
            "metal_reference_object_count",
            "energy_reference_object_count",
            "dated_contract_count",
            "expired_dated_contract_count",
            "qualified_reference_count",
            "front_contract_verified_count",
            "roll_semantics_verified_count",
            "continuous_semantics_verified_count",
        ):
            if int(getattr(self, field_name)) < 0:
                raise B5AssetWorldError(f"{field_name} cannot be negative")
        if self.expired_dated_contract_count > self.dated_contract_count:
            raise B5AssetWorldError("expired contracts exceed dated contracts")
        if self.blockers != tuple(sorted(set(self.blockers))):
            raise B5AssetWorldError("commodity blockers must be canonical")
        if (
            self.provider_symbol_implies_front
            or self.provider_symbol_implies_roll
            or self.provider_symbol_implies_continuous
            or self.relational_claims_authorized
            or self.productive_authority
        ):
            raise B5AssetWorldError("commodity inference/authority leakage forbidden")

    def fingerprint(self) -> str:
        return _fingerprint(
            {
                **asdict(self),
                "as_of": self.as_of.astimezone(UTC).isoformat(),
                "state": self.state.value,
            }
        )


def assess_agricultural_world(
    *,
    as_of: datetime,
    conceptual_market_count: int,
    provider_candidate_count: int,
    provider_count: int,
    secondary_provider_scientifically_admitted: bool = False,
) -> AgriculturalWorldReceipt:
    """Return honest agricultural coverage without proxy substitution."""

    state = (
        AssetWorldState.KNOWN_BLINDSPOT
        if provider_candidate_count == 0
        else AssetWorldState.UNRESOLVED
    )
    reasons = (
        ("NO_AUTHORIZED_AGRICULTURAL_PROVIDER_CANDIDATES",)
        if provider_candidate_count == 0
        else ("PROVIDER_CANDIDATES_REQUIRE_CANONICAL_IDENTITY_REVIEW",)
    )
    return AgriculturalWorldReceipt(
        as_of=as_of,
        conceptual_market_count=conceptual_market_count,
        provider_candidate_count=provider_candidate_count,
        provider_count=provider_count,
        state=state,
        reason_codes=tuple(sorted(reasons)),
        secondary_provider_scientifically_admitted=(
            secondary_provider_scientifically_admitted
        ),
    )


def energy_reference_objects_from_evidence(
    payload: dict[str, Any],
) -> tuple[CommodityReferenceObject, ...]:
    """Parse authority-bound energy references without inventing product identity."""

    if payload.get("identity") != "QORE_SHARED_GW2_ENERGY_REFERENCE_AUTHORITY_EVIDENCE_001":
        raise B5AssetWorldError("unexpected energy authority evidence identity")
    rows = payload.get("bindings")
    if not isinstance(rows, list):
        raise B5AssetWorldError("energy authority bindings missing")

    result: list[CommodityReferenceObject] = []
    for raw in rows:
        if not isinstance(raw, dict):
            raise B5AssetWorldError("energy authority binding must be object")
        authority_ids = raw.get("authority_ids")
        if not isinstance(authority_ids, list):
            raise B5AssetWorldError("energy authority ids missing")
        result.append(
            CommodityReferenceObject(
                provider_symbol=str(raw["provider_symbol"]),
                reference_identity=str(raw["reference_identity"]),
                tradable_product_identity_status=str(
                    raw["tradable_product_identity_status"]
                ),
                venue_status=str(raw["venue_status"]),
                contract_month_status=str(raw["contract_month_status"]),
                roll_semantics_status=str(raw["roll_semantics_status"]),
                authority_refs=tuple(sorted(str(value) for value in authority_ids)),
            )
        )
    return tuple(sorted(result, key=lambda item: item.provider_symbol))


def dated_gc_contracts_from_evidence(
    payload: dict[str, Any],
) -> tuple[DatedCommodityContract, ...]:
    """Parse exact GC month/year identity while keeping front/roll/continuous open."""

    if payload.get("identity") != "QORE_SHARED_GW2_GC_FUTURES_CONTRACT_AUTHORITY_EVIDENCE_001":
        raise B5AssetWorldError("unexpected GC authority evidence identity")
    semantics = payload.get("resolved_semantics")
    if not isinstance(semantics, dict):
        raise B5AssetWorldError("GC resolved semantics missing")
    venue = str(semantics.get("venue", ""))
    rows = payload.get("provider_contract_bindings")
    if not isinstance(rows, list):
        raise B5AssetWorldError("GC provider contract bindings missing")

    contracts = tuple(
        sorted(
            (
                DatedCommodityContract(
                    provider_symbol=str(raw["provider_symbol"]),
                    canonical_product=str(raw["canonical_product"]),
                    venue=venue,
                    contract_year=int(raw["contract_year"]),
                    contract_month=int(raw["contract_month"]),
                )
                for raw in rows
                if isinstance(raw, dict)
            ),
            key=lambda item: (
                item.contract_year,
                item.contract_month,
                item.provider_symbol,
            ),
        )
    )
    if len(contracts) != len(rows):
        raise B5AssetWorldError("invalid GC binding row")
    return contracts


def assess_commodity_world(
    *,
    as_of: datetime,
    metal_reference_object_count: int,
    energy_reference_objects: tuple[CommodityReferenceObject, ...],
    dated_contracts: tuple[DatedCommodityContract, ...],
) -> CommodityWorldReceipt:
    """Assess B-15 without converting reference objects into futures semantics."""

    _require_aware(as_of)
    qualified = sum(
        item.state is AssetWorldState.QUALIFIED
        for item in energy_reference_objects
    )
    expired = sum(item.expired_by_month(as_of=as_of) for item in dated_contracts)
    front = sum(item.front_semantics_verified for item in dated_contracts)
    roll = sum(item.roll_semantics_verified for item in dated_contracts)
    continuous = sum(item.continuous_semantics_verified for item in dated_contracts)

    blockers: list[str] = []
    if qualified < len(energy_reference_objects):
        blockers.append("ENERGY_TRADABLE_PRODUCT_IDENTITY_UNRESOLVED")
    if dated_contracts and front < len(dated_contracts):
        blockers.append("FRONT_CONTRACT_SELECTION_UNRESOLVED")
    if dated_contracts and roll < len(dated_contracts):
        blockers.append("ROLL_SEMANTICS_UNRESOLVED")
    if dated_contracts and continuous < len(dated_contracts):
        blockers.append("CONTINUOUS_SERIES_CONSTRUCTION_UNRESOLVED")
    if expired:
        blockers.append("OBSERVED_GC_CONTRACT_SET_EXPIRED_BY_AS_OF_MONTH")

    state = AssetWorldState.UNRESOLVED if blockers else AssetWorldState.QUALIFIED
    return CommodityWorldReceipt(
        as_of=as_of,
        metal_reference_object_count=metal_reference_object_count,
        energy_reference_object_count=len(energy_reference_objects),
        dated_contract_count=len(dated_contracts),
        expired_dated_contract_count=expired,
        qualified_reference_count=qualified,
        front_contract_verified_count=front,
        roll_semantics_verified_count=roll,
        continuous_semantics_verified_count=continuous,
        state=state,
        blockers=tuple(sorted(blockers)),
    )


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise B5AssetWorldError("as_of must be timezone-aware")


def _fingerprint(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
