import pytest

from qore.infrastructure.core_stack_v2.governed_epistemic_layer import (
    EpistemicSituation,
    GovernedEpistemicEvidence,
    assess_governed_epistemics,
)


def _evidence(**overrides: object) -> GovernedEpistemicEvidence:
    values: dict[str, object] = {
        "calibration_error_bps": 500,
        "uncertainty_index_bps": 2000,
        "contradiction_bps": 1000,
        "novelty_index_bps": 1000,
        "missing_evidence_bps": 0,
        "evidence_refs": ("evidence:a",),
        "belief_probability_calibrated": True,
    }
    values.update(overrides)
    return GovernedEpistemicEvidence(**values)  # type: ignore[arg-type]


def test_coherent_epistemics_remain_calibrated_and_authority_free() -> None:
    state = assess_governed_epistemics(_evidence())
    assert state.state is EpistemicSituation.CALIBRATED
    assert state.assertiveness_ceiling_bps == 8000
    assert state.trading_command is False
    assert state.methodology_authority is False
    assert state.sizing_authority is False
    assert state.capital_authority is False
    assert state.risk_authority is False
    assert state.execution_authority is False


def test_contradiction_reduces_assertiveness() -> None:
    state = assess_governed_epistemics(
        _evidence(contradiction_bps=8000)
    )
    assert state.state is EpistemicSituation.CONTESTED
    assert state.assertiveness_ceiling_bps <= 2000


def test_missing_information_dominates_support() -> None:
    state = assess_governed_epistemics(
        _evidence(missing_evidence_bps=9000)
    )
    assert state.state is EpistemicSituation.INSUFFICIENT
    assert state.assertiveness_ceiling_bps <= 1000


def test_novelty_is_visible_not_silently_known() -> None:
    state = assess_governed_epistemics(
        _evidence(novelty_index_bps=8000)
    )
    assert state.state is EpistemicSituation.NOVELTY_ALERT
    assert state.assertiveness_ceiling_bps <= 2000


def test_uncertainty_and_novelty_cannot_masquerade_as_probabilities() -> None:
    with pytest.raises(ValueError, match="uncertainty research index"):
        _evidence(uncertainty_is_calibrated_probability=True)
    with pytest.raises(ValueError, match="novelty research index"):
        _evidence(novelty_is_calibrated_probability=True)
