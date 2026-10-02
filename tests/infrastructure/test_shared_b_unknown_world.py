from __future__ import annotations

from datetime import UTC, datetime

import pytest

from qore.infrastructure.core_stack_v2.shared_b_unknown_world import (
    SharedBWorldKnowledgeState,
    SharedBWorldObservation,
    world_observation_can_support_new_claim,
    world_observation_requires_abstention,
)

NOW=datetime(2026,9,30,18,0,tzinfo=UTC)


def _world(**overrides: object) -> SharedBWorldObservation:
    values:dict[str,object]={
        "observation_key":"MARKET:US2000:M1",
        "as_of":NOW,
        "evidence_cutoff_at":NOW,
        "state":SharedBWorldKnowledgeState.OBSERVED,
        "value_present":True,
        "quality_bps":10_000,
        "uncertainty_bps":0,
        "reason_codes":("OBSERVED_CAUSAL",),
        "provenance_refs":("source:sealed",),
    }
    values.update(overrides)
    return SharedBWorldObservation(**values)  # type: ignore[arg-type]


def test_only_observed_state_supports_new_claim() -> None:
    observed=_world()
    assert world_observation_can_support_new_claim(observed) is True
    assert world_observation_requires_abstention(observed) is False

    for state in (
        SharedBWorldKnowledgeState.MISSING,
        SharedBWorldKnowledgeState.NOT_OBSERVED,
        SharedBWorldKnowledgeState.UNKNOWN,
        SharedBWorldKnowledgeState.INSUFFICIENT,
    ):
        value=_world(
            state=state,
            value_present=False,
            quality_bps=None,
            uncertainty_bps=10_000,
            reason_codes=(state.value,),
        )
        assert world_observation_can_support_new_claim(value) is False
        assert world_observation_requires_abstention(value) is True


def test_unknown_missing_not_observed_cannot_claim_value() -> None:
    for state in (
        SharedBWorldKnowledgeState.MISSING,
        SharedBWorldKnowledgeState.NOT_OBSERVED,
        SharedBWorldKnowledgeState.UNKNOWN,
        SharedBWorldKnowledgeState.INSUFFICIENT,
    ):
        with pytest.raises(ValueError,match="cannot claim an observed value"):
            _world(state=state)


def test_unknown_world_forbids_neutral_safe_or_productive_default() -> None:
    for field in (
        "neutral_assumption_applied",
        "safe_assumption_applied",
        "productive_authority",
    ):
        with pytest.raises(ValueError,match="silently normalized"):
            _world(**{field:True})


def test_future_world_evidence_fails_closed() -> None:
    with pytest.raises(ValueError,match="future world evidence"):
        _world(
            evidence_cutoff_at=datetime(2026,9,30,18,1,tzinfo=UTC)
        )
