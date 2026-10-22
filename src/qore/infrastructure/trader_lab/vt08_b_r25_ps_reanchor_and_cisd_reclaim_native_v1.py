"""VT08 B R25: original protected-low reanchor and post-CISD level reclaim.

This tests a *physical negative claim*, not a self-selected replacement PS:
if an origin PS-low has been exceeded before the C3 decision, R14's stale
origin price cannot be presented as a protected intact low. R25 rechecks
the authentic cTrader M3 bars and measures whether the original CISD
closure level is reclaimed after a *new* low, without guessing a fresh
CISD, important POI, intrabar tick path or TTrades stop/target.

The universe was selected by UNIQUE initial R14 M3 CISD shape, so do NOT
naively treat absence of a second R14 CISD as out-of-sample evidence.
"""
from __future__ import annotations

import hashlib
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
from qore.infrastructure.trader_lab.vt08_b_r24_protected_swing_post_cisd_invalidation_v1 import (
    classify_post_cisd_original_ps,
)

M3 = timedelta(minutes=3)
M30 = timedelta(minutes=30)
SCHEMA = "qore.vt08.b.r25.original_ps_reanchor_and_old_cisd_level_reclaim.v1"
AUTHOR_URL = "https://ttrades.com/protected-swings-understanding-trends-and-invalidations/"
RECLAIM_SAME = "NEW_LOW_M3_CLOSE_RECLAIMS_OLD_CISD_LEVEL"
RECLAIM_LATER = "LATER_M3_CLOSE_RECLAIMS_OLD_CISD_LEVEL"
RECLAIM_ABSENT = "NO_CLOSED_M3_RECLAIM_OF_OLD_CISD_LEVEL_BEFORE_C3"
RECLAIM_NA = "NO_POST_CISD_NEW_LOW_BELOW_CISD_ANCHOR"
RECLAIM_CLASSES = (RECLAIM_SAME, RECLAIM_LATER, RECLAIM_ABSENT, RECLAIM_NA)


def classify_reanchored_low_and_reclaim(
    prices: list[tuple[Decimal, Decimal, Decimal, Decimal]], *,
    cisd_i: int, original_low: Decimal, prior_cisd_level: Decimal,
) -> dict[str, object]:
    """0-based first post-break time; all bars closed within C2 as of C3."""
    if len(prices) != 10 or not 1 <= cisd_i <= 10:
        raise ValueError("R25 original M30 requires ten M3 and valid CISD index")
    if original_low <= 0 or prior_cisd_level <= original_low:
        raise ValueError("R25 invalid source-verified original low/level")
    for op, high, low, close in prices:
        if not all(v.is_finite() and v > 0 for v in (op, high, low, close)):
            raise ValueError("R25 nonfinite/negative native source M3")
        if low > min(op, close) or high < max(op, close):
            raise ValueError("R25 ill-formed original source OHLC")
    confirming = prices[cisd_i-1]
    anchor = min(original_low, confirming[2])
    remaining = prices[cisd_i:]
    orig = classify_post_cisd_original_ps(
        prices, proxy_low=original_low, cisd_closed_m3_index=cisd_i,
    )
    broken_offset = next(
        (i for i, row in enumerate(remaining) if row[2] < anchor), None,
    )
    if broken_offset is None:
        cls = RECLAIM_NA
        recovered_at = None
    elif remaining[broken_offset][3] > prior_cisd_level:
        cls = RECLAIM_SAME
        recovered_at = cisd_i+broken_offset
    else:
        found = next(
            (i for i in range(broken_offset+1, len(remaining))
             if remaining[i][3] > prior_cisd_level),
            None,
        )
        cls = RECLAIM_LATER if found is not None else RECLAIM_ABSENT
        recovered_at = cisd_i+found if found is not None else None
    return {
        "original_run_low": str(original_low),
        "cisd_confirming_bar_low": str(confirming[2]),
        "reanchored_as_of_cisd_closed_low": str(anchor),
        "confirming_bar_reanchors_original_run_low": anchor < original_low,
        "post_cisd_lower_than_reanchored_low": broken_offset is not None,
        "first_post_cisd_break_reanchored_index": (
            cisd_i+broken_offset if broken_offset is not None else None
        ),
        "original_low_broken_after_cisd": (
            orig["first_post_cisd_break_m3_index"] is not None
        ),
        "post_break_old_cisd_level_reclaim": cls,
        "first_post_break_reclaim_m3_index": recovered_at,
        "reclaim_of_old_level_is_new_cisd": False,
        "authentic_reformed_protected_swing": "D_NOT_ASSESSED",
        "source_author_complete": False,
    }


def audit_r25(
    frozen: dict[str, object], blind: dict[str, object], *,
    market: str, native_m3: Path,
) -> dict[str, object]:
    """Attest entire 2657 native source census + exact pre-PnL 107 samples."""
    if market not in MARKET_EXPECTED:
        raise ValueError("R25 unauthorized market")
    n, r18sha = MARKET_EXPECTED[market]
    r19sha = PINNED_R19_REPORT_DIGESTS[market]
    if (
        blind.get("market") != market or digest_r19(blind) != r19sha
        or blind.get("original_r18_sha256") != r18sha
        or blind.get("original_r18_cases") != n
        or blind.get("rater_A_signed") != 0 or blind.get("rater_B_signed") != 0
        or blind.get("source_complete_entries") != 0
        or blind.get("cognitive_admissions") != 0
        or blind.get("broker_fills") != 0
        or blind.get("holdout_7y_accessed") is not False
        or blind.get("sizing_used") is not False
    ):
        raise ValueError("R25 immutable R19 original sample/cognitive authority changed")
    verified = audit_m3_opposing_series(
        frozen, market=market, native_m3=native_m3,
    )
    sha, raw = _raw_bars(native_m3, "M3", market)
    if verified.get("native_m3_sha256") != sha or verified.get("frozen_source_cases") != n:
        raise ValueError("R25 native raw M3 SHA/reconstructed R14 drift")
    old_by_id = {
        x["case_id_sha256"]: x for x in verified["all_source_only_witnesses"]
    }
    firstfail = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
    cases = frozen["examples_by_stage"][firstfail]
    if len(cases) != n or len(old_by_id) != n:
        raise ValueError("R25 original M3 universe changed")
    all_index = {}
    classes: Counter[str] = Counter()
    flags: Counter[str] = Counter()
    for case in cases:
        if case.get("market") != market:
            raise ValueError("R25 cross-market original source case")
        c2 = _instant(case["c2_opened_at_utc"])
        c3 = _instant(case["decision_at_utc"])
        if c3 != c2+M30:
            raise ValueError("R25 invalid M30 C3 as-of window")
        cid = hashlib.sha256(
            f"{market}|{c2.isoformat()}|{c3.isoformat()}".encode()
        ).hexdigest()
        prior = old_by_id.pop(cid, None)
        if prior is None or cid in all_index:
            raise ValueError("R25 original independent R14 case ID missing")
        cisd = _instant(prior["cisd_proxy_confirmed_at_utc"])
        start = _instant(prior["opposing_series_opened_at_utc"])
        if (
            cisd <= c2 or cisd > c3 or (cisd-c2) % M3
            or not c2 <= start < cisd or (start-c2) % M3
        ):
            raise ValueError("R25 malformed original source opposing series clocks")
        cisd_i = int((cisd-c2)//M3)
        run_i = int((start-c2)//M3)
        receipts = case["c2_m3_raw_bar_receipts"]
        if not isinstance(receipts, list) or len(receipts) != 10:
            raise ValueError("R25 missing signed ten original source M3 receipts")
        prices = [
            _verify_bar(
                rec, expected_open=c2+i*M3, minutes=3,
                profile="M3", source_sha=sha, raw=raw,
            ) for i, rec in enumerate(receipts)
        ]
        prior_level = Decimal(prior["cisd_level_proxy"])
        old_low = Decimal(prior["ps_low_proxy"])
        if prices[run_i][0] != prior_level or (
            min(row[2] for row in prices[run_i:cisd_i-1]) != old_low
        ) or any(row[3] >= row[0] for row in prices[run_i:cisd_i-1]):
            raise ValueError("R25 false original M3 opposing run/PS low/level")
        if prices[cisd_i-1][3] <= prior_level:
            raise ValueError("R25 original bullish CISD not closed above run")
        state = classify_reanchored_low_and_reclaim(
            prices, cisd_i=cisd_i, original_low=old_low,
            prior_cisd_level=prior_level,
        )
        category = state["post_break_old_cisd_level_reclaim"]
        classes[str(category)] += 1
        flags["CISD_CONFIRM_BAR_REANCHOR_OLD_LOW"] += int(
            state["confirming_bar_reanchors_original_run_low"]
        )
        flags["POST_CISD_BREACH_REANCHORED_LOW"] += int(
            state["post_cisd_lower_than_reanchored_low"]
        )
        flags["OLD_RUN_LOW_BREACHED_AFTER_CISD"] += int(
            state["original_low_broken_after_cisd"]
        )
        flags["OLD_RUN_LOW_NEEDS_ANY_REANCHOR"] += int(
            state["confirming_bar_reanchors_original_run_low"]
            or state["original_low_broken_after_cisd"]
        )
        broken = state["first_post_cisd_break_reanchored_index"]
        rec_ix = state["first_post_break_reclaim_m3_index"]
        all_index[cid] = {
            "market": market, "case_id_sha256": cid,
            "c2_opened_at_utc": c2.isoformat(),
            "c3_decision_at_utc": c3.isoformat(),
            "first_cisd_closed_at_utc": cisd.isoformat(),
            "opposing_series_source_bar_ids": [
                x["source_bar_id"] for x in receipts[run_i:cisd_i-1]
            ],
            "first_cisd_source_bar_id": receipts[cisd_i-1]["source_bar_id"],
            "old_cisd_bullish_breakout_level": str(prior_level),
            "first_new_low_after_reanchor_bar_id": (
                receipts[broken]["source_bar_id"] if broken is not None else None
            ),
            "first_new_low_after_reanchor_closed_at_utc": (
                (c2+(broken+1)*M3).isoformat() if broken is not None else None
            ),
            "first_close_reclaiming_old_level_source_bar_id": (
                receipts[rec_ix]["source_bar_id"] if rec_ix is not None else None
            ),
            "first_close_reclaiming_old_level_available_at_utc": (
                (c2+(rec_ix+1)*M3).isoformat() if rec_ix is not None else None
            ),
            **state,
            "author_validated_poi": False,
            "author_validated_protected_swing": False,
            "A_signed_review": None,
            "B_signed_review": None,
            "cognitive_admission": False,
        }
    if old_by_id or len(all_index) != n or sum(classes.values()) != n:
        raise ValueError("R25 physical source/candidate denominator drift")
    selected = blind.get("review_packets")
    if not isinstance(selected, list) or len(selected) != blind.get(
        "selected_source_only_cases"
    ):
        raise ValueError("R25 missing preregistered R19 review packet sample")
    seen: set[str] = set()
    reviewed = []
    for item in selected:
        if not isinstance(item, dict):
            raise ValueError("R25 malformed blind review packet")
        cid = item.get("case_id_sha256")
        if cid not in all_index or cid in seen or item.get("market") != market:
            raise ValueError("R25 reviewer case ID changed")
        if (
            item.get("human_rater_A_source_signoff") is not None
            or item.get("human_rater_B_independent_signoff") is not None
            or item.get("source_complete") is not False
            or item.get("cognitive_ready") is not False
            or item.get("orders_authorized") is not False
        ):
            raise ValueError("R25 fake reviewer signoff or trade authority")
        seen.add(cid)
        reviewed.append({
            "original_category": item["category"],
            "selection_rank_sha256": item["selection_rank_sha256"],
            **all_index[cid],
        })
    return {
        "schema": SCHEMA, "market": market,
        "source_native_m3_sha256": sha,
        "original_blind_r19_report_sha256": r19sha,
        "original_candidate_census": n,
        "original_r19_source_review_cases": len(reviewed),
        "post_break_old_level_reclaim_histogram": dict(sorted(classes.items())),
        "source_old_vs_reanchored_low_counts": dict(sorted(flags.items())),
        "full_source_case_index": [all_index[i] for i in sorted(all_index)],
        "same_107_r19_blind_source_review": reviewed,
        "primary_author_source": AUTHOR_URL,
        "reanchored_low_author_validated": False,
        "source_complete_entries": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "verdict": "R25_PHYSICAL_REANCHOR_AND_CLOSED_BAR_RECLAIM_ONLY_TTRADES_D",
    }
