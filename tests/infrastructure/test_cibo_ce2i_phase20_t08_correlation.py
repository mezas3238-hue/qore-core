from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_correlation import (
    assess_t08_correlation_readiness,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_returns import (
    FROZEN_T08_FACTOR_IDS,
    T08FactorReturn,
    T08FactorReturnObservation,
    T08MarketCollectionBasis,
)

BASE = datetime(2026, 9, 28, tzinfo=UTC)


def _observation(index: int) -> T08FactorReturnObservation:
    start = BASE + timedelta(minutes=5 * index)
    end = start + timedelta(minutes=5)
    base = Decimal(index + 1) / Decimal("10000")
    returns = {
        "AUD": base,
        "EUR": base * Decimal(2),
        "GBP": base * Decimal(3),
        "JPY": -base,
        "USD": Decimal(0),
        "US_TECH_EQUITY_BETA": base * Decimal(4),
        "XAU": -base * Decimal(2),
    }
    return T08FactorReturnObservation(
        provider_key="ctrader-demo",
        start_snapshot_id=f"s{index}",
        end_snapshot_id=f"s{index + 1}",
        start_market_at=start,
        end_market_at=end,
        known_at=end + timedelta(milliseconds=100),
        collection_basis=T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE,
        factor_returns=tuple(
            T08FactorReturn(
                factor_id=factor_id,
                gross_change=Decimal(1) + returns[factor_id],
                fractional_return=returns[factor_id],
            )
            for factor_id in FROZEN_T08_FACTOR_IDS
        ),
        source_evidence_refs=(f"factor-return:{index}",),
    )


def test_correlation_audit_identifies_predecision_four_fold_matrix() -> None:
    observations = tuple(_observation(index) for index in range(32))
    decision_at = observations[-1].known_at + timedelta(seconds=1)

    audit = assess_t08_correlation_readiness(
        observations=observations,
        decision_at=decision_at,
    )

    assert audit.sample_size == 32
    assert audit.sample_ready is True
    assert len(audit.folds) == 4
    assert all(item.sample_size == 8 for item in audit.folds)
    assert audit.zero_variance_factors == ()
    assert audit.correlation_matrix_identified is True
    assert audit.directional_stability_observed is True
    assert audit.risk_mapping_verified is False
    assert audit.netting_utility_oos is False
    assert audit.netting_credit_authorized is False
    assert "SIGNED_FACTOR_RISK_MAP_NOT_CERTIFIED" in audit.blockers
    assert "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED" in audit.blockers


def test_correlation_audit_stays_unidentified_below_minimum_sample() -> None:
    observations = tuple(_observation(index) for index in range(12))

    audit = assess_t08_correlation_readiness(
        observations=observations,
        decision_at=observations[-1].known_at + timedelta(seconds=1),
    )

    assert audit.sample_ready is False
    assert audit.correlation_matrix_identified is False
    assert audit.netting_credit_authorized is False
    assert "T08_CORRELATION_MINIMUM_SAMPLE_NOT_MET:12/30" in audit.blockers


def test_correlation_audit_rejects_future_known_observation() -> None:
    observations = tuple(_observation(index) for index in range(4))

    with pytest.raises(
        CiboCapitalManagementError,
        match="future-known",
    ):
        assess_t08_correlation_readiness(
            observations=observations,
            decision_at=observations[-1].known_at - timedelta(microseconds=1),
        )


def test_correlation_audit_rejects_overlapping_return_intervals() -> None:
    first = _observation(0)
    second = T08FactorReturnObservation(
        provider_key=first.provider_key,
        start_snapshot_id="overlap-start",
        end_snapshot_id="overlap-end",
        start_market_at=first.start_market_at + timedelta(minutes=1),
        end_market_at=first.end_market_at + timedelta(minutes=1),
        known_at=first.known_at + timedelta(minutes=1),
        collection_basis=T08MarketCollectionBasis.FULL_FROZEN_UNIVERSE,
        factor_returns=first.factor_returns,
        source_evidence_refs=("overlap",),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="must not overlap",
    ):
        assess_t08_correlation_readiness(
            observations=(first, second),
            decision_at=second.known_at + timedelta(seconds=1),
        )
