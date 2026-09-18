from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.trader_lab import turtle_soup_xauusd_r3_cibo_journey as r3
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r23_hierarchical_friction_memory as r23,
)
from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r24_friction_resolved_full_cibo_brain as r24,
)
from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import Side


def _setup() -> SimpleNamespace:
    signal = SimpleNamespace(
        side=Side.LONG,
        protected_swing=Decimal("99"),
    )
    context = SimpleNamespace(
        signal=signal,
        timeframe="H1",
        fvg_before_entry="yes",
        cisd_progress_bucket="q4:>0.75",
        protected_risk_range_bucket="q3:<=1.0",
        source_range_state_bucket="q3:<=1.5",
    )
    return SimpleNamespace(context=context)


def _ladder() -> list[r3.TargetCandidate]:
    base = {
        "episode_id": "e",
        "known_at": datetime(2026, 1, 1, tzinfo=UTC),
        "touch_at": None,
        "kind": "ACTIVE_SWING_3_DIRECTIONAL_BOUNDARY",
        "timeframe": "H1",
    }
    return [
        r3.TargetCandidate(level=Decimal("100.7"), **base),
        r3.TargetCandidate(level=Decimal("102"), **base),
    ]


def _empty_resilience() -> dict[str, dict[str, object]]:
    return {
        name: {"fields": list(fields), "signatures": {}}
        for name, fields in r23.RESILIENCE_LEVELS
    }


def test_supportive_entry_policy_is_immediate() -> None:
    mode, policy, level = r24._entry_policy(
        memory_state="SUPPORTIVE",
        setup=_setup(),
        posture="RANGE_OR_COMPRESSION",
        subtype_hierarchy={},
    )
    assert mode == "NEXT_SOURCE_OPEN"
    assert policy == "SUPPORTIVE_EXECUTE"
    assert level is None


def test_choose_target_keeps_resilient_base(monkeypatch) -> None:
    monkeypatch.setattr(
        r23,
        "resolve_resilience",
        lambda hierarchy, row: (
            r23.RESILIENT if row["target_rank"] == 1 else r23.NON_RESILIENT,
            "r4",
            "sig",
        ),
    )
    rank, reason, diagnostics = r24.choose_target_rank(
        base_rank=1,
        ladder=_ladder(),
        memory_state="SUPPORTIVE",
        setup=_setup(),
        entry=Decimal("100"),
        resilience_hierarchy=_empty_resilience(),
    )
    assert rank == 1
    assert reason == "BASE_TARGET_RESILIENT_010"
    assert diagnostics["1"]["classification"] == r23.RESILIENT


def test_choose_target_can_extend_to_resilient_rank2(monkeypatch) -> None:
    monkeypatch.setattr(
        r23,
        "resolve_resilience",
        lambda hierarchy, row: (
            r23.RESILIENT if row["target_rank"] == 2 else r23.NON_RESILIENT,
            "r4",
            "sig",
        ),
    )
    rank, reason, _diagnostics = r24.choose_target_rank(
        base_rank=1,
        ladder=_ladder(),
        memory_state="SUPPORTIVE",
        setup=_setup(),
        entry=Decimal("100"),
        resilience_hierarchy=_empty_resilience(),
    )
    assert rank == 2
    assert reason == "EXTEND_TO_RESILIENT_RANK2"


def test_choose_target_abstains_when_no_rank_is_resilient(monkeypatch) -> None:
    monkeypatch.setattr(
        r23,
        "resolve_resilience",
        lambda hierarchy, row: (r23.NON_RESILIENT, "r4", "sig"),
    )
    rank, reason, _diagnostics = r24.choose_target_rank(
        base_rank=1,
        ladder=_ladder(),
        memory_state="SUPPORTIVE",
        setup=_setup(),
        entry=Decimal("100"),
        resilience_hierarchy=_empty_resilience(),
    )
    assert rank is None
    assert reason == "ABSTAIN_NO_RESILIENT_DOL_010"
