from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "qore_fundednext_rules_refresh.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "qore_rule_refresh_script_test",
        _SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load_script()

_GOOD = {
    "mll": (
        b"Stellar Instant has no Daily Loss Limit and a 6% trailing Maximum Loss."
    ),
    "ea": (
        b"Stellar Instant Expert Advisors are allowed on MetaTrader 5 MT5. "
        b"Customize the EA. No duplicate strategies. Max allocation $300,000."
    ),
    "clarity": (
        b"Risk Limit default risk limit is 3% cumulative across all open positions. "
        b"If reclassified the limit is 1%. Stop-loss is required. Quick Strike "
        b"means profitable positions closed within 30 seconds; keep below 30%. "
        b"Warning at 20%. News is 5 minutes before and 5 minutes after; 40% counts."
    ),
    "copy": (
        b"Copy trading between Stellar Instant accounts owned by the same individual "
        b"is allowed. Across individuals is strictly prohibited. Copy with Stellar "
        b"1-Step, Stellar 2-Step, or Stellar Lite is strictly prohibited."
    ),
    "payout": (
        b"Performance Reward on demand at 5% growth after End of Day EOD. "
        b"Bi-weekly after 14 days. Minimum growth requirement is 1%."
    ),
    "reward": (
        b"Tier 1 and Tier 2 receive 70%. Tier 3 and above receive 80%."
    ),
    "inactivity": (
        b"Accounts expire after 30 consecutive calendar days of inactivity."
    ),
    "consistency": (
        b"Stellar Instant has no consistency rules."
    ),
    "allocation": (
        b"Maximum purchased allocation is $20,000. Account merging is not allowed. "
        b"Scaling can reach $2 million."
    ),
    "general": (
        b"VPS services are permitted. Copy Trading rules apply. Restricted trading "
        b"strategies intended to exploit the system are prohibited."
    ),
    "news": (
        b"News trading applies 5 minutes before and 5 minutes after. Only 40% of "
        b"profit counts. A 1% safety buffer or 1% equity extension applies to the "
        b"MLL and can be used a maximum of 3 times."
    ),
    "pricing": (
        b"Stellar Instant Pricing Table $2,000 Account $59.99 "
        b"$5,000 Account $149.99 $10,000 Account $299.99 "
        b"$20,000 Account $599.99"
    ),
}


def _prepare_root(tmp_path: Path, *, fingerprint_matches: bool = True) -> str:
    provider = tmp_path / "src/qore/infrastructure/fundednext_stellar_instant.py"
    provider.parent.mkdir(parents=True)
    provider.write_bytes(b"provider-contract")
    fingerprint = hashlib.sha256(provider.read_bytes()).hexdigest()
    activation_fingerprint = fingerprint if fingerprint_matches else "b" * 64
    activation = tmp_path / "var/fundednext/live-activation.json"
    activation.parent.mkdir(parents=True)
    activation.write_text(
        json.dumps({"provider_rules_fingerprint": activation_fingerprint}),
        encoding="utf-8",
    )
    return fingerprint


def _pages(overrides: dict[str, bytes] | None = None) -> dict[str, bytes]:
    source_by_name = dict(_GOOD)
    if overrides:
        source_by_name.update(overrides)
    return {
        MODULE.MLL_URL: source_by_name["mll"],
        MODULE.EA_URL: source_by_name["ea"],
        MODULE.CLARITY_URL: source_by_name["clarity"],
        MODULE.COPY_URL: source_by_name["copy"],
        MODULE.PAYOUT_URL: source_by_name["payout"],
        MODULE.REWARD_URL: source_by_name["reward"],
        MODULE.INACTIVITY_URL: source_by_name["inactivity"],
        MODULE.CONSISTENCY_URL: source_by_name["consistency"],
        MODULE.ALLOCATION_URL: source_by_name["allocation"],
        MODULE.GENERAL_URL: source_by_name["general"],
        MODULE.NEWS_URL: source_by_name["news"],
        MODULE.PRICING_URL: source_by_name["pricing"],
    }


def test_refresh_certifies_complete_stellar_instant_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _prepare_root(tmp_path)
    pages = _pages()
    monkeypatch.setattr(MODULE, "_fetch", lambda url: pages[url])

    payload = MODULE.refresh(tmp_path)

    assert payload["schema"] == "qore.fundednext.provider-rules-refresh.v3"
    assert payload["provider_rules_fingerprint"] == expected
    assert isinstance(payload["observed_at"], str)
    facts = payload["facts"]
    assert facts["maximum_loss_fraction"] == "0.06"
    assert facts["cumulative_open_risk_fraction"] == "0.03"
    assert facts["reclassified_open_risk_fraction"] == "0.01"
    assert facts["stop_loss_required"] is True
    assert facts["quick_strike_seconds"] == 30
    assert facts["news_profit_attribution_fraction"] == "0.40"
    assert facts["reward_split_tier_1_2"] == "0.70"
    assert facts["reward_split_tier_3_plus"] == "0.80"
    assert facts["inactivity_calendar_days"] == 30
    assert facts["account_merging_allowed"] is False
    assert facts["stellar_instant_5k_purchase_price_usd"] == "149.99"
    assert len(payload["sources"]) == 12
    for item in payload["sources"].values():
        assert len(item["sha256"]) == 64
        assert item["url"].startswith("https://help.fundednext.com/")


def test_refresh_rejects_fingerprint_mismatch_before_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_root(tmp_path, fingerprint_matches=False)
    called = False

    def fetch(_: str) -> bytes:
        nonlocal called
        called = True
        return b"unused"

    monkeypatch.setattr(MODULE, "_fetch", fetch)
    with pytest.raises(RuntimeError, match="fingerprint mismatch"):
        MODULE.refresh(tmp_path)
    assert called is False


def test_refresh_rejects_source_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _prepare_root(tmp_path)

    def fetch(_: str) -> bytes:
        raise RuntimeError("source-read-failed")

    monkeypatch.setattr(MODULE, "_fetch", fetch)
    with pytest.raises(RuntimeError, match="source-read-failed"):
        MODULE.refresh(tmp_path)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"mll": b"Stellar Instant no Daily Loss Limit trailing Maximum Loss"},
            "6% trailing Maximum Loss",
        ),
        (
            {"clarity": b"Risk Limit default risk limit is 3%"},
            "cumulative open-position",
        ),
        (
            {
                "clarity": (
                    b"Risk Limit default risk limit is 3% cumulative across all "
                    b"open positions."
                )
            },
            "1% reclassification",
        ),
        (
            {
                "copy": (
                    b"Copy trading between accounts owned by the same individual "
                    b"is allowed. Across individuals is strictly prohibited."
                )
            },
            "cross-program restriction",
        ),
        (
            {"payout": b"Performance Reward 5% growth and 14 days."},
            "minimum growth",
        ),
        (
            {"news": b"News 5 minutes before and 5 minutes after; 40%."},
            "news MLL buffer",
        ),
        (
            {"pricing": b"Stellar Instant $5,000 Account price unavailable"},
            "5K purchase price",
        ),
    ],
)
def test_refresh_rejects_missing_certified_rule_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, bytes],
    message: str,
) -> None:
    _prepare_root(tmp_path)
    pages = _pages(overrides)
    monkeypatch.setattr(MODULE, "_fetch", lambda url: pages[url])
    with pytest.raises(RuntimeError, match=message):
        MODULE.refresh(tmp_path)
