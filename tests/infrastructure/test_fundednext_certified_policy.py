from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import qore.infrastructure.account_policy as account_policy
import qore.infrastructure.fundednext_certified_policy as certified
import qore.kernel.result as result

_T0 = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)


def _payload(*, observed_at: datetime = _T0) -> dict[str, object]:
    facts: dict[str, object] = {
        "no_daily_loss_limit": True,
        "maximum_loss_fraction": "0.06",
        "trailing_maximum_loss": True,
        "ea_allowed_mt5": True,
        "ea_strategy_allocation_max_usd": "300000",
        "ea_duplicate_strategy_prohibited": True,
        "cumulative_open_risk_fraction": "0.03",
        "reclassified_open_risk_fraction": "0.01",
        "cumulative_open_risk_applies": True,
        "stop_loss_required": True,
        "quick_strike_seconds": 30,
        "quick_strike_warning_fraction": "0.20",
        "quick_strike_limit_fraction": "0.30",
        "news_window_minutes_each_side": 5,
        "news_profit_attribution_fraction": "0.40",
        "news_mll_equity_extension_fraction": "0.01",
        "news_mll_equity_extension_max_uses": 3,
        "copy_same_owner_stellar_instant_allowed": True,
        "copy_cross_fundednext_program_prohibited": True,
        "reward_split_tier_1_2": "0.70",
        "reward_split_tier_3_plus": "0.80",
        "reward_on_demand_growth_fraction": "0.05",
        "reward_biweekly_days": 14,
        "reward_min_growth_fraction": "0.01",
        "reward_eod_gate": True,
        "inactivity_calendar_days": 30,
        "consistency_rule_present": False,
        "max_purchased_allocation_usd": "20000",
        "account_merging_allowed": False,
        "max_scaled_allocation_usd": "2000000",
        "vps_allowed": True,
        "stellar_instant_5k_purchase_price_usd": "149.99",
    }
    sources = {
        name: {
            "url": f"https://help.fundednext.com/en/articles/{1000 + index}-rule",
            "sha256": f"{index + 1:064x}",
        }
        for index, name in enumerate(
            (
                "allocation",
                "clarity",
                "consistency",
                "copy",
                "ea",
                "general",
                "inactivity",
                "mll",
                "news",
                "payout",
                "pricing",
                "reward",
            )
        )
    }
    return {
        "schema": "qore.fundednext.provider-rules-refresh.v3",
        "observed_at": observed_at.isoformat(),
        "provider_rules_fingerprint": "a" * 64,
        "facts": facts,
        "sources": sources,
    }


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_certified_stellar_policy_resolves_for_risk(tmp_path: Path) -> None:
    path = tmp_path / "provider-rules-refresh.json"
    _write(path, _payload())

    bundle = certified.load_certified_stellar_instant_policy(
        refresh_path=path,
        account_binding_id="b" * 64,
        account_size=Decimal("2000"),
    )
    resolved = bundle.resolve_for_risk(_T0)

    assert isinstance(resolved, result.Success)
    assert resolved.value.max_drawdown.logical_values() == (600,)
    assert resolved.value.daily_loss_limit.logical_values() == (0,)
    assert resolved.value.drawdown_mode is account_policy.DrawdownMode.TRAILING
    assert resolved.value.client_profit_split.logical_values() == (7000,)
    assert bundle.facts.cumulative_open_risk_fraction == Decimal("0.03")
    assert bundle.facts.reclassified_open_risk_fraction == Decimal("0.01")
    assert bundle.facts.stop_loss_required is True
    assert bundle.facts.stellar_instant_5k_purchase_price_usd == Decimal("149.99")


def test_certified_stellar_policy_expires_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "provider-rules-refresh.json"
    _write(path, _payload())

    bundle = certified.load_certified_stellar_instant_policy(
        refresh_path=path,
        account_binding_id="b" * 64,
        account_size=Decimal("2000"),
    )
    resolved = bundle.resolve_for_risk(_T0 + timedelta(hours=7))

    assert isinstance(resolved, result.Failure)
    assert str(resolved.error) == (
        "certified policy source evidence is stale, revoked or not yet valid"
    )


def test_certified_stellar_policy_rejects_rule_drift(tmp_path: Path) -> None:
    path = tmp_path / "provider-rules-refresh.json"
    payload = _payload()
    facts = payload["facts"]
    assert isinstance(facts, dict)
    facts["maximum_loss_fraction"] = "0.08"
    _write(path, payload)

    try:
        certified.load_certified_stellar_instant_policy(
            refresh_path=path,
            account_binding_id="b" * 64,
            account_size=Decimal("2000"),
        )
    except ValueError as error:
        assert "maximum_loss_fraction" in str(error)
    else:
        raise AssertionError("rule drift must fail closed")


def test_certified_stellar_policy_rejects_non_official_source(tmp_path: Path) -> None:
    path = tmp_path / "provider-rules-refresh.json"
    payload = _payload()
    sources = payload["sources"]
    assert isinstance(sources, dict)
    item = sources["mll"]
    assert isinstance(item, dict)
    item["url"] = "http://example.com/rules"
    _write(path, payload)

    try:
        certified.load_certified_stellar_instant_policy(
            refresh_path=path,
            account_binding_id="b" * 64,
            account_size=Decimal("2000"),
        )
    except Exception as error:
        assert "HTTPS" in str(error) or "https" in str(error).casefold()
    else:
        raise AssertionError("untrusted source must fail closed")
