from __future__ import annotations

from copy import deepcopy
from typing import cast

import pytest

from qore.infrastructure.trader_lab.first_cohort_eleven_market_dossier import (
    ElevenMarketDossierError,
    build_eleven_market_dossiers,
)
from qore.infrastructure.trader_lab.story_forensics_eleven_market_thesis import (
    build_eleven_market_thesis_panel,
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


def _market_payload(symbol: str) -> dict[str, object]:
    summaries: list[dict[str, object]] = []
    packs: list[dict[str, object]] = []
    for index, trader_code in enumerate(_TRADERS):
        summaries.append(
            {
                "trader_code": trader_code,
                "episode_count": index + 10,
                "family_status": {"canonical_winners": "READY"},
                "session_breakdown": {"NEW_YORK": {"entry_count": index + 1}},
                "outside_primary_session_entry_count": 0,
                "forensics_fingerprint": f"forensics-{trader_code}-{symbol}",
                "session_intelligence_fingerprint": f"session-{trader_code}-{symbol}",
            }
        )
        packs.append(
            {
                "source_binding": {
                    "symbol": symbol,
                    "software_sha": f"sha-{symbol.lower()}",
                    "account_fingerprint": "demo-account",
                    "trader_code": trader_code,
                    "config_fingerprint": f"config-{trader_code}",
                    "methodology_fingerprint": f"method-{trader_code}",
                    "execution_period": "M15" if trader_code == "vt-09" else "M5",
                },
                "forensics_fingerprint": f"forensics-{trader_code}-{symbol}",
            }
        )
    return {
        "schema": "qore.trader_lab.first_cohort_market_story_forensics.v1",
        "research_only": True,
        "execution_authority": False,
        "symbol": symbol,
        "market_forensics_fingerprint": f"market-{symbol.lower()}",
        "trader_summaries": summaries,
        "trader_story_packs": packs,
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
    first_pack = packs[0]
    binding = cast(dict[str, object], first_pack["source_binding"])
    binding["methodology_fingerprint"] = "different-methodology"
    payloads[-1] = changed

    with pytest.raises(ElevenMarketDossierError, match="changes config, methodology, or timeframe"):
        build_eleven_market_dossiers(payloads)


def test_rejects_duplicate_market_even_when_count_is_eleven() -> None:
    payloads = _eleven()
    payloads[-1] = _market_payload("EURUSD")

    with pytest.raises(ElevenMarketDossierError, match="duplicate market"):
        build_eleven_market_dossiers(payloads)
