from dataclasses import dataclass
from decimal import Decimal

import pytest

import qore.infrastructure.cibo_economic_engine_wiring as wiring
import qore.infrastructure.cibo_sovereign_capital_runtime as runtime
from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMission,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_account_sizing_authority import (
    CiboAccountSizingDecision,
    CiboAccountSizingMode,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CapitalSource,
    CapitalSourceLot,
    CapitalStage,
    CiboCapitalActionPlan,
    CiboCapitalState,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ceiling_ablation import (
    CiboCeilingAblationMode,
    validate_ceiling_ablation_mode,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


def _opportunity() -> TraderOpportunityEnvelope:
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="ablation-alpha",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("2"),
        volume_step=Decimal("1"),
        minimum_volume=Decimal("1"),
        maximum_volume=Decimal("100"),
    )


def _mission_policy():
    identity = CiboAccountCapitalIdentity(
        provider_key="ablation-test",
        account_ref="ceiling-usd60",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    return derive_cibo_capital_mission(identity)


def test_ablation_mode_is_canonical_and_rejects_plain_string() -> None:
    assert (
        validate_ceiling_ablation_mode(CiboCeilingAblationMode.SIZING)
        is CiboCeilingAblationMode.SIZING
    )
    with pytest.raises(Exception):
        validate_ceiling_ablation_mode("sizing")  # type: ignore[arg-type]


def test_sizing_ablation_fixes_variable_size_to_one_minimum_seed() -> None:
    opportunity = _opportunity()
    plan = CiboCapitalActionPlan(
        trader_id=opportunity.trader_id,
        qore_symbol=opportunity.qore_symbol,
        stage=CapitalStage.CAPITALIZE,
        action=CapitalAction.OPEN_CAPABILITY_MAX,
        volume=Decimal("10"),
        stop_risk_usd=Decimal("10"),
        margin_usd=Decimal("20"),
        capital_source=None,
        capital_source_amount_usd=Decimal("10"),
        reason="full sizing",
        capital_source_lots=(
            CapitalSourceLot(
                source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                amount_usd=Decimal("5"),
                source_id="base",
            ),
            CapitalSourceLot(
                source=CapitalSource.REALIZED_PROFIT,
                amount_usd=Decimal("5"),
                source_id="profit",
            ),
        ),
    )
    sizing = CiboAccountSizingDecision(
        mission=CiboCapitalMission.DEMO_CAPABILITY_DISCOVERY,
        mode=CiboAccountSizingMode.CAPABILITY_MAXIMUM,
        base_protected=False,
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
        plan=plan,
    )

    ablated = runtime._ablate_variable_sizing(
        opportunity=opportunity,
        sizing=sizing,
    )

    assert ablated.mode is CiboAccountSizingMode.SURVIVAL_MINIMAL_SEED
    assert ablated.plan.volume == Decimal("1")
    assert ablated.plan.stop_risk_usd == Decimal("1")
    assert ablated.plan.margin_usd == Decimal("2")
    assert tuple(
        (lot.source, lot.amount_usd)
        for lot in ablated.plan.capital_source_lots
    ) == ((CapitalSource.ORIGINAL_BASE_CAPITAL, Decimal("1")),)


def test_compound_ablation_makes_realized_profit_non_deployable() -> None:
    opportunity = _opportunity()
    capital = CiboCapitalState(
        assigned_capital_usd=Decimal("100"),
        hard_risk_headroom_usd=Decimal("100"),
        margin_headroom_usd=Decimal("1000"),
        base_capital_at_risk_usd=Decimal("20"),
        realized_net_profit_usd=Decimal("40"),
        protected_open_economic_floor_usd=Decimal("0"),
        proven_self_financing_capacity_usd=Decimal("40"),
        reserved_expansion_risk_usd=Decimal("0"),
        cost_reserve_usd=Decimal("0"),
    )

    ablated = runtime._plan_without_compound_funding(
        opportunity=opportunity,
        capital=capital,
        mission_policy=_mission_policy(),
        survival_capital_usd=Decimal("60"),
        protected_capital_usd=Decimal("0"),
        provider_cost_per_volume_usd=Decimal("0"),
        original_base_available_usd=Decimal("20"),
    )

    assert ablated.plan.stop_risk_usd == Decimal("20")
    assert all(
        lot.source is CapitalSource.ORIGINAL_BASE_CAPITAL
        for lot in ablated.plan.capital_source_lots
    )
    assert all(
        lot.source is not CapitalSource.REALIZED_PROFIT
        for lot in ablated.plan.capital_source_lots
    )


@dataclass(frozen=True)
class _Portfolio:
    opportunity_ids: tuple[str, ...]


@dataclass(frozen=True)
class _Twin:
    twin_id: str
    opportunities: tuple[object, ...]
    portfolio: _Portfolio


def test_portfolio_and_leverage_ablation_seams_are_orthogonal(monkeypatch) -> None:
    options = (
        type("Option", (), {"option_id": "a"})(),
        type("Option", (), {"option_id": "b"})(),
    )
    twin = _Twin(
        twin_id="twin",
        opportunities=options,
        portfolio=_Portfolio(opportunity_ids=("a", "b")),
    )
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        wiring,
        "plan_genc11_multi_period_capital",
        lambda **kwargs: object(),
    )

    def _portfolio_plan(seen_twin, *, fixed_multiplier=None):
        observed["ids"] = tuple(
            item.option_id for item in seen_twin.opportunities
        )
        observed["fixed_multiplier"] = fixed_multiplier
        return object()

    monkeypatch.setattr(
        wiring,
        "plan_account_wide_capital_allocation",
        _portfolio_plan,
    )
    monkeypatch.setattr(
        wiring,
        "plan_position_opportunity_competition",
        lambda twin, *, opportunity_id: object(),
    )

    wiring.run_cibo_economic_engine_chain(
        twin=twin,  # type: ignore[arg-type]
        world_paths=(),
        option_schedules=(),
        competition_option_ids=("a",),
        portfolio_fixed_multiplier=1,
        portfolio_target_only_option_id="a",
    )

    assert observed["ids"] == ("a",)
    assert observed["fixed_multiplier"] == 1
