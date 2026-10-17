"""B R11 physical chronology of M3 CISD proxy inside frozen M30 C2.

Does NOT prove an author-valid CISD. Audits which M30 candle had closed
when A's M3 confirmation was available; never reads post-C3 outcomes.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _raw_bars,
    _verify_bar,
)

SCHEMA = "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1"
STAGE = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
M3 = timedelta(minutes=3)
M30 = timedelta(minutes=30)


def audit_cisd_htf_sequence(
    report: dict[str, object],
    *,
    expected_market: str,
    native_m3_file: Path,
) -> dict[str, object]:
    if report.get("schema") != SCHEMA or report.get("market") != expected_market:
        raise ValueError("R11 market/source R3 identity changed")
    cases_by_stage = report.get("examples_by_stage")
    stage_counts = report.get("stage_counts")
    if not isinstance(cases_by_stage, dict) or not isinstance(stage_counts, dict):
        raise ValueError("R11 frozen all-stages census missing")
    positives = cases_by_stage.get(STAGE)
    if not isinstance(positives, list) or not positives:
        raise ValueError("R11 frozen M3 PS precursor receipts missing")
    if (
        type(stage_counts.get(STAGE)) is not int
        or len(positives) != stage_counts[STAGE]
        or len(positives) != report.get("all_unique_proxy_cases_with_raw_receipts")
    ):
        raise ValueError("R11 stage/source universe does not reconcile")
    sha, raw = _raw_bars(native_m3_file, "M3", expected_market)
    if report.get("source_m3_sha256") != sha:
        raise ValueError("R11 original cTrader M3 source SHA mismatched")
    count_by_delta: Counter[int] = Counter()
    first_closed_after_cisd: Counter[str] = Counter()
    seen: set[datetime] = set()
    aligned = 0
    sample: list[dict[str, object]] = []
    for case in positives:
        if not isinstance(case, dict) or case.get("market") != expected_market:
            raise ValueError("R11 cross-market M3 source event")
        if (
            case.get("stage") != STAGE
            or case.get("A_rule_complete") is not False
            or case.get("B_signoff") is not False
            or case.get("cognitive_ready") is not False
            or case.get("broker_fill") is not False
            or case.get("pnl_read") is not False
        ):
            raise ValueError("R11 physical PS masquerading as author/fill permission")
        c2 = _instant(case.get("c2_opened_at_utc"))
        c1 = _instant(case.get("c1_opened_at_utc"))
        decision = _instant(case.get("decision_at_utc"))
        if decision - c2 != M30 or c2 - c1 != M30:
            raise ValueError("R11 M30 chronology changed")
        if c2 in seen:
            raise ValueError("R11 duplicate physical M30 C2")
        seen.add(c2)
        details = case.get("details")
        if not isinstance(details, dict):
            raise ValueError("R11 missing per-event M3 proxy details")
        if (
            details.get("proxy_not_author_validated") is not True
            or details.get("reference_swing_author_valid") is not False
            or details.get("significant_poi_author_valid") is not False
            or details.get("breaker_low_author_valid") is not False
            or details.get("methodology_complete") is not False
            or details.get("m3_ps_proxy_count") != 1
        ):
            raise ValueError("R11 false author CISD method status")
        confirmed = _instant(details.get("cisd_confirmed_at_utc"))
        series_opened = _instant(details.get("opposing_series_opened_at_utc"))
        if not c2 < confirmed <= decision or series_opened > confirmed:
            raise ValueError("R11 proxy CISD confirmation violates C2 causal window")
        receipts = case.get("c2_m3_raw_bar_receipts")
        if not isinstance(receipts, list) or len(receipts) != 10:
            raise ValueError("R11 C2 requires 10 native M3 receipts")
        seen_closes: set[datetime] = set()
        for i, rec in enumerate(receipts):
            opened = c2 + i * M3
            _verify_bar(
                rec, expected_open=opened, minutes=3, profile="M3",
                source_sha=sha, raw=raw,
            )
            seen_closes.add(opened + M3)
        if confirmed not in seen_closes:
            raise ValueError("R11 CISD timestamp not an original closed M3 bar")
        remaining = decision - confirmed
        if remaining.total_seconds() % 180:
            raise ValueError("R11 M3 timing not 3-minute-aligned")
        delta_minutes = int(remaining.total_seconds() / 60)
        count_by_delta[delta_minutes] += 1
        if confirmed < decision:
            first_closed_after_cisd["C2_OPEN_BUT_NOT_CLOSED"] += 1
        elif confirmed == decision:
            first_closed_after_cisd["C2_CLOSE_SIMULTANEOUS"] += 1
        else:
            raise ValueError("R11 future M3 CISD")
        aligned += 1
        if len(sample) < 6:
            sample.append({
                "c2_opened_at_utc": c2.isoformat(),
                "previous_m30_c1_closed_at_utc": c2.isoformat(),
                "m3_cisd_proxy_confirmed_at_utc": confirmed.isoformat(),
                "c2_closed_at_utc": decision.isoformat(),
                "minutes_before_c2_close": delta_minutes,
            })
    if aligned != len(positives):
        raise ValueError("R11 incomplete source chronology")
    return {
        "market": expected_market,
        "r3_unique_m3_proxy_source_cases": aligned,
        "raw_m3_sha256": sha,
        "confirmed_while_c2_in_progress": first_closed_after_cisd[
            "C2_OPEN_BUT_NOT_CLOSED"
        ],
        "confirmed_exactly_at_c2_close": first_closed_after_cisd[
            "C2_CLOSE_SIMULTANEOUS"
        ],
        "confirmed_after_c2_close": 0,
        "minutes_before_c2_close_histogram": {
            str(k): count_by_delta[k] for k in sorted(count_by_delta)
        },
        "six_chronological_examples_source_only": sample,
        "prior_m30_c1_closed_by_cisd": True,
        "m30_c2_closed_by_cisd_in_all_cases": (
            first_closed_after_cisd["C2_OPEN_BUT_NOT_CLOSED"] == 0
        ),
        "ttrades_htf_closure_to_ltf_cisd_rule_author_adjudicated": False,
        "source_author_complete_entries": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "verdict": "CISD_PROXY_TIMING_PHYSICAL_ONLY_AUTHOR_RULE_D",
    }
