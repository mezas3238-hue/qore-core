from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t16_hedge_candidate import (
    T16HedgePairDeclaration,
    T16HedgeReturnObservation,
    assess_t16_hedge_candidate,
)

T0 = datetime(2026, 10, 1, 2, 0, tzinfo=UTC)


def _declaration() -> T16HedgePairDeclaration:
    return T16HedgePairDeclaration(
        declaration_id="t16-pair-001",
        provider_key="ctrader-demo",
        target_symbol="NAS100",
        hedge_symbol="SPX500",
        declared_at=T0 - timedelta(seconds=1),
        evidence_sha256="sha256:" + "d" * 64,
    )


def _rows(
    count: int,
    *,
    execution_supported: bool = True,
) -> tuple[T16HedgeReturnObservation, ...]:
    rows = []
    for index in range(count):
        start = T0 + timedelta(minutes=5 * index)
        hedge = Decimal(index % 7 - 3) / Decimal("1000")
        target = hedge * Decimal("1.5")
        rows.append(
            T16HedgeReturnObservation(
                provider_key="ctrader-demo",
                target_symbol="NAS100",
                hedge_symbol="SPX500",
                start_market_at=start,
                end_market_at=start + timedelta(minutes=5),
                known_at=start + timedelta(minutes=5),
                target_return=target,
                hedge_return=hedge,
                hedge_cost_bps=Decimal("1.25"),
                execution_supported=execution_supported,
                source_evidence_sha256="sha256:" + f"{index + 1:064x}",
            )
        )
    return tuple(rows)


def test_ready_measurement_still_cannot_promote_t16_policy() -> None:
    report = assess_t16_hedge_candidate(
        declaration=_declaration(),
        observations=_rows(40),
        decision_at=T0 + timedelta(hours=4),
    )

    assert report.sample_ready is True
    assert report.fold_coverage_ready is True
    assert report.correlation == Decimal("1")
    assert report.correlation_stable is True
    assert report.hedge_beta == Decimal("1.5")
    assert report.basis_error_rms == Decimal("0")
    assert report.mean_hedge_cost_bps == Decimal("1.25")
    assert report.execution_support_complete is True
    assert report.measurement_ready is True
    assert report.fresh_oos_utility_demonstrated is False
    assert report.t16_policy_ready is False
    assert report.productive_authority is False
    assert report.blockers == (
        "T16_NET_ECONOMIC_BENEFIT_NOT_PROVEN",
        "T16_FRESH_OOS_HEDGE_UTILITY_REQUIRED",
    )


def test_insufficient_sample_stays_fail_closed() -> None:
    report = assess_t16_hedge_candidate(
        declaration=_declaration(),
        observations=_rows(8),
        decision_at=T0 + timedelta(hours=1),
        minimum_samples=30,
        required_folds=4,
    )

    assert report.sample_ready is False
    assert report.measurement_ready is False
    assert "T16_MINIMUM_SAMPLE_NOT_MET:8/30" in report.blockers


def test_missing_execution_support_is_explicit_blocker() -> None:
    report = assess_t16_hedge_candidate(
        declaration=_declaration(),
        observations=_rows(40, execution_supported=False),
        decision_at=T0 + timedelta(hours=4),
    )

    assert report.execution_support_complete is False
    assert report.measurement_ready is False
    assert "T16_PROVIDER_EXECUTION_SUPPORT_INCOMPLETE" in report.blockers


def test_future_known_evidence_is_rejected() -> None:
    rows = _rows(2)
    decision_at = rows[-1].end_market_at - timedelta(seconds=1)

    with pytest.raises(
        CiboCapitalManagementError,
        match="future-known evidence",
    ):
        assess_t16_hedge_candidate(
            declaration=_declaration(),
            observations=rows,
            decision_at=decision_at,
            minimum_samples=2,
            required_folds=2,
        )


def test_mixed_pairs_are_rejected() -> None:
    rows = list(_rows(2))
    rows[1] = T16HedgeReturnObservation(
        provider_key=rows[1].provider_key,
        target_symbol=rows[1].target_symbol,
        hedge_symbol="US30",
        start_market_at=rows[1].start_market_at,
        end_market_at=rows[1].end_market_at,
        known_at=rows[1].known_at,
        target_return=rows[1].target_return,
        hedge_return=rows[1].hedge_return,
        hedge_cost_bps=rows[1].hedge_cost_bps,
        execution_supported=True,
        source_evidence_sha256=rows[1].source_evidence_sha256,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="one provider and one fixed pair",
    ):
        assess_t16_hedge_candidate(
            declaration=_declaration(),
            observations=tuple(rows),
            decision_at=T0 + timedelta(hours=1),
            minimum_samples=2,
            required_folds=2,
        )


def test_pair_must_be_declared_before_return_windows() -> None:
    rows = _rows(2)
    declaration = T16HedgePairDeclaration(
        declaration_id="late-pair",
        provider_key="ctrader-demo",
        target_symbol="NAS100",
        hedge_symbol="SPX500",
        declared_at=T0 + timedelta(seconds=1),
        evidence_sha256="sha256:" + "e" * 64,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="declared before observed return windows",
    ):
        assess_t16_hedge_candidate(
            declaration=declaration,
            observations=rows,
            decision_at=T0 + timedelta(hours=1),
            minimum_samples=2,
            required_folds=2,
        )


def test_pair_declaration_identity_drift_is_rejected() -> None:
    rows = _rows(2)
    declaration = T16HedgePairDeclaration(
        declaration_id="wrong-pair",
        provider_key="ctrader-demo",
        target_symbol="NAS100",
        hedge_symbol="US30",
        declared_at=T0 - timedelta(seconds=1),
        evidence_sha256="sha256:" + "e" * 64,
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="identity drift",
    ):
        assess_t16_hedge_candidate(
            declaration=declaration,
            observations=rows,
            decision_at=T0 + timedelta(hours=1),
            minimum_samples=2,
            required_folds=2,
        )
