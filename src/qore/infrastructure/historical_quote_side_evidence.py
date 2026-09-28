"""Historical quote-side evidence for Active Perception research.

Historical provider evidence is not live Core ingress. This boundary preserves
provider event time separately from retrieval time and retains BID/ASK as
independent event streams. It never manufactures a paired quote.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.ctrader_historical_tick_data import (
    CTraderHistoricalTickPage,
    CTraderQuoteType,
)
from qore.infrastructure.market_data import Instrument
from qore.infrastructure.market_observation import MarketPrice, MarketPriceSide
from qore.infrastructure.ports import ExternalPortError, ExternalSourceDescriptor


class HistoricalQuoteSideEvidenceError(ExternalPortError):
    """Historical quote-side provenance violates the research contract."""


class HistoricalReplayAvailabilityBasis(StrEnum):
    """What timestamp may make evidence visible during historical replay."""

    PROVIDER_EVENT_TIME = "provider_event_time"


def _utc(value: datetime, *, field_name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise HistoricalQuoteSideEvidenceError(
            f"{field_name} must be a timezone-aware datetime"
        )
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class HistoricalQuoteSideObservation:
    """One immutable historical provider-side quote event.

    provider_event_at is the historical market timestamp. retrieved_at states
    when Core actually obtained the historical evidence. The former may drive
    point-in-time research replay; the latter must never be rewritten to
    pretend that Core ingested the event live in the past.
    """

    instrument: Instrument
    source: ExternalSourceDescriptor
    provider_account_id: int
    provider_symbol_id: int
    provider_symbol: str
    quote_side: MarketPriceSide
    provider_event_at: datetime
    retrieved_at: datetime
    relative_price: int
    price: MarketPrice
    availability_basis: HistoricalReplayAvailabilityBasis = (
        HistoricalReplayAvailabilityBasis.PROVIDER_EVENT_TIME
    )

    def __post_init__(self) -> None:
        if not isinstance(self.instrument, Instrument):
            raise HistoricalQuoteSideEvidenceError(
                "historical quote instrument must be Instrument"
            )
        if not isinstance(self.source, ExternalSourceDescriptor):
            raise HistoricalQuoteSideEvidenceError(
                "historical quote source must be ExternalSourceDescriptor"
            )
        port_name = self.source.port_name.value
        if port_name != "market-data" and not port_name.startswith("market-data."):
            raise HistoricalQuoteSideEvidenceError(
                "historical quote source must use market-data namespace"
            )
        if type(self.provider_account_id) is not int or self.provider_account_id <= 0:
            raise HistoricalQuoteSideEvidenceError(
                "provider_account_id must be a positive int"
            )
        if type(self.provider_symbol_id) is not int or self.provider_symbol_id <= 0:
            raise HistoricalQuoteSideEvidenceError(
                "provider_symbol_id must be a positive int"
            )
        if (
            not isinstance(self.provider_symbol, str)
            or not self.provider_symbol
            or self.provider_symbol != self.provider_symbol.strip()
        ):
            raise HistoricalQuoteSideEvidenceError(
                "provider_symbol must be a non-empty trimmed string"
            )
        if self.quote_side not in (MarketPriceSide.BID, MarketPriceSide.ASK):
            raise HistoricalQuoteSideEvidenceError(
                "historical quote side must be BID or ASK"
            )
        provider_event_at = _utc(
            self.provider_event_at,
            field_name="provider_event_at",
        )
        retrieved_at = _utc(self.retrieved_at, field_name="retrieved_at")
        if retrieved_at < provider_event_at:
            raise HistoricalQuoteSideEvidenceError(
                "retrieved_at must not predate provider_event_at"
            )
        if type(self.relative_price) is not int or self.relative_price <= 0:
            raise HistoricalQuoteSideEvidenceError(
                "relative_price must be a positive int"
            )
        if not isinstance(self.price, MarketPrice):
            raise HistoricalQuoteSideEvidenceError(
                "historical quote price must be MarketPrice"
            )
        if (
            self.availability_basis
            is not HistoricalReplayAvailabilityBasis.PROVIDER_EVENT_TIME
        ):
            raise HistoricalQuoteSideEvidenceError(
                "historical replay availability must use provider event time"
            )

    @property
    def replay_available_at(self) -> datetime:
        """Historical research visibility time, not a live Core-ingress claim."""

        return self.provider_event_at.astimezone(UTC)

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.instrument.symbol,
            self.source.logical_values(),
            self.provider_account_id,
            self.provider_symbol_id,
            self.provider_symbol,
            self.quote_side.value,
            self.provider_event_at.astimezone(UTC).isoformat(
                timespec="microseconds"
            ),
            self.retrieved_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.relative_price,
            self.price.canonical,
            self.availability_basis.value,
        )


def retain_ctrader_historical_quote_side_page(
    *,
    page: CTraderHistoricalTickPage,
    instrument: Instrument,
    source: ExternalSourceDescriptor,
    provider_symbol: str,
    retrieved_at: datetime,
) -> tuple[HistoricalQuoteSideObservation, ...]:
    """Retain one cTrader page without pairing or synthesizing the opposite side."""

    if not isinstance(page, CTraderHistoricalTickPage):
        raise HistoricalQuoteSideEvidenceError(
            "page must be CTraderHistoricalTickPage"
        )
    retrieval_time = _utc(retrieved_at, field_name="retrieved_at")
    if page.request.quote_type is CTraderQuoteType.BID:
        side = MarketPriceSide.BID
    elif page.request.quote_type is CTraderQuoteType.ASK:
        side = MarketPriceSide.ASK
    else:  # pragma: no cover - enum is closed by request validation
        raise HistoricalQuoteSideEvidenceError("unsupported cTrader quote side")

    retained: list[HistoricalQuoteSideObservation] = []
    for tick in page.ticks:
        if tick.quote_type is not page.request.quote_type:
            raise HistoricalQuoteSideEvidenceError(
                "tick quote side does not match page request"
            )
        retained.append(
            HistoricalQuoteSideObservation(
                instrument=instrument,
                source=source,
                provider_account_id=page.request.account_id,
                provider_symbol_id=page.request.symbol_id,
                provider_symbol=provider_symbol,
                quote_side=side,
                provider_event_at=tick.observed_at,
                retrieved_at=retrieval_time,
                relative_price=tick.relative_price,
                price=MarketPrice(tick.price),
            )
        )
    return tuple(retained)
