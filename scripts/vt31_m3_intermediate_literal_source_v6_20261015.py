#!/usr/bin/env python3
"""VT31 M3 V6: literal TTrades basic intermediate geometry vs QORE V5 strict.

Research witness only. A triple of same-kind short-term swings is not an
authorial MSS, verified displacement, protected swing, trade or stop.
No economic metrics, broker orders, fills or sizing.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_m3_intermediate_swing_hierarchy_v5_20261015 import (
    SOURCE_STATES,
    V4_STATES,
    audit_day as audit_v5_day,
    intermediate_swing_source_geometry,
)
from scripts.vt31_m3_source_first_cisd_cognition_v3_20261015 import (
    TTradesAmSourceFirstCognitionV3,
)
from scripts.vt31_m4_m5_author_semantics_bridge_20261015 import short_term_swings
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    MARKET_SHA,
    M1_TOTAL,
    collect_hours,
    hash_file,
    market_rows,
    run_census,
)

SCHEMA = "VT31_M3_V6_LITERAL_BASIC_INTERMEDIATE_DIAGNOSTIC_NOT_MSS"
PREREG_PATH = "docs/research/VT31_M3_V6_LITERAL_INTERMEDIATE_VS_QORE_STRICT_PREREG_2026-10-15.md"
V5_FROZEN = {
    "NOT_IN_318_AMBIGUOUS_SCOPE": 165,
    "SINGLE_SOURCE_INTERMEDIATE_GEOMETRY_COMPONENT_ONLY": 24,
    "NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF": 294,
}
_GRP: dict | None = None


@dataclass(frozen=True, slots=True)
class LiteralIntermediateEvidence:
    state: str
    as_of: datetime
    short_term_same_kind: int
    eligible_literal_triples: int
    freshly_crossed_literal_triples: int
    single_center_pivot_closed_at: datetime | None = None
    single_right_confirmed_at: datetime | None = None
    author_displacement_certified: bool = False
    causative_protected_swing_certified: bool = False
    methodology_certified: bool = False
    cognition_certified: bool = False
    trader_certified: bool = False
    orders_or_sizing: int = 0


def literal_intermediate_source_geometry(
    ten_prefix: tuple[M1Bar, ...],
    *,
    side: Side,
    first_return_at: datetime,
    as_of: datetime,
) -> LiteralIntermediateEvidence:
    """Compare same-kind triples, no QORE strict center-price tie-break.

    V5 validates aware time, consecutive fully-closed M1, causal as-of and
    first return. It remains unchanged; a literal triple never upgrades V5.
    """
    if not isinstance(side, Side):
        raise ValueError("LITERAL_INTERMEDIATE_INVALID_SIDE")
    intermediate_swing_source_geometry(
        ten_prefix, side=side, first_return_at=first_return_at, as_of=as_of,
    )
    if len(ten_prefix) < 8 or first_return_at >= as_of:
        return LiteralIntermediateEvidence(
            "NO_LITERAL_INTERMEDIATE_BREAK", as_of, 0, 0, 0,
        )
    kind = "HIGH" if side is Side.LONG else "LOW"
    swings = tuple(
        s for s in short_term_swings(ten_prefix)
        if s.kind == kind and s.confirmed_at < as_of
    )
    literal_triples = tuple(
        (center, right)
        for left, center, right in zip(
            swings, swings[1:], swings[2:], strict=False,
        )
        if (
            center.pivot_closed_at >= first_return_at
            and left.confirmed_at < center.confirmed_at < right.confirmed_at
        )
    )
    previous, current = ten_prefix[-2:]
    fresh = tuple(
        pair for pair in literal_triples
        if (
            previous.close <= pair[0].extremum < current.close
            if side is Side.LONG
            else previous.close >= pair[0].extremum > current.close
        )
    )
    common = (as_of, len(swings), len(literal_triples), len(fresh))
    if len(fresh) == 1:
        return LiteralIntermediateEvidence(
            "ONE_LITERAL_INTERMEDIATE_COMPONENT_ONLY",
            *common,
            fresh[0][0].pivot_closed_at,
            fresh[0][1].confirmed_at,
        )
    if len(fresh) > 1:
        return LiteralIntermediateEvidence(
            "MULTIPLE_LITERAL_INTERMEDIATES_UNKNOWN", *common,
        )
    return LiteralIntermediateEvidence(
        "NO_LITERAL_INTERMEDIATE_BREAK", *common,
    )


def audit_day(
    *, day: str, nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...], return_at: datetime,
) -> dict[str, object]:
    base = audit_v5_day(day=day, nine=nine, ten=ten, return_at=return_at)
    cls = base["v5_intermediate_source_geometry"]
    out: dict[str, object] = {
        "ny_day": day,
        "first_return_at": base["first_return_at"],
        "first_v4_ambiguous_at": base["first_v4_ambiguous_at"],
        "v4_original_source_class": base["v4_original_source_class"],
        "v5_strict_geometry_unchanged": cls,
        "v6_literal_geometry": "NOT_IN_318_AMBIGUOUS_SCOPE",
        "v6_same_kind_short_term_count": 0,
        "v6_eligible_literal_triples": 0,
        "v6_newly_crossed_literal_triples": 0,
        "v6_one_center_pivot_at": None,
        "v6_one_right_confirmation_at": None,
        "author_mss_displacement_certified": False,
        "protected_causative_swing_certified": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "broker_orders_fills_sizing": 0,
    }
    if base["v4_original_source_class"] != "MULTIPLE_MSS_SWING_REFERENCE_UNKNOWN":
        if cls != "NOT_IN_318_AMBIGUOUS_SCOPE":
            raise AssertionError("V5_165_OUTSIDE_SCOPE_RECLASSIFIED")
        return out
    if cls not in {
        "SINGLE_SOURCE_INTERMEDIATE_GEOMETRY_COMPONENT_ONLY",
        "NO_INTERMEDIATE_CONFIRMED_AT_CAUSAL_ASOF",
    }:
        raise AssertionError("V5_318_BASELINE_UNEXPECTED")
    at_str = base["first_v4_ambiguous_at"]
    if not at_str:
        raise AssertionError("V4_AMBIGUOUS_ASOF_MISSING")
    at = datetime.fromisoformat(at_str).astimezone(UTC)
    prefix = tuple(x for x in ten if x.closed_at <= at)
    source = TTradesAmSourceFirstCognitionV3()
    for bar in (*nine, *prefix):
        source.observe_closed_m1(bar)
    snap = source.snapshot()
    if snap.bias not in ("LONG", "SHORT") or snap.first_return_at != return_at:
        raise AssertionError("V3_SOURCE_BIAS_OR_RETURN_CHANGED")
    evidence = literal_intermediate_source_geometry(
        prefix, side=Side(snap.bias), first_return_at=return_at, as_of=at,
    )
    out.update({
        "v6_literal_geometry": evidence.state,
        "v6_same_kind_short_term_count": evidence.short_term_same_kind,
        "v6_eligible_literal_triples": evidence.eligible_literal_triples,
        "v6_newly_crossed_literal_triples": evidence.freshly_crossed_literal_triples,
        "v6_one_center_pivot_at": (
            evidence.single_center_pivot_closed_at.isoformat()
            if evidence.single_center_pivot_closed_at else None
        ),
        "v6_one_right_confirmation_at": (
            evidence.single_right_confirmed_at.isoformat()
            if evidence.single_right_confirmed_at else None
        ),
    })
    # A V5 strict intermediate is also a literal same-kind triple. Extra
    # literal triples can turn a strict singleton into an ambiguous set.
    if (
        cls == "SINGLE_SOURCE_INTERMEDIATE_GEOMETRY_COMPONENT_ONLY"
        and evidence.freshly_crossed_literal_triples < 1
    ):
        raise AssertionError("V5_STRICT_SWING_MUST_EXIST_IN_V6_LITERAL")
    return out


def _worker(tasks: list[tuple[str, datetime]]) -> list[dict[str, object]]:
    if _GRP is None:
        raise ValueError("M1_SOURCE_NOT_PRELOADED_FOR_FAST_FORK")
    return [
        audit_day(
            day=day, nine=_GRP[day][9], ten=_GRP[day][10], return_at=at,
        )
        for day, at in tasks
    ]


def _digest(items: list[dict[str, object]]) -> str:
    return sha256(json.dumps(
        items, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def audit_real_m1(market: Path, *, parity: bool = True) -> dict[str, object]:
    """Run V6 on unchanged 483 observed development cases only."""
    global _GRP  # noqa: PLW0603
    if hash_file(market) != MARKET_SHA:
        raise ValueError("ORIGINAL_NAS100_SOURCE_SHA_MISMATCH")
    groups, total = collect_hours(market_rows(market))
    if total != M1_TOTAL:
        raise AssertionError("CANONICAL_SOURCE_BAR_COUNT_CHANGED")
    census = run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != SOURCE_STATES:
        raise AssertionError("CANONICAL_775_SOURCE_CENSUS_CHANGED")
    tasks = [
        (c["ny_day"], datetime.fromisoformat(c["as_of"]).astimezone(UTC))
        for c in census["source_classifications"]
        if c["classification"] == "FIRST_RETURN_NO_QORE_MSS"
    ]
    if len(tasks) != 483 or len({a for a, _ in tasks}) != 483:
        raise AssertionError("CANONICAL_483_COHORT_CHANGED")
    _GRP = groups
    start = time.monotonic()
    baseline = (
        sorted(_worker(tasks), key=lambda x: x["ny_day"]) if parity else None
    )
    scalar_sec = time.monotonic() - start if parity else None
    start = time.monotonic()
    with mp.get_context("fork").Pool(processes=2) as pool:
        parts = pool.map(_worker, [tasks[::2], tasks[1::2]])
    fast = sorted((x for part in parts for x in part), key=lambda x: x["ny_day"])
    fork_sec = time.monotonic() - start
    if len(fast) != 483 or (parity and (
        baseline is None or _digest(baseline) != _digest(fast)
    )):
        raise AssertionError("V6_SCALAR_VS_FORK_FULL_CASEBOOK_MISMATCH")
    prior_v4 = Counter(x["v4_original_source_class"] for x in fast)
    prior_v5 = Counter(x["v5_strict_geometry_unchanged"] for x in fast)
    literal = Counter(x["v6_literal_geometry"] for x in fast)
    if prior_v4 != V4_STATES or prior_v5 != V5_FROZEN:
        raise AssertionError("V4_V5_FROZEN_COHORT_RECLASSIFIED")
    if sum(literal.values()) != 483 or literal["NOT_IN_318_AMBIGUOUS_SCOPE"] != 165:
        raise AssertionError("V6_318_AUDIT_SCOPE_MISMATCH")
    if any(
        x["trader_certified"] or x["methodology_certified"]
        or x["cognition_certified"] or x["broker_orders_fills_sizing"]
        for x in fast
    ):
        raise AssertionError("LITERAL_GEOMETRY_IS_NEVER_TRADE_AUTHORITY")
    cross = Counter(
        (x["v5_strict_geometry_unchanged"], x["v6_literal_geometry"])
        for x in fast
        if x["v4_original_source_class"] == "MULTIPLE_MSS_SWING_REFERENCE_UNKNOWN"
    )
    if sum(cross.values()) != 318:
        raise AssertionError("V6_318_CROSS_TAB_INCOMPLETE")
    first_day: dict[str, str] = {}
    for x in fast:
        first_day.setdefault(x["v6_literal_geometry"], x["ny_day"])
    return {
        "schema": SCHEMA,
        "prereg_file": PREREG_PATH,
        "frozen_NAS100_M1_sha256": MARKET_SHA,
        "frozen_NAS100_M1_total": total,
        "frozen_775_days": census["observed_days_total"],
        "frozen_483_contexts": len(tasks),
        "V4_classes_unchanged": dict(sorted(prior_v4.items())),
        "V5_strict_geometry_classes_unchanged": dict(sorted(prior_v5.items())),
        "V6_literal_geometry_classes_not_MSS": dict(sorted(literal.items())),
        "V5_vs_V6_318_cross_tab": [
            {"v5": k[0], "v6": k[1], "contexts": value}
            for k, value in sorted(cross.items())
        ],
        "first_real_day_per_literal_class": first_day,
        "all_483_source_cases": fast,
        "full_casebook_sha256": _digest(fast),
        "scalar_fork_full_JSON_parity": parity,
        "time_scalar_s": round(scalar_sec, 5) if scalar_sec is not None else None,
        "time_fork_s": round(fork_sec, 5),
        "QORE_V5_strict_extremum_not_author_rule": True,
        "rebalanced_intermediates_not_evaluated": True,
        "higher_timeframe_reactions_not_evaluated": True,
        "author_displacement_not_evaluated": True,
        "protected_swing_causation_not_evaluated": True,
        "M4_entry_families_not_evaluated": True,
        "M6_independent_signatures": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "orders_fills_sizing": 0,
        "economic_metrics_calculated": False,
        "live_demo_VPS_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--parity", action="store_true")
    args = parser.parse_args()
    report = audit_real_m1(args.market, parity=args.parity)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "frozen_prior_V5": report["V5_strict_geometry_classes_unchanged"],
        "V6_literal_source_components": report["V6_literal_geometry_classes_not_MSS"],
        "cross": report["V5_vs_V6_318_cross_tab"],
        "sha": report["full_casebook_sha256"],
        "parity": report["scalar_fork_full_JSON_parity"],
        "trader_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
