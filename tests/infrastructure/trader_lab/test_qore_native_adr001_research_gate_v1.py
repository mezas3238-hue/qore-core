"""QORE Native ADR001: no invented net edge, independence, or fifth price rule."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import qore_native_adr001_research_gate_v1 as gate

PATH = Path(__file__).resolve().parents[3] / "docs/research/QORE_NATIVE_ADR001_HYPOTHESIS_CLOSURE_REGISTRY_2026-10-12.json"


def sample() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_documented_four_precommitted_no_support_and_no_live() -> None:
    assert PATH.is_file()
    d = sample()
    status = gate.validate(d)
    assert status == {
        "status": "ADR001_RESEARCH_CLASS_CLOSED_STRUCTURAL_E0_ONLY",
        "g0_market_sources": 33,
        "prereg_NO_SUPPORT": 4,
        "structural_price_outcomes_tested": 0,
        "certified_traders": 0,
        "net_or_live_authorized": False,
    }


def test_do_not_claim_unverified_effective_independent_N() -> None:
    d = sample()
    d["factor_equivalent_count"] = 7
    with pytest.raises(ValueError, match="fictional effective N"):
        gate.validate(d)
    d = sample()
    d["effective_sample_size"] = 4000
    with pytest.raises(ValueError, match="fictional effective N"):
        gate.validate(d)


def test_four_null_trials_cannot_be_relabelled_significant() -> None:
    d = sample()
    d["tests"][2]["result"] = "EDGE_CERTIFIED"
    with pytest.raises(ValueError, match="outcomes mutated"):
        gate.validate(d)
    d = sample()
    d["tests"][2]["diag_CI_delta_bps"] = [2.0, 12.0]
    with pytest.raises(ValueError, match="intervals must include zero"):
        gate.validate(d)


def test_separate_gross_from_net_and_forbid_trader_production() -> None:
    d = sample()
    d["historical_bidask_broker_cost_verified"] = True
    with pytest.raises(ValueError, match="no live authorization"):
        gate.validate(d)
    d = sample()
    d["native_traders_certified"] = 1
    with pytest.raises(ValueError, match="no live authorization"):
        gate.validate(d)
    d = sample()
    d["net_economics_authorized"] = True
    with pytest.raises(ValueError, match="no live authorization"):
        gate.validate(d)


def test_no_unapproved_fifth_intraday_ohlc_pattern() -> None:
    d = sample()
    d["no_new_price_pattern_backtests_without_new_adr"] = False
    with pytest.raises(ValueError, match="no live authorization"):
        gate.validate(d)
    d = sample()
    d["preregistered_native_attempts"] = 5
    with pytest.raises(ValueError, match="no live authorization"):
        gate.validate(d)
    d = sample()
    d["tests"].append(copy.deepcopy(d["tests"][0]))
    with pytest.raises(ValueError, match="prereg runs required"):
        gate.validate(d)


def test_g0_data_is_not_economic_certification() -> None:
    d = sample()
    d["source_g0"]["manifest_sha256"] = "1" * 64
    with pytest.raises(ValueError, match="provenance drift"):
        gate.validate(d)
    assert "nasdaq" in d["decision"].lower() or d["decision"].startswith("PIVOT_TO_EXOGENOUS")


def test_source_does_not_import_prices_or_broker_orders() -> None:
    code = Path(gate.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "backtest(", "place_order(", "profit_factor(", "ctrader_open_api_client",
        "open_relative", "close_relative", "ProtoOANewOrderReq",
    ):
        assert forbidden not in code
