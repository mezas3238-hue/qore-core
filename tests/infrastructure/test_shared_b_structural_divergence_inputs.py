from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.shared_b_structural_divergence_inputs import (
    SharedBStructuralDirection,
    SharedBStructuralInputStatus,
    SharedBStructuralObservation,
    build_cross_asset_structural_input,
)

NOW=datetime(2026,9,30,18,30,tzinfo=UTC)


def _obs(observation_id: str, key: str, **overrides: object) -> SharedBStructuralObservation:
    values:dict[str,object]={
        "observation_id":observation_id,
        "canonical_observation_key":key,
        "asset_family":"EQUITY_INDEX",
        "horizon":"M1",
        "observed_at":NOW,
        "evidence_cutoff_at":NOW,
        "direction":SharedBStructuralDirection.UP,
        "relative_position_bps":6_000,
        "displacement_bps":5_000,
        "volatility_bps":4_000,
        "canonical_identity_verified":True,
        "market_state_known":True,
        "market_open":True,
        "freshness_passed":True,
        "data_health_passed":True,
        "provenance_refs":(f"source:{observation_id}",),
    }
    values.update(overrides)
    return SharedBStructuralObservation(**values)  # type: ignore[arg-type]


def test_comparable_pair_exposes_structural_inputs_without_declaring_divergence() -> None:
    result=build_cross_asset_structural_input(
        comparison_id="CMP:US2000:XAUUSD:M1",
        source=_obs("SRC","QORE:OBS:US2000"),
        target=_obs(
            "TGT",
            "QORE:OBS:XAUUSD",
            asset_family="METAL_REFERENCE",
            direction=SharedBStructuralDirection.DOWN,
            relative_position_bps=3_000,
            observed_at=NOW-timedelta(milliseconds=250),
            evidence_cutoff_at=NOW-timedelta(milliseconds=250),
        ),
        as_of=NOW,
        maximum_temporal_skew_ms=500,
    )
    assert result.status is SharedBStructuralInputStatus.COMPARABLE
    assert result.temporal_skew_ms == 250
    assert result.source_direction is SharedBStructuralDirection.UP
    assert result.target_direction is SharedBStructuralDirection.DOWN
    assert result.divergence_declared is False
    assert result.causality_declared is False
    assert result.opportunity_declared is False
    assert result.trade_priority_authority is False
    assert result.capital_priority_authority is False
    assert len(result.fingerprint())==64


def test_closed_or_stale_market_is_not_comparable() -> None:
    for overrides in (
        {"market_open":False},
        {"freshness_passed":False},
        {"data_health_passed":False},
    ):
        result=build_cross_asset_structural_input(
            comparison_id="CMP",
            source=_obs("SRC","S",**overrides),
            target=_obs("TGT","T"),
            as_of=NOW,
            maximum_temporal_skew_ms=500,
        )
        assert result.status is SharedBStructuralInputStatus.NOT_COMPARABLE
        assert result.temporal_skew_ms is None
        assert result.source_direction is None
        assert result.target_direction is None


def test_unknown_identity_or_structure_is_insufficient() -> None:
    identity=build_cross_asset_structural_input(
        comparison_id="CMP1",
        source=_obs("SRC","S",canonical_identity_verified=False),
        target=_obs("TGT","T"),
        as_of=NOW,
        maximum_temporal_skew_ms=500,
    )
    structure=build_cross_asset_structural_input(
        comparison_id="CMP2",
        source=_obs(
            "SRC","S",
            direction=SharedBStructuralDirection.UNKNOWN,
            relative_position_bps=None,
        ),
        target=_obs("TGT","T"),
        as_of=NOW,
        maximum_temporal_skew_ms=500,
    )
    assert identity.status is SharedBStructuralInputStatus.INSUFFICIENT
    assert structure.status is SharedBStructuralInputStatus.INSUFFICIENT


def test_temporal_skew_exceeding_policy_fails_closed() -> None:
    result=build_cross_asset_structural_input(
        comparison_id="CMP",
        source=_obs("SRC","S"),
        target=_obs(
            "TGT","T",
            observed_at=NOW-timedelta(seconds=2),
            evidence_cutoff_at=NOW-timedelta(seconds=2),
        ),
        as_of=NOW,
        maximum_temporal_skew_ms=500,
    )
    assert result.status is SharedBStructuralInputStatus.NOT_COMPARABLE
    assert "TEMPORAL_SKEW_EXCEEDS_POLICY" in result.reason_codes


def test_future_evidence_is_rejected() -> None:
    with pytest.raises(ValueError,match="future structural evidence"):
        _obs(
            "SRC","S",
            observed_at=NOW,
            evidence_cutoff_at=NOW+timedelta(milliseconds=1),
        )

    with pytest.raises(ValueError,match="future structural observation"):
        build_cross_asset_structural_input(
            comparison_id="CMP",
            source=_obs(
                "SRC","S",
                observed_at=NOW+timedelta(seconds=1),
                evidence_cutoff_at=NOW,
            ),
            target=_obs("TGT","T"),
            as_of=NOW,
            maximum_temporal_skew_ms=500,
        )


def test_structural_observation_rejects_outcome_or_authority() -> None:
    for field in (
        "target_or_outcome_used","pnl_used","execution_authority",
        "risk_authority","sizing_authority","capital_authority",
    ):
        with pytest.raises(ValueError,match="forbidden evidence"):
            _obs("SRC","S",**{field:True})
