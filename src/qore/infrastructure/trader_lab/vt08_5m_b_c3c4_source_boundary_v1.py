"""Independent Architect B source/clock boundary for C3-close to C4-first-M15.

Verifies frozen Architect A's SHAPE_ONLY artifacts against independent consumed
M15; never promotes source geometry into cognitive CandidateEvent or fills.
A owns methodology/source rules. B owns non-lookahead admission boundary.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_b_independent_real_lineage_audit_v1 import (
    ORIGINAL_SOURCE_SHA,
    _canonical_digest,
    _sha_m15,
    _timestamp,
    _window,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA: Final = "qore.vt08.5m.c3_closure_c4.two_clocks.shape.v1"
MARKETS: Final = ("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD")
EXPECTED: Final = {"EURJPY":79, "USDCHF":54, "NZDUSD":63, "CADJPY":64, "USDCAD":34}
NY: Final = ZoneInfo("America/New_York")
EQ_BASIS: Final = "C3_FULL_WICK_TO_WICK_AFTER_CLOSURE"


def _h4(rows: tuple[Vt08B01Bar, ...]) -> dict[str, Decimal]:
    if len(rows) != 16:
        raise ValueError("H4 must contain exactly 16 closed M15")
    return {
        "open": rows[0].open,
        "high": max(b.high for b in rows),
        "low": min(b.low for b in rows),
        "close": rows[-1].close,
    }


def _source_ps_proxy(
    rows: tuple[Vt08B01Bar, ...],
    side: str,
) -> list[list[str]]:
    """Independently reconstruct A's SHAPE-ONLY opposing-series proxy.

    This does not attest a TTrades-valid POI, PS, OB, or CISD source sequence.
    """
    bullish = side == "long"
    important = rows[0].low if bullish else rows[0].high
    opened: datetime | None = None
    first_open: Decimal | None = None
    extreme: Decimal | None = None
    outputs: list[list[str]] = []
    for bar in rows:
        opposing = bar.close < bar.open if bullish else bar.close > bar.open
        if opposing:
            if opened is None:
                opened, first_open = bar.opened_at, bar.open
                extreme = bar.low if bullish else bar.high
            elif extreme is not None:
                extreme = min(extreme, bar.low) if bullish else max(extreme, bar.high)
            continue
        if opened is not None and first_open is not None and extreme is not None:
            swept = extreme < important if bullish else extreme > important
            crossed = bar.close > first_open if bullish else bar.close < first_open
            if swept and crossed:
                outputs.append([
                    opened.isoformat(), bar.closed_at.isoformat(), str(extreme)
                ])
        opened, first_open, extreme = None, None, None
    return outputs


def verify_c3_shape(
    event: object,
    by_open: dict[datetime, Vt08B01Bar],
) -> dict[str, object]:
    if not isinstance(event, dict) or event.get("schema") != SCHEMA:
        raise ValueError("unrecognized source C3 shape schema")
    if event.get("as_of_stage") != "C3_CLOSED":
        raise ValueError("C3 stage must be at its H4 close")
    close_at = _timestamp(event.get("observed_at"))
    c3_open = close_at - timedelta(hours=4)
    c1_rows = _window(by_open, c3_open - timedelta(hours=8), c3_open - timedelta(hours=4))
    c2_rows = _window(by_open, c3_open - timedelta(hours=4), c3_open)
    c3_rows = _window(by_open, c3_open, close_at)
    c1, c2, c3 = _h4(c1_rows), _h4(c2_rows), _h4(c3_rows)
    side = event.get("side")
    if side not in ("long", "short"):
        raise ValueError("C3 unknown structural side")
    bullish = side == "long"
    if event.get("c3_m15_sha256") != _sha_m15(c3_rows):
        raise ValueError("C3 immutable constituent M15 SHA mismatch")
    if Decimal(str(event.get("c3_full_low"))) != c3["low"] or Decimal(
        str(event.get("c3_full_high"))
    ) != c3["high"]:
        raise ValueError("C3 full OHLC extreme mismatch")

    swept_hi, swept_lo = c2["high"] > c1["high"], c2["low"] < c1["low"]
    c2_closure = (swept_hi != swept_lo) and c1["low"] < c2["close"] < c1["high"]
    if c2_closure:
        raise ValueError("C3 Model A completed-C2 reversal contaminated Model B")
    if c3["high"] > c2["high"] or c3["low"] < c2["low"]:
        raise ValueError("C3 body proxy does not remain in C2 high/low range")
    c2_body_hi = max(c2["open"], c2["close"])
    c2_body_lo = min(c2["open"], c2["close"])
    if (bullish and c3["close"] <= c2_body_hi) or (
        not bullish and c3["close"] >= c2_body_lo
    ):
        raise ValueError("C3 body closure proxy not confirmed at closed H4")
    strong_engulf = (
        c3["open"] < c2_body_lo if bullish else c3["open"] > c2_body_hi
    )
    if event.get("strong_body_engulf_proxy") is not strong_engulf:
        raise ValueError("C3 strong engulf proxy inconsistency")
    sweep_status = (
        "DUAL_SWEEP_UNADJUDICATED" if swept_hi and swept_lo else
        "ONE_SIDE_SWEEP_FAILED_CLOSURE" if swept_hi or swept_lo else
        "NO_REFERENCE_SWEEP"
    )
    if event.get("c2_sweep_state") != sweep_status:
        raise ValueError("C2 dual sweep/category changed or unadjudicated")
    owner = close_at.astimezone(NY).hour in (1, 5, 9)
    if event.get("next_c4_owner_permitted") is not owner:
        raise ValueError("C4 Owner capability classification inconsistent")
    midpoint = (c3["high"] + c3["low"]) / 2
    if event.get("eq_intra_c3_basis") != EQ_BASIS:
        raise ValueError("wrong EQ range: C3 requires full H/L")
    if Decimal(str(event.get("eq_intra_c3_level"))) != midpoint:
        raise ValueError("C3 source EQ must use high/low, never C2 wick")

    proxy = _source_ps_proxy(c3_rows, side)
    if event.get("c3_ps_internal_proxies") != proxy:
        raise ValueError("C3 M15 PS proxy source timing/value mismatch")
    for p in proxy:
        if not (c3_open <= _timestamp(p[0]) < _timestamp(p[1]) <= close_at):
            raise ValueError("C3 PS proxy leaks from C4 or before C3")
    if event.get("daily_eq_context") != "NOT_ATTESTED_IN_THIS_BUNDLE":
        raise ValueError("source C3 incorrectly declares daily EQ attested")
    if event.get("poi_source_confirmed") is not False or event.get(
        "c3_ps_source_confirmed"
    ) is not False or event.get("c4_ps_source_confirmed") is not False:
        raise ValueError("unverified C3/POI/PS wrongly promoted")
    if (event.get("methodology_status") != "SHAPE_ONLY_NOT_SOURCE_COMPLETE"
        or event.get("order_authorized") is not False
        or event.get("trades_executed") != 0
        or event.get("no_c4_ohlc_consumed") is not True):
        raise ValueError("C3 cannot become executable or consume C4 source")

    origin = {
        "schema": SCHEMA,
        "market": event.get("market"),
        "ltf_profile": "M15_STANDARD",
        "source_family": "C3_CLOSURE_TO_C4_SHAPE",
        "c2_origin_at": (c3_open - timedelta(hours=4)).isoformat(),
        "c3_origin_at": c3_open.isoformat(),
        "side": side,
    }
    origin_id = "vt08-c3c4-source:" + _canonical_digest(origin)
    if event.get("origin_id") != origin_id:
        raise ValueError("C3 origin identity mismatch")
    eq_payload = {
        "source_candle": "C3",
        "side": side,
        "evidence_closed_at": close_at.isoformat(),
        "eq": str(midpoint),
        "lower_bound": str(c3["low"]),
        "upper_bound": str(c3["high"]),
        "range_basis": EQ_BASIS,
        "source_ref": "https://ttrades.com/how-to-use-equilibrium-eq-ttrades-fractal-model/",
        "research_only": True,
        "source_complete_entry": False,
    }
    facts = {
        "origin": origin,
        "c1": [str(c1["high"]), str(c1["low"]),
               (c3_open - timedelta(hours=4)).isoformat()],
        "c2": [str(c2[k]) for k in ("open", "high", "low", "close")],
        "c3": [str(c3[k]) for k in ("open", "high", "low", "close")],
        "c3_m15_sha": _sha_m15(c3_rows),
        "c3_ps_proxies": proxy,
        "eq": eq_payload,
    }
    if event.get("snapshot_fingerprint") != _canonical_digest(facts):
        raise ValueError("C3 snapshot fingerprint not bound to closed source")
    return {
        "origin_id": origin_id,
        "snapshot_fingerprint": event["snapshot_fingerprint"],
        "market": event["market"],
        "side": side,
        "closed_at": close_at,
        "c2_dual_sweep": swept_hi and swept_lo,
        "owner_permitted": owner,
        "ps_proxy_present": bool(proxy),
        "body_engulf_proxy": strong_engulf,
        "eq": midpoint,
        "c3_low": c3["low"],
        "c3_high": c3["high"],
    }


def verify_c4_observation(
    event: object,
    parent: dict[str, object],
    by_open: dict[datetime, Vt08B01Bar],
) -> None:
    if not isinstance(event, dict) or event.get("schema") != SCHEMA:
        raise ValueError("invalid C4 event")
    if event.get("as_of_stage") != "C4_FIRST_M15_CLOSED":
        raise ValueError("C4 must use first closed M15 stage")
    if (event.get("origin_id") != parent["origin_id"] or
        event.get("parent_snapshot_fingerprint") != parent["snapshot_fingerprint"]):
        raise ValueError("C4 lineage must match stable source and C3 snapshot")
    expected = parent["closed_at"] + timedelta(minutes=15)
    if _timestamp(event.get("observed_at")) != expected:
        raise ValueError("C4 first M15 cannot be known before its close")
    bar = by_open.get(parent["closed_at"])
    if bar is None or bar.closed_at.astimezone(UTC) != expected:
        raise ValueError("C4 M15 physical bar absent or incomplete")
    if event.get("c4_first_m15_sha256") != _sha_m15((bar,)):
        raise ValueError("C4 first M15 source hash mismatch")
    eq = parent["eq"]
    if Decimal(str(event.get("c3_eq_level_used"))) != eq:
        raise ValueError("C4 modified C3 full range EQ")
    bullish = parent["side"] == "long"
    expected_respect = bar.close >= eq if bullish else bar.close <= eq
    expected_wick = (
        eq <= bar.low <= parent["c3_high"] if bullish
        else parent["c3_low"] <= bar.high <= eq
    )
    if event.get("eq_half_respected_at_closed_m15") is not expected_respect:
        raise ValueError("C4 EQ respect misreported")
    if event.get("wick_in_respected_half") is not expected_wick:
        raise ValueError("C4 wick/source half-range misreported")
    if event.get("poi_source_confirmed") is not False or event.get(
        "order_authorized"
    ) is not False or event.get("trades_executed") != 0:
        raise ValueError("C4 cannot claim POI, trade, or live authority")
    no_hash = {k: v for k, v in event.items() if k != "snapshot_fingerprint"}
    if event.get("snapshot_fingerprint") != _canonical_digest(no_hash):
        raise ValueError("C4 snapshot hash is not its actual source observation")


def audit_market(a_file: Path, market_file: Path) -> dict[str, object]:
    raw = json.loads(a_file.read_text(encoding="utf-8"))
    fingerprint, market, checked, sha, rows = load_market_evidence(market_file)
    if market not in MARKETS or sha != ORIGINAL_SOURCE_SHA:
        raise ValueError("C3C4 raw M15 source outside frozen research")
    if raw.get("schema") != SCHEMA or raw.get("market") != market:
        raise ValueError("A C3C4 artifact schema or market mismatch")
    if (raw.get("evidence_fingerprint") != fingerprint or
        raw.get("evidence_checked_at") != checked.isoformat() or
        raw.get("consumed_source_software_sha") != sha):
        raise ValueError("A C3C4 artifact not bound to raw market source")
    sources = raw.get("c3_closed_source_snapshots")
    updates = raw.get("separate_c4_closed_bar_observations")
    if not isinstance(sources, list) or not isinstance(updates, list):
        raise ValueError("missing two-clock source event collections")
    if len(sources) != EXPECTED[market] or len(updates) != len(sources):
        raise ValueError("C3C4 cardinality differs from source evidence")
    indexed = {x.opened_at for x in rows}
    if len(indexed) != len(rows):
        raise ValueError("duplicate original M15 opening")
    by_open = {x.opened_at: x for x in rows}
    origins: dict[str, dict[str, object]] = {}
    counts: Counter[str] = Counter()
    for s in sources:
        parent = verify_c3_shape(s, by_open)
        origin = str(parent["origin_id"])
        if origin in origins:
            raise ValueError("duplicate C3 stable source ID")
        origins[origin] = parent
        counts["c3_shapes"] += 1
        if parent["owner_permitted"]:
            counts["c4_owner_permitted"] += 1
        else:
            counts["c4_outside_owner"] += 1
        if parent["c2_dual_sweep"]:
            counts["c2_dual_sweep_unadjudicated"] += 1
            if parent["owner_permitted"]:
                counts["c4_owner_c2_dual_sweep"] += 1
        elif parent["owner_permitted"]:
            counts["c4_owner_no_dual_sweep"] += 1
        if parent["ps_proxy_present"]:
            counts["c3_internal_ps_proxy"] += 1
        if parent["body_engulf_proxy"]:
            counts["c3_body_engulf_strong_proxy"] += 1
    seen_updates: set[str] = set()
    for u in updates:
        if not isinstance(u, dict):
            raise ValueError("C4 update must be a dict")
        origin = str(u.get("origin_id"))
        if origin not in origins or origin in seen_updates:
            raise ValueError("C4 update missing/duplicate corresponding C3 origin")
        verify_c4_observation(u, origins[origin], by_open)
        seen_updates.add(origin)
    if len(seen_updates) != len(origins):
        raise ValueError("C4 update not one-to-one with C3 source")
    declared = raw.get("counts")
    if not isinstance(declared, dict):
        raise ValueError("C3C4 expected source counts missing")
    map_expected = {
        "C3_CLOSED_SHAPES": "c3_shapes",
        "C4_OWNER_PERMITTED": "c4_owner_permitted",
        "C4_OUTSIDE_OWNER_SHAPE_ONLY": "c4_outside_owner",
        "C2_DUAL_SWEEP_UNADJUDICATED": "c2_dual_sweep_unadjudicated",
        "C4_OWNER_WITH_UNADJUDICATED_C2_DUAL_SWEEP": "c4_owner_c2_dual_sweep",
        "C4_OWNER_WITHOUT_C2_DUAL_SWEEP_SHAPE_ONLY": "c4_owner_no_dual_sweep",
        "C3_INTERNAL_CISD_PS_PROXY": "c3_internal_ps_proxy",
        "BODY_ENGULF_STRONG_PROXY": "c3_body_engulf_strong_proxy",
        "C4_M15_CLOSED_OBSERVATIONS": "c3_shapes",
    }
    for key, name in map_expected.items():
        if declared.get(key, 0) != counts[name]:
            raise ValueError(f"C3C4 source stage counter invalid: {key}")
    if (raw.get("unverified_poi") is not True or
        raw.get("candidate_event_approved") is not False or
        raw.get("cognitive_ready") is not False or
        raw.get("trades_executed") != 0 or
        raw.get("pnl_evaluated") is not False or
        raw.get("sealed_7y_accessed") is not False or
        raw.get("c3_continuation_family_overlap_under_frozen_c2_partition") != 0):
        raise ValueError("C3C4 SHAPE_ONLY artifact falsely claimed authorization")
    return {"market": market, **counts, "cognitive_ready": 0,
            "candidate_events": 0, "fills": 0,
            "trades": 0, "research_only": True}


def run_all(root: Path) -> dict[str, object]:
    results = [
        audit_market(
            root / "a" / symbol / f"{symbol}-two-clocks-source-full.json",
            root / "raw" / symbol / "market-evidence-1095d.json",
        ) for symbol in MARKETS
    ]
    total: Counter[str] = Counter()
    for item in results:
        for k, v in item.items():
            if isinstance(v, int) and not isinstance(v, bool):
                total[k] += v
    expected = {
        "c3_shapes": 294,
        "c4_owner_permitted": 213,
        "c4_outside_owner": 81,
        "c2_dual_sweep_unadjudicated": 105,
        "c4_owner_c2_dual_sweep": 80,
        "c4_owner_no_dual_sweep": 133,
        "c3_internal_ps_proxy": 129,
        "c3_body_engulf_strong_proxy": 36,
    }
    for k, value in expected.items():
        if total[k] != value:
            raise ValueError(f"C3C4 aggregate {k} unexpected")
    result: dict[str, object] = {
        "schema": "qore.vt08.b_c3_c4_independent_m15_source_boundary.v1",
        "verified_source_shapes": total["c3_shapes"],
        "verified_c4_first_m15_observations": total["c3_shapes"],
        "c4_owner_permitted": total["c4_owner_permitted"],
        "c4_outside_owner": total["c4_outside_owner"],
        "c2_dual_sweep_unadjudicated": total["c2_dual_sweep_unadjudicated"],
        "c4_owner_c2_dual_sweep": total["c4_owner_c2_dual_sweep"],
        "c4_owner_no_dual_sweep": total["c4_owner_no_dual_sweep"],
        "c3_internal_ps_proxy": total["c3_internal_ps_proxy"],
        "c3_body_engulf_strong_proxy": total["c3_body_engulf_strong_proxy"],
        "source_complete": 0,
        "cognitive_ready": 0,
        "fills": 0,
        "pnl_calculated": False,
        "market_results": results,
    }
    return result


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_all(args.artifacts_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True),
                           encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="market_results"},
                     sort_keys=True))


if __name__ == "__main__":
    main()
