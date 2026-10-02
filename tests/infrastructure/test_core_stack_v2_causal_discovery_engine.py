from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.causal_discovery_engine import (
    CausalDiscoveryEpisode,
    CausalDiscoveryStatus,
    CausalEffectDirection,
    discover_causal_relation,
)
from qore.infrastructure.core_stack_v2.dynamic_causal_graph import (
    CausalConcept,
)

NOW = datetime(2026, 9, 26, 11, 0, tzinfo=UTC)


def _episode(
    *,
    exposed: bool,
    target_bps: int,
    confounder: str,
    regime: str,
    partition: str,
    intervention: bool = True,
    counterfactual_bps: int | None = None,
) -> CausalDiscoveryEpisode:
    return CausalDiscoveryEpisode(
        source=CausalConcept.COMPRESSION,
        target=CausalConcept.EXPANSION_READINESS,
        source_at=NOW - timedelta(minutes=2),
        target_at=NOW - timedelta(minutes=1),
        source_state_bps=8_000 if exposed else 2_000,
        target_state_bps=target_bps,
        confounder_key=confounder,
        regime_key=regime,
        replication_partition=partition,
        natural_intervention=intervention,
        counterfactual_target_without_source_bps=counterfactual_bps,
    )


def _replicated_positive_relation() -> tuple[CausalDiscoveryEpisode, ...]:
    rows: list[CausalDiscoveryEpisode] = []
    for confounder in ("LOW_VOL", "HIGH_VOL"):
        for regime in ("TREND", "RANGE"):
            for partition in ("CAL", "REPL"):
                for _ in range(2):
                    rows.append(
                        _episode(
                            exposed=True,
                            target_bps=8_000,
                            confounder=confounder,
                            regime=regime,
                            partition=partition,
                            counterfactual_bps=2_500,
                        )
                    )
                    rows.append(
                        _episode(
                            exposed=False,
                            target_bps=2_000,
                            confounder=confounder,
                            regime=regime,
                            partition=partition,
                        )
                    )
    return tuple(rows)


def test_replicated_relation_remains_research_only() -> None:
    assessment = discover_causal_relation(
        as_of=NOW,
        episodes=_replicated_positive_relation(),
    )

    assert assessment.status is CausalDiscoveryStatus.RESEARCH_REPLICATED
    assert assessment.direction is CausalEffectDirection.SUPPORTS
    assert assessment.raw_effect_bps == 6_000
    assert assessment.conditional_effect_bps == 6_000
    assert assessment.intervention_effect_bps == 6_000
    assert assessment.counterfactual_effect_bps == 5_500
    assert assessment.temporal_precedence_bps == 10_000
    assert assessment.conditional_sign_stability_bps == 10_000
    assert assessment.cross_regime_stability_bps == 10_000
    assert assessment.replication_stability_bps == 10_000
    assert assessment.replicated is True
    assert assessment.knowledge_promotion_authority is False
    assert assessment.execution_authority is False
    assert assessment.risk_authority is False


def test_confounder_created_association_cannot_be_called_causal() -> None:
    rows: list[CausalDiscoveryEpisode] = []
    for index in range(8):
        rows.append(
            _episode(
                exposed=True,
                target_bps=8_000,
                confounder="RISK_ON",
                regime="TREND",
                partition="CAL" if index < 4 else "REPL",
                intervention=False,
            )
        )
        rows.append(
            _episode(
                exposed=False,
                target_bps=2_000,
                confounder="RISK_OFF",
                regime="RANGE",
                partition="CAL" if index < 4 else "REPL",
                intervention=False,
            )
        )

    assessment = discover_causal_relation(
        as_of=NOW,
        episodes=tuple(rows),
    )

    assert assessment.raw_effect_bps == 6_000
    assert assessment.conditional_effect_bps is None
    assert assessment.conditional_strata_count == 0
    assert assessment.status is CausalDiscoveryStatus.ASSOCIATION_ONLY
    assert assessment.observational_association_only is True
    assert "OBSERVATIONAL_ASSOCIATION_NOT_CAUSAL" in assessment.reasons


def test_neutral_strata_count_against_causal_stability() -> None:
    rows: list[CausalDiscoveryEpisode] = []
    for confounder, exposed_target, control_target in (
        ("A", 8_000, 2_000),
        ("B", 5_000, 5_000),
        ("C", 5_000, 5_000),
        ("D", 5_000, 5_000),
    ):
        for _ in range(2):
            rows.append(
                _episode(
                    exposed=True,
                    target_bps=exposed_target,
                    confounder=confounder,
                    regime="TREND",
                    partition="CAL",
                    intervention=False,
                )
            )
            rows.append(
                _episode(
                    exposed=False,
                    target_bps=control_target,
                    confounder=confounder,
                    regime="TREND",
                    partition="CAL",
                    intervention=False,
                )
            )

    assessment = discover_causal_relation(
        as_of=NOW,
        episodes=tuple(rows),
    )

    assert assessment.raw_effect_bps == 1_500
    assert assessment.conditional_effect_bps == 1_500
    assert assessment.conditional_strata_count == 4
    assert assessment.conditional_sign_stability_bps == 2_500
    assert assessment.status is CausalDiscoveryStatus.ASSOCIATION_ONLY
    assert "OBSERVATIONAL_ASSOCIATION_NOT_CAUSAL" in assessment.reasons


def test_temporal_precedence_failure_falsifies_candidate() -> None:
    rows = list(_replicated_positive_relation())
    rows[0] = replace(
        rows[0],
        source_at=NOW - timedelta(seconds=30),
        target_at=NOW - timedelta(minutes=1),
    )

    assessment = discover_causal_relation(
        as_of=NOW,
        episodes=tuple(rows),
    )

    assert assessment.temporal_precedence_bps < 10_000
    assert assessment.status is CausalDiscoveryStatus.FALSIFIED
    assert "TEMPORAL_PRECEDENCE_FAILED" in assessment.reasons


def test_replication_sign_flip_falsifies_relation() -> None:
    rows: list[CausalDiscoveryEpisode] = []
    for partition, positive, repeats in (
        ("CAL", True, 12),
        ("REPL", False, 4),
    ):
        for index in range(repeats):
            confounder = "A" if index % 2 == 0 else "B"
            regime = "TREND" if index % 2 == 0 else "RANGE"
            rows.append(
                _episode(
                    exposed=True,
                    target_bps=8_000 if positive else 2_000,
                    confounder=confounder,
                    regime=regime,
                    partition=partition,
                    counterfactual_bps=2_500 if positive else 8_500,
                )
            )
            rows.append(
                _episode(
                    exposed=False,
                    target_bps=2_000 if positive else 8_000,
                    confounder=confounder,
                    regime=regime,
                    partition=partition,
                )
            )

    assessment = discover_causal_relation(
        as_of=NOW,
        episodes=tuple(rows),
    )

    assert assessment.raw_effect_bps == 3_000
    assert assessment.replication_stability_bps == 5_000
    assert assessment.status is CausalDiscoveryStatus.FALSIFIED
    assert "REPLICATION_SIGN_INSTABILITY" in assessment.reasons


def test_counterfactual_contradiction_falsifies_relation() -> None:
    rows = tuple(
        replace(
            item,
            counterfactual_target_without_source_bps=9_000,
        )
        if item.source_state_bps >= 6_500
        else item
        for item in _replicated_positive_relation()
    )

    assessment = discover_causal_relation(
        as_of=NOW,
        episodes=rows,
    )

    assert assessment.counterfactual_effect_bps == -1_000
    assert assessment.status is CausalDiscoveryStatus.FALSIFIED
    assert "COUNTERFACTUAL_EVIDENCE_CONTRADICTS" in assessment.reasons


def test_low_integrity_evidence_is_excluded_from_causal_inference() -> None:
    rows = list(_replicated_positive_relation())
    poisoned = replace(
        rows[0],
        target_state_bps=0,
        integrity_bps=1_000,
    )
    rows[0] = poisoned

    assessment = discover_causal_relation(
        as_of=NOW,
        episodes=tuple(rows),
    )

    assert assessment.excluded_low_integrity_count == 1
    assert assessment.sample_count == len(rows) - 1
    assert assessment.status is CausalDiscoveryStatus.RESEARCH_REPLICATED


def test_all_low_integrity_evidence_fails_closed() -> None:
    rows = tuple(
        replace(item, integrity_bps=1_000)
        for item in _replicated_positive_relation()
    )

    with pytest.raises(ValueError, match="integrity gate"):
        discover_causal_relation(
            as_of=NOW,
            episodes=rows,
        )


def test_future_discovery_evidence_fails_closed() -> None:
    row = replace(
        _replicated_positive_relation()[0],
        target_at=NOW + timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="future causal-discovery evidence"):
        discover_causal_relation(
            as_of=NOW,
            episodes=(row,),
        )
