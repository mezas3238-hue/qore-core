from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_genc10_transition_uncertainty_calibration import (
    GENC10_TRANSITION_CALIBRATION_ID,
    Genc10ObservedTransition,
    Genc10TransitionEvidenceKind,
    calibrate_genc10_transition_uncertainty,
)

T0 = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
POPULATION_SHA = "sha256:" + "a" * 64


def _sha(char: str) -> str:
    return "sha256:" + char * 64


def _observation(
    index: int,
    *,
    conditioning_key: str = "BALANCED",
) -> Genc10ObservedTransition:
    start = T0 + timedelta(hours=index * 2)
    return Genc10ObservedTransition(
        transition_id=f"transition-{index}",
        account_identity_fingerprint="ctrader:demo:account-a",
        conditioning_key=conditioning_key,
        start_twin_sha256=_sha("1"),
        end_twin_sha256=_sha("2"),
        provider_registry_sha256=_sha("3"),
        observed_start_at=start,
        observed_end_at=start + timedelta(hours=1),
        realized_capital_delta_usd=Decimal(str(index)),
        compound_value_delta_usd=Decimal(str(index - 1)),
        protected_floor_delta_usd=Decimal("0"),
        stop_risk_capacity_delta_usd=Decimal("-1"),
        stop_risk_usage_delta_usd=Decimal("0.5"),
        margin_capacity_delta_usd=Decimal("-2"),
        margin_usage_delta_usd=Decimal("1"),
        active_deployment_count_delta=index - 1,
        known_option_count_delta=1 - index,
        provider_constraints_changed=index == 2,
        evidence_kind=Genc10TransitionEvidenceKind.FORWARD_OBSERVED,
        decision_population_sha256=POPULATION_SHA,
    )


def test_genc10_transition_calibration_builds_descriptive_support_only() -> None:
    report = calibrate_genc10_transition_uncertainty(
        observations=(
            _observation(1),
            _observation(2),
            _observation(3, conditioning_key="CRISIS"),
        ),
        source_population_sha256=POPULATION_SHA,
        calibration_cutoff_at=T0 + timedelta(days=1),
    )

    assert report.calibration_id == GENC10_TRANSITION_CALIBRATION_ID
    assert report.observation_count == 3
    assert tuple(item.conditioning_key for item in report.supports) == (
        "BALANCED",
        "CRISIS",
    )
    balanced = report.supports[0]
    assert balanced.observation_count == 2
    assert balanced.realized_capital_delta_usd.minimum == Decimal("1")
    assert balanced.realized_capital_delta_usd.maximum == Decimal("2")
    assert balanced.provider_constraint_change_observations == 1
    assert report.report_sha256.startswith("sha256:")
    assert report.frozen_v1_mutated is False
    assert report.market_probability_claimed is False
    assert report.production_policy_selected is False
    assert report.certification_ready is False


def test_genc10_transition_rejects_non_forward_evidence() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="requires FORWARD_OBSERVED evidence",
    ):
        replace(
            _observation(1),
            evidence_kind=Genc10TransitionEvidenceKind.SYNTHETIC_CONTRACT,
        )


def test_genc10_transition_rejects_future_data_or_probability_claim() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="forbids future data/probability claims",
    ):
        replace(_observation(1), future_data_used=True)

    with pytest.raises(
        CiboCompoundCapitalError,
        match="forbids future data/probability claims",
    ):
        replace(_observation(1), market_probability_claimed=True)


def test_genc10_calibration_rejects_mixed_accounts() -> None:
    second = replace(
        _observation(2),
        account_identity_fingerprint="ctrader:demo:account-b",
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot mix account identities",
    ):
        calibrate_genc10_transition_uncertainty(
            observations=(_observation(1), second),
            source_population_sha256=POPULATION_SHA,
            calibration_cutoff_at=T0 + timedelta(days=1),
        )


def test_genc10_calibration_rejects_population_lineage_drift() -> None:
    second = replace(
        _observation(2),
        decision_population_sha256=_sha("f"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="population lineage drift",
    ):
        calibrate_genc10_transition_uncertainty(
            observations=(_observation(1), second),
            source_population_sha256=POPULATION_SHA,
            calibration_cutoff_at=T0 + timedelta(days=1),
        )


def test_genc10_calibration_rejects_at_or_after_cutoff_transition() -> None:
    cutoff = T0 + timedelta(hours=3)
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot consume at/after-cutoff transitions",
    ):
        calibrate_genc10_transition_uncertainty(
            observations=(_observation(1),),
            source_population_sha256=POPULATION_SHA,
            calibration_cutoff_at=cutoff,
        )


def test_genc10_calibration_digest_is_deterministic() -> None:
    kwargs = {
        "observations": (_observation(1), _observation(2)),
        "source_population_sha256": POPULATION_SHA,
        "calibration_cutoff_at": T0 + timedelta(days=1),
    }

    first = calibrate_genc10_transition_uncertainty(**kwargs)
    second = calibrate_genc10_transition_uncertainty(**kwargs)

    assert first.report_sha256 == second.report_sha256

def test_genc10_report_rejects_manual_support_count_drift() -> None:
    report = calibrate_genc10_transition_uncertainty(
        observations=(_observation(1), _observation(2)),
        source_population_sha256=POPULATION_SHA,
        calibration_cutoff_at=T0 + timedelta(days=1),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="observation identity/count drift",
    ):
        replace(report, observation_count=3)

def test_genc10_report_rejects_manual_digest_drift() -> None:
    report = calibrate_genc10_transition_uncertainty(
        observations=(_observation(1), _observation(2)),
        source_population_sha256=POPULATION_SHA,
        calibration_cutoff_at=T0 + timedelta(days=1),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="report digest drift",
    ):
        replace(report, report_sha256=_sha("f"))

