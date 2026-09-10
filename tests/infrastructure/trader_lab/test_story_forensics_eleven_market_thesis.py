from __future__ import annotations

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


def _dossier() -> dict[str, object]:
    return {
        "schema": "qore.trader_lab.eleven_market_trader_dossier.v1",
        "research_only": True,
        "execution_authority": False,
        "trader_code": "vt-08",
        "markets": [
            {
                "symbol": symbol,
                "evidence_ready": True,
                "evidence_digest": f"digest-{symbol.lower()}",
                "summary": {
                    "sample_size": index + 1,
                    "session_signal": "NEW_YORK" if symbol == "US30" else "MIXED",
                },
            }
            for index, symbol in enumerate(_MARKETS)
        ],
    }


def _assessment(
    panel: dict[str, object],
    *,
    role: ReviewRole,
    verdict: VerdictFamily = VerdictFamily.SPECIALIST,
) -> dict[str, object]:
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
            symbol: [f"{symbol} was explicitly reviewed in the frozen dossier."]
            for symbol in _MARKETS
        },
        "causal_hypothesis": "Edge depends on market-specific context alignment.",
        "counterexample_or_falsifier": (
            "Fresh evidence shows comparable robust expectancy across most markets."
        ),
        "confidence": "medium",
        "fresh_holdout_required_for_changes": True,
    }


def test_panel_requires_exact_eleven_market_universe() -> None:
    dossier = _dossier()
    markets = cast(list[dict[str, object]], dossier["markets"])
    markets.pop()

    with pytest.raises(ElevenMarketThesisError, match="exactly eleven markets"):
        build_eleven_market_thesis_panel(dossier)


def test_machine_review_packet_contains_no_peer_conclusions() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    packet = reviewer_packet(panel, role=ReviewRole.HARNESS)

    assert packet["mode"] == "independent_first_pass"
    assert "sealed_machine_reviews" not in packet
    assert packet["dossier_digest"] == panel["dossier_digest"]


def test_assessment_must_address_every_market() -> None:
    panel = build_eleven_market_thesis_panel(_dossier())
    assessment = _assessment(panel, role=ReviewRole.HARNESS)
    evidence = cast(dict[str, list[str]], assessment["evidence_by_market"])
    evidence.pop("US30")

    with pytest.raises(ElevenMarketThesisError, match="all eleven markets"):
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
