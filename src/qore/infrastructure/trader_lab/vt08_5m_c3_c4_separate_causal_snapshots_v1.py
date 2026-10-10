"""P0 A: separated C3-closed and C4-M15-closed observations, never fills.

On the consumed 1095D M15 source, reconstruct source candles and check the
observed-at clock BEFORE admitting each observation. A C3 snapshot cannot
include C4 OHLC; a C4 observation cannot exist before that M15 has CLOSED.
C3 closure is SHAPE_ONLY until real POI, CISD/PS and source trade terms are
independently proven. Research only, no economics or LIVE authority.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_c3_delayed_closure_c4_shape_census_v1 import (
    c2_reversal_closure,
    c3_body_closure,
)
from qore.infrastructure.trader_lab.vt08_5m_source_bias_asof_attestation_v1 import (
    SOURCE_SHA,
    _sha_bars,
)
from qore.infrastructure.trader_lab.vt08_5m_ttrades_c2_c3_source_eq_range_v1 import (
    source_eq_after_closure,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
    _window_bars,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_v1 import (
    ANCHORS_NY,
    EXPANSION_MARKETS,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import (
    Vt08B01Bar,
    protected_swings_in_candle2,
    source_h4_from_m15,
)

SCHEMA: Final = "qore.vt08.5m.c3_closure_c4.two_clocks.shape.v1"
_NY = ZoneInfo("America/New_York")


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("UTC aware source timestamp required")
    return dt.astimezone(UTC)


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ClosedC3SourceShape:
    """Immutable C3-close-only evidence: no C4 bar, fill, future PnL or target."""

    market: str
    side: str
    origin_id: str
    c3_closed_at: datetime
    snapshot_fingerprint: str
    c3_eq: Decimal
    c3_eq_range_basis: str
    c3_ps_proxies: tuple[tuple[str, str, str], ...]
    next_c4_owner_permitted: bool
    c2_sweep_state: str
    strong_body_engulf_proxy: bool
    c3_m15_sha256: str
    status: str = "SHAPE_ONLY_NOT_SOURCE_COMPLETE"

    def payload(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "market": self.market,
            "side": self.side,
            "origin_id": self.origin_id,
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "observed_at": _utc(self.c3_closed_at).isoformat(),
            "as_of_stage": "C3_CLOSED",
            "eq_intra_c3_level": str(self.c3_eq),
            "eq_intra_c3_basis": self.c3_eq_range_basis,
            "c3_ps_internal_proxies": self.c3_ps_proxies,
            "c3_m15_sha256": self.c3_m15_sha256,
            "next_c4_owner_permitted": self.next_c4_owner_permitted,
            "c2_sweep_state": self.c2_sweep_state,
            "strong_body_engulf_proxy": self.strong_body_engulf_proxy,
            "daily_eq_context": "NOT_ATTESTED_IN_THIS_BUNDLE",
            "poi_source_confirmed": False,
            "c3_ps_source_confirmed": False,
            "c4_ps_source_confirmed": False,
            "no_c4_ohlc_consumed": True,
            "methodology_status": self.status,
            "order_authorized": False,
            "trades_executed": 0,
        }


def c3_closed_source_shape(
    *,
    market: str,
    c1: Vt08B01Bar,
    c2: Vt08B01Bar,
    c3: Vt08B01Bar,
    c3_m15: tuple[Vt08B01Bar, ...],
    observed_at: datetime,
) -> ClosedC3SourceShape | None:
    if market not in EXPANSION_MARKETS:
        raise ValueError("market out of research scope")
    now = _utc(observed_at)
    if not (
        _utc(c1.closed_at) == _utc(c2.opened_at)
        and _utc(c2.closed_at) == _utc(c3.opened_at)
    ):
        raise ValueError("C1 C2 C3 not H4-contiguous")
    if _utc(c3.closed_at) > now:
        raise ValueError("C3 closure unknowable until H4 closes")
    if c2_reversal_closure(c1, c2):
        return None
    variants = c3_body_closure(c2, c3)
    if not variants:
        return None
    if len(variants) != 1:
        raise ValueError("C3 body shape direction ambiguous")
    variant = variants[0]
    if len(c3_m15) != 16:
        raise ValueError("C3 needs all 16 independently closed M15 bars")
    t = _utc(c3.opened_at)
    for bar in c3_m15:
        if _utc(bar.opened_at) != t or _utc(bar.closed_at) != t + timedelta(
            minutes=15
        ) or _utc(bar.closed_at) > now:
            raise ValueError("future, missing or overlapping C3 M15")
        t = _utc(bar.closed_at)
    if t != _utc(c3.closed_at) or (
        c3_m15[0].open != c3.open
        or c3_m15[-1].close != c3.close
        or max(b.high for b in c3_m15) != c3.high
        or min(b.low for b in c3_m15) != c3.low
    ):
        raise ValueError("C3 H4 candle not authenticated by closed M15")
    # Reuses ONLY C3 M15. The first-M15 level is a proxy, NOT an author POI.
    proxy_level = (
        c3_m15[0].low
        if variant.side is DemoTradingSetupSide.LONG
        else c3_m15[0].high
    )
    raw_ps = protected_swings_in_candle2(
        c3_m15, side=variant.side, important_level=proxy_level
    )
    for ps in raw_ps:
        if not (_utc(c3.opened_at) <= _utc(ps.opposing_series_opened_at)
                < _utc(ps.confirmed_at) <= _utc(c3.closed_at)):
            raise ValueError("C3 proxy PS consumed C2 or future bar")
    ps_proxies = tuple(
        (ps.opposing_series_opened_at.isoformat(),
         ps.confirmed_at.isoformat(), str(ps.price)) for ps in raw_ps
    )
    eq = source_eq_after_closure(
        c3, candle_label="C3", intended_side=variant.side,
        closure_adjudicated=True, decision_at=now,
    )
    if eq is None or eq.evidence_closed_at != c3.closed_at:
        raise ValueError("C3 source-range EQ not available at close")
    c4_local = c3.closed_at.astimezone(_NY)
    owner = (
        c4_local.hour in ANCHORS_NY
        and c4_local.minute == 0 and c4_local.second == 0
        and c4_local.microsecond == 0
    )
    swept_hi, swept_lo = c2.high > c1.high, c2.low < c1.low
    sweep_state = (
        "DUAL_SWEEP_UNADJUDICATED" if swept_hi and swept_lo else
        "ONE_SIDE_SWEEP_FAILED_CLOSURE" if swept_hi or swept_lo else
        "NO_REFERENCE_SWEEP"
    )
    origin = {
        "schema": SCHEMA,
        "market": market,
        "ltf_profile": "M15_STANDARD",
        "source_family": "C3_CLOSURE_TO_C4_SHAPE",
        "c2_origin_at": _utc(c2.opened_at).isoformat(),
        "c3_origin_at": _utc(c3.opened_at).isoformat(),
        "side": variant.side.value,
    }
    # Source identity excludes the mutable/evolving C4 observation and PnL.
    origin_id = "vt08-c3c4-source:" + _digest(origin)
    c3_facts = {
        "origin": origin,
        "c1": [str(c1.high), str(c1.low), _utc(c1.closed_at).isoformat()],
        "c2": [str(c2.open), str(c2.high), str(c2.low), str(c2.close)],
        "c3": [str(c3.open), str(c3.high), str(c3.low), str(c3.close)],
        "c3_m15_sha": _sha_bars(c3_m15),
        "c3_ps_proxies": ps_proxies,
        "eq": eq.payload(),
    }
    return ClosedC3SourceShape(
        market=market,
        side=variant.side.value,
        origin_id=origin_id,
        c3_closed_at=c3.closed_at,
        snapshot_fingerprint=_digest(c3_facts),
        c3_eq=eq.eq,
        c3_eq_range_basis=eq.basis.value,
        c3_ps_proxies=ps_proxies,
        next_c4_owner_permitted=owner,
        c2_sweep_state=sweep_state,
        strong_body_engulf_proxy=variant.body_engulfed,
        c3_m15_sha256=_sha_bars(c3_m15),
    )


def c4_first_m15_closed_observation(
    c3_shape: ClosedC3SourceShape,
    *,
    first_c4_m15: Vt08B01Bar,
    observed_at: datetime,
) -> dict[str, object]:
    """A DIFFERENT event, impossible before C4 first M15 close."""
    now = _utc(observed_at)
    if (
        _utc(first_c4_m15.opened_at) != _utc(c3_shape.c3_closed_at)
        or _utc(first_c4_m15.closed_at) != (
            _utc(c3_shape.c3_closed_at) + timedelta(minutes=15)
        )
    ):
        raise ValueError("C4 observation is not first contiguous M15")
    if _utc(first_c4_m15.closed_at) > now:
        raise ValueError("cannot observe unclosed C4 M15")
    eq = c3_shape.c3_eq
    bullish = c3_shape.side == DemoTradingSetupSide.LONG.value
    respected = first_c4_m15.close >= eq if bullish else first_c4_m15.close <= eq
    wick_half = (
        first_c4_m15.low >= eq
        if bullish else first_c4_m15.high <= eq
    )
    observation = {
        "schema": SCHEMA,
        "market": c3_shape.market,
        "origin_id": c3_shape.origin_id,
        "parent_snapshot_fingerprint": c3_shape.snapshot_fingerprint,
        "as_of_stage": "C4_FIRST_M15_CLOSED",
        "observed_at": _utc(first_c4_m15.closed_at).isoformat(),
        "c4_first_m15_sha256": _sha_bars((first_c4_m15,)),
        "c3_eq_level_used": str(eq),
        "eq_half_respected_at_closed_m15": respected,
        "wick_in_respected_half": wick_half,
        "poi_source_confirmed": False,
        "order_authorized": False,
        "trades_executed": 0,
    }
    observation["snapshot_fingerprint"] = _digest(observation)
    return observation


def audit_market(path: Path) -> dict[str, object]:
    fp, market, checked, sha, rows = load_market_evidence(path)
    if market not in EXPANSION_MARKETS or sha != SOURCE_SHA:
        raise ValueError("wrong consumed research M15 source")
    bars = {x.opened_at: x for x in rows}
    if len(bars) != len(rows):
        raise ValueError("duplicate M15 source open")
    counts: Counter[str] = Counter()
    source: list[dict[str, object]] = []
    updates: list[dict[str, object]] = []
    for anchor in rows:
        local = anchor.opened_at.astimezone(_NY)
        if local.hour not in ANCHORS_NY or local.minute != 0 or local.second != 0:
            continue
        c1 = source_h4_from_m15(bars, opened_at_local=local - timedelta(hours=8))
        c2 = source_h4_from_m15(bars, opened_at_local=local - timedelta(hours=4))
        c3 = source_h4_from_m15(bars, opened_at_local=local)
        if c1 is None or c2 is None or c3 is None:
            continue
        m15 = _window_bars(
            bars, opened_at=c3.opened_at, closed_at=c3.closed_at,
        )
        if m15 is None:
            raise AssertionError("H4 C3 exists but source 16 M15 missing")
        # Invariant: C3 snapshot sees NOTHING from following C4.
        shape = c3_closed_source_shape(
            market=market, c1=c1, c2=c2, c3=c3, c3_m15=m15,
            observed_at=c3.closed_at,
        )
        if shape is None:
            continue
        counts["C3_CLOSED_SHAPES"] += 1
        if shape.next_c4_owner_permitted:
            counts["C4_OWNER_PERMITTED"] += 1
        else:
            counts["C4_OUTSIDE_OWNER_SHAPE_ONLY"] += 1
        if shape.strong_body_engulf_proxy:
            counts["BODY_ENGULF_STRONG_PROXY"] += 1
        if shape.c3_ps_proxies:
            counts["C3_INTERNAL_CISD_PS_PROXY"] += 1
        if shape.c2_sweep_state == "DUAL_SWEEP_UNADJUDICATED":
            counts["C2_DUAL_SWEEP_UNADJUDICATED"] += 1
        source.append(shape.payload())
        c4_first = bars.get(c3.closed_at)
        if c4_first is not None:
            update = c4_first_m15_closed_observation(
                shape, first_c4_m15=c4_first,
                observed_at=c4_first.closed_at,
            )
            updates.append(update)
            counts["C4_M15_CLOSED_OBSERVATIONS"] += 1
    if len(source) != counts["C3_CLOSED_SHAPES"]:
        raise AssertionError("source C3 count mismatch")
    if len({x["origin_id"] for x in source}) != len(source):
        raise AssertionError("duplicate C3 stable origin IDs")
    return {
        "schema": SCHEMA,
        "market": market,
        "evidence_fingerprint": fp,
        "evidence_checked_at": checked.isoformat(),
        "consumed_source_software_sha": sha,
        "counts": dict(sorted(counts.items())),
        "c3_closed_source_snapshots": source,
        "separate_c4_closed_bar_observations": updates,
        "c3_continuation_family_overlap_under_frozen_c2_partition": 0,
        "unverified_poi": True,
        "candidate_event_approved": False,
        "cognitive_ready": False,
        "trades_executed": 0,
        "pnl_evaluated": False,
        "sealed_7y_accessed": False,
    }
