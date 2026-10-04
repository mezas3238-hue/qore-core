from qore.infrastructure.core_stack_v2.meta_cognitive_scientific_intelligence import (
    MetaCognitiveConcern,
    MetaCognitiveObservation,
    assess_meta_cognition,
)


def _observation(**overrides):
    values = {
        "prediction_error_bps": 2000,
        "calibration_error_bps": 7000,
        "model_disagreement_bps": 3000,
        "dominant_specialist_share_bps": 2000,
        "concept_decay_bps": 1000,
        "regime_novelty_bps": 2000,
        "information_gap_bps": 4000,
        "falsification_coverage_bps": 9000,
        "expected_compute_value_bps": 1000,
        "evidence_refs": ("meta:test",),
    }
    values.update(overrides)
    return MetaCognitiveObservation(**values)


def test_overconfidence_becomes_top_research_priority() -> None:
    result = assess_meta_cognition(_observation())
    assert result.priorities[0].concern is MetaCognitiveConcern.OVERCONFIDENCE
    assert result.self_modification_authority is False


def test_information_gaps_remain_explicit() -> None:
    result = assess_meta_cognition(_observation(information_gap_bps=8000))
    assert result.unknowns_explicit is True
    assert any(
        item.concern is MetaCognitiveConcern.UNKNOWN_UNKNOWN
        for item in result.priorities
    )


def test_deeper_compute_requires_expected_value() -> None:
    result = assess_meta_cognition(_observation(expected_compute_value_bps=7000))
    compute = next(
        item for item in result.priorities
        if item.concern is MetaCognitiveConcern.COMPUTE_VALUE
    )
    assert compute.deeper_compute_justified is True
