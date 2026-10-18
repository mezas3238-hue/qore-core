"""B R24 native M3 falsification: did original PS proxy survive until C3?

A selected exactly one M3 bearish-series→bullish-CISD shape. B R14 verifies
that geometry and the originating run-low from the source. R24 checks the
unselected LATER M3 bars of the SAME M30 C2: a lower low AFTER CISD
contradicts persistence of that original provisional swing at C3. Touch/low
inside the confirming M3 bar cannot be tick-ordered and is always UNKNOWN.

This is a falsification of the ORIGINAL proxy, not an author-validated PS
rule, not automatic rejection of other valid setups, and not a trade.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from qore.infrastructure.trader_lab.vt08_5m_b_independent_raw_receipts_v1 import (
    _instant,
    _raw_bars,
    _verify_bar,
)
from qore.infrastructure.trader_lab.vt08_b_r14_opposing_series_native_cisd_v1 import (
    audit_m3_opposing_series,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    MARKET_EXPECTED,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    digest as digest_r19,
)
from qore.infrastructure.trader_lab.vt08_b_r23_signed_semantic_review_contract_v1 import (
    PINNED_R19_REPORT_DIGESTS,
)

M3 = timedelta(minutes=3)
M30 = timedelta(minutes=30)
SCHEMA = "qore.vt08.b.r24.post_cisd_original_ps_proxy_survival.v1"
SOURCE = "https://ttrades.com/ttrades-ideal-formation-high-probability-swing-points/"


def classify_post_cisd_original_ps(
    bars: list[tuple[Decimal, Decimal, Decimal, Decimal]],
    *,
    proxy_low: Decimal,
    cisd_closed_m3_index: int,
) -> dict[str, object]:
    """Scan ONLY source bars as-of C3; CISD bar is intrabar-unknown."""
    if (
        len(bars) != 10 or not 1 <= cisd_closed_m3_index <= 10
        or proxy_low <= 0
        or any(not isinstance(x, Decimal) or not x.is_finite() for bar in bars for x in bar)
    ):
        raise ValueError("R24 invalid original C2 M3 evidence")
    if any(
        low <= 0 or high < max(op, close) or low > min(op, close)
        for op, high, low, close in bars
    ):
        raise ValueError("R24 original M3 OHLC inconsistent")
    confirm = bars[cisd_closed_m3_index-1]
    subsequent = bars[cisd_closed_m3_index:]
    if subsequent and min(x[2] for x in subsequent) < proxy_low:
        phase = "ORIGINAL_PS_PROXY_LOW_BROKEN_AFTER_CISD_BEFORE_C3"
    elif subsequent and any(x[2] == proxy_low for x in subsequent):
        phase = "PS_PROXY_LOW_RETOUCHED_AFTER_CISD"
    elif subsequent:
        phase = "NO_POST_CISD_LOWER_LOW_OBSERVED"
    else:
        phase = "CISD_AT_C2_CLOSE_NO_LATER_M3"
    return {
        "post_cisd_original_ps_proxy_state": phase,
        "cisd_m3_confirmation_bar_low_below_proxy": confirm[2] < proxy_low,
        "cisd_m3_confirmation_bar_touches_proxy": confirm[2] <= proxy_low,
        "cisd_bar_intrabar_sequence_proven": False,
        "post_cisd_m3_count": len(subsequent),
        "new_author_ps_reestablished": "D_NOT_ASSESSED",
    }


def audit_original_ps_proxy_survival(
    frozen: dict[str, object], blind: dict[str, object],
    *, market: str, native_m3: Path,
) -> dict[str, object]:
    """All physically frozen precursors, exact 107 blind-sample coverage."""
    if market not in MARKET_EXPECTED:
        raise ValueError("R24 market outside VT08")
    expected, digest18 = MARKET_EXPECTED[market]
    r19sha = PINNED_R19_REPORT_DIGESTS[market]
    if (
        blind.get("market") != market or digest_r19(blind) != r19sha
        or blind.get("original_r18_sha256") != digest18
        or blind.get("original_r18_cases") != expected
        or blind.get("rater_A_signed") != 0 or blind.get("rater_B_signed") != 0
        or blind.get("source_complete_entries") != 0
        or blind.get("cognitive_admissions") != 0
        or blind.get("broker_fills") != 0
        or blind.get("holdout_7y_accessed") is not False
        or blind.get("sizing_used") is not False
    ):
        raise ValueError("R24 original outcome-blind source digest/authority changed")
    verified = audit_m3_opposing_series(
        frozen, market=market, native_m3=native_m3,
    )
    sha, raw = _raw_bars(native_m3, "M3", market)
    if (
        verified.get("native_m3_sha256") != sha
        or verified.get("frozen_source_cases") != expected
        or blind.get("original_r18_cases") != expected
    ):
        raise ValueError("R24 original raw M3 custody/census changed")
    firstfail = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
    cases = frozen["examples_by_stage"][firstfail]
    source_by_id = {
        x["case_id_sha256"]: x for x in verified["all_source_only_witnesses"]
    }
    if len(cases) != expected or len(source_by_id) != expected:
        raise ValueError("R24 native M3 case count/case IDs drift")
    bucket: Counter[str] = Counter()
    confirming: Counter[str] = Counter()
    entire = []
    index = {}
    for case in cases:
        if case.get("market") != market:
            raise ValueError("R24 foreign M3 source event")
        c2 = _instant(case["c2_opened_at_utc"])
        c3 = _instant(case["decision_at_utc"])
        if c3 != c2+M30:
            raise ValueError("R24 C2/C3 source clocks drift")
        cid = hashlib.sha256(
            f"{market}|{c2.isoformat()}|{c3.isoformat()}".encode(),
        ).hexdigest()
        proxy = source_by_id.pop(cid, None)
        if proxy is None or cid in index:
            raise ValueError("R24 lost/colliding original R14 source ID")
        confirm_at = _instant(proxy["cisd_proxy_confirmed_at_utc"])
        minutes = (confirm_at-c2).total_seconds()/60
        if minutes % 3 or not 3 <= minutes <= 30:
            raise ValueError("R24 CISD not a native source M3 closing time")
        cisd_i = int(minutes//3)
        prices = []
        for i, rec in enumerate(case["c2_m3_raw_bar_receipts"]):
            prices.append(_verify_bar(
                rec, expected_open=c2+i*M3, minutes=3,
                profile="M3", source_sha=sha, raw=raw,
            ))
        ps_low = Decimal(proxy["ps_low_proxy"])
        if not any(
            x[2] == ps_low for x in prices[:cisd_i-1]
        ):
            raise ValueError("R24 PS proxy was NOT created before CISD confirming M3")
        physical = classify_post_cisd_original_ps(
            prices, proxy_low=ps_low, cisd_closed_m3_index=cisd_i,
        )
        after_ids = [
            rec["source_bar_id"]
            for rec in case["c2_m3_raw_bar_receipts"][cisd_i:]
        ]
        if len(after_ids) != physical["post_cisd_m3_count"]:
            raise ValueError("R24 post-CISD source bar IDs absent")
        cls = str(physical["post_cisd_original_ps_proxy_state"])
        bucket[cls] += 1
        confirming["CISD_M3_BAR_MADE_NEW_LOW_VS_RUN"] += int(
            physical["cisd_m3_confirmation_bar_low_below_proxy"]
        )
        confirming["CISD_M3_BAR_TOUCHED_RUN_LOW"] += int(
            physical["cisd_m3_confirmation_bar_touches_proxy"]
        )
        record = {
            "market": market, "case_id_sha256": cid,
            "c2_opened_at_utc": c2.isoformat(),
            "c3_decision_at_utc": c3.isoformat(),
            "cisd_observed_at_utc": confirm_at.isoformat(),
            "original_opposing_series_low_proxy": str(ps_low),
            "first_cisd_m3_bar_id": (
                case["c2_m3_raw_bar_receipts"][cisd_i-1]["source_bar_id"]
            ),
            "post_cisd_m3_source_bar_ids": after_ids,
            **physical,
            "author_selected_poi": False,
            "author_protected_swing_validated": False,
            "cognitive_admission": False,
        }
        index[cid] = record
        entire.append(record)
    if source_by_id or len(entire) != expected or sum(bucket.values()) != expected:
        raise ValueError("R24 original source denominator not conserved")
    selected = blind.get("review_packets")
    if not isinstance(selected, list) or len(selected) != blind.get(
        "selected_source_only_cases"
    ):
        raise ValueError("R24 blind R19 sample corruption")
    seen = set()
    review = []
    for pkt in selected:
        cid = pkt.get("case_id_sha256")
        if cid in seen or cid not in index or pkt.get("market") != market:
            raise ValueError("R24 selected source IDs altered/duplicated")
        if (
            pkt.get("human_rater_A_source_signoff") is not None
            or pkt.get("human_rater_B_independent_signoff") is not None
            or pkt.get("source_complete") is not False
            or pkt.get("orders_authorized") is not False
        ):
            raise ValueError("R24 false actual review or trading authorization")
        seen.add(cid)
        review.append({
            "selected_category": pkt["category"],
            "source_sample_original_seed_rank_sha256": pkt["selection_rank_sha256"],
            **index[cid],
            "A_author_source_decision": None,
            "B_independent_source_decision": None,
        })
    return {
        "schema": SCHEMA, "market": market,
        "source_native_m3_sha256": sha,
        "frozen_original_r19_sha256": r19sha,
        "original_frozen_case_count": len(entire),
        "post_cisd_ps_proxy_state_counts": dict(sorted(bucket.items())),
        "cisd_bar_proxy_low_context_counts": dict(sorted(confirming.items())),
        "blind_review_107_sample_cases": len(review),
        "full_original_physical_index": sorted(entire, key=lambda x: x["case_id_sha256"]),
        "same_107_blind_review_with_post_cisd_causality": review,
        "source_author_article": SOURCE,
        "interpretation": (
            "A later lower low falsifies persistence of the original provisional "
            "M3 swing origin at C3; it does NOT prove no other swing/POI exists."
        ),
        "source_complete_author_entries": 0,
        "real_cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "verdict": "PHYSICAL_PS_PROXY_SURVIVAL_DIAGNOSTIC_NOT_TTRADES_CERTIFICATION",
    }
