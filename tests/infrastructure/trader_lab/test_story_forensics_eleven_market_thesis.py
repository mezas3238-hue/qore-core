from __future__ import annotations

import json
from hashlib import sha256
from typing import cast

import pytest

from qore.infrastructure.trader_lab.story_forensics_eleven_market_thesis import (
    ElevenMarketThesisError,
    VerdictFamily,
    build_eleven_market_thesis_panel,
    reviewer_packet,
    seal_assessment,
    synthesize_eleven_market_thesis,
)
from qore.infrastructure.trader_lab.story_forensics_review_panel import ReviewRole

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


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _dossier() -> dict[str, object]:
    dossier: dict[str, object] = {
        "schema": "qore.trader_lab.eleven_market_trader_research_dossier.v1",
        "research_only": True,
        "execution_authority": False,
        "trader_code": "vt-08",
        "identity": {
            "config_fingerprint": "c" * 64,
            "methodology_fingerprint": "d" * 64,
            "execution_period": "M5",
        },
        "markets": [
            {
                "symbol": symbol,
                "evidence_ready": True,
                "evidence_digest": f"digest-{symbol.lower()}",
                "summary": {
                    "story_forensics": {
                        "episode_count": index + 1,
                        "session_breakdown": {
                            "NEW_YORK": {
                                "entry_count": index + 1,
                            }
                        },
                    },
                    "characterization": {
                        "setup_count": 100 + index,
                        "fill_rate": "0.5",
                        "by_side": {
                            "long": {"sample_size": 10 + index},
                            "short": {"sample_size": 8 + index},
                        },
                        "by_trend_regime": {
                            "range": {"sample_size": 9 + index},
                        },
                        "walk_forward_assessment": {
                            "oos": {"mean_return": "0.001"},
                            "oos_pass": symbol in {"NAS100", "US30"},
                            "stressed_oos": {"mean_return": "-0.001"},
                            "stress_pass": False,
                        },
                    },
                    "provenance": {
                        "market_story_payload_digest": f"story-{symbol.lower()}",
                        "characterization_digest": f"char-{symbol.lower()}",
                    },
                },
            }
            for index, symbol in enumerate(_MARKETS)
        ],
    }
    dossier["dossier_fingerprint"] = _digest(dossier)
    return dossier


def _assessment(
    panel: dict[str, object],
    *,
    role: ReviewRole,
    verdict: VerdictFamily = VerdictFamily.SPECIALIST,
) -> dict[str, object]:
    evidence_index = cast(dict[str, str], panel["market_evidence_index"])
    return {
        "dossier_digest": panel["dossier_digest"],
        "role": role.value,
        "verdict_family": verdict.value,
        "central_conclusion": "The Trader behaves as a specialist, not a universal model.",
        "rationale": ["Cross-market behavior differs materially by market and session."],
        "common_patterns": ["Performance is concentrated in narrow contexts."],
        "material_exceptions": ["US30 behaves differently from weak markets."],
        "strengths_to_preserve": ["Preserve narrow high-quality context selection."],
        "degradation_risks": ["Broadening the operating envelope may dilute edge."],
        "evidence_by_market": {
            symbol: {
                "evidence_digest": evidence_index[symbol],
                "findings": [
                    f"{symbol} was explicitly reviewed in the frozen research dossier."
                ],
            }
            for symbol in _MARKETS
        },
        "causal_hypothesis": "Edge depends on market-specific context alignment.",
        "counterexample_or_falsifier": (
            "Fresh evidence shows comparable robust expectancy across most markets."
        ),
        "confidence": "medium",
        "fresh_holdout_required_for_changes": True,
    }


def test_panel_rejects_shallow_dossier_schema() -> None:
    dossier = _dossier()
    dossier["schema"] = "qore.trader_lab.eleven_market_trader_dossier.v1"

    with pytest.raises(ElevenMarketThesisError, match="research dossier v1"):
        build_eleven_market_thesis_panel(dossier)


def test_panel_requires_exact_eleven_market_universe() -> None:
    dossier = _dossier()
    markets = cast(list[dict[str, object]], dossier["markets"])
    markets.pop()

    with pytest.raises(ElevenMarketThesisError, match="exactly eleven markets"):
        build_eleven_market_thesis_panel(dossier)


def test_panel_rejects_tampered_research_dossier_fingerprint() -> None:
    dossier = _dossier()
    markets = cast(list[dict[str, object]], dossier["markets"])
    summary = cast(dict[str, object], markets[0]["summary"])
    characterization = cast(dict[str, object], summary["characterization"])
    characterization["fill_rate"] = "0.999"

    with pytest.raises(ElevenMarketThesisError, match="research dossier fingerprint mismatch"):
        build_eleven_market_thesis_panel(dossier)


def test_machine_review_packet_contains_no_peer_conclusions() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    packet = reviewer_packet(panel, role=ReviewRole.HARNESS)

    assert packet["mode"] == "independent_first_pass"
    assert "sealed_machine_reviews" not in packet
    assert packet["dossier_digest"] == panel["dossier_digest"]
    assert packet["market_evidence_index"] == panel["market_evidence_index"]
    required = cast(dict[str, object], packet["required_output"])
    assert "verdict_family" in required
    assert "central_verdict" not in required
    evidence_contract = cast(
        dict[str, dict[str, object]],
        required["evidence_by_market"],
    )
    assert evidence_contract["US30"]["evidence_digest"] == "digest-us30"


def test_assessment_must_address_every_market() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    assessment = _assessment(panel, role=ReviewRole.HARNESS)
    evidence = cast(dict[str, dict[str, object]], assessment["evidence_by_market"])
    evidence.pop("US30")

    with pytest.raises(ElevenMarketThesisError, match="all eleven markets"):
        seal_assessment(panel, assessment=assessment)


def test_assessment_market_evidence_digest_must_match_frozen_panel() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    assessment = _assessment(panel, role=ReviewRole.HARNESS)
    evidence = cast(dict[str, dict[str, object]], assessment["evidence_by_market"])
    evidence["US30"]["evidence_digest"] = "digest-from-different-evidence"

    with pytest.raises(ElevenMarketThesisError, match="US30 evidence digest mismatch"):
        seal_assessment(panel, assessment=assessment)


def test_human_is_blocked_until_four_independent_machine_reviews_are_sealed() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())

    with pytest.raises(ElevenMarketThesisError, match="human review is blocked"):
        reviewer_packet(panel, role=ReviewRole.HUMAN_OWNER)

    for role in (
        ReviewRole.HARNESS,
        ReviewRole.EXPERT,
        ReviewRole.WORK,
        ReviewRole.ARCHITECT,
    ):
        panel = seal_assessment(panel, assessment=_assessment(panel, role=role))

    packet = reviewer_packet(panel, role=ReviewRole.HUMAN_OWNER)
    sealed = cast(dict[str, object], packet["sealed_machine_reviews"])
    assert set(sealed) == {"harness", "expert", "work", "architect"}


def test_synthesis_retains_disagreement_and_has_no_execution_authority() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    verdicts = {
        ReviewRole.HARNESS: VerdictFamily.SPECIALIST,
        ReviewRole.EXPERT: VerdictFamily.MARKET_DEPENDENT,
        ReviewRole.WORK: VerdictFamily.SESSION_DEPENDENT,
        ReviewRole.ARCHITECT: VerdictFamily.SPECIALIST,
    }
    for role, verdict in verdicts.items():
        panel = seal_assessment(
            panel,
            assessment=_assessment(panel, role=role, verdict=verdict),
        )
    panel = seal_assessment(
        panel,
        assessment=_assessment(
            panel,
            role=ReviewRole.HUMAN_OWNER,
            verdict=VerdictFamily.MIXED_UNRESOLVED,
        ),
    )

    synthesis = synthesize_eleven_market_thesis(panel)

    assert synthesis["state"] == "RESEARCH_SYNTHESIS_ONLY"
    assert synthesis["execution_authority"] is False
    assert synthesis["majority_vote_is_truth"] is False
    assert synthesis["disagreement_retained"] is True
    counts = cast(dict[str, int], synthesis["verdict_counts"])
    assert counts["SPECIALIST"] == 2
    assert counts["MIXED_UNRESOLVED"] == 1


def test_reviewer_packet_rejects_frozen_dossier_mutation_after_panel_creation() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    frozen = cast(dict[str, object], panel["frozen_dossier"])
    markets = cast(list[dict[str, object]], frozen["markets"])
    markets[0]["evidence_digest"] = "tampered-after-freeze"

    with pytest.raises(ElevenMarketThesisError, match="research dossier fingerprint mismatch"):
        reviewer_packet(panel, role=ReviewRole.HARNESS)


def test_seal_rejects_evidence_index_mutation_after_panel_creation() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    assessment = _assessment(panel, role=ReviewRole.HARNESS)
    evidence_index = cast(dict[str, str], panel["market_evidence_index"])
    evidence_index["US30"] = "tampered-index"

    with pytest.raises(ElevenMarketThesisError, match="evidence index diverges"):
        seal_assessment(panel, assessment=assessment)


def test_sealed_assessment_digest_is_revalidated_before_synthesis() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    for role in (
        ReviewRole.HARNESS,
        ReviewRole.EXPERT,
        ReviewRole.WORK,
        ReviewRole.ARCHITECT,
    ):
        panel = seal_assessment(panel, assessment=_assessment(panel, role=role))
    panel = seal_assessment(
        panel,
        assessment=_assessment(panel, role=ReviewRole.HUMAN_OWNER),
    )
    lanes = cast(dict[str, object], panel["review_lanes"])
    harness_lane = cast(dict[str, object], lanes["harness"])
    harness_assessment = cast(dict[str, object], harness_lane["assessment"])
    harness_assessment["central_conclusion"] = "tampered after sealing"

    with pytest.raises(ElevenMarketThesisError, match="sealed assessment digest mismatch"):
        synthesize_eleven_market_thesis(panel)


def test_machine_assessment_rejects_peer_material_outside_first_pass_contract() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    assessment = _assessment(panel, role=ReviewRole.HARNESS)
    assessment["sealed_machine_reviews"] = {"expert": "must not be embedded"}

    with pytest.raises(ElevenMarketThesisError, match="assessment shape"):
        seal_assessment(panel, assessment=assessment)
