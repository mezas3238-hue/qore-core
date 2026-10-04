from qore.infrastructure.core_stack_v2.shared_lab_experiments import (
    ExperimentKind,
    ExperimentObservation,
    assess_capability_experiments,
)


def test_mutation_requires_real_downstream_reaction():
    item = ExperimentObservation(
        experiment_id="m1",
        capability_id="MC18",
        kind=ExperimentKind.MUTATION,
        baseline_fingerprint="a",
        treatment_fingerprint="b",
        baseline_downstream_fingerprint="same",
        treatment_downstream_fingerprint="same",
        material_intervention=True,
        expected_downstream_change=True,
        actual_downstream_change=False,
    )
    assert item.passed is False


def test_metamorphic_invariant_rejects_irrelevant_sensitivity():
    item = ExperimentObservation(
        experiment_id="meta1",
        capability_id="MC18",
        kind=ExperimentKind.METAMORPHIC,
        baseline_fingerprint="a",
        treatment_fingerprint="b",
        baseline_downstream_fingerprint="x",
        treatment_downstream_fingerprint="y",
        material_intervention=True,
        expected_downstream_change=False,
        actual_downstream_change=True,
        invariant_expected=True,
        invariant_preserved=False,
    )
    assert item.passed is False


def test_capability_requires_mutation_metamorphic_and_ablation():
    observations = (
        ExperimentObservation("m", "MC18", ExperimentKind.MUTATION, "a", "b", "x", "y", True, True, True),
        ExperimentObservation("meta", "MC18", ExperimentKind.METAMORPHIC, "a", "b", "x", "x", True, False, False, True, True),
        ExperimentObservation("a", "MC18", ExperimentKind.ABLATION, "a", "b", "x", "y", True, True, True),
    )
    result = assess_capability_experiments("MC18", observations)
    assert result.mutation_pass is True
    assert result.metamorphic_pass is True
    assert result.ablation_pass is True
    assert result.all_required_experiments_pass is True
