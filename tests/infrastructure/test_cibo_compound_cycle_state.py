from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

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
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    CompoundCycleDeployment,
    CompoundCycleMarketRecord,
    CompoundCycleSettlementRecord,
    classify_compound_capital,
    ingest_base_settlement,
    initialize_compound_cycle,
    policy_protect_floor,
    protect_compound_capital,
)
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 1, 15, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="compound-cycle-test",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _t19() -> PortfolioAllocationLedger:
    return PortfolioAllocationLedger(
        total_stop_risk_capacity_usd=Decimal("20"),
        total_margin_capacity_usd=Decimal("200"),
        concentration_limit_by_group=(
            ("EQUITY_BETA", Decimal("20")),
        ),
    )


def _settlement(
    *,
    signal: str,
    position_id: int,
    deal_id: int,
    pnl: str,
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


def test_compound_cycle_base_profit_is_gen1_and_reconciles() -> None:
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=_t19(),
    )
    state = ingest_base_settlement(
        state,
        event_id="base-win",
        occurred_at=T0,
        trader_id=TraderLineage.VT31_NAS100,
        settlement=_settlement(
            signal="vt31-win",
            position_id=101,
            deal_id=201,
            pnl="20",
        ),
    )

    assert state.current_original_base_usd == Decimal("100")
    assert state.cumulative_realized_gains_usd == Decimal("20")
    assert state.cumulative_realized_losses_usd == Decimal("0")
    assert state.closing_realized_capital_usd == Decimal("120")
    assert state.accounting_identity_usd == Decimal("120")
    assert state.original_capital_dependence_ratio == Decimal("100") / Decimal(
        "120"
    )

    lot = state.compound_ledger.lot("base-win:gen1")
    assert lot.generation == 1
    assert lot.origin_trader is TraderLineage.VT31_NAS100
    assert lot.state is CompoundCapitalState.REALIZED_PROFIT


def test_compound_cycle_protection_and_classification_are_explicit() -> None:
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=_t19(),
    )
    state = ingest_base_settlement(
        state,
        event_id="base-win",
        occurred_at=T0,
        trader_id=TraderLineage.VT31_NAS100,
        settlement=_settlement(
            signal="vt31-win",
            position_id=101,
            deal_id=201,
            pnl="20",
        ),
    )
    state = protect_compound_capital(
        state,
        event_id="protect",
        occurred_at=T0 + timedelta(seconds=1),
        source_lot_id="base-win:gen1",
        amount_usd=Decimal("5"),
    )
    state = policy_protect_floor(
        state,
        event_id="policy-protect",
        occurred_at=T0 + timedelta(seconds=2),
        tranche_id="protect:tranche",
        policy_id="COMPOUND_CYCLE_TEST_POLICY",
        policy_sha256="sha256:" + "a" * 64,
    )
    state = classify_compound_capital(
        state,
        event_id="compoundable",
        occurred_at=T0 + timedelta(seconds=3),
        source_lot_id="protect:remainder",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("15"),
    )
    state = classify_compound_capital(
        state,
        event_id="activate",
        occurred_at=T0 + timedelta(seconds=4),
        source_lot_id="compoundable:moved",
        to_state=CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY,
        amount_usd=Decimal("15"),
    )

    assert state.floor_ledger.total_floor_usd == Decimal("5")
    assert state.floor_ledger.policy_protected_floor_usd == Decimal("5")
    assert state.compound_ledger.balance(
        CompoundCapitalState.ACTIVE_COMPOUND_CAPACITY
    ) == Decimal("15")
    assert state.closing_realized_capital_usd == Decimal("120")
    assert state.accounting_identity_usd == Decimal("120")


def test_compound_cycle_base_loss_reduces_gen0_without_phantom_capital() -> None:
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=_t19(),
    )
    state = ingest_base_settlement(
        state,
        event_id="base-loss",
        occurred_at=T0,
        trader_id=TraderLineage.R34_XAUUSD,
        settlement=_settlement(
            signal="r34-loss",
            position_id=102,
            deal_id=202,
            pnl="-12",
        ),
    )

    assert state.current_original_base_usd == Decimal("88")
    assert state.compound_ledger.current_economic_value_usd == Decimal("0")
    assert state.cumulative_realized_losses_usd == Decimal("12")
    assert state.closing_realized_capital_usd == Decimal("88")
    assert state.accounting_identity_usd == Decimal("88")
    assert state.highest_generation == 0


def test_compound_cycle_cannot_reuse_same_settlement_evidence() -> None:
    settlement = _settlement(
        signal="duplicate",
        position_id=103,
        deal_id=203,
        pnl="10",
    )
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=_t19(),
    )
    state = ingest_base_settlement(
        state,
        event_id="first",
        occurred_at=T0,
        trader_id=TraderLineage.VT31_NAS100,
        settlement=settlement,
    )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="settlement evidence already consumed",
    ):
        ingest_base_settlement(
            state,
            event_id="second",
            occurred_at=T0 + timedelta(seconds=1),
            trader_id=TraderLineage.VT31_NAS100,
            settlement=settlement,
        )


def test_compound_cycle_rejects_noncanonical_provenance_hashes() -> None:
    invalid = "sha256:" + "z" * 64

    with pytest.raises(
        CiboCompoundCapitalError,
        match="settlement digest must be canonical SHA-256",
    ):
        CompoundCycleSettlementRecord(
            event_id="bad-settlement",
            occurred_at=T0,
            source_kind="BASE_CAPITAL",
            trader_id=TraderLineage.VT31_NAS100,
            signal_fingerprint="signal-bad",
            position_id=1,
            settlement_sha256=invalid,
            realized_net_pnl_usd=Decimal("1"),
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="market portfolio_state_sha256 must be canonical SHA-256",
    ):
        CompoundCycleMarketRecord(
            event_id="bad-market",
            occurred_at=T0,
            decision_id="decision-bad",
            action="RESERVE_NO_DEPLOYMENT",
            candidate_id=None,
            amount_usd=Decimal("0"),
            scarcity_event_id="scarcity-bad",
            portfolio_state_sha256=invalid,
            t19_ledger_sha256="sha256:" + "a" * 64,
        )

    with pytest.raises(
        CiboCompoundCapitalError,
        match="deployment settlement digest must be canonical SHA-256",
    ):
        CompoundCycleDeployment(
            deployment_id="bad-deployment",
            market_event_id="bad-market",
            decision_id="decision-bad",
            candidate_id="candidate-bad",
            deployed_at=T0,
            trader_id=TraderLineage.VT31_NAS100,
            signal_fingerprint="signal-bad",
            source_lot_id="source-lot",
            deployed_lot_id="deployed-lot",
            amount_usd=Decimal("1"),
            source_generation=1,
            stop_risk_usd=Decimal("0.1"),
            margin_usd=Decimal("1"),
            settled=True,
            settlement_sha256=invalid,
        )
