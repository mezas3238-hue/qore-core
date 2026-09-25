"""Pure CRT source and identity contract.

This module intentionally contains no CRT entry logic.  It freezes the Owner-approved
methodology boundary, source-authority hierarchy and initial market scope before source
adjudication promotes any machine-executable rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CrtPureSourceTier(StrEnum):
    """Authority tier for CRT source evidence."""

    LEVEL_A = "LEVEL_A"
    LEVEL_A_PLUS = "LEVEL_A_PLUS"
    LEVEL_B = "LEVEL_B"


class CrtPureAdjudicationState(StrEnum):
    """Permitted source-adjudication states."""

    CANONICAL = "CANONICAL"
    CORROBORATED = "CORROBORATED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_SOURCE_SUPPORTED = "NOT_SOURCE_SUPPORTED"


class CrtPureMarket(StrEnum):
    """Initial Owner-approved CRT PURE market universe."""

    AUDUSD = "AUDUSD"
    USDJPY = "USDJPY"
    BTCUSD = "BTCUSD"


@dataclass(frozen=True, slots=True)
class CrtPureSourceAuthority:
    """One approved source authority and its role."""

    name: str
    tier: CrtPureSourceTier
    can_define_methodology: bool
    role: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("source authority name must be non-empty")
        if not self.role.strip():
            raise ValueError("source authority role must be non-empty")
        if self.tier is CrtPureSourceTier.LEVEL_B and self.can_define_methodology:
            raise ValueError("LEVEL_B corroboration cannot define CRT methodology")


@dataclass(frozen=True, slots=True)
class CrtPureIdentityContract:
    """Frozen non-economic identity contract for the CRT PURE lineage."""

    methodology_family: str
    methodology_variant: str
    markets: tuple[CrtPureMarket, ...]
    sources: tuple[CrtPureSourceAuthority, ...]
    excluded_methodology_ids: tuple[str, ...]
    source_adjudication_complete: bool = False
    strategy_identity_complete: bool = False
    certified: bool = False

    def __post_init__(self) -> None:
        if self.methodology_family != "CRT":
            raise ValueError("pure CRT family must be exactly CRT")
        if self.methodology_variant != "PURE":
            raise ValueError("pure CRT variant must be exactly PURE")
        if self.markets != (
            CrtPureMarket.AUDUSD,
            CrtPureMarket.USDJPY,
            CrtPureMarket.BTCUSD,
        ):
            raise ValueError("CRT PURE initial market scope must be AUDUSD/USDJPY/BTCUSD")
        if len(set(self.markets)) != len(self.markets):
            raise ValueError("CRT PURE markets must be unique")
        if not self.sources:
            raise ValueError("CRT PURE requires an approved source hierarchy")
        if not any(
            item.tier is CrtPureSourceTier.LEVEL_A and item.can_define_methodology
            for item in self.sources
        ):
            raise ValueError("CRT PURE requires at least one canonical LEVEL_A authority")
        if "crt-4h-amd" not in self.excluded_methodology_ids:
            raise ValueError("historical crt-4h-amd methodology must remain excluded")
        if self.certified and (
            not self.source_adjudication_complete or not self.strategy_identity_complete
        ):
            raise ValueError("CRT PURE cannot be certified before source and identity closure")


CRT_PURE_SOURCES: tuple[CrtPureSourceAuthority, ...] = (
    CrtPureSourceAuthority(
        name="RomeoTPT",
        tier=CrtPureSourceTier.LEVEL_A,
        can_define_methodology=True,
        role="canonical original CRT authority",
    ),
    CrtPureSourceAuthority(
        name="RomeoTPT author-distributed documents",
        tier=CrtPureSourceTier.LEVEL_A_PLUS,
        can_define_methodology=True,
        role="primary author-distributed documentary evidence",
    ),
    CrtPureSourceAuthority(
        name="SpeculatorFL",
        tier=CrtPureSourceTier.LEVEL_B,
        can_define_methodology=False,
        role="corroboration and ambiguity discovery only",
    ),
    CrtPureSourceAuthority(
        name="TraderFlameseN",
        tier=CrtPureSourceTier.LEVEL_B,
        can_define_methodology=False,
        role="corroboration and ambiguity discovery only",
    ),
    CrtPureSourceAuthority(
        name="TTrades",
        tier=CrtPureSourceTier.LEVEL_B,
        can_define_methodology=False,
        role="corroboration and ambiguity discovery only",
    ),
)


CRT_PURE_IDENTITY = CrtPureIdentityContract(
    methodology_family="CRT",
    methodology_variant="PURE",
    markets=(
        CrtPureMarket.AUDUSD,
        CrtPureMarket.USDJPY,
        CrtPureMarket.BTCUSD,
    ),
    sources=CRT_PURE_SOURCES,
    excluded_methodology_ids=(
        "crt-4h-amd",
        "vt08-crt-159-v3-machine-operationalization",
    ),
)


def canonical_methodology_sources() -> tuple[CrtPureSourceAuthority, ...]:
    """Return only authorities allowed to define CRT methodology."""

    return tuple(item for item in CRT_PURE_SOURCES if item.can_define_methodology)


def corroboration_sources() -> tuple[CrtPureSourceAuthority, ...]:
    """Return approved non-authoritative corroboration sources."""

    return tuple(
        item
        for item in CRT_PURE_SOURCES
        if item.tier is CrtPureSourceTier.LEVEL_B
    )
