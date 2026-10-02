from qore.infrastructure.cibo_arch2_t11_nonlinear_input_freeze import (
    GROSS_EDGE_MINIMUM_OUTCOMES_PER_LINEAGE,
    GROSS_EDGE_REQUIRED_FOLDS,
    MARKET_IMPACT_AGGREGATE_CHILD_COUNTS,
    MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL,
    REQUIRED_SYMBOLS,
    T11_NONLINEAR_INPUT_FREEZE,
)


def test_t11_nonlinear_freeze_is_pre_outcome_and_no_refit() -> None:
    freeze = T11_NONLINEAR_INPUT_FREEZE
    assert freeze.gross_edge.required_lineages == 7
    assert (
        freeze.gross_edge.minimum_outcomes_per_lineage
        == GROSS_EDGE_MINIMUM_OUTCOMES_PER_LINEAGE
    )
    assert freeze.gross_edge.required_folds == GROSS_EDGE_REQUIRED_FOLDS == 4
    assert freeze.gross_edge.estimator_refit_allowed is False
    assert freeze.gross_edge.validation_outcomes_may_change_model is False
    assert freeze.gross_edge.fresh_oos_required is True
    assert freeze.gross_edge.temporal_stability_required is True
    assert freeze.gross_edge_population_consumed_at_freeze is False
    assert freeze.market_impact_population_consumed_at_freeze is False


def test_t11_market_impact_uses_only_minimum_volume_child_orders() -> None:
    impact = T11_NONLINEAR_INPUT_FREEZE.market_impact
    assert impact.required_symbols == REQUIRED_SYMBOLS
    assert impact.aggregate_child_counts == MARKET_IMPACT_AGGREGATE_CHILD_COUNTS == (
        1,
        2,
    )
    assert impact.each_child_order_minimum_volume_required is True
    assert impact.calibration_episodes_per_level_per_symbol == (
        MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL
    )
    assert impact.validation_episodes_per_level_per_symbol == (
        MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL
    )
    assert impact.temporally_disjoint_validation_required is True
    assert impact.nonnegative_quadratic_coefficient_required is True
    assert impact.fundednext_allowed is False
    assert impact.vps_allowed is False
    assert impact.live_allowed is False
    assert impact.real_capital_allowed is False
    assert impact.phase22_outcomes_allowed_for_calibration is False
    assert freeze_fingerprint_is_canonical()


def freeze_fingerprint_is_canonical() -> bool:
    value = T11_NONLINEAR_INPUT_FREEZE.fingerprint()
    return value.startswith("sha256:") and len(value) == 71
