from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    AdvancedToolDisposition,
    evaluate_margin_efficiency,
)
from qore.infrastructure.cibo_ce2i_t03_equivalent_expression import (
    T03EquivalentExpressionDeclaration,
    T03ExpressionEconomics,
    T03NormalizedExposureComponent,
)
from qore.infrastructure.cibo_profitability_lab_t03_predecision_adapter import (
    T03ShadowAdapterStatus,
    adapt_t03_predecision_shadow,
)

T0 = datetime(2026, 10, 1, 3, 0, tzinfo=UTC)
EXPOSURE = (
    T03NormalizedExposureComponent(
        factor_id="US_EQUITY_BETA",
        signed_exposure_usd=Decimal("1000"),
    ),
)


def _declaration() -> T03EquivalentExpressionDeclaration:
    return T03EquivalentExpressionDeclaration(
        declaration_id="t03-adapter-001",
        provider_key="ctrader-demo",
        account_fingerprint_sha256="a" * 64,
        target_qore_symbol="NAS100",
        target_provider_symbol="US100",
        candidate_qore_symbol="NAS100_EQUIVALENT",
        candidate_provider_symbol="US100_ALT",
        normalized_factor_ids=("US_EQUITY_BETA",),
        declared_at=T0 - timedelta(seconds=3),
        evidence_sha256="sha256:" + "d" * 64,
    )


def _expression(
    *,
    qore_symbol: str,
    provider_symbol: str,
    margin: str,
) -> T03ExpressionEconomics:
    return T03ExpressionEconomics(
        provider_key="ctrader-demo",
        account_fingerprint_sha256="a" * 64,
        qore_symbol=qore_symbol,
        provider_symbol=provider_symbol,
        observed_at=T0 - timedelta(seconds=2),
        known_at=T0 - timedelta(seconds=1),
        normalized_exposure=EXPOSURE,
        margin_occupancy_usd=Decimal(margin),
        stop_risk_usd=Decimal("10"),
        stressed_loss_usd=Decimal("12"),
        execution_cost_usd=Decimal("1"),
        provider_verified=True,
        execution_supported=True,
        evidence_sha256="sha256:" + "1" * 64,
    )


def test_t03_adapter_transports_causal_measurement_without_policy_authority() -> None:
    result = adapt_t03_predecision_shadow(
        signal_fingerprint="signal-t03",
        declaration=_declaration(),
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

    assert result.status is T03ShadowAdapterStatus.SHADOW_AVAILABLE
    assert result.economic_authority is False
    assert result.evidence is not None
    assert result.evidence.observed_at == T0 - timedelta(seconds=1)
    assert result.evidence.fresh_oos_utility_demonstrated is False
    assert result.evidence.policy_authorized is False

    decision = evaluate_margin_efficiency(result.evidence)
    assert decision.disposition is AdvancedToolDisposition.FAIL_CLOSED
    assert "fresh OOS" in decision.reason
