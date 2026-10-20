"""R26 source-verified join: reuse R25 receipts and immutable R19 review sample."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_b_r25_ps_reanchor_and_cisd_reclaim_native_v1 import (
    audit_r25, M3,
)
from qore.infrastructure.trader_lab.vt08_b_r26_second_run_diagnostic import inspect
from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant, _raw_bars, _verify_bar,
)

FIRSTFAIL = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"


def audit_r26(frozen: dict, blind: dict, *, market: str, native_m3: Path) -> dict:
    base = audit_r25(frozen, blind, market=market, native_m3=native_m3)
    sha, raw = _raw_bars(native_m3, "M3", market)
    if sha != base["source_native_m3_sha256"]:
        raise ValueError("R26 native source SHA drift")
    cases = frozen["examples_by_stage"][FIRSTFAIL]
    prior = {r["case_id_sha256"]: r for r in base["full_source_case_index"]}
    if len(cases) != len(prior):
        raise ValueError("R26 census drift")
    result = {}
    counts = Counter()
    for case in cases:
        c2 = _instant(case["c2_opened_at_utc"])
        c3 = _instant(case["decision_at_utc"])
        from hashlib import sha256
        cid = sha256(f"{market}|{c2.isoformat()}|{c3.isoformat()}".encode()).hexdigest()
        row = prior.pop(cid, None)
        if row is None:
            raise ValueError("R26 case mismatch")
        receipts = case["c2_m3_raw_bar_receipts"]
        if len(receipts) != 10:
            raise ValueError("R26 missing source receipts")
        prices = [
            _verify_bar(rec, expected_open=c2+i*M3, minutes=3,
                        profile="M3", source_sha=sha, raw=raw)
            for i, rec in enumerate(receipts)
        ]
        cisd_i = int((_instant(row["first_cisd_closed_at_utc"])-c2)//M3)
        state = inspect(prices, cisd_i, row["original_run_low"])
        if str(state["anchor"]) != row["reanchored_as_of_cisd_closed_low"]:
            raise ValueError("R26 reanchor disagrees with R25")
        if (state["first_breach"] is None) != (
            row["first_post_cisd_break_reanchored_index"] is None
        ):
            raise ValueError("R26 breach disagrees with R25")
        if state["first_breach"] != row["first_post_cisd_break_reanchored_index"]:
            raise ValueError("R26 first breach drift")
        for run in state["runs"]:
            start, end = run["start"], run["end_exclusive"]
            run["source_bar_ids"] = [
                receipts[i]["source_bar_id"] for i in range(start, end)
            ]
            run["confirming_bar_source_id"] = (
                receipts[run["confirm_index"]]["source_bar_id"]
                if run["confirm_index"] is not None else None
            )
            run["confirmation_available_at_utc"] = (
                (c2+(run["confirm_index"]+1)*M3).isoformat()
                if run["confirm_index"] is not None else None
            )
        counts[state["status"]] += 1
        result[cid] = {"case_id_sha256": cid, "market": market, **state}
    if prior or len(result) != base["original_candidate_census"]:
        raise ValueError("R26 unjoined original cases")
    selected = base["same_107_r19_blind_source_review"]
    return {
        "schema": "qore.vt08.b.r26.native_m3_second_run_audit.v1",
        "market": market,
        "source_native_m3_sha256": sha,
        "original_blind_r19_report_sha256": base["original_blind_r19_report_sha256"],
        "original_candidate_census": len(result),
        "original_r19_source_review_cases": len(selected),
        "histogram": dict(sorted(counts.items())),
        "full_source_case_index": [result[k] for k in sorted(result)],
        "same_r19_blind_case_ids": [r["case_id_sha256"] for r in selected],
        "source_complete_entries": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "trade_authorized": False,
        "verdict": "R26_GEOMETRY_ONLY_NO_AUTHOR_SIGNOFF",
    }
