"""VT08 B R12: separate CISD formation time from joint as-of verification time.

TTrades primary text describes identifying LTF CISD *inside* a closed HTF
candle, as well as "higher timeframe closure first". Those phrases cannot
by themselves determine if CISD must physically FORM after HTF.close or if
the setup is reviewed retrospectively when HTF has closed. Record BOTH
clocks without claiming author semantics or certified trades.

Uses B R11's original-M3 independently rehashed census, not an A detector.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
)
from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import (
    STAGE,
    audit_cisd_htf_sequence,
)

SCHEMA = "qore.vt08.b.r12.dual_clock_physical_cisd_source_boundary.v1"
SOURCE = (
    "https://ttrades.com/how-change-in-the-state-of-delivery-"
    "cisd-confirms-swing-points/"
)
SAME_DECISION = timedelta(minutes=30)
M3 = timedelta(minutes=3)


def dual_clock_cisd_source_gate(
    r3: dict[str, object],
    *,
    market: str,
    original_m3: Path,
) -> dict[str, object]:
    """Do not elevate pre-close formation to post-close author confirmation."""
    # B R11 verifies original native M3 RAW file SHA/market, every referenced
    # M3 source_bar_id/OHLC/closed_at, event uniqueness and full positive set.
    attested = audit_cisd_htf_sequence(
        r3, expected_market=market, native_m3_file=original_m3,
    )
    stage = r3.get("examples_by_stage")
    if not isinstance(stage, dict):
        raise ValueError("R12 missing original frozen stage")
    cases = stage.get(STAGE)
    if (
        not isinstance(cases, list)
        or len(cases) != attested["r3_unique_m3_proxy_source_cases"]
        or attested["source_author_complete_entries"] != 0
        or attested["cognitive_admissions"] != 0
        or attested["broker_fills"] != 0
        or attested["economic_gates_evaluated"] is not False
    ):
        raise ValueError("R12 cannot admit false source or economic authority")
    rows: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("R12 non-object source event")
        details = case.get("details")
        if not isinstance(details, dict):
            raise ValueError("R12 missing PS/CISD timing")
        c1 = _instant(case.get("c1_opened_at_utc"))
        c2 = _instant(case.get("c2_opened_at_utc"))
        c3 = _instant(case.get("decision_at_utc"))
        cisd = _instant(details.get("cisd_confirmed_at_utc"))
        # R11 verified each cisd aligns to a physically closed native M3.
        if (
            c2 - c1 != SAME_DECISION
            or c3 - c2 != SAME_DECISION
            or not c2 < cisd <= c3
            or (cisd - c2) % M3 != timedelta(0)
        ):
            raise ValueError("R12 inconsistent temporal source sequence")
        identity = hashlib.sha256(
            (market + "|" + c2.isoformat() + "|" + c3.isoformat()).encode()
        ).hexdigest()
        if identity in ids:
            raise ValueError("R12 duplicate event identity")
        ids.add(identity)
        before = cisd < c3
        counts["cisds_formed_before_c2_closed"] += int(before)
        counts["cisds_formed_simultaneously_with_c2_close"] += int(not before)
        counts["cisds_physically_formed_after_c2_close"] += 0
        counts["joint_c2_and_m3_evidence_known_at_c3_open"] += 1
        rows.append({
            "case_id_sha256": identity,
            "market": market,
            "c1_closed_at_utc": c2.isoformat(),
            "c2_opened_at_utc": c2.isoformat(),
            "c2_closed_at_utc": c3.isoformat(),
            "decision_at_utc": c3.isoformat(),
            "m3_cisd_proxy_formed_at_utc": cisd.isoformat(),
            "m3_cisd_before_c2_close": before,
            "m3_cisd_simultaneous_with_c2_close": not before,
            "earliest_jointly_observable_at_utc": c3.isoformat(),
            "physical_intra_c2_m3_evidence_available_at_c3": True,
            "author_accepts_retrospective_intra_c2_cisd": None,
            "original_htf_confirming_candle_identity": None,
            "original_author_rule_status": "D_UNADJUDICATED",
            "source_complete": False,
            "cognitive_admission_authorized": False,
        })
    expected_before = attested["confirmed_while_c2_in_progress"]
    expected_at = attested["confirmed_exactly_at_c2_close"]
    if (
        counts["cisds_formed_before_c2_closed"] != expected_before
        or counts["cisds_formed_simultaneously_with_c2_close"] != expected_at
        or len(ids) != len(cases)
    ):
        raise ValueError("R12 did not conserve independent B R11 census")
    return {
        "schema": SCHEMA,
        "source_primary_url": SOURCE,
        "market": market,
        "original_raw_m3_sha256": attested["raw_m3_sha256"],
        "full_r3_unique_source_cases": len(rows),
        "counts": dict(counts),
        "all_case_clocks_before_outcome": rows,
        "author_temporal_interpretation": "D_UNADJUDICATED",
        "semantic_rationale": (
            "BOTH HTF C2 CLOSE AND INTRA-C2 M3 CISD ARE OBSERVABLE "
            "AT C3 OPEN; PHYSICAL TIMING DOES NOT PROVE AUTHOR ACCEPTANCE"
        ),
        "a_b_signed_manifest": None,
        "author_complete_events": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "profit_factor": None,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
    }


def canonical_digest(result: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
