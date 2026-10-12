"""Synthetic, broker-off tests for NZDUSD forward DEMO received-at source pilot."""
from datetime import UTC, datetime, timedelta

import pytest

from qore.research.alpha2_g2_nzdusd_forward_spot_receipt import (
    MAX_SIDE_AGE,
    SourceBlockedError,
    classify_received_pair,
    normalize_spot_event,
)

T = datetime(2026, 10, 12, 18, 0, tzinfo=UTC)
SYM = 12345


class FakeEvent:
    def __init__(self, *, bid=None, ask=None, stamp=None, symbol=SYM):
        self.symbolId=symbol
        self.bid=bid
        self.ask=ask
        self.timestamp=stamp

    def HasField(self, key):  # noqa: N802 -- exact protobuf API fixture
        return getattr(self,key,None) is not None


def test_receipt_after_async_event_dequeue_preserves_pit_two_sides():
    timestamp=int((T-timedelta(milliseconds=50)).timestamp()*1000)
    x=normalize_spot_event(
        FakeEvent(bid=105500,stamp=timestamp),
        expected_symid=SYM,received_at=T,sequence=0,
    )
    assert x["first_observed_by_runner_utc"]==T.isoformat()
    assert x["provider_event_at_ms"]==timestamp
    assert x["native_bid_1e5"]==105500
    assert x["native_ask_1e5"] is None
    assert x["event_is_NOT_fill"] is True


def test_partial_bid_ask_events_cannot_become_simultaneous_quote():
    x=normalize_spot_event(FakeEvent(ask=105510),expected_symid=SYM,
                           received_at=T,sequence=1)
    assert x["native_bid_1e5"] is None
    assert x["native_ask_1e5"]==105510
    assert x["provider_event_at_ms"] is None
    assert classify_received_pair(
        bid=None,ask=105510,bid_seen=None,ask_seen=T,now=T
    )=="MISSING_OR_STALE_BIDASK"


def test_quote_age_max_five_seconds_and_zero_crossed_quarantine():
    assert classify_received_pair(
        bid=100,ask=101,bid_seen=T,ask_seen=T+timedelta(seconds=5),
        now=T+timedelta(seconds=5)
    )=="POSITIVE_SPREAD_OBSERVATION_NO_FILL"
    assert classify_received_pair(
        bid=100,ask=101,bid_seen=T,ask_seen=T+timedelta(seconds=5, milliseconds=1),
        now=T+timedelta(seconds=5, milliseconds=1)
    )=="MISSING_OR_STALE_BIDASK"
    assert classify_received_pair(
        bid=100,ask=100,bid_seen=T,ask_seen=T,now=T
    )=="ZERO_QUOTE_QUARANTINED"
    assert classify_received_pair(
        bid=101,ask=100,bid_seen=T,ask_seen=T,now=T
    )=="CROSSED_QUOTE_QUARANTINED"
    assert MAX_SIDE_AGE==timedelta(seconds=5)


def test_wrong_provider_symbol_id_blocked_not_remapped():
    with pytest.raises(SourceBlockedError,match="SYMBOL_ID_CHANGED"):
        normalize_spot_event(
            FakeEvent(bid=105500,symbol=54321),
            expected_symid=SYM,received_at=T,sequence=0,
        )


def test_future_provider_stamp_is_rejected_not_backfilled():
    future=int((T+timedelta(milliseconds=1)).timestamp()*1000)
    with pytest.raises(SourceBlockedError,match="FUTURE"):
        normalize_spot_event(FakeEvent(bid=105500,stamp=future),
                             expected_symid=SYM,received_at=T,sequence=0)


def test_missing_quote_sides_are_not_replaced_by_zeros():
    with pytest.raises(SourceBlockedError,match="SIDE_VALUES_ABSENT"):
        normalize_spot_event(FakeEvent(),expected_symid=SYM,
                             received_at=T,sequence=0)
    with pytest.raises(SourceBlockedError,match="SIDE_VALUES_ABSENT"):
        normalize_spot_event(FakeEvent(bid=0),expected_symid=SYM,
                             received_at=T,sequence=0)


def test_boolean_and_negative_native_bidask_fail_closed():
    with pytest.raises(SourceBlockedError,match="INTEGER_INVALID"):
        normalize_spot_event(FakeEvent(bid=True),
                             expected_symid=SYM,received_at=T,sequence=0)
    with pytest.raises(SourceBlockedError,match="INTEGER_INVALID"):
        normalize_spot_event(FakeEvent(bid=-1),
                             expected_symid=SYM,received_at=T,sequence=0)


def test_naive_clock_rejected():
    with pytest.raises(SourceBlockedError,match="NOT_UTC"):
        normalize_spot_event(FakeEvent(bid=105500),
                             expected_symid=SYM,
                             received_at=datetime(2026,10,12),sequence=0)
