from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2w_usdjpy_eff5d_validation import (
    BOUNDS,
    END,
    FAMILY,
    FOLD,
    MAX_DD_R,
    MIN_PF,
    MIN_TRADES,
    START,
    Candidate,
    _accept,
)


def test_r2w_family_is_frozen() -> None:
    assert FAMILY == (
        Candidate.CONTROL,
        Candidate.EFF5D_010_020_PRIMARY,
        Candidate.EFF5D_008_020,
        Candidate.EFF5D_010_022,
        Candidate.EFF5D_008_022,
    )
    assert BOUNDS[Candidate.EFF5D_010_020_PRIMARY] == (
        Decimal("0.10"),
        Decimal("0.20"),
    )


def test_r2w_primary_bounds_are_half_open() -> None:
    candidate = Candidate.EFF5D_010_020_PRIMARY

    assert not _accept(candidate, Decimal("0.0999"))
    assert _accept(candidate, Decimal("0.10"))
    assert _accept(candidate, Decimal("0.1999"))
    assert not _accept(candidate, Decimal("0.20"))


def test_r2w_window_is_frozen() -> None:
    assert START == datetime(2018, 9, 21, 0, 0, tzinfo=UTC)
    assert FOLD == datetime(2019, 9, 21, 0, 0, tzinfo=UTC)
    assert END == datetime(2020, 9, 21, 0, 0, tzinfo=UTC)


def test_r2w_gate_is_frozen() -> None:
    assert MIN_TRADES == 12
    assert MIN_PF == 1.05
    assert MAX_DD_R == 12.0
