"""Refresh FundedNext Stellar Instant certified provider-rule evidence."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

MLL_URL = (
    "https://help.fundednext.com/en/articles/"
    "11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-"
    "for-the-stellar-instant-accounts"
)
EA_URL = (
    "https://help.fundednext.com/en/articles/"
    "11641338-can-i-use-ea-in-stellar-instant"
)
CLARITY_URL = (
    "https://help.fundednext.com/en/articles/"
    "15644011-what-are-the-clarity-cards-and-how-do-they-affect-my-account"
)
COPY_URL = (
    "https://help.fundednext.com/en/articles/"
    "11672342-is-copy-trading-allowed-in-stellar-instant"
)
PAYOUT_URL = (
    "https://help.fundednext.com/en/articles/"
    "11641693-what-is-the-eligibility-criteria-for-my-performance-reward-"
    "in-the-stellar-instant-account"
)
REWARD_URL = (
    "https://help.fundednext.com/en/articles/"
    "11641381-what-will-be-my-performance-reward-from-the-stellar-instant-account"
)
INACTIVITY_URL = (
    "https://help.fundednext.com/en/articles/"
    "8019664-is-there-an-inactivity-period-for-my-accounts-in-fundednext-cfd"
)
CONSISTENCY_URL = (
    "https://help.fundednext.com/en/articles/"
    "11641328-are-there-any-consistency-rules-for-the-stellar-instant-account"
)
ALLOCATION_URL = (
    "https://help.fundednext.com/en/articles/"
    "11641400-what-is-the-maximum-allocation-for-the-stellar-instant-account"
)
GENERAL_URL = (
    "https://help.fundednext.com/en/articles/"
    "11641614-what-rules-do-i-need-to-follow-in-the-stellar-instant-account"
)
NEWS_URL = (
    "https://help.fundednext.com/en/articles/"
    "11641410-is-news-trading-allowed-in-the-stellar-instant-accounts"
)

_SCHEMA = "qore.fundednext.provider-rules-refresh.v3"


def _fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "QORE-Core/1.0 provider-rule-verifier"})
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed trusted HTTPS URLs
        if getattr(response, "status", 200) != 200:
            raise RuntimeError(f"provider rule source returned HTTP {response.status}")
        return response.read()


def _text(raw: bytes) -> str:
    decoded = raw.decode("utf-8", errors="replace")
    stripped = re.sub(r"<[^>]+>", " ", html.unescape(decoded))
    return re.sub(r"\s+", " ", stripped).casefold()


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def refresh(root: Path) -> dict[str, object]:
    activation_path = root / "var/fundednext/live-activation.json"
    activation = json.loads(activation_path.read_text(encoding="utf-8-sig"))
    provider_path = root / "src/qore/infrastructure/fundednext_stellar_instant.py"
    local_provider_hash = hashlib.sha256(provider_path.read_bytes()).hexdigest()
    expected_provider_hash = str(activation["provider_rules_fingerprint"])
    _require(
        local_provider_hash == expected_provider_hash,
        "provider contract fingerprint mismatch",
    )

    urls = {
        "mll": MLL_URL,
        "ea": EA_URL,
        "clarity": CLARITY_URL,
        "copy": COPY_URL,
        "payout": PAYOUT_URL,
        "reward": REWARD_URL,
        "inactivity": INACTIVITY_URL,
        "consistency": CONSISTENCY_URL,
        "allocation": ALLOCATION_URL,
        "general": GENERAL_URL,
        "news": NEWS_URL,
    }
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {name: pool.submit(_fetch, url) for name, url in urls.items()}
        sources = {name: future.result() for name, future in futures.items()}

    texts = {name: _text(raw) for name, raw in sources.items()}
    mll = texts["mll"]
    ea = texts["ea"]
    clarity = texts["clarity"]
    copy = texts["copy"]
    payout = texts["payout"]
    reward = texts["reward"]
    inactivity = texts["inactivity"]
    consistency = texts["consistency"]
    allocation = texts["allocation"]
    general = texts["general"]
    news = texts["news"]

    _require("stellar instant" in mll, "MLL source no longer identifies Stellar Instant")
    _require(
        "no daily loss limit" in mll or "no daily loss limits" in mll,
        "no-daily-loss rule not verified",
    )
    _require("6%" in mll and "trailing" in mll, "6% trailing Maximum Loss not verified")

    _require("stellar instant" in ea, "EA source no longer identifies Stellar Instant")
    _require(
        "expert advisors" in ea
        and ("meta trader 5" in ea or "metatrader 5" in ea or "mt5" in ea),
        "EA-on-MT5 rule not verified",
    )
    _require("allowed" in ea, "EA permission wording not verified")
    _require("$300,000" in ea or "300,000" in ea, "EA strategy allocation not verified")
    _require("duplicate" in ea, "EA duplicate-strategy restriction not verified")

    _require("risk limit" in clarity, "Clarity risk rule missing")
    _require(
        "default risk limit is 3%" in clarity,
        "3% cumulative open-position Risk Limit not verified",
    )
    _require(
        "cumulative across all open positions" in clarity,
        "cumulative open-position risk scope not verified",
    )
    _require("1%" in clarity and "reclassified" in clarity, "1% reclassification not verified")
    _require("stop-loss" in clarity, "mandatory stop-loss rule not verified")
    _require("30 seconds" in clarity and "30%" in clarity, "Quick Strike rule not verified")
    _require(
        "5 minutes before" in clarity
        and "5 minutes after" in clarity
        and "40%" in clarity,
        "Clarity news-profit rule not verified",
    )

    _require(
        "same individual" in copy and "strictly prohibited" in copy,
        "copy-trading ownership restriction not verified",
    )
    _require(
        "stellar 1-step" in copy and "stellar 2-step" in copy and "stellar lite" in copy,
        "copy-trading cross-program restriction not verified",
    )

    _require("5% growth" in payout and "14 days" in payout, "payout cadence not verified")
    _require("minimum growth" in payout and "1%" in payout, "payout minimum growth not verified")
    _require("end of day" in payout or "eod" in payout, "payout EOD gate not verified")

    _require("70%" in reward and "80%" in reward, "reward split tiers not verified")
    _require("tier 3" in reward, "reward tier transition not verified")

    _require(
        "30 consecutive calendar days" in inactivity,
        "30-day inactivity rule not verified",
    )
    _require(
        "no consistency rules" in consistency,
        "no-consistency rule not verified",
    )
    _require("$20,000" in allocation or "20,000" in allocation, "allocation cap not verified")
    _require("merging is not allowed" in allocation, "account merging rule not verified")
    _require("$2 million" in allocation or "2 million" in allocation, "scale ceiling not verified")

    _require("vps" in general and "permitted" in general, "VPS permission not verified")
    _require("copy trading" in general, "general copy-trading rule missing")
    _require("restricted" in general, "restricted-strategy rule missing")

    _require(
        "5 minutes before" in news and "5 minutes after" in news,
        "news execution window not verified",
    )
    _require("40%" in news, "news profit attribution not verified")
    _require("1% safety buffer" in news or "1% equity extension" in news, "news MLL buffer not verified")
    _require(
        "maximum of 3 times" in news or "maximum of three times" in news,
        "news MLL buffer usage cap not verified",
    )

    observed_at = datetime.now(UTC).isoformat()
    payload: dict[str, object] = {
        "schema": _SCHEMA,
        "observed_at": observed_at,
        "provider_rules_fingerprint": expected_provider_hash,
        "facts": {
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
        },
        "sources": {
            name: {
                "url": url,
                "sha256": hashlib.sha256(sources[name]).hexdigest(),
            }
            for name, url in urls.items()
        },
    }
    _atomic_json(root / "var/fundednext/provider-rules-refresh.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    payload = refresh(Path(args.root).resolve())
    facts = payload["facts"]
    assert isinstance(facts, dict)
    print(
        json.dumps(
            {
                "ok": True,
                "maximum_loss_fraction": facts["maximum_loss_fraction"],
                "cumulative_open_risk_fraction": facts[
                    "cumulative_open_risk_fraction"
                ],
                "source_count": len(payload["sources"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
