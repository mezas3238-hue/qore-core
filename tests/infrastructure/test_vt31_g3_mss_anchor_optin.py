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
    CognitiveDecision,
    G3_MSS_FRAMEWORK_POLICY,
    LEGACY_FRAMEWORK_POLICY,
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
