from decimal import Decimal

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
    select_ce2i_tools_for_regime,
)
from qore.infrastructure.cibo_next_policy_advanced_scientific_eligibility import (
    ADVANCED_CODES,
    NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


def _selection():
    account = CiboAccountCapitalIdentity(
        provider_key="ctrader-demo",
        account_id="NEXT_POLICY_TEST",
        environment=MarketRuntimeEnvironment.DEMO,
        starting_balance_usd=Decimal("60"),
        current_realized_balance_usd=Decimal("60"),
    )
    mission = derive_cibo_capital_mission(account)
    state = CiboCapitalRegimeState(
        liquidity=LiquidityState.NORMAL,
        volatility=VolatilityState.NORMAL,
        correlation=CorrelationState.NORMAL,
        provider_condition=ProviderCondition.HEALTHY,
        risk_utilization=Decimal("0"),
        margin_utilization=Decimal("0"),
        drawdown_utilization=Decimal("0"),
        opportunity_count=3,
    )
    return select_ce2i_tools_for_regime(mission=mission, state=state)


def test_freeze_covers_exact_advanced_surface_without_runtime_promotion() -> None:
    freeze = NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY

    assert tuple(item.tool_code for item in freeze.tools) == ADVANCED_CODES
    assert freeze.runtime_eligible_codes == ()
    assert freeze.shadow_only_codes == ("T02", "T04", "T08", "T10")
    assert freeze.terminal_disabled_codes == ("T03", "T16", "T17")
    assert freeze.v2_economic_outcomes_used_for_selection is False
    assert freeze.v2_qualification_failure_used_as_runtime_tuning is False
    assert freeze.fingerprint().startswith("sha256:")


def test_scientific_filter_removes_unproven_advanced_tools_but_not_registry() -> None:
    raw = _selection()
    filtered = (
        NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY
        .filter_regime_selection(raw)
    )

    assert not (set(filtered.enabled_tools) & set(ADVANCED_CODES))
    assert set(ADVANCED_CODES).issubset(set(filtered.blocked_tools))
    assert "scientific eligibility=sha256:" in filtered.reason

    nonadvanced_raw = tuple(
        code for code in raw.enabled_tools if code not in ADVANCED_CODES
    )
    nonadvanced_filtered = tuple(
        code for code in filtered.enabled_tools if code not in ADVANCED_CODES
    )
    assert nonadvanced_filtered == nonadvanced_raw


def test_shadow_only_tools_have_preregistered_protocols() -> None:
    freeze = NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY

    for item in freeze.tools:
        if item.tool_code in {"T02", "T04", "T08", "T10"}:
            assert item.scientific_disposition == "EXTERNAL_DEPENDENCY_BLOCKED"
            assert item.shadow_protocol_refs
        else:
            assert item.scientific_disposition == "FALSIFIED_AND_CLOSED"
            assert item.shadow_protocol_refs == ()


def test_filter_is_deterministic_and_never_reenables_regime_blocked_tool() -> None:
    raw = _selection()
    freeze = NEXT_POLICY_ADVANCED_SCIENTIFIC_ELIGIBILITY

    first = freeze.filter_regime_selection(raw)
    second = freeze.filter_regime_selection(raw)

    assert first == second
    assert set(first.enabled_tools).issubset(set(raw.enabled_tools))
