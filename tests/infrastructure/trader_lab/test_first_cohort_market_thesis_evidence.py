from __future__ import annotations

from copy import deepcopy
from typing import cast

import pytest

from qore.infrastructure.trader_lab.first_cohort_market_thesis_evidence import (
    MarketThesisEvidenceError,
    build_market_thesis_evidence,
)

_TRADERS = ("vt-01", "vt-08", "vt-09", "vt-17", "vt-31")
_CONFIG = "c" * 64
_METHOD = "d" * 64
_ACCOUNT = "a" * 64
_SOFTWARE = "b" * 40


def _story() -> dict[str, object]:
    summaries = []
    packs = []
    for index, code in enumerate(_TRADERS):
        summaries.append(
            {
                "trader_code": code,
                "episode_count": index + 10,
                "family_status": {"direct_stop_episodes": {"status": "READY"}},
                "session_breakdown": {"NEW_YORK": {"entry_count": index + 1}},
                "outside_primary_session_entry_count": 0,
                "forensics_fingerprint": f"{index + 1:064x}",
                "session_intelligence_fingerprint": f"{index + 11:064x}",
            }
        )
        packs.append(
            {
                "source_binding": {
                    "symbol": "US30",
                    "software_sha": _SOFTWARE,
                    "account_fingerprint": _ACCOUNT,
                    "trader_code": code,
                    "config_fingerprint": _CONFIG,
                    "methodology_fingerprint": _METHOD,
                    "execution_period": "M5",
                },
                "forensics_fingerprint": f"{index + 1:064x}",
            }
        )
    return {
        "schema": "qore.trader_lab.first_cohort_market_story_forensics.v1",
        "environment": "demo",
        "research_only": True,
        "read_only": True,
        "execution_authority": False,
        "symbol": "US30",
        "software_sha": _SOFTWARE,
        "account_fingerprint": _ACCOUNT,
        "trader_codes": list(_TRADERS),
        "trader_count": 5,
        "trader_summaries": summaries,
        "trader_story_packs": packs,
        "market_forensics_fingerprint": "e" * 64,
    }


def _profile() -> dict[str, object]:
    return {
        "profile": "production-default",
        "config_fingerprint": _CONFIG,
        "methodology_identity": {
            "methodology_fingerprint": _METHOD,
        },
        "execution_period": "M5",
        "parameters": {"sweep_strength": 2},
        "setup_count": 100,
        "filled_setup_count": 40,
        "unfilled_setup_count": 60,
        "fill_rate": "0.4",
        "max_losing_streak": 8,
        "exit_reason_counts": {"stop": 20, "target": 20},
        "outcomes": {"mean_return": "0.001", "win_rate": "0.5"},
        "by_side": {"long": {"sample_size": 20}, "short": {"sample_size": 20}},
        "by_session": {"ny-am-session": {"sample_size": 40}},
        "by_trend_regime": {"range": {"sample_size": 40}},
        "by_volatility_regime": {"normal": {"sample_size": 40}},
        "by_chronological_quartile": [{"quartile": 1, "sample_size": 10}],
        "close_path_excursions": {"mfe": {"mean": "0.001"}},
        "decision_funnel": {"SETUP": 100},
        "geometry": {"reward_risk_multiple": {"mean": "2"}},
        "execution_model_diagnostics": {"model": "test"},
        "walk_forward_assessment": {
            "config_fingerprint": _CONFIG,
            "in_sample": {"mean_return": "0.001"},
            "in_sample_pass": True,
            "oos": {"mean_return": "0.0005"},
            "oos_pass": True,
            "stressed_oos": {"mean_return": "-0.0001"},
            "stress_pass": False,
        },
        "setup_reason_counts": {"canonical": 100},
        "abstain_reason_counts": {"no_setup": 20},
        "setups": [],
    }


def _characterization() -> dict[str, object]:
    return {
        "schema": "qore.trader_lab.first_cohort_characterization.v1",
        "environment": "demo",
        "read_only": True,
        "symbol": "US30",
        "software_sha": _SOFTWARE,
        "account_fingerprint": _ACCOUNT,
        "holdout_governance": {"state": "consumed_for_research"},
        "results": [
            {
                "trader_code": code,
                "profiles": [_profile()],
            }
            for code in _TRADERS
        ],
    }


def test_market_thesis_evidence_preserves_deep_research_profile() -> None:
    payload = build_market_thesis_evidence(_story(), _characterization())

    assert payload["schema"] == "qore.trader_lab.first_cohort_market_thesis_evidence.v1"
    assert payload["research_only"] is True
    assert payload["execution_authority"] is False
    rows = cast(list[object], payload["trader_evidence"])
    assert len(rows) == 5
    first = cast(dict[str, object], rows[0])
    characterization = cast(dict[str, object], first["characterization"])
    walk_forward = cast(
        dict[str, object],
        characterization["walk_forward_assessment"],
    )
    assert walk_forward["oos_pass"] is True
    assert walk_forward["stress_pass"] is False
    assert "by_side" in characterization
    assert "by_trend_regime" in characterization
    provenance = cast(dict[str, object], first["provenance"])
    assert len(cast(str, provenance["market_story_payload_digest"])) == 64
    assert len(cast(str, provenance["characterization_digest"])) == 64
    assert len(cast(str, first["trader_market_evidence_digest"])) == 64


def test_market_thesis_evidence_fails_closed_on_identity_mismatch() -> None:
    characterization = _characterization()
    results = cast(list[dict[str, object]], characterization["results"])
    profiles = cast(list[dict[str, object]], results[0]["profiles"])
    profiles[0]["config_fingerprint"] = "x" * 64

    with pytest.raises(
        MarketThesisEvidenceError,
        match="vt-01 config fingerprint mismatch",
    ):
        build_market_thesis_evidence(_story(), characterization)


def test_market_thesis_evidence_changes_when_story_payload_changes() -> None:
    story = _story()
    first = build_market_thesis_evidence(story, _characterization())
    mutated = deepcopy(story)
    summaries = cast(list[dict[str, object]], mutated["trader_summaries"])
    summaries[0]["episode_count"] = 999
    second = build_market_thesis_evidence(mutated, _characterization())

    assert (
        first["market_thesis_evidence_fingerprint"]
        != second["market_thesis_evidence_fingerprint"]
    )
