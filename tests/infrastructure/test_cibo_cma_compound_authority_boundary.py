from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_account_sizing_authority import (
    CiboAccountSizingMode,
    account_capital_state,
    plan_account_sizing,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    ingest_base_settlement,
    initialize_compound_cycle,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
    build_integrated_capital_truth,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="testbroker",
        account_ref="cma-compound-boundary",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint="vt31-boundary",
        qore_symbol="NAS100",
        provider_symbol="NAS100",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("20000"),
        stop_loss=Decimal("19900"),
        take_profit=Decimal("20200"),
        stop_loss_per_volume=Decimal("10"),
        margin_per_volume=Decimal("5"),
        volume_step=Decimal("0.01"),
        minimum_volume=Decimal("0.01"),
        maximum_volume=Decimal("1"),
    )


def test_trader_envelope_has_no_sizing_or_capital_authority() -> None:
    names = {item.name for item in fields(TraderOpportunityEnvelope)}

    assert "volume" not in names
    assert "lots" not in names
    assert "risk_usd" not in names
    assert "requested_risk_usd" not in names
    assert "capital_allocation_usd" not in names


def test_cibo_alone_creates_account_scoped_size_from_trader_geometry() -> None:
    opportunity = _opportunity()
    capital = account_capital_state(
        assigned_capital_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("5"),
        margin_headroom_usd=Decimal("20"),
        survival_capital_usd=Decimal("10"),
        protected_capital_usd=Decimal("0"),
    )
    decision = plan_account_sizing(
        opportunity=opportunity,
        capital=capital,
        mission_policy=derive_cibo_capital_mission(_identity()),
        survival_capital_usd=Decimal("10"),
        protected_capital_usd=Decimal("0"),
    )

    assert decision.mode is CiboAccountSizingMode.SURVIVAL_MINIMAL_SEED
    assert decision.plan.volume == Decimal("0.01")
    assert decision.plan.stop_risk_usd == Decimal("0.10")
    assert decision.plan.margin_usd == Decimal("0.05")


def test_cma_settlement_becomes_compound_only_after_realization() -> None:
    settlement = apply_settlement(
        CmaSettlementState(
            signal_fingerprint="vt31-boundary",
            position_id=1001,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=1002,
            signal_fingerprint="vt31-boundary",
            position_id=1001,
            net_profit_usd=Decimal("10"),
            position_open_after=False,
        ),
    )
    cycle = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(("EQUITY_BETA", Decimal("10")),),
        ),
    )
    cycle = ingest_base_settlement(
        cycle,
        event_id="settled-profit",
        occurred_at=T0,
        trader_id=TraderLineage.VT31_NAS100,
        settlement=settlement,
    )
    source = (
        CapitalSourceLedger()
        .add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .add_source(
            source_id="settled-profit-source",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("10"),
        )
    )
    truth = build_integrated_capital_truth(
        account_identity=_identity(),
        source_ledger=source,
        compound_state=cycle,
        realized_profit_bindings=(
            RealizedProfitEquivalenceBinding(
                source_id="settled-profit-source",
                admission_lot_ids=("settled-profit:gen1",),
            ),
        ),
    )

    assert settlement.realized_net_pnl_usd == Decimal("10")
    assert cycle.closing_realized_capital_usd == Decimal("110")
    assert cycle.accounting_identity_usd == Decimal("110")
    assert truth.realized_profit_proven_usd == Decimal("10")
    assert truth.compound_admitted_realized_profit_usd == Decimal("10")
    assert truth.no_double_counting_pass is True
    assert truth.equivalence_residual_usd == Decimal("0")
