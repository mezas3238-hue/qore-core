"""B R22: source-only competing-POI physical review join (R18+R19+R21).

R18: native M3/M15 H1 lows and three-H1 FVG candidates as of C2/CISD.
R19: fixed SHA-rank, PnL-blind 107 dual-review packets.
R21: independently reconstructed NY day-to-date low context before C2.
Keep ALL 2657 source precursor case IDs; never infer author POI significance.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from qore.infrastructure.trader_lab.vt08_b_r18_pre_cisd_h1_poi_native_timing_v1 import (
    SCHEMA as R18_SCHEMA,
    digest as digest_r18,
)
from qore.infrastructure.trader_lab.vt08_b_r19_blind_dual_rater_poi_queue_v1 import (
    MARKET_EXPECTED,
    SCHEMA as R19_SCHEMA,
    SEED,
    _category,
    digest as digest_r19,
)
from qore.infrastructure.trader_lab.vt08_b_r21_intraday_low_source_context_v1 import (
    LABEL_GAP,
    LABEL_NO,
    LABEL_YES,
)

SCHEMA = "qore.vt08.b.r22.multi_poi_conflict_review.v1"
R21_SCHEMA = "qore.vt08.b.r21.day_low_context_diagnostic.v1"
R19_REPORT_DIGEST = {
    "EURJPY": "f553e6f8da86d7af30ce1f811257b0d05b892d03ee4d60d046d1f10bb65c5b7c",
    "USDCHF": "87d43288eecddce84c1fcc99578558cb03f1be69dbf5d438766582fbd8e14bc4",
    "NZDUSD": "cbba1ff00d19608968ed58c48b7eb5fdfd038e5187ab738b4710ae0b91e26e56",
    "CADJPY": "b16f7ffe78892c5eb53d2ecf33c2057e7a70e70140e2b1fd1e2ddd3673486e32",
    "USDCAD": "a5ed7db7cb965db87ffb949ea0644d24199114895fd3b3da3529c870781c01f9",
}
PRE = "TOUCHED_BEFORE_CISD_BAR"
SAME = "TOUCHED_IN_CISD_BAR_SEQUENCE_UNKNOWN"
GAP_H1 = "UPSTREAM_H1_SOURCE_GAP"
DAY_LABELS = (LABEL_YES, LABEL_NO, LABEL_GAP)


def _instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("R22 source time string required")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("R22 source time invalid") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("R22 source time must be aware")
    return dt.astimezone(UTC)


def _money(value: object) -> Decimal:
    try:
        x = Decimal(value) if isinstance(value, str) else Decimal("NaN")
    except InvalidOperation as exc:
        raise ValueError("R22 invalid price") from exc
    if not x.is_finite() or x <= 0:
        raise ValueError("R22 nonfinite/nonpositive price")
    return x


def _check_touch(
    witness: dict[str, object], *, cisd: datetime, c2: datetime,
) -> bool:
    phase = witness.get("first_touch_phase")
    opened = witness.get("first_touch_bar_opened_at_utc")
    bid = witness.get("first_touch_m3_source_bar_id")
    if phase == "NOT_TOUCHED_DURING_C2":
        if opened is not None or bid is not None:
            raise ValueError("R22 false missing touch evidence")
        return False
    if phase not in (
        PRE, SAME, "TOUCHED_AFTER_CISD_CLOSE",
    ) or not isinstance(bid, str) or len(bid) != 64:
        raise ValueError("R22 first-touch phase/ID forged")
    start = _instant(opened)
    if not (c2 <= start < c2 + timedelta(minutes=30)):
        raise ValueError("R22 first touch outside C2 interval")
    actual_phase = (
        PRE if start + timedelta(minutes=3) < cisd
        else SAME if start + timedelta(minutes=3) == cisd
        else "TOUCHED_AFTER_CISD_CLOSE"
    )
    if phase != actual_phase:
        raise ValueError("R22 first-touch timing phase drift")
    return phase == PRE


def join_competing_poi_contexts(
    r18: dict[str, object], r19: dict[str, object], r21: dict[str, object], *,
    market: str,
) -> dict[str, object]:
    """Verify all A/B pre-PnL diagnostic witnesses and competing POI counts.

    A conflict is a physical multi-candidate ambiguity, NOT an author veto,
    setup exclusion, or an input to economic evaluation.
    """
    if market not in MARKET_EXPECTED:
        raise ValueError("R22 unsupported VT08 market")
    n, pinned_r18 = MARKET_EXPECTED[market]
    if (
        r18.get("schema") != R18_SCHEMA or r18.get("market") != market
        or digest_r18(r18) != pinned_r18
        or r18.get("original_source_cases") != n
        or r18.get("owner_scope") != "VT08_CURRENT_ONLY_NO_QORE_ALPHA"
        or r18.get("source_complete_entries") != 0
        or r18.get("cognitive_admissions") != 0
        or r18.get("broker_fills") != 0
        or r18.get("profit_factor") is not None
    ):
        raise ValueError("R22 R18 original source SHA/owner/authority changed")
    if (
        r19.get("schema") != R19_SCHEMA or r19.get("market") != market
        or digest_r19(r19) != R19_REPORT_DIGEST[market]
        or r19.get("seed") != SEED
        or r19.get("original_r18_sha256") != pinned_r18
        or r19.get("original_r18_cases") != n
        or r19.get("selection_without_pnl") is not True
        or r19.get("review_sample_not_a_trading_cohort") is not True
        or r19.get("rater_A_signed") != 0
        or r19.get("rater_B_signed") != 0
        or r19.get("source_complete_entries") != 0
        or r19.get("cognitive_admissions") != 0
        or r19.get("broker_fills") != 0
    ):
        raise ValueError("R22 dual-review source seed/sha/approval forged")
    if (
        r21.get("schema") != R21_SCHEMA or r21.get("market") != market
        or r21.get("all_case_count") != n
        or r21.get("r20_universe_count") != n
        or r21.get("original_raw_m3_sha256") != r18.get("original_m3_sha256")
        or r21.get("all_source_author_poi_signatures_present") is not False
        or r21.get("source_complete_entries") != 0
        or r21.get("cognitive_admissions") != 0
        or r21.get("broker_fills") != 0
        or r21.get("economic_gates_evaluated") is not False
        or r21.get("holdout_7y_accessed") is not False
        or r21.get("sizing_used") is not False
    ):
        raise ValueError("R22 R21 original feed/authority mismatch")
    cases = r18.get("all_pre_cisd_h1_poi_source_witnesses")
    dayrows = r21.get("full_day_context_index")
    packets = r19.get("review_packets")
    if (
        not isinstance(cases, list) or len(cases) != n
        or not isinstance(dayrows, list) or len(dayrows) != n
        or not isinstance(packets, list)
        or len(packets) != r19.get("selected_source_only_cases")
    ):
        raise ValueError("R22 missing original full census or 107 review packet identities")
    indexed_days: dict[str, dict[str, object]] = {}
    for day in dayrows:
        if not isinstance(day, dict) or day.get("market") != market:
            raise ValueError("R22 cross-market NY day history")
        cid = day.get("case_id_sha256")
        if not isinstance(cid, str) or cid in indexed_days:
            raise ValueError("R22 duplicate day context ID")
        if day.get("day_low_source_diagnostic") not in DAY_LABELS:
            raise ValueError("R22 invalid NY day physical class")
        if day.get("important_level_ttrades_author_confirmed") is not False:
            raise ValueError("R22 day low proxy fraudulently author approved")
        indexed_days[cid] = day
    if Counter(x["day_low_source_diagnostic"] for x in dayrows) != Counter({
        k: r21.get("day_low_category_counts", {}).get(k, 0) for k in DAY_LABELS
    }):
        raise ValueError("R22 R21 original day-category conservation drift")
    all_index: dict[str, dict[str, object]] = {}
    joint: Counter[str] = Counter()
    low_mult: Counter[str] = Counter()
    for case in cases:
        if not isinstance(case, dict) or case.get("market") != market:
            raise ValueError("R22 invalid R18 source case market")
        cid = case.get("case_id_sha256")
        if not isinstance(cid, str) or cid in all_index:
            raise ValueError("R22 duplicate H1 case ID")
        day = indexed_days.pop(cid, None)
        if day is None:
            raise ValueError("R22 unmatched R18/R21 source case")
        c2 = _instant(case.get("c2_opened_at_utc"))
        c3 = _instant(case.get("c3_opened_at_utc"))
        cisd = _instant(case.get("cisd_closed_at_utc"))
        if not (c2 < cisd <= c3 and c3 == c2 + timedelta(minutes=30)):
            raise ValueError("R22 invalid as-of clocks")
        if (
            _instant(day.get("c2_opened_at_utc")) != c2
            or _instant(day.get("C3_decision_at_utc")) != c3
            or day.get("cognitive_admission") is not False
        ):
            raise ValueError("R22 R18/R21 event chronology changed")
        if (
            case.get("author_source_complete") is not False
            or case.get("author_poi_significant_and_selected") is not False
            or case.get("cognitive_admission") is not False
        ):
            raise ValueError("R22 false H1 POI source approval")
        status = case.get("upstream_h1_status")
        lows = case.get("pre_existing_h1_low_candidates")
        if not isinstance(lows, list) or (status == GAP_H1) != (len(lows) == 0):
            raise ValueError("R22 missing/contradictory three H1 context")
        if status not in (GAP_H1, "THREE_PRIOR_H1_CLOSED"):
            raise ValueError("R22 original H1 status invalid")
        if status != GAP_H1 and len(lows) != 3:
            raise ValueError("R22 three H1 lows required")
        pre_lows = []
        for level in lows:
            if not isinstance(level, dict):
                raise ValueError("R22 invalid H1 low candidate")
            if _instant(level.get("available_at_utc")) > c2 or (
                level.get("author_relevant_low_adjudicated") is not False
            ):
                raise ValueError("R22 future or author-forged H1 low")
            _money(level.get("level"))
            if _check_touch(level, cisd=cisd, c2=c2):
                pre_lows.append(level)
        fvg = case.get("pre_existing_h1_fvg_candidate")
        pre_fvg = False
        fvg_type = "NONE"
        if fvg is not None:
            if not isinstance(fvg, dict) or fvg.get("author_significant_poi") is not False:
                raise ValueError("R22 false FVG source relevance")
            if _instant(fvg.get("available_at_utc")) > c2:
                raise ValueError("R22 future H1 FVG")
            lo, hi = _money(fvg.get("lower")), _money(fvg.get("upper"))
            if lo >= hi:
                raise ValueError("R22 invalid H1 FVG bounds")
            fvg_type = str(fvg.get("type"))
            if fvg_type not in (
                "BULLISH_H1_3BAR_FVG_GEOMETRY", "BEARISH_H1_3BAR_FVG_GEOMETRY"
            ):
                raise ValueError("R22 invalid FVG direction")
            pre_fvg = _check_touch(fvg, cisd=cisd, c2=c2)
        cat = day["day_low_source_diagnostic"]
        c1 = _money(day.get("c1_low"))
        c2low = _money(day.get("c2_low"))
        if c2low >= c1:
            raise ValueError("R22 C1.low was not swept in original day record")
        raw_ny_low = day.get("ny_midnight_to_c2_prior_low")
        if cat == LABEL_GAP:
            if day.get("day_context_complete") is not False or raw_ny_low is not None:
                raise ValueError("R22 NY source gap cannot be assigned price")
        else:
            if day.get("day_context_complete") is not True:
                raise ValueError("R22 NY complete context mismatch")
            dlow = _money(raw_ny_low)
            should_sweep = c2low < dlow
            if should_sweep != (cat == LABEL_YES):
                raise ValueError("R22 NY physical low diagnostic falsified")
        count_pre = len(pre_lows)
        if count_pre > 3:
            raise ValueError("R22 invalid low POI cardinality")
        # Co-observed levels are competing contextual candidates, not
        # necessarily distinct POIs; duplicate lows count as bars, not prices.
        day_bucket = {
            LABEL_YES: "NY_LOW_SWEPT",
            LABEL_NO: "NY_LOW_NOT_SWEPT",
            LABEL_GAP: "NY_LOW_CONTEXT_MISSING",
        }[cat]
        fvg_bucket = (
            "BULL_FVG_PRE" if pre_fvg and fvg_type.startswith("BULLISH")
            else "BEAR_FVG_PRE" if pre_fvg else "NO_FVG_PRE"
        )
        key = fvg_bucket + "__" + day_bucket
        joint[key] += 1
        low_mult[str(count_pre)] += 1
        all_index[cid] = {
            "case_id_sha256": cid,
            "market": market,
            "decision_at_utc": c3.isoformat(),
            "r18_fvg_type": fvg_type,
            "h1_fvg_touched_before_cisd_bar": pre_fvg,
            "h1_lows_touched_before_cisd_bar": count_pre,
            "h1_low_source_bar_id_groups": [
                x["raw_m15_bar_ids"] for x in pre_lows
            ],
            "pre_cisd_fvg_source_bar_ids": (
                fvg.get("source_bar_ids") if pre_fvg else None
            ),
            "ny_day_low_context": cat,
            "source_context_cross_category": key,
            "relevance_and_poi_selection_adjudicated": False,
            "two_independent_raters_signed": False,
            "cognitive_source_ready": False,
        }
    if indexed_days or len(all_index) != n:
        raise ValueError("R22 missing source case from complete join")
    selected = []
    selected_ids = set()
    for packet in packets:
        if not isinstance(packet, dict) or packet.get("market") != market:
            raise ValueError("R22 blind review packet market drift")
        cid = packet.get("case_id_sha256")
        base = all_index.get(cid)
        if base is None or cid in selected_ids:
            raise ValueError("R22 missing/duplicated blind sample")
        selected_ids.add(cid)
        if (
            packet.get("selection_seed") != SEED
            or packet.get("human_rater_A_source_signoff") is not None
            or packet.get("human_rater_B_independent_signoff") is not None
            or packet.get("source_complete") is not False
            or packet.get("cognitive_ready") is not False
            or packet.get("orders_authorized") is not False
        ):
            raise ValueError("R22 false independent review or trade authorisation")
        matched = next(x for x in cases if x["case_id_sha256"] == cid)
        if _category(matched) != packet.get("category"):
            raise ValueError("R22 original blinded POI stratum changed")
        if (
            _instant(packet.get("c2_opened_at_utc")) != _instant(matched["c2_opened_at_utc"])
            or _instant(packet.get("cisd_closed_at_utc")) != _instant(
                matched["cisd_closed_at_utc"]
            )
            or _instant(packet.get("c3_opened_at_utc")) != _instant(
                matched["c3_opened_at_utc"]
            )
        ):
            raise ValueError("R22 blind sample clock changed")
        selected.append({
            **packet,
            "R22_independent_physical_context": base,
            "primary_source_relevant_swing_ref": None,
            "primary_source_important_poi_ref": None,
            "rater_A_verified": False,
            "rater_B_verified": False,
            "eligible_for_pnl": False,
        })
    if len(selected) != r19.get("selected_source_only_cases"):
        raise ValueError("R22 lost preregistered blind sample")
    srccounts = r18.get("counts")
    if not isinstance(srccounts, dict) or srccounts.get(
        "cases_h1_prior_low_touched_before_cisd_bar"
    ) != n - low_mult["0"]:
        raise ValueError("R22 R18 H1-low coverage tally mismatch")
    if srccounts.get("cases_source_only") != n or sum(joint.values()) != n:
        raise ValueError("R22 original physical census drift")
    expected_bull = srccounts.get(
        "fvg_BULLISH_H1_3BAR_FVG_GEOMETRY_TOUCHED_BEFORE_CISD_BAR", 0
    )
    expected_bear = srccounts.get(
        "fvg_BEARISH_H1_3BAR_FVG_GEOMETRY_TOUCHED_BEFORE_CISD_BAR", 0
    )
    if (
        sum(v for k, v in joint.items() if k.startswith("BULL_FVG_PRE")) != expected_bull
        or sum(v for k, v in joint.items() if k.startswith("BEAR_FVG_PRE")) != expected_bear
    ):
        raise ValueError("R22 R18 FVG source counts changed")
    return {
        "schema": SCHEMA,
        "market": market,
        "frozen_original_r18_digest": pinned_r18,
        "frozen_original_r19_digest": R19_REPORT_DIGEST[market],
        "original_r21_m3_source_sha": r21["original_raw_m3_sha256"],
        "all_original_case_count": n,
        "crossed_fvg_vs_ny_day_low_counts": dict(sorted(joint.items())),
        "count_h1_lows_touched_before_cisd_histogram": dict(sorted(low_mult.items())),
        "r19_blind_packets_enriched": len(selected),
        "dual_source_human_reviews_completed": 0,
        "source_author_complete": 0,
        "cognitive_admissions": 0,
        "broker_fills": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "entire_original_census": [all_index[i] for i in sorted(all_index)],
        "blind_rater_dossiers": selected,
        "verdict": "MULTI_POI_PHYSICAL_DIAGNOSTIC_ONLY_ALL_AUTHOR_SELECTION_D",
    }
