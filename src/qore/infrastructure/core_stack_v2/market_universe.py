"""Global read-only market knowledge for QORE CORE STACK V2.

Shared Core must understand the complete QORE market universe without owning a
private symbol allowlist. Concrete markets come from the provider-neutral
ExecutiveMarketsReadModel. Instrument-family semantics come from the canonical
InstrumentUniverseRegistrySnapshot when available.

Knowledge is descriptive only:
- unavailable/restricted markets remain visible as context;
- authorization state is retained, never reinterpreted;
- no market record grants signal, strategy, Risk, order, or execution authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Final

from qore.governance.executive_operational_read_models import ExecutiveMarketsReadModel
from qore.infrastructure.instrument_universe_registry import (
    InstrumentUniverseRegistrySnapshot,
)

GLOBAL_MARKET_UNIVERSE_REQUIRED: Final = True


def _aware_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("global market universe timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class CoreMarketKnowledge:
    instrument: str
    asset_class: str
    availability: str
    authorization_state: str
    regime_code: str
    session_code: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.instrument or not self.asset_class:
            raise ValueError("market knowledge identity must be non-empty")
        if not self.availability or not self.authorization_state:
            raise ValueError("market knowledge state must be explicit")
        if self.reason_codes != tuple(sorted(self.reason_codes)):
            raise ValueError("market reason codes must be canonical")
        if self.evidence_refs != tuple(sorted(self.evidence_refs)):
            raise ValueError("market evidence refs must be canonical")


@dataclass(frozen=True, slots=True)
class CoreInstrumentFamilyKnowledge:
    family: str
    coverage_status: str
    owner_status: str
    owner_refs: tuple[str, ...]
    unresolved_semantics: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.family or not self.coverage_status or not self.owner_status:
            raise ValueError("instrument-family knowledge must be explicit")
        for values in (
            self.owner_refs,
            self.unresolved_semantics,
            self.evidence_refs,
        ):
            if values != tuple(sorted(values)):
                raise ValueError("instrument-family refs must be canonical")


@dataclass(frozen=True, slots=True)
class CoreGlobalMarketUniverse:
    source_observed_at: datetime
    projected_at: datetime
    source_freshness: str
    markets: tuple[CoreMarketKnowledge, ...]
    instrument_families: tuple[CoreInstrumentFamilyKnowledge, ...]
    order_authority: bool = False
    risk_authority: bool = False
    strategy_mutation_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        _aware_iso(self.source_observed_at)
        _aware_iso(self.projected_at)
        if self.projected_at < self.source_observed_at:
            raise ValueError("market-universe projection cannot predate its source")
        if not self.source_freshness:
            raise ValueError("market-universe freshness must be explicit")
        if (
            self.order_authority
            or self.risk_authority
            or self.strategy_mutation_authority
            or self.execution_authority
        ):
            raise ValueError("global market knowledge cannot carry trading authority")

        symbols = tuple(item.instrument for item in self.markets)
        if symbols != tuple(sorted(symbols)) or len(symbols) != len(set(symbols)):
            raise ValueError("global markets must be unique and canonical")

        families = tuple(item.family for item in self.instrument_families)
        if families != tuple(sorted(families)) or len(families) != len(set(families)):
            raise ValueError("instrument families must be unique and canonical")

    @property
    def market_count(self) -> int:
        return len(self.markets)

    @property
    def family_count(self) -> int:
        return len(self.instrument_families)

    def payload(self) -> dict[str, object]:
        return {
            "source_observed_at": _aware_iso(self.source_observed_at),
            "projected_at": _aware_iso(self.projected_at),
            "source_freshness": self.source_freshness,
            "markets": [asdict(item) for item in self.markets],
            "instrument_families": [
                asdict(item) for item in self.instrument_families
            ],
            "order_authority": self.order_authority,
            "risk_authority": self.risk_authority,
            "strategy_mutation_authority": self.strategy_mutation_authority,
            "execution_authority": self.execution_authority,
        }

    def fingerprint(self) -> str:
        raw = json.dumps(self.payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def build_global_market_universe(
    markets: ExecutiveMarketsReadModel,
    *,
    instrument_registry: InstrumentUniverseRegistrySnapshot | None = None,
) -> CoreGlobalMarketUniverse:
    """Retain every QORE market as read-only knowledge, without a symbol allowlist."""
    concrete = tuple(
        sorted(
            (
                CoreMarketKnowledge(
                    instrument=item.instrument.symbol,
                    asset_class=item.asset_class.value,
                    availability=item.availability.value,
                    authorization_state=item.authorization_state.value,
                    regime_code=item.regime_code,
                    session_code=item.session_code,
                    reason_codes=item.reason_codes,
                    evidence_refs=tuple(ref.value for ref in item.evidence_refs),
                )
                for item in markets.markets
            ),
            key=lambda item: item.instrument,
        )
    )

    families: tuple[CoreInstrumentFamilyKnowledge, ...] = ()
    if instrument_registry is not None:
        if instrument_registry.as_of > markets.metadata.projected_at.date():
            raise ValueError(
                "instrument-universe registry cannot postdate market projection"
            )
        families = tuple(
            sorted(
                (
                    CoreInstrumentFamilyKnowledge(
                        family=item.family.value,
                        coverage_status=item.coverage_status.value,
                        owner_status=item.owner_status.value,
                        owner_refs=tuple(ref.value for ref in item.owner_refs),
                        unresolved_semantics=tuple(
                            ref.value for ref in item.unresolved_semantics
                        ),
                        evidence_refs=tuple(ref.value for ref in item.evidence_refs),
                    )
                    for item in instrument_registry.entries
                ),
                key=lambda item: item.family,
            )
        )

    return CoreGlobalMarketUniverse(
        source_observed_at=markets.metadata.source_observed_at,
        projected_at=markets.metadata.projected_at,
        source_freshness=markets.metadata.freshness.value,
        markets=concrete,
        instrument_families=families,
    )
