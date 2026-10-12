"""Synthetic protections for USTEC native source candidate, NOT NAS100 certified."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from qore.infrastructure.trader_lab import qore_native_g1_ustec_candidate_bidask_v1 as q


@dataclass
class Sym:
    symbolName: str
    symbolId: int
    enabled: bool


def test_original_id_and_three_frozen_windows_not_pnl_selected():
    assert q.USTEC_PINNED_SYMBOL_ID == 10014
    assert q.WINDOWS == q.FROZEN_WINDOWS
    assert len(q.WINDOWS) == 3
    assert q.ALIAS_IDENTITY_SOURCE_RUN == 38284304699
    assert q.ALIAS_IDENTITY_ARTIFACT == 11762018327


def test_only_exact_enabled_ustec_id10014_can_be_considered():
    assert q.exact_candidate((Sym("USTEC", 10014, True), Sym("NAS100", 55, True))) == 10014
    with pytest.raises(q.SourceBlock, match="ID_CHANGED"):
        q.exact_candidate((Sym("USTEC", 10015, True),))
    with pytest.raises(q.SourceBlock, match="UNAVAILABLE_OR_AMBIGUOUS"):
        q.exact_candidate((Sym("USTEC", 10014, True), Sym("USTEC", 10014, True)))
    with pytest.raises(q.SourceBlock, match="UNAVAILABLE_OR_AMBIGUOUS"):
        q.exact_candidate((Sym("USTEC", 10014, False),))


def test_native_source_integer_precision_not_index_point_value(tmp_path):
    rows = [(1600174800000, 1135020000)]
    item = q._write_side(tmp_path, 1, "BID", rows, 1)
    from json import loads
    v = loads((tmp_path / item["decoded_file"]).read_text().strip())
    assert v["price"] == "11350.2"
    assert item["count"] == 1
    assert item["integer_sha256"] == q._sha(tmp_path / item["integer_file"])


def test_readonly_never_allows_order_refresh_or_spot_subscription():
    allowed = q.ReadOnlyTickPilot._HISTORY_ONLY_REQUEST_NAMES
    assert "ProtoOAGetTickDataReq" in allowed
    assert all(x not in allowed for x in (
        "ProtoOANewOrderReq", "ProtoOACancelOrderReq", "ProtoOAModifyOrderReq",
        "ProtoOARefreshTokenReq", "ProtoOASubscribeSpotsReq",
    ))


def test_ustec_prereg_10min_bounds():
    for window in q.WINDOWS:
        start, end = q.window_milliseconds(window)
        assert end - start == 600000
