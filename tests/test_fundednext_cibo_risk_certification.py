from __future__ import annotations

from qore.infrastructure.fundednext_cibo_risk_certification import build_certification

_SHA = "a" * 40


def test_component_certification_binds_exact_6pct_provider_and_separate_qore_policy() -> None:
    payload = build_certification(git_sha=_SHA)
    assert payload["status"] == "CIBO_RISK_COMPONENT_CERTIFIED"
    provider = payload["provider"]
    assert isinstance(provider, dict)
    assert provider["maximum_loss_fraction"] == "0.06"
    assert provider["daily_loss_limit"] is None
    assert provider["cumulative_open_risk_fraction"] == "0.03"
    assert provider["cumulative_open_risk_guard_enforced"] is True
    assert provider["cumulative_open_risk_is_maximum_loss"] is False
    internal = payload["qore_internal_policy"]
    assert isinstance(internal, dict)
    assert internal["explicitly_not_provider_rule"] is True
    assert internal["maximum_loss_fraction"] == "0.06"
    assert internal["uses_provider_mll_without_second_trailing_wall"] is True


def test_component_certification_cannot_self_authorize_live_send() -> None:
    payload = build_certification(git_sha=_SHA)
    governance = payload["governance"]
    assert isinstance(governance, dict)
    assert governance["component_certification_grants_order_send_authority"] is False
    assert governance["component_certification_grants_live_activation"] is False


def test_component_certification_binds_cibo_as_fundednext_capital_authority() -> None:
    payload = build_certification(git_sha=_SHA)

    cibo = payload["cibo"]
    assert isinstance(cibo, dict)
    assert cibo["capital_management_authority"] is True
    assert cibo["runtime_sizing_authority"] is True
    assert cibo["legacy_trader_sizing_authority"] is False
    assert cibo["mission"] == "FUNDED_SURVIVAL_COMPOUND"
    assert cibo["provider"] == "FundedNext"
    assert cibo["provider_program"] == "STELLAR_INSTANT"

    risk = payload["account_wide_risk"]
    assert isinstance(risk, dict)
    assert risk["hard_survivability_governor"] is True
    assert risk["capital_management_strategy_authority"] is False
    assert risk["runtime_sizing_authority"] is False
    assert risk["decisions"] == ["ALLOW", "REDUCE", "REJECT"]



def test_component_certification_covers_all_seven_cibo_lineages() -> None:
    payload = build_certification(git_sha=_SHA)
    scope = payload["scope"]
    assert isinstance(scope, dict)
    assert scope["trader_count"] == 7
    traders = scope["traders"]
    assert isinstance(traders, dict)
    assert set(traders) == {
        "VT08_FOREX",
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
        "VT31_NAS100",
    }
    assert scope["legacy_trader_sizing_execution_authority"] is False


def test_component_certification_binds_survival_then_protected_capacity_law() -> None:
    payload = build_certification(git_sha=_SHA)
    cibo = payload["cibo"]
    assert isinstance(cibo, dict)
    assert cibo["account_scoped_sizing"] is True
    assert cibo["all_loaded_traders_use_cibo_sizing"] is True
    assert cibo["survival_capital_source"] == "QORE_ACCOUNT_HEAT_CAP"
    assert cibo["protected_capital_source"] == "EARNED_CLOSED_BALANCE_CUSHION"
    assert cibo["before_base_protection_mode"] == "SURVIVAL_MINIMAL_SEED"
    assert cibo["after_base_protection_mode"] == "PROTECTED_FULL_CAPACITY"
    assert cibo["floating_pnl_counts_as_protected_capital"] is False
    assert cibo["legacy_trader_risk_fraction_execution_authority"] is False
    assert cibo["account_capital_postures"] == [
        "BANK",
        "NORMAL",
        "ATTACK",
    ]
