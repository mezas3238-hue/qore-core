"""D0 QORE Native 33 markets × seven methods: completeness before ANY PnL."""
from __future__ import annotations

from collections import Counter
import copy
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_33x7_method_market_registry_v1 as m


def test_full_33_by_seven_all_cells_including_older_no_support() -> None:
    r = m.build()
    assert r["source_markets"] == 33
    assert r["methodologies"] == 7
    assert r["planned_cells"] == 231
    assert len(r["cells"]) == 231
    assert len({c["cell_id"] for c in r["cells"]}) == 231
    assert r["previously_evaluated_in_all33_panel"] == 33
    assert r["previous_single_market_evidence"] == 3
    assert r["design_only_untested"] == 195
    assert r["market_returns_accessed_in_registry"] is False
    assert r["native_traders_certified"] == 0


def test_every_market_seven_methods_and_every_method_33_markets() -> None:
    rows = m.build()["cells"]
    per_symbol = Counter(c["symbol"] for c in rows)
    per_method = Counter(c["method_id"] for c in rows)
    assert set(per_symbol) == m.final33.FROZEN_UNIVERSE_33
    assert all(n == 7 for n in per_symbol.values())
    assert set(per_method) == {name for name, _ in m.METHODOLOGIES}
    assert all(n == 33 for n in per_method.values())


def test_no_relabeling_panel_or_single_no_support_as_new_discovery() -> None:
    rows = m.build()["cells"]
    s = [c for c in rows if c["method_id"] == "SWEEP_RECLAIM"]
    assert len(s) == 33
    assert {x["prior_pr"] for x in s} == {830}
    assert all(x["prior_result"] == "PANEL_NO_SUPPORT_NOT_INDIVIDUAL_MARKET_INFERENCE" for x in s)
    originals = {
        ("REVERSAL_12H", "XAUUSD"): 825,
        ("POST_OPEN_CONT", "NAS100"): 827,
        ("PERSISTENCE_12H", "EURUSD"): 822,
    }
    for (method, symbol), pr in originals.items():
        e = next(x for x in rows if x["method_id"] == method and x["symbol"] == symbol)
        assert e["prior_pr"] == pr
        assert e["prior_result"] == "NO_SUPPORT"
    for e in rows:
        assert e["certified_edge"] is False
        assert e["pnl_or_returns"] is None
        assert e["eligible_for_live"] is False


def test_session_clocks_are_different_and_uncertified() -> None:
    index = m.session_reference("NAS100", "POST_OPEN_CONT")
    major = m.session_reference("EURUSD", "POST_OPEN_CONT")
    metal = m.session_reference("XAUUSD", "OPEN_INITIAL_REACTION")
    assert (index["tz"], index["local_reference"]) == ("America/New_York", "09:30")
    assert (major["tz"], major["local_reference"]) == ("Europe/London", "08:00")
    assert metal["session_kind"] == "US_METALS_LIQUIDITY_PROXY_UNVALIDATED"
    assert all(x["broker_open_verified"] is False for x in (index, major, metal))
    assert m.session_reference("USDCHF", "PERSISTENCE_12H")["local_reference"] is None


def test_no_source_account_equivalence_invented() -> None:
    r = m.build()
    original = next(c for c in r["cells"] if c["symbol"] == "EURUSD")
    new = next(c for c in r["cells"] if c["symbol"] == "NZDCHF")
    assert original["source_origin"] != new["source_origin"]
    assert original["source_origin"].startswith("ORIGINAL12")
    assert new["source_origin"].startswith("NEW21")


def test_missing_or_duplicated_bad_outcome_and_erased_prior_fails() -> None:
    base = m.build()
    cases = []
    a = copy.deepcopy(base)
    a["cells"].pop()
    cases.append(a)
    a = copy.deepcopy(base)
    a["cells"][0]["cell_id"] = a["cells"][1]["cell_id"]
    cases.append(a)
    a = copy.deepcopy(base)
    a["cells"][0]["certified_edge"] = True
    cases.append(a)
    a = copy.deepcopy(base)
    a["cells"][0]["p_value"] = 0.01
    cases.append(a)
    a = copy.deepcopy(base)
    a["cells"][0]["market_family"] = "equity_indices"
    cases.append(a)
    a = copy.deepcopy(base)
    a["cells"][0]["prior_pr"] = 999
    cases.append(a)
    a = copy.deepcopy(base)
    a["source_g0_manifest_sha256"] = "0" * 64
    cases.append(a)
    for invalid in cases:
        with pytest.raises(ValueError):
            m.validate(invalid)


def test_no_prices_broker_live_or_PnL_in_registry_generator() -> None:
    source = Path(m.__file__).read_text(encoding="utf-8")
    for forbidden in (
        '["open_relative"]', '["close_relative"]', "ProtoOANewOrderReq",
        "backtest(", "place_order(", "calculate_pnl(", "broker_api",
    ):
        assert forbidden not in source
