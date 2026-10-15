"""V3 seal adversaries: unchanged historical M1, transactional WAIT/REJECT."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from scripts import vt31_m0m4_continuous_tape_seal_cog_v3_20261015 as v3
from scripts.vt31_m0_m4_context_memory_cog_candidate_20261015 import (
    VT31M0M4CognitiveCandidate,
)
from scripts.vt31_m4_ob_breaker_author_evidence_gate_20261015 import (
    PROFILE,
    Candle,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)


def _bar(at, *, side: Side, idx: int) -> M1Bar:
    if side is Side.LONG:
        vals = (
            ("104", "106", "100", "103"),
            ("103", "107", "101", "105"),
            ("105", "107", "102", "104"),
            ("104", "106", "100", "102"),
        )[idx]
    else:
        vals = (
            ("98", "101", "96", "99"),
            ("99", "102", "95", "97"),
            ("97", "101", "95", "98"),
            ("98", "103", "96", "100"),
        )[idx]
    return M1Bar(
        opened_at=at + timedelta(minutes=idx),
        closed_at=at + timedelta(minutes=idx + 1),
        open=Decimal(vals[0]),
        high=Decimal(vals[1]),
        low=Decimal(vals[2]),
        close=Decimal(vals[3]),
    )


def _tapes(side: Side, month: int):
    seed, at = ttrades_fixture(
        side=side, month=month, min10_valid=True,
    )
    ext = tuple(_bar(at, side=side, idx=i) for i in range(4))
    return seed, seed + ext[:2], seed + ext[:3], seed + ext


def _captured(side: Side, month: int):
    t0, t2, t3, t4 = _tapes(side, month)
    actor = v3.VT31ContinuousSealCandidate()
    first = actor.capture_context(
        session=SessionId.NY_AM, closed_m1=t0, as_of=t0[-1].closed_at,
    )
    assert first.action == "WAIT" and actor.seal is not None
    return actor, t0, t2, t3, t4


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_v3_successive_waits_seal_all_observed_m1_without_trade(month, side):
    actor, t0, t2, t3, t4 = _captured(side, month)
    assert actor.seal.count == len(t0)
    first = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    assert first.action == "WAIT" and first.delegated_to_v2
    assert actor.seal.count == len(t2)
    assert actor.seal.sha256_total == v3.tape_sha256(t2)
    second = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
    )
    assert second.action == "WAIT"
    assert actor.seal.count == len(t3)
    third = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t4, as_of=t4[-1].closed_at,
    )
    assert third.action == "WAIT"
    assert actor.seal.count == len(t4)
    assert all(
        not v.methodology_certified and not v.cognition_certified
        and not v.production_integrated and v.broker_orders == v.trader_sizing == 0
        for v in (first, second, third)
    )


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
@pytest.mark.parametrize("attribute", ["high", "low", "close"])
def test_v2_would_accept_post_m0_history_fork_but_v3_rejects_before_delegation(
    monkeypatch, month, side, attribute,
):
    actor, t0, t2, t3, _ = _captured(side, month)
    seen = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    assert seen.action == "WAIT"
    tampered = list(t3)
    pos = len(t0)  # 10:03 M1, already sealed by prior assessment.
    original = tampered[pos]
    changed = getattr(original, attribute)
    delta = Decimal("0.05") if attribute != "low" else Decimal("-0.05")
    tampered[pos] = replace(original, **{attribute: changed + delta})
    fork = tuple(tampered)

    # Demonstrate the V2 defect on an independent actor: it freezes M0 only.
    baseline = VT31M0M4CognitiveCandidate()
    baseline.capture_context(
        session=SessionId.NY_AM, closed_m1=t0, as_of=t0[-1].closed_at,
    )
    assert baseline.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    ).action == "WAIT"
    old_verdict = baseline.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=fork, as_of=fork[-1].closed_at,
    )
    assert old_verdict.action == "WAIT"  # Historic B25 vulnerability.

    def forbidden(**kwargs):
        pytest.fail("REWRITTEN_PREVIOUSLY_OBSERVED_TAPE_REACHED_V2")
    monkeypatch.setattr(actor._inner, "assess_later_retest", forbidden)
    rejected = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=fork, as_of=fork[-1].closed_at,
    )
    assert rejected.action == "REJECT"
    assert rejected.reason == "SOURCE_OBSERVED_TAPE_FORK"
    assert not rejected.delegated_to_v2
    assert actor.seal.count == len(t2)
    assert actor.seal.sha256_total == v3.tape_sha256(t2)


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_forged_m4_candle_rejected_and_same_minute_can_be_retried(month, side):
    actor, _, t2, t3, _ = _captured(side, month)
    assert actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    ).action == "WAIT"
    old_seal = actor.seal
    latest = t3[-1]
    forged = Candle(
        latest.opened_at, latest.open, latest.high + Decimal("1"),
        latest.low, latest.close,
    )
    fake = {
        "family": "ORDER_BLOCK_RETEST", "profile": PROFILE,
        "side": side.value, "as_of": latest.closed_at,
        "first_raid_at": actor.context.first_raid_at,
        "displacement_at": t2[-1].closed_at,
        "retest": forged,
        "opposing_candles": (),
    }
    bad = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
        family_evidence=fake,
    )
    assert bad.action == "REJECT"
    assert bad.original_v2_reason == "M4_CANDLE_OHLC_NOT_IN_CLOSED_M1_TAPE"
    assert actor.seal == old_seal
    valid = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
    )
    assert valid.action == "WAIT"
    assert actor.seal.count == len(t3)


@pytest.mark.parametrize("month", [1, 7])
def test_invalid_series_type_is_fail_closed_and_does_not_poison_minute(month):
    actor, _, t2, t3, _ = _captured(Side.LONG, month)
    actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    old_seal = actor.seal
    bad = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
        family_evidence={"opposing_candles": ["not-tuple"]},
    )
    assert bad.action == "REJECT"
    assert bad.reason == "M4_EVIDENCE_SERIES_NOT_IMMUTABLE_TUPLE"
    assert not bad.delegated_to_v2
    assert actor.seal == old_seal
    assert actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
    ).action == "WAIT"


@pytest.mark.parametrize("month", [1, 7])
def test_gap_after_wait_fails_v2_and_does_not_commit_source_seal(month):
    actor, _, t2, t3, t4 = _captured(Side.SHORT, month)
    actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    old_seal = actor.seal
    gap = t2 + t4[len(t3):]
    bad = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=gap, as_of=t4[-1].closed_at,
    )
    assert bad.action == "REJECT"
    assert actor.seal == old_seal
    assert actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
    ).action == "WAIT"


def test_duplicate_time_and_wrong_session_do_not_advance_seal():
    actor, _, t2, t3, _ = _captured(Side.LONG, 1)
    actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    seal = actor.seal
    duplicate = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    assert duplicate.action == "REJECT"
    wrong = actor.assess_later_retest(
        session=SessionId.NY_PM, closed_m1=t3, as_of=t3[-1].closed_at,
    )
    assert wrong.action == "REJECT"
    assert actor.seal == seal
    assert actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
    ).action == "WAIT"


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_min10_context_wait_does_not_get_sealed(month, side):
    rows, at = ttrades_fixture(
        side=side, month=month, min10_valid=False,
    )
    actor = v3.VT31ContinuousSealCandidate()
    v = actor.capture_context(
        session=SessionId.NY_AM, closed_m1=rows, as_of=at,
    )
    assert v.action == "WAIT"
    assert actor.seal is None and actor.context is None
    v = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=rows, as_of=at,
    )
    assert v.action == "WAIT" and not v.delegated_to_v2


def test_pre_registered_dossier_forbids_certification_and_sizing():
    p = v3.prereg_context_dossier()
    assert p["prereg_commit"] == v3.PREREG
    assert len(p["cases"]) == 8
    assert sum(x["seal_count"] is not None for x in p["cases"]) == 4
    assert all(x["action"] == "WAIT" for x in p["cases"])
    assert not p["owner_m0_signed"] and not p["author_m3_m4_m5_certified"]
    assert not p["independent_cog_ops_human_signed"]
    assert not p["native_cog_integrated"]
    assert not p["methodology_certified"] and not p["cognition_certified"]
    assert p["broker_orders"] == p["sizing"] == 0 and not p["live"]
