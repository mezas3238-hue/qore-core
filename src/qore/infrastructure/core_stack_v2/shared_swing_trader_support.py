"""Research-only support contracts for future Shared-aware Swing Traders."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedIntelligenceClass,
    SharedTraderCapability,
    SharedTraderIntelligenceValidationError,
)


class SharedSwingTraderFamily(StrEnum):
    GLOBAL_MACRO_SWING = "QORE_GLOBAL_MACRO_SWING"
    COMMODITY_SWING = "QORE_COMMODITY_SWING"
    CROSS_ASSET_SWING = "QORE_CROSS_ASSET_SWING"
    REGIME_TRANSITION_SWING = "QORE_REGIME_TRANSITION_SWING"


class SharedSwingHorizon(StrEnum):
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"


@dataclass(frozen=True, slots=True)
class SharedSwingSupportProfile:
    """Describes future consumer capability; it does not create a Trader."""

    profile_id: str
    trader_family: SharedSwingTraderFamily
    version: str
    frozen_at: datetime
    markets: tuple[str, ...]
    horizons: tuple[SharedSwingHorizon, ...]
    intelligence_classes: tuple[SharedIntelligenceClass, ...]
    source_evidence_refs: tuple[str, ...]
    runtime_trader_exists: bool = False
    trader_certified: bool = False
    setup_authority: bool = False
    direction_authority: bool = False
    entry_authority: bool = False
    stop_target_authority: bool = False
    position_management_authority: bool = False
    execution_authority: bool = False
    sizing_authority: bool = False

    def __post_init__(self) -> None:
        for name in ("profile_id", "version"):
            if not str(getattr(self, name)).strip():
                raise SharedTraderIntelligenceValidationError(
                    f"{name} must be non-empty"
                )
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise SharedTraderIntelligenceValidationError(
                "swing profile frozen_at must be timezone-aware"
            )
        if not self.markets or self.markets != tuple(sorted(set(self.markets))):
            raise SharedTraderIntelligenceValidationError(
                "swing profile markets must be non-empty and canonical"
            )
        if self.horizons != tuple(
            sorted(set(self.horizons), key=lambda item: item.value)
        ):
            raise SharedTraderIntelligenceValidationError(
                "swing profile horizons must be unique and canonical"
            )
        if not self.horizons:
            raise SharedTraderIntelligenceValidationError(
                "swing profile horizons must be non-empty"
            )
        if self.intelligence_classes != tuple(
            sorted(set(self.intelligence_classes), key=lambda item: item.value)
        ):
            raise SharedTraderIntelligenceValidationError(
                "swing intelligence classes must be unique and canonical"
            )
        if not self.intelligence_classes:
            raise SharedTraderIntelligenceValidationError(
                "swing intelligence classes must be non-empty"
            )
        if (
            not self.source_evidence_refs
            or self.source_evidence_refs
            != tuple(sorted(set(self.source_evidence_refs)))
        ):
            raise SharedTraderIntelligenceValidationError(
                "swing profile evidence must be non-empty and canonical"
            )
        if self.runtime_trader_exists or self.trader_certified:
            raise SharedTraderIntelligenceValidationError(
                "STI-12 profile cannot create or certify a Swing Trader"
            )
        if (
            self.setup_authority
            or self.direction_authority
            or self.entry_authority
            or self.stop_target_authority
            or self.position_management_authority
            or self.execution_authority
            or self.sizing_authority
        ):
            raise SharedTraderIntelligenceValidationError(
                "Shared Swing support cannot own Trader authority"
            )

    def as_routing_capability(self) -> SharedTraderCapability:
        return SharedTraderCapability(
            trader_id=self.trader_family.value + "_RESEARCH_INTERFACE",
            markets=self.markets,
            horizons=tuple(
                sorted(item.value for item in self.horizons)
            ),
            supported_intelligence_classes=self.intelligence_classes,
            open_position_monitoring_capability=True,
        )

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["trader_family"] = self.trader_family.value
        payload["frozen_at"] = self.frozen_at.astimezone(UTC).isoformat()
        payload["horizons"] = tuple(item.value for item in self.horizons)
        payload["intelligence_classes"] = tuple(
            item.value for item in self.intelligence_classes
        )
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def build_research_swing_support_profile(
    *,
    profile_id: str,
    trader_family: SharedSwingTraderFamily,
    version: str,
    frozen_at: datetime,
    markets: tuple[str, ...],
    horizons: tuple[SharedSwingHorizon, ...],
    intelligence_classes: tuple[SharedIntelligenceClass, ...],
    source_evidence_refs: tuple[str, ...],
) -> SharedSwingSupportProfile:
    """Create a research interface only; no runtime Trader is instantiated."""

    return SharedSwingSupportProfile(
        profile_id=profile_id,
        trader_family=trader_family,
        version=version,
        frozen_at=frozen_at,
        markets=markets,
        horizons=horizons,
        intelligence_classes=intelligence_classes,
        source_evidence_refs=source_evidence_refs,
    )
