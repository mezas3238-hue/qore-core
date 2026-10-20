from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2ch_archived_source_novelty as r2ch,
)


def _dt(day: int) -> str:
    return datetime(2025, 1, day, tzinfo=UTC).isoformat()


def _row(i: int, *, c3: str, source: str, gen: int, confirmed: bool) -> dict[str, object]:
    return {
        "identity": r2ch.R2F_IDENTITY,
        "market": "AUDUSD",
        "parent_c3_opened_at": c3,
        "source_opened_at": source,
        "source_event_id": f"source{i}",
        "hypothesis_id": f"hyp{i}",
        "event_generation": gen,
        "state_at_c3_close": (
            r2ch.CONFIRMED_SLOT if confirmed else "AWAITING_CONFIRMATION"
        ),
        "grants_entry_authority": False,
    }


def test_distinct_confirmed_later_event_can_be_only_structurally_unmatched() -> None:
    parent = _dt(1)
    source0, source1 = _dt(2), _dt(3)
    rows = (
        _row(0, c3=parent, source=source0, gen=1, confirmed=True),
        _row(1, c3=parent, source=source1, gen=2, confirmed=True),
    )
    original = {r2ch._key("AUDUSD", parent, source0): 1}
    out = r2ch._classify("AUDUSD", rows, original)
    cnt = out["event_counts"]
    assert cnt["LATER_CONFIRMED_SLOT_ALL"] == 1
    assert cnt["LATER_CONFIRMED_SLOT_STRUCTURALLY_UNMATCHED_ORIGINAL"] == 1
    assert cnt["STRUCTURALLY_MATCHED_ORIGINAL"] == 1
    assert out["parent_c3_with_later_confirmed_unmatched_source"] == 1
    assert out["not_a_trade_capacity_or_alpha_estimate"] is True


def test_ambiguous_source_timestamp_does_not_become_new_trade() -> None:
    parent, source = _dt(1), _dt(2)
    rows = (
        _row(0, c3=parent, source=source, gen=1, confirmed=True),
        _row(1, c3=parent, source=source, gen=2, confirmed=True),
    )
    out = r2ch._classify("AUDUSD", rows, {})
    assert out["event_counts"]["AMBIGUOUS_KEY"] == 2
    assert out["event_counts"]["LATER_CONFIRMED_SLOT_AMBIGUOUS_KEY"] == 1
    assert out["parent_c3_with_later_confirmed_unmatched_source"] == 0


def test_old_r2f_counts_are_integrity_requirements() -> None:
    parent = _dt(1)
    rows = (_row(0, c3=parent, source=_dt(2), gen=2, confirmed=True),)
    report = {
        "identity": r2ch.R2F_IDENTITY,
        "market": "AUDUSD",
        "ledger_rows": 1,
        "full_2y": {
            "source_event_count": 1,
            "later_source_event_count": 1,
            "confirmed_entry_slot_event_count": 1,
        },
    }
    r2ch._check_original_r2f("AUDUSD", rows, report)
    bad = {**report, "full_2y": {**report["full_2y"], "later_source_event_count": 0}}
    with pytest.raises(ValueError, match="reconciliation failed"):
        r2ch._check_original_r2f("AUDUSD", rows, bad)


def test_no_btcusd_reopening_and_timezone_aware_keys() -> None:
    assert "BTCUSD" not in r2ch.ALLOWED_MARKETS
    with pytest.raises(ValueError, match="timezone-aware"):
        r2ch._key("AUDUSD", "2025-01-01T00:00:00", _dt(2))
    assert r2ch.END - r2ch.BEGIN > timedelta(days=729)
