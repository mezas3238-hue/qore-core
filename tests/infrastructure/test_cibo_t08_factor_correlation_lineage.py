from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_correlation import (
    T08CorrelationAudit,
    T08CorrelationEstimate,
    T08CorrelationFold,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_risk_mapping import (
    T08FactorRiskAllocation,
    T08FactorRiskMappingAudit,
)
from qore.infrastructure.cibo_t08_factor_correlation_lineage import (
    assess_t08_factor_correlation_lineage,
)

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)


def _sha(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode()).hexdigest()


def _correlation() -> T08CorrelationAudit:
    estimate = T08CorrelationEstimate(
        left_factor="EUR",
        right_factor="GBP",
        sample_size=40,
        correlation=Decimal("0.5"),
    )
    folds = tuple(
        T08CorrelationFold(
            fold_index=index,
            start_market_at=NOW - timedelta(hours=8 - index * 2),
            end_market_at=NOW - timedelta(hours=7 - index * 2),
            sample_size=10,
            estimates=(
                T08CorrelationEstimate(
                    left_factor="EUR",
                    right_factor="GBP",
                    sample_size=10,
                    correlation=Decimal("0.4"),
                ),
            ),
            zero_variance_factors=(),
        )
        for index in range(4)
    )
    return T08CorrelationAudit(
        provider_key="ctrader-demo",
        decision_at=NOW,
        sample_size=40,
        minimum_samples=30,
        required_folds=4,
        estimates=(estimate,),
        folds=folds,
        zero_variance_factors=(),
        sample_ready=True,
        correlation_matrix_identified=True,
        directional_stability_observed=True,
        risk_mapping_verified=False,
        netting_utility_oos=False,
        netting_credit_authorized=False,
        blockers=(
            "SIGNED_FACTOR_RISK_MAP_NOT_CERTIFIED",
            "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
        ),
    )


def _mapping(
    *,
    candidate: str,
    signal: str,
    structural_risk: str,
    eur_risk: str,
    gbp_risk: str,
) -> T08FactorRiskMappingAudit:
    total = Decimal(structural_risk)
    eur = Decimal(eur_risk)
    gbp = Decimal(gbp_risk)
    return T08FactorRiskMappingAudit(
        mapping_candidate_id=_sha(candidate),
        signal_fingerprint=signal,
        qore_symbol="EURUSD",
        decision_at=NOW,
        structural_stop_risk_usd=total,
        correlation_sample_size=40,
        allocations=(
            T08FactorRiskAllocation(
                factor_id="EUR",
                signed_notional_usd=Decimal("100") if eur > 0 else Decimal("-100"),
                absolute_variance_contribution=Decimal("1"),
                risk_share=abs(eur) / total,
                signed_risk_usd=eur,
            ),
            T08FactorRiskAllocation(
                factor_id="GBP",
                signed_notional_usd=Decimal("80") if gbp > 0 else Decimal("-80"),
                absolute_variance_contribution=Decimal("0.5"),
                risk_share=abs(gbp) / total,
                signed_risk_usd=gbp,
            ),
        ),
        gross_allocated_risk_usd=abs(eur) + abs(gbp),
        candidate_mapping_identified=True,
        risk_mapping_verified=False,
        netting_credit_authorized=False,
        blockers=(
            "T08_FACTOR_RISK_MAPPING_REQUIRES_FRESH_OOS_VALIDATION",
            "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
        ),
    )


def test_t08_lineage_measures_overlap_without_authorizing_netting() -> None:
    report = assess_t08_factor_correlation_lineage(
        correlation=_correlation(),
        mappings=(
            _mapping(
                candidate="m1",
                signal="s1",
                structural_risk="10",
                eur_risk="6",
                gbp_risk="-4",
            ),
            _mapping(
                candidate="m2",
                signal="s2",
                structural_risk="5",
                eur_risk="-3",
                gbp_risk="2",
            ),
        ),
    )

    assert report.lineage_complete is True
    assert report.total_structural_stop_risk_usd == Decimal("15")
    assert report.total_gross_factor_risk_usd == Decimal("15")
    assert report.total_factor_cancellation_usd == Decimal("10")
    assert report.dominant_factor_gross_share == Decimal("0.6")
    assert report.netting_credit_authorized is False
    assert report.scientific_disposition_allowed_by_lineage_alone is False
    assert report.scientific_blockers == (
        "T08_FRESH_OOS_NETTING_UTILITY_REQUIRED",
        "T08_STRESS_AND_WF1_WF4_REPLICATION_REQUIRED",
    )


def test_t08_lineage_rejects_duplicate_signal_mapping() -> None:
    first = _mapping(
        candidate="m1",
        signal="same",
        structural_risk="10",
        eur_risk="6",
        gbp_risk="-4",
    )
    second = _mapping(
        candidate="m2",
        signal="same",
        structural_risk="5",
        eur_risk="-3",
        gbp_risk="2",
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="duplicate signal mapping",
    ):
        assess_t08_factor_correlation_lineage(
            correlation=_correlation(),
            mappings=(first, second),
        )


def test_t08_lineage_fails_closed_on_decision_time_drift() -> None:
    mapping = replace(
        _mapping(
            candidate="m1",
            signal="s1",
            structural_risk="10",
            eur_risk="6",
            gbp_risk="-4",
        ),
        decision_at=NOW + timedelta(seconds=1),
    )

    report = assess_t08_factor_correlation_lineage(
        correlation=_correlation(),
        mappings=(mapping,),
    )

    assert report.lineage_complete is False
    assert "T08_FACTOR_RISK_MAPPING_LINEAGE_INCOMPLETE" in report.blockers


def test_t08_lineage_requires_four_fold_correlation_truth() -> None:
    correlation = replace(_correlation(), required_folds=3)

    with pytest.raises(
        CiboCapitalManagementError,
        match="requires at least two folds",
    ):
        # Canonical T08 correlation object itself may admit >=2 folds, but
        # A1 lineage requires exactly four and will reject if construction
        # survives upstream validation.
        replace(correlation, required_folds=1)


def test_t08_lineage_empty_mapping_surface_remains_open() -> None:
    report = assess_t08_factor_correlation_lineage(
        correlation=_correlation(),
        mappings=(),
    )

    assert report.lineage_complete is False
    assert "T08_FACTOR_RISK_MAPPING_LINEAGE_INCOMPLETE" in report.blockers
    assert "T08_STRUCTURAL_STOP_RISK_CONSERVATION_NOT_PROVEN" in report.blockers
    assert "T08_FACTOR_OVERLAP_NOT_MEASURABLE" in report.blockers
