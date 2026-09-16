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
    assert provider["separate_max_risk_at_any_time_fraction"] == "0.03"
    assert provider["provider_three_percent_rule_used_by_risk"] is True
    internal = payload["qore_internal_policy"]
    assert isinstance(internal, dict)
    assert internal["explicitly_not_provider_rule"] is True


def test_component_certification_cannot_self_authorize_live_send() -> None:
    payload = build_certification(git_sha=_SHA)
    governance = payload["governance"]
    assert isinstance(governance, dict)
    assert governance["component_certification_grants_order_send_authority"] is False
    assert governance["component_certification_grants_live_activation"] is False
