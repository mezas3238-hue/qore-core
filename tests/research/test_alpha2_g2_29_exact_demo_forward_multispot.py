"""Synthetic-only exact 29 market source pilot checks; no broker login."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.research.alpha2_g2_29_exact_demo_forward_multispot import (
    MAX_EVENTS,
    PARTIAL,
    SIDE_MAX_AGE,
    SUCCESS,
    WINDOW_SECONDS,
    SourceBlockedError,
    _normalize,
    classify,
)
from qore.research.alpha2_g2_29_real_bidask_reuse import SOURCE_29

T=datetime(2026,10,12,19,0,tzinfo=UTC)


class StubSpot:
    def __init__(self,*,bid=None,ask=None,stamp=None):
        self.bid=bid
        self.ask=ask
        self.timestamp=stamp

    def HasField(self, key):  # noqa: N802 -- exact SDK protobuf fixture
        return getattr(self,key,None) is not None


def test_frozen_29_scope_and_bounded_run_no_alias_expansion():
    assert len(SOURCE_29)==29
    assert {"NZDUSD","NAS100","SP500","XAGUSD"}.isdisjoint(SOURCE_29)
    assert WINDOW_SECONDS==60
    assert MAX_EVENTS==120000
    assert SIDE_MAX_AGE==timedelta(seconds=5)
    assert SUCCESS!=PARTIAL


def test_exact_source_event_has_independent_bid_ask_and_dequeue_utc():
    source=StubSpot(bid=108225,
                    stamp=int((T-timedelta(milliseconds=20)).timestamp()*1000))
    d=_normalize(source,symbol="EURCHF",received_at=T,
                 sequence=0,local_sequence=0)
    assert d["native_bid_1e5"]==108225
    assert d["native_ask_1e5"] is None
    assert d["provider_event_at_ms"] is not None
    assert d["first_observed_by_runner_utc"]==T.isoformat()
    assert d["trade_fill_verified"] is False


def test_quotation_first_one_sided_missing_not_executable():
    assert classify(bid=100,ask=None,bid_at=T,ask_at=None,now=T
                    )=="MISSING_OR_STALE_SIDE"


def test_prior_side_exactly_five_seconds_admitted_six_seconds_rejected():
    assert classify(bid=100,ask=101,bid_at=T,ask_at=T,now=T+timedelta(seconds=5)
                    )=="POSITIVE_SPREAD_SOURCE_ONLY"
    assert classify(bid=100,ask=101,bid_at=T,ask_at=T,now=T+timedelta(seconds=6)
                    )=="MISSING_OR_STALE_SIDE"


def test_zero_and_crossed_quote_quarantined():
    assert classify(bid=100,ask=100,bid_at=T,ask_at=T,now=T
                    )=="ZERO_SPREAD_NO_FILL"
    assert classify(bid=101,ask=100,bid_at=T,ask_at=T,now=T
                    )=="CROSSED_SPREAD_NO_FILL"


def test_unverified_alias_or_wrong_symbol_fails_closed():
    with pytest.raises(SourceBlockedError,match="FROZEN29"):
        _normalize(StubSpot(bid=100),symbol="NAS100",received_at=T,
                   sequence=0,local_sequence=0)


def test_event_with_no_native_price_cannot_be_source():
    with pytest.raises(SourceBlockedError,match="BOTH_PRICE_SIDES_MISSING"):
        _normalize(StubSpot(),symbol="EURCHF",received_at=T,
                   sequence=0,local_sequence=0)


def test_event_with_future_provider_clock_is_rejected():
    future=int((T+timedelta(seconds=1)).timestamp()*1000)
    with pytest.raises(SourceBlockedError,match="TIMESTAMP_AFTER_RECEIPT"):
        _normalize(StubSpot(bid=100,stamp=future),symbol="EURCHF",
                   received_at=T,sequence=0,local_sequence=0)


def test_future_first_seen_side_fails_even_if_comparator_thinks_fresh():
    with pytest.raises(SourceBlockedError,match="SIDE_FROM_FUTURE"):
        classify(bid=100,ask=101,bid_at=T+timedelta(seconds=1),
                 ask_at=T,now=T)
