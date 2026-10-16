"""B R20: independent raw M3 causal sweep→CISD→M30 C2 closure audit.

TTrades describes LTF CISD *inside* HTF C2, evaluated alongside its closing
confirmation before positional C3 entry. Physical time order is NOT author
validation: important POI, swing relevance, PS, breaker and target remain D.
No outcome, broker fill, sizing, QORE-alpha or 7Y used.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _aggregate,
    _instant,
    _raw_bars,
    _verify_bar,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_author_semantics_reviewer_pack_v1 import (
    R3_STAGE,
    build_blind_semantic_review_packets,
)

M3 = timedelta(minutes=3)
M30 = timedelta(minutes=30)
SRC_CISD = (
    "https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/"
)
SRC_PLAYBOOK = (
    "https://ttrades.com/fractal-model-playbook-aligning-daily-hourly-and-5-minute-charts/"
)
SRC_POSITIONAL = "https://ttrades.com/positional-entries-enter-before-the-expansion/"


def audit_intrac2_sweep_cisd_source(
    r3: dict[str, object], r7: dict[str, object], *,
    market: str, native_m3_file: Path,
) -> dict[str, object]:
    """Produce exhaustive causal first-fail evidence, never approve a setup."""
    reviewer = build_blind_semantic_review_packets(
        r3, r7, expected_market=market,
    )
    native_sha, raw = _raw_bars(native_m3_file, "M3", market)
    if r3.get("source_m3_sha256") != native_sha:
        raise ValueError("R20 native M3 SHA differs from frozen cTrader source")
    cases = r3["examples_by_stage"][R3_STAGE]
    if len(cases) != reviewer["all_cases_census"]:
        raise ValueError("R20 source universe changed")
    result_by_id: dict[str, dict[str, object]] = {}
    outcomes: Counter[str] = Counter()
    temporal: Counter[str] = Counter()
    for item in cases:
        c2 = _instant(item.get("c2_opened_at_utc"))
        decision = _instant(item.get("decision_at_utc"))
        if decision != c2 + M30:
            raise ValueError("R20 C3 decision is not M30 C2 close")
        details = item.get("details")
        if not isinstance(details, dict) or (
            details.get("m3_ps_proxy_count") != 1
            or details.get("proxy_not_author_validated") is not True
            or details.get("methodology_complete") is not False
        ):
            raise ValueError("R20 forbidden PS semantic promotion")
        cisd = _instant(details.get("cisd_confirmed_at_utc"))
        opp = _instant(details.get("opposing_series_opened_at_utc"))
        if not (opp < cisd and c2 < cisd <= decision):
            raise ValueError("R20 CISD/PS evidence out of causal C2 bounds")
        groups = (
            item.get("c1_m3_raw_bar_receipts"),
            item.get("c2_m3_raw_bar_receipts"),
        )
        if any(not isinstance(group, list) or len(group) != 10 for group in groups):
            raise ValueError("R20 C1/C2 full original M3 required")
        c1_prices = []
        c2_prices = []
        for start, recs, collected in (
            (c2 - M30, groups[0], c1_prices),
            (c2, groups[1], c2_prices),
        ):
            for i, rec in enumerate(recs):
                collected.append(_verify_bar(
                    rec, expected_open=start+i*M3, minutes=3,
                    profile="M3", source_sha=native_sha, raw=raw,
                ))
        c1ohlc, c2ohlc = _aggregate(c1_prices), _aggregate(c2_prices)
        c1_low = c1ohlc[2]
        if not (
            c2ohlc[2] < c1_low
            and c2ohlc[1] <= c1ohlc[1]
            and c1_low < c2ohlc[3] < c1ohlc[1]
            and c2ohlc[3] > c2ohlc[0]
        ):
            raise ValueError("R20 frozen bullish C2 OHLC geometry differs from native M3")
        sweep_indices = [i for i, p in enumerate(c2_prices) if p[2] < c1_low]
        if not sweep_indices:
            raise ValueError("R20 missing physically observed C1-low sweep")
        sweep_i = min(sweep_indices)
        # A candle low is observable at the candle close in a closed-bar
        # replay, NOT at an invented intrabar tick clock.
        first_sweep_observable = c2+(sweep_i+1)*M3
        cisd_i = int((cisd-c2)/M3)-1
        if cisd_i not in range(10) or cisd != c2+(cisd_i+1)*M3:
            raise ValueError("R20 CISD timestamp not a closed source M3 bar")
        if sweep_i < cisd_i:
            bucket = "SWEEP_OBSERVED_BEFORE_CISD_M3_CLOSE"
        elif sweep_i == cisd_i:
            bucket = "SWEEP_AND_CISD_SAME_M3_CLOSE_INTRABAR_UNRESOLVED"
        else:
            bucket = "SWEEP_OBSERVED_AFTER_CISD_M3_CLOSE_FIRST_FAIL"
        outcomes[bucket] += 1
        delta = int((decision-cisd)/M3)
        temporal["CISD_BEFORE_C2_CLOSE" if delta else "CISD_AT_C2_CLOSE"] += 1
        eid = hashlib.sha256(
            f"{market}|{c2.isoformat()}|{decision.isoformat()}".encode(),
        ).hexdigest()
        if eid in result_by_id:
            raise ValueError("R20 duplicate frozen source identity")
        result_by_id[eid] = {
            "case_id_sha256": eid,
            "market": market,
            "c2_opened_at_utc": c2.isoformat(),
            "c3_decision_at_utc": decision.isoformat(),
            "c1_low_physical_only": str(c1_low),
            "first_c1_low_sweep_m3_source_bar_id": groups[1][sweep_i]["source_bar_id"],
            "first_c1_low_sweep_available_at_utc": first_sweep_observable.isoformat(),
            "cisd_m3_source_bar_id": groups[1][cisd_i]["source_bar_id"],
            "cisd_observed_closed_at_utc": cisd.isoformat(),
            "m3_sweep_vs_cisd": bucket,
            "m3_cisd_inside_c2_before_c3": True,
            "m30_c2_closed_at_entry_decision": True,
            "c1_low_author_important_level": "D_UNADJUDICATED",
            "source_poi_and_swing_author_validated": False,
            "protected_swing_author_validated": False,
            "ttrades_source_complete": False,
            "cognitive_admission": False,
        }
    if len(result_by_id) != reviewer["all_cases_census"] or sum(outcomes.values()) != len(
        result_by_id
    ):
        raise ValueError("R20 physical sample dropping source cases")
    pack_ids = {p["case_id_sha256"] for p in reviewer["review_packets"]}
    if not pack_ids.issubset(result_by_id) or len(pack_ids) != len(
        reviewer["review_packets"]
    ):
        raise ValueError("R20 original blind reviewer packet drift")
    if sum(temporal.values()) != len(result_by_id):
        raise ValueError("R20 CISD timing evidence census drift")
    return {
        "schema": "qore.vt08.b.r20.intrac2_sweep_cisd_source.v1",
        "market": market,
        "source_m3_sha256": native_sha,
        "frozen_r3_sha256": reviewer["frozen_r3_sha256"],
        "frozen_r7_sha256": reviewer["frozen_r7_sha256"],
        "cases_audited": len(result_by_id),
        "first_sweep_vs_cisd_counts": dict(sorted(outcomes.items())),
        "intrac2_cisd_vs_c2_close_counts": dict(sorted(temporal.items())),
        "r19_blind_packets_enriched_count": len(pack_ids),
        "blind_packet_causal_evidence": [
            result_by_id[p["case_id_sha256"]]
            for p in reviewer["review_packets"]
        ],
        "all_case_causal_index": [
            result_by_id[i] for i in sorted(result_by_id)
        ],
        "author_primary_sources": {
            "ltf_cisd_inside_htf": SRC_CISD,
            "cisd_inside_candle2_playbook": SRC_PLAYBOOK,
            "model_complete_before_positional_c3": SRC_POSITIONAL,
        },
        "interpretation": (
            "HTF_C2_CLOSE_AND_LTF_INSIDE_C2_BOTH_OBSERVED_BY_C3; "
            "NO_REQUIREMENT_CISD_AFTER_C2_CLOSE_FOR_THIS_CAUSAL_BUNDLE"
        ),
        "author_semantic_review_complete": False,
        "source_complete_entries": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "verdict": "PHYSICAL_CAUSAL_FIRST_FAIL_ONLY_NOT_AUTHOR_APPROVED",
    }
