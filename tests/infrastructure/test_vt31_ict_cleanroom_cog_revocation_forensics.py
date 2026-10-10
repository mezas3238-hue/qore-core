"""Independent read-only forensic control for the joined one-trader VT31."""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vt31_ict_cleanroom_cog_revocation_forensics_3y_fast_v1 import (  # noqa: E402
    CausalForensicCognition,
    scan,
)


def bar(t: datetime, o: str, h: str, lo: str, c: str) -> M1Bar:
    return M1Bar(
        opened_at=t, closed_at=t + timedelta(minutes=1),
        open=Decimal(o), high=Decimal(h), low=Decimal(lo), close=Decimal(c),
    )


def source() -> tuple[M1Bar, ...]:
    cash = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    asian = datetime(2026, 1, 5, 5, tzinfo=UTC)
    previous = tuple(
        bar(cash + timedelta(minutes=i), "110",
            "150" if i == 33 else "114",
            "80" if i == 45 else "108", "111")
        for i in range(390)
    )
    asia = tuple(bar(
        asian + timedelta(minutes=i), "100", "101", "99", "100.5"
    ) for i in range(180))
    london = asian + timedelta(minutes=180)
    first = (
        bar(london, "100", "103", "99", "101"),
        bar(london + timedelta(minutes=1), "101", "103", "100", "100.5"),
        bar(london + timedelta(minutes=2), "101", "105", "100", "102"),
        bar(london + timedelta(minutes=3), "101", "104", "100", "101"),
        bar(london + timedelta(minutes=4), "101", "104", "100", "104"),
        bar(london + timedelta(minutes=5), "105", "109", "105", "108"),
    )
    return previous + asia + first


def rows(bars: tuple[M1Bar, ...]):
    for x in bars:
        yield {
            "opened_at": x.opened_at.isoformat(),
            "closed_at": x.closed_at.isoformat(),
            "open": str(x.open),
            "high": str(x.high),
            "low": str(x.low),
            "close": str(x.close),
        }


def test_probe_preserves_real_cognition_and_ops_source_candidate() -> None:
    normal = VT31Trader()
    probed = VT31Trader(cognition=CausalForensicCognition())
    for item in source():
        x = normal.on_closed_m1(item)
        y = probed.on_closed_m1(item)
        assert y == x
    assert normal.snapshot()["session_windows"] == probed.snapshot()["session_windows"]
    assert probed.cognition.probes["ACTIVE_M1_THESIS_REEVALUATED"] >= 1
    assert probed.trader_id == "VT31"


def test_causal_swept_dol_is_wick_cause_not_a_broker_fill() -> None:
    model = VT31Trader(cognition=CausalForensicCognition())
    baseline = source()
    for item in baseline:
        model.on_closed_m1(item)
    assert model.cognition.latest_assessment is not None
    assert model.cognition.latest_assessment.decision is not None
    t = baseline[-1].closed_at
    next_bar = bar(t, "110", "151", "106", "110")
    observation = model.on_closed_m1(next_bar)
    assert observation.cognition is not None
    assert observation.cognition.decision is None
    assert "DOL_SWEPT_THIS_CLOSED_M1" in model.cognition.last_causes
    assert model.cognition.probes["DOL_SWEPT_THIS_CLOSED_M1"] >= 1
    assert observation.order_authorized is False


def test_prior_thesis_pivot_close_reversal_detected_with_as_of_m1() -> None:
    model = VT31Trader(cognition=CausalForensicCognition())
    baseline = source()
    for item in baseline:
        model.on_closed_m1(item)
    t = baseline[-1].closed_at
    below = bar(t, "108", "110", "100", "102")
    observation = model.on_closed_m1(below)
    assert observation.cognition is not None
    assert observation.cognition.decision is None
    assert "M1_CLOSE_REVERSED_PREVIOUS_PIVOT" in model.cognition.last_causes
    assert not observation.order_authorized


def test_full_source_close_to_close_will_revoke_pending_without_cognition() -> None:
    baseline = source()
    after = bar(
        baseline[-1].closed_at, "110", "151", "106", "110"
    )
    # Forensics scanner requires complete source M1 hour.
    rest = tuple(
        bar(
            after.closed_at + timedelta(minutes=i),
            "110", "112", "108", "111",
        )
        for i in range(53)
    )
    # A selected London FVG is a source proposal ONLY. OPS must immediately
    # revoke it at a closed bar if current COG proof disappears.
    result = scan(rows(baseline + (after,) + rest))
    assert result["trader_id"] == "VT31"
    assert result["source_candidate_by_window"]["VT31_LONDON"] == 1
    assert result["pending_m1_without_cog"] == 0
    assert result["unique_source_pending_without_cog"] == 0
    assert result["interpretation_limits"]["live_authorized"] is False
    assert result["final_source_invalidation_reasons"]


def test_missing_and_partial_source_never_produce_fake_fvg() -> None:
    start = datetime(2025, 7, 7, 7, tzinfo=UTC)
    bars = tuple(bar(
        start + timedelta(minutes=i),
        "100", "101", "99", "100",
    ) for i in range(59))
    result = scan(rows(bars))
    assert result["market_closed_m1"] == 59
    assert result["cognitive_calls"] == 0
    assert result["partial_m1_window_days"] == {"VT31_LONDON": 1}
    assert result["source_candidate_by_window"] == {}
    assert result["final_source_candidate_states"] == {}


def test_forensics_rejects_duplicate_and_never_estimates_pf() -> None:
    t = datetime(2025, 7, 7, 7, tzinfo=UTC)
    with pytest.raises(ValueError, match="duplicate"):
        scan(rows((bar(t, "100", "101", "99", "100"),) * 2))
