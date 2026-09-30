from qore.infrastructure.core_stack_v2.scientific_society import (
    ScientificClaim,
    ScientificContribution,
    ScientificRole,
    ScientificSocietyVerdict,
    arbitrate_scientific_society,
)


def _contributions(*, falsify: bool) -> tuple[ScientificContribution, ...]:
    rows = []
    for role in ScientificRole:
        claim = ScientificClaim.SUPPORT
        confidence = 8_000
        if falsify and role is ScientificRole.ADVERSARIAL_CRITIC:
            claim = ScientificClaim.FALSIFY
            confidence = 7_000
        rows.append(
            ScientificContribution(
                role=role,
                claim=claim,
                confidence_bps=confidence,
                model_family=f"MODEL_{role.value}",
                evidence_refs=(f"society:{role.value}",),
                real_engine_bound=False,
            )
        )
    return tuple(rows)


def test_one_material_falsifier_defeats_eleven_supporters() -> None:
    decision = arbitrate_scientific_society(
        proposition_id="minority-falsification-test",
        contributions=_contributions(falsify=True),
    )
    assert decision.verdict is ScientificSocietyVerdict.REJECTED_BY_FALSIFICATION
    assert decision.minority_falsification_preserved is True
    assert decision.simple_majority_voting_used is False


def test_support_without_falsification_remains_research_only() -> None:
    decision = arbitrate_scientific_society(
        proposition_id="support-test",
        contributions=_contributions(falsify=False),
    )
    assert decision.verdict is ScientificSocietyVerdict.RESEARCH_ONLY
    assert decision.knowledge_promotion_authority is False
    assert decision.execution_authority is False
