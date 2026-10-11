"""Selected source-ID M1 forensic suite is read-only and fail closed."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_fifteenth_native_forensics_v1 as forensic,
)


def test_missing_nine_market_replays_fail_closed(tmp_path:Path)->None:
    with pytest.raises(ValueError,match="9 source markets"):
        forensic.summarize(tmp_path)


def test_market_requires_original_source_and_current_max3(tmp_path:Path)->None:
    with pytest.raises(ValueError,match="exactly one frozen"):
        forensic.market(tmp_path,tmp_path,tmp_path,tmp_path)


def test_constants_are_preexisting_h1_null_not_trading_controls()->None:
    assert forensic.HORIZONS == (15,30,60)
    assert forensic.DRAWS == 32
    assert len(forensic.MODES) == 2
    assert "SELECTED_MAX3" in forensic.IDENTITY
