"""Falsifiable DST/read-only contract for VT31 G5 wave2 before source request."""
from datetime import UTC, datetime
from inspect import getsource

from qore.infrastructure.trader_lab import vt31_g5_ustec_sb_quote_wave2_v1 as s


def test_frozen_eight_days_24_session_hours_no_fresh_holdout() -> None:
    assert s.DAYS_NY == (
        "2024-02-14", "2024-03-13", "2024-05-15", "2024-08-14",
        "2024-10-16", "2024-12-11", "2025-02-19", "2025-04-16",
    )
    assert len(s.frozen_windows()) == 24
    assert len({x["start_utc"] for x in s.frozen_windows()}) == 24
    assert s.MAX_REQUESTS_ALL == 300
    assert all(x["day_ny"][:4] in {"2024", "2025"} for x in s.frozen_windows())


def test_dst_exact_ny_clock_and_utc_hours() -> None:
    for w in s.frozen_windows():
        opened = datetime.fromisoformat(w["start_utc"])
        closed = datetime.fromisoformat(w["end_utc"])
        assert opened.tzinfo == UTC
        assert int((closed - opened).total_seconds()) == 3600
        assert datetime.fromisoformat(w["start_ny"]).hour in (3, 10, 14)
        assert datetime.fromisoformat(w["end_ny"]).hour in (4, 11, 15)
        ny_offset = datetime.fromisoformat(w["start_ny"]).utcoffset()
        assert ny_offset is not None
        assert int(ny_offset.total_seconds() / 3600) == s.EXPECTED_OFFSETS[w["day_ny"]]


def test_no_oms_order_submission_or_refresh_in_source_runner() -> None:
    source = getsource(s.capture)
    assert "ProtoOASymbolsListReq" in source
    assert "_native_fetch" in source
    for disallowed in ("ProtoOANewOrderReq", "ProtoOACancelOrderReq",
                       "ProtoOAAmendOrderReq", ".refresh_token(", "order_send("):
        assert disallowed not in source
    assert '"trades_replayed": 0' in source
    assert '"net_pnl_certified": False' in source
    assert '"fresh_holdout_accessed": False' in source
