"""Outcome-blind native M3 census: do NOT conflate stop rule A with executable stop."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_a_m30m3_h1_liquidity_swing_asof_verifier_v1 import (
    ClosedExternalPivot,
    ExternalPivotKind,
    evaluate as independently_verify_m30m3,
)
from qore.infrastructure.trader_lab.vt08_5m_a_native_m30_m3_favorable_entry_v1 import (
    aggregate,
    closed_source_window,
)
from qore.infrastructure.trader_lab.vt08_5m_a_ttrades_m30m3_stop_authority_contract_v1 import (
    AuthorCheckStatus,
    inspect_bullish_m30_example,
)
from qore.infrastructure.trader_lab.vt08_cognitive_m3_fractal_density_recovery_v1 import (
    _load_m3,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA = "qore.vt08.5m.m30m3.author_stop.bullish_example_evidence_only.v1"


def audit_market_stop_example(base_path: Path, native_m3_path: Path) -> dict[str, object]:
    """Read-only read from independent verifier, no self-asserted POI/stop authority."""
    verified = independently_verify_m30m3(base_path, native_m3_path)
    source_m3 = _load_m3(
        native_m3_path, expected_symbol=str(verified["market"]),
    )
    indexed: dict[datetime, Vt08B01Bar] = {c.opened_at: c for c in source_m3}
    if len(indexed) != len(source_m3):
        raise ValueError("M3 duplicate timestamp")
    counts: Counter[str] = Counter()
    traces: list[dict[str, object]] = []
    for row in verified["source_receipts"]:
        counts["M30M3_ORIGINAL_GEOMETRY"] += 1
        if row["status"] == "H1_SOURCE_UNAVAILABLE":
            counts["PRE_C2_H1_EVIDENCE_INCOMPLETE"] += 1
            continue
        if row["status"] != "INDEPENDENT_M3_CISD_VERIFIED_HTF_POI_STILL_D":
            raise ValueError("unexpected independent source-verifier state")
        counts["INDEPENDENT_M3_CISD_GEOMETRY_OK"] += 1
        if row["side"] != DemoTradingSetupSide.LONG.value:
            counts["BEARISH_REQUIRES_DISTINCT_AUTHOR_STOP_RULE"] += 1
            continue
        counts["BULLISH_M30M3_SHAPES_NOT_TRADES"] += 1
        opened = datetime.fromisoformat(str(row["c2_opened_at"]))
        last_closed = datetime.fromisoformat(str(row["c2_closed_at"]))
        constituents = closed_source_window(
            indexed, begin=opened, count=10, minutes=3,
        )
        if constituents is None:
            raise ValueError("previously verified M30 C2 missing original M3")
        c2 = aggregate(constituents, period_minutes=30, member_minutes=3)
        if c2.closed_at != last_closed:
            raise ValueError("M30 source event clock changed")
        pre = row["poi_before_c2"]
        if not isinstance(pre, dict):
            raise ValueError("independent H1 source absent")
        pivots: list[ClosedExternalPivot] = []
        for item in pre["h1_external_pivots"]:
            if item["kind"] != ExternalPivotKind.LOW.value:
                continue
            pivots.append(ClosedExternalPivot(
                kind=ExternalPivotKind.LOW,
                extreme=Decimal(item["level"]),
                pivot_candle_opened_at=datetime.fromisoformat(
                    item["pivot_candle_opened_at"]
                ),
                confirmed_at=datetime.fromisoformat(
                    item["pivot_confirmed_at"]
                ),
            ))
        check = inspect_bullish_m30_example(
            c2=c2, decision_at=c2.closed_at,
            side=DemoTradingSetupSide.LONG,
            candidate_reference_pivots=tuple(pivots),
            preceding_m3=constituents,
        )
        if check.status is not AuthorCheckStatus.BOTH_EQ_AND_BREAKER_UNADJUDICATED:
            raise AssertionError("raw H1 pivot improperly authorized author EQ or breaker")
        if check.source_entry_complete or check.authorized_orders:
            raise AssertionError("author-example geometry may not authorize execution")
        counts["AUTHOR_STOP_RULE_WRITTEN_A_BUT_INPUTS_D"] += 1
        if check.pre_c2_external_pivot_known:
            counts["PRE_C2_GEOMETRIC_LOW_PIVOT_WITHOUT_EQ_AUTHORITY"] += 1
        if check.research_breaker_proxy_count:
            counts["QORE_BULLISH_BREAKER_SEQUENCE_PROXY_NOT_AUTHOR_LOW"] += 1
        traces.append({
            "origin_id": row["origin_id"],
            "c2_closed_at": c2.closed_at.isoformat(),
            "status": check.status.value,
            "author_stop_asof": check.as_json(),
            "author_POI_verified": False,
            "author_EQ_swing_valid": False,
            "author_breaker_low_verified": False,
            "orders_authorized": 0,
        })
    if counts["M30M3_ORIGINAL_GEOMETRY"] != verified["prior_geometry_count"]:
        raise AssertionError("record count changed between independent replay and stop audit")
    return {
        "schema": SCHEMA,
        "market": verified["market"],
        "counts": dict(sorted(counts.items())),
        "bullish_author_stop_observation_rows": traces,
        "author_rule_written": True,
        "author_eq_reference_before_c2_verified": False,
        "author_breaker_low_selection_verified": False,
        "author_poi_selection_verified": False,
        "candidate_events_source_complete": 0,
        "cognitive_approved_signals": 0,
        "orders": 0,
        "fills": 0,
        "pnl_evaluated": False,
        "sealed_7y_accessed": False,
    }
