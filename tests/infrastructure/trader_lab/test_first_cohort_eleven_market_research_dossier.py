from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import cast

import pytest

from qore.infrastructure.trader_lab.first_cohort_eleven_market_research_dossier import (
    ElevenMarketResearchDossierError,
    build_eleven_market_research_dossiers,
)

_MARKETS = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "AUDUSD",
    "USDCAD",
    "XAUUSD",
    "NAS100",
    "SP500",
    "GBPJPY",
    "AUDJPY",
    "US30",
)
_TRADERS = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _market_package(
    symbol: str,
    *,
    changed_identity: bool = False,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for index, code in enumerate(_TRADERS):
        config = "c" * 64
        if changed_identity and code == "vt-08":
            config = "x" * 64
        row: dict[str, object] = {
            "trader_code": code,
            "identity": {
                "config_fingerprint": config,
                "methodology_fingerprint": f"{index + 1:064x}",
                "execution_period": "M5",
            },
            "story_forensics": {
                "episode_count": 100 + index,
                "family_status": {"direct_stop_episodes": {"status": "READY"}},
                "session_breakdown": {"NEW_YORK": {"entry_count": 10}},
            },
            "characterization": {
                "setup_count": 200,
                "fill_rate": "0.5",
                "by_side": {"long": {"sample_size": 50}},
                "by_trend_regime": {"range": {"sample_size": 50}},
                "walk_forward_assessment": {
                    "oos": {"mean_return": "0.001"},
                    "oos_pass": symbol in {"NAS100", "US30"},
                    "stressed_oos": {"mean_return": "-0.001"},
                    "stress_pass": False,
                },
            },
            "provenance": {
                "market_story_fingerprint": f"story-{symbol.lower()}",
                "market_story_payload_digest": f"story-payload-{symbol.lower()}",
                "characterization_digest": f"char-{symbol.lower()}",
                "production_default_profile_digest": f"profile-{symbol.lower()}",
            },
        }
        row["trader_market_evidence_digest"] = _digest(row)
        rows.append(row)
    payload: dict[str, object] = {
        "schema": "qore.trader_lab.first_cohort_market_thesis_evidence.v1",
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "symbol": symbol,
        "software_sha": f"sha-{symbol.lower()}",
        "account_fingerprint": f"account-{symbol.lower()}",
        "market_story_fingerprint": f"story-{symbol.lower()}",
        "market_story_payload_digest": f"story-payload-{symbol.lower()}",
        "characterization_digest": f"char-{symbol.lower()}",
        "trader_codes": list(_TRADERS),
        "trader_evidence": rows,
    }
    payload["market_thesis_evidence_fingerprint"] = _digest(payload)
    return payload


def test_research_dossiers_group_each_trader_across_exact_eleven_markets() -> None:
    payload = build_eleven_market_research_dossiers(
        [_market_package(symbol) for symbol in _MARKETS]
    )

    assert (
        payload["schema"]
        == "qore.trader_lab.eleven_market_trader_research_dossier_set.v1"
    )
    assert payload["market_count"] == 11
    assert payload["trader_count"] == 5
    dossiers = cast(list[object], payload["dossiers"])
    assert len(dossiers) == 5
    vt08 = cast(dict[str, object], dossiers[1])
    assert vt08["trader_code"] == "vt-08"
    markets = cast(list[object], vt08["markets"])
    assert [cast(dict[str, object], row)["symbol"] for row in markets] == list(
        _MARKETS
    )
    nas100 = cast(dict[str, object], markets[6])
    summary = cast(dict[str, object], nas100["summary"])
    characterization = cast(dict[str, object], summary["characterization"])
    walk_forward = cast(
        dict[str, object],
        characterization["walk_forward_assessment"],
    )
    assert walk_forward["oos_pass"] is True
    assert walk_forward["stress_pass"] is False
    assert len(cast(str, nas100["evidence_digest"])) == 64


def test_research_dossier_rejects_cross_market_identity_drift() -> None:
    packages = [_market_package(symbol) for symbol in _MARKETS]
    packages[-1] = _market_package("US30", changed_identity=True)

    with pytest.raises(
        ElevenMarketResearchDossierError,
        match="vt-08 changes config, methodology, or timeframe",
    ):
        build_eleven_market_research_dossiers(packages)


def test_research_dossier_rejects_tampered_market_evidence() -> None:
    packages = [_market_package(symbol) for symbol in _MARKETS]
    tampered = deepcopy(packages[0])
    rows = cast(list[dict[str, object]], tampered["trader_evidence"])
    characterization = cast(dict[str, object], rows[0]["characterization"])
    characterization["fill_rate"] = "0.999"
    packages[0] = tampered

    with pytest.raises(
        ElevenMarketResearchDossierError,
        match="market thesis evidence fingerprint mismatch",
    ):
        build_eleven_market_research_dossiers(packages)
