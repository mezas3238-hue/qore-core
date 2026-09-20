from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_index_r94_ttrades_timeframe_hierarchy_freeze as r94,
)


def test_r94_primary_model_is_daily_h4_m15() -> None:
    report = r94.payload()
    primary = report["frozen_hierarchy"]["vt08_primary_model"]
    assert primary["bias_timeframe"] == "D1"
    assert primary["structure_timeframe"] == "H4"
    assert primary["entry_timeframe"] == "M15"


def test_r94_alternate_pairs_are_not_additive_layers() -> None:
    report = r94.payload()
    alternate = report["frozen_hierarchy"]["alternate_pairings"]
    assert alternate["H1_M5"]["valid_pairing"] is True
    assert alternate["H1_M5"]["independent_additive_layer_to_H4_M15"] is False
    assert alternate["M15_M1"]["valid_pairing"] is True
    assert alternate["M15_M1"]["independent_additive_layer_to_H4_M15"] is False


def test_r94_lower_timeframe_refinement_does_not_create_new_narrative() -> None:
    report = r94.payload()
    refinement = report["frozen_hierarchy"]["lower_timeframe_refinement"]
    assert refinement["allowed"] is True
    assert refinement["requires_preexisting_higher_timeframe_narrative"] is True
    assert refinement["creates_new_independent_narrative"] is False
    assert refinement["creates_new_setup_count_by_default"] is False


def test_r94_cascade_union_is_diagnostic_only() -> None:
    report = r94.payload()
    cascade = report["frozen_hierarchy"]["cascade_union"]
    assert cascade["r92_r93_role"] == "DENSITY_UPPER_BOUND_DIAGNOSTIC"
    assert cascade["promotable_as_candidate_without_model_selection_rule"] is False
    assert cascade["pnl_may_not_choose_timeframe_pairing"] is True


def test_r94_governance_denies_authority() -> None:
    report = r94.payload()
    gov = report["governance"]
    assert gov["candidate_created"] is False
    assert gov["trader_certified"] is False
    assert gov["live_authorized"] is False
    assert gov["real_capital_authorized"] is False
    assert gov["production_authorized"] is False
