from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.ict_turtle_soup_r4_source_exact import (
    Bar,
    BearishFvg,
)
from qore.infrastructure.trader_lab.nq_am_tlr_v5_source_resolved import (
    _causal_inversion_and_retest,
    _complete_body_below,
    _opening_pair_signature,
    _target_outcome,
)


def _bar(
    minute: int,
    *,
    o: str,
    h: str,
    lo: str,
    c: str,
) -> Bar:
    opened = datetime(2016, 5, 2, 13, 30, tzinfo=UTC) + timedelta(minutes=minute)
    return Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(lo),
        close=Decimal(c),
    )


def test_complete_body_below_requires_open_and_close_below() -> None:
    assert _complete_body_below(
        _bar(0, o="99", h="101", lo="98", c="99.5"),
        Decimal("100"),
    )
    assert not _complete_body_below(
        _bar(1, o="101", h="102", lo="98", c="99"),
        Decimal("100"),
    )


def test_opening_signature_is_telemetry_for_specific_pair() -> None:
    bars = (
        _bar(0, o="99", h="100.5", lo="98", c="99.5"),
        _bar(1, o="99.5", h="100.7", lo="98.5", c="99.6"),
    )
    assert _opening_pair_signature(
        bars,
        index_a=0,
        lower_quadrant_top=Decimal("101"),
        lowest_octant_top=Decimal("100"),
    )


def test_ifvg_trade_above_does_not_require_close_above() -> None:
    zone = BearishFvg(
        created_at=_bar(0, o="105", h="106", lo="104", c="104.5").closed_at,
        low=Decimal("100"),
        high=Decimal("102"),
    )
    bars = (
        _bar(0, o="99", h="101", lo="98", c="100"),
        _bar(1, o="100", h="103", lo="99", c="101.5"),
        _bar(2, o="103", h="104", lo="101", c="103"),
    )
    result = _causal_inversion_and_retest(
        bars,
        zone=zone,
        sweep_at=bars[0].opened_at,
        session_end=bars[-1].closed_at + timedelta(minutes=1),
    )
    assert result is not None
    inversion_at, close_above, entry_at, entry = result
    assert inversion_at == bars[1].closed_at
    assert close_above is False
    assert entry_at == bars[2].opened_at
    assert entry == Decimal("102")


def test_target_same_bar_structural_loss_scores_loss_first() -> None:
    entry_at = _bar(0, o="100", h="101", lo="99", c="100").opened_at
    bars = (
        _bar(0, o="100", h="110", lo="94", c="105"),
    )
    result = _target_outcome(
        bars,
        entry_at=entry_at,
        sweep_low=Decimal("95"),
        target_name="rth_0930_open",
        target_price=Decimal("108"),
        entry=Decimal("100"),
    )
    assert result.eligible is True
    assert result.reached_before_new_sweep_low is False


def test_0930_open_is_single_target_identity_not_duplicate_gap_low() -> None:
    result = _target_outcome(
        (_bar(0, o="100", h="109", lo="99", c="108"),),
        entry_at=_bar(0, o="100", h="109", lo="99", c="108").opened_at,
        sweep_low=Decimal("95"),
        target_name="rth_0930_open",
        target_price=Decimal("108"),
        entry=Decimal("100"),
    )
    assert result.target_name == "rth_0930_open"
    assert result.reached_before_new_sweep_low is True
