from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_index_v4_root_cause_forensics import (
    _holm_adjust,
    _hypotheses,
    _range_state,
    _sweep_type,
)
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import Vt08IndexC2R1Bar


def _bar(open_: str, high: str, low: str, close: str) -> Vt08IndexC2R1Bar:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_sweep_type_separates_reclaim_from_breakout() -> None:
    reference = _bar("100", "110", "90", "102")
    assert _sweep_type(_bar("102", "112", "98", "108"), reference) == "high_reclaim"
    assert _sweep_type(_bar("102", "114", "98", "112"), reference) == "high_breakout"
    assert _sweep_type(_bar("102", "108", "88", "94"), reference) == "low_reclaim"
    assert _sweep_type(_bar("102", "108", "86", "88"), reference) == "low_breakout"


def test_range_state_uses_declared_descriptor_boundaries() -> None:
    assert _range_state(Decimal("0.79")) == "compressed"
    assert _range_state(Decimal("0.80")) == "normal"
    assert _range_state(Decimal("1.20")) == "normal"
    assert _range_state(Decimal("1.21")) == "expanded"


def test_holm_adjustment_is_monotone_and_family_wise() -> None:
    adjusted = _holm_adjust({"a": 0.001, "b": 0.01, "c": 0.2})
    assert adjusted == {"a": 0.003, "b": 0.02, "c": 0.2}


def test_hypothesis_predicates_never_reference_outcome_columns() -> None:
    source = {
        "previous_source_day_body_alignment": "opposed",
        "cisd_latency_m15": 7,
        "closure_family": "c2",
        "source_day_relationship": "reversal",
        "cross_index_directional_state": "mixed",
        "protected_swing_count": 2,
        "opposing_series_length": 2,
        "current_source_day_body_alignment": "aligned",
        "recent_causal_h4_range_state": "normal",
        "recent_causal_daily_range_state": "normal",
        "current_day_sweep_type": "low_reclaim",
    }
    results_without_label = {name: predicate(source) for name, predicate in _hypotheses().items()}
    source["outcome_r"] = "-1"
    results_with_label = {name: predicate(source) for name, predicate in _hypotheses().items()}
    assert results_without_label == results_with_label
    assert len(results_with_label) == 18
