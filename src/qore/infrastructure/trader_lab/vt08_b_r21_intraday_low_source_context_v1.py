"""B R21 source diagnostic: C1-low sweep versus earlier NY day-to-date low.

TTrades says 'intraday lows' in M30->M3 Example 1 but does not prescribe a
NY-midnight day-low selection algorithm. This is a labeled QORE PHYSICAL
CONTEXT OBSERVATION, NOT a new filter, author POI or CandidateEvent.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _prices,
    _raw_bars,
)
from qore.infrastructure.trader_lab.vt08_b_r20_intrac2_cisd_sweep_causal_order_v1 import (
    audit_intrac2_sweep_cisd_source,
)

NY = ZoneInfo("America/New_York")
STEP = timedelta(minutes=3)
SRC_EXAMPLE = (
    "https://ttrades.com/timeframe-alignment-how-to-align-higher-and-lower-time-frames-for-precision-entries/"
)
LABEL_YES = "C2_SWEPT_PRIOR_NY_MIDNIGHT_TO_C2_DAY_LOW"
LABEL_NO = "C2_ONLY_SWEPT_LOCAL_C1_LOW_NOT_NY_DAY_LOW"
LABEL_GAP = "NY_DAY_TO_DATE_CONTEXT_INCOMPLETE_D"


def inspect_intraday_low_context(
    r3: dict[str, object], r7: dict[str, object], *,
    market: str, native_m3_file: Path,
) -> dict[str, object]:
    """Full 2657 frozen census; strictly as-of C2.close, no PnL."""
    r20 = audit_intrac2_sweep_cisd_source(
        r3, r7, market=market, native_m3_file=native_m3_file,
    )
    native_sha, raw = _raw_bars(native_m3_file, "M3", market)
    if native_sha != r20["source_m3_sha256"]:
        raise ValueError("R21 M3 source changed after causal attestation")
    by_id = {x["case_id_sha256"]: x for x in r20["all_case_causal_index"]}
    if len(by_id) != r20["cases_audited"]:
        raise ValueError("R21 duplicate causal ID")
    stage = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
    c2_events = r3["examples_by_stage"][stage]
    result = []
    counts: Counter[str] = Counter()
    c1_vs_prior_day: Counter[str] = Counter()
    for case in c2_events:
        c2 = _instant(case.get("c2_opened_at_utc"))
        decision = _instant(case.get("decision_at_utc"))
        key = __import__("hashlib").sha256(
            f"{market}|{c2.isoformat()}|{decision.isoformat()}".encode()
        ).hexdigest()
        trusted = by_id.pop(key, None)
        if trusted is None:
            raise ValueError("R21 C2 identity not verified by independent R20")
        bars = case["c2_m3_raw_bar_receipts"]
        c2_low = min(_prices(p["ohlc"])[2] for p in bars)
        c1_low = Decimal(str(trusted["c1_low_physical_only"]))
        if not c2_low < c1_low:
            raise ValueError("R21 physically swept C1.low contradicted")
        start = datetime.combine(
            c2.astimezone(NY).date(), time.min, tzinfo=NY,
        ).astimezone(UTC)
        if c2 <= start or (c2-start).total_seconds() % 180:
            raise ValueError("R21 malformed NY day-to-date observation period")
        day_prior_low: Decimal | None = None
        t = start
        gap = False
        checked = 0
        while t < c2:
            row = raw.get(t)
            if row is None or _instant(row.get("closed_at")) != t+STEP:
                gap = True
                break
            low = _prices(tuple(str(row.get(k)) for k in (
                "open", "high", "low", "close",
            )))[2]
            if day_prior_low is None or low < day_prior_low:
                day_prior_low = low
            t += STEP
            checked += 1
        if gap or day_prior_low is None:
            label = LABEL_GAP
            significance = "UNKNOWN_INCOMPLETE_NY_DAY_CONTEXT"
        else:
            label = LABEL_YES if c2_low < day_prior_low else LABEL_NO
            if c1_low == day_prior_low:
                significance = "C1_LOW_EQUAL_PRIOR_DAY_TO_DATE_LOW"
            else:
                significance = "C1_LOW_ABOVE_PRIOR_DAY_TO_DATE_LOW"
            c1_vs_prior_day[significance] += 1
        counts[label] += 1
        result.append({
            "case_id_sha256": key,
            "market": market,
            "ny_day": c2.astimezone(NY).date().isoformat(),
            "c2_opened_at_utc": c2.isoformat(),
            "C3_decision_at_utc": decision.isoformat(),
            "c1_low": str(c1_low),
            "c2_low": str(c2_low),
            "ny_midnight_to_c2_prior_low": (
                None if gap or day_prior_low is None else str(day_prior_low)
            ),
            "day_context_bar_count_observed": checked,
            "day_context_complete": not gap,
            "day_low_source_diagnostic": label,
            "c1_low_vs_day_context": significance,
            "important_level_ttrades_author_confirmed": False,
            "poI_selection_source_rule": "D_NOT_ADJUDICATED",
            "cognitive_admission": False,
        })
    if by_id or len(result) != r20["cases_audited"] or sum(counts.values()) != len(
        result
    ):
        raise ValueError("R21 failed all-case conservation")
    samples = {p["case_id_sha256"] for p in r20["blind_packet_causal_evidence"]}
    return {
        "schema": "qore.vt08.b.r21.day_low_context_diagnostic.v1",
        "market": market,
        "original_raw_m3_sha256": native_sha,
        "r20_universe_count": r20["cases_audited"],
        "all_case_count": len(result),
        "day_low_category_counts": {k: counts[k] for k in (
            LABEL_YES, LABEL_NO, LABEL_GAP,
        )},
        "c1_low_vs_completed_ny_context_counts": dict(c1_vs_prior_day),
        "r19_sample_enriched_count": len(samples),
        "blind_review_day_context": [
            x for x in result if x["case_id_sha256"] in samples
        ],
        "full_day_context_index": result,
        "author_example_source": SRC_EXAMPLE,
        "reference_window_note": (
            "NY midnight to C2.open is a fixed QORE physical comparison; "
            "TTrades does not define it as a universal important-POI selector."
        ),
        "all_source_author_poi_signatures_present": False,
        "source_complete_entries": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "verdict": "INTRADAY_PHYSICAL_CONTEXT_ONLY_POI_RELEVANCE_D",
    }
