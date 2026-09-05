"""Tests for the CIBO Cognitive multi-scenario simulation substrate (CA 3.2)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from qore.infrastructure.cibo_cognitive_common import fingerprint_material
from qore.infrastructure.cibo_cognitive_scenarios import (
    ScenarioAlternative,
    ScenarioAssumption,
    ScenarioFactKind,
    ScenarioFamily,
    ScenarioValidationError,
    assert_scenario_lineage_acyclic,
    build_scenario,
)
from qore.modules.cibo.cognitive_contracts import (
    CiboCognitiveEvidenceRef,
    CiboConfidence,
    CiboConfidenceLevel,
    CiboUncertainty,
    CiboUncertaintyKind,
)

_SNAPSHOT = uuid4()
_FP = fingerprint_material("world")


def _uncertainty() -> CiboUncertainty:
    return CiboUncertainty(kind=CiboUncertaintyKind.INSUFFICIENT_EVIDENCE)


def _bounded() -> CiboUncertainty:
    return CiboUncertainty(
        kind=CiboUncertaintyKind.BOUNDED_CONFIDENCE,
        confidence=CiboConfidence(
            CiboConfidenceLevel.MEDIUM, (CiboCognitiveEvidenceRef("evidence:x"),)
        ),
    )


def test_scenario_builds_and_revalidates() -> None:
    scenario = build_scenario(
        scenario_id=uuid4(),
        family=ScenarioFamily.ADVERSE,
        version="v1",
        uncertainty=_uncertainty(),
        abstained=True,
    )
    scenario.revalidate()
    assert scenario.family is ScenarioFamily.ADVERSE


def test_all_four_families_representable() -> None:
    for family in ScenarioFamily:
        scenario = build_scenario(
            scenario_id=uuid4(), family=family, version="v1", uncertainty=_uncertainty()
        )
        assert scenario.family is family


def test_observed_assumption_requires_world_binding() -> None:
    with pytest.raises(ScenarioValidationError):
        build_scenario(
            scenario_id=uuid4(),
            family=ScenarioFamily.BASE,
            version="v1",
            assumptions=(ScenarioAssumption("market.open", ScenarioFactKind.OBSERVED),),
            uncertainty=_uncertainty(),
        )


def test_observed_assumption_with_binding_ok() -> None:
    scenario = build_scenario(
        scenario_id=uuid4(),
        family=ScenarioFamily.BASE,
        version="v1",
        assumptions=(ScenarioAssumption("market.open", ScenarioFactKind.OBSERVED),),
        world_snapshot_id=_SNAPSHOT,
        world_fingerprint=_FP,
        uncertainty=_uncertainty(),
    )
    scenario.revalidate()


def test_hypothetical_separated_from_observed() -> None:
    scenario = build_scenario(
        scenario_id=uuid4(),
        family=ScenarioFamily.BASE,
        version="v1",
        assumptions=(ScenarioAssumption("market.open", ScenarioFactKind.HYPOTHETICAL),),
        uncertainty=_uncertainty(),
    )
    assert scenario.assumptions[0].fact_kind is ScenarioFactKind.HYPOTHETICAL


def test_abstained_scenario_must_not_carry_alternatives() -> None:
    with pytest.raises(ScenarioValidationError):
        build_scenario(
            scenario_id=uuid4(),
            family=ScenarioFamily.ADVERSE,
            version="v1",
            alternatives=(
                ScenarioAlternative(uuid4(), "action.hold", "outcome.stable"),
            ),
            abstained=True,
            uncertainty=_uncertainty(),
        )


def test_alternatives_are_comparable() -> None:
    scenario = build_scenario(
        scenario_id=uuid4(),
        family=ScenarioFamily.ADVERSE,
        version="v1",
        alternatives=(
            ScenarioAlternative(uuid4(), "action.hold", "outcome.stable"),
            ScenarioAlternative(uuid4(), "action.reduce", "outcome.drawdown"),
        ),
        uncertainty=_bounded(),
    )
    assert len(scenario.alternatives) == 2


def test_copied_id_with_changed_content_fails_fingerprint() -> None:
    scenario = build_scenario(
        scenario_id=uuid4(), family=ScenarioFamily.BASE, version="v1", uncertainty=_uncertainty()
    )
    object.__setattr__(scenario, "version", "v2")
    with pytest.raises(ScenarioValidationError):
        scenario.revalidate()


def test_supersession_self_reference_rejected() -> None:
    scenario_id = uuid4()
    with pytest.raises(ScenarioValidationError):
        build_scenario(
            scenario_id=scenario_id,
            family=ScenarioFamily.BASE,
            version="v1",
            uncertainty=_uncertainty(),
            supersedes=scenario_id,
        )


def test_lineage_acyclicity() -> None:
    a_id = uuid4()
    b_id = uuid4()
    a = build_scenario(
        scenario_id=a_id, family=ScenarioFamily.BASE, version="v1", uncertainty=_uncertainty()
    )
    b = build_scenario(
        scenario_id=b_id,
        family=ScenarioFamily.ADVERSE,
        version="v1",
        uncertainty=_uncertainty(),
        supersedes=a_id,
    )
    assert_scenario_lineage_acyclic([a, b])
    with pytest.raises(ScenarioValidationError):
        a_cycle = build_scenario(
            scenario_id=a_id,
            family=ScenarioFamily.BASE,
            version="v1",
            uncertainty=_uncertainty(),
            supersedes=b_id,
        )
        assert_scenario_lineage_acyclic([a_cycle, b])


def test_no_probability_field() -> None:
    scenario = build_scenario(
        scenario_id=uuid4(), family=ScenarioFamily.BASE, version="v1", uncertainty=_bounded()
    )
    assert not hasattr(scenario, "probability")
    assert not hasattr(scenario, "p")


def test_authority_free() -> None:
    scenario = build_scenario(
        scenario_id=uuid4(), family=ScenarioFamily.BASE, version="v1", uncertainty=_uncertainty()
    )
    for absent in (
        "order",
        "intent",
        "account",
        "quantity",
        "provider",
        "promotion",
        "risk",
        "execute",
    ):
        assert not hasattr(scenario, absent)


class TestScenarioBuilderPermutationInvariance:
    def test_assumptions_permutation_invariant(self) -> None:
        sid = uuid4()

        def assumptions() -> tuple[ScenarioAssumption, ...]:
            return (
                ScenarioAssumption(
                    code="no-fabricated-probability", fact_kind=ScenarioFactKind.HYPOTHETICAL
                ),
                ScenarioAssumption(
                    code="stress-liquidity", fact_kind=ScenarioFactKind.HYPOTHETICAL
                ),
            )

        first = build_scenario(
            scenario_id=sid,
            family=ScenarioFamily.ADVERSE,
            version="v1",
            assumptions=assumptions(),
            uncertainty=_uncertainty(),
        )
        second = build_scenario(
            scenario_id=sid,
            family=ScenarioFamily.ADVERSE,
            version="v1",
            assumptions=tuple(reversed(assumptions())),
            uncertainty=_uncertainty(),
        )
        assert first.assumptions == second.assumptions
        assert first.fingerprint == second.fingerprint

    def test_assumptions_different_multiset_differs(self) -> None:
        def assumptions(code: str) -> tuple[ScenarioAssumption, ...]:
            return (
                ScenarioAssumption(code=code, fact_kind=ScenarioFactKind.HYPOTHETICAL),
            )

        sid = uuid4()
        first = build_scenario(
            scenario_id=sid,
            family=ScenarioFamily.ADVERSE,
            version="v1",
            assumptions=assumptions("no-fabricated-probability"),
            uncertainty=_uncertainty(),
        )
        second = build_scenario(
            scenario_id=sid,
            family=ScenarioFamily.ADVERSE,
            version="v1",
            assumptions=assumptions("stress-liquidity"),
            uncertainty=_uncertainty(),
        )
        assert first.fingerprint != second.fingerprint

    def test_assumptions_duplicate_rejected(self) -> None:
        duplicate = ScenarioAssumption(
            code="no-fabricated-probability", fact_kind=ScenarioFactKind.HYPOTHETICAL
        )
        with pytest.raises(ScenarioValidationError, match="duplicate"):
            build_scenario(
                scenario_id=uuid4(),
                family=ScenarioFamily.ADVERSE,
                version="v1",
                assumptions=(duplicate, duplicate),
                uncertainty=_uncertainty(),
            )
