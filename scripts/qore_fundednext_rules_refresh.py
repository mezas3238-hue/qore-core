"""Refresh FundedNext Stellar Instant provider-rule evidence from official sources."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

MLL_URL = "https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts"
EA_URL = "https://help.fundednext.com/en/articles/11641338-can-i-use-ea-in-stellar-instant"
RISK_URL = "https://help.fundednext.com/en/articles/15644011-what-are-the-clarity-cards-and-how-do-they-affect-my-account"
_SCHEMA = "qore.fundednext.provider-rules-refresh.v2"


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
    handle, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
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

    urls = {"mll": MLL_URL, "ea": EA_URL, "risk": RISK_URL}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {name: pool.submit(_fetch, url) for name, url in urls.items()}
        sources = {name: future.result() for name, future in futures.items()}

    mll = _text(sources["mll"])
    ea = _text(sources["ea"])
    risk = _text(sources["risk"])

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
    _require(
        "stellar instant" in risk or "instant account" in risk,
        "risk source no longer identifies Instant account",
    )
    _require(
        "default risk limit is 3%" in risk,
        "3% cumulative open-position Risk Limit not verified",
    )
    _require(
        "cumulative across all open positions" in risk,
        "cumulative open-position risk scope not verified",
    )

    payload: dict[str, object] = {
        "schema": _SCHEMA,
        "provider_rules_fingerprint": expected_provider_hash,
        "facts": {
            "no_daily_loss_limit": True,
            "maximum_loss_fraction": "0.06",
            "trailing_maximum_loss": True,
            "ea_allowed_mt5": True,
            "cumulative_open_risk_fraction": "0.03",
            "cumulative_open_risk_applies": True,
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
                "cumulative_open_risk_fraction": facts["cumulative_open_risk_fraction"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
