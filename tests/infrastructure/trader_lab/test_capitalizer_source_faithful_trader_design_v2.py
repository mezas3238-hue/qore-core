from qore.infrastructure.trader_lab.capitalizer_master_cognitive_contract import (
    CapitalizerChainStatus,
)
from qore.infrastructure.trader_lab.capitalizer_source_faithful_trader_design_v2 import (
    FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN,
    CapitalizerTraderDesignAuthority,
    CapitalizerTraderDesignComponent,
)


def test_source_faithful_trader_design_covers_every_required_component() -> None:
    design = FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN

    assert design.status is CapitalizerChainStatus.FROZEN_APT
    assert {rule.component for rule in design.rules} == set(CapitalizerTraderDesignComponent)
    assert design.ready_for_integrated_nine_market_replay is True
    assert design.integrated_nine_market_replay_completed is False


def test_author_rules_have_provenance_and_qore_rules_do_not_masquerade_as_author() -> None:
    design = FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN

    for rule in design.rules:
        if rule.authority is CapitalizerTraderDesignAuthority.QORE:
            assert rule.qore_operationalization is True
            assert rule.source_fact_ids == ()
        else:
            assert rule.qore_operationalization is False
            assert rule.source_fact_ids


def test_source_faithful_design_forbids_methodology_drift() -> None:
    design = FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN

    assert design.exact_entry_algorithms_derived_from_terminal_outcomes is False
    assert design.numeric_confidence_score_used is False
    assert design.arbitrary_fixed_r_target_used is False
    assert design.unsourced_entry_route_allowed is False
    assert design.advanced_be_trailing_zigzig_claimed_as_source is False
    assert design.executes_trade is False
    assert design.sizes_position is False
    assert design.grants_capital_authority is False


def test_full_design_keeps_qore_governance_separate_from_author_methodology() -> None:
    design = FROZEN_SOURCE_FAITHFUL_TRADER_DESIGN
    rules = {rule.rule_id: rule for rule in design.rules}

    assert (
        rules["MAX3_AND_NINE_MARKETS_ARE_QORE_NOT_AUTHOR"].authority
        is CapitalizerTraderDesignAuthority.QORE
    )
    assert (
        rules["FRACTAL_ROUTE_H1_M15_M1"].authority
        is CapitalizerTraderDesignAuthority.TTRADES
    )
    assert (
        rules["STRUCTURAL_LIQUIDITY_DESTINATION_REQUIRED"].authority
        is CapitalizerTraderDesignAuthority.ICT_TTRADES
    )
