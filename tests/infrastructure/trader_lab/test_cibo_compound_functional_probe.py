from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_capital import CompoundCapitalState
from qore.infrastructure.cibo_compound_cycle_replay import (
    BaseSettlementEvent,
    ClassificationEvent,
    PolicyProtectFloorEvent,
    ProtectProfitEvent,
    replay_compound_cycle,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    initialize_compound_cycle,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)
from qore.infrastructure.trader_lab.candidate import TraderLabCandidateBinding

NOW = datetime(2026, 10, 3, 3, 15, tzinfo=UTC)


def _tag(candidate: TraderLabCandidateBinding, suffix: str) -> str:
    return f"trader-lab:{candidate.fingerprint.value}:{suffix}"


def _initial(candidate: TraderLabCandidateBinding):
    return initialize_compound_cycle(
        account_identity=CiboAccountCapitalIdentity(
            provider_key="trader-lab",
            account_ref=_tag(candidate, "compound-account"),
            environment=MarketRuntimeEnvironment.TEST,
        ),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("20"),
            total_margin_capacity_usd=Decimal("200"),
            concentration_limit_by_group=(
                ("EQUITY_BETA", Decimal("20")),
            ),
        ),
    )


def _settlement(
    candidate: TraderLabCandidateBinding,
    *,
    suffix: str,
    position_id: int,
    deal_id: int,
    pnl: str,
) -> CmaSettlementState:
    signal = _tag(candidate, suffix)
    state = CmaSettlementState(
        signal_fingerprint=signal,
        position_id=position_id,
    )
    return apply_settlement(
        state,
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=deal_id,
            signal_fingerprint=signal,
            position_id=position_id,
            net_profit_usd=Decimal(pnl),
            position_open_after=False,
        ),
    )


def test_trader_lab_compound_profit_protection_and_reconciliation(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=940)
    settle_id = _tag(candidate, "base-win")
    protect_id = _tag(candidate, "protect")
    policy_id = _tag(candidate, "policy")
    compoundable_id = _tag(candidate, "compoundable")

    result = replay_compound_cycle(
        initial_state=_initial(candidate),
        events=(
            BaseSettlementEvent(
                event_id=settle_id,
                occurred_at=NOW,
                trader_id=TraderLineage.VT31_NAS100,
                settlement=_settlement(
                    candidate,
                    suffix="compound-win",
                    position_id=94001,
                    deal_id=94010,
                    pnl="20",
                ),
            ),
            ProtectProfitEvent(
                event_id=protect_id,
                occurred_at=NOW + timedelta(seconds=1),
                source_lot_id=f"{settle_id}:gen1",
                amount_usd=Decimal("5"),
            ),
            PolicyProtectFloorEvent(
                event_id=policy_id,
                occurred_at=NOW + timedelta(seconds=2),
                tranche_id=f"{protect_id}:tranche",
                policy_id="TRADER_LAB_COMPOUND_FLOOR_V1",
                policy_sha256="sha256:" + "a" * 64,
            ),
            ClassificationEvent(
                event_id=compoundable_id,
                occurred_at=NOW + timedelta(seconds=3),
                source_lot_id=f"{protect_id}:remainder",
                to_state=CompoundCapitalState.COMPOUNDABLE,
                amount_usd=Decimal("15"),
            ),
        ),
    )

    assert result.event_count == 4
    assert result.chronological is True
    assert result.future_leakage_used is False
    assert result.productive_authority is False
    assert result.final_state.current_original_base_usd == Decimal("100")
    assert result.final_state.closing_realized_capital_usd == Decimal("120")
    assert result.final_state.highest_generation == 1
    assert result.reconciliation.accounting_residual_usd == 0
    assert result.reconciliation.accounting_integrity_pass is True
    assert result.reconciliation.protected_floor_usd == Decimal("5")
    assert result.reconciliation.compoundable_usd == Decimal("15")


def test_trader_lab_compound_loss_cannot_create_phantom_capital(
    candidate_factory,
) -> None:
    candidate = candidate_factory(candidate_suffix=941)
    result = replay_compound_cycle(
        initial_state=_initial(candidate),
        events=(
            BaseSettlementEvent(
                event_id=_tag(candidate, "base-loss"),
                occurred_at=NOW,
                trader_id=TraderLineage.R34_XAUUSD,
                settlement=_settlement(
                    candidate,
                    suffix="compound-loss",
                    position_id=94101,
                    deal_id=94110,
                    pnl="-12",
                ),
            ),
        ),
    )

    assert result.event_count == 1
    assert result.final_state.current_original_base_usd == Decimal("88")
    assert result.final_state.closing_realized_capital_usd == Decimal("88")
    assert result.final_state.compound_ledger.current_economic_value_usd == 0
    assert result.final_state.highest_generation == 0
    assert result.reconciliation.accounting_residual_usd == 0
    assert result.reconciliation.accounting_integrity_pass is True
