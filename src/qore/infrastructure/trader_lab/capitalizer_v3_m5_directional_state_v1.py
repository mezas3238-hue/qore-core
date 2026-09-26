"""Frozen causal M5 directional-state mapping for Capitalizer V3 research.

The existing CORE microstructure detector describes each completed M5 bar relative to the
previous completed M5 bar. This module maps those already-causal events to a setup-relative
directional state. It does not reinterpret them as reactions to the V3 liquidity level.

LONG:
- bullish evidence: LOW_RAID_REJECTION or HIGH_ACCEPTANCE
- bearish evidence: HIGH_RAID_REJECTION or LOW_ACCEPTANCE

SHORT:
- bullish/bearish interpretation is inverted relative to the trade side.

State:
- ALIGNED: setup-direction evidence exists and opposed evidence does not.
- OPPOSED: opposed-direction evidence exists and aligned evidence does not.
- NEUTRAL: neither side has decisive evidence, or both sides are present.

Break-attempt-only, inside-bar, outside-bar-only, NONE, and mixed directional evidence are
therefore fail-closed NEUTRAL.
"""

from __future__ import annotations

from enum import StrEnum

from qore.infrastructure.trader_lab.capitalizer_exposure_graph import CapitalizerSide
from qore.infrastructure.trader_lab.capitalizer_microstructure_discovery import (
    CapitalizerMicrostructureEvent,
)

IDENTITY = "QORE_CAPITALIZER_V3_M5_DIRECTIONAL_STATE_V1"


class CapitalizerM5DirectionalState(StrEnum):
    ALIGNED = "ALIGNED"
    OPPOSED = "OPPOSED"
    NEUTRAL = "NEUTRAL"


_BULLISH = frozenset(
    {
        CapitalizerMicrostructureEvent.LOW_RAID_REJECTION.value,
        CapitalizerMicrostructureEvent.HIGH_ACCEPTANCE.value,
    }
)
_BEARISH = frozenset(
    {
        CapitalizerMicrostructureEvent.HIGH_RAID_REJECTION.value,
        CapitalizerMicrostructureEvent.LOW_ACCEPTANCE.value,
    }
)


def _signature_events(signature: str) -> frozenset[str]:
    if signature == "NONE":
        return frozenset()
    return frozenset(item for item in signature.split("+") if item)


def classify_m5_directional_state(
    *,
    side: CapitalizerSide,
    microstructure_signature: str,
) -> CapitalizerM5DirectionalState:
    events = _signature_events(microstructure_signature)
    bullish = bool(events & _BULLISH)
    bearish = bool(events & _BEARISH)

    if side is CapitalizerSide.LONG:
        aligned = bullish
        opposed = bearish
    else:
        aligned = bearish
        opposed = bullish

    if aligned and not opposed:
        return CapitalizerM5DirectionalState.ALIGNED
    if opposed and not aligned:
        return CapitalizerM5DirectionalState.OPPOSED
    return CapitalizerM5DirectionalState.NEUTRAL
