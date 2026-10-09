"""P0 causal ATR/stop calibration candidate; SHADOW-ONLY, never an MT5 order.

CIBO receives Trader-created valid signals without cognitive admission voting.
This pure module proposes stop geometry only with predecision ATR and verified
structure are available. No future candles, hidden ATR inference, outcomes,
budget overrides, or physical lot computation. QDLE owns actual broker lotage.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext

_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_TIMEFRAME_SECONDS = {"M1": 60, "M15": 900, "H1": 3600, "H4": 14400}
# CIBO CEO research starting grid. No claim of learned/optimal multipliers.
_MULTIPLIERS = {
    ("AUDJPY", "M15"): ("0.5", "1", "1.5"),
    ("AUDJPY", "H1"): ("0.5", "1", "1.75"),
    ("AUDJPY", "H4"): ("0.5", "1", "2"),
    ("EURUSD", "H1"): ("0.5", "1", "1.5"),
    ("EURUSD", "H4"): ("0.5", "1", "1.75"),
    ("GBPJPY", "M15"): ("0.5", "1", "1.75"),
    ("GBPJPY", "H1"): ("0.5", "1", "2"),
    ("GBPJPY", "H4"): ("0.5", "1", "2"),
    ("GBPUSD", "M15"): ("0.5", "1", "1.5"),
    ("GBPUSD", "H1"): ("0.5", "1", "1.75"),
    ("GBPUSD", "H4"): ("0.5", "1", "2"),
    ("NDX100", "M1"): ("0.5", "1", "2"),
    ("XAUUSD", "H1"): ("0.5", "1", "2"),
    ("XAUUSD", "H4"): ("0.5", "1", "2"),
}
_MODES = ("BANK", "MEDIUM", "ATTACK")
ATR_SL_POLICY_VERSION = "CIBO_ATR_SL_SHADOW_PROPOSAL_V1_NO_LIVE"


class CausalATRStopError(ValueError):
    """Invalid, stale or unverifiable predecision stop geometry."""


def _positive(name: str, value: Decimal, *, zero: bool = False) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CausalATRStopError(f"{name}: finite Decimal required")
    if value < 0 or (not zero and value == 0):
        raise CausalATRStopError(f"{name}: positive Decimal required")


def _aware(name: str, value: datetime) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CausalATRStopError(f"{name}: timezone-aware required")


@dataclass(frozen=True, slots=True)
class CausalATR14:
    symbol: str
    timeframe: str
    atr14_price_units: Decimal
    last_bar_closed_at: datetime
    evidence_available_at: datetime
    evidence_sha256: str
    closed_bar_count: int

    def __post_init__(self) -> None:
        _positive("atr14_price_units", self.atr14_price_units)
        _aware("last_bar_closed_at", self.last_bar_closed_at)
        _aware("evidence_available_at", self.evidence_available_at)
        if (
            self.timeframe not in _TIMEFRAME_SECONDS
            or self.symbol not in {x[0] for x in _MULTIPLIERS}
        ):
            raise CausalATRStopError("symbol/timeframe unsupported")
        if type(self.closed_bar_count) is not int or self.closed_bar_count < 15:
            raise CausalATRStopError("ATR14 requires a sufficient closed-bar warmup")
        if not isinstance(self.evidence_sha256, str) or not _SHA.fullmatch(self.evidence_sha256):
            raise CausalATRStopError("ATR evidence_sha256 required")
        if self.evidence_available_at < self.last_bar_closed_at:
            raise CausalATRStopError("ATR evidence cannot predate the last closed bar")


@dataclass(frozen=True, slots=True)
class CausalATRStopCandidate:
    status: str
    mode: str
    symbol: str
    timeframe: str
    entry_price: Decimal
    original_stop_price: Decimal
    proposed_stop_price: Decimal
    proposed_stop_distance_price: Decimal
    multiplier: Decimal
    atr14_price_units: Decimal
    evidence_sha256: str
    last_bar_closed_at: datetime
    decision_at: datetime
    reason_codes: tuple[str, ...]
    policy_version: str = ATR_SL_POLICY_VERSION
    is_live_authorized: bool = False


def propose_cibo_atr_stop_shadow(
    *, mode: str, symbol: str, timeframe: str, side: str,
    entry_price: Decimal, original_stop_price: Decimal,
    tick_size_price: Decimal, broker_min_stop_distance_price: Decimal,
    structure_min_stop_distance_price: Decimal | None,
    decision_at: datetime, atr: CausalATR14,
) -> CausalATRStopCandidate:
    """Compute a counterfactual stop; NEVER resize/approve a trade or use outcome.

    structure_min_stop_distance_price MUST be independently established from
    predecision market structure. If absent, the candidate is ONLY a diagnostic.
    A too-tight ATR stop is rejected, NOT silently clipped or retrospectively
    relabeled with the historical Trader's R.
    """
    if mode not in _MODES or side not in ("BUY", "SELL"):
        raise CausalATRStopError("recognized CIBO mode and trade side required")
    if not isinstance(atr, CausalATR14):
        raise CausalATRStopError("authentic typed predecision ATR evidence required")
    normalized = "NDX100" if symbol == "NAS100" else symbol
    if (atr.symbol not in {normalized, symbol}
        or atr.timeframe != timeframe or (normalized, timeframe) not in _MULTIPLIERS):
        raise CausalATRStopError("ATR symbol/timeframe mismatch")
    _aware("decision_at", decision_at)
    for name, value, zero in (
        ("entry_price", entry_price, False),
        ("original_stop_price", original_stop_price, False),
        ("tick_size_price", tick_size_price, False),
        ("broker_min_stop_distance_price", broker_min_stop_distance_price, True),
    ):
        _positive(name, value, zero=zero)
    if structure_min_stop_distance_price is not None:
        _positive("structure_min_stop_distance_price", structure_min_stop_distance_price, zero=True)
    if ((side == "BUY" and original_stop_price >= entry_price)
        or (side == "SELL" and original_stop_price <= entry_price)):
        raise CausalATRStopError("original stop geometry is invalid")

    if atr.last_bar_closed_at > decision_at or atr.evidence_available_at > decision_at:
        raise CausalATRStopError("ATR future bar/evidence leakage")
    if ((decision_at - atr.last_bar_closed_at).total_seconds()
        > 2 * _TIMEFRAME_SECONDS[timeframe]):
        raise CausalATRStopError("ATR closed-bar evidence stale")
    m = Decimal(_MULTIPLIERS[(normalized, timeframe)][_MODES.index(mode)])
    with localcontext() as ctx:
        ctx.prec = 100
        distance = atr.atr14_price_units * m
        raw_price = entry_price - distance if side == "BUY" else entry_price + distance
        # Round away from entry, never inward, so true risk isn't understated.
        rounded = (
            (raw_price / tick_size_price).to_integral_value(
                rounding=ROUND_FLOOR if side == "BUY" else ROUND_CEILING
            ) * tick_size_price
        )
        true_distance = abs(entry_price - rounded)
    if rounded <= 0:
        raise CausalATRStopError("ATR stop would be nonpositive")
    reasons = []
    if true_distance < broker_min_stop_distance_price:
        reasons.append("BROKER_MIN_STOP_DISTANCE")
    if structure_min_stop_distance_price is None:
        reasons.append("STRUCTURAL_INVALIDATION_NOT_VERIFIED")
    elif true_distance < structure_min_stop_distance_price:
        reasons.append("INVALID_STRUCTURE_TOO_TIGHT")
    return CausalATRStopCandidate(
        status="SHADOW_GEOMETRY_VALID" if not reasons else "SHADOW_NOT_EXECUTABLE",
        mode=mode, symbol=normalized, timeframe=timeframe,
        entry_price=entry_price, original_stop_price=original_stop_price,
        proposed_stop_price=rounded, proposed_stop_distance_price=true_distance,
        multiplier=m, atr14_price_units=atr.atr14_price_units,
        evidence_sha256=atr.evidence_sha256,
        last_bar_closed_at=atr.last_bar_closed_at, decision_at=decision_at,
        reason_codes=tuple(reasons),
    )
