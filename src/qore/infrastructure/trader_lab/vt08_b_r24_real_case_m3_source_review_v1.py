"""VT08 B R24: actual case-by-case TTrades evidence examination, no forged reviews.

Read existing SHA-pinned R23 source dossiers and independent original R3 M3
native data to produce reviewer-readable C2 snapshots (not PnL, not a new
strategy). Cases are selected deterministically from frozen blind R19 and
include controls; none receives author-signoff automatically.
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
from qore.infrastructure.trader_lab.vt08_b_r11_cisd_after_htf_close_chronology_v1 import STAGE
from qore.infrastructure.trader_lab.vt08_b_r23_semantic_review_firstfail_ledger_v1 import (
    SCHEMA as R23_SCHEMA,
)
from qore.infrastructure.trader_lab.vt08_b_r23_semantic_review_firstfail_ledger_v1 import (
    digest as digest23,
)

SCHEMA = "qore.vt08.b.r24.real_case_m3_review_snapshot.v1"
M3 = timedelta(minutes=3)
REVIEW_BUCKETS = (
    "WITHIN_BEARISH_OPPOSING_SERIES",
    "BEFORE_BEARISH_OPPOSING_SERIES",
    "NO_H1_THREE_BAR_FVG",
    "IN_CISD_CONFIRMATION_BAR_INTRABAR_UNKNOWN",
)
PINNED = {
    "EURJPY": (538, 21, "642751096ea272b327838aef6e1ed4665053901219b10b4ad1744619845a0c7c"),
    "USDCHF": (518, 21, "5af3eacb822456217d3a05e0e6d46dd015b445a168a43f64143e64ac1ca9c346"),
    "NZDUSD": (550, 21, "1d534eb82a45f6fae8386eb896d47ad2cdaf3d0fedc5b51fa3339124e683b3eb"),
    "CADJPY": (516, 21, "1ec64b4bff295b2b18d0e96010ddfc6943fadc0dd7336abc6347b05fd5627dd9"),
    "USDCAD": (535, 23, "31f8241ad67c1a1d3ddbb90efe47c89f524b4e769544abada2cc35c952b4647e"),
}
CISD_SOURCE = "https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/"
IDEAL_SOURCE = "https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/"


def review_real_frozen_cases(
    source_r23: dict[str, object], frozen: dict[str, object],
    native_m3: Path, *, market: str,
) -> dict[str, object]:
    if market not in PINNED:
        raise ValueError("R24 outside authorized original VT08 markets")
    expected, sample, sha23 = PINNED[market]
    if (
        source_r23.get("schema") != R23_SCHEMA
        or source_r23.get("market") != market
        or digest23(source_r23) != sha23
        or source_r23.get("original_source_cases_unchanged") != expected
        or source_r23.get("sample_cases_for_genuine_review") != sample
        or source_r23.get("source_author_complete") != 0
        or source_r23.get("human_A_genuinely_reviewed") != 0
        or source_r23.get("human_B_genuinely_reviewed") != 0
        or source_r23.get("broker_fills") != 0
        or source_r23.get("QORE_alpha_excluded") is not True
        or source_r23.get("sizing_used") is not False
        or source_r23.get("holdout_7y_accessed") is not False
    ):
        raise ValueError("R24 R23 immutable original evidence or owner scope changed")
    sha3, raw = _raw_bars(native_m3, "M3", market)
    if frozen.get("source_m3_sha256") != sha3:
        raise ValueError("R24 original cTrader source SHA mismatch")
    cases = frozen.get("examples_by_stage", {}).get(STAGE)
    if not isinstance(cases, list) or len(cases) != expected:
        raise ValueError("R24 wrong raw case denominator")
    indexed = {}
    for case in cases:
        c2 = _instant(case["c2_opened_at_utc"])
        c3 = _instant(case["decision_at_utc"])
        cid = hashlib.sha256(
            (market + "|" + c2.isoformat() + "|" + c3.isoformat()).encode()
        ).hexdigest()
        if cid in indexed:
            raise ValueError("R24 duplicate original M3 case")
        indexed[cid] = case
    original = source_r23.get("review_dossiers")
    if not isinstance(original, list) or len(original) != sample:
        raise ValueError("R24 preregistered sample incomplete")
    groups: dict[str, list[dict[str, object]]] = {}
    for row in original:
        if row.get("human_A_real_review") is not None or row.get(
            "human_B_real_review"
        ) is not None or row.get("source_authenticity_accepted") is not False:
            raise ValueError("R24 no fake methodological signoff allowed")
        physical = row["physical_candidate_evidence"]["r20_bearish_series_causal_witness"]
        bucket = physical["physical_first_touch_relative_to_run"]
        groups.setdefault(bucket, []).append(row)
    # The deterministic first SHA-sorted example is selected from each bucket.
    # No PnL or future returns influence the choice.
    chosen = []
    for bucket in REVIEW_BUCKETS:
        eligible = sorted(groups.get(bucket, []), key=lambda x: x["case_id_sha256"])
        if eligible:
            chosen.append((bucket, eligible[0]))
    if not chosen:
        raise ValueError("R24 no original preregistered review case")
    dossiers = []
    for bucket, row in chosen:
        cid = row["case_id_sha256"]
        if cid not in indexed:
            raise ValueError("R24 source blinded candidate missing R3 raw")
        original_case = indexed[cid]
        c2 = _instant(original_case["c2_opened_at_utc"])
        receipts = original_case.get("c2_m3_raw_bar_receipts")
        if not isinstance(receipts, list) or len(receipts) != 10:
            raise ValueError("R24 source C2 requires original 10 M3 bars")
        candles = []
        for i, receipt in enumerate(receipts):
            opened = c2 + i * M3
            ohlc = _verify_bar(
                receipt, expected_open=opened, minutes=3,
                profile="M3", source_sha=sha3, raw=raw,
            )
            candles.append({
                "opened_at_utc": opened.isoformat(),
                "available_at_utc": (opened + M3).isoformat(),
                "source_bar_id": receipt["source_bar_id"],
                "open": str(ohlc[0]), "high": str(ohlc[1]),
                "low": str(ohlc[2]), "close": str(ohlc[3]),
                "down_close": ohlc[3] < ohlc[0],
            })
        physical = row["physical_candidate_evidence"]["r20_bearish_series_causal_witness"]
        context = row["physical_candidate_evidence"]["r22_competing_poi_context"]
        if physical["case_id_sha256"] != cid or context["case_id_sha256"] != cid:
            raise ValueError("R24 wrong physical witnesses for case")
        if source_r23["original_r18_sha256"] != physical["original_r18_source_sha256"]:
            raise ValueError("R24 original R18 witnesses changed")
        cisd = _instant(physical["cisd_close_at_utc"])
        series = _instant(physical["opposing_series_opened_at_utc"])
        if not (c2 <= series < cisd <= c2+timedelta(minutes=30)):
            raise ValueError("R24 contradictory source/CISD/series chronology")
        run_bars = [
            x for x in candles if series <= _instant(x["opened_at_utc"]) < cisd-M3
        ]
        if not run_bars or not all(x["down_close"] for x in run_bars):
            raise ValueError("R24 opposing run not native down-close series")
        evidence = {
            "case_id_sha256": cid, "market": market, "review_bucket": bucket,
            "c2_opened_at_utc": c2.isoformat(),
            "cisd_confirmed_at_utc": cisd.isoformat(),
            "opposing_series_started_at_utc": series.isoformat(),
            "reviewed_as_of_utc": row["C3_decision_at_utc"],
            "native_c2_m3_source_only_bars": candles,
            "original_m3_source_sha256": sha3,
            "fvg_touch_phase": physical["fvg_first_touch_phase"] if physical[
                "original_fvg_physical_exists"
            ] else "NO_FVG_IN_THREE_CLOSED_H1_WINDOW",
            "fvg_first_touch_id": physical.get("fvg_first_touch_m3_bar_id"),
            "run_fvg_touch_bar_ids": physical.get("bearish_series_fvg_touch_bar_ids", []),
            "run_liquidity_sweep_bar_ids": physical.get("bearish_series_sweep_bar_ids", []),
            "same_bar_sweep_and_poi_touch": physical.get(
                "same_bar_fvg_touch_and_liquidity_sweep"
            ),
            "same_bar_tick_sequence_proven": False,
            "competing_poi_source_context": context,
            "source_statement_validated": {
                "CISD_requires_important_level_and_opposing_series": CISD_SOURCE,
                "Ideal_Formation_requires_meaningful_POI": IDEAL_SOURCE,
            },
            "methodological_findings": {
                "C2_M3_bar_series_physically_verifiable": True,
                "important_POI_author_selected": False,
                "relevant_swing_author_selected": False,
                "protected_swing_author_confirmed": False,
                "trade_admission": False,
            },
            "case_review_ruling": "D_NO_AUTHOR_SELECTION_EVIDENCE_YET__WAIT",
            "human_A_signed": False, "human_B_signed": False,
            "cognitive_admitted": False, "broker_fill": False,
        }
        dossiers.append(evidence)
    return {
        "schema": SCHEMA, "market": market,
        "owner_scope": "VT08_CURRENT_ONLY_NO_QORE_ALPHA",
        "preregistered_original_universe": expected,
        "original_blind_sample": sample,
        "case_review_snapshots": len(dossiers), "review_evidence": dossiers,
        "count_by_real_temporal_bucket": dict(sorted(Counter(
            x["review_bucket"] for x in dossiers
        ).items())),
        "author_complete_entries": 0, "genuine_A_signoffs": 0,
        "genuine_B_signoffs": 0, "cognitive_admissions": 0,
        "broker_fills": 0, "economic_gates_evaluated": False,
        "sizing_used": False, "holdout_7y_accessed": False,
    }


def digest(report: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(
        report, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
