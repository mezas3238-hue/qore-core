"""Provider-neutral agricultural sensor discovery and qualification contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final


class AgriculturalWorldFamily(StrEnum):
    AGRICULTURE = "AGRICULTURE"
    SOFTS = "SOFTS"
    LIVESTOCK = "LIVESTOCK"


class AgriculturalProviderDiscoveryState(StrEnum):
    ABSENT_FROM_CURRENT_CATALOG_EVIDENCE = (
        "ABSENT_FROM_CURRENT_CATALOG_EVIDENCE"
    )
    DISCOVERED_CANDIDATE = "DISCOVERED_CANDIDATE"


class AgriculturalCapabilityEvidenceState(StrEnum):
    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AgriculturalScientificMaturity(StrEnum):
    ABSENT = "ABSENT"
    DISCOVERED = "DISCOVERED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    CONTRACT_MAPPED = "CONTRACT_MAPPED"
    TEMPORALLY_READY = "TEMPORALLY_READY"
    DATA_QUALITY_READY = "DATA_QUALITY_READY"
    RELATIONALLY_READY = "RELATIONALLY_READY"
    RESEARCH = "RESEARCH"
    FALSIFIED = "FALSIFIED"
    OBSERVE_ONLY = "OBSERVE_ONLY"
    VALIDATED = "VALIDATED"
    REPLICATED = "REPLICATED"
    ADMITTED = "ADMITTED"


class AgriculturalQualificationStage(StrEnum):
    DISCOVERED = "DISCOVERED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    CONTRACT_MAPPED = "CONTRACT_MAPPED"
    CALENDAR_MAPPED = "CALENDAR_MAPPED"
    HISTORICAL_AVAILABILITY_VERIFIED = "HISTORICAL_AVAILABILITY_VERIFIED"
    TIMESTAMP_VERIFIED = "TIMESTAMP_VERIFIED"
    DATA_QUALITY_VERIFIED = "DATA_QUALITY_VERIFIED"
    ROLL_POLICY_VERIFIED = "ROLL_POLICY_VERIFIED"
    TEMPORALLY_OBSERVABLE = "TEMPORALLY_OBSERVABLE"
    RELATIONALLY_COMPARABLE = "RELATIONALLY_COMPARABLE"
    INFORMATION_GAIN_TESTED = "INFORMATION_GAIN_TESTED"
    CAUSALLY_RESEARCHED = "CAUSALLY_RESEARCHED"
    TEMPORALLY_REPLICATED = "TEMPORALLY_REPLICATED"
    SCIENTIFICALLY_ADMITTED = "SCIENTIFICALLY_ADMITTED"


AGRICULTURAL_QUALIFICATION_PIPELINE: Final = tuple(
    AgriculturalQualificationStage
)


@dataclass(frozen=True, slots=True)
class AgriculturalDiscoveryTarget:
    """Conceptual discovery target only; never a canonical economic identity."""

    conceptual_market_key: str
    display_name: str
    world_family: AgriculturalWorldFamily
    complex_memberships: tuple[str, ...]
    discovery_terms: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.conceptual_market_key.strip():
            raise ValueError("conceptual_market_key must be non-empty")
        if not self.display_name.strip():
            raise ValueError("display_name must be non-empty")
        if self.complex_memberships != tuple(
            sorted(set(self.complex_memberships))
        ):
            raise ValueError(
                "complex_memberships must be unique and canonical"
            )
        if self.discovery_terms != tuple(sorted(set(self.discovery_terms))):
            raise ValueError("discovery_terms must be unique and canonical")
        if not self.discovery_terms:
            raise ValueError("discovery_terms must be non-empty")
        if any(not item.strip() for item in self.discovery_terms):
            raise ValueError("discovery_terms cannot contain empty values")


@dataclass(frozen=True, slots=True, order=True)
class ProviderAgriculturalCandidate:
    provider: str
    provider_symbol_id: int
    provider_symbol: str
    provider_native_symbol_name: str | None
    provider_description: str | None
    provenance_ref: str

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.provider_symbol.strip():
            raise ValueError("provider candidate identity must be explicit")
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise ValueError("provider_symbol_id must be positive int")
        if (
            self.provider_native_symbol_name is not None
            and not self.provider_native_symbol_name.strip()
        ):
            raise ValueError(
                "provider_native_symbol_name must be non-empty or None"
            )
        if (
            self.provider_description is not None
            and not self.provider_description.strip()
        ):
            raise ValueError(
                "provider_description must be non-empty or None"
            )
        if not self.provenance_ref.strip():
            raise ValueError("provider candidate provenance must be explicit")


@dataclass(frozen=True, slots=True)
class AgriculturalProviderCapabilityRow:
    target: AgriculturalDiscoveryTarget
    provider: str
    discovery_state: AgriculturalProviderDiscoveryState
    candidates: tuple[ProviderAgriculturalCandidate, ...]
    contract_type: str = "UNKNOWN"
    historical_availability: AgriculturalCapabilityEvidenceState = (
        AgriculturalCapabilityEvidenceState.UNKNOWN
    )
    history_depth_days: int | None = None
    realtime_availability: AgriculturalCapabilityEvidenceState = (
        AgriculturalCapabilityEvidenceState.UNKNOWN
    )
    bid_ask_availability: AgriculturalCapabilityEvidenceState = (
        AgriculturalCapabilityEvidenceState.UNKNOWN
    )
    tick_availability: AgriculturalCapabilityEvidenceState = (
        AgriculturalCapabilityEvidenceState.UNKNOWN
    )
    ohlc_availability: AgriculturalCapabilityEvidenceState = (
        AgriculturalCapabilityEvidenceState.UNKNOWN
    )
    contract_metadata_availability: AgriculturalCapabilityEvidenceState = (
        AgriculturalCapabilityEvidenceState.UNKNOWN
    )
    identity_verified: bool = False
    contract_mapped: bool = False
    calendar_mapped: bool = False
    data_quality_verified: bool = False
    roll_policy_verified: bool = False
    relational_ready: bool = False
    scientific_maturity: AgriculturalScientificMaturity = (
        AgriculturalScientificMaturity.ABSENT
    )
    final_global_admission_authority: bool = False
    execution_authority: bool = False
    risk_authority: bool = False
    sizing_authority: bool = False
    strategy_mutation_authority: bool = False

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must be non-empty")
        if self.candidates != tuple(sorted(set(self.candidates))):
            raise ValueError("agricultural candidates must be canonical")
        if (
            self.discovery_state
            is AgriculturalProviderDiscoveryState.ABSENT_FROM_CURRENT_CATALOG_EVIDENCE
        ):
            if self.candidates:
                raise ValueError(
                    "absent agricultural target cannot carry candidates"
                )
            if self.scientific_maturity is not AgriculturalScientificMaturity.ABSENT:
                raise ValueError(
                    "absent agricultural target must remain ABSENT maturity"
                )
        elif not self.candidates:
            raise ValueError(
                "discovered agricultural target requires provider candidate"
            )
        if self.history_depth_days is not None and self.history_depth_days < 0:
            raise ValueError("history_depth_days cannot be negative")
        if self.contract_type != "UNKNOWN":
            raise ValueError(
                "AGRI-1 discovery cannot infer agricultural contract type"
            )
        if (
            self.identity_verified
            or self.contract_mapped
            or self.calendar_mapped
            or self.data_quality_verified
            or self.roll_policy_verified
            or self.relational_ready
            or self.final_global_admission_authority
            or self.execution_authority
            or self.risk_authority
            or self.sizing_authority
            or self.strategy_mutation_authority
        ):
            raise ValueError(
                "AGRI-1 provider discovery cannot grant qualification or authority"
            )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["target"]["world_family"] = self.target.world_family.value
        payload["discovery_state"] = self.discovery_state.value
        for field_name in (
            "historical_availability",
            "realtime_availability",
            "bid_ask_availability",
            "tick_availability",
            "ohlc_availability",
            "contract_metadata_availability",
        ):
            payload[field_name] = getattr(self, field_name).value
        payload["scientific_maturity"] = self.scientific_maturity.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class GlobalAgriculturalSensorMatrix:
    as_of: datetime
    source_catalog_fingerprint: str
    rows: tuple[AgriculturalProviderCapabilityRow, ...]
    conceptual_universe_identity: str
    conceptual_universe_fingerprint: str
    provider_symbol_is_canonical_identity: bool = False
    automatic_sensor_admission: bool = False
    relational_claims_authorized: bool = False
    protected_holdout_opened: bool = False

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise ValueError("agricultural matrix as_of must be timezone-aware")
        for name in (
            "source_catalog_fingerprint",
            "conceptual_universe_fingerprint",
        ):
            value = getattr(self, name)
            if len(value) != 64:
                raise ValueError(f"{name} must be sha256 hex")
            try:
                int(value, 16)
            except ValueError as exc:
                raise ValueError(f"{name} must be sha256 hex") from exc
        if not self.conceptual_universe_identity.strip():
            raise ValueError(
                "conceptual_universe_identity must be non-empty"
            )
        keys = tuple(
            (item.provider, item.target.conceptual_market_key)
            for item in self.rows
        )
        if keys != tuple(sorted(keys)) or len(keys) != len(set(keys)):
            raise ValueError(
                "agricultural matrix rows must be unique and canonical"
            )
        if (
            self.provider_symbol_is_canonical_identity
            or self.automatic_sensor_admission
            or self.relational_claims_authorized
            or self.protected_holdout_opened
        ):
            raise ValueError(
                "agricultural discovery matrix cannot expand authority"
            )

    def fingerprint(self) -> str:
        payload = {
            "as_of": self.as_of.astimezone(UTC).isoformat(),
            "source_catalog_fingerprint": self.source_catalog_fingerprint,
            "conceptual_universe_identity": self.conceptual_universe_identity,
            "conceptual_universe_fingerprint": (
                self.conceptual_universe_fingerprint
            ),
            "rows": [
                {
                    "provider": item.provider,
                    "conceptual_market_key": (
                        item.target.conceptual_market_key
                    ),
                    "fingerprint": item.fingerprint(),
                }
                for item in self.rows
            ],
            "provider_symbol_is_canonical_identity": False,
            "automatic_sensor_admission": False,
            "relational_claims_authorized": False,
            "protected_holdout_opened": False,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def _normalize(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.casefold().split())


def _term_matches(*, term: str, haystack: str) -> bool:
    normalized_term = _normalize(term)
    if not normalized_term:
        return False
    return (
        re.search(
            r"(?<![a-z0-9])"
            + re.escape(normalized_term)
            + r"(?![a-z0-9])",
            haystack,
        )
        is not None
    )


def build_agricultural_provider_capability_matrix(
    *,
    provider: str,
    as_of: datetime,
    source_catalog_fingerprint: str,
    conceptual_universe_identity: str,
    conceptual_universe_fingerprint: str,
    targets: tuple[AgriculturalDiscoveryTarget, ...],
    provider_catalog: tuple[ProviderAgriculturalCandidate, ...],
) -> GlobalAgriculturalSensorMatrix:
    """Discover candidates conservatively without creating economic identity."""

    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    if not provider.strip():
        raise ValueError("provider must be non-empty")
    if targets != tuple(
        sorted(targets, key=lambda item: item.conceptual_market_key)
    ):
        raise ValueError("agricultural targets must be canonical")
    catalog = tuple(
        sorted(
            (
                item
                for item in provider_catalog
                if item.provider == provider
            ),
            key=lambda item: (
                item.provider,
                item.provider_symbol_id,
                item.provider_symbol,
            ),
        )
    )
    if catalog != tuple(sorted(set(catalog))):
        raise ValueError("provider catalog candidates must be unique")

    rows: list[AgriculturalProviderCapabilityRow] = []
    for target in targets:
        matches: list[ProviderAgriculturalCandidate] = []
        for item in catalog:
            haystack = _normalize(
                " ".join(
                    part
                    for part in (
                        item.provider_symbol,
                        item.provider_native_symbol_name,
                        item.provider_description,
                    )
                    if part is not None
                )
            )
            if any(
                _term_matches(term=term, haystack=haystack)
                for term in target.discovery_terms
            ):
                matches.append(item)
        candidates = tuple(sorted(set(matches)))
        if candidates:
            discovery_state = (
                AgriculturalProviderDiscoveryState.DISCOVERED_CANDIDATE
            )
            maturity = AgriculturalScientificMaturity.DISCOVERED
        else:
            discovery_state = (
                AgriculturalProviderDiscoveryState.ABSENT_FROM_CURRENT_CATALOG_EVIDENCE
            )
            maturity = AgriculturalScientificMaturity.ABSENT
        rows.append(
            AgriculturalProviderCapabilityRow(
                target=target,
                provider=provider,
                discovery_state=discovery_state,
                candidates=candidates,
                scientific_maturity=maturity,
            )
        )

    return GlobalAgriculturalSensorMatrix(
        as_of=as_of,
        source_catalog_fingerprint=source_catalog_fingerprint,
        rows=tuple(
            sorted(
                rows,
                key=lambda item: (
                    item.provider,
                    item.target.conceptual_market_key,
                ),
            )
        ),
        conceptual_universe_identity=conceptual_universe_identity,
        conceptual_universe_fingerprint=conceptual_universe_fingerprint,
    )
