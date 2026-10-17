"""VT08 B R13: C2 closure and three-M30-pivot causal non-equivalence.

Frozen A R3 positive universe, independently reconstructed M30 OHLC from
original cTrader M15 and independently cross-checked to original M3
receipts. A bullish C2 sweep below C1's low logically makes C1 NOT
a standard bullish three-M30-bar pivot, while a central C2 pivot needs
future C3.close and is UNKNOWN as-of the proposed C3.open entry.
This proves neither absence nor presence of an author-valid *M3*
protected swing. No PnL, author signal promotion or operational decisions.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _raw_bars,
    _verify_bar,
)
from qore.infrastructure.trader_lab.vt08_b_r10_three_h1_current_asof_v1 import (
    PINNED_M15,
    _window,
)
from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import (
    STAGE,
    audit_cisd_htf_sequence,
)

SCHEMA = "qore.vt08.b.r13.c2_m30_threebar_pivot_temporal_non_equivalence.v1"
M3 = timedelta(minutes=3)
M15 = timedelta(minutes=15)
M30 = timedelta(minutes=30)


def audit_m30_pivot_temporal_non_equivalence(
    frozen: dict[str, object], *, market: str,
    original_m3: Path, original_m15: Path,
) -> dict[str, object]:
    """R3 2657 source events, with strict original-bar and time provenance."""
    base = audit_cisd_htf_sequence(
        frozen, expected_market=market, native_m3_file=original_m3,
    )
    sha15, b15 = _raw_bars(original_m15, "M15", market)
    if (
        sha15 != PINNED_M15.get(market)
        or frozen.get("source_m15_sha256") != sha15
    ):
        raise ValueError("R13 M15 original market digest changed")
    sha3, b3 = _raw_bars(original_m3, "M3", market)
    if frozen.get("source_m3_sha256") != sha3:
        raise ValueError("R13 M3 digest changed")
    stages = frozen.get("examples_by_stage")
    cases = stages.get(STAGE) if isinstance(stages, dict) else None
    if not isinstance(cases, list) or len(cases) != base[
        "r3_unique_m3_proxy_source_cases"
    ]:
        raise ValueError("R13 frozen source census incompatible")
    counts: Counter[str] = Counter()
    all_cases: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in cases:
        if not isinstance(item, dict) or item.get("market") != market:
            raise ValueError("R13 foreign candidate")
        c2 = _instant(item.get("c2_opened_at_utc"))
        entry = _instant(item.get("decision_at_utc"))
        if entry != c2 + M30:
            raise ValueError("R13 C3 entry clock drift")
        c1 = c2 - M30
        c0 = c1 - M30
        digest = hashlib.sha256(
            (market + "|" + c2.isoformat() + "|" + entry.isoformat()).encode()
        ).hexdigest()
        if digest in seen:
            raise ValueError("R13 duplicate source identity")
        seen.add(digest)
        c0_m30 = _window(b15, sha15, c0, c1)
        c1_m30 = _window(b15, sha15, c1, c2)
        c2_m30 = _window(b15, sha15, c2, entry)
        if c1_m30 is None or c2_m30 is None:
            raise ValueError("R13 cannot reconstruct M30 C1/C2 from original M15")
        r3_c2_m15 = item.get("c2_m15_raw_bar_receipts")
        r3_c1_m3 = item.get("c1_m3_raw_bar_receipts")
        if (
            not isinstance(r3_c2_m15, list) or len(r3_c2_m15) != 2
            or not isinstance(r3_c1_m3, list) or len(r3_c1_m3) != 10
        ):
            raise ValueError("R13 missing native M3/M15 cross-feed receipts")
        for i, bar in enumerate(r3_c2_m15):
            _verify_bar(
                bar, expected_open=c2 + i * M15, minutes=15,
                profile="M15", source_sha=sha15, raw=b15,
            )
        c1_m3_ohlc = []
        for i, bar in enumerate(r3_c1_m3):
            c1_m3_ohlc.append(_verify_bar(
                bar, expected_open=c1 + i * M3, minutes=3,
                profile="M3", source_sha=sha3, raw=b3,
            ))
        c1m = c1_m30["ohlc"]
        c2m = c2_m30["ohlc"]
        if not isinstance(c1m, list) or not isinstance(c2m, list):
            raise ValueError("R13 corrupted M30 aggregate")
        from decimal import Decimal
        a = tuple(Decimal(x) for x in c1m)
        b = tuple(Decimal(x) for x in c2m)
        v = (
            c1_m3_ohlc[0][0],
            max(x[1] for x in c1_m3_ohlc),
            min(x[2] for x in c1_m3_ohlc),
            c1_m3_ohlc[-1][3],
        )
        if a != v:
            raise ValueError("R13 original M15 and M3 C1 aggregates disagree")
        if not (
            b[2] < a[2] and b[1] <= a[1]
            and a[2] < b[3] < a[1] and b[3] > b[0]
        ):
            raise ValueError("R13 C2 not genuine original bullish single-low sweep")
        if b[2] >= a[2]:
            raise ValueError("R13 bullish C1 pivot invalidation not reproduced")
        # A three-M30-bar bullish pivot centered on C1 would require
        # low(C0) > low(C1) AND low(C2) > low(C1). The second conjunct
        # conflicts with observed C2 low sweep; C0 does not matter.
        counts["bullish_c2_source_closure_physical"] += 1
        counts["c1_center_bullish_three_m30_pivot_fails_right_side"] += 1
        counts["c2_center_bullish_three_m30_pivot_waits_for_c3_close"] += 1
        counts["c0_native_m30_available"] += int(c0_m30 is not None)
        all_cases.append({
            "case_id_sha256": digest,
            "market": market, "c1_opened_at_utc": c1.isoformat(),
            "c2_opened_at_utc": c2.isoformat(),
            "c3_opened_at_utc": entry.isoformat(),
            "c1_low_native": str(a[2]), "c2_low_native": str(b[2]),
            "c2_closed_ohlc_native": list(map(str, b)),
            "c1_center_pivot_right_side_pass": False,
            "c2_center_m30_pivot_right_side_asof_c3_open": None,
            "c2_center_m30_pivot_earliest_confirmation_at_utc": (
                entry + M30
            ).isoformat(),
            "ltf_m3_protected_swing_authentic": None,
            "c2_closed_source_semantics": "PHYSICAL_C2_SHAPE_ONLY",
            "original_author_rule_adjudicated": False,
        })
    if len(all_cases) != base["r3_unique_m3_proxy_source_cases"]:
        raise ValueError("R13 source conservation failed")
    return {
        "schema": SCHEMA, "market": market,
        "original_m3_sha256": sha3, "original_m15_sha256": sha15,
        "frozen_events": len(all_cases),
        "counts": dict(counts), "all_case_native_clock_witnesses": all_cases,
        "distinction": (
            "M30 C1 OR C2 STANDARD THREE-BAR PIVOT IS NOT "
            "EQUIVALENT TO AN LTF M3 PROTECTED SWING"
        ),
        "m30_structure_pairing_source": (
            "https://ttrades.com/timeframe-alignment-how-to-align-"
            "higher-and-lower-time-frames-for-precision-entries/"
        ),
        "ttrades_protected_swing_validated": False,
        "source_complete_entries": 0,
        "cognitive_admissions": 0,
        "fills": 0, "profit_factor": None,
        "sizing_used": False, "holdout_7y_accessed": False,
    }


def result_sha256(report: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
