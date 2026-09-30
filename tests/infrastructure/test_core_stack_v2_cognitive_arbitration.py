from qore.infrastructure.core_stack_v2.cognitive_arbitration import (
    CognitiveFacet,
    CognitiveFacetEvidence,
    SharedSituationState,
    arbitrate_shared_situation,
)


def _facets(*, critical: bool = False, gap: int = 1000):
    return tuple(
        CognitiveFacetEvidence(
            facet=facet,
            support_bps=8000,
            contradiction_bps=1000,
            uncertainty_bps=gap if facet is CognitiveFacet.INFORMATION_GAPS else 1000,
            critical_negative=critical and facet is CognitiveFacet.NEGATIVE_EVIDENCE,
            evidence_refs=(f"facet:{facet.value}",),
        )
        for facet in CognitiveFacet
    )


def test_critical_negative_cannot_be_outvoted() -> None:
    result = arbitrate_shared_situation("critical", _facets(critical=True))
    assert result.state is SharedSituationState.CONTESTED
    assert result.assertiveness_bps <= 2500
    assert result.critical_negative_preserved is True


def test_information_gap_caps_assertiveness() -> None:
    result = arbitrate_shared_situation("gap", _facets(gap=8000))
    assert result.state is SharedSituationState.INSUFFICIENT
    assert result.assertiveness_bps <= 2000


def test_coherent_situation_has_no_authority() -> None:
    result = arbitrate_shared_situation("coherent", _facets())
    assert result.state is SharedSituationState.COHERENT
    assert result.trading_command is False
    assert result.risk_authority is False
    assert result.capital_authority is False
    assert result.broker_authority is False
