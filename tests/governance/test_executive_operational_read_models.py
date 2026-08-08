from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.governance.executive_control import ExecutiveReadScope
from qore.governance.executive_operational_read_models import (
    ExecutiveAssetClass,
    ExecutiveMarketAuthorizationState,
    ExecutiveMarketAvailability,
    ExecutiveMarketInstrument,
    ExecutiveMarketSummary,
    ExecutiveMarketsReadModel,
    ExecutiveStrategyVersionRef,
    ExecutiveTraderAuthorizationState,
    ExecutiveTraderConfidence,
    ExecutiveTraderId,
    ExecutiveTraderState,
    ExecutiveTraderSummary,
    ExecutiveTradersReadModel,
)
from qore.governance.executive_ports import ExecutiveEvidenceRef
from qore.governance.executive_read_models import (
    ExecutiveAttentionLevel,
    ExecutiveProjectionId,
    ExecutiveProjectionMetadata,
    ExecutiveProjectionVersion,
    ExecutiveReadModelValidationError,
    ExecutiveSourceFreshness,
)

_NOW = datetime(2026, 8, 8, 21, 15, tzinfo=UTC)


def _metadata(scope: ExecutiveReadScope) -> ExecutiveProjectionMetadata:
    return ExecutiveProjectionMetadata(
        projection_id=ExecutiveProjectionId(
            UUID("2a000000-0000-0000-0000-000000000001")
        ),
        projection_version=ExecutiveProjectionVersion("executive-operational.v1"),
        scope=scope,
        source_observed_at=_NOW,
        projected_at=_NOW + timedelta(seconds=1),
        freshness=ExecutiveSourceFreshness.FRESH,
        evidence_refs=(ExecutiveEvidenceRef("evidence:operational/root-001"),),
    )


def _market(symbol: str) -> ExecutiveMarketSummary:
    return ExecutiveMarketSummary(
        instrument=ExecutiveMarketInstrument(symbol),
        asset_class=ExecutiveAssetClass("forex"),
        availability=ExecutiveMarketAvailability.AVAILABLE,
        authorization_state=ExecutiveMarketAuthorizationState.AUTHORIZED,
        regime_code="trend.balanced",
        session_code="new-york",
        reason_codes=("market.certified",),
        evidence_refs=(ExecutiveEvidenceRef(f"evidence:market/{symbol.lower()}"),),
    )


def _trader(trader_id: str) -> ExecutiveTraderSummary:
    return ExecutiveTraderSummary(
        trader_id=ExecutiveTraderId(trader_id),
        kind_code="virtual-trader.structure",
        strategy_version=ExecutiveStrategyVersionRef("strategy.v3"),
        state=ExecutiveTraderState.OPERATING,
        authorization_state=ExecutiveTraderAuthorizationState.AUTHORIZED,
        confidence=ExecutiveTraderConfidence(0.8),
        judgment_code="opportunity.valid",
        market_instruments=(
            ExecutiveMarketInstrument("GBP_USD"),
            ExecutiveMarketInstrument("EUR_USD"),
        ),
        reason_codes=("validation.passed", "risk.allowed"),
        evidence_refs=(ExecutiveEvidenceRef(f"evidence:trader/{trader_id}"),),
    )


def test_market_projection_is_scope_bound_and_provider_free() -> None:
    model = ExecutiveMarketsReadModel(
        metadata=_metadata(ExecutiveReadScope.MARKETS),
        attention=ExecutiveAttentionLevel.INFORMATION,
        markets=(_market("GBP_USD"), _market("EUR_USD")),
    )

    assert model.metadata.scope is ExecutiveReadScope.MARKETS
    assert tuple(item.instrument.symbol for item in model.markets) == (
        "EUR_USD",
        "GBP_USD",
    )
    assert not hasattr(model, "provider")
    assert not hasattr(model, "broker")
    assert not hasattr(model, "credentials")
    assert model.logical_values() == model.logical_values()


def test_market_projection_rejects_wrong_scope_and_duplicate_instruments() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveMarketsReadModel(
            metadata=_metadata(ExecutiveReadScope.TRADERS),
            attention=ExecutiveAttentionLevel.INFORMATION,
            markets=(_market("EUR_USD"),),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveMarketsReadModel(
            metadata=_metadata(ExecutiveReadScope.MARKETS),
            attention=ExecutiveAttentionLevel.ATTENTION,
            markets=(_market("EUR_USD"), _market("EUR_USD")),
        )


def test_market_asset_class_is_extensible_not_forex_locked() -> None:
    crypto = ExecutiveMarketSummary(
        instrument=ExecutiveMarketInstrument("BTC_USD"),
        asset_class=ExecutiveAssetClass("crypto"),
        availability=ExecutiveMarketAvailability.RESTRICTED,
        authorization_state=ExecutiveMarketAuthorizationState.RESTRICTED,
        regime_code="volatility.high",
        session_code="continuous",
        reason_codes=("market.restricted",),
        evidence_refs=(ExecutiveEvidenceRef("evidence:market/btc-usd"),),
    )

    assert crypto.asset_class.value == "crypto"
    assert not hasattr(crypto, "oanda_instrument")


def test_market_summary_requires_structured_evidence_and_safe_codes() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveMarketSummary(
            instrument=ExecutiveMarketInstrument("EUR_USD"),
            asset_class=ExecutiveAssetClass("forex"),
            availability=ExecutiveMarketAvailability.UNKNOWN,
            authorization_state=ExecutiveMarketAuthorizationState.UNKNOWN,
            regime_code="unknown",
            session_code="unknown",
            reason_codes=("evidence.missing",),
            evidence_refs=(),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveMarketSummary(
            instrument=ExecutiveMarketInstrument("EUR_USD"),
            asset_class=ExecutiveAssetClass("forex"),
            availability=ExecutiveMarketAvailability.UNAVAILABLE,
            authorization_state=ExecutiveMarketAuthorizationState.BLOCKED,
            regime_code="token=secret",
            session_code="new-york",
            reason_codes=("market.blocked",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:market/blocked"),),
        )


def test_trader_projection_is_scope_bound_and_deterministic() -> None:
    model = ExecutiveTradersReadModel(
        metadata=_metadata(ExecutiveReadScope.TRADERS),
        attention=ExecutiveAttentionLevel.IMPORTANT,
        traders=(_trader("trader.zeta"), _trader("trader.alpha")),
    )

    assert tuple(item.trader_id.value for item in model.traders) == (
        "trader.alpha",
        "trader.zeta",
    )
    assert model.traders[0].market_instruments == (
        ExecutiveMarketInstrument("EUR_USD"),
        ExecutiveMarketInstrument("GBP_USD"),
    )
    assert model.logical_values() == model.logical_values()


def test_trader_projection_rejects_wrong_scope_and_duplicate_ids() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveTradersReadModel(
            metadata=_metadata(ExecutiveReadScope.MARKETS),
            attention=ExecutiveAttentionLevel.ATTENTION,
            traders=(_trader("trader.alpha"),),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveTradersReadModel(
            metadata=_metadata(ExecutiveReadScope.TRADERS),
            attention=ExecutiveAttentionLevel.CRITICAL,
            traders=(_trader("trader.alpha"), _trader("trader.alpha")),
        )


def test_trader_projection_exposes_version_and_evidence_not_strategy_logic() -> None:
    trader = _trader("trader.alpha")

    assert trader.strategy_version.value == "strategy.v3"
    assert trader.kind_code == "virtual-trader.structure"
    assert not hasattr(trader, "strategy_parameters")
    assert not hasattr(trader, "entry_logic")
    assert not hasattr(trader, "broker")
    assert not hasattr(trader, "account")


def test_trader_confidence_is_strict_finite_float() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveTraderConfidence(True)  # type: ignore[arg-type]

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveTraderConfidence(1.1)


def test_trader_summary_requires_evidence_and_unique_markets() -> None:
    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveTraderSummary(
            trader_id=ExecutiveTraderId("trader.blocked"),
            kind_code="virtual-trader.structure",
            strategy_version=ExecutiveStrategyVersionRef("strategy.v3"),
            state=ExecutiveTraderState.SUSPENDED,
            authorization_state=ExecutiveTraderAuthorizationState.BLOCKED,
            confidence=None,
            judgment_code="no-action",
            market_instruments=(),
            reason_codes=("risk.blocked",),
            evidence_refs=(),
        )

    with pytest.raises(ExecutiveReadModelValidationError):
        ExecutiveTraderSummary(
            trader_id=ExecutiveTraderId("trader.duplicate-market"),
            kind_code="virtual-trader.structure",
            strategy_version=ExecutiveStrategyVersionRef("strategy.v3"),
            state=ExecutiveTraderState.ELIGIBLE,
            authorization_state=ExecutiveTraderAuthorizationState.RESTRICTED,
            confidence=ExecutiveTraderConfidence(0.5),
            judgment_code="hold",
            market_instruments=(
                ExecutiveMarketInstrument("EUR_USD"),
                ExecutiveMarketInstrument("EUR_USD"),
            ),
            reason_codes=("market.restricted",),
            evidence_refs=(ExecutiveEvidenceRef("evidence:trader/restricted"),),
        )
