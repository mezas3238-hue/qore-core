from qore.infrastructure.trader_lab.vt08_index_v5_phase_b_ideal_formation import (
    _context_direction,
    _ideal,
)


def _row(**overrides: str) -> dict[str, str]:
    row = {
        "cisd_latency_m15": "7",
        "protected_swing_count": "1",
        "current_day_sweep_type": "low_reclaim",
        "side": "long",
    }
    row.update(overrides)
    return row


def test_ideal_requires_same_h4_confirmation_window() -> None:
    assert _ideal(_row())
    assert not _ideal(_row(cisd_latency_m15="16"))
    assert not _ideal(_row(protected_swing_count="0"))


def test_source_context_direction_is_ttrades_consistent() -> None:
    assert _context_direction(_row(current_day_sweep_type="high_breakout")) == "long"
    assert _context_direction(_row(current_day_sweep_type="low_breakout")) == "short"
    assert _context_direction(_row(current_day_sweep_type="high_reclaim")) == "short"
    assert _context_direction(_row(current_day_sweep_type="low_reclaim")) == "long"
    assert _context_direction(_row(current_day_sweep_type="inside")) is None
