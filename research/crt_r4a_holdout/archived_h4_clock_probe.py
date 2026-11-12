"""Audit structural R4-A H4 six-anchor coverage vs older three-anchor proxy.

This checks genuine SHA-verified 2024-25 archived OHLC for one feed ONLY.
No pivot/MSS/entry/TP/SL/PnL logic, no untouched holdout claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.crt_r4a_holdout.archived_2y_strategy_proxy import (
    h4_blocks,
    source_m5,
)
from research.crt_r4a_holdout.pine_h4_geometry import (
    ClosedH4,
    c1_allowed,
    proxy_old_c1_allowed,
    true_three_c,
    two_c_return,
)


def adapt(source: object) -> ClosedH4:
    from scripts.crt_radar_archived_m5_prescreen import H4

    if not isinstance(source, H4):
        raise ValueError("unknown native H4 decoder")
    return ClosedH4(
        source.opened_at, source.closed_at,
        float(source.high), float(source.low), float(source.close)
    )


def audit(root: Path, symbol: str, family: str, cohort: str) -> dict:
    if family not in ("forex", "index"):
        raise ValueError("BTC feed not in this original 33 feed pilot")
    bars, verified = source_m5(root, symbol, cohort)
    closed, partial = h4_blocks(bars, family)
    full_anchor = old_anchor = full2 = old2 = full3 = old3 = 0
    ranges = [adapt(x.h4) for x in closed]
    for i, h in enumerate(ranges):
        is_full = c1_allowed(h.opened_at, family)
        is_old = proxy_old_c1_allowed(h.opened_at, family)
        if is_old and not is_full:
            raise ValueError("old eligible C1 not included in Pine six anchors")
        full_anchor += is_full
        old_anchor += is_old
        if i + 1 < len(ranges):
            is2 = two_c_return(h, ranges[i + 1], family)
            if is2:
                full2 += 1
                if is_old:
                    old2 += 1
        if i + 2 < len(ranges):
            is3 = true_three_c(h, ranges[i + 1], ranges[i + 2], family)
            if is3:
                full3 += 1
                if is_old:
                    old3 += 1
    if not full_anchor > old_anchor:
        raise ValueError("real source H4 did not reveal six-vs-three omission")
    return {
        "status": "REAL_SHA_VERIFIED_H4_CLOCK_DISCREPANCY_AUDITED_NO_TRADES",
        "symbol": symbol,
        "family": family,
        "native_m5": verified["total_m5"],
        "closed_h4": len(closed),
        "incomplete_h4": partial,
        "eligible_c1_pine_six": full_anchor,
        "eligible_c1_old_proxy_three": old_anchor,
        "closed_2c_geometry_pine_clock": full2,
        "closed_2c_geometry_old_proxy_clock": old2,
        "closed_true3c_geometry_pine_clock": full3,
        "closed_true3c_geometry_old_proxy_clock": old3,
        "pine_f_engine_event_parity": False,
        "includes_MSS": False,
        "includes_costs_or_PnL": False,
        "certified_holdout": False,
        "window": "2024_2025_RESEARCH_CONSUMED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--family", choices=("forex", "index"), required=True)
    parser.add_argument("--cohort", required=True)
    args = parser.parse_args()
    print(json.dumps(
        audit(args.root, args.symbol, args.family, args.cohort),
        sort_keys=True
    ))


if __name__ == "__main__":
    main()
