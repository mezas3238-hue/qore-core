"""Proposed G3 V1 MSS-close gate, opt-in only. Synthetic witnesses, not PnL."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    CausalSwingBreak,
    LiquidityPool,
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    LEGACY_FRAMEWORK_POLICY,
    CognitiveDecision,
    M1Bar,
    MethodologyDecision,
    SessionId,
    Side,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.operations import (
    IctSilverBulletOperations,
)

T0 = datetime(2025, 7, 7, 7, 10, tzinfo=UTC)


def bar(i: int, o: str, h: str, lo: str, c: str) -> M1Bar:
    at = T0 + timedelta(minutes=i)
    return M1Bar(at, at + timedelta(minutes=1), Decimal(o), Decimal(h),
                 Decimal(lo), Decimal(c))


def sample(kind: str) -> tuple[list[M1Bar], Side, str, int, str]:
    if kind == "long_mss_pass_c3_fail":
        return [
            bar(0, "110", "112", "108", "110"),
            bar(1, "116", "120", "114", "118"),
            bar(2, "121", "124", "119", "121"),
        ], Side.LONG, "130", 0, "109"
    if kind == "long_c3_pass_mss_fail":
        return [
            bar(0, "115", "118", "110", "115"),
            bar(1, "120", "127", "119", "125"),
            bar(2, "120", "123", "119", "120"),
        ], Side.LONG, "132", 1, "117"
    if kind == "short_mss_pass_c3_fail":
        return [
            bar(0, "130", "132", "125", "130"),
            bar(1, "123", "124", "120", "121"),
            bar(2, "116", "119", "113", "117"),
        ], Side.SHORT, "110", 0, "131"
    raise ValueError(kind)


def cognitive_decision(
    bars: list[M1Bar], side: Side, target: str, shift_index: int,
    level: str, policy: str,
) -> CognitiveDecision:
    return CognitiveDecision(
        session=SessionId.LONDON,
        side=side,
        observed_at=bars[-1].closed_at,
        draw_target=Decimal(target),
        draw_family="STABLE_CAUSAL_DOL",
        draw_level_observed_at=T0-timedelta(minutes=20),
        structure_level=Decimal(level),
        structure_level_confirmed_at=T0-timedelta(minutes=3),
        structure_break_confirmed_at=bars[shift_index].closed_at,
        source_provenance="SYNTHETIC_RESEARCH_ONLY_NO_BROKER",
        cognitive_version="TEST_G3" if policy == G3_MSS_FRAMEWORK_POLICY
        else "VT31_ICT_CLEANROOM_COG_V1",
        framework_policy=policy,
        mss_anchor_close=(
            bars[shift_index].close
            if policy == G3_MSS_FRAMEWORK_POLICY else None
        ),
    )


def run_ops(kind: str, *, policy: str) -> IctSilverBulletOperations:
    bars, side, target, pivot, level = sample(kind)
    ops = IctSilverBulletOperations(
        session=SessionId.LONDON, day=T0, framework_policy=policy,
    )
    ops.on_closed_m1(bars[0], cognition=None)
    ops.on_closed_m1(bars[1], cognition=None)
    ops.on_closed_m1(
        bars[2],
        cognition=cognitive_decision(
            bars, side, target, pivot, level, policy,
        ),
    )
    return ops


@pytest.mark.parametrize("kind,legacy_pending,g3_pending", [
    ("long_mss_pass_c3_fail", False, True),
    ("long_c3_pass_mss_fail", True, False),
    ("short_mss_pass_c3_fail", False, True),
])
def test_old_c3_gate_can_disagree_with_new_mss_gate(
    kind: str, legacy_pending: bool, g3_pending: bool,
) -> None:
    legacy = run_ops(kind, policy=LEGACY_FRAMEWORK_POLICY)
    v1 = run_ops(kind, policy=G3_MSS_FRAMEWORK_POLICY)
    assert (legacy.decision is MethodologyDecision.RESEARCH_PENDING_CE) == legacy_pending
    assert (v1.decision is MethodologyDecision.RESEARCH_PENDING_CE) == g3_pending
    if g3_pending:
        assert v1.first_suitable is not None
        assert v1.first_suitable.projected_index_points >= Decimal("10")
    if legacy_pending:
        assert legacy.first_suitable is not None


def test_wrong_mss_close_claim_rejected_by_ops() -> None:
    bars, side, target, shift_index, level = sample("long_mss_pass_c3_fail")
    ops = IctSilverBulletOperations(
        session=SessionId.LONDON, day=T0,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    ops.on_closed_m1(bars[0], cognition=None)
    ops.on_closed_m1(bars[1], cognition=None)
    honest = cognitive_decision(
        bars, side, target, shift_index, level, G3_MSS_FRAMEWORK_POLICY,
    )
    with pytest.raises(ValueError, match="not independently verified"):
        ops.on_closed_m1(
            bars[2], cognition=replace(honest, mss_anchor_close=Decimal("105")),
        )
    assert ops.first_suitable is None
    assert ops.last_closed == bars[1].closed_at


def test_unobserved_mss_close_fails_closed_even_if_mss_stamp_is_in_past() -> None:
    bars, side, target, pivot, level = sample("long_mss_pass_c3_fail")
    ops = IctSilverBulletOperations(
        session=SessionId.LONDON, day=T0,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    ops.on_closed_m1(bars[0], cognition=None)
    ops.on_closed_m1(bars[1], cognition=None)
    proposed = cognitive_decision(
        bars, side, target, pivot, level, G3_MSS_FRAMEWORK_POLICY,
    )
    old_timestamp = T0 - timedelta(minutes=5)
    proposed = replace(proposed, structure_break_confirmed_at=old_timestamp,
                       structure_level_confirmed_at=old_timestamp-timedelta(minutes=1))
    with pytest.raises(ValueError, match="not independently verified"):
        ops.on_closed_m1(bars[2], cognition=proposed)


def test_v1_decision_rejected_by_legacy_ops() -> None:
    bars, side, target, pivot, level = sample("long_mss_pass_c3_fail")
    ops = IctSilverBulletOperations(session=SessionId.LONDON, day=T0)
    ops.on_closed_m1(bars[0], cognition=None)
    ops.on_closed_m1(bars[1], cognition=None)
    with pytest.raises(ValueError, match="cannot feed legacy"):
        ops.on_closed_m1(
            bars[2], cognition=cognitive_decision(
                bars, side, target, pivot, level, G3_MSS_FRAMEWORK_POLICY,
            ),
        )


def test_legacy_cognition_rejected_by_v1_ops() -> None:
    bars, side, target, pivot, level = sample("long_mss_pass_c3_fail")
    ops = IctSilverBulletOperations(
        session=SessionId.LONDON, day=T0,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    ops.on_closed_m1(bars[0], cognition=None)
    ops.on_closed_m1(bars[1], cognition=None)
    with pytest.raises(ValueError, match="share G3"):
        ops.on_closed_m1(
            bars[2], cognition=cognitive_decision(
                bars, side, target, pivot, level, LEGACY_FRAMEWORK_POLICY,
            ),
        )


def test_missing_mss_close_is_not_fabricated_by_dto() -> None:
    bars, side, target, pivot, level = sample("long_mss_pass_c3_fail")
    with pytest.raises(ValueError, match="MSS close witness required"):
        replace(
            cognitive_decision(
                bars, side, target, pivot, level,
                G3_MSS_FRAMEWORK_POLICY,
            ), mss_anchor_close=None,
        )


def test_mss_close_not_allowed_in_legacy_dto() -> None:
    bars, side, target, pivot, level = sample("long_mss_pass_c3_fail")
    with pytest.raises(ValueError, match="legacy cognition cannot"):
        replace(
            cognitive_decision(
                bars, side, target, pivot, level,
                LEGACY_FRAMEWORK_POLICY,
            ), mss_anchor_close=Decimal("110"),
        )


def test_invalid_policy_name_rejected_on_both_engines() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        VT31CleanroomCognition(framework_policy="V2_TUNED_FOR_PNL")
    with pytest.raises(ValueError, match="unsupported"):
        IctSilverBulletOperations(
            session=SessionId.LONDON, day=T0,
            framework_policy="V2_TUNED_FOR_PNL",
        )


def test_cog_captures_mss_close_then_preserves_during_later_revalidations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cog = VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY)
    first = bar(0, "107", "113", "106", "110")
    cog.observe_closed_m1(first)
    pivot = CausalSwingBreak(
        Side.LONG, Decimal("108"),
        first.opened_at - timedelta(minutes=2),
        first.closed_at, Decimal("3"), Decimal("2"),
    )
    pool = LiquidityPool(
        "PRIOR_NY_CASH_SESSION_HIGH", Side.LONG, Decimal("125"),
        first.opened_at - timedelta(hours=3),
        first.opened_at - timedelta(hours=8),
        first.opened_at - timedelta(hours=3),
    )
    monkeypatch.setattr(
        cog._index, "context",
        lambda at: (("M15", "H1"), {"M15": "BULLISH", "H1": "BULLISH"}),
    )
    monkeypatch.setattr(cog._index, "pools", lambda at, sess: (pool,))
    monkeypatch.setattr(cog._index, "shift", lambda: pivot)
    fresh = cog.assess(session=SessionId.LONDON, as_of=first.closed_at)
    assert fresh.decision is not None
    assert fresh.decision.mss_anchor_close == Decimal("110")
    assert fresh.decision.structure_break_confirmed_at == first.closed_at
    assert fresh.decision.framework_policy == G3_MSS_FRAMEWORK_POLICY

    # The new current close has only 2 pts left to DOL, but an earlier
    # qualifying MSS thesis remains eligible if source pivot/DOL are intact.
    second = bar(1, "111", "123", "110", "123")
    cog.observe_closed_m1(second)
    monkeypatch.setattr(cog._index, "shift", lambda: None)
    still = cog.assess(session=SessionId.LONDON, as_of=second.closed_at)
    assert still.decision is not None
    assert still.decision.mss_anchor_close == Decimal("110")
    assert still.decision.structure_break_confirmed_at == first.closed_at
    assert still.decision.observed_at == second.closed_at


def test_cog_rejects_shift_timestamp_not_same_as_current_closed_m1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cog = VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY)
    first = bar(0, "107", "113", "106", "110")
    cog.observe_closed_m1(first)
    fake = CausalSwingBreak(
        Side.LONG, Decimal("108"),
        first.opened_at-timedelta(minutes=3),
        first.opened_at, Decimal("3"), Decimal("2"),
    )
    pool = LiquidityPool(
        "PRIOR_NY_CASH_SESSION_HIGH", Side.LONG, Decimal("125"),
        first.opened_at-timedelta(hours=3),
        first.opened_at-timedelta(hours=8),
        first.opened_at-timedelta(hours=3),
    )
    monkeypatch.setattr(
        cog._index, "context",
        lambda at: (("M15", "H1"), {"M15": "BULLISH", "H1": "BULLISH"}),
    )
    monkeypatch.setattr(cog._index, "pools", lambda at, sess: (pool,))
    monkeypatch.setattr(cog._index, "shift", lambda: fake)
    with pytest.raises(ValueError, match="MSS witness must be"):
        cog.assess(session=SessionId.LONDON, as_of=first.closed_at)


def _genuine_cog_mss_witness() -> tuple[
    list[M1Bar], CognitiveDecision, VT31CleanroomCognition,
]:
    """Create REAL native MSS/DOL on closed bars, not an invented DTO.

    Mirrors pre-existing cleanroom cognition fixtures but runs the actual
    _OnlineCausalIndex, _confirmed_break, pool confirmation and assess().
    Only the downstream OPS market stream is corrupted in adversarial tests.
    """
    previous = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    today = datetime(2026, 1, 5, 5, tzinfo=UTC)

    def candle(
        dt: datetime, o: str = "100", h: str = "101",
        lo: str = "99", c: str = "100.5",
    ) -> M1Bar:
        return M1Bar(
            opened_at=dt,
            closed_at=dt + timedelta(minutes=1),
            open=Decimal(o), high=Decimal(h),
            low=Decimal(lo), close=Decimal(c),
        )

    previous_cash = [
        candle(
            previous + timedelta(minutes=i),
            o="110", h="150" if i == 33 else "114",
            lo="80" if i == 45 else "108", c="111",
        ) for i in range(390)
    ]
    asia = [candle(today + timedelta(minutes=i)) for i in range(180)]
    start = today + timedelta(minutes=180)  # Monday 03:00 New York
    session = [
        candle(start, o="100", h="103", lo="99", c="101"),
        candle(start + timedelta(minutes=1), o="101",
               h="103", lo="100", c="100.5"),
        candle(start + timedelta(minutes=2), o="101",
               h="105", lo="100", c="102"),
        candle(start + timedelta(minutes=3), o="101",
               h="104", lo="100", c="101"),
        candle(start + timedelta(minutes=4), o="101",
               h="104", lo="100", c="104"),
        candle(start + timedelta(minutes=5), o="101",
               h="109", lo="101", c="107"),
    ]
    cog = VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY)
    for item in previous_cash + asia + session:
        cog.observe_closed_m1(item)
    assessment = cog.assess(
        session=SessionId.LONDON, as_of=session[-1].closed_at,
    )
    assert assessment.decision is not None, assessment.missing
    witness = assessment.decision
    assert witness.side is Side.LONG
    assert witness.structure_level == Decimal("105")
    assert witness.mss_anchor_close == Decimal("107")
    assert witness.structure_break_confirmed_at == session[-1].closed_at
    assert witness.structure_level_confirmed_at < witness.structure_break_confirmed_at
    assert witness.draw_target == Decimal("150")
    return session, witness, cog


def test_genuine_cog_decision_accepted_against_untampered_ops_m1() -> None:
    bars, witness, _ = _genuine_cog_mss_witness()
    ops = IctSilverBulletOperations(
        session=SessionId.LONDON, day=bars[0].opened_at,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    for item in bars[:-1]:
        ops.on_closed_m1(item, cognition=None)
    # Actual original COG witness + identical OPS M1. Gate must NOT reject.
    ops.on_closed_m1(bars[-1], cognition=witness)
    assert ops.last_closed == bars[-1].closed_at


def test_falsified_mss_close_same_timestamp_is_rejected_by_ops() -> None:
    bars, witness, _ = _genuine_cog_mss_witness()
    ops = IctSilverBulletOperations(
        session=SessionId.LONDON, day=bars[0].opened_at,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    for item in bars[:-1]:
        ops.on_closed_m1(item, cognition=None)
    # Timestamp, direction, pivot, DOL and CognitiveDecision remain genuine.
    # ONLY the M1 close as loaded downstream differs from the COG witness.
    corrupted = replace(bars[-1], close=Decimal("106"))
    assert corrupted.closed_at == witness.structure_break_confirmed_at
    assert corrupted.close != witness.mss_anchor_close
    with pytest.raises(
        ValueError, match="MSS_ANCHOR_INCONSISTENT_WITH_M1_DATA",
    ):
        ops.on_closed_m1(corrupted, cognition=witness)
    assert ops.last_closed == bars[-2].closed_at
    assert ops.first_suitable is None
    assert bars[-1].close == Decimal("107")  # upstream unmodified


def test_falsified_mss_m1_cached_before_later_c3_revalidation_rejected() -> None:
    bars, witness, cog = _genuine_cog_mss_witness()
    ops = IctSilverBulletOperations(
        session=SessionId.LONDON, day=bars[0].opened_at,
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    for item in bars[:-1]:
        ops.on_closed_m1(item, cognition=None)
    altered_mss = replace(bars[-1], close=Decimal("106"))
    ops.on_closed_m1(altered_mss, cognition=None)

    # COG maintains the *same* original MSS witness after the next M1.
    at = bars[-1].closed_at
    later = M1Bar(
        at, at + timedelta(minutes=1),
        Decimal("107"), Decimal("110"),
        Decimal("105.5"), Decimal("108"),
    )
    cog.observe_closed_m1(later)
    continued = cog.assess(
        session=SessionId.LONDON, as_of=later.closed_at,
    )
    assert continued.decision is not None, continued.missing
    assert continued.decision.structure_break_confirmed_at == witness.structure_break_confirmed_at
    assert continued.decision.mss_anchor_close == Decimal("107")
    assert continued.decision.observed_at == later.closed_at
    with pytest.raises(
        ValueError, match="MSS_ANCHOR_INCONSISTENT_WITH_M1_DATA",
    ):
        ops.on_closed_m1(later, cognition=continued.decision)
    # OPS does not re-run MSS and does not silently trust the valid COG DTO.
    assert ops.last_closed == altered_mss.closed_at
    assert ops.first_suitable is None
