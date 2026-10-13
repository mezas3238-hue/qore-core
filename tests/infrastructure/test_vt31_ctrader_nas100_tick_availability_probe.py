"""Pure synthetic fail-closed contract tests; NEVER connects or sends orders."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from qore.kernel.result import Success
from scripts.vt31_ctrader_nas100_tick_availability_probe import (
    ALLOWED_READ_MESSAGES,
    PilotDataError,
    ProbeWindow,
    decode_response,
    pilot_windows,
    read_pilot,
)

START = datetime(2024, 10, 8, 14, 0, tzinfo=UTC)
WINDOW = ProbeWindow("synthetic", START, START + timedelta(minutes=15))


class FakeClient:
    is_ready = True
    account_id = 42

    def __init__(self, *, missing_ask=False, no_symbol=False, more=False, corrupted=False):
        self.calls: list[str] = []
        self.missing_ask = missing_ask
        self.no_symbol = no_symbol
        self.more = more
        self.corrupted = corrupted

    def request(self, message_name, fields, *, client_msg_id, timeout_seconds):
        del client_msg_id, timeout_seconds
        self.calls.append(message_name)
        assert message_name in ALLOWED_READ_MESSAGES
        assert fields["ctidTraderAccountId"] == self.account_id
        if message_name == "ProtoOASymbolsListReq":
            symbol = (
                [] if self.no_symbol else
                [SimpleNamespace(symbolName="NAS100", enabled=True, symbolId=987)]
            )
            return Success(SimpleNamespace(
                ctidTraderAccountId=self.account_id, symbol=symbol,
            ))
        if message_name == "ProtoOASymbolByIdReq":
            assert fields["symbolId"] == [987]
            return Success(SimpleNamespace(
                ctidTraderAccountId=self.account_id,
                symbol=[SimpleNamespace(symbolId=987, digits=2)],
            ))
        assert message_name == "ProtoOAGetTickDataReq"
        assert fields["symbolId"] == 987
        assert fields["type"] in (1, 2)
        assert fields["toTimestamp"] - fields["fromTimestamp"] == 900_000
        if fields["type"] == 2 and self.missing_ask:
            ticks = []
        else:
            newest = fields["fromTimestamp"] + 600_000
            delta = 999_999_999 if self.corrupted else 180_000
            ticks = [
                SimpleNamespace(timestamp=newest, tick=3_080_000_000),
                SimpleNamespace(timestamp=delta, tick=3_079_900_000),
            ]
        return Success(SimpleNamespace(
            ctidTraderAccountId=self.account_id,
            hasMore=self.more, tickData=ticks,
        ))


def test_realistic_synthetic_read_only_pilot_does_not_claim_edge() -> None:
    fake = FakeClient()
    r = read_pilot(fake, symbol_name="NAS100", windows=(WINDOW,))
    assert r["status"] == "PILOT_BOTH_SIDES_PRESENT_NONCERTIFIED"
    assert r["pilot_15min_windows"][0]["bid"]["count"] == 2
    assert r["pilot_15min_windows"][0]["ask"]["count"] == 2
    assert r["executions"] == 0
    assert r["three_year_coverage_verified"] is False
    assert r["broker_matches_original_m1_verified"] is False
    assert r["edge_economic"] == "NOT_IDENTIFIED"
    assert fake.calls == [
        "ProtoOASymbolsListReq", "ProtoOASymbolByIdReq",
        "ProtoOAGetTickDataReq", "ProtoOAGetTickDataReq",
    ]


def test_absent_exact_broker_symbol_never_tries_tick_or_substitute_us100() -> None:
    fake = FakeClient(no_symbol=True)
    r = read_pilot(fake, symbol_name="NAS100", windows=(WINDOW,))
    assert r["status"] == "BLOCKED_EXACT_SYMBOL_ABSENT_OR_AMBIGUOUS"
    assert fake.calls == ["ProtoOASymbolsListReq"]


def test_no_ask_must_block_two_sided_coverage() -> None:
    r = read_pilot(FakeClient(missing_ask=True), symbol_name="NAS100", windows=(WINDOW,))
    assert r["status"] == "HISTORICAL_SAMPLE_GAPS"


def test_has_more_blocks_full_interval_claims() -> None:
    r = read_pilot(FakeClient(more=True), symbol_name="NAS100", windows=(WINDOW,))
    assert r["status"] == "SAMPLE_PAGINATION_REQUIRED"


def test_invalid_delta_is_rejected_not_silently_clamped() -> None:
    with pytest.raises(PilotDataError, match="TICK_OUTSIDE_REQUEST_WINDOW"):
        read_pilot(FakeClient(corrupted=True), symbol_name="NAS100", windows=(WINDOW,))


def test_cross_account_ticks_rejected() -> None:
    result = SimpleNamespace(
        ctidTraderAccountId=999, hasMore=False, tickData=[],
    )
    with pytest.raises(PilotDataError, match="ACCOUNT_MISMATCH"):
        decode_response(result, window=WINDOW, account_id=42)


def test_one_week_vendor_limit_and_utc_precondition() -> None:
    with pytest.raises(PilotDataError, match="limited to one week"):
        ProbeWindow("bad", START, START + timedelta(days=8))
    with pytest.raises(PilotDataError, match="UTC sample"):
        ProbeWindow("naive", datetime(2026, 1, 1), datetime(2026, 1, 2))


def test_four_samples_across_three_year_development_are_not_full_coverage() -> None:
    windows = pilot_windows()
    assert len(windows) == 4
    assert windows[0].opened.year == 2023
    assert windows[-1].opened.year == 2026
    assert all(w.closed - w.opened == timedelta(minutes=15) for w in windows)
    assert len({w.opened for w in windows}) == 4


def test_invalid_symbol_and_empty_samples_fail_closed() -> None:
    fake = FakeClient()
    with pytest.raises(PilotDataError, match="EXACT_BROKER_SYMBOL"):
        read_pilot(fake, symbol_name="NAS100.suffix", windows=(WINDOW,))
    with pytest.raises(PilotDataError, match="PROBE_WINDOWS"):
        read_pilot(fake, symbol_name="NAS100", windows=())
    assert fake.calls == []
