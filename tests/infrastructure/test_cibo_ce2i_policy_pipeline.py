from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CapitalStage,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_capital_source_ledger import CapitalSourceLedger
from qore.infrastructure.cibo_capital_source_ledger_store import (
    DurableCapitalSourceLedgerStore,
)
from qore.infrastructure.cibo_cma_capital_observation import CmaCapitalObservation
from qore.infrastructure.cibo_ce2i_execution_efficiency import (
    ExecutionCostCurveInput,
)
from qore.infrastructure.cibo_ce2i_policy_pipeline import propose_ce2i_expansion


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD,
        signal_fingerprint="signal-1",
        qore_symbol="EURUSD",
        provider_symbol="EURUSD",
        side="long",
        entry_type="MARKET",
        intended_entry=Decimal("1.10"),
        stop_loss=Decimal("1.09"),
        take_profit=Decimal("1.12"),
        stop_loss_per_volume=Decimal("2"),
        margin_per_volume=Decimal("3"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("10"),
    )


def _observation(
    *,
    realized: str = "20",
    protected: str = "20",
    capacity: str = "20",
    eligible: bool = True,
) -> CmaCapitalObservation:
    return CmaCapitalObservation(
        event="CIBO_CMA_CAPITAL_OBSERVATION",
        trader=TraderLineage.R38_EURUSD.value,
        symbol="EURUSD",
        signal_fingerprint="signal-1",
        position_id=101,
        stage=CapitalStage.CAPITALIZE if eligible else CapitalStage.PROTECT_BASE,
        evidence_sufficient=eligible,
        expansion_eligible=eligible,
        realized_net_pnl_usd=Decimal(realized),
        remaining_stop_worst_case_pnl_usd=Decimal("0"),
        net_economic_floor_usd=Decimal(capacity) if eligible else Decimal("-1"),
        base_capital_at_risk_usd=Decimal("0") if eligible else Decimal("1"),
        protected_open_floor_usd=Decimal(protected),
        self_financing_capacity_usd=Decimal(capacity) if eligible else Decimal("0"),
        reason="test",
    )


def _curve(*, impact: str = "1", gross: str = "10") -> ExecutionCostCurveInput:
    return ExecutionCostCurveInput(
        evidence_id="curve-1",
        volume_step=Decimal("1"),
        maximum_volume=Decimal("10"),
        gross_edge_per_volume_usd=Decimal(gross),
        spread_cost_per_volume_usd=Decimal("1"),
        commission_cost_per_volume_usd=Decimal("1"),
        slippage_cost_per_volume_usd=Decimal("0"),
        impact_cost_per_volume_squared_usd=Decimal(impact),
    )


def _store(
    tmp_path: Path,
    *,
    realized_amount: str = "20",
    protected_amount: str = "20",
) -> DurableCapitalSourceLedgerStore:
    store = DurableCapitalSourceLedgerStore(tmp_path / "pipeline-ledger.json")
    ledger = (
        CapitalSourceLedger()
        .add_source(
            source_id="realized-1",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal(realized_amount),
        )
        .add_source(
            source_id="protected-1",
            source=CapitalSource.PROTECTED_ECONOMIC_FLOOR,
            proven_amount_usd=Decimal(protected_amount),
        )
    )
    store.store(ledger, expected_generation=0)
    return store


def _propose(
    tmp_path: Path,
    *,
    observation: CmaCapitalObservation | None = None,
    curve: ExecutionCostCurveInput | None = None,
    realized_amount: str = "20",
    protected_amount: str = "20",
):
    store = _store(
        tmp_path,
        realized_amount=realized_amount,
        protected_amount=protected_amount,
    )
    decision = propose_ce2i_expansion(
        reservation_id="policy-r1",
        request_id="policy-risk-1",
        opportunity=_opportunity(),
        observation=observation or _observation(),
        execution_curve=curve or _curve(),
        assigned_capital_usd=Decimal("10000"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("100"),
        requested_at=NOW,
        expires_at=NOW + timedelta(seconds=30),
        ledger_store=store,
    )
    return store, decision


def test_pipeline_applies_execution_cap_before_reservation(tmp_path: Path) -> None:
    store, decision = _propose(tmp_path)

    assert decision.applied_tools == ("T11", "T06", "T19")
    assert decision.execution_cap.volume_cap == Decimal("4")
    assert decision.proposal is not None
    assert decision.proposal.plan.volume == Decimal("4")
    assert decision.proposal.plan.stop_risk_usd == Decimal("8")
    realized = next(
        account
        for account in store.load().ledger.accounts
        if account.source_id == "realized-1"
    )
    assert realized.reserved_usd == Decimal("8")


def test_realized_profit_has_conservative_priority_over_protected_floor(
    tmp_path: Path,
) -> None:
    _, decision = _propose(tmp_path)

    assert decision.proposal is not None
    assert decision.proposal.source is CapitalSource.REALIZED_PROFIT


def test_protected_floor_is_fallback_when_realized_lot_cannot_express_minimum(
    tmp_path: Path,
) -> None:
    _, decision = _propose(
        tmp_path,
        realized_amount="1",
        protected_amount="20",
        observation=_observation(realized="1", protected="20", capacity="20"),
    )

    assert decision.applied_tools == ("T11", "T07", "T19")
    assert decision.proposal is not None
    assert decision.proposal.source is CapitalSource.PROTECTED_ECONOMIC_FLOOR


def test_execution_rejection_creates_no_reservation(tmp_path: Path) -> None:
    store, decision = _propose(
        tmp_path,
        curve=_curve(gross="1"),
    )

    assert decision.applied_tools == ("T11",)
    assert decision.proposal is None
    assert store.load().ledger.reservations == ()


def test_ineligible_capital_observation_creates_no_reservation(
    tmp_path: Path,
) -> None:
    store, decision = _propose(
        tmp_path,
        observation=_observation(eligible=False),
    )

    assert decision.proposal is None
    assert decision.applied_tools == ("T11",)
    assert store.load().ledger.reservations == ()


def test_no_single_source_above_provider_minimum_holds_without_double_spend(
    tmp_path: Path,
) -> None:
    store, decision = _propose(
        tmp_path,
        realized_amount="1",
        protected_amount="1",
        observation=_observation(realized="1", protected="1", capacity="2"),
    )

    assert decision.proposal is None
    assert "multi-source" in decision.reason
    assert store.load().ledger.reservations == ()
