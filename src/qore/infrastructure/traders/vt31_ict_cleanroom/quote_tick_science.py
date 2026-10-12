"""One-VT31 passive historical quote evidence; NEVER a trade or fill simulator.

Read-only tick contract and fingerprinted CSV audit. A quote crossing CE is
NOT a broker ACK/fill, and a different NAS100/NDX100 quote instrument cannot
be backfilled into a 3Y source without independently evidenced identity.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Iterator

from .contracts import Side

SCHEMA = "qore.vt31.quote_tick_evidence.read_only.v1"
FIELDS = ("time_msc", "bid", "ask", "flags", "symbol")
KNOWN_SOURCE_SHA = "0563370fd021ad091392eb26f60cda0d3356d38c801fc1c2083cceafc5043cfa"


def _finite_positive(value: str, field: str) -> Decimal:
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field} numeric quote") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"invalid {field} nonpositive/nonfinite quote")
    return number


def _utc_milliseconds(milliseconds: int) -> datetime:
    sec, remainder = divmod(milliseconds, 1000)
    return datetime.fromtimestamp(sec, tz=UTC) + timedelta(
        milliseconds=remainder
    )


def _ms_utc(time: datetime) -> int:
    if time.tzinfo is None or time.utcoffset() is None:
        raise ValueError("naive datetime forbidden")
    at = time.astimezone(UTC)
    if at.microsecond % 1000:
        raise ValueError("submillisecond timestamps cannot be fabricated")
    return (at.toordinal() - datetime(1970, 1, 1, tzinfo=UTC).toordinal()) * 86400000 + (
        at.hour * 3600000 + at.minute * 60000
        + at.second * 1000 + at.microsecond // 1000
    )


@dataclass(frozen=True, slots=True)
class BidAskTick:
    symbol: str
    time_msc: int
    bid: Decimal
    ask: Decimal
    flags: int

    def __post_init__(self) -> None:
        if not self.symbol or not isinstance(self.time_msc, int) or (
            self.time_msc <= 0
        ) or not isinstance(self.flags, int) or self.flags < 0:
            raise ValueError("invalid source symbol, UTC millisecond, or flag")
        if (
            not self.bid.is_finite() or not self.ask.is_finite()
            or self.bid <= 0 or self.ask < self.bid
        ):
            raise ValueError("invalid bid/ask price or inverted quote")

    @property
    def at(self) -> datetime:
        return _utc_milliseconds(self.time_msc)

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    @classmethod
    def from_csv(cls, row: dict[str, str]) -> BidAskTick:
        if tuple(row) != FIELDS:
            raise ValueError("quote CSV fields do not match frozen native contract")
        try:
            time_msc = int(row["time_msc"])
            flags = int(row["flags"])
        except (ValueError, TypeError) as exc:
            raise ValueError("bad millisecond or flags integer") from exc
        return cls(
            symbol=row["symbol"],
            time_msc=time_msc,
            bid=_finite_positive(row["bid"], "bid"),
            ask=_finite_positive(row["ask"], "ask"),
            flags=flags,
        )


@dataclass(frozen=True, slots=True)
class TickSourceContract:
    """Public instrument spec; NEVER account ID, token, password or file path."""

    source: str
    broker: str
    server_alias: str
    symbol: str
    digits: int
    point: Decimal
    tick_size: Decimal
    contract_size: Decimal
    currency_profit: str
    requested_start_msc: int
    requested_end_msc: int

    def __post_init__(self) -> None:
        if (
            not all((
                self.source, self.broker, self.server_alias,
                self.symbol, self.currency_profit
            ))
            or self.requested_start_msc >= self.requested_end_msc
            or not 0 <= self.digits <= 10
            or any(
                not x.is_finite() or x <= 0
                for x in (self.point, self.tick_size, self.contract_size)
            )
        ):
            raise ValueError("broker/symbol identity and contract fields required")
        if self.source != "MT5_COPY_TICKS_INFO_READ_ONLY":
            raise ValueError("evidence source must be native MT5 read-only ticks")


def read_ticks_gzip(
    compressed: bytes, *, required_symbol: str,
) -> Iterator[BidAskTick]:
    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as gz:
        with io.TextIOWrapper(gz, encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise ValueError("wrong quote CSV header")
            for row in reader:
                tick = BidAskTick.from_csv(row)
                if tick.symbol != required_symbol:
                    raise ValueError("foreign symbol in a single-symbol tick file")
                yield tick


def audit_quote_gzip(
    compressed: bytes, contract: TickSourceContract,
    *, major_gap_ms: int = 60000,
) -> dict[str, Any]:
    if not compressed:
        raise ValueError("empty gzip bytes are not evidence")
    if major_gap_ms <= 0:
        raise ValueError("positive gap threshold required")
    raw_sha256 = hashlib.sha256(compressed).hexdigest()
    first: BidAskTick | None = None
    prev: BidAskTick | None = None
    total = 0
    equal_ms = 0
    biggest_gap = 0
    big_gaps = 0
    max_spread = Decimal("0")
    min_spread: Decimal | None = None
    days: Counter[str] = Counter()
    for tick in read_ticks_gzip(
        compressed, required_symbol=contract.symbol
    ):
        if not (
            contract.requested_start_msc <= tick.time_msc
            < contract.requested_end_msc
        ):
            raise ValueError("tick falls outside requested half-open UTC period")
        if prev is not None:
            delta = tick.time_msc - prev.time_msc
            if delta < 0:
                raise ValueError("nonchronological quote ticks")
            if delta == 0:
                equal_ms += 1
            if delta > major_gap_ms:
                big_gaps += 1
            biggest_gap = max(biggest_gap, delta)
        if first is None:
            first = tick
        prev = tick
        total += 1
        max_spread = max(max_spread, tick.spread)
        min_spread = (
            tick.spread if min_spread is None
            else min(min_spread, tick.spread)
        )
        days[tick.at.date().isoformat()] += 1
    return {
        "schema": SCHEMA,
        "source": contract.source,
        "broker": contract.broker,
        "server_alias": contract.server_alias,
        "symbol": contract.symbol,
        "digits": contract.digits,
        "point": str(contract.point),
        "trade_tick_size": str(contract.tick_size),
        "trade_contract_size": str(contract.contract_size),
        "currency_profit": contract.currency_profit,
        "requested_start_utc": _utc_milliseconds(
            contract.requested_start_msc
        ).isoformat(),
        "requested_end_exclusive_utc": _utc_milliseconds(
            contract.requested_end_msc
        ).isoformat(),
        "quote_gzip_sha256": raw_sha256,
        "valid_two_sided_quote_count": total,
        "first_actual_tick_utc": first.at.isoformat() if first else None,
        "last_actual_tick_utc": prev.at.isoformat() if prev else None,
        "same_millisecond_tick_pairs": equal_ms,
        "gaps_over_threshold_ms": big_gaps,
        "largest_consecutive_tick_gap_ms": biggest_gap,
        "min_observed_spread_price_units": (
            str(min_spread) if min_spread is not None else None
        ),
        "max_observed_spread_price_units": (
            str(max_spread) if first else None
        ),
        "actual_UTC_days_with_ticks": dict(sorted(days.items())),
        "complete_requested_history_proven": False,
        "broker_fills_proven": 0,
        "market_source_matches_original_NAS100": False,
        "replaces_unresolved_A_B_M1_cases": False,
        "live_authorized": False,
        "certified": False,
    }


class QuoteCEEvidence(StrEnum):
    SOURCE_IDENTITY_NOT_VERIFIED = "SOURCE_IDENTITY_NOT_VERIFIED"
    MISSING_CANCELLATION_TIME = "MISSING_CANCELLATION_TIME"
    MISSING_COMPLETE_QUOTE_COVERAGE = "MISSING_COMPLETE_QUOTE_COVERAGE"
    SAME_MILLISECOND_CANCEL_CROSS_AMBIGUOUS = (
        "SAME_MILLISECOND_CANCEL_CROSS_AMBIGUOUS"
    )
    QUOTE_CROSSED_CE_NO_BROKER_FILL = "QUOTE_CROSSED_CE_NO_BROKER_FILL"
    NO_CE_CROSS_OBSERVED_NO_NEGATIVE_PROOF = (
        "NO_CE_CROSS_OBSERVED_NO_NEGATIVE_PROOF"
    )


def compare_quote_ce(
    *,
    ticks: tuple[BidAskTick, ...],
    source_symbol: str,
    validated_market_symbol: str | None,
    side: Side,
    ce: Decimal,
    offered_at: datetime,
    cancel_at: datetime | None,
    expires_at: datetime,
    coverage_prevalidated: bool = False,
) -> QuoteCEEvidence:
    """Conservative quote CE evidence, never a fill or unknown->win mutation.

    "validated_market_symbol" must come from independent signed source
    equivalence review; a literal mapping NAS100=NDX100 is NOT inferred.
    Even if all quote ticks are good, matching/ACK evidence remains absent.
    """
    if validated_market_symbol != source_symbol or not ticks or (
        any(t.symbol != validated_market_symbol for t in ticks)
    ):
        return QuoteCEEvidence.SOURCE_IDENTITY_NOT_VERIFIED
    if cancel_at is None:
        return QuoteCEEvidence.MISSING_CANCELLATION_TIME
    start = _ms_utc(offered_at)
    end = min(_ms_utc(cancel_at), _ms_utc(expires_at))
    if start >= end or not coverage_prevalidated:
        return QuoteCEEvidence.MISSING_COMPLETE_QUOTE_COVERAGE
    if not ce.is_finite() or ce <= 0:
        raise ValueError("invalid original as-of CE")
    prev_ms: int | None = None
    crossed = False
    same_cancel_ms = False
    for t in ticks:
        if prev_ms is not None and t.time_msc < prev_ms:
            raise ValueError("out-of-order price evidence")
        prev_ms = t.time_msc
        active_side = t.ask if side is Side.LONG else t.bid
        crossed_here = (
            active_side <= ce if side is Side.LONG else active_side >= ce
        )
        if crossed_here and t.time_msc == end:
            same_cancel_ms = True
        if start < t.time_msc < end and crossed_here:
            crossed = True
    if crossed:
        return QuoteCEEvidence.QUOTE_CROSSED_CE_NO_BROKER_FILL
    if same_cancel_ms:
        return QuoteCEEvidence.SAME_MILLISECOND_CANCEL_CROSS_AMBIGUOUS
    return QuoteCEEvidence.NO_CE_CROSS_OBSERVED_NO_NEGATIVE_PROOF
