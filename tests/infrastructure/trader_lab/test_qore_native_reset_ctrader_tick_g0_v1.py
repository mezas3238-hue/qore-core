"""No-network native cTrader DEMO tick source tests for QORE RESET G0."""
from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from qore.infrastructure.trader_lab import qore_native_reset_ctrader_tick_g0_v1 as g


def test_fixed_only_provider_post2015_dates() -> None:
    dates = g.probe_dates()
    assert len(dates) == 12
    assert [v.year for v in dates] == list(range(2015, 2027))
    assert dates[0] == date(2015, 9, 15)
    assert all(v.weekday() == 1 and v.day >= 15 and v.month == 9 for v in dates)
    assert g.QUOTE_TYPES == {"BID": 1, "ASK": 2}


def test_fixing_utc_london_dst() -> None:
    summer = g.fixing_range_utc(date(2024, 9, 17))
    winter = g.fixing_range_utc(date(2024, 1, 16))
    assert datetime.fromtimestamp(summer[0]/1000, UTC).hour == 14
    assert datetime.fromtimestamp(winter[0]/1000, UTC).hour == 15
    assert summer[1] - summer[0] == 30*60*1000


def test_newest_first_absolute_then_backward_deltas() -> None:
    rows = [SimpleNamespace(timestamp=1009, tick=110005),
            SimpleNamespace(timestamp=4, tick=110003),
            SimpleNamespace(timestamp=5, tick=110002)]
    decoded = g.decode_native_newest_first(rows, from_ms=1000, to_ms_inclusive=1010)
    assert [r.timestamp_ms for r in decoded] == [1009, 1005, 1000]
    assert [r.integer_price for r in decoded] == [110005, 110003, 110002]


def test_reject_wrong_time_or_prices() -> None:
    with pytest.raises(g.TickSourceError, match="outside requested"):
        g.decode_native_newest_first(
            [SimpleNamespace(timestamp=900, tick=110000)],
            from_ms=1000, to_ms_inclusive=1100,
        )
    with pytest.raises(g.TickSourceError, match="invalid"):
        g.decode_native_newest_first(
            [SimpleNamespace(timestamp=1000, tick=0)],
            from_ms=1000, to_ms_inclusive=1100,
        )


def test_hasmore_requires_split_and_merges_no_missing_millisecond() -> None:
    calls = []
    def request(start: int, end: int) -> dict:
        calls.append((start, end))
        if end - start > 2:
            return {"has_more": True, "tick_data": [
                SimpleNamespace(timestamp=end, tick=110000)]}
        # Each native page is newest first: first absolute, following backward delta=1.
        return {"has_more": False, "tick_data": [
            SimpleNamespace(timestamp=end, tick=110000),
            *[SimpleNamespace(timestamp=1, tick=110000)
              for _ in range(end - start)],
        ]}
    ticks, requests = g.complete_side_range(
        request, from_ms=1000, to_ms_inclusive=1009,
    )
    assert requests == len(calls)
    assert [tick.timestamp_ms for tick in ticks] == list(range(1000, 1010))
    assert len(set(t.timestamp_ms for t in ticks)) == 10


def test_hasmore_1ms_cannot_claim_complete() -> None:
    with pytest.raises(g.TickSourceError, match="same millisecond"):
        g.complete_side_range(
            lambda start, finish: {"has_more": True, "tick_data": []},
            from_ms=1000, to_ms_inclusive=1000,
        )


def test_hasmore_budget_fail_closed() -> None:
    with pytest.raises(g.TickSourceError, match="budget exceeded"):
        g.complete_side_range(
            lambda start, finish: {"has_more": True, "tick_data": []},
            from_ms=1000, to_ms_inclusive=1050, max_requests=1,
        )


def test_max_seven_day_limit_and_no_tick_order_equivalence() -> None:
    with pytest.raises(g.TickSourceError, match="maximum week"):
        g.complete_side_range(
            lambda _a, _b: {"has_more": False, "tick_data": []},
            from_ms=0, to_ms_inclusive=g.MAX_WINDOW_MS,
        )
    assert g.SOURCE_RUN == 35166210458
    assert g.SOURCE_ARTIFACT == 10475354631
    assert g.IDENTITY == "QORE_NATIVE_RESET_CTRADER_DEMO_TICK_G0_V1"


def test_no_unauthorized_request_surface() -> None:
    import inspect
    method = inspect.getsource(g.ReadOnlyNativeTickSession._request)
    assert "ProtoOANewOrderReq" not in method
    assert "unapproved request type" in method
    assert "ProtoOAGetTickDataReq" in method
    assert "ProtoOARefreshTokenReq" not in method


def test_complete_oauth_aliases_prefer_cibo_generic_and_no_cross_wiring() -> None:
    env = {
        "QORE_CTRADER_CLIENT_ID": "generic-app",
        "QORE_CTRADER_CLIENT_SECRET": "generic-secret",
        "QORE_CTRADER_ACCESS_TOKEN": "generic-access",
        "QORE_CTRADER_DEMO_CLIENT_ID": "demo-app",
        "QORE_CTRADER_DEMO_CLIENT_SECRET": "demo-secret",
        "QORE_CTRADER_DEMO_ACCESS_TOKEN": "demo-access",
    }
    bundles = g.candidate_auth_bundles(env)
    assert [b.source_alias for b in bundles] == [
        "GENERIC_SECRET_ALIAS", "DEMO_SECRET_ALIAS"
    ]
    assert bundles[0].client_id == "generic-app"
    assert bundles[0].access_token == "generic-access"
    assert bundles[1].client_id == "demo-app"
    assert bundles[1].access_token == "demo-access"
    assert not any(
        token in repr(b)
        for b in bundles for token in ("generic-secret", "demo-access")
    )


def test_duplicate_secrets_are_tried_once_and_partial_bundles_ignored() -> None:
    full = {
        "QORE_CTRADER_CLIENT_ID": "id",
        "QORE_CTRADER_CLIENT_SECRET": "secret",
        "QORE_CTRADER_ACCESS_TOKEN": "access",
        "QORE_CTRADER_DEMO_CLIENT_ID": "id",
        "QORE_CTRADER_DEMO_CLIENT_SECRET": "secret",
        "QORE_CTRADER_DEMO_ACCESS_TOKEN": "access",
    }
    assert len(g.candidate_auth_bundles(full)) == 1
    full.pop("QORE_CTRADER_ACCESS_TOKEN")
    bundles = g.candidate_auth_bundles(full)
    assert len(bundles) == 1
    assert bundles[0].source_alias == "DEMO_SECRET_ALIAS"
