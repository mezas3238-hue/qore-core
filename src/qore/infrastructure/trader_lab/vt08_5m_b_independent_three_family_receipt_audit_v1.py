"""Independent B as-of receipt verification of A's 237 C2 + 258 C3 FVG shapes.

Consumes frozen A artifact and separate original 1095D M15. Never imports the
producer's swing/POI/census code. Reconstructs each claim from raw candles and
keeps reference-swing pre-C2, POI significance, and SOURCE_COMPLETE unproven.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Final

from qore.infrastructure.trader_lab.vt08_5m_b_independent_real_lineage_audit_v1 import (
    ORIGINAL_SOURCE_SHA,
    _canonical_digest,
    _timestamp,
    _window,
)
from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_backtest_v1 import (
    load_market_evidence,
)
from qore.infrastructure.traders.vt08_b01_r3_8 import Vt08B01Bar

SCHEMA: Final = "qore.vt08.5m.three_family.fvg_source_causal_swing.shape.v1"
C2: Final = "C2_CLOSURE_TO_C3"
C3: Final = "C3_CONTINUATION_INTRAC3"
C4: Final = "C3_CLOSURE_TO_C4"
MARKETS: Final = ("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD")
COUNTS: Final = {
    "EURJPY": (48, 49), "USDCHF": (52, 44), "NZDUSD": (48, 49),
    "CADJPY": (42, 63), "USDCAD": (47, 53),
}


class BSourceReceiptError(ValueError):
    """Source evidence does not support this upstream structural assertion."""


def _fmt(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def _fvg_candidates(
    rows: tuple[Vt08B01Bar, ...], *, side: str,
) -> tuple[tuple[datetime, Decimal, Decimal], ...]:
    """Text-rule FVG: first.high < third.low (long), reversed (short).

    This is only a *geometry* reconstructed by B, NOT author POI priority or
    proof of a valid pre-C2 reference swing. Distal invalidation remains QORE C.
    """
    output: list[tuple[datetime, Decimal, Decimal]] = []
    if len(rows) != 16:
        raise BSourceReceiptError("exact parent H4 M15 source required")
    for i in range(2, 16):
        first, _, third = rows[i - 2 : i + 1]
        low, high = (
            (first.high, third.low) if side == "long"
            else (third.high, first.low)
        )
        if not low < high:
            continue
        remaining = rows[i + 1 :]
        invalidated = (
            any(b.low < low for b in remaining) if side == "long"
            else any(b.high > high for b in remaining)
        )
        if not invalidated:
            output.append((third.closed_at, low, high))
    return tuple(output)


def _m15_ps(
    prefix: tuple[Vt08B01Bar, ...], *, side: str,
    important: Decimal,
) -> tuple[tuple[datetime, datetime, Decimal, Decimal], ...]:
    """Independently reconstruct opposing series OPEN break at closed M15."""
    first_at: datetime | None = None
    first_open: Decimal | None = None
    extreme: Decimal | None = None
    result: list[tuple[datetime, datetime, Decimal, Decimal]] = []
    for b in prefix:
        opposite = b.close < b.open if side == "long" else b.close > b.open
        if opposite:
            if first_at is None:
                first_at, first_open = b.opened_at, b.open
                extreme = b.low if side == "long" else b.high
            elif extreme is not None:
                extreme = min(extreme, b.low) if side == "long" else max(extreme, b.high)
            continue
        if first_at is not None and first_open is not None and extreme is not None:
            touched_extreme = extreme < important if side == "long" else extreme > important
            broke_open = b.close > first_open if side == "long" else b.close < first_open
            if touched_extreme and broke_open:
                result.append((first_at, b.closed_at, extreme, first_open))
        first_at, first_open, extreme = None, None, None
    return tuple(result)


def verify_receipt(
    receipt: object,
    market: str,
    by_open: dict[datetime, Vt08B01Bar],
) -> dict[str, object]:
    if not isinstance(receipt, dict) or receipt.get("market") != market:
        raise BSourceReceiptError("receipt not tied to market")
    if receipt.get("family") not in (C2, C3):
        raise BSourceReceiptError("C4 has no proven shapes in frozen narrow-FVG ledger")
    if receipt.get("status") != "CONFIRMED_STRUCTURE_ONLY":
        raise BSourceReceiptError("source receipt is not a structural-only confirmation")
    if receipt.get("source_status") != "STRUCTURE_RESEARCH_NOT_SOURCE_COMPLETE":
        raise BSourceReceiptError("producer misrepresents full source fidelity")
    if (receipt.get("source_poi_significance_adjudicated") is not False
        or receipt.get("author_strategy_entry_approved") is not False
        or receipt.get("cognitive_ready") is not False
        or receipt.get("orders_authorized") is not False
        or receipt.get("pnl_evaluated") is not False):
        raise BSourceReceiptError("unproven source promoted to economic authority")
    event_id = receipt.get("source_event_id")
    if event_id != receipt.get("origin_id"):
        raise BSourceReceiptError("unstable source identity alias")
    s = receipt.get("side")
    if s not in ("long", "short"):
        raise BSourceReceiptError("unknown side")
    anchor = _timestamp(receipt.get("owner_anchor_ny"))
    c2_open = anchor - timedelta(hours=4)
    c1_open = c2_open - timedelta(hours=4)
    c1 = _window(by_open, c1_open, c2_open)
    c2 = _window(by_open, c2_open, anchor)
    c2_h = (max(x.high for x in c2), min(x.low for x in c2), c2[-1].close)
    c1_h = (max(x.high for x in c1), min(x.low for x in c1))
    swept_low = c2_h[1] < c1_h[1]
    swept_high = c2_h[0] > c1_h[0]
    if swept_low == swept_high or not c1_h[1] < c2_h[2] < c1_h[0]:
        raise BSourceReceiptError("receipt has no unambiguous completed C2 closure")
    if s != ("long" if swept_low else "short"):
        raise BSourceReceiptError("receipt side is opposite actual C2 sweep")

    family = str(receipt["family"])
    parent = c1 if family == C2 else c2
    if receipt.get("poi_policy") != "UNIQUE_FVG_ONLY_NO_PRIORITY_TIEBREAK":
        raise BSourceReceiptError("unapproved POI priority/source selection")
    fvgs = _fvg_candidates(parent, side=s)
    if len(fvgs) != 1:
        raise BSourceReceiptError("no exactly-one FVG closed in parent H4")
    formed, low, high = fvgs[0]
    if receipt.get("poi_type") != "FVG" or _timestamp(
        receipt.get("poi_formed_at")
    ) != formed:
        raise BSourceReceiptError("FVG provenance not physically bound to M15 triple")
    if family == C2:
        expected_start = c2_open
        htf = anchor
    else:
        expected_start = anchor
        htf = anchor
    decision = _timestamp(receipt.get("evaluated_at"))
    count = receipt.get("used_ltf_bar_count")
    if type(count) is not int or not 1 <= count <= 16:
        raise BSourceReceiptError("receipt has invalid live M15 prefix cardinality")
    actual_end = expected_start + timedelta(minutes=15 * count)
    if decision != (htf if family == C2 else actual_end):
        raise BSourceReceiptError("M15 prefix and decision timestamp disagree")
    if family == C3 and decision > anchor + timedelta(hours=4):
        raise BSourceReceiptError("C3 prefix beyond four hours")
    prefix = _window(by_open, expected_start, actual_end)
    touches = [
        b for b in prefix
        if b.opened_at >= formed and b.low <= high and b.high >= low
    ]
    if not touches:
        raise BSourceReceiptError("no real M15 POI touch")
    touch = touches[0]
    if (formed > touch.opened_at
        or _timestamp(receipt.get("poi_first_touched_at")) != touch.closed_at):
        raise BSourceReceiptError("POI first touch not available before its M15 open")
    important = low if s == "long" else high
    ps = [x for x in _m15_ps(prefix, side=s, important=important)
          if x[1] > touch.closed_at]
    if len(ps) != 1:
        raise BSourceReceiptError("missing or multiple source PS proxy in M15 prefix")
    start, confirmed, extreme, level = ps[0]
    if (
        _timestamp(receipt.get("cisd_opposing_series_started_at")) != start
        or _timestamp(receipt.get("cisd_confirmed_at")) != confirmed
        or Decimal(str(receipt.get("protected_swing_price"))) != extreme
        or Decimal(str(receipt.get("cisd_level"))) != level
    ):
        raise BSourceReceiptError("CISD/PS values differ from independently closed M15")
    if not (expected_start <= start < confirmed <= actual_end):
        raise BSourceReceiptError("CISD/PS consumed future/opposing history")
    if _timestamp(receipt.get("swing_point_confirmed_at")) != max(htf, confirmed):
        raise BSourceReceiptError("HTF swing source confirmed before actual source close")
    if family == C3 and confirmed > decision:
        raise BSourceReceiptError("C3 uses future closed M15")
    if receipt.get("c2_double_sweep") is not False:
        raise BSourceReceiptError("C2 dual-sweep D cannot become source receipt")
    if (receipt.get("used_ltf_bar_count") != len(prefix)
        or receipt.get("source_poi_priority_fully_reconstructed") is True):
        raise BSourceReceiptError("source POI priority was falsely certified")

    origin = {
        "market": market, "family": family, "side": s,
        "c1_at": _fmt(c1_open), "c2_at": _fmt(c2_open),
    }
    expected_id = "vt08-source-swing:" + _canonical_digest(origin)
    if event_id != expected_id:
        raise BSourceReceiptError("stable source ID mismatch")
    digest_payload = {k: v for k, v in receipt.items() if k != "snapshot_sha256"}
    if receipt.get("snapshot_sha256") != _canonical_digest(digest_payload):
        raise BSourceReceiptError("receipt snapshot SHA differs from original payload")
    if _timestamp(receipt.get("htf_closure_known_at")) != htf:
        raise BSourceReceiptError("HTF causal close not valid")
    return {
        "market": market, "family": family,
        "source_event_id": event_id,
        "parent_fvg_formed_at": _fmt(formed),
        "ltf_cisd_closed_at": _fmt(confirmed),
        "decision_at": _fmt(decision),
        "pre_c2_reference_swing_attested": False,
        "source_poi_significance_adjudicated": False,
        "author_methodology_accepted": False,
    }


def audit_market(a_file: Path, raw_file: Path) -> dict[str, object]:
    data = json.loads(a_file.read_text(encoding="utf-8"))
    fp, market, checked, sha, rows = load_market_evidence(raw_file)
    if market not in MARKETS or sha != ORIGINAL_SOURCE_SHA:
        raise BSourceReceiptError("unfrozen raw M15 evidence")
    if (data.get("schema") != SCHEMA or data.get("market") != market
        or data.get("evidence_fingerprint") != fp
        or data.get("evidence_checked_at") != _fmt(checked)
        or data.get("source_software_sha") != sha):
        raise BSourceReceiptError("source receipt package not bound to raw M15")
    if (data.get("structural_proof_only") is not True
        or data.get("source_poi_priority_fully_reconstructed") is not False
        or data.get("cognitive_ready") is not False
        or data.get("authorized_orders") != 0
        or data.get("fills") != 0
        or data.get("pnl_evaluated") is not False
        or data.get("sealed_7y_accessed") is not False):
        raise BSourceReceiptError("source artifact falsely asserts authorization")
    events = data.get("source_geometry_receipts")
    if not isinstance(events, list):
        raise BSourceReceiptError("source receipt collection absent")
    indexes = {row.opened_at: row for row in rows}
    if len(indexes) != len(rows):
        raise BSourceReceiptError("duplicate bar source")
    seen: set[str] = set()
    count: Counter[str] = Counter()
    for e in events:
        v = verify_receipt(e, market, indexes)
        if v["source_event_id"] in seen:
            raise BSourceReceiptError("duplicate structural source identity")
        seen.add(str(v["source_event_id"]))
        count[str(v["family"])] += 1
    if (count[C2], count[C3]) != COUNTS[market] or any(
        name not in (C2, C3) for name in count
    ):
        raise BSourceReceiptError("frozen three-family candidate count mismatch")
    declared = data.get("counts")
    if (not isinstance(declared, dict)
        or declared.get(C2 + ":SINGLE_FVG_CISD_PS_SOURCE_SHAPE") != count[C2]
        or declared.get(C3 + ":SINGLE_FVG_CISD_PS_SOURCE_SHAPE") != count[C3]
        or declared.get(C4 + ":SINGLE_FVG_CISD_PS_SOURCE_SHAPE", 0) != 0):
        raise BSourceReceiptError("source declared counts do not match receipts")
    return {
        "market": market, "c2_fvg_ps_shapes": count[C2],
        "c3_intracycle_fvg_ps_shapes": count[C3],
        "c3_c4_fvg_ps_shapes": 0, "independent_receipts_verified": len(events),
        "full_source_methodology_attested": 0,
        "pre_c2_reference_swing_attested": 0,
        "cognitive_ready": 0, "executed_trades": 0, "research_only": True,
    }


def run_all(root: Path) -> dict[str, object]:
    result = [
        audit_market(
            root / "a" / symbol / f"{symbol}-three-families-full.json",
            root / "raw" / symbol / "market-evidence-1095d.json",
        )
        for symbol in MARKETS
    ]
    c2 = sum(int(x["c2_fvg_ps_shapes"]) for x in result)
    c3 = sum(int(x["c3_intracycle_fvg_ps_shapes"]) for x in result)
    if c2 != 237 or c3 != 258:
        raise BSourceReceiptError("A research count not reproduced independently")
    return {
        "schema": "qore.vt08.b_three_family_fvg_m15_receipt_audit.v1",
        "c2_completed_structural_receipts_verified": c2,
        "c3_intracycle_structural_receipts_verified": c3,
        "c3_c4_structural_receipts_verified": 0,
        "actual_entries_verified": 0,
        "prior_reference_swing_eq_attested": 0,
        "all_source_rules_A_verified": False,
        "cognitive_ready": 0,
        "simulated_fills": 0,
        "economic_pnl_computed": False,
        "families": result,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_all(args.artifacts_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True),
                           encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="families"},
                     sort_keys=True))


if __name__ == "__main__":
    main()
