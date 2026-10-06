from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import CapitalSource
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    VersionedCapitalSourceLedger,
)
from qore.infrastructure.cibo_ce2i_portfolio_allocation_ledger import (
    PortfolioAllocationLedger,
)
from qore.infrastructure.cibo_cma_settlement_ledger import (
    CmaSettlementRecord,
    CmaSettlementState,
    apply_settlement,
)
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_cycle_replay import (
    BaseSettlementEvent,
    ClassificationEvent,
    PolicyProtectFloorEvent,
    ProtectProfitEvent,
    replay_compound_cycle,
    replay_compound_cycle_with_capital_truth,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    initialize_compound_cycle,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 2, 0, tzinfo=UTC)


def _initial():
    return initialize_compound_cycle(
        account_identity=CiboAccountCapitalIdentity(
            provider_key="ctrader",
            account_ref="compound-replay-test",
            environment=MarketRuntimeEnvironment.TEST,
        ),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(
                ("EQUITY_BETA", Decimal("10")),
            ),
        ),
    )


def _settlement(
    *,
    signal: str = "replay-profit",
    position_id: int = 7001,
    deal_id: int = 8001,
    pnl: str = "20",
) -> CmaSettlementState:
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


def test_compound_cycle_runner_is_chronological_and_reconciled() -> None:
    events = (
        BaseSettlementEvent(
            event_id="settle",
            occurred_at=T0,
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(),
        ),
        ProtectProfitEvent(
            event_id="protect",
            occurred_at=T0 + timedelta(seconds=1),
            source_lot_id="settle:gen1",
            amount_usd=Decimal("5"),
        ),
        PolicyProtectFloorEvent(
            event_id="policy",
            occurred_at=T0 + timedelta(seconds=2),
            tranche_id="protect:tranche",
            policy_id="REPLAY_FLOOR_V1",
            policy_sha256="sha256:" + "a" * 64,
        ),
        ClassificationEvent(
            event_id="compoundable",
            occurred_at=T0 + timedelta(seconds=3),
            source_lot_id="protect:remainder",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("15"),
        ),
    )

    result = replay_compound_cycle(
        initial_state=_initial(),
        events=events,
    )

    assert result.event_count == 4
    assert result.chronological is True
    assert result.future_leakage_used is False
    assert result.productive_authority is False
    assert result.final_state.closing_realized_capital_usd == Decimal("120")
    assert result.reconciliation.accounting_residual_usd == Decimal("0")
    assert result.reconciliation.accounting_integrity_pass is True
    assert result.reconciliation.protected_floor_usd == Decimal("5")
    assert result.reconciliation.compoundable_usd == Decimal("15")
    assert result.reconciliation.certification_ready is False


def test_genc1_end_to_end_mathematical_reconciliation_replay() -> None:
    events = (
        BaseSettlementEvent(
            event_id="genc1-profit",
            occurred_at=T0,
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(
                signal="genc1-profit",
                position_id=7101,
                deal_id=8101,
                pnl="20",
            ),
        ),
        ProtectProfitEvent(
            event_id="genc1-protect",
            occurred_at=T0 + timedelta(seconds=1),
            source_lot_id="genc1-profit:gen1",
            amount_usd=Decimal("5"),
        ),
        ClassificationEvent(
            event_id="genc1-compoundable",
            occurred_at=T0 + timedelta(seconds=2),
            source_lot_id="genc1-protect:remainder",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("15"),
        ),
        BaseSettlementEvent(
            event_id="genc1-loss",
            occurred_at=T0 + timedelta(seconds=3),
            trader_id=TraderLineage.R34_XAUUSD,
            settlement=_settlement(
                signal="genc1-loss",
                position_id=7102,
                deal_id=8102,
                pnl="-7",
            ),
        ),
    )

    result = replay_compound_cycle(
        initial_state=_initial(),
        events=events,
    )
    audit = result.reconciliation

    assert result.chronological is True
    assert result.future_leakage_used is False
    assert audit.opening_original_base_usd == Decimal("100")
    assert audit.current_original_base_usd == Decimal("93")
    assert audit.admitted_realized_profit_usd == Decimal("20")
    assert audit.cumulative_realized_gains_usd == Decimal("20")
    assert audit.cumulative_realized_losses_usd == Decimal("7")
    assert audit.consumed_compound_capital_usd == Decimal("0")
    assert audit.base_capital_loss_usd == Decimal("7")
    assert audit.closing_realized_capital_usd == Decimal("113")
    assert audit.accounting_identity_usd == Decimal("113")
    assert audit.accounting_residual_usd == Decimal("0")
    assert audit.protected_floor_usd == Decimal("5")
    assert audit.compoundable_usd == Decimal("15")
    assert audit.accounting_integrity_pass is True
    assert audit.provenance_pass is True
    assert audit.no_double_counting_pass is True
    assert audit.no_unexplained_creation_pass is True
    assert audit.no_unexplained_destruction_pass is True
    assert audit.path_dependence_mechanics_pass is True
    assert audit.economic_value_demonstrated is False
    assert audit.certification_ready is False


def test_compound_cycle_runner_rejects_reversed_input() -> None:
    events = (
        BaseSettlementEvent(
            event_id="late",
            occurred_at=T0 + timedelta(seconds=2),
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(),
        ),
        ClassificationEvent(
            event_id="early",
            occurred_at=T0 + timedelta(seconds=1),
            source_lot_id="late:gen1",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("20"),
        ),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="input chronology is reversed",
    ):
        replay_compound_cycle(
            initial_state=_initial(),
            events=events,
        )


def test_compound_cycle_runner_binds_persisted_source_truth() -> None:
    events = (
        BaseSettlementEvent(
            event_id="settle-truth",
            occurred_at=T0,
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(),
        ),
        ClassificationEvent(
            event_id="compoundable-truth",
            occurred_at=T0 + timedelta(seconds=1),
            source_lot_id="settle-truth:gen1",
            to_state=CompoundCapitalState.COMPOUNDABLE,
            amount_usd=Decimal("20"),
        ),
    )
    source = (
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

    result = replay_compound_cycle_with_capital_truth(
        initial_state=_initial(),
        events=events,
        source_ledger_version=VersionedCapitalSourceLedger(
            generation=1,
            ledger=source,
        ),
        source_ledger_observed_at=T0 + timedelta(seconds=1),
        realized_profit_bindings=(
            RealizedProfitEquivalenceBinding(
                source_id="profit-source",
                admission_lot_ids=("settle-truth:gen1",),
            ),
        ),
    )

    assert result.source_ledger_generation == 1
    assert result.capital_truth.no_double_counting_pass is True
    assert result.capital_truth.realized_profit_proven_usd == Decimal("20")
    assert result.cycle.reconciliation.accounting_residual_usd == Decimal("0")
    assert result.productive_authority is False


def test_integrated_runner_rejects_stale_source_snapshot() -> None:
    events = (
        BaseSettlementEvent(
            event_id="settle-stale",
            occurred_at=T0,
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(),
        ),
    )
    source = CapitalSourceLedger().add_source(
        source_id="profit-source",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("20"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="predates final compound event",
    ):
        replay_compound_cycle_with_capital_truth(
            initial_state=_initial(),
            events=events,
            source_ledger_version=VersionedCapitalSourceLedger(
                generation=1,
                ledger=source,
            ),
            source_ledger_observed_at=T0 - timedelta(seconds=1),
            realized_profit_bindings=(
                RealizedProfitEquivalenceBinding(
                    source_id="profit-source",
                    admission_lot_ids=("settle-stale:gen1",),
                ),
            ),
        )


def test_integrated_runner_requires_persisted_source_generation() -> None:
    events = (
        BaseSettlementEvent(
            event_id="settle-generation",
            occurred_at=T0,
            trader_id=TraderLineage.VT31_NAS100,
            settlement=_settlement(),
        ),
    )
    source = CapitalSourceLedger().add_source(
        source_id="profit-source",
        source=CapitalSource.REALIZED_PROFIT,
        proven_amount_usd=Decimal("20"),
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="must be durably persisted",
    ):
        replay_compound_cycle_with_capital_truth(
            initial_state=_initial(),
            events=events,
            source_ledger_version=VersionedCapitalSourceLedger(
                generation=0,
                ledger=source,
            ),
            source_ledger_observed_at=T0,
            realized_profit_bindings=(
                RealizedProfitEquivalenceBinding(
                    source_id="profit-source",
                    admission_lot_ids=("settle-generation:gen1",),
                ),
            ),
        )
