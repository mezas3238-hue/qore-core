"""Market-lab driver for VT-31 pre-departure structure analysis.

CIBO Atlas is intentionally independent from trader acceptance. The source
trader abstains if both 09:00 boundaries are swept during the 10:00-11:00
window. That rule must not censor the laboratory: an eventual opposite-boundary
hit is exactly the path Atlas is studying. Therefore this driver freezes the
*first directional breach* as the market-path origin while retaining the
existing VT-31 source formalization for Breaker/OB/FVG geometry.

A same-M1 breach of both reference boundaries remains ambiguous and is not
forced into a direction. America/New_York is bound explicitly and DST-aware.
"""
from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

import cibo_atlas_vt31_pre_departure_structure_lab as lab
import vt31_r8_sparse_reference_forensics as sparse
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt31_silver_bullet_r2_2 import _Raid


def first_directional_breach(bars: tuple[Any, ...], reference: Any) -> _Raid | None:
    """Return the first one-sided breach without looking ahead to later sweeps."""
    for index, bar in enumerate(bars):
        high = lab.dec(bar.high) > reference.high
        low = lab.dec(bar.low) < reference.low
        if high and low:
            return _Raid(index, DemoTradingSetupSide.SHORT, True, True)
        if high:
            return _Raid(index, DemoTradingSetupSide.SHORT, True, False)
        if low:
            return _Raid(index, DemoTradingSetupSide.LONG, False, True)
    return None


def main() -> None:
    sparse.NY = ZoneInfo("America/New_York")
    lab._detect_raid = first_directional_breach
    lab.main()


if __name__ == "__main__":
    main()
