from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import qore.infrastructure.cibo_single_account_sovereign_ceiling_epoch as epoch_module
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
    initialize_ceiling_account_state,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_executor import (
    CiboSovereignCeilingEpochResult,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class _Budget:
    provider_headroom: Decimal = Decimal("60")
    max_risk_at_any_time: Decimal = Decimal("60")
    active_mll: Decimal = Decimal("0")
    hard_breach: bool = False


def _opportunity(
    signal: str,
    trader: TraderLineage,
    symbol: str,
) -> CiboCeilingOpportunityEvidence:
    envelope = TraderOpportunityEnvelope(
        trader_id=trader,
        signal_fingerprint=signal,
        qore_symbol=symbol,
        provider_symbol=symbol,
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
        expectation_evidence_sha256="sha256:" + signal[0] * 64,
    )


def test_predecision_epoch_binds_full_surface_state_risk_and_executor(
    monkeypatch,
) -> None:
    identity = CiboAccountCapitalIdentity(
        provider_key="ctrader-research",
        account_ref="ceiling-account",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    account = initialize_ceiling_account_state(account_identity=identity)
    rows = (
        _opportunity("alpha", TraderLineage.R34_XAUUSD, "XAUUSD"),
        _opportunity("beta", TraderLineage.R38_EURUSD, "EURUSD"),
    )
    regime = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0"),
        margin_utilization=Decimal("0"),
        drawdown_utilization=Decimal("0"),
        opportunity_count=2,
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
        epoch_module,
        "execute_sovereign_ceiling_epoch",
        _fake_execute,
    )

    prepared = epoch_module.run_predecision_sovereign_ceiling_epoch(
        decision_epoch_id="epoch-1",
        decision_at=NOW,
        expires_at=NOW + timedelta(minutes=1),
        account=account,
        opportunities=rows,
        regime_state=regime,
        evidence_ref=CiboEvidenceRef("cibo:ceiling:test"),
        mission_policy=derive_cibo_capital_mission(identity),
        risk_engine=AccountWideRiskEngine(),
        provider_budget=_Budget(),
        provider_free_margin_usd=Decimal("60"),
        open_floating_loss_usd=Decimal("0"),
        pending_broker_worst_case_loss_usd=Decimal("0"),
        qore_authorizable_headroom_usd=Decimal("60"),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
    )

    expected_envelopes = tuple(item.opportunity for item in rows)
    assert seen["opportunities"] == expected_envelopes
    assert seen["twin"] == prepared.epoch_state.twin
    assert seen["capital"] == prepared.epoch_state.capital
    assert seen["risk_snapshot"] == prepared.risk_snapshot
    assert seen["option_id_by_signal"] == (
        ("alpha", "ceiling:alpha"),
        ("beta", "ceiling:beta"),
    )
    assert prepared.risk_snapshot.equity == Decimal("60")
    assert prepared.epoch_state.twin.future_outcome_used is False
