from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_digital_twin import (
    GENC10_POLICY_SHA256,
    Genc10CapitalFlow,
    Genc10EconomicBucket,
    Genc10FlowKind,
    Genc10KnownCapitalOption,
    Genc10WorldKind,
    Genc10WorldScenario,
    build_genc10_observed_twin,
    project_genc10_world,
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
from qore.infrastructure.cibo_compound_capital import (
    CiboCompoundCapitalError,
    CompoundCapitalState,
)
from qore.infrastructure.cibo_compound_cycle_state import (
    classify_compound_capital,
    ingest_base_settlement,
    initialize_compound_cycle,
    policy_protect_floor,
    protect_compound_capital,
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
from qore.infrastructure.market_test_environment import (
    MarketRuntimeEnvironment,
)

T0 = datetime(2026, 9, 30, 8, 0, tzinfo=UTC)


def _identity() -> CiboAccountCapitalIdentity:
    return CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="genc10-twin",
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


def _cycle():
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
        policy_id="GENC10_TEST_FLOOR",
        policy_sha256="sha256:" + "a" * 64,
    )
    return classify_compound_capital(
        state,
        event_id="compoundable",
        occurred_at=T0 - timedelta(minutes=2),
        source_lot_id="protect:remainder",
        to_state=CompoundCapitalState.COMPOUNDABLE,
        amount_usd=Decimal("15"),
    )


def _truth(state):
    return build_integrated_capital_truth(
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


def _registry(identity=None):
    account = _identity() if identity is None else identity
    entries = (
        ProviderCapabilityEvidence(
            evidence_id="cfd",
            account_identity=account,
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
        ProviderCapabilityEvidence(
            evidence_id="option",
            account_identity=account,
            capability=InstrumentCapability.OPTION,
            status=CapabilityStatus.UNAVAILABLE,
            observed_at=T0 - timedelta(hours=1),
            produced_at=T0 - timedelta(minutes=50),
            source="PROVIDER_NORMALIZATION",
            source_ref="provider://option",
            evidence_sha256="sha256:" + "c" * 64,
            policy_version="PROVIDER_CAPABILITY_V1",
            provider_verified=True,
        ),
    )
    return ProviderInstrumentCapabilityRegistry(
        account_identity=account,
        entries=entries,
        captured_at=T0 - timedelta(minutes=1),
    )


def _option() -> Genc10KnownCapitalOption:
    return Genc10KnownCapitalOption(
        option_id="known-r34",
        known_at=T0 - timedelta(minutes=1),
        earliest_action_at=T0 + timedelta(minutes=1),
        expires_at=T0 + timedelta(minutes=20),
        requested_capital_usd=Decimal("5"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        evidence_sha256="sha256:" + "d" * 64,
    )


def _twin():
    state = _cycle()
    return build_genc10_observed_twin(
        twin_id="twin-1",
        captured_at=T0,
        compound_state=state,
        capital_truth=_truth(state),
        source_ledger=_source(),
        provider_registry=_registry(),
        known_options=(_option(),),
    )


def test_genc10_policy_digest_is_frozen() -> None:
    assert GENC10_POLICY_SHA256 == (
        "sha256:d9f8eac29481e502c1f45e8eb1c4f59c6aaa90bfa63ca0dcb067ee7b5620cc0b"
    )


def test_genc10_observed_twin_conserves_current_capital_truth() -> None:
    twin = _twin()

    assert twin.total_realized_capital_usd == Decimal("120")
    assert twin.original_base_usd == Decimal("100")
    assert twin.compound_economic_value_usd == Decimal("20")
    assert twin.protected_floor_usd == Decimal("5")
    assert twin.policy_protected_floor_usd == Decimal("5")
    assert twin.broker_guaranteed_floor_usd == Decimal("0")
    assert twin.bucket(
        Genc10EconomicBucket.RETIRED_TO_PROTECTED_FLOOR
    ) == Decimal("5")
    assert twin.bucket(
        Genc10EconomicBucket.COMPOUNDABLE
    ) == Decimal("15")
    assert twin.stop_risk_headroom_usd == Decimal("10")
    assert twin.margin_headroom_usd == Decimal("100")
    assert twin.generation_balances == ((1, Decimal("20")),)
    assert twin.known_options[0].option_id == "known-r34"
    assert twin.productive_authority is False


def test_genc10_world_transition_conserves_value_and_capacity() -> None:
    twin = _twin()
    scenario = Genc10WorldScenario(
        scenario_id="balanced-1",
        kind=Genc10WorldKind.BALANCED,
        declared_at=T0,
        scenario_evidence_sha256="sha256:" + "1" * 64,
        transition_uncertainty_evidence_sha256="sha256:" + "2" * 64,
        flows=(
            Genc10CapitalFlow(
                flow_id="reserve",
                kind=Genc10FlowKind.INTERNAL_TRANSFER,
                amount_usd=Decimal("3"),
                source_bucket=Genc10EconomicBucket.COMPOUNDABLE,
                target_bucket=Genc10EconomicBucket.STRATEGIC_RESERVE,
                evidence_sha256="sha256:" + "3" * 64,
            ),
            Genc10CapitalFlow(
                flow_id="gain",
                kind=Genc10FlowKind.SETTLED_GAIN,
                amount_usd=Decimal("4"),
                target_bucket=Genc10EconomicBucket.REALIZED_PROFIT,
                evidence_sha256="sha256:" + "4" * 64,
            ),
            Genc10CapitalFlow(
                flow_id="loss",
                kind=Genc10FlowKind.REALIZED_LOSS,
                amount_usd=Decimal("2"),
                source_bucket=Genc10EconomicBucket.ORIGINAL_BASE,
                evidence_sha256="sha256:" + "5" * 64,
            ),
        ),
        stop_risk_capacity_delta_usd=Decimal("-1"),
        stop_risk_usage_delta_usd=Decimal("2"),
        margin_capacity_delta_usd=Decimal("-10"),
        margin_usage_delta_usd=Decimal("5"),
        surviving_known_option_ids=("known-r34",),
        hypothetical_new_option_count=2,
    )

    projected = project_genc10_world(
        twin=twin,
        scenario=scenario,
        projected_at=T0 + timedelta(minutes=10),
    )

    assert projected.total_realized_capital_usd == Decimal("122")
    assert projected.settled_gain_usd == Decimal("4")
    assert projected.realized_loss_usd == Decimal("2")
    assert projected.conservation_residual_usd == Decimal("0")
    assert projected.protected_floor_usd == Decimal("5")
    assert projected.total_stop_risk_capacity_usd == Decimal("9")
    assert projected.used_stop_risk_usd == Decimal("2")
    assert projected.stop_risk_headroom_usd == Decimal("7")
    assert projected.total_margin_capacity_usd == Decimal("90")
    assert projected.used_margin_usd == Decimal("5")
    assert projected.margin_headroom_usd == Decimal("85")
    assert projected.market_probability_claimed is False
    assert projected.productive_authority is False


def test_genc10_protected_floor_cannot_flow_back_to_growth() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="protected floor cannot flow back",
    ):
        Genc10CapitalFlow(
            flow_id="unprotect",
            kind=Genc10FlowKind.INTERNAL_TRANSFER,
            amount_usd=Decimal("1"),
            source_bucket=(
                Genc10EconomicBucket.RETIRED_TO_PROTECTED_FLOOR
            ),
            target_bucket=Genc10EconomicBucket.COMPOUNDABLE,
            evidence_sha256="sha256:" + "6" * 64,
        )


def test_genc10_scenario_rejects_probability_or_future_outcome() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="cannot claim calibration/outcome/authority",
    ):
        Genc10WorldScenario(
            scenario_id="oracle",
            kind=Genc10WorldKind.AGGRESSIVE_GROWTH,
            declared_at=T0,
            scenario_evidence_sha256="sha256:" + "7" * 64,
            transition_uncertainty_evidence_sha256="sha256:" + "8" * 64,
            market_probability_claimed=True,
        )


def test_genc10_capacity_shock_cannot_make_used_capacity_impossible() -> None:
    twin = _twin()
    scenario = Genc10WorldScenario(
        scenario_id="margin-crisis",
        kind=Genc10WorldKind.CRISIS,
        declared_at=T0,
        scenario_evidence_sha256="sha256:" + "9" * 64,
        transition_uncertainty_evidence_sha256="sha256:" + "e" * 64,
        stop_risk_usage_delta_usd=Decimal("5"),
        stop_risk_capacity_delta_usd=Decimal("-6"),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="exceeds projected stop-risk capacity",
    ):
        project_genc10_world(
            twin=twin,
            scenario=scenario,
            projected_at=T0 + timedelta(minutes=1),
        )


def test_genc10_provider_change_requires_explicit_evidence() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="provider change requires evidence",
    ):
        Genc10WorldScenario(
            scenario_id="provider-change",
            kind=Genc10WorldKind.CRISIS,
            declared_at=T0,
            scenario_evidence_sha256="sha256:" + "f" * 64,
            transition_uncertainty_evidence_sha256=(
                "sha256:" + "1" * 64
            ),
            provider_constraints_changed=True,
        )


def test_genc10_rejects_cross_account_provider_registry() -> None:
    other = CiboAccountCapitalIdentity(
        provider_key="ctrader",
        account_ref="other-account",
        environment=MarketRuntimeEnvironment.TEST,
    )
    state = _cycle()
    with pytest.raises(
        CiboCompoundCapitalError,
        match="provider registry account drift",
    ):
        build_genc10_observed_twin(
            twin_id="cross-account",
            captured_at=T0,
            compound_state=state,
            capital_truth=_truth(state),
            source_ledger=_source(),
            provider_registry=_registry(other),
        )


def test_genc10_observed_twin_rejects_future_known_option() -> None:
    state = _cycle()
    option = Genc10KnownCapitalOption(
        option_id="future-known",
        known_at=T0 + timedelta(seconds=1),
        earliest_action_at=T0 + timedelta(minutes=1),
        expires_at=T0 + timedelta(minutes=20),
        requested_capital_usd=Decimal("5"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        evidence_sha256="sha256:" + "2" * 64,
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="future-known options",
    ):
        build_genc10_observed_twin(
            twin_id="future-option",
            captured_at=T0,
            compound_state=state,
            capital_truth=_truth(state),
            source_ledger=_source(),
            provider_registry=_registry(),
            known_options=(option,),
        )

def test_genc10_frozen_contract_accepts_historical_observed_state() -> None:
    historical_at = datetime(2021, 1, 4, 12, 0, tzinfo=UTC)
    twin = _twin()
    historical = __import__("dataclasses").replace(
        twin,
        captured_at=historical_at,
        known_options=(),
    )

    assert historical.captured_at == historical_at
    assert historical.policy_sha256 == GENC10_POLICY_SHA256
    assert historical.future_leakage_used is False

