"""V4 transactional COG candidate: discarded rejected snapshots are atomic."""
from __future__ import annotations

import inspect
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from scripts import vt31_cog_v4_transactional_context_20261016 as v4
from scripts.vt31_m0_m4_context_memory_cog_candidate_20261015 import (
    VT31M0M4CognitiveCandidate,
)
from scripts.vt31_m4_ob_breaker_author_evidence_gate_20261015 import (
    PROFILE,
    Candle,
)
from scripts.vt31_original_cog_traderlab_32x_long_short_20261015 import (
    mirror_long_history,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)


def _tail(start, side):
    template = (
        (
            ("104", "106", "100", "103"),
            ("103", "107", "101", "105"),
            ("105", "107", "102", "104"),
            ("104", "106", "100", "102"),
        ) if side is Side.LONG else (
            ("98", "101", "96", "99"),
            ("99", "102", "95", "97"),
            ("97", "101", "95", "98"),
            ("98", "103", "96", "100"),
        )
    )
    return tuple(
        M1Bar(
            opened_at=start + timedelta(minutes=i),
            closed_at=start + timedelta(minutes=i + 1),
            open=Decimal(o), high=Decimal(h),
            low=Decimal(lo), close=Decimal(c),
        )
        for i, (o, h, lo, c) in enumerate(template)
    )


def _actor(side: Side, month: int):
    hist, at = ttrades_fixture(
        side=side, month=month, min10_valid=True,
    )
    tail = _tail(at, side)
    actor = v4.VT31TwoPhaseCognitiveCandidate()
    first = actor.capture_context(
        session=SessionId.NY_AM, closed_m1=hist, as_of=at,
    )
    assert first.action == "WAIT" and first.committed
    assert actor.context is not None and actor.seal is not None
    return actor, hist, hist + tail[:2], hist + tail[:3], hist + tail


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_v4_three_successive_wait_commits_with_immutable_full_tape(month, side):
    actor, base, t2, t3, t4 = _actor(side, month)
    assert actor.revision == 1 and actor.seal.count == len(base)
    for i, tape in enumerate((t2, t3, t4), start=2):
        v = actor.assess_later_retest(
            session=SessionId.NY_AM, closed_m1=tape,
            as_of=tape[-1].closed_at,
        )
        assert v.action == "WAIT" and v.committed
        assert v.prepare_invoked and v.revision == i
        assert v.committed_m1_count == len(tape)
        assert actor.seal.sha256_total == v4.tape_sha256(tape)
        assert not v.author_method_certified and not v.cognition_certified
        assert not v.live_or_oms_authorized
        assert v.broker_orders == v.lot_sizing == 0


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_reject_forged_ob_does_not_poison_state_and_same_asof_retries(month, side):
    actor, _, t2, t3, _ = _actor(side, month)
    actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    before = actor._committed
    seal = actor.seal
    version = actor.revision
    bar = t3[-1]
    forged = Candle(
        bar.opened_at, bar.open, bar.high + Decimal("1"),
        bar.low, bar.close,
    )
    fake = {
        "family": "ORDER_BLOCK_RETEST",
        "profile": PROFILE,
        "side": side.value,
        "as_of": bar.closed_at,
        "first_raid_at": actor.context.first_raid_at,
        "displacement_at": t2[-1].closed_at,
        "retest": forged,
        "opposing_candles": (),
    }
    rejected = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3,
        as_of=t3[-1].closed_at, family_evidence=fake,
    )
    assert rejected.action == "REJECT"
    assert rejected.v2_reason == "M4_CANDLE_OHLC_NOT_IN_CLOSED_M1_TAPE"
    assert rejected.prepare_invoked and not rejected.committed
    assert actor._committed is before
    assert actor.seal == seal and actor.revision == version
    retry = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
    )
    assert retry.action == "WAIT" and retry.committed
    assert retry.revision == version + 1


@pytest.mark.parametrize("month", [1, 7])
def test_exception_after_mutating_staged_v2_does_not_mutate_committed(
    monkeypatch, month,
):
    actor, _, t2, t3, _ = _actor(Side.LONG, month)
    actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    before = actor._committed
    previous_seal, previous_rev = actor.seal, actor.revision
    real_method = VT31M0M4CognitiveCandidate.assess_later_retest

    def poison_staged(self, **kwargs):
        self._last_assessed = kwargs["as_of"]
        self._source = None
        raise RuntimeError("INJECTED_ERROR_AFTER_STAGED_MUTATION")

    with monkeypatch.context() as mp:
        mp.setattr(
            VT31M0M4CognitiveCandidate,
            "assess_later_retest",
            poison_staged,
        )
        rejected = actor.assess_later_retest(
            session=SessionId.NY_AM, closed_m1=t3,
            as_of=t3[-1].closed_at,
        )
    assert rejected.action == "REJECT"
    assert rejected.reason == "V2_PREPARE_EXCEPTION_DISCARDED"
    assert actor._committed is before
    assert actor.context is not None
    assert actor.seal == previous_seal and actor.revision == previous_rev
    assert VT31M0M4CognitiveCandidate.assess_later_retest is real_method
    retry = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
    )
    assert retry.action == "WAIT" and retry.committed


def test_mutating_v2_then_returning_reject_cannot_poison_v4(monkeypatch):
    actor, _, t2, t3, _ = _actor(Side.SHORT, 7)
    actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    before, seal = actor._committed, actor.seal
    from scripts.vt31_m0_m4_context_memory_cog_candidate_20261015 import (
        CandidateVerdict,
    )

    def poison_then_reject(self, **kwargs):
        self._source = None
        self._last_assessed = kwargs["as_of"]
        return CandidateVerdict(
            action="REJECT", reason="INJECTED_M4_CAUSAL_REJECT",
            session="NY_AM",
        )

    with monkeypatch.context() as mp:
        mp.setattr(
            VT31M0M4CognitiveCandidate,
            "assess_later_retest",
            poison_then_reject,
        )
        v = actor.assess_later_retest(
            session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
        )
    assert v.action == "REJECT" and not v.committed
    assert actor._committed is before
    assert actor.context is not None and actor.seal == seal
    assert actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3, as_of=t3[-1].closed_at,
    ).action == "WAIT"


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_late_m1_fork_rejected_before_v2_prepare(monkeypatch, month, side):
    actor, base, t2, t3, _ = _actor(side, month)
    actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    source = list(t3)
    prior = source[len(base)]
    source[len(base)] = replace(prior, high=prior.high + Decimal("0.01"))
    before, seal = actor._committed, actor.seal

    def forbidden(self, **kwargs):
        pytest.fail("PREVIOUSLY_SEEN_M1_MUTATION_REACHED_V2")

    with monkeypatch.context() as mp:
        mp.setattr(
            VT31M0M4CognitiveCandidate, "assess_later_retest", forbidden,
        )
        out = actor.assess_later_retest(
            session=SessionId.NY_AM, closed_m1=tuple(source),
            as_of=t3[-1].closed_at,
        )
    assert out.action == "REJECT" and not out.prepare_invoked
    assert out.reason == "PREVIOUSLY_SEEN_M1_MUTATED"
    assert actor._committed is before and actor.seal == seal


@pytest.mark.parametrize("month", [1, 7])
def test_gap_cross_session_replay_and_malformed_family_not_committed(month):
    actor, _, t2, t3, t4 = _actor(Side.SHORT, month)
    actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t2, as_of=t2[-1].closed_at,
    )
    seal, revision = actor.seal, actor.revision
    gap = t2 + (t4[-1],)
    requests = [
        dict(session=SessionId.NY_AM, closed_m1=gap,
             as_of=gap[-1].closed_at),
        dict(session=SessionId.NY_PM, closed_m1=t3,
             as_of=t3[-1].closed_at),
        dict(session=SessionId.NY_AM, closed_m1=t2,
             as_of=t2[-1].closed_at),
        dict(session=SessionId.NY_AM, closed_m1=t3,
             as_of=t3[-1].closed_at,
             family_evidence={"opposing_candles": ["NOT_A_TUPLE"]}),
    ]
    assert all(
        actor.assess_later_retest(**req).action == "REJECT"
        for req in requests
    )
    assert actor.seal == seal and actor.revision == revision
    assert actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=t3,
        as_of=t3[-1].closed_at,
    ).action == "WAIT"


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_min10_never_commits_context_no_trade(month, side):
    hist, at = ttrades_fixture(
        month=month, side=side, min10_valid=False,
    )
    actor = v4.VT31TwoPhaseCognitiveCandidate()
    v = actor.capture_context(
        session=SessionId.NY_AM, closed_m1=hist, as_of=at,
    )
    assert v.action == "WAIT" and not v.committed
    assert actor.seal is None and actor.context is None
    assert actor.revision == 0
    later = actor.assess_later_retest(
        session=SessionId.NY_AM, closed_m1=hist, as_of=at,
    )
    assert later.action == "WAIT" and not later.committed


@pytest.mark.parametrize("month", [1, 7])
@pytest.mark.parametrize("session", [SessionId.LONDON, SessionId.NY_PM])
@pytest.mark.parametrize("side", [Side.LONG, Side.SHORT])
def test_ict_sessions_not_conflated_with_ttrades_method(month, side, session):
    hist, at = short_fixture(session=session, month=month)
    if side is Side.LONG:
        hist = mirror_long_history(hist)
    actor = v4.VT31TwoPhaseCognitiveCandidate()
    verdict = actor.capture_context(
        session=session, closed_m1=hist, as_of=at,
    )
    assert verdict.action == "WAIT"
    assert not verdict.committed and actor.seal is None
    assert actor.context is None


def test_v4_source_code_has_no_v2_private_clock_or_state_write():
    source = inspect.getsource(v4)
    assert "._last_assessed" not in source
    assert "._source" not in source
    assert "copy.deepcopy" in source


def test_v4_dossier_no_false_certification():
    dossier = v4.transactional_m0_dossier()
    cases = dossier["cases"]
    assert dossier["prereg_sha"] == v4.PREREG
    assert len(cases) == 8
    assert sum(row["committed"] for row in cases) == 4
    assert all(row["action"] == "WAIT" for row in cases)
    assert not dossier["methodology_certified"]
    assert not dossier["cognition_certified"]
    assert not dossier["human_cog_ops_reviews_complete"]
    assert not dossier["owner_policy_signed"]
    assert not dossier["m3_m4_m5_author_approved"]
    assert not dossier["native_cog_integrated"]
    assert dossier["orders"] == dossier["sizing"] == 0 and not dossier["live"]
