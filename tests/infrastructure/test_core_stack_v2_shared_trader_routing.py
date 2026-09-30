from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_trader_intelligence import (
    SharedIntelligenceClass,
    SharedTraderCapability,
)
from qore.infrastructure.core_stack_v2.shared_trader_routing import (
    SharedRoutableFact,
    route_shared_facts_to_trader,
)

T0 = datetime(2026, 9, 30, 14, 30, tzinfo=UTC)
FP = "a" * 64


def _capability(*, monitor: bool = True) -> SharedTraderCapability:
    return SharedTraderCapability(
        trader_id="R38_GBPJPY",
        markets=("GBPJPY",),
        horizons=("H1", "H4", "M5"),
        supported_intelligence_classes=tuple(
            sorted(
                (
                    SharedIntelligenceClass.OPPORTUNITY,
                    SharedIntelligenceClass.REGIME_TRANSITION,
                    SharedIntelligenceClass.CONTINUATION,
                    SharedIntelligenceClass.WORLD_EXPLANATION,
                    SharedIntelligenceClass.POSITION_THREAT,
                ),
                key=lambda item: item.value,
            )
        ),
        open_position_monitoring_capability=monitor,
    )


def _fact(
    ref: str,
    cls: SharedIntelligenceClass,
    *,
    markets: tuple[str, ...] = (),
    horizons: tuple[str, ...] = (),
    materiality: bool = True,
    health: bool = True,
    cutoff: datetime = T0,
) -> SharedRoutableFact:
    return SharedRoutableFact(
        fact_ref=ref,
        snapshot_id="global-1",
        intelligence_class=cls,
        markets=markets,
        horizons=horizons,
        evidence_cutoff_at=cutoff,
        materiality_passed=materiality,
        data_health_passed=health,
    )


def test_routes_only_material_healthy_relevant_facts() -> None:
    facts = tuple(
        sorted(
            (
                _fact(
                    "fact-1",
                    SharedIntelligenceClass.OPPORTUNITY,
                    markets=("GBPJPY",),
                    horizons=("H1",),
                ),
                _fact(
                    "fact-2",
                    SharedIntelligenceClass.WORLD_EXPLANATION,
                ),
                _fact(
                    "fact-3",
                    SharedIntelligenceClass.OPPORTUNITY,
                    markets=("NAS100",),
                    horizons=("H1",),
                ),
                _fact(
                    "fact-4",
                    SharedIntelligenceClass.CONTINUATION,
                    markets=("GBPJPY",),
                    horizons=("D1",),
                ),
                _fact(
                    "fact-5",
                    SharedIntelligenceClass.REGIME_TRANSITION,
                    materiality=False,
                ),
                _fact(
                    "fact-6",
                    SharedIntelligenceClass.REGIME_TRANSITION,
                    health=False,
                ),
            ),
            key=lambda item: item.fact_ref,
        )
    )
    result = route_shared_facts_to_trader(
        capability=_capability(),
        facts=facts,
        projection_id="projection-1",
        snapshot_id="global-1",
        projected_at=T0,
        global_state_fingerprint=FP,
    )

    assert result.routed_fact_refs == ("fact-1", "fact-2")
    reasons = dict(result.omission_reasons)
    assert reasons["fact-3"] == "MARKET_NOT_RELEVANT"
    assert reasons["fact-4"] == "HORIZON_NOT_RELEVANT"
    assert reasons["fact-5"] == "MATERIALITY_BLOCK"
    assert reasons["fact-6"] == "DATA_HEALTH_BLOCK"
    assert result.projection.projection_changes_global_truth is False
    assert result.methodology_inspected is False
    assert result.methodology_mutated is False


def test_position_threat_requires_open_position_monitoring_capability() -> None:
    facts = (
        _fact(
            "fact-threat",
            SharedIntelligenceClass.POSITION_THREAT,
            markets=("GBPJPY",),
            horizons=("M5",),
        ),
    )
    result = route_shared_facts_to_trader(
        capability=_capability(monitor=False),
        facts=facts,
        projection_id="projection-2",
        snapshot_id="global-1",
        projected_at=T0,
        global_state_fingerprint=FP,
    )

    assert result.routed_fact_refs == ()
    assert dict(result.omission_reasons)["fact-threat"] == (
        "NO_OPEN_POSITION_MONITORING_CAPABILITY"
    )


def test_global_fact_routes_without_changing_global_truth() -> None:
    fact = _fact("fact-global", SharedIntelligenceClass.WORLD_EXPLANATION)
    result = route_shared_facts_to_trader(
        capability=_capability(),
        facts=(fact,),
        projection_id="projection-3",
        snapshot_id="global-1",
        projected_at=T0,
        global_state_fingerprint=FP,
    )
    assert result.routed_fact_refs == ("fact-global",)
    assert result.projection.global_state_fingerprint == FP
    assert result.projection.projection_changes_global_truth is False


def test_future_fact_is_rejected() -> None:
    fact = _fact(
        "fact-future",
        SharedIntelligenceClass.WORLD_EXPLANATION,
        cutoff=T0 + timedelta(seconds=1),
    )
    with pytest.raises(ValueError, match="future evidence"):
        route_shared_facts_to_trader(
            capability=_capability(),
            facts=(fact,),
            projection_id="projection-4",
            snapshot_id="global-1",
            projected_at=T0,
            global_state_fingerprint=FP,
        )


def test_methodology_visibility_is_not_required_or_allowed() -> None:
    cap = _capability()
    assert cap.methodology_visible_to_shared is False
    assert cap.shared_methodology_mutation_authority is False

    result = route_shared_facts_to_trader(
        capability=cap,
        facts=(
            _fact(
                "fact-opp",
                SharedIntelligenceClass.OPPORTUNITY,
                markets=("GBPJPY",),
                horizons=("H4",),
            ),
        ),
        projection_id="projection-5",
        snapshot_id="global-1",
        projected_at=T0,
        global_state_fingerprint=FP,
    )
    assert result.methodology_inspected is False
    assert result.methodology_mutated is False
    assert result.execution_authority is False
    assert result.capital_authority is False
    assert result.risk_authority is False
