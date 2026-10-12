"""All 33 markets must appear exactly once, with broker source provenance."""
from __future__ import annotations

from pathlib import Path
import pytest

from qore.infrastructure.trader_lab import qore_native_market33_source_census_v1 as m
from qore.infrastructure.trader_lab import qore_native_final33_three_m5_g0_v1 as tail


def manifest_fixture() -> dict:
    origins = sorted(m.source.EXISTING)
    new_parent = sorted(tail.EXPECTED_PARENT_30 - set(origins))
    last = sorted(tail.SOURCE_TAIL)
    assert len(origins) == 12 and len(new_parent) == 18 and len(last) == 3
    m5 = {}
    for i, symbol in enumerate(origins):
        m5[symbol] = 720000 if i != 11 else 8726985 - 11 * 720000
    for i, symbol in enumerate(new_parent):
        m5[symbol] = 745000 if i != 17 else tail.PARENT_30_M5_BARS - 8726985 - 17 * 745000
    for symbol in last:
        m5[symbol] = 745000
    records = []
    for symbol in sorted(m.FAMILIES["fx_majors"] | m.FAMILIES["fx_crosses"] |
                         m.FAMILIES["metals"] | m.FAMILIES["equity_indices"]):
        original = symbol in origins
        row = {
            "symbol":symbol, "m5_bars":m5[symbol],
            "source_cohort": (m.ORIGINAL_COHORT if original else "NEW11_ICMARKETS_CTRADER_DEMO"),
        }
        if not original:
            row["raw_sha256_by_year"] = {str(y):"a"*64 for y in range(2016, 2027)}
        records.append(row)
    return {
        "identity":tail.IDENTITY, "status":"G0_33_OF_33_PROVIDER_M5_SHA_VERIFIED_NO_ECONOMICS",
        "market_count":33, "parent30_bars":tail.PARENT_30_M5_BARS,
        "parent30_manifest_sha256":tail.PARENT_30_JSON_SHA,
        "parent30_producer_head_sha":tail.PARENT_30_CODE_SHA,
        "added_tail_three_bars":3*745000,
        "all_33_original_m5_bars":sum(m5.values()),
        "market_roster":records, "market_outcomes_unexamined":True,
        "historical_bidask_spread_verified":False,
        "net_execution_economics_authorized":False,
        "production_untouched":True, "traders_certified":0,
        "original12_vs_new21_same_ICMarkets_account_verified":False,
    }


def test_fixed_families_cover_all_33_and_do_not_overlap() -> None:
    m.frozen_family_contract()
    assert len(m.FAMILIES["equity_indices"]) == 3
    assert len(m.FAMILIES["metals"]) == 2
    assert len(m.FAMILIES["fx_majors"]) == 7
    assert len(m.FAMILIES["fx_crosses"]) == 21


def test_33_manifest_source_census_reconciles_all_families() -> None:
    data = m.census(manifest_fixture())
    assert data["status"] == "G0_FULL33_FAMILIES_ALL_COVERED_NO_MARKET_OUTCOMES"
    assert data["markets_count"] == 33
    assert data["native_m5_bars"] == 22141699 + 3*745000
    assert sum(x["assets"] for x in data["families"].values()) == 33
    assert data["provenance"]["original12_demo"]["native_m5_bars"] == 8726985
    assert data["provenance"]["new21_icmarkets_demo"]["assets"] == 21
    assert data["no_returns_or_PnL_read"] and data["no_broker_historical_bidask"]


def test_missing_annual_raw_SHA_does_not_pass_for_new_21() -> None:
    fixture = manifest_fixture()
    row = next(x for x in fixture["market_roster"] if x["symbol"] == "NZDCHF")
    row["raw_sha256_by_year"].pop("2026")
    with pytest.raises(ValueError, match="11-year SHA"):
        m.census(fixture)


def test_do_not_fake_broker_identity() -> None:
    fixture = manifest_fixture()
    fixture["original12_vs_new21_same_ICMarkets_account_verified"] = True
    with pytest.raises(ValueError):
        m.census(fixture)


def test_33_missing_even_single_symbol_rejected() -> None:
    fixture = manifest_fixture()
    fixture["market_roster"].pop()
    with pytest.raises(ValueError, match="not unique"):
        m.census(fixture)


def test_false_parent_count_or_tail_count_rejected() -> None:
    fixture = manifest_fixture()
    fixture["added_tail_three_bars"] += 1
    with pytest.raises(ValueError, match="reconcile"):
        m.census(fixture)
    fixture = manifest_fixture()
    fixture["parent30_manifest_sha256"] = "b"*64
    with pytest.raises(ValueError):
        m.census(fixture)


def test_no_ohlc_or_pnl_in_source_metadata_census_module() -> None:
    script = Path(m.__file__).read_text(encoding="utf-8")
    for banned in (
        'row["close_relative"]', 'row["open_relative"]', "place_order(",
        "profit_factor(", "backtest(", "pnl_by_symbol(", "ProtoOANewOrderReq",
    ):
        assert banned not in script
