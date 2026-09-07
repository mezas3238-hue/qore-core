"""Lane 5 adversarial conformance for the Trader cognitive wrapper (#492).

This file asserts the cognitive layer is a CHANNEL (never a reasoning tier and
never a source of authority) and that its routing is decided ONLY from the typed
``TraderCognitiveSituation``. It is self-contained: it imports only from the
cognitive/contracts modules and the standard library, never relative modules.
"""

from __future__ import annotations

import inspect
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
    TraderCognitiveRoute,
    TraderCognitiveRouting,
    TraderCognitiveSituation,
    TraderCognitiveValidationError,
    TraderVoiceChannel,
    build_trader_cognitive_opinion,
    build_trader_cognitive_receipt,
    compute_trader_cognitive_receipt_fingerprint,
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

_CODE = DemoTradingTraderCode("vt-01")
_VER = DemoTradingTraderVersion("v1")
_CFG = DemoTradingConfigFingerprint("a" * 64)
_MID = DemoTradingMethodologyId("ny-precision-core")
_MVER = DemoTradingMethodologyVersion("v1")
_MFP = compute_trader_methodology_fingerprint(
    methodology_id=_MID,
    methodology_version=_MVER,
    timeframe="M5",
    session="ny-am-session",
    ruleset="r",
)
_OUT = DemoTradingConfigFingerprint("b" * 64)
_SUP = (
    DemoTradingEvidenceRef("qore:demo:ev:1"),
    DemoTradingEvidenceRef("qore:demo:ev:2"),
)
_USED = (DemoTradingEvidenceRef("qore:demo:ev:1"),)

_TS = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)
_TS_LATER = datetime(2026, 1, 6, 12, 0, 1, tzinfo=UTC)


def _op(
    situation: TraderCognitiveSituation,
    *,
    used: tuple[DemoTradingEvidenceRef, ...] = _USED,
    supplied: tuple[DemoTradingEvidenceRef, ...] = _SUP,
) -> TraderCognitiveOpinion:
    return build_trader_cognitive_opinion(
        trader_code=_CODE,
        version=_VER,
        config_fingerprint=_CFG,
        methodology_id=_MID,
        methodology_version=_MVER,
        methodology_fingerprint=_MFP,
        deterministic_output_fingerprint=_OUT,
        supplied_evidence_refs=supplied,
        evidence_refs=used,
        situation=situation,
        provenance=TraderCognitiveProvenance.INDEPENDENT,
        thesis="t",
        invalidation="i",
        limitations=("l",),
        voiced_at=_TS,
    )


def test_voice_text_ui_identical_routing_for_ambiguous_and_conflict() -> None:
    # Voice, text, and UI are channels, not reasoning tiers: speaking must never
    # force HIGH/MAX beyond the typed situation's governed route.
    for mode in (TraderCognitiveMode.AMBIGUOUS, TraderCognitiveMode.CONFLICT):
        situation = TraderCognitiveSituation(mode)
        voice = TraderVoiceChannel("voice").route(situation)
        text = TraderVoiceChannel("text").route(situation)
        ui = TraderVoiceChannel("ui").route(situation)
        governed = route_trader_cognition(situation)
        assert voice == text == ui == governed
        assert voice.routing is text.routing is ui.routing is governed.routing
        assert voice.model == text.model == ui.model == governed.model
        assert voice.effort == text.effort == ui.effort == governed.effort
        assert voice.destination is text.destination is ui.destination is governed.destination


def test_prompt_words_cannot_escalate_and_situation_has_no_text_field() -> None:
    # Routing is typed-only: "urgent"/"MAX"/"controversy"/"escalate" cannot raise
    # a ROUTINE situation above TERRA_MEDIUM.
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    for _word in ("urgent", "MAX", "controversy", "escalate"):
        route = route_trader_cognition(situation)
        assert route.routing is TraderCognitiveRouting.TERRA_MEDIUM
        assert route.model == TERRA_MODEL
        assert route.effort == "medium"
        assert route.destination is TraderCognitiveDestination.TRADER_LOCAL

    # The situation cannot even carry text: it exposes only a `mode` field.
    assert {field.name for field in fields(TraderCognitiveSituation)} == {"mode"}
    assert set(inspect.signature(TraderCognitiveSituation).parameters) == {"mode"}


def test_evidence_subset_enforced() -> None:
    outside = (
        DemoTradingEvidenceRef("qore:demo:ev:1"),
        DemoTradingEvidenceRef("qore:demo:ev:9"),
    )
    with pytest.raises(TraderCognitiveValidationError):
        _op(
            situation=TraderCognitiveSituation(TraderCognitiveMode.ROUTINE),
            used=outside,
        )


def test_receipt_effort_mismatch_rejected() -> None:
    # A receipt whose effort is "max" for a ROUTINE situation must not be
    # attachable to an admitted opinion.
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    good = _op(situation=situation)
    forged = TraderCognitiveReceipt(
        routing=TraderCognitiveRouting.TERRA_MEDIUM,
        model=TERRA_MODEL,
        effort="max",
        fingerprint=good.receipt.fingerprint,
    )
    with pytest.raises(TraderCognitiveValidationError):
        TraderCognitiveOpinion(
            trader_code=_CODE,
            version=_VER,
            config_fingerprint=_CFG,
            methodology_id=_MID,
            methodology_version=_MVER,
            methodology_fingerprint=_MFP,
            deterministic_output_fingerprint=_OUT,
            supplied_evidence_refs=_SUP,
            evidence_refs=_USED,
            situation=situation,
            receipt=forged,
            provenance=TraderCognitiveProvenance.INDEPENDENT,
            thesis="t",
            invalidation="i",
            limitations=("l",),
            voiced_at=_TS,
            opinion_fingerprint=good.opinion_fingerprint,
        )


def test_contradiction_does_not_self_grant() -> None:
    route = route_trader_cognition(
        TraderCognitiveSituation(TraderCognitiveMode.CONTRADICTION)
    )
    assert route.routing is TraderCognitiveRouting.ESCALATION_REQUEST
    assert route.model is None
    assert route.effort is None
    assert route.destination is TraderCognitiveDestination.GOVERNED_ESCALATION


def test_route_rejects_reflectively_corrupted_mode_member_string() -> None:
    # A frozen situation whose mode is reflectively replaced by a plain string
    # that equals a StrEnum member value must fail closed, never silently
    # self-escalate routing (raw "council-adversarial" must not reach CIBO_MAX).
    for raw in ("routine", "conflict", "council-adversarial"):
        situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
        object.__setattr__(situation, "mode", raw)
        with pytest.raises(TraderCognitiveValidationError):
            route_trader_cognition(situation)


def test_route_rejects_reflectively_corrupted_mode_non_member_string() -> None:
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    object.__setattr__(situation, "mode", "urgent")
    with pytest.raises(TraderCognitiveValidationError):
        route_trader_cognition(situation)


def test_conflict_is_single_cibo_sol_high_not_sol_max_fanout() -> None:
    route = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.CONFLICT))
    # Exactly one route object, and it is a single Sol/high adjudication — not a
    # fan-out of independent Sol/MAX calls (that is COUNCIL_ADVERSARIAL).
    assert type(route) is TraderCognitiveRoute
    assert route.routing is TraderCognitiveRouting.CIBO_HIGH
    assert route.model == SOL_MODEL
    assert route.effort == "high"
    assert route.destination is TraderCognitiveDestination.CIBO_ADJUDICATION
    assert route.routing.value != TraderCognitiveRouting.CIBO_MAX.value
    assert route.effort != "max"


def test_receipt_fingerprint_replay_safe_and_time_sensitive() -> None:
    route = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.AMBIGUOUS))
    first = build_trader_cognitive_receipt(route=route, issued_at=_TS)
    replay = build_trader_cognitive_receipt(route=route, issued_at=_TS)
    assert first.fingerprint == replay.fingerprint
    later = build_trader_cognitive_receipt(route=route, issued_at=_TS_LATER)
    assert first.fingerprint != later.fingerprint


def test_routing_is_stateless_routine_after_conflict() -> None:
    conflict = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.CONFLICT))
    assert conflict.routing is TraderCognitiveRouting.CIBO_HIGH
    later = route_trader_cognition(TraderCognitiveSituation(TraderCognitiveMode.ROUTINE))
    assert later.routing is TraderCognitiveRouting.TERRA_MEDIUM
    assert later.model == TERRA_MODEL
    assert later.effort == "medium"
    assert later.destination is TraderCognitiveDestination.TRADER_LOCAL


def test_contradiction_opinion_builds_without_forced_consensus() -> None:
    # An unresolved contradiction is admitted as a governed escalation request;
    # it is not coerced into a consensus opinion and grants no model/effort.
    opinion = _op(
        situation=TraderCognitiveSituation(TraderCognitiveMode.CONTRADICTION)
    )
    assert opinion.situation.mode is TraderCognitiveMode.CONTRADICTION
    assert opinion.receipt.routing is TraderCognitiveRouting.ESCALATION_REQUEST
    assert opinion.receipt.model is None
    assert opinion.receipt.effort is None
    governed = route_trader_cognition(opinion.situation)
    assert governed.destination is TraderCognitiveDestination.GOVERNED_ESCALATION


def test_provenance_enum_covers_four_dialogue_values() -> None:
    assert {member.value for member in TraderCognitiveProvenance} == {
        "independent",
        "reply-to-cibo",
        "reply-to-ceo",
        "reply-to-trader",
    }
    assert TraderCognitiveProvenance.INDEPENDENT is TraderCognitiveProvenance("independent")
    assert TraderCognitiveProvenance.REPLY_TO_CIBO is TraderCognitiveProvenance("reply-to-cibo")
    assert TraderCognitiveProvenance.REPLY_TO_CEO is TraderCognitiveProvenance("reply-to-ceo")
    assert TraderCognitiveProvenance.REPLY_TO_TRADER is TraderCognitiveProvenance(
        "reply-to-trader"
    )


def test_opinion_has_no_execution_authority_fields() -> None:
    field_names = {field.name for field in fields(TraderCognitiveOpinion)}
    forbidden = {
        "order",
        "account",
        "quantity",
        "risk_approval",
        "risk",
        "production_authorization",
        "production",
    }
    assert field_names.isdisjoint(forbidden)


def _opinion_with_receipt(receipt: TraderCognitiveReceipt) -> TraderCognitiveOpinion:
    # Build an opinion with a specific (possibly forged) receipt. The receipt
    # fingerprint is re-verified before the opinion fingerprint, so a forged
    # receipt raises even though the opinion fingerprint is a valid typed value.
    return TraderCognitiveOpinion(
        trader_code=_CODE,
        version=_VER,
        config_fingerprint=_CFG,
        methodology_id=_MID,
        methodology_version=_MVER,
        methodology_fingerprint=_MFP,
        deterministic_output_fingerprint=_OUT,
        supplied_evidence_refs=_SUP,
        evidence_refs=_USED,
        situation=TraderCognitiveSituation(TraderCognitiveMode.ROUTINE),
        receipt=receipt,
        provenance=TraderCognitiveProvenance.INDEPENDENT,
        thesis="t",
        invalidation="i",
        limitations=("l",),
        voiced_at=_TS,
        opinion_fingerprint=DemoTradingConfigFingerprint("c" * 64),
    )


def test_opinion_rejects_receipt_with_forged_fingerprint() -> None:
    # A receipt whose fingerprint is not derived from its routing/model/effort
    # and the opinion's voiced_at is tamper-evidently rejected at the boundary.
    forged = TraderCognitiveReceipt(
        routing=TraderCognitiveRouting.TERRA_MEDIUM,
        model=TERRA_MODEL,
        effort="medium",
        fingerprint=DemoTradingConfigFingerprint("0" * 64),
    )
    with pytest.raises(TraderCognitiveValidationError):
        _opinion_with_receipt(forged)


def test_opinion_rejects_receipt_fingerprint_from_different_issued_at() -> None:
    # A receipt fingerprint computed at a DIFFERENT issued_at must not validate
    # against an opinion voiced at _TS (replay-safe, time-bound receipt).
    wrong = compute_trader_cognitive_receipt_fingerprint(
        routing=TraderCognitiveRouting.TERRA_MEDIUM,
        model=TERRA_MODEL,
        effort="medium",
        issued_at=_TS_LATER,
    )
    forged = TraderCognitiveReceipt(
        routing=TraderCognitiveRouting.TERRA_MEDIUM,
        model=TERRA_MODEL,
        effort="medium",
        fingerprint=wrong,
    )
    with pytest.raises(TraderCognitiveValidationError):
        _opinion_with_receipt(forged)


def test_opinion_fingerprint_binds_supplied_evidence_refs() -> None:
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    a = _op(situation=situation, supplied=_SUP)
    b = _op(
        situation=situation,
        supplied=(DemoTradingEvidenceRef("qore:demo:ev:1"),),
    )
    assert a.opinion_fingerprint != b.opinion_fingerprint


def test_opinion_evidence_order_canonicalized_in_logical_values() -> None:
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    used_a = (
        DemoTradingEvidenceRef("qore:demo:ev:1"),
        DemoTradingEvidenceRef("qore:demo:ev:2"),
    )
    used_b = (
        DemoTradingEvidenceRef("qore:demo:ev:2"),
        DemoTradingEvidenceRef("qore:demo:ev:1"),
    )
    a = _op(situation=situation, used=used_a)
    b = _op(situation=situation, used=used_b)
    assert a.logical_values() == b.logical_values()
    assert a.opinion_fingerprint == b.opinion_fingerprint


def test_opinion_rejects_duplicate_supplied_evidence_refs() -> None:
    situation = TraderCognitiveSituation(TraderCognitiveMode.ROUTINE)
    dup = (
        DemoTradingEvidenceRef("qore:demo:ev:1"),
        DemoTradingEvidenceRef("qore:demo:ev:1"),
    )
    with pytest.raises(TraderCognitiveValidationError):
        _op(situation=situation, supplied=dup)
