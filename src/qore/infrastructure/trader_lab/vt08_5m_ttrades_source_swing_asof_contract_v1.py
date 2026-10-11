"""Source-causal swing contract: HTF closure + proven POI + closed LTF CISD/PS.

Research-only. IMPORTANT: these are auditable structural observations,
NOT author-complete trade signals, broker orders or cognitive admissions.
FVG is the first source-priority POI type currently reconstructable from
three independently CLOSED M15 candles. Swing H/L and CISD retest still D.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.trader_lab.vt08_5m_c3_delayed_closure_c4_shape_census_v1 import (
    c3_body_closure,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    Vt08B01ProtectedSwing,
    protected_swings_in_candle2,
)

_SOURCE_CISD = "https://ttrades.com/how-change-in-the-state-of-delivery-confirms-swing-points/"
_SOURCE_POI = "https://ttrades.com/the-only-points-of-interest-that-actually-matter-for-trading/"
_SOURCE_C2 = "https://ttrades.com/understanding-candle-2-closures-within-the-fractal-model/"
SOURCE_EQ = "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/"


class Family(StrEnum):
    C2_CLOSURE_TO_C3 = "C2_CLOSURE_TO_C3"
    C3_CONTINUATION_INTRAC3 = "C3_CONTINUATION_INTRAC3"
    C3_CLOSURE_TO_C4 = "C3_CLOSURE_TO_C4"


class PoiType(StrEnum):
    FVG = "FVG"
    SWING_HIGH_LOW = "SWING_HIGH_LOW"
    CISD_RETEST = "CISD_RETEST"


class ProofStatus(StrEnum):
    CONFIRMED_STRUCTURE_ONLY = "CONFIRMED_STRUCTURE_ONLY"
    WAIT_H4_CLOSURE = "WAIT_H4_CLOSURE"
    WAIT_LTF_CISD = "WAIT_LTF_CISD"
    POI_NOT_ATTESTED = "POI_NOT_ATTESTED"
    DUAL_SWEEP_UNADJUDICATED = "DUAL_SWEEP_UNADJUDICATED"
    MULTIPLE_PS_UNADJUDICATED = "MULTIPLE_PS_UNADJUDICATED"
    NOT_FAMILY_CLOSURE = "NOT_FAMILY_CLOSURE"


def _utc(t: datetime) -> datetime:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("source timestamp must be timezone-aware")
    return t.astimezone(UTC)


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _side_matches_c2(c1: Vt08B01Bar, c2: Vt08B01Bar, side: DemoTradingSetupSide) -> bool:
    inside = c1.low < c2.close < c1.high
    if not inside:
        return False
    swept_low, swept_high = c2.low < c1.low, c2.high > c1.high
    return (
        swept_low and not swept_high if side is DemoTradingSetupSide.LONG
        else swept_high and not swept_low
    )


@dataclass(frozen=True, slots=True)
class PoiReceipt:
    """POI provenance; C2 M15 FVG requires a closed 3-bar source triple."""

    kind: PoiType
    side: DemoTradingSetupSide
    lower: Decimal
    upper: Decimal
    formed_at: datetime
    sources: tuple[Vt08B01Bar, ...]

    def __post_init__(self) -> None:
        _utc(self.formed_at)
        if not self.lower < self.upper:
            raise ValueError("POI range must be positive")

    def fvg_proven_at(self, cutoff: datetime) -> bool:
        if self.kind is not PoiType.FVG or len(self.sources) != 3:
            return False
        a, b, c = self.sources
        if any(
            _utc(x.closed_at) != _utc(y.opened_at)
            for x, y in ((a, b), (b, c))
        ):
            return False
        if any(
            _utc(bar.closed_at) != _utc(bar.opened_at) + timedelta(minutes=15)
            for bar in self.sources
        ):
            return False
        if _utc(self.formed_at) != _utc(c.closed_at) or _utc(c.closed_at) > _utc(cutoff):
            return False
        lo, hi = (
            (a.high, c.low) if self.side is DemoTradingSetupSide.LONG
            else (c.high, a.low)
        )
        return lo < hi and (lo, hi) == (self.lower, self.upper)


@dataclass(frozen=True, slots=True)
class SourceSwingReceipt:
    family: Family
    side: DemoTradingSetupSide
    origin_id: str
    status: ProofStatus
    evaluated_at: datetime
    htf_closure_known_at: datetime
    poi_first_touched_at: datetime | None
    cisd_confirmed_at: datetime | None
    swing_point_confirmed_at: datetime | None
    protected_swing_price: Decimal | None
    cisd_level: Decimal | None
    cisd_opposing_series_started_at: datetime | None
    poi_type: PoiType | None
    poi_form_at: datetime | None
    is_c2_dual_sweep: bool
    used_ltf_bar_count: int
    cognitive_ready: bool = False
    orders_authorized: bool = False
    pnl_evaluated: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "family": self.family.value,
            "side": self.side.value,
            "origin_id": self.origin_id,
            "status": self.status.value,
            "evaluated_at": _utc(self.evaluated_at).isoformat(),
            "htf_closure_known_at": _utc(self.htf_closure_known_at).isoformat(),
            "poi_first_touched_at": (
                _utc(self.poi_first_touched_at).isoformat()
                if self.poi_first_touched_at else None
            ),
            "cisd_confirmed_at": (
                _utc(self.cisd_confirmed_at).isoformat()
                if self.cisd_confirmed_at else None
            ),
            "swing_point_confirmed_at": (
                _utc(self.swing_point_confirmed_at).isoformat()
                if self.swing_point_confirmed_at else None
            ),
            "protected_swing_price": (
                str(self.protected_swing_price) if self.protected_swing_price else None
            ),
            "cisd_level": str(self.cisd_level) if self.cisd_level else None,
            "cisd_opposing_series_started_at": (
                _utc(self.cisd_opposing_series_started_at).isoformat()
                if self.cisd_opposing_series_started_at else None
            ),
            "poi_type": self.poi_type.value if self.poi_type else None,
            "poi_formed_at": (
                _utc(self.poi_form_at).isoformat() if self.poi_form_at else None
            ),
            "c2_double_sweep": self.is_c2_dual_sweep,
            "used_ltf_bar_count": self.used_ltf_bar_count,
            "authority_sources": [_SOURCE_CISD, _SOURCE_POI, _SOURCE_C2],
            "source_status": "STRUCTURE_RESEARCH_NOT_SOURCE_COMPLETE",
            "cognitive_ready": False,
            "orders_authorized": False,
            "pnl_evaluated": False,
        }


def evaluate_source_swing_asof(
    *,
    market: str,
    family: Family,
    side: DemoTradingSetupSide,
    c1: Vt08B01Bar,
    c2: Vt08B01Bar,
    c3: Vt08B01Bar | None,
    ltf_bars: tuple[Vt08B01Bar, ...],
    poi: PoiReceipt | None,
    decision_at: datetime,
) -> SourceSwingReceipt:
    """Evidence-based causal gate, **not** a SOURCE_COMPLETE signal.

    C2 closure: LTF belongs C2, HTF C2 confirmation only after its close.
    C3 continuation: HTF prior C2 closed, LTF belongs C3, C3 final H4
    must NOT be supplied or accessed for in-C3 decision.
    C3 closure -> C4: C3 H4 closed, LTF belongs C3 OR current C4
    prefix; C4 full H4 is NEVER necessary or inspected.
    """
    now = _utc(decision_at)
    if _utc(c1.closed_at) != _utc(c2.opened_at):
        raise ValueError("C1/C2 are not contiguous")
    if _utc(c2.closed_at) != _utc(c2.opened_at) + timedelta(hours=4):
        raise ValueError("requires complete 4H C2")
    if c3 is not None and _utc(c3.opened_at) != _utc(c2.closed_at):
        raise ValueError("C3 cannot precede end of C2")
    if family is Family.C3_CLOSURE_TO_C4:
        if c3 is None:
            raise ValueError("C3 H4 close is required for C4 family")
        if _utc(c3.closed_at) != _utc(c3.opened_at) + timedelta(hours=4):
            raise ValueError("C3 H4 must span exactly 4h")
        htf_close = c3.closed_at
    else:
        # C3 HTF info never inspected for C3_CONTINUATION_INTRAC3.
        htf_close = c2.closed_at
    origin = {
        "market": market,
        "family": family.value,
        "side": side.value,
        "c1_at": _utc(c1.opened_at).isoformat(),
        "c2_at": _utc(c2.opened_at).isoformat(),
    }
    stable_id = "vt08-source-swing:" + _digest(origin)

    def result(
        status: ProofStatus,
        *,
        touched: datetime | None = None,
        ps: Vt08B01ProtectedSwing | None = None,
    ) -> SourceSwingReceipt:
        confirmed = (
            max(_utc(htf_close), _utc(ps.confirmed_at))
            if ps else None
        )
        return SourceSwingReceipt(
            family=family, side=side, origin_id=stable_id,
            status=status, evaluated_at=decision_at,
            htf_closure_known_at=htf_close,
            poi_first_touched_at=touched,
            cisd_confirmed_at=ps.confirmed_at if ps else None,
            swing_point_confirmed_at=confirmed if ps else None,
            protected_swing_price=ps.price if ps else None,
            cisd_level=ps.cisd_level if ps else None,
            cisd_opposing_series_started_at=(
                ps.opposing_series_opened_at if ps else None
            ),
            poi_type=poi.kind if poi else None,
            poi_form_at=poi.formed_at if poi else None,
            is_c2_dual_sweep=c2.low < c1.low and c2.high > c1.high,
            used_ltf_bar_count=len(ltf_bars),
        )

    # Dual sweep cannot be classified from latest CISD: leave source-D.
    if c2.low < c1.low and c2.high > c1.high:
        return result(ProofStatus.DUAL_SWEEP_UNADJUDICATED)
    if _utc(htf_close) > now:
        return result(ProofStatus.WAIT_H4_CLOSURE)
    if family in {Family.C2_CLOSURE_TO_C3, Family.C3_CONTINUATION_INTRAC3}:
        if not _side_matches_c2(c1, c2, side):
            return result(ProofStatus.NOT_FAMILY_CLOSURE)
    else:
        assert c3 is not None
        shapes = c3_body_closure(c2, c3)
        if not any(item.side is side for item in shapes):
            return result(ProofStatus.NOT_FAMILY_CLOSURE)
        if _side_matches_c2(c1, c2, side):
            return result(ProofStatus.NOT_FAMILY_CLOSURE)
        # C3 closure follows an earlier FAILED C2 SWEEP (not a generic
        # no-sweep body close), as stated by the 2026-05 author model.
        if not (c2.low < c1.low or c2.high > c1.high):
            return result(ProofStatus.NOT_FAMILY_CLOSURE)

    if family is Family.C2_CLOSURE_TO_C3:
        expected_open, expected_end = _utc(c2.opened_at), _utc(c2.closed_at)
    elif family is Family.C3_CONTINUATION_INTRAC3:
        expected_open, expected_end = _utc(c2.closed_at), _utc(c2.closed_at) + timedelta(hours=4)
    else:
        assert c3 is not None
        # A C3-only sequence OR newly forming C4 sequence is valid;
        # never splice both into one opposing-series replay.
        expected_open = (
            _utc(c3.opened_at) if ltf_bars and _utc(ltf_bars[0].opened_at)
            < _utc(c3.closed_at) else _utc(c3.closed_at)
        )
        expected_end = expected_open + timedelta(hours=4)
    if ltf_bars:
        if _utc(ltf_bars[0].opened_at) != expected_open:
            raise ValueError("LTF evidence must begin exactly at family window")
        prev = expected_open
        for bar in ltf_bars:
            if _utc(bar.opened_at) != prev:
                raise ValueError("LTF bars missing or reordered")
            if _utc(bar.closed_at) != prev + timedelta(minutes=15):
                raise ValueError("LTF must be exact closed M15")
            if _utc(bar.closed_at) > now or _utc(bar.closed_at) > expected_end:
                raise ValueError("LTF future M15 cannot be consumed")
            prev = _utc(bar.closed_at)
    if poi is None or not poi.fvg_proven_at(now):
        return result(ProofStatus.POI_NOT_ATTESTED)
    if poi.side is not side:
        return result(ProofStatus.POI_NOT_ATTESTED)
    # This V1 authenticates only preexisting M15 FVGs; it does not yet
    # certify priority among several FVGs or HTF swing relevance.
    if family is Family.C3_CONTINUATION_INTRAC3:
        if not (_utc(c2.opened_at) <= _utc(poi.sources[0].opened_at)
                and _utc(poi.formed_at) <= _utc(c2.closed_at)):
            return result(ProofStatus.POI_NOT_ATTESTED)
    touches = [
        bar for bar in ltf_bars
        if _utc(bar.opened_at) >= _utc(poi.formed_at)
        and bar.low <= poi.upper and bar.high >= poi.lower
    ]
    if not touches:
        return result(ProofStatus.WAIT_LTF_CISD)
    first_touch = touches[0].closed_at
    # A FVG existing at the time of the touched M15 bar's OPEN is required.
    if _utc(poi.formed_at) > _utc(touches[0].opened_at):
        return result(ProofStatus.POI_NOT_ATTESTED)
    important = poi.lower if side is DemoTradingSetupSide.LONG else poi.upper
    matches = tuple(
        ps for ps in protected_swings_in_candle2(
            ltf_bars, side=side, important_level=important
        )
        if _utc(ps.confirmed_at) > _utc(first_touch)
    )
    if not matches:
        return result(ProofStatus.WAIT_LTF_CISD, touched=first_touch)
    if len(matches) != 1:
        return result(ProofStatus.MULTIPLE_PS_UNADJUDICATED, touched=first_touch)
    ps = matches[0]
    if _utc(ps.opposing_series_opened_at) < expected_open:
        raise ValueError("CISD opposing series from earlier family window")
    if _utc(ps.confirmed_at) > now:
        raise ValueError("CISD confirmation cannot be future")
    return result(ProofStatus.CONFIRMED_STRUCTURE_ONLY, touched=first_touch, ps=ps)
