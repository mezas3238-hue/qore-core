from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    Genc10KnownCapitalOption,
    build_genc10_observed_twin,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalSource,
    CiboCapitalManagementError,
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
from qore.infrastructure.cibo_compound_capital import CompoundCapitalState
from qore.infrastructure.cibo_compound_cycle_state import (
    classify_compound_capital,
    ingest_base_settlement,
    initialize_compound_cycle,
    policy_protect_floor,
    protect_compound_capital,
)
from qore.infrastructure.cibo_full_economic_digital_twin import (
    CiboCapitalVelocityState,
    CiboCounterfactualEconomicWorld,
    CiboIdleCapitalClass,
    CiboObservedEconomicTwin,
    CiboObservedOpportunityState,
    CiboObservedPortfolioState,
    CiboObservedPositionState,
    observed_twin_constraints,
)
from qore.infrastructure.cibo_instrument_capability_registry import (
    CapabilityStatus,
    InstrumentCapability,
    ProviderCapabilityEvidence,
    ProviderInstrumentCapabilityRegistry,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    RealizedProfitEquivalenceBinding,
    build_integrated_capital_truth,
)
from qore.infrastructure.cibo_portfolio_allocation_engine import (
    plan_account_wide_capital_allocation,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="full-economic-twin",
        environment=MarketRuntimeEnvironment.TEST,
    )


def _source() -> CapitalSourceLedger:
    return (
        CapitalSourceLedger()
        .add_source(
            source_id="gen0",
            source=CapitalSource.ORIGINAL_BASE_CAPITAL,
            proven_amount_usd=Decimal("100"),
        )
        .add_source(
            source_id="profit",
            source=CapitalSource.REALIZED_PROFIT,
            proven_amount_usd=Decimal("20"),
        )
    )


def _capital_twin():
    state = initialize_compound_cycle(
        account_identity=_identity(),
        opening_original_base_usd=Decimal("100"),
        t19_ledger=PortfolioAllocationLedger(
            total_stop_risk_capacity_usd=Decimal("10"),
            total_margin_capacity_usd=Decimal("100"),
            concentration_limit_by_group=(("EQUITY_BETA", Decimal("10")),),
        ),
    )
    settlement = apply_settlement(
        CmaSettlementState(
            signal_fingerprint="origin-profit",
            position_id=1001,
        ),
        CmaSettlementRecord(
            event="CTRADER_DEMO_EXIT_SETTLEMENT",
            deal_id=2001,
            signal_fingerprint="origin-profit",
            position_id=1001,
            net_profit_usd=Decimal("20"),
            position_open_after=False,
        ),
    )
    state = ingest_base_settlement(
        state,
        event_id="origin",
        occurred_at=T0 - timedelta(minutes=5),
        trader_id=TraderLineage.VT31_NAS100,
        settlement=settlement,
    )
    state = protect_compound_capital(
        state,
        event_id="protect",
        occurred_at=T0 - timedelta(minutes=4),
        source_lot_id="origin:gen1",
        amount_usd=Decimal("5"),
    )
    state = policy_protect_floor(
        state,
        event_id="policy",
        occurred_at=T0 - timedelta(minutes=3),
        tranche_id="protect:tranche",
        policy_id="FULL_TWIN_TEST_FLOOR",
        policy_sha256="sha256:" + "a" * 64,
    )
    state = classify_compound_capital(
        state,
        event_id="compoundable",
        occurred_at=T0 - timedelta(minutes=2),
        source_lot_id="protect:remainder",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("15"),
    )
    truth = build_integrated_capital_truth(
        account_identity=_identity(),
        source_ledger=_source(),
        compound_state=state,
        realized_profit_bindings=(
            RealizedProfitEquivalenceBinding(
                source_id="profit",
                admission_lot_ids=("origin:gen1",),
            ),
        ),
    )
    registry = ProviderInstrumentCapabilityRegistry(
        account_identity=_identity(),
        entries=(
            ProviderCapabilityEvidence(
                evidence_id="cfd",
                account_identity=_identity(),
                capability=InstrumentCapability.CFD,
                status=CapabilityStatus.SUPPORTED,
                observed_at=T0 - timedelta(hours=1),
                produced_at=T0 - timedelta(minutes=50),
                source="PROVIDER_NORMALIZATION",
                source_ref="provider://cfd",
                evidence_sha256="sha256:" + "b" * 64,
                policy_version="PROVIDER_CAPABILITY_V1",
                provider_verified=True,
            ),
        ),
        captured_at=T0 - timedelta(minutes=1),
    )
    option = Genc10KnownCapitalOption(
        option_id="known-r34",
        known_at=T0 - timedelta(minutes=1),
        earliest_action_at=T0 + timedelta(minutes=1),
        expires_at=T0 + timedelta(minutes=20),
        requested_capital_usd=Decimal("5"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        evidence_sha256="sha256:" + "d" * 64,
    )
    return build_genc10_observed_twin(
        twin_id="capital-twin",
        captured_at=T0,
        compound_state=state,
        capital_truth=truth,
        source_ledger=_source(),
        provider_registry=registry,
        known_options=(option,),
    )


def _opportunity(*, known_at: datetime = T0) -> CiboObservedOpportunityState:
    return CiboObservedOpportunityState(
        option_id="known-r34",
        trader_id="R34_XAUUSD",
        qore_symbol="XAUUSD",
        known_at=known_at,
        earliest_action_at=max(known_at, T0),
        expires_at=max(known_at, T0) + timedelta(minutes=20),
        requested_capital_usd=Decimal("5"),
        expected_net_value_usd=Decimal("0.40"),
        expected_capital_minutes=Decimal("20"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        provider_cost_usd=Decimal("0.05"),
        uncertainty_penalty=Decimal("0.10"),
        context_allowed=True,
        provider_viable=True,
        capital_source_eligible=True,
        evidence_sha256="sha256:" + "e" * 64,
    )


def _full_twin() -> CiboObservedEconomicTwin:
    capital = _capital_twin()
    opportunity = _opportunity()
    portfolio = CiboObservedPortfolioState(
        observed_at=T0,
        active_position_ids=(),
        opportunity_ids=(opportunity.option_id,),
        concentration_utilization=Decimal("0.10"),
        correlation_utilization=Decimal("0.10"),
        reserved_stop_risk_usd=Decimal("1"),
        reserved_margin_usd=Decimal("2"),
    )
    velocity = CiboCapitalVelocityState(
        observed_at=T0,
        released_stop_risk_usd=Decimal("0"),
        released_margin_usd=Decimal("0"),
        waiting_stop_risk_usd=Decimal("0"),
        waiting_margin_usd=Decimal("0"),
        oldest_release_age_minutes=Decimal("0"),
        idle_classification=CiboIdleCapitalClass.OPTIONALITY_RESERVE,
    )
    return CiboObservedEconomicTwin(
        twin_id="full-economic-twin",
        captured_at=T0,
        capital_twin=capital,
        positions=(),
        opportunities=(opportunity,),
        portfolio=portfolio,
        velocity=velocity,
        cognitive_constraints=(("capital_intensity_cap", "3"),),
        provider_state=(("XAUUSD", "SUPPORTED"),),
    )


def test_full_twin_reuses_canonical_genc10_capital_truth_deterministically() -> None:
    first = _full_twin()
    second = _full_twin()

    assert first.capital_twin.total_realized_capital_usd == Decimal("120")
    assert first.snapshot_sha256 == second.snapshot_sha256
    assert observed_twin_constraints(first) == {
        "stop_risk_headroom_usd": Decimal("9"),
        "margin_headroom_usd": Decimal("98"),
        "waiting_stop_risk_usd": Decimal("0"),
        "waiting_margin_usd": Decimal("0"),
    }
    assert first.risk_authority is False
    assert first.execution_authority is False


def test_full_twin_rejects_future_known_opportunity() -> None:
    capital = _capital_twin()
    future = _opportunity(known_at=T0 + timedelta(minutes=1))

    with pytest.raises(
        CiboCapitalManagementError,
        match="future-known opportunity",
    ):
        CiboObservedEconomicTwin(
            twin_id="future-leak",
            captured_at=T0,
            capital_twin=capital,
            positions=(),
            opportunities=(future,),
            portfolio=CiboObservedPortfolioState(
                observed_at=T0,
                active_position_ids=(),
                opportunity_ids=(future.option_id,),
                concentration_utilization=Decimal("0"),
                correlation_utilization=Decimal("0"),
                reserved_stop_risk_usd=Decimal("0"),
                reserved_margin_usd=Decimal("0"),
            ),
            velocity=CiboCapitalVelocityState(
                observed_at=T0,
                released_stop_risk_usd=Decimal("0"),
                released_margin_usd=Decimal("0"),
                waiting_stop_risk_usd=Decimal("0"),
                waiting_margin_usd=Decimal("0"),
                oldest_release_age_minutes=Decimal("0"),
                idle_classification=CiboIdleCapitalClass.NO_VALID_OPPORTUNITY,
            ),
        )


def test_full_twin_cannot_fabricate_position_risk_beyond_genc10_truth() -> None:
    capital = _capital_twin()
    position = CiboObservedPositionState(
        signal_fingerprint="p1",
        qore_symbol="EURUSD",
        side="long",
        entry_at=T0 - timedelta(minutes=10),
        observed_at=T0,
        current_volume=Decimal("1"),
        current_stop_risk_usd=Decimal("1"),
        current_margin_usd=Decimal("1"),
        released_stop_risk_usd=Decimal("0"),
        released_margin_usd=Decimal("0"),
        remaining_reward_r=Decimal("1"),
        provider_cost_usd=Decimal("0.01"),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="position risk exceeds GEN-C10 used risk",
    ):
        CiboObservedEconomicTwin(
            twin_id="risk-fabrication",
            captured_at=T0,
            capital_twin=capital,
            positions=(position,),
            opportunities=(),
            portfolio=CiboObservedPortfolioState(
                observed_at=T0,
                active_position_ids=("p1",),
                opportunity_ids=(),
                concentration_utilization=Decimal("0.1"),
                correlation_utilization=Decimal("0.1"),
                reserved_stop_risk_usd=Decimal("0"),
                reserved_margin_usd=Decimal("0"),
            ),
            velocity=CiboCapitalVelocityState(
                observed_at=T0,
                released_stop_risk_usd=Decimal("0"),
                released_margin_usd=Decimal("0"),
                waiting_stop_risk_usd=Decimal("0"),
                waiting_margin_usd=Decimal("0"),
                oldest_release_age_minutes=Decimal("0"),
                idle_classification=CiboIdleCapitalClass.SAFE_RESERVE,
            ),
        )


def test_counterfactual_world_is_separate_and_non_authoritative() -> None:
    twin = _full_twin()
    before = twin.snapshot_sha256

    world = CiboCounterfactualEconomicWorld(
        world_id="mean-reversion",
        observed_twin_id=twin.twin_id,
        declared_at=T0,
        assumptions=(("regime", "MEAN_REVERSION"),),
        hypothetical_actions=("R34_XAUUSD:2x",),
        projected_stop_risk_delta_usd=Decimal("2"),
        projected_margin_delta_usd=Decimal("4"),
    )

    assert world.observed_twin_id == twin.twin_id
    assert world.productive_authority is False
    assert twin.snapshot_sha256 == before


def test_frontier_consumes_full_twin_for_portfolio_competition_and_leverage() -> None:
    twin = _full_twin()

    plan = plan_account_wide_capital_allocation(twin)

    assert tuple((item.option_id, item.multiplier) for item in plan.lines) == (
        ("known-r34", 3),
    )
    assert twin.risk_authority is False
    assert twin.execution_authority is False
