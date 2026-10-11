"""Audit15 M15/M1 factor combinations never approve LIVE or optimization."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_fifteenth_online_stop_factorial_v1 as audit,
)
from qore.infrastructure.trader_lab.capitalizer_scalper_stop_noise_factorial_v1 import (
    Arm,
)


def test_absent_original_and_selection_fail_closed(tmp_path:Path)->None:
    with pytest.raises(ValueError,match="one frozen"):
        audit.market(tmp_path,tmp_path,tmp_path,tmp_path)


def test_not_nine_markets_not_valid_factorial(tmp_path:Path)->None:
    with pytest.raises(ValueError,match="9-market factorial"):
        audit.matrix(tmp_path)


def test_four_prespecified_arms_not_tuned()->None:
    assert len(Arm)==4
    assert Arm.M15_NOISE_OFF.value=="M15_NOISE_OFF"
    assert "FIXED_MAX3" in audit.IDENTITY
