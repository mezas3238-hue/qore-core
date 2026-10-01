from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t03_equivalent_expression import (
    T03ExpressionEconomics,
    T03NormalizedExposureComponent,
    assess_t03_equivalent_expression,
)

T0 = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
EXPOSURE = (
    T03NormalizedExposureComponent(
        factor_id="US_EQUITY_BETA",
        signed_exposure_usd=Decimal("1000"),
    ),
)


def _expression(
    *,
    qore_symbol: str,
    provider_symbol: str,
    margin: str,
    stop_risk: str = "10",
    stressed_loss: str = "12",
    execution_cost: str = "1",
    provider_verified: bool = True,
    execution_supported: bool = True,
    exposure=EXPOSURE,
) -> T03ExpressionEconomics:
    return T03ExpressionEconomics(
        provider_key="ctrader-demo",
        account_fingerprint_sha256="a" * 64,
        qore_symbol=qore_symbol,
        provider_symbol=provider_symbol,
        observed_at=T0 - timedelta(seconds=2),
        known_at=T0 - timedelta(seconds=1),
        normalized_exposure=exposure,
        margin_occupancy_usd=Decimal(margin),
        stop_risk_usd=Decimal(stop_risk),
        stressed_loss_usd=Decimal(stressed_loss),
        execution_cost_usd=Decimal(execution_cost),
        provider_verified=provider_verified,
        execution_supported=execution_supported,
        evidence_sha256="sha256:" + "1" * 64,
    )


def test_lower_margin_equivalent_expression_is_only_mechanically_eligible() -> None:
    report = assess_t03_equivalent_expression(
        target=_expression(
            qore_symbol="NAS100",
            provider_symbol="US100",
            margin="100",
        ),
        candidate=_expression(
            qore_symbol="NAS100_EQUIVALENT",
            provider_symbol="US100_ALT",
            margin="60",
        ),
        decision_at=T0,
    )

    assert report.normalized_exposure_equivalent is True
    assert report.lower_margin is True
    assert report.margin_saved_usd == Decimal("40")
    assert report.margin_reduction_fraction == Decimal("0.4")
    assert report.no_stop_risk_increase is True
    assert report.no_stressed_loss_increase is True
    assert report.mechanically_eligible is True
    assert report.fresh_oos_utility_demonstrated is False
    assert report.t03_policy_ready is False
    assert report.productive_authority is False
    assert report.blockers == (
        "T03_FRESH_OOS_EQUIVALENT_EXPRESSION_UTILITY_REQUIRED",
        "T03_HISTORICAL_2017_MARGIN_TERMS_NOT_PROVEN",
    )


def test_different_normalized_exposure_is_not_equivalent() -> None:
    other = (
        T03NormalizedExposureComponent(
            factor_id="US_EQUITY_BETA",
            signed_exposure_usd=Decimal("900"),
        ),
    )
    report = assess_t03_equivalent_expression(
        target=_expression(
            qore_symbol="NAS100",
            provider_symbol="US100",
            margin="100",
        ),
        candidate=_expression(
            qore_symbol="NAS100_EQUIVALENT",
            provider_symbol="US100_ALT",
            margin="60",
            exposure=other,
        ),
        decision_at=T0,
    )

    assert report.mechanically_eligible is False
    assert "T03_NORMALIZED_EXPOSURE_NOT_EQUIVALENT" in report.blockers


def test_lower_margin_cannot_hide_more_stop_or_stressed_loss() -> None:
    target = _expression(
        qore_symbol="NAS100",
        provider_symbol="US100",
        margin="100",
    )
    candidate = _expression(
        qore_symbol="NAS100_EQUIVALENT",
        provider_symbol="US100_ALT",
        margin="60",
        stop_risk="11",
        stressed_loss="13",
    )
    report = assess_t03_equivalent_expression(
        target=target,
        candidate=candidate,
        decision_at=T0,
    )

    assert report.mechanically_eligible is False
    assert "T03_STOP_RISK_INCREASES" in report.blockers
    assert "T03_STRESSED_LOSS_INCREASES" in report.blockers


def test_unverified_or_unsupported_candidate_stays_fail_closed() -> None:
    target = _expression(
        qore_symbol="NAS100",
        provider_symbol="US100",
        margin="100",
    )
    candidate = _expression(
        qore_symbol="NAS100_EQUIVALENT",
        provider_symbol="US100_ALT",
        margin="60",
        provider_verified=False,
        execution_supported=False,
    )
    report = assess_t03_equivalent_expression(
        target=target,
        candidate=candidate,
        decision_at=T0,
    )

    assert report.mechanically_eligible is False
    assert "T03_PROVIDER_EVIDENCE_NOT_VERIFIED" in report.blockers
    assert "T03_EXECUTION_SUPPORT_INCOMPLETE" in report.blockers


def test_future_known_candidate_is_rejected() -> None:
    target = _expression(
        qore_symbol="NAS100",
        provider_symbol="US100",
        margin="100",
    )
    candidate = replace(
        _expression(
            qore_symbol="NAS100_EQUIVALENT",
            provider_symbol="US100_ALT",
            margin="60",
        ),
        known_at=T0 + timedelta(seconds=1),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="future-known evidence",
    ):
        assess_t03_equivalent_expression(
            target=target,
            candidate=candidate,
            decision_at=T0,
        )
