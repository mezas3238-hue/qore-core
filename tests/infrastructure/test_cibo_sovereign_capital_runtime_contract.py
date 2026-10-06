import ast
import inspect
from decimal import Decimal

import qore.infrastructure.cibo_sovereign_capital_runtime as module
from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_account_capital_mission import CiboCapitalMission
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
    TraderOpportunityEnvelope,
)


def test_every_sovereign_decision_constructor_carries_capital_science() -> None:
    tree = ast.parse(inspect.getsource(module))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "CiboSovereignCapitalDecision"
    ]

    assert calls
    for call in calls:
        keywords = {item.arg for item in call.keywords}
        assert "capital_science" in keywords



def test_sovereign_cap_resize_preserves_long_decimal_source_provenance() -> None:
    step = Decimal("0.0000000000000000000000000000000000000001")
    first = Decimal("1.1111111111111111111111111111111111111111")
    second = Decimal("2.2222222222222222222222222222222222222222")
    total = Decimal("3.3333333333333333333333333333333333333333")
    capped = Decimal("2.2222222222222222222222222222222222222222")
    opportunity = TraderOpportunityEnvelope(
        trader_id=TraderLineage.R34_XAUUSD,
        signal_fingerprint="resize-long-decimal",
        qore_symbol="XAUUSD",
        provider_symbol="XAUUSD",
        side="long",
        entry_type="market",
        intended_entry=Decimal("100"),
        stop_loss=Decimal("99"),
        take_profit=Decimal("102"),
        stop_loss_per_volume=Decimal("1"),
        margin_per_volume=Decimal("1"),
        volume_step=step,
        minimum_volume=step,
        maximum_volume=Decimal("10"),
    )
    plan = CiboCapitalActionPlan(
        trader_id=TraderLineage.R34_XAUUSD,
        qore_symbol="XAUUSD",
        stage=CapitalStage.CAPITALIZE,
        action=CapitalAction.OPEN_CAPABILITY_MAX,
        volume=total,
        stop_risk_usd=total,
        margin_usd=total,
        capital_source=None,
        capital_source_amount_usd=total,
        reason="resize exact provenance",
        capital_source_lots=(
            CapitalSourceLot(
                source=CapitalSource.ORIGINAL_BASE_CAPITAL,
                amount_usd=first,
                source_id="base",
            ),
            CapitalSourceLot(
                source=CapitalSource.REALIZED_PROFIT,
                amount_usd=second,
                source_id="profit",
            ),
        ),
    )
    sizing = CiboAccountSizingDecision(
        mission=CiboCapitalMission.DEMO_CAPABILITY_DISCOVERY,
        mode=CiboAccountSizingMode.CAPABILITY_MAXIMUM,
        base_protected=False,
        survival_capital_usd=Decimal("0"),
        protected_capital_usd=Decimal("0"),
        plan=plan,
    )

    resized = module._cap_sizing_plan(
        opportunity=opportunity,
        sizing=sizing,
        portfolio_risk_cap_usd=capped,
        portfolio_margin_cap_usd=Decimal("10"),
        robust_risk_cap_usd=capped,
        robust_margin_cap_usd=Decimal("10"),
    )

    assert resized.stop_risk_usd == capped
    assert resized.capital_source_amount_usd == capped
    assert tuple(lot.amount_usd for lot in resized.capital_source_lots) == (
        first,
        Decimal("1.1111111111111111111111111111111111111111"),
    )
