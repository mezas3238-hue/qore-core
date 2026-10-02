from __future__ import annotations

from qore.infrastructure.core_stack_v2.active_perception import (
    ActivePerceptionPlan,
    ActivePerceptionRequest,
)
from qore.infrastructure.core_stack_v2.active_perception_research_planner import (
    ActivePerceptionResearchCandidate,
    plan_active_perception_sensor_research,
)
from qore.infrastructure.core_stack_v2.active_perception_sensor_governance import (
    ActivePerceptionSensorContract,
    ActivePerceptionSensorFamily,
    SensorMissingnessSemantics,
    SensorObservationKind,
    SensorTimestampSemantics,
)
from qore.infrastructure.core_stack_v2.competitive_hypothesis_engine import (
    CompetitiveHypothesis,
)
from qore.infrastructure.core_stack_v2.latent_market_state_engine import (
    LatentMarketFactor,
)


def _plan() -> ActivePerceptionPlan:
    return ActivePerceptionPlan(
        requests=(
            ActivePerceptionRequest(
                factor=LatentMarketFactor.ABSORPTION,
                hypothesis_a=CompetitiveHypothesis.SWEEP_REVERSAL,
                hypothesis_b=CompetitiveHypothesis.CONTINUATION,
                information_need_bps=7_500,
                expected_separation_bps=7_000,
                current_factor_uncertainty_bps=8_000,
                suggested_source_families=(
                    "liquidity_response",
                    "microstructure",
                    "price_response",
                ),
                reason="absorption uncertainty",
            ),
            ActivePerceptionRequest(
                factor=LatentMarketFactor.REGIME_TRANSITION,
                hypothesis_a=CompetitiveHypothesis.SWEEP_REVERSAL,
                hypothesis_b=CompetitiveHypothesis.CONTINUATION,
                information_need_bps=5_500,
                expected_separation_bps=5_000,
                current_factor_uncertainty_bps=7_000,
                suggested_source_families=(
                    "volatility",
                    "structure",
                    "cross_market",
                ),
                reason="regime uncertainty",
            ),
        ),
        top_hypotheses=(
            CompetitiveHypothesis.SWEEP_REVERSAL,
            CompetitiveHypothesis.CONTINUATION,
        ),
        unresolved_information_need_bps=7_000,
    )


def _contract(
    key: str,
    *,
    family: ActivePerceptionSensorFamily,
    kind: SensorObservationKind = SensorObservationKind.DIRECT_OBSERVATION,
    replay: bool = True,
) -> ActivePerceptionSensorContract:
    return ActivePerceptionSensorContract(
        sensor_key=key,
        family=family,
        observation_kind=kind,
        provider_or_source_id="retained-provider",
        economic_or_market_scope="NAS100",
        timestamp_semantics=SensorTimestampSemantics.SNAPSHOT_AS_OF,
        missingness_semantics=SensorMissingnessSemantics.EXPLICIT_MISSING,
        retained_evidence=True,
        deterministic_replay=replay,
        exact_provenance=True,
        timezone_aware=True,
        causal_as_of_available=True,
        future_backfill_visible_at_runtime=False,
        provider_revision_policy_known=True,
        runtime_equivalent_source_available=True,
    )


def test_research_planner_prefers_high_need_direct_sensor() -> None:
    plan = plan_active_perception_sensor_research(
        perception_plan=_plan(),
        candidates=(
            ActivePerceptionResearchCandidate(
                contract=_contract(
                    "nas100.bid_ask",
                    family=ActivePerceptionSensorFamily.MARKET_MICROSTRUCTURE,
                ),
                supported_factors=(LatentMarketFactor.ABSORPTION,),
                source_family_tags=("microstructure", "liquidity_response"),
                acquisition_cost_bps=200,
            ),
            ActivePerceptionResearchCandidate(
                contract=_contract(
                    "volatility.index",
                    family=ActivePerceptionSensorFamily.VOLATILITY_OPTIONALITY,
                ),
                supported_factors=(LatentMarketFactor.REGIME_TRANSITION,),
                source_family_tags=("volatility",),
                acquisition_cost_bps=200,
            ),
        ),
    )

    assert tuple(item.sensor_key for item in plan.ranked_sensors) == (
        "nas100.bid_ask",
        "volatility.index",
    )
    assert plan.ranked_sensors[0].matched_source_families == (
        "liquidity_response",
        "microstructure",
    )
    assert plan.selection_partition == "r8"
    assert plan.r6_r5_consumed_for_selection is False


def test_research_planner_rejects_non_replayable_sensor() -> None:
    plan = plan_active_perception_sensor_research(
        perception_plan=_plan(),
        candidates=(
            ActivePerceptionResearchCandidate(
                contract=_contract(
                    "non.replayable",
                    family=ActivePerceptionSensorFamily.MARKET_MICROSTRUCTURE,
                    replay=False,
                ),
                supported_factors=(LatentMarketFactor.ABSORPTION,),
                source_family_tags=("microstructure",),
            ),
        ),
    )

    assert plan.ranked_sensors == ()
    assert plan.rejected_sensor_keys == ("non.replayable",)


def test_research_planner_does_not_rank_irrelevant_factor() -> None:
    plan = plan_active_perception_sensor_research(
        perception_plan=_plan(),
        candidates=(
            ActivePerceptionResearchCandidate(
                contract=_contract(
                    "momentum.only",
                    family=ActivePerceptionSensorFamily.EQUITY_LEADERSHIP_BREADTH,
                ),
                supported_factors=(LatentMarketFactor.MOMENTUM_PERSISTENCE,),
                source_family_tags=("cross_market",),
            ),
        ),
    )

    assert plan.ranked_sensors == ()
    assert plan.rejected_sensor_keys == ()


def test_research_planner_direct_observation_beats_equal_provider_derived() -> None:
    candidates = (
        ActivePerceptionResearchCandidate(
            contract=_contract(
                "direct",
                family=ActivePerceptionSensorFamily.MARKET_MICROSTRUCTURE,
            ),
            supported_factors=(LatentMarketFactor.ABSORPTION,),
            source_family_tags=("microstructure",),
            acquisition_cost_bps=100,
        ),
        ActivePerceptionResearchCandidate(
            contract=_contract(
                "derived",
                family=ActivePerceptionSensorFamily.MARKET_MICROSTRUCTURE,
                kind=SensorObservationKind.PROVIDER_DERIVED_OBSERVATION,
            ),
            supported_factors=(LatentMarketFactor.ABSORPTION,),
            source_family_tags=("microstructure",),
            acquisition_cost_bps=100,
        ),
    )
    plan = plan_active_perception_sensor_research(
        perception_plan=_plan(),
        candidates=candidates,
    )

    assert tuple(item.sensor_key for item in plan.ranked_sensors) == (
        "direct",
        "derived",
    )
