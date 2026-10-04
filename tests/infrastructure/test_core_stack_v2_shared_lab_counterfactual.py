from qore.infrastructure.core_stack_v2.shared_lab_counterfactual import (
    CounterfactualWorldReceipt,
    assess_counterfactual_worlds,
)


def _world(**overrides):
    values = dict(
        capability_id="MC18",
        actual_world_fingerprint_before="actual",
        actual_world_fingerprint_after="actual",
        counterfactual_world_fingerprint="cf1",
        assumptions_explicit=True,
        interventions_explicit=True,
        causal_interventions_valid=True,
        transition_coherent=True,
        future_outcome_consumed=False,
        actual_world_mutated=False,
    )
    values.update(overrides)
    return CounterfactualWorldReceipt(**values)


def test_clean_counterfactual_world_passes():
    assert _world().passed is True


def test_future_outcome_leakage_fails():
    assert _world(future_outcome_consumed=True).passed is False


def test_actual_world_mutation_fails():
    assert _world(
        actual_world_mutated=True,
        actual_world_fingerprint_after="mutated",
    ).passed is False


def test_all_worlds_must_pass():
    result = assess_counterfactual_worlds(
        "MC18",
        (_world(), _world(transition_coherent=False)),
    )
    assert result.failed_world_indexes == (1,)
    assert result.all_worlds_truth_valid is False
