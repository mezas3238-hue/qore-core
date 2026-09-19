from __future__ import annotations

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import CTraderDemoLabProbeError
from qore.infrastructure.ctrader_demo_lab_vt08_index_v3_probe import (
    FROZEN_LOOKBACK_DAYS,
    frozen_lookback_days,
)


def test_v3_probe_freezes_exact_four_year_lookback() -> None:
    assert FROZEN_LOOKBACK_DAYS == 1460
    assert frozen_lookback_days(None) == 1460
    assert frozen_lookback_days("1460") == 1460


def test_v3_probe_rejects_lookback_drift() -> None:
    with pytest.raises(CTraderDemoLabProbeError, match="must equal 1460"):
        frozen_lookback_days("1459")
    with pytest.raises(CTraderDemoLabProbeError, match="must be integer"):
        frozen_lookback_days("four-years")
