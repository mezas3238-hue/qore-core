from qore.infrastructure.cibo_arch2_t03_current_contract_falsification import (
    RECOMMENDATION,
    T03_CURRENT_CONTRACT_FALSIFICATION,
)


def test_t03_current_contract_has_no_surviving_candidate() -> None:
    result = T03_CURRENT_CONTRACT_FALSIFICATION
    assert result.recommendation == RECOMMENDATION == "FALSIFIED_AND_CLOSED"
    assert result.multileg_candidate_count == 33
    assert result.continuous_lower_margin_candidate_count == 0
    assert result.best_observed_margin_ratio > 1
    assert result.direct_single_instrument_candidate_exhausted is True
    assert result.nas100_related_indices_are_exact_equivalents is False
    assert (
        result.alternate_provider_admissible_under_frozen_comparison_contract
        is False
    )
    assert result.fresh_oos_needed_without_candidate is False
    assert result.holdout_outcomes_used is False
    assert result.broker_mutation_performed is False
    assert result.terminal_disposition_assigned is False
    assert result.productive_authority is False
