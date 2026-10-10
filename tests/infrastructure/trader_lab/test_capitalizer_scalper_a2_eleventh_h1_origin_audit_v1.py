"""H1 closure attribution and inherited-session falsifiers."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab.capitalizer_scalper_a2_eleventh_h1_origin_audit_v1 import (
    aggregate,
    classify_basis,
)


@pytest.mark.parametrize(
    ("basis", "expected"),
    [
        ("CANDLE2_REVERSAL:BULLISH_FVG", ("CANDLE2_REVERSAL", False)),
        ("SESSION_INHERITED:CANDLE2_REVERSAL:BEARISH_FVG", ("CANDLE2_REVERSAL", True)),
        ("CANDLE3_CONFIRMATION:BULLISH_FVG", ("CANDLE3_CONFIRMATION", False)),
        ("SESSION_INHERITED:CANDLE3_CONFIRMATION:BULLISH_FVG", ("CANDLE3_CONFIRMATION", True)),
        ("ENGINEERED_OTHER:POI", ("UNRESOLVED_SOURCE_BASIS", False)),
    ],
)
def test_original_h1_basis_is_not_c3_only(basis: str, expected: tuple[str, bool]) -> None:
    assert classify_basis(basis) == expected


def test_h1_audit_fails_closed_without_all_nine_markets(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="nine distinct"):
        aggregate(tmp_path)
