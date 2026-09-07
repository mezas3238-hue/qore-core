"""Adversarial + normal tests for the governed Trader cognitive wrapper (#492)."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime

import pytest

from qore.infrastructure.traders.cognitive import (
    SOL_MODEL,
    TERRA_MODEL,
    TraderCognitiveDestination,
    TraderCognitiveMode,
    TraderCognitiveOpinion,
    TraderCognitiveProvenance,
    TraderCognitiveReceipt,
    TraderCognitiveRouting,
    TraderCognitiveSituation,
    TraderCognitiveValidationError,
    TraderVoiceChannel,
    build_trader_cognitive_opinion,
    build_trader_cognitive_receipt,
    route_trader_cognition,
)
from qore.infrastructure.traders.contracts import (
    DemoTradingConfigFingerprint,
    DemoTradingEvidenceRef,
    DemoTradingMethodologyId,
    DemoTradingMethodologyVersion,
    DemoTradingTraderCode,
    DemoTradingTraderVersion,
    compute_trader_methodology_fingerprint,
)

_PROCESS = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)

_CODE = DemoTradingTraderCode("vt-01")
_VERSION = DemoTradingTraderVersion("v1")
_CONFIG = DemoTradingConfigFingerprint("a" * 64)
_MID = DemoTradingMethodologyId("ny-precision-core")
_MVER = DemoTradingMethodologyVersion("v1")
_MFP = compute_trader_methodology_fingerprint(
    methodology_id=_MID,
    methodology_version=_MVER,
    timeframe="M5",
    session="ny-am-session",
    ruleset="rule",
)
_OUT = DemoTradingConfigFingerprint("b" * 64)
_SUPPLIED = (DemoTradingEvidenceRef("qore:demo:ev:1"), DemoTradingEvidenceRef("qore:demo:ev:2"))
_USED = (DemoTradingEvidenceRef("qore:demo:ev:1"),)


def _opinion(
    *,
    situation: TraderCognitiveSituation,
    used: tuple[DemoTradingEvidenceRef, ...] = _USED,
    supplied: tuple[DemoTradingEvidenceRef, ...] = _SUPPLIED,
) -> TraderCognitiveOpinion:
    return build_trader_cognitive_opinion(
        trader_code=_CODE,
        version=_VERSION,
        config_fingerprint=_CONFIG,
        methodology_id=_MID,
        methodology_version=_MVER,
        methodology_fingerprint=_MFP,
        deterministic_output_fingerprint=_OUT,
        supplied_evidence_refs=supplied,
        evidence_refs=used,
        situation=situation,
        provenance=TraderCognitiveProvenance.INDEPENDENT,
        thesis="the trader sees an FVG in the reversal direction",
        invalidation="below the swept level",
        limitations=("no-order-authority",),
        voiced_at=_PROCESS,
    )


def test_routine_routes_terra_medium() -> None:
    route = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.ROUTINE))
    assert route.routing is TraderCognitiveRouting.TERRA_MEDIUM
    assert route.model == TERRA_MODEL
    assert route.effort == "medium"
    assert route.destination is TraderCognitiveDestination.TRADER_LOCAL


def test_ambiguous_routes_terra_high() -> None:
    route = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.AMBIGUOUS))
    assert route.routing is TraderCognitiveRouting.TERRA_HIGH
    assert route.model == TERRA_MODEL
    assert route.effort == "high"


def test_contradiction_routes_governed_escalation_without_self_grant() -> None:
    route = route_trader_cognition(
        TraderCognitiveSituation(TraderCognitiveMode.CONTRADICTION)
    )
    assert route.routing is TraderCognitiveRouting.ESCALATION_REQUEST
    assert route.model is None
    assert route.effort is None
    assert route.destination is TraderCognitiveDestination.GOVERNED_ESCALATION


def test_conflict_routes_cibo_sol_high() -> None:
    route = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.CONFLICT))
    assert route.routing is TraderCognitiveRouting.CIBO_HIGH
    assert route.model == SOL_MODEL
    assert route.effort == "high"
    assert route.destination is TraderCognitiveDestination.CIBO_ADJUDICATION


def test_council_routes_cibo_sol_max() -> None:
    route = route_trader_cognition(
        TraderCognitiveSituation(TraderCognitiveMode.COUNCIL_ADVERSARIAL)
    )
    assert route.routing is TraderCognitiveRouting.CIBO_MAX
    assert route.model == SOL_MODEL
    assert route.effort == "max"


def test_voice_and_text_share_same_routing() -> None:
    situation = TraderCognitiveSituation(TraderCognitiveMode.AMBIGUOUS)
    voice = TraderVoiceChannel("voice").route(situation)
    text = TraderVoiceChannel("text").route(situation)
    ui = TraderVoiceChannel("ui").route(situation)
    assert voice.routing is text.routing is ui.routing
    assert voice.model == text.model == ui.model == TERRA_MODEL
    assert voice.effort == text.effort == ui.effort == "high"


def test_prompt_words_do_not_self_escalate() -> None:
    # Routing is decided ONLY from the typed situation. The situation has no text
    # field, so words like "urgent", "MAX", "controversy" cannot influence it.
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    for _prompt in ("urgent please escalate", "use MAX", "serious controversy"):
        route = route_trader_cognition(situation)
        assert route.routing is TraderCognitiveRouting.TERRA_MEDIUM


def test_unrelated_later_episode_deescalates() -> None:
    # A prior conflict episode does not inherit escalation into a later routine one.
    route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.CONFLICT))
    later = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.ROUTINE))
    assert later.routing is TraderCognitiveRouting.TERRA_MEDIUM


def test_receipt_matches_governed_route() -> None:
    route = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.ROUTINE))
    receipt = build_trader_cognitive_receipt(route=route, issued_at=_PROCESS)
    assert receipt.model == TERRA_MODEL
    assert receipt.effort == "medium"
    assert receipt.routing is TraderCognitiveRouting.TERRA_MEDIUM


def test_opinion_rejects_evidence_outside_supplied_set() -> None:
    with pytest.raises(TraderCognitiveValidationError):
        _opinion(
            situation=TraderCognitiveSituation(TraderCognitiveMode.ROUTINE),
            used=(DemoTradingEvidenceRef("qore:demo:ev:9"),),
        )


def test_opinion_receipt_mismatch_rejected() -> None:
    # A receipt with a wrong effort must not launder into an admitted opinion.
    opinion = _opinion(situation=TraderCognitiveSituation(TraderCognitiveMode.ROUTINE))
    wrong_receipt = TraderCognitiveReceipt(
        routing=TraderCognitiveRouting.TERRA_MEDIUM,
        model=TERRA_MODEL,
        effort="max",
        fingerprint=opinion.receipt.fingerprint,
    )
    with pytest.raises(TraderCognitiveValidationError):
        TraderCognitiveOpinion(
            trader_code=_CODE,
            version=_VERSION,
            config_fingerprint=_CONFIG,
            methodology_id=_MID,
            methodology_version=_MVER,
            methodology_fingerprint=_MFP,
            deterministic_output_fingerprint=_OUT,
            supplied_evidence_refs=_SUPPLIED,
            evidence_refs=_USED,
            situation=TraderCognitiveSituation(TraderCognitiveMode.ROUTINE),
            receipt=wrong_receipt,
            provenance=TraderCognitiveProvenance.INDEPENDENT,
            thesis="thesis",
            invalidation="invalidation",
            limitations=("limitation",),
            voiced_at=_PROCESS,
            opinion_fingerprint=opinion.opinion_fingerprint,
        )


def test_opinion_carries_no_execution_authority_fields() -> None:
    field_names = {field.name for field in fields(TraderCognitiveOpinion)}
    forbidden = {
        "order",
        "account",
        "quantity",
        "risk_approval",
        "production_authorization",
        "provider_order",
    }
    assert field_names.isdisjoint(forbidden)


def test_opinion_replay_safe_identical() -> None:
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    first = _opinion(situation=situation)
    second = _opinion(situation=situation)
    assert first.opinion_fingerprint == second.opinion_fingerprint
    assert first.logical_values() == second.logical_values()


def test_opinion_fingerprint_changes_with_thesis() -> None:
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    first = _opinion(situation=situation)
    changed = build_trader_cognitive_opinion(
        trader_code=_CODE,
        version=_VERSION,
        config_fingerprint=_CONFIG,
        methodology_id=_MID,
        methodology_version=_MVER,
        methodology_fingerprint=_MFP,
        deterministic_output_fingerprint=_OUT,
        supplied_evidence_refs=_SUPPLIED,
        evidence_refs=_USED,
        situation=situation,
        provenance=TraderCognitiveProvenance.INDEPENDENT,
        thesis="a different thesis",
        invalidation="below the swept level",
        limitations=("no-order-authority",),
        voiced_at=_PROCESS,
    )
    assert first.opinion_fingerprint != changed.opinion_fingerprint
