from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import cast

import pytest

from qore.infrastructure.trader_lab.first_cohort_eleven_market_dossier import (
    ElevenMarketDossierError,
    build_eleven_market_dossiers,
)
from qore.infrastructure.trader_lab.story_forensics_eleven_market_thesis import (
    build_eleven_market_thesis_panel,
)

_MARKET_SCHEMA = "qore.trader_lab.first_cohort_market_story_forensics.v1"
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
    material = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return sha256(material.encode("utf-8")).hexdigest()


def _market_payload(symbol: str) -> dict[str, object]:
    software_sha = f"sha-{symbol.lower()}"
    account_fingerprint = "demo-account"
    summaries: list[dict[str, object]] = []
    packs: list[dict[str, object]] = []
    fingerprint_rows: list[dict[str, object]] = []
    for index, trader_code in enumerate(_TRADERS):
        forensics_fingerprint = f"forensics-{trader_code}-{symbol}"
        session_fingerprint = f"session-{trader_code}-{symbol}"
        summaries.append(
            {
                "trader_code": trader_code,
                "episode_count": index + 10,
                "family_status": {"canonical_winners": "READY"},
                "session_breakdown": {"NEW_YORK": {"entry_count": index + 1}},
                "outside_primary_session_entry_count": 0,
                "forensics_fingerprint": forensics_fingerprint,
                "session_intelligence_fingerprint": session_fingerprint,
            }
        )
        packs.append(
            {
                "source_binding": {
                    "symbol": symbol,
                    "software_sha": software_sha,
                    "account_fingerprint": account_fingerprint,
                    "trader_code": trader_code,
                    "config_fingerprint": f"config-{trader_code}",
                    "methodology_fingerprint": f"method-{trader_code}",
                    "execution_period": "M15" if trader_code == "vt-09" else "M5",
                },
                "forensics_fingerprint": forensics_fingerprint,
            }
        )
        fingerprint_rows.append(
            {
                "trader_code": trader_code,
                "forensics_fingerprint": forensics_fingerprint,
                "session_intelligence_fingerprint": session_fingerprint,
            }
        )
    return {
        "schema": _MARKET_SCHEMA,
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "symbol": symbol,
        "software_sha": software_sha,
        "account_fingerprint": account_fingerprint,
        "trader_codes": list(_TRADERS),
        "trader_count": len(_TRADERS),
        "session_groups": ["ASIA", "LONDON", "NEW_YORK"],
        "trader_summaries": summaries,
        "trader_story_packs": packs,
        "market_forensics_fingerprint": _digest(
            {
                "schema": _MARKET_SCHEMA,
                "symbol": symbol,
                "software_sha": software_sha,
                "traders": fingerprint_rows,
            }
        ),
    }


def _eleven() -> list[dict[str, object]]:
    return [_market_payload(symbol) for symbol in _MARKETS]


def test_builds_five_frozen_dossiers_each_covering_exact_eleven_markets() -> None:
    result = build_eleven_market_dossiers(_eleven())

    assert result["market_count"] == 11
    assert result["trader_count"] == 5
    assert result["execution_authority"] is False
    dossiers = cast(list[object], result["dossiers"])
    assert len(dossiers) == 5

    for item in dossiers:
        dossier = cast(dict[str, object], item)
        markets = cast(list[dict[str, object]], dossier["markets"])
        assert [row["symbol"] for row in markets] == list(_MARKETS)
        assert all(row["evidence_ready"] is True for row in markets)
        assert all(len(cast(str, row["evidence_digest"])) == 64 for row in markets)
        panel = build_eleven_market_thesis_panel(dossier)
        assert panel["trader_code"] == dossier["trader_code"]


def test_dossier_is_deterministic() -> None:
    first = build_eleven_market_dossiers(_eleven())
    second = build_eleven_market_dossiers(_eleven())

    assert first == second
    assert len(cast(str, first["dossier_set_fingerprint"])) == 64


def test_rejects_missing_market_instead_of_generalizing_from_ten() -> None:
    payloads = _eleven()
    payloads.pop()

    with pytest.raises(ElevenMarketDossierError, match="exactly eleven"):
        build_eleven_market_dossiers(payloads)


def test_rejects_cross_market_methodology_contamination() -> None:
    payloads = _eleven()
    changed = deepcopy(payloads[-1])
    packs = cast(list[dict[str, object]], changed["trader_story_packs"])
    binding = cast(dict[str, object], packs[0]["source_binding"])
    binding["methodology_fingerprint"] = "different-methodology"
    payloads[-1] = changed

    with pytest.raises(ElevenMarketDossierError, match="changes config, methodology, or timeframe"):
        build_eleven_market_dossiers(payloads)


def test_rejects_duplicate_market_even_when_count_is_eleven() -> None:
    payloads = _eleven()
    payloads[-1] = _market_payload("EURUSD")

    with pytest.raises(ElevenMarketDossierError, match="duplicate market"):
        build_eleven_market_dossiers(payloads)


def test_rejects_tampered_summary_forensics_fingerprint() -> None:
    payloads = _eleven()
    summaries = cast(list[dict[str, object]], payloads[0]["trader_summaries"])
    summaries[0]["forensics_fingerprint"] = "tampered"

    with pytest.raises(ElevenMarketDossierError, match="summary/story forensics fingerprint mismatch"):
        build_eleven_market_dossiers(payloads)


def test_rejects_story_pack_software_sha_different_from_market_package() -> None:
    payloads = _eleven()
    packs = cast(list[dict[str, object]], payloads[0]["trader_story_packs"])
    binding = cast(dict[str, object], packs[0]["source_binding"])
    binding["software_sha"] = "tampered-sha"

    with pytest.raises(ElevenMarketDossierError, match="story pack software SHA mismatch"):
        build_eleven_market_dossiers(payloads)


def test_rejects_tampered_market_fingerprint() -> None:
    payloads = _eleven()
    payloads[0]["market_forensics_fingerprint"] = "tampered"

    with pytest.raises(ElevenMarketDossierError, match="market forensics fingerprint mismatch"):
        build_eleven_market_dossiers(payloads)
