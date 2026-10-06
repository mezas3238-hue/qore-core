from datetime import UTC, datetime, timedelta
from decimal import Decimal

import qore.infrastructure.cibo_single_account_historical_ceiling_epoch as module
from qore.infrastructure.account_wide_risk import (
    AccountWideRiskEngine,
    TraderLineage,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingOpportunityEvidence,
)
from qore.infrastructure.cibo_single_account_historical_capital_ledger import (
    CiboHistoricalProfitGeneration,
    CiboHistoricalResearchCapitalState,
)
from qore.infrastructure.cibo_single_account_historical_ceiling_epoch import (
    CiboHistoricalProviderAssumption,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_executor import (
    CiboSovereignCeilingEpochResult,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="historical-research",
        account_ref="ceiling-usd60",
        environment=MarketRuntimeEnvironment.DEMO,
    )


def _opportunity() -> CiboCeilingOpportunityEvidence:
    envelope = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="alpha",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("103"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("20"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("10"),
    )
    return CiboCeilingOpportunityEvidence(
        opportunity=envelope,
        expected_net_value_usd=Decimal("1"),
        expected_capital_minutes=Decimal("30"),
        provider_cost_per_volume_usd=Decimal("0.1"),
        expectation_evidence_sha256="sha256:" + "a" * 64,
    )


def _regime() -> CiboCapitalRegimeState:
    return CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0"),
        margin_utilization=Decimal("0"),
        drawdown_utilization=Decimal("0"),
        opportunity_count=1,
    )


def test_historical_epoch_uses_current_compounded_equity(monkeypatch) -> None:
    identity = _identity()
    state = CiboHistoricalResearchCapitalState(
        original_base_consumed_usd=Decimal("2"),
        profit_generations=(
            CiboHistoricalProfitGeneration(
                generation=1,
                proven_usd=Decimal("20"),
            ),
        ),
        peak_realized_capital_usd=Decimal("78"),
    )
    seen = {}

    def _fake_execute(**kwargs):
        seen.update(kwargs)
        return CiboSovereignCeilingEpochResult(
            decision_epoch_id=kwargs["decision_epoch_id"],
            decision_receipts=(),
            native_decisions=(),
            risk_authorizations=(),
            risk_submission_order=(),
        )

    monkeypatch.setattr(
        module,
        "execute_sovereign_ceiling_epoch",
        _fake_execute,
    )

    prepared = module.run_predecision_historical_sovereign_ceiling_epoch(
        decision_epoch_id="epoch-1",
        decision_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        account_identity=identity,
        historical_capital=state,
        open_exposures=(),
        opportunities=(_opportunity(),),
        regime_state=_regime(),
        evidence_ref=CiboEvidenceRef("cibo:historical-ceiling:test"),
        mission_policy=derive_cibo_capital_mission(identity),
        risk_engine=AccountWideRiskEngine(),
        provider_assumption=CiboHistoricalProviderAssumption(),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
    )

    assert prepared.risk_snapshot.equity == Decimal("78")
    assert prepared.risk_snapshot.qore_authorizable_headroom == Decimal("54.60")
    assert prepared.risk_snapshot.free_margin == Decimal("7800")
    assert prepared.epoch_state.capital.assigned_capital_usd == Decimal("78")
    assert seen["capital"].assigned_capital_usd == Decimal("78")
    assert seen["twin"].capital_twin.total_stop_risk_capacity_usd == Decimal(
        "54.60"
    )
    assert seen["capital"].hard_risk_headroom_usd == Decimal("54.60")
    assert seen["option_id_by_signal"] == (("alpha", "alpha"),)
    assert seen["twin"].opportunities[0].option_id == "alpha"
    assert seen["twin"].future_outcome_used is False
    assert seen["risk_snapshot"] == prepared.risk_snapshot


def test_provider_assumption_is_explicit_and_not_observed_history(
    monkeypatch,
) -> None:
    identity = _identity()
    seen = {}

    def _fake_execute(**kwargs):
        seen.update(kwargs)
        return CiboSovereignCeilingEpochResult(
            decision_epoch_id=kwargs["decision_epoch_id"],
            decision_receipts=(),
            native_decisions=(),
            risk_authorizations=(),
            risk_submission_order=(),
        )

    monkeypatch.setattr(
        module,
        "execute_sovereign_ceiling_epoch",
        _fake_execute,
    )

    module.run_predecision_historical_sovereign_ceiling_epoch(
        decision_epoch_id="epoch-2",
        decision_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        account_identity=identity,
        historical_capital=CiboHistoricalResearchCapitalState(),
        open_exposures=(),
        opportunities=(_opportunity(),),
        regime_state=_regime(),
        evidence_ref=CiboEvidenceRef("cibo:historical-ceiling:test"),
        mission_policy=derive_cibo_capital_mission(identity),
        risk_engine=AccountWideRiskEngine(),
        provider_assumption=CiboHistoricalProviderAssumption(
            risk_headroom_multiple_of_equity=Decimal("0.5"),
            max_risk_multiple_of_equity=Decimal("0.25"),
            margin_capacity_multiple_of_equity=Decimal("20"),
        ),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
    )

    snapshot = seen["risk_snapshot"]
    assert snapshot.provider_budget.provider_headroom == Decimal("30.0")
    assert snapshot.provider_budget.max_risk_at_any_time == Decimal("15.00")
    assert snapshot.free_margin == Decimal("1200")
    assert snapshot.qore_authorizable_headroom == Decimal("15.00")
    assert seen["twin"].capital_twin.total_stop_risk_capacity_usd == Decimal(
        "15.00"
    )
    assert seen["twin"].capital_twin.stop_risk_headroom_usd == Decimal(
        "15.00"
    )
    assert seen["capital"].hard_risk_headroom_usd == Decimal("15.00")
