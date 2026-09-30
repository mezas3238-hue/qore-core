from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
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
    CiboIntegratedCapitalTruthError,
    RealizedProfitEquivalenceBinding,
    build_integrated_capital_truth,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 2, 15, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="integrated-capital-truth",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _compound_state():
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("EQUITY_BETA", Decimal("10")),
            ),
        ),
    )
    settlement = apply_settlement(
        CmaSettlementState(
            signal_fingerprint="profit-signal",
            position_id=901,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=902,
            signal_fingerprint="profit-signal",
            position_id=901,
            net_profit_usd=Decimal("20"),
            position_open_after=False,
        ),
    )
    return ingest_base_settlement(
        state,
        event_id="profit",
        occurred_at=T0,
        trader_id=TraderLineage.VT31_NAS100,
        settlement=settlement,
    )


def _source_ledger() -> CapitalSourceLedger:
    return (
        CapitalSourceLedger()
        .add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .add_source(
            source_id="profit-source",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
    )


def _binding() -> tuple[RealizedProfitEquivalenceBinding, ...]:
    return (
        RealizedProfitEquivalenceBinding(
            source_id="profit-source",
            admission_lot_ids=("profit:gen1",),
        ),
    )


def test_integrated_truth_prevents_realized_profit_double_counting() -> None:
    truth = build_integrated_capital_truth(
        account_identity=_identity(),
        source_ledger=_source_ledger(),
        compound_state=_compound_state(),
        realized_profit_bindings=_binding(),
    )

    assert truth.realized_profit_proven_usd == Decimal("20")
    assert truth.compound_admitted_realized_profit_usd == Decimal("20")
    assert truth.equivalence_residual_usd == Decimal("0")
    assert truth.nonconsumed_residual_usd == Decimal("0")
    assert truth.settlement_provenance_pass is True
    assert truth.admission_coverage_pass is True
    assert truth.no_double_counting_pass is True
    assert truth.fungible_cross_dimension_total_computed is False


def test_integrated_truth_requires_all_profit_sources_to_bind() -> None:
    with pytest.raises(
        CiboIntegratedCapitalTruthError,
        match="binding coverage is incomplete",
    ):
        build_integrated_capital_truth(
            account_identity=_identity(),
            source_ledger=_source_ledger(),
            compound_state=_compound_state(),
            realized_profit_bindings=(),
        )


def test_integrated_truth_rejects_amount_drift() -> None:
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .add_source(
            source_id="profit-source",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("19"),
        )
    )
    with pytest.raises(
        CiboIntegratedCapitalTruthError,
        match="amount differs from bound admissions",
    ):
        build_integrated_capital_truth(
            account_identity=_identity(),
            source_ledger=ledger,
            compound_state=_compound_state(),
            realized_profit_bindings=_binding(),
        )


def test_integrated_truth_rejects_duplicate_admission_binding() -> None:
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id="profit-a",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("10"),
        )
        .add_source(
            source_id="profit-b",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("10"),
        )
    )
    bindings = (
        RealizedProfitEquivalenceBinding(
            source_id="profit-a",
            admission_lot_ids=("profit:gen1",),
        ),
        RealizedProfitEquivalenceBinding(
            source_id="profit-b",
            admission_lot_ids=("profit:gen1",),
        ),
    )
    with pytest.raises(
        CiboIntegratedCapitalTruthError,
        match="cannot bind to multiple profit sources",
    ):
        build_integrated_capital_truth(
            account_identity=_identity(),
            source_ledger=ledger,
            compound_state=_compound_state(),
            realized_profit_bindings=bindings,
        )


def test_integrated_truth_refuses_unbound_protected_profit_source() -> None:
    ledger = _source_ledger().add_source(
        source_id="protected-profit",
        source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
        proven_amount_usd=Decimal("5"),
    )
    with pytest.raises(
        CiboIntegratedCapitalTruthError,
        match="requires explicit lineage",
    ):
        build_integrated_capital_truth(
            account_identity=_identity(),
            source_ledger=ledger,
            compound_state=_compound_state(),
            realized_profit_bindings=_binding(),
        )


def test_integrated_truth_detects_source_consumption_drift() -> None:
    ledger = (
        _source_ledger()
        .reserve(
            reservation_id="profit-use",
            source_id="profit-source",
            amount_usd=Decimal("5"),
        )
        .deploy("profit-use")
        .settle_deployment(
            "profit-use",
            returned_capacity_usd=Decimal("0"),
        )
    )
    with pytest.raises(
        CiboIntegratedCapitalTruthError,
        match="nonconsumed profit diverge",
    ):
        build_integrated_capital_truth(
            account_identity=_identity(),
            source_ledger=ledger,
            compound_state=_compound_state(),
            realized_profit_bindings=_binding(),
        )
