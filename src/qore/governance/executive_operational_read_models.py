from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from re import fullmatch

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionMetadata,
    ExecutiveReadModelValidationError,
)


def _validate_canonical_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[a-z][a-z0-9._:/-]*", value) is None:
        raise ExecutiveReadModelValidationError(
            f"{field_name} must use canonical lowercase syntax"
        )
    return value


def _validated_codes(values: tuple[str, ...], *, field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise ExecutiveReadModelValidationError(f"{field_name} must be an immutable tuple")
    normalized = tuple(
        _validate_canonical_text(value, field_name=field_name) for value in values
    )
    if not normalized:
        raise ExecutiveReadModelValidationError(f"{field_name} must not be empty")
    if len(set(normalized)) != len(normalized):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(normalized))


def _validated_evidence_refs(
    values: tuple[ExecutiveEvidenceRef, ...],
    *,
    field_name: str,
) -> tuple[ExecutiveEvidenceRef, ...]:
    if not isinstance(values, tuple) or any(
        not isinstance(item, ExecutiveEvidenceRef) for item in values
    ):
        raise ExecutiveReadModelValidationError(
            f"{field_name} must be an immutable tuple of ExecutiveEvidenceRef"
        )
    if not values:
        raise ExecutiveReadModelValidationError(f"{field_name} must not be empty")
    if len(set(values)) != len(values):
        raise ExecutiveReadModelValidationError(f"{field_name} must not contain duplicates")
    return tuple(sorted(values, key=lambda item: item.value))


@dataclass(frozen=True, slots=True)
class ExecutiveMarketInstrument:
    """Provider-neutral instrument identifier exposed to executive clients."""

    symbol: str

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str) or fullmatch(
            r"[A-Z0-9][A-Z0-9._/-]*", self.symbol
        ) is None:
            raise ExecutiveReadModelValidationError(
                "executive market instrument must use canonical uppercase syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.symbol,)


@dataclass(frozen=True, slots=True)
class ExecutiveAssetClass:
    """Extensible asset-class code; intentionally not a provider-specific enum."""

    value: str

    def __post_init__(self) -> None:
        _validate_canonical_text(self.value, field_name="executive asset class")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ExecutiveMarketAvailability(StrEnum):
    AVAILABLE = "available"
    RESTRICTED = "restricted"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ExecutiveMarketAuthorizationState(StrEnum):
    AUTHORIZED = "authorized"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveMarketSummary:
    """Evidence-backed public market state without provider or broker objects."""

    instrument: ExecutiveMarketInstrument
    asset_class: ExecutiveAssetClass
    availability: ExecutiveMarketAvailability
    authorization_state: ExecutiveMarketAuthorizationState
    regime_code: str
    session_code: str
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, ExecutiveMarketInstrument):
            raise ExecutiveReadModelValidationError(
                "market summary requires ExecutiveMarketInstrument"
            )
        if not isinstance(self.asset_class, ExecutiveAssetClass):
            raise ExecutiveReadModelValidationError(
                "market summary requires ExecutiveAssetClass"
            )
        if not isinstance(self.availability, ExecutiveMarketAvailability):
            raise ExecutiveReadModelValidationError(
                "market summary requires ExecutiveMarketAvailability"
            )
        if not isinstance(
            self.authorization_state,
            ExecutiveMarketAuthorizationState,
        ):
            raise ExecutiveReadModelValidationError(
                "market summary requires ExecutiveMarketAuthorizationState"
            )
        object.__setattr__(
            self,
            "regime_code",
            _validate_canonical_text(self.regime_code, field_name="market regime code"),
        )
        object.__setattr__(
            self,
            "session_code",
            _validate_canonical_text(self.session_code, field_name="market session code"),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="market reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="market evidence refs",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.logical_values(),
            self.asset_class.logical_values(),
            self.availability.value,
            self.authorization_state.value,
            self.regime_code,
            self.session_code,
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveMarketsReadModel:
    """Stable MARKETS projection for the authorized executive read boundary."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    markets: tuple[ExecutiveMarketSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "markets read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.MARKETS:
            raise ExecutiveReadModelValidationError(
                "markets projection requires MARKETS scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "markets projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.markets, tuple) or any(
            not isinstance(item, ExecutiveMarketSummary) for item in self.markets
        ):
            raise ExecutiveReadModelValidationError(
                "markets must be an immutable tuple of ExecutiveMarketSummary"
            )
        symbols = tuple(item.instrument.symbol for item in self.markets)
        if len(set(symbols)) != len(symbols):
            raise ExecutiveReadModelValidationError(
                "markets projection must not contain duplicate instruments"
            )
        object.__setattr__(
            self,
            "markets",
            tuple(sorted(self.markets, key=lambda item: item.instrument.symbol)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.markets),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveTraderId:
    """Stable opaque executive reference to a virtual trader."""

    value: str

    def __post_init__(self) -> None:
        _validate_canonical_text(self.value, field_name="executive trader id")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveStrategyVersionRef:
    """Sanitized version reference, never strategy implementation or parameters."""

    value: str

    def __post_init__(self) -> None:
        _validate_canonical_text(self.value, field_name="strategy version reference")

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ExecutiveTraderConfidence:
    """Explicit finite executive confidence projection in the closed [0, 1] interval."""

    value: float

    def __post_init__(self) -> None:
        if type(self.value) is not float or not isfinite(self.value):
            raise ExecutiveReadModelValidationError(
                "executive trader confidence must be a finite float"
            )
        if not 0.0 <= self.value <= 1.0:
            raise ExecutiveReadModelValidationError(
                "executive trader confidence must be between 0.0 and 1.0"
            )

    def logical_values(self) -> tuple[float, ...]:
        return (self.value,)


class ExecutiveTraderState(StrEnum):
    ELIGIBLE = "eligible"
    OPERATING = "operating"
    RESTRICTED = "restricted"
    TRAINING = "training"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"


class ExecutiveTraderAuthorizationState(StrEnum):
    AUTHORIZED = "authorized"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not-applicable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ExecutiveTraderSummary:
    """Evidence-backed trader projection without internal specialist/domain objects."""

    trader_id: ExecutiveTraderId
    kind_code: str
    strategy_version: ExecutiveStrategyVersionRef
    state: ExecutiveTraderState
    authorization_state: ExecutiveTraderAuthorizationState
    confidence: ExecutiveTraderConfidence | None
    judgment_code: str
    market_instruments: tuple[ExecutiveMarketInstrument, ...]
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[ExecutiveEvidenceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.trader_id, ExecutiveTraderId):
            raise ExecutiveReadModelValidationError(
                "trader summary requires ExecutiveTraderId"
            )
        object.__setattr__(
            self,
            "kind_code",
            _validate_canonical_text(self.kind_code, field_name="trader kind code"),
        )
        if not isinstance(self.strategy_version, ExecutiveStrategyVersionRef):
            raise ExecutiveReadModelValidationError(
                "trader summary requires ExecutiveStrategyVersionRef"
            )
        if not isinstance(self.state, ExecutiveTraderState):
            raise ExecutiveReadModelValidationError(
                "trader summary requires ExecutiveTraderState"
            )
        if not isinstance(
            self.authorization_state,
            ExecutiveTraderAuthorizationState,
        ):
            raise ExecutiveReadModelValidationError(
                "trader summary requires ExecutiveTraderAuthorizationState"
            )
        if self.confidence is not None and not isinstance(
            self.confidence,
            ExecutiveTraderConfidence,
        ):
            raise ExecutiveReadModelValidationError(
                "trader confidence must be ExecutiveTraderConfidence or None"
            )
        object.__setattr__(
            self,
            "judgment_code",
            _validate_canonical_text(self.judgment_code, field_name="trader judgment code"),
        )
        if not isinstance(self.market_instruments, tuple) or any(
            not isinstance(item, ExecutiveMarketInstrument)
            for item in self.market_instruments
        ):
            raise ExecutiveReadModelValidationError(
                "trader markets must be an immutable tuple of ExecutiveMarketInstrument"
            )
        symbols = tuple(item.symbol for item in self.market_instruments)
        if len(set(symbols)) != len(symbols):
            raise ExecutiveReadModelValidationError(
                "trader market instruments must not contain duplicates"
            )
        object.__setattr__(
            self,
            "market_instruments",
            tuple(sorted(self.market_instruments, key=lambda item: item.symbol)),
        )
        object.__setattr__(
            self,
            "reason_codes",
            _validated_codes(self.reason_codes, field_name="trader reason codes"),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _validated_evidence_refs(
                self.evidence_refs,
                field_name="trader evidence refs",
            ),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.trader_id.logical_values(),
            self.kind_code,
            self.strategy_version.logical_values(),
            self.state.value,
            self.authorization_state.value,
            self.confidence.logical_values() if self.confidence is not None else None,
            self.judgment_code,
            tuple(item.logical_values() for item in self.market_instruments),
            self.reason_codes,
            tuple(item.logical_values() for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class ExecutiveTradersReadModel:
    """Stable TRADERS projection for the authorized executive read boundary."""

    metadata: ExecutiveProjectionMetadata
    attention: ExecutiveAttentionLevel
    traders: tuple[ExecutiveTraderSummary, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.metadata, ExecutiveProjectionMetadata):
            raise ExecutiveReadModelValidationError(
                "traders read model requires ExecutiveProjectionMetadata"
            )
        if self.metadata.scope is not ExecutiveReadScope.TRADERS:
            raise ExecutiveReadModelValidationError(
                "traders projection requires TRADERS scope"
            )
        if not isinstance(self.attention, ExecutiveAttentionLevel):
            raise ExecutiveReadModelValidationError(
                "traders projection requires ExecutiveAttentionLevel"
            )
        if not isinstance(self.traders, tuple) or any(
            not isinstance(item, ExecutiveTraderSummary) for item in self.traders
        ):
            raise ExecutiveReadModelValidationError(
                "traders must be an immutable tuple of ExecutiveTraderSummary"
            )
        trader_ids = tuple(item.trader_id.value for item in self.traders)
        if len(set(trader_ids)) != len(trader_ids):
            raise ExecutiveReadModelValidationError(
                "traders projection must not contain duplicate trader ids"
            )
        object.__setattr__(
            self,
            "traders",
            tuple(sorted(self.traders, key=lambda item: item.trader_id.value)),
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.metadata.logical_values(),
            self.attention.value,
            tuple(item.logical_values() for item in self.traders),
        )
