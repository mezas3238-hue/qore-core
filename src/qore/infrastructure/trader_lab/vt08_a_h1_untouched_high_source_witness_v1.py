"""VT08 bullish target physical H1 HIGH witnesses, no TTrades target selector.

Author source: bullish direction targets previous HTF highs NOT already
taken out. This module records all H1-high candidates from native M15
bars after observed gap-free formation and removes each on a later M15
high >= level, as of each frozen C3 decision. NEVER read after decision,
infer that every H1 high is relevant, or choose a PnL-optimal target.

An observational M15 stream interrupted by any gap invalidates previous
"untouched" proof; reset, don't assume absence of trading through gaps.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_a_m30m3_raw_bar_custody_v1 import (
    MARKETS,
    _bar_receipt,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SOURCE: Final = "https://ttrades.com/how-to-set-price-targets-using-the-fractal-model/"
SCHEMA: Final = "qore.vt08.a.observed_h1_untouched_high_witness.v1"
CATALOG_SCHEMA: Final = "qore.vt08.a_b.market_raw_custody_catalog.v1"
M15: Final = timedelta(minutes=15)


def _utc(value: datetime) -> datetime:
    if value.utcoffset() is None:
        raise ValueError("native source date lacks timezone")
    return value.astimezone(UTC)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat()


def _read_iso(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("source decision time must be ISO-8601 string")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("bad source decision timestamp") from exc
    return _utc(result)


@dataclass(frozen=True, slots=True)
class UntouchedH1High:
    high: Decimal
    origin_h1_opened_at: datetime
    origin_h1_closed_at: datetime
    h1_source_m15_bar_ids: tuple[str, ...]


@dataclass(slots=True)
class H1HighState:
    """A strictly chronological observed-bar state, reset on any gap."""
    market: str
    m15_raw_sha: str
    active: list[UntouchedH1High] = field(default_factory=list)
    last_four: deque[Vt08B01Bar] = field(default_factory=lambda: deque(maxlen=4))
    previous_close: datetime | None = None
    source_gaps: int = 0
    h1_formed: int = 0
    levels_touched: int = 0

    def advance(self, bar: Vt08B01Bar) -> None:
        opened, closed = _utc(bar.opened_at), _utc(bar.closed_at)
        if closed - opened != M15:
            raise ValueError("non-native M15 bar duration")
        if self.previous_close is not None:
            if opened < self.previous_close:
                raise ValueError("overlapping/out-of-order native M15 bars")
            if opened > self.previous_close:
                self.source_gaps += 1
                self.active.clear()
                self.last_four.clear()
        # Exclude a level when it is touched by ANY later observed M15,
        # including partial progress through current H1.
        survivors = [x for x in self.active if bar.high < x.high]
        self.levels_touched += len(self.active) - len(survivors)
        self.active = survivors
        self.last_four.append(bar)
        self.previous_close = closed
        if closed.minute != 0 or closed.second or closed.microsecond:
            return
        if len(self.last_four) != 4:
            return
        candles = list(self.last_four)
        h1_begin = closed - timedelta(hours=1)
        if any(
            _utc(x.opened_at) != h1_begin + i * M15
            or _utc(x.closed_at) != h1_begin + (i + 1) * M15
            for i, x in enumerate(candles)
        ):
            return
        h = max(c.high for c in candles)
        receipts = tuple(
            str(_bar_receipt(c, self.m15_raw_sha, "M15")["source_bar_id"])
            for c in candles
        )
        self.active.append(UntouchedH1High(
            high=h, origin_h1_opened_at=h1_begin,
            origin_h1_closed_at=closed, h1_source_m15_bar_ids=receipts,
        ))
        self.h1_formed += 1


def witness_events(
    *,
    market: str,
    source_catalog: dict[str, object],
    native_m15: tuple[Vt08B01Bar, ...] | list[Vt08B01Bar],
    raw_m15_sha256: str,
) -> dict[str, object]:
    """Inspect complete frozen A family chronology with causal gap quarantine."""
    if market not in MARKETS or source_catalog.get("market") != market:
        raise ValueError("frozen market mismatch")
    if source_catalog.get("schema") != CATALOG_SCHEMA:
        raise ValueError("frozen A/B catalog schema mismatch")
    custody = source_catalog.get("source_raw_market_map")
    shas = source_catalog.get("pinned_raw_shas")
    if (
        not isinstance(custody, dict)
        or not isinstance(shas, list)
        or set(custody) != set(shas)
        or custody.get(raw_m15_sha256) != market
        or any(v != market for v in custody.values())
    ):
        raise ValueError("native M15 feed not pinned to correct market")
    if any(
        source_catalog.get(key) is not False
        for key in (
            "author_fidelity_certified",
            "cognitive_certified",
            "economic_gates_certified",
            "pnl_evaluated",
        )
    ) or source_catalog.get("orders") != 0 or source_catalog.get("fills") != 0:
        raise ValueError("source catalog falsely claims trading authority")
    cases = source_catalog.get("source_only_events")
    bar_catalog = source_catalog.get("bar_catalog")
    if not isinstance(cases, list) or not isinstance(bar_catalog, dict):
        raise ValueError("missing frozen source events and bar catalog")
    if len(cases) != source_catalog.get("source_only_event_count"):
        raise ValueError("frozen source event count mismatch")
    if not native_m15:
        raise ValueError("no native historical M15")
    by_open = {_utc(x.opened_at): x for x in native_m15}
    if len(by_open) != len(native_m15):
        raise ValueError("native M15 bar clocks duplicated")
    st = H1HighState(market=market, m15_raw_sha=raw_m15_sha256)
    by_time = sorted(cases, key=lambda e: str(e["decision_at_utc"]))
    next_bar = 0
    results: list[dict[str, object]] = []
    unique_decisions: set[str] = set()
    missing_quote_cutoff = 0
    all_have_multiple = 0
    for case in by_time:
        if not isinstance(case, dict) or case.get("market") != market:
            raise ValueError("cross-market candidate in frozen catalog")
        if case.get("source_complete") is not False:
            raise ValueError("false TTrades author-complete event")
        t = _read_iso(case.get("decision_at_utc"))
        c2 = _read_iso(case.get("c2_opened_at_utc"))
        if t != c2 + timedelta(minutes=30):
            raise ValueError("C3 decision clock invalid")
        key = _iso(t)
        if key in unique_decisions:
            raise ValueError("duplicate C3 decision in source-only event set")
        unique_decisions.add(key)
        while next_bar < len(native_m15) and _utc(native_m15[next_bar].closed_at) <= t:
            st.advance(native_m15[next_bar])
            next_bar += 1
        has_bar_at_cutoff = st.previous_close == t
        if not has_bar_at_cutoff:
            missing_quote_cutoff += 1
        groups = case.get("source_bar_groups")
        if not isinstance(groups, dict):
            raise ValueError("frozen source bar groups missing")
        ids = groups.get("c2_m15_raw_bar_receipts")
        if not isinstance(ids, list) or len(ids) != 2:
            raise ValueError("C2 authentic M15 bars missing")
        candles = []
        for i, bar_id in enumerate(ids):
            raw = bar_catalog.get(bar_id)
            if not isinstance(raw, dict):
                raise ValueError("C2 source M15 bar absent")
            if (
                raw.get("profile") != "M15"
                or raw.get("market") != market
                or raw.get("source_raw_sha256") != raw_m15_sha256
                or _read_iso(raw.get("opened_at_utc")) != c2 + i * M15
                or _read_iso(raw.get("closed_at_utc")) != c2 + (i + 1) * M15
            ):
                raise ValueError("C2 M15 bar/market/time mismatch")
            native = by_open.get(c2 + i * M15)
            if native is None or _utc(native.closed_at) != c2 + (i + 1) * M15:
                raise ValueError("C2 M15 native original missing")
            attested = _bar_receipt(native, raw_m15_sha256, "M15")
            if (
                raw.get("source_bar_id") != attested["source_bar_id"]
                or tuple(raw.get("ohlc", ())) != tuple(attested["ohlc"])
                or _read_iso(raw.get("available_at_utc")) != _utc(native.closed_at)
            ):
                raise ValueError("C2 M15 source catalog differs from native original")
            if not native.close.is_finite() or native.close <= 0:
                raise ValueError("invalid native C2 close")
            candles.append(native.close)
        c2_close = candles[-1]
        targets = [
            {
                "high": str(x.high),
                "origin_h1_opened_at_utc": _iso(x.origin_h1_opened_at),
                "origin_h1_available_at_utc": _iso(x.origin_h1_closed_at),
                "origin_source_m15_bar_ids": x.h1_source_m15_bar_ids,
                "higher_than_c2_close_proxy": x.high > c2_close,
                "continuity_since_origin": "OBSERVED_GAP_FREE_M15_ONLY",
                "author_target_relevance_verified": False,
            }
            for x in st.active
            if x.origin_h1_closed_at <= t
        ] if has_bar_at_cutoff else []
        if len(targets) > 1:
            all_have_multiple += 1
        results.append({
            "market": market, "decision_at_utc": key,
            "c2_opened_at_utc": _iso(c2),
            "observed_m15_c3_close_available": has_bar_at_cutoff,
            "c2_close_price_source_proxy": str(c2_close),
            "untouched_h1_high_candidates": targets,
            "witness_count": len(targets),
            "candidate_targets_above_c2_close_proxy": sum(
                1 for x in targets if x["higher_than_c2_close_proxy"]
            ),
            "author_target_selected": False,
            "author_target_validated": False,
            "broker_target_order_created": False,
            "pnl_consulted": False,
        })
    return {
        "schema": SCHEMA,
        "market": market,
        "input_m15_source_sha256": raw_m15_sha256,
        "author_source": SOURCE,
        "frozen_source_events": len(results),
        "cases_missing_m15_at_c3_cutoff": missing_quote_cutoff,
        "cases_multiple_observed_h1_highs": all_have_multiple,
        "observed_h1_highs_formed": st.h1_formed,
        "observed_h1_highs_touched": st.levels_touched,
        "source_gap_resets": st.source_gaps,
        "witnesses": results,
        "source_complete_entries": 0,
        "broker_fills": 0,
        "profit_factor": None,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "certified": False,
    }


def run_from_files(market: str, catalog_path: Path, m15_path: Path) -> dict[str, object]:
    if not m15_path.is_file() or not catalog_path.is_file():
        raise ValueError("source files missing")
    m15_sha = hashlib.sha256(m15_path.read_bytes()).hexdigest()
    _, source_market, _, _, m15 = load_market_evidence(m15_path)
    if source_market != market:
        raise ValueError("physical M15 market does not match requested market")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    return witness_events(
        market=market, source_catalog=catalog,
        native_m15=tuple(m15), raw_m15_sha256=m15_sha,
    )
