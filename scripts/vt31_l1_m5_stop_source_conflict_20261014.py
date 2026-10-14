#!/usr/bin/env python3
"""Compare G3 C2 full-wick to observed pre-MSS extremes, NOT TTrades swing.

Real source-only, development data consumed; no new stop policy, OMS or PnL.
TTrades describes "beyond the swing causing displacement", which this witness
cannot independently identify. Research proxies must never be certified as it.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_m4_m5_ttrades_census_20261014 import census
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    MARKET_SHA,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
)

PREREG = "bd5a6f48345c974232a0a914f1a83b583952b9cf"
PRIMARY_SOURCE = "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/"


def _price(value: object) -> Decimal:
    price = Decimal(str(value))
    if not price.is_finite() or price <= 0:
        raise ValueError("M4_PRICE_INVALID")
    return price


def classify_c2_against_extreme(
    *, side: str, c2: Decimal, extreme: Decimal,
) -> str:
    """Not a trade stop: only ordered reference levels of completed M1."""
    if side not in ("LONG", "SHORT"):
        raise ValueError("COG_SIDE_NOT_SUPPORTED")
    if side == "LONG":
        relation = "INSIDE" if c2 > extreme else "OUTSIDE" if c2 < extreme else "MATCHES"
    else:
        relation = "INSIDE" if c2 < extreme else "OUTSIDE" if c2 > extreme else "MATCHES"
    return "C2_" + relation + "_PRE_MSS_EXTREME"


def observe_stop_conflict(
    *,
    nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...],
    m4: dict[str, Any],
) -> dict[str, Any]:
    """Receive strictly the closed prefix ending at first C3, no M5 future.

    Asserts source first sweep and MSS temporal lineage. Pre-MSS extrema include
    raid minute and all subsequent CLOSED minutes before the MSS candle, but
    these are NOT independently attested swing pivots.
    """
    formed_raw = m4.get("first_fvg_confirmed_at")
    if m4.get("state") != "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE" or formed_raw is None:
        raise ValueError("NO_FVG_SOURCE_FOR_STOP_PROVENANCE")
    formed = datetime.fromisoformat(str(formed_raw))
    if not ten or ten[-1].closed_at != formed:
        raise ValueError("LOOKAHEAD_OR_STALE_M1_PREFIX_AT_C3")
    side = str(m4["side"])
    if side not in ("LONG", "SHORT"):
        raise ValueError("SIDE_UNKNOWN")
    if not complete_hour(nine[0].opened_at.astimezone(
        __import__("zoneinfo").ZoneInfo("America/New_York")
    ).date().isoformat(), 9, nine):
        raise ValueError("H1_09_SOURCE_INCOMPLETE")
    if any(
        a.closed_at != b.opened_at
        for a, b in zip(ten, ten[1:], strict=False)
    ):
        raise ValueError("M1_10_SOURCE_GAP")
    native = native_ttrades_am_context(as_of=formed, nine=nine, ten=ten)
    if native.state != "RETURN_INSIDE_OBSERVED":
        raise ValueError("NATIVE_H1_SOURCE_NOT_ATTESTED:" + native.state)
    if (
        native.candidate_side != side
        or native.opposite_h1_dol != _price(m4["target_dol"])
        or native.first_sweep_at is None
    ):
        raise ValueError("NATIVE_H1_DOL_OR_SIDE_CONFLICT")
    mss_at = datetime.fromisoformat(str(m4["cognitive_mss_at"]))
    if not (native.first_sweep_at < mss_at <= formed):
        raise ValueError("MSS_NOT_AFTER_FIRST_SWEEP_AND_BEFORE_C3")
    if native.return_inside_at != mss_at:
        raise ValueError("FIRST_RETURN_MSS_WITNESS_DISAGREEMENT")
    k = next(
        (i for i, x in enumerate(ten) if x.closed_at == formed),
        None,
    )
    if k is None or k < 2:
        raise ValueError("FIRST_FVG_C3_NOT_IN_PREFIX")
    middle = ten[k - 1]
    c2 = _price(m4["c2_full_wick_reference"])
    if c2 != (middle.low if side == "LONG" else middle.high):
        raise ValueError("C2_MUST_EQUAL_EXACT_SECOND_FVG_M1_WICK")
    ce = _price(m4["ce_research_only"])
    lo = _price(m4["fvg_lower"])
    hi = _price(m4["fvg_upper"])
    if not (lo < ce < hi and ce == (lo + hi) / Decimal("2")):
        raise ValueError("ORIGINAL_M4_FVG_CE_GEOMETRY_MISMATCH")
    first = ten[k - 2]
    third = ten[k]
    gap = (
        (first.high, third.low) if side == "LONG"
        else (third.high, first.low)
    )
    if not (gap[0] < gap[1] and gap == (lo, hi)):
        raise ValueError("FVG_SOURCE_M1_GEOMETRY_MUTATED")
    raid_idx = next(
        (i for i, x in enumerate(ten) if x.closed_at == native.first_sweep_at),
        None,
    )
    mss_idx = next(
        (i for i, x in enumerate(ten) if x.closed_at == mss_at),
        None,
    )
    if raid_idx is None or mss_idx is None or raid_idx >= mss_idx:
        raise ValueError("SOURCE_RAID_MSS_CHRONOLOGY_NOT_RECONCILED")
    if ten[mss_idx].close != _price(m4["mss_anchor"]):
        raise ValueError("MSS_ANCHOR_M1_PRICE_NOT_RECONCILED")
    raid_bar = ten[raid_idx]
    pre_mss = ten[raid_idx:mss_idx]  # STOP before MSS: no future displacement
    raid_extreme = raid_bar.low if side == "LONG" else raid_bar.high
    pre_extreme = (
        min(x.low for x in pre_mss) if side == "LONG"
        else max(x.high for x in pre_mss)
    )
    structural = classify_c2_against_extreme(
        side=side, c2=c2, extreme=pre_extreme,
    )
    raid_relation = classify_c2_against_extreme(
        side=side, c2=c2, extreme=raid_extreme,
    ).replace("_PRE_MSS_EXTREME", "_FIRST_RAID_EXTREME")
    geometry = (
        "C2_REFERENCE_ON_RISK_SIDE_OF_CE"
        if (c2 < ce if side == "LONG" else c2 > ce)
        else "C2_REFERENCE_NOT_ON_RISK_SIDE_OF_CE"
    )
    return {
        "first_fvg_confirmed_at": formed.isoformat(),
        "first_source_raid_at": native.first_sweep_at.isoformat(),
        "mss_at": mss_at.isoformat(),
        "side": side,
        "c2_full_wick_qore_reference": str(c2),
        "ce_research_only": str(ce),
        "first_raid_m1_extreme_proxy": str(raid_extreme),
        "pre_mss_path_extreme_proxy": str(pre_extreme),
        "c2_to_pre_mss_extreme_abs_points": str(abs(c2 - pre_extreme)),
        "c2_to_first_raid_extreme_abs_points": str(abs(c2 - raid_extreme)),
        "c2_vs_raid_extreme": raid_relation,
        "c2_vs_pre_mss_extreme": structural,
        "c2_ce_geometry": geometry,
        "author_swing_identified": False,
        "ttrades_author_stop_certified": False,
        "g3_c2_equals_author_stop": False,
        "broker_tick_attested": False,
        "executable_stop_produced": False,
        "filled": False,
    }


def run_audit(
    groups: dict[str, dict[int, tuple[M1Bar, ...]]],
) -> dict[str, Any]:
    original = census(groups)
    m4_counts = original["M4_source_state_counts"]
    if original["baseline_days_total"] != 775 or m4_counts != {
        "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE": 119,
        "NO_ELIGIBLE_FVG": 8,
        "WINDOW_CLOSED_FOR_NEW_LIMIT": 1,
    }:
        raise ValueError("ORIGINAL_PR935_POPULATION_DRIFT")
    cases: list[dict[str, Any]] = []
    source_relations: Counter[str] = Counter()
    raid_relations: Counter[str] = Counter()
    ce_geometry: Counter[str] = Counter()
    for item in original["cognitive_case_evidence"]:
        m4 = item["m4_m5_source_only"]
        if m4["state"] != "FVG_GEOMETRY_ATTESTED_NOT_EXECUTABLE":
            continue
        day = item["ny_day"]
        nine, ten = groups[day][9], groups[day][10]
        formed = datetime.fromisoformat(m4["first_fvg_confirmed_at"])
        prefix = tuple(bar for bar in ten if bar.closed_at <= formed)
        witness = observe_stop_conflict(nine=nine, ten=prefix, m4=m4)
        cases.append({"ny_day": day, **witness})
        source_relations[witness["c2_vs_pre_mss_extreme"]] += 1
        raid_relations[witness["c2_vs_raid_extreme"]] += 1
        ce_geometry[witness["c2_ce_geometry"]] += 1
    if len(cases) != 119:
        raise ValueError("STOP_SOURCE_AUDIT_DROPPED_OR_ADDED_FVG")
    return {
        "model": "VT31_L1_M5_C2_SWING_SOURCE_CONFLICT_AUDIT_V1",
        "original_3y_m1_sha256": MARKET_SHA,
        "prereg_commit": PREREG,
        "ttrades_primary_source": PRIMARY_SOURCE,
        "author_stop_semantics": "BEYOND_SWING_CAUSING_DISPLACEMENT",
        "qore_stop_semantics": "C2_FULL_WICK_REFERENCE",
        "actual_author_swing_not_identifiable_by_proxy": True,
        "original_m2_m3_contexts": 128,
        "fixed_m4_first_fvg_population": 119,
        "c2_vs_pre_mss_extreme_counts": dict(sorted(source_relations.items())),
        "c2_vs_first_raid_extreme_counts": dict(sorted(raid_relations.items())),
        "c2_relative_to_ce_counts": dict(sorted(ce_geometry.items())),
        "cases": cases,
        "ttrades_author_stop_certified": False,
        "method_l1_certified": False,
        "g3_dual_signoff_verified": False,
        "broker_tick_and_contract_attested": False,
        "orders_executed": 0,
        "entry_execution_acks": 0,
        "risk_sizing_produced": False,
        "PnL_PF_DD_Sharpe_Sortino": None,
        "fresh_holdout_used": False,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    opt = parser.parse_args()
    if hash_file(opt.market) != MARKET_SHA:
        raise ValueError("FROZEN_M1_SHA256_MISMATCH")
    groups, n = collect_hours(market_rows(opt.market))
    if n != 1_059_784:
        raise ValueError("FROZEN_M1_COUNT_MISMATCH")
    report = run_audit(groups)
    report["original_m1_count"] = n
    opt.out.parent.mkdir(parents=True, exist_ok=True)
    opt.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "original_m1_count": n,
        "fixed_m4_first_fvg_population": report["fixed_m4_first_fvg_population"],
        "c2_vs_pre_mss_extreme_counts": report["c2_vs_pre_mss_extreme_counts"],
        "c2_vs_first_raid_extreme_counts":
            report["c2_vs_first_raid_extreme_counts"],
        "c2_relative_to_ce_counts": report["c2_relative_to_ce_counts"],
        "ttrades_author_stop_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
