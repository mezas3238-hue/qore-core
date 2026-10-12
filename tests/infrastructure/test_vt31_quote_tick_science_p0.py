"""VT31 P0: adversarial passive BID/ASK source gates (no simulated fills)."""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import Side
from qore.infrastructure.traders.vt31_ict_cleanroom.quote_tick_science import (
    BidAskTick,
    QuoteCEEvidence,
    TickSourceContract,
    audit_quote_gzip,
    compare_quote_ce,
)

START = 1791813600000  # fixed UTC-ms origin; not a claimed market observation


def _contract(*, symbol: str = "NDX100") -> TickSourceContract:
    return TickSourceContract(
        source="MT5_COPY_TICKS_INFO_READ_ONLY",
        broker="BROKER_UNVERIFIED_TEST_ONLY",
        server_alias="SYNTHETIC_TEST_ONLY",
        symbol=symbol,
        digits=2,
        point=Decimal("0.01"),
        tick_size=Decimal("0.01"),
        contract_size=Decimal("1"),
        currency_profit="USD",
        requested_start_msc=START,
        requested_end_msc=START + 120_000,
    )


def _gz(rows: list[tuple[object, object, object, object, object]],
        *, header: tuple[str, ...] = ("time_msc", "bid", "ask", "flags", "symbol")) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(header)
    writer.writerows(rows)
    return gzip.compress(stream.getvalue().encode("utf-8"), mtime=0)


def _row(ms: int, bid: object = "100", ask: object = "101",
         flags: object = 0, symbol: object = "NDX100") -> tuple[object, ...]:
    return (ms, bid, ask, flags, symbol)


def _tick(ms: int, bid: str = "100", ask: str = "101",
          symbol: str = "NAS100") -> BidAskTick:
    return BidAskTick(symbol, ms, Decimal(bid), Decimal(ask), 0)


def _time(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def _compare(*, side: Side, ce: str, ticks: tuple[BidAskTick, ...],
             source_symbol: str = "NAS100",
             validated_market_symbol: str | None = "NAS100",
             cancel_ms: int | None = START + 4000,
             expire_ms: int = START + 5000,
             coverage: bool = True) -> QuoteCEEvidence:
    return compare_quote_ce(
        ticks=ticks,
        source_symbol=source_symbol,
        validated_market_symbol=validated_market_symbol,
        side=side,
        ce=Decimal(ce),
        offered_at=_time(START),
        cancel_at=None if cancel_ms is None else _time(cancel_ms),
        expires_at=_time(expire_ms),
        coverage_prevalidated=coverage,
    )


def test_native_gzip_fingerprints_and_counts_but_does_not_certify_coverage() -> None:
    rows = [_row(START, "100", "101"), _row(START, "100", "102"),
            _row(START + 70_001, "101", "101")]
    payload = _gz(rows)
    report = audit_quote_gzip(payload, _contract(), major_gap_ms=60_000)
    assert report["quote_gzip_sha256"] == hashlib.sha256(payload).hexdigest()
    assert report["valid_two_sided_quote_count"] == 3
    assert report["same_millisecond_tick_pairs"] == 1
    assert report["gaps_over_threshold_ms"] == 1
    assert report["largest_consecutive_tick_gap_ms"] == 70_001
    assert report["min_observed_spread_price_units"] == "0"
    assert report["max_observed_spread_price_units"] == "2"
    assert report["complete_requested_history_proven"] is False
    assert report["broker_fills_proven"] == 0
    assert report["market_source_matches_original_NAS100"] is False
    assert report["certified"] is False
    assert report["live_authorized"] is False


@pytest.mark.parametrize("rows,error", [
    ([_row(START, "101", "100")], "inverted quote"),
    ([_row(START, "NaN", "101")], "nonpositive/nonfinite"),
    ([_row(START, "-1", "101")], "nonpositive/nonfinite"),
    ([_row(START, "100", "101", -1)], "flag"),
    ([_row(START, "100", "101", 0, "NAS100")], "foreign symbol"),
    ([_row(START + 20), _row(START + 10)], "nonchronological"),
    ([_row(START - 1)], "outside requested"),
    ([_row(START + 120_000)], "outside requested"),
])
def test_bad_ticks_never_become_valid_evidence(
    rows: list[tuple[object, ...]], error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        audit_quote_gzip(_gz(rows), _contract())


def test_reject_wrong_column_order_corrupt_gzip_and_bad_threshold() -> None:
    with pytest.raises(ValueError, match="wrong quote CSV header"):
        audit_quote_gzip(
            _gz([_row(START)], header=("bid", "time_msc", "ask", "flags", "symbol")),
            _contract(),
        )
    with pytest.raises((OSError, EOFError, gzip.BadGzipFile)):
        audit_quote_gzip(b"this is not gzip", _contract())
    with pytest.raises(ValueError, match="positive gap"):
        audit_quote_gzip(_gz([_row(START)]), _contract(), major_gap_ms=0)


def test_header_only_is_zero_observations_not_coverage() -> None:
    audit = audit_quote_gzip(_gz([]), _contract())
    assert audit["valid_two_sided_quote_count"] == 0
    assert audit["first_actual_tick_utc"] is None
    assert audit["complete_requested_history_proven"] is False


def test_source_requires_validated_symbol_and_does_not_infer_alias() -> None:
    tick = _tick(START + 1000, "99", "100", symbol="NDX100")
    assert _compare(side=Side.LONG, ce="100", ticks=(tick,)) == (
        QuoteCEEvidence.SOURCE_IDENTITY_NOT_VERIFIED
    )
    # Simply typing NDX100 as a validated label is not source equivalence.
    assert _compare(
        side=Side.LONG, ce="100", ticks=(tick,),
        validated_market_symbol="NDX100",
    ) == QuoteCEEvidence.SOURCE_IDENTITY_NOT_VERIFIED


def test_long_buy_limit_uses_ask_never_bid() -> None:
    assert _compare(
        side=Side.LONG, ce="100", ticks=(_tick(START + 1000, "100", "101"),),
    ) == QuoteCEEvidence.NO_CE_CROSS_OBSERVED_NO_NEGATIVE_PROOF
    assert _compare(
        side=Side.LONG, ce="100", ticks=(_tick(START + 1000, "99", "100"),),
    ) == QuoteCEEvidence.QUOTE_CROSSED_CE_NO_BROKER_FILL


def test_short_sell_limit_uses_bid_never_ask() -> None:
    assert _compare(
        side=Side.SHORT, ce="101", ticks=(_tick(START + 1000, "100", "101"),),
    ) == QuoteCEEvidence.NO_CE_CROSS_OBSERVED_NO_NEGATIVE_PROOF
    assert _compare(
        side=Side.SHORT, ce="101", ticks=(_tick(START + 1000, "101", "102"),),
    ) == QuoteCEEvidence.QUOTE_CROSSED_CE_NO_BROKER_FILL


def test_coverage_and_cancel_required_even_when_quote_crosses() -> None:
    tick = _tick(START + 1000, "99", "100")
    assert _compare(
        side=Side.LONG, ce="100", ticks=(tick,), coverage=False,
    ) == QuoteCEEvidence.MISSING_COMPLETE_QUOTE_COVERAGE
    assert _compare(
        side=Side.LONG, ce="100", ticks=(tick,), cancel_ms=None,
    ) == QuoteCEEvidence.MISSING_CANCELLATION_TIME


def test_cross_exactly_at_cancel_time_is_ambiguous_not_fill() -> None:
    assert _compare(
        side=Side.LONG, ce="100", ticks=(_tick(START + 4000, "99", "100"),),
    ) == QuoteCEEvidence.SAME_MILLISECOND_CANCEL_CROSS_AMBIGUOUS


def test_cross_at_expiry_timestamp_is_conservatively_ambiguous() -> None:
    assert _compare(
        side=Side.LONG, ce="100",
        ticks=(_tick(START + 3000, "99", "100"),),
        cancel_ms=START + 6000, expire_ms=START + 3000,
    ) == QuoteCEEvidence.SAME_MILLISECOND_CANCEL_CROSS_AMBIGUOUS


def test_quote_after_cancellation_is_not_a_valid_contact() -> None:
    assert _compare(
        side=Side.LONG, ce="100",
        ticks=(_tick(START + 4500, "99", "100"),),
    ) == QuoteCEEvidence.NO_CE_CROSS_OBSERVED_NO_NEGATIVE_PROOF


def test_out_of_order_quote_stream_rejected() -> None:
    with pytest.raises(ValueError, match="out-of-order"):
        _compare(
            side=Side.LONG, ce="100",
            ticks=(_tick(START + 2000), _tick(START + 1000)),
        )


def test_naive_and_submillisecond_decision_timestamps_forbidden() -> None:
    tick = _tick(START + 1000)
    args = dict(
        ticks=(tick,), source_symbol="NAS100",
        validated_market_symbol="NAS100",
        side=Side.LONG, ce=Decimal("100"),
        cancel_at=_time(START + 4000),
        expires_at=_time(START + 5000),
        coverage_prevalidated=True,
    )
    with pytest.raises(ValueError, match="naive"):
        compare_quote_ce(offered_at=datetime(2026, 10, 12, 14), **args)
    with pytest.raises(ValueError, match="submillisecond"):
        compare_quote_ce(
            offered_at=_time(START) + timedelta(microseconds=1), **args,
        )


def test_contract_never_accepts_non_native_pseudoticks() -> None:
    with pytest.raises(ValueError, match="native MT5"):
        TickSourceContract(
            source="SYNTHETIC_OHLC", broker="test", server_alias="test",
            symbol="NDX100", digits=2, point=Decimal(".01"),
            tick_size=Decimal(".01"), contract_size=Decimal("1"),
            currency_profit="USD", requested_start_msc=START,
            requested_end_msc=START + 1000,
        )
