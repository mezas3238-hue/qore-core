"""No outcome-derived filtering in the frozen audit15 classification."""

from __future__ import annotations

from pathlib import Path

import pytest

from qore.infrastructure.trader_lab import (
    capitalizer_scalper_a2_fifteenth_residual_anatomy_v1 as audit,
)


def test_empty_books_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="frozen Audit14"):
        audit.anatomy(tmp_path)


def test_market_session_and_family_partition_are_provenance_not_pnl() -> None:
    row={
        "symbol":"AUDJPY", "session":"ASIA",
        "source_family":"LIQUIDITY_SWEEP_CISD",
        "online_family":"FVG_RETRACE_CISD",
        "first_online_differs":True, "frozen_381":True,
        "status":"INVALID_M15_STOP_AT_ONLINE_CLOSE",
    }
    counts=audit.partition([row,row])
    assert counts["ALL"]["n"]==2
    assert counts["INVALID_M15_STOP"]["n"]==2
    assert counts["NO_H1_TARGET"]["n"]==0
    assert counts["INVALID_M15_STOP"]["by_market"]=={"AUDJPY":2}
    assert counts["INVALID_M15_STOP"]["by_family_transition"]=={
        "LIQUIDITY_SWEEP_CISD->FVG_RETRACE_CISD":2,
    }
    assert counts["ALL"]["frozen_381"]==2
