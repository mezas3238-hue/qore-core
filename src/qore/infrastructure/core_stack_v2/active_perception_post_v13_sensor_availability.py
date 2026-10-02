"""Pure source-only governance for the WP-05 post-V13 sensor audit."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class PostV13SensorAvailabilityError(ValueError):
    """The source-only availability audit received invalid evidence."""


class CrossMarketPeerFamily(StrEnum):
    SP500 = "SP500_PEER"
    US30 = "US30_PEER"


_PROVIDER_PREFIXES: dict[CrossMarketPeerFamily, tuple[str, ...]] = {
    CrossMarketPeerFamily.SP500: ("US500", "SPX500", "SP500"),
    CrossMarketPeerFamily.US30: ("US30", "DJ30", "DOW30", "WS30"),
}


class HistoricalPeerCoverageStatus(StrEnum):
    FULL_BID_ASK_HISTORY = "full_bid_ask_history"
    PARTIAL_BID_ASK_HISTORY = "partial_bid_ask_history"
    NO_HISTORY = "no_history"


@dataclass(frozen=True, slots=True)
class ProviderSymbolCandidate:
    family: CrossMarketPeerFamily
    provider_symbol: str

    def __post_init__(self) -> None:
        if not isinstance(self.family, CrossMarketPeerFamily):
            raise PostV13SensorAvailabilityError("candidate family is invalid")
        if (
            not isinstance(self.provider_symbol, str)
            or not self.provider_symbol
            or self.provider_symbol != self.provider_symbol.strip()
        ):
            raise PostV13SensorAvailabilityError(
                "provider symbol must be a non-empty trimmed string"
            )


@dataclass(frozen=True, slots=True)
class HistoricalWindowCoverage:
    manifest_index: int
    bid_count: int
    ask_count: int

    def __post_init__(self) -> None:
        if type(self.manifest_index) is not int or self.manifest_index < 0:
            raise PostV13SensorAvailabilityError(
                "manifest_index must be a non-negative int"
            )
        for name, value in (("bid_count", self.bid_count), ("ask_count", self.ask_count)):
            if type(value) is not int or value < 0:
                raise PostV13SensorAvailabilityError(
                    f"{name} must be a non-negative int"
                )


def normalize_provider_symbol(value: str) -> str:
    """Normalize provider display syntax without inventing semantic identity."""

    if not isinstance(value, str) or not value or value != value.strip():
        raise PostV13SensorAvailabilityError(
            "provider symbol must be a non-empty trimmed string"
        )
    normalized = "".join(character for character in value.upper() if character.isalnum())
    if not normalized:
        raise PostV13SensorAvailabilityError("provider symbol normalized empty")
    return normalized


def discover_cross_market_microstructure_candidates(
    enabled_provider_symbols: Sequence[str],
) -> tuple[ProviderSymbolCandidate, ...]:
    """Return deterministic provider-name candidates for two frozen peer families."""

    if isinstance(enabled_provider_symbols, (str, bytes)):
        raise PostV13SensorAvailabilityError("symbol catalogue must be a sequence")
    discovered: set[tuple[CrossMarketPeerFamily, str]] = set()
    for provider_symbol in enabled_provider_symbols:
        normalized = normalize_provider_symbol(provider_symbol)
        for family, prefixes in _PROVIDER_PREFIXES.items():
            if any(normalized.startswith(prefix) for prefix in prefixes):
                discovered.add((family, provider_symbol))
    return tuple(
        ProviderSymbolCandidate(family=family, provider_symbol=provider_symbol)
        for family, provider_symbol in sorted(
            discovered,
            key=lambda item: (item[0].value, item[1]),
        )
    )


def classify_historical_peer_coverage(
    windows: Sequence[HistoricalWindowCoverage],
) -> HistoricalPeerCoverageStatus:
    """Classify source-only BID/ASK history without target/outcome information."""

    if not windows:
        raise PostV13SensorAvailabilityError("coverage requires at least one window")
    full = all(item.bid_count > 0 and item.ask_count > 0 for item in windows)
    if full:
        return HistoricalPeerCoverageStatus.FULL_BID_ASK_HISTORY
    none = all(item.bid_count == 0 and item.ask_count == 0 for item in windows)
    if none:
        return HistoricalPeerCoverageStatus.NO_HISTORY
    return HistoricalPeerCoverageStatus.PARTIAL_BID_ASK_HISTORY
