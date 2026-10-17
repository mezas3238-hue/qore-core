"""B R19: reproducible blind human-review packets from frozen A R3 + A R7.

This exports PRE-OUTCOME physical price/bar receipts for qualitative TTrades
adjudication. Never fabricates rater answers or upgrades a shape to a setup.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from typing import Final

from qore.infrastructure.trader_lab.vt08_b_r10_blind_cognitive_admission_inventory_v1 import (
    CLASSES,
    MARKETS,
    audit_blind_cognitive_admission,
)
from qore.infrastructure.trader_lab.vt08_b_r16_owner_scope_no_alpha_v1 import (
    audit_frozen_source_program_scope,
    no_excluded_alpha_lineage,
)

SCHEMA: Final = "qore.vt08.b.r19.blind_author_semantics_reviewer_pack.v1"
R3_STAGE: Final = "UNIQUE_M3_CISD_PS_SHAPE_REQUIRES_AUTHOR_ADJUDICATION"
R3_CENSUS: Final = "qore.vt08.a.frozen_bullish_m30m3.source_funnel.v1"
QUESTIONS: Final = (
    "relevant_swing_pre_c2_which_bar_ids_and_confirmed_or_provisional",
    "valid_separation_contextual_source_reason_and_disagreement",
    "significant_poi_exists_pre_cisd_and_selected_poi_bar_ids",
    "causal_m3_opposing_series_cisd_ps_and_confirming_htf_closure",
    "bullish_breaker_sequence_low_high_lowerlow_higherhigh_bar_ids",
    "eq_regime_with_vs_against_valid_swing_and_c2_close",
    "stop_relative_eq_breaker_ps_and_lower_fvg_space_exact_basis",
    "untouched_htf_target_ids_and_author_tiebreak_basis",
)


def _key(case: dict[str, object], market: str) -> tuple[str, str]:
    if case.get("market") != market:
        raise ValueError("R19 cross-market physical source")
    try:
        opened = datetime.fromisoformat(str(case["c2_opened_at_utc"]))
        decision = datetime.fromisoformat(str(case["decision_at_utc"]))
    except (ValueError, KeyError) as exc:
        raise ValueError("R19 missing valid C2/C3 time") from exc
    if opened.utcoffset() is None or decision.utcoffset() is None:
        raise ValueError("R19 naive C2/C3 time")
    return opened.astimezone(UTC).isoformat(), decision.astimezone(UTC).isoformat()


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()


def _sample_indices(n: int, k: int) -> list[int]:
    if n <= k:
        return list(range(n))
    if k == 1:
        return [n // 2]
    return [i * (n - 1) // (k - 1) for i in range(k)]


def build_blind_semantic_review_packets(
    r3: dict[str, object], r7: dict[str, object], *,
    expected_market: str, per_category: int = 3,
) -> dict[str, object]:
    if expected_market not in MARKETS or type(per_category) is not int or not (
        1 <= per_category <= 10
    ):
        raise ValueError("R19 unsupported market or review sample rule")
    no_excluded_alpha_lineage(r3)
    no_excluded_alpha_lineage(r7)
    scope = audit_frozen_source_program_scope(r3, expected_market=expected_market)
    inventory = audit_blind_cognitive_admission(r7, expected_market=expected_market)
    if (
        r3.get("schema") != R3_CENSUS
        or r3.get("selection") != "ALL_C2_M30_OPEN_WITHIN_OWNER_WINDOWS_FIRST_FAIL_PRE_PNL"
        or r3.get("c2_windows_total") != 18646
        or r3.get("pnl_evaluated") is not False
        or r3.get("A_B_signed_manifest") is not False
        or r3.get("AUTHOR_RELEVANT_SWING_POI_BREAKER_TARGET_PENDING") is not True
        or scope["frozen_vt08_cases_verified"] != inventory["cases_review_queued"]
    ):
        raise ValueError("R19 R3/R7 frozen PNL-blind universe not equal")
    cases = r3["examples_by_stage"][R3_STAGE]
    if len(cases) != r7["frozen_event_count"]:
        raise ValueError("R19 source case count not identical")
    source_lookup: dict[tuple[str, str], dict[str, object]] = {}
    for case in cases:
        if not isinstance(case, dict) or case.get("family") != (
            "BULLISH_M30_C2_REVERSAL_M3_CISD_C3_POSITIONAL"
        ):
            raise ValueError("R19 wrong author source family")
        key = _key(case, expected_market)
        if key in source_lookup:
            raise ValueError("R19 duplicate R3 source case")
        if not (
            case.get("pre_c2_h1_context_available") is True
            or case.get("pre_c2_h1_context_available") is False
        ):
            raise ValueError("R19 missing H1 physical context flag")
        for receipt_list, count in (
            ("c1_m3_raw_bar_receipts", 10),
            ("c2_m3_raw_bar_receipts", 10),
            ("c2_m15_raw_bar_receipts", 2),
        ):
            if not isinstance(case.get(receipt_list), list) or len(case[receipt_list]) != count:
                raise ValueError("R19 missing real M3/M15 review receipts")
        prev = case.get("pre_c2_h1_m15_raw_bar_receipts")
        expected = 12 if case["pre_c2_h1_context_available"] else 0
        if not isinstance(prev, list) or len(prev) != expected:
            raise ValueError("R19 incomplete prior H1 source bars misrepresented")
        for list_name in ("c1_m3_raw_bar_receipts", "c2_m3_raw_bar_receipts",
                          "c2_m15_raw_bar_receipts", "pre_c2_h1_m15_raw_bar_receipts"):
            sha = (
                r3["source_m15_sha256"] if "m15" in list_name
                else r3["source_m3_sha256"]
            )
            if any(
                not isinstance(row, dict) or row.get("source_raw_sha256") != sha
                # Original A R3 bar receipts lack per-bar market; market
                # remains bound by the case identity and pinned raw SHA.
                or row.get("market") not in (None, expected_market)
                or row.get("semantics") != "OBSERVED_OHLC_ONLY_NOT_TTRADES_RULE"
                for row in case[list_name]
            ):
                raise ValueError("R19 source receipt feed/market/authority mismatch")
            for row in case[list_name]:
                body = {
                    k: row.get(k) for k in (
                        "profile", "source_raw_sha256", "opened_at_utc",
                        "closed_at_utc", "ohlc",
                    )
                }
                if row.get("source_bar_id") != _digest(body):
                    raise ValueError("R19 original source_bar_id digest mismatch")
        if (
            case.get("A_rule_complete") is not False
            or case.get("B_signoff") is not False
            or case.get("cognitive_ready") is not False
            or case.get("broker_fill") is not False
            or case.get("pnl_read") is not False
        ):
            raise ValueError("R19 forged A/B signoff or economic authority")
        source_lookup[key] = case
    bucket: dict[str, list[dict[str, object]]] = defaultdict(list)
    full_index = []
    for row in r7["all_source_only_cases"]:
        key = _key(row, expected_market)
        source = source_lookup.pop(key, None)
        if source is None:
            raise ValueError("R19 source row missing in R3")
        if row["pre_c2_three_h1_physically_complete"] is not (
            source["pre_c2_h1_context_available"]
        ):
            raise ValueError("R19 incompatible H1 context completeness")
        if source.get("source_m3_file_sha256") != r3["source_m3_sha256"] or (
            source.get("source_m15_file_sha256") != r3["source_m15_sha256"]
        ):
            raise ValueError("R19 cross-feed source identity drift")
        if row.get("case_id_sha256") != hashlib.sha256(
            f"{expected_market}|{key[0]}|{key[1]}".encode()
        ).hexdigest():
            raise ValueError("R19 physical review case fingerprint invalid")
        category = row["diagnostic_review_class"]
        bucket[category].append({"r7": row, "r3": source})
        full_index.append({
            "case_id_sha256": row["case_id_sha256"],
            "decision_at_utc": key[1],
            "diagnostic_review_class": category,
            "source_method_author_complete": False,
        })
    if source_lookup:
        raise ValueError("R19 R3 extra source rows not in R7")
    packets = []
    n_by_category = {}
    for category in CLASSES:
        ordered = sorted(bucket[category], key=lambda x: (
            x["r7"]["decision_at_utc"], x["r7"]["case_id_sha256"]
        ))
        n_by_category[category] = len(ordered)
        for ix in _sample_indices(len(ordered), per_category):
            material = ordered[ix]
            row = material["r7"]
            physical = material["r3"]
            # Deliberate reviewer source receipts only, never producer's
            # success, order, price target election, or terminal PnL.
            dossier = {
                "case_id_sha256": row["case_id_sha256"],
                "market": expected_market,
                "diagnostic_review_class": category,
                "c2_opened_at_utc": row["c2_opened_at_utc"],
                "decision_at_utc": row["decision_at_utc"],
                "pre_c2_three_h1_physically_complete": row[
                    "pre_c2_three_h1_physically_complete"
                ],
                "c2_m3_receipts": physical["c2_m3_raw_bar_receipts"],
                "c1_m3_receipts": physical["c1_m3_raw_bar_receipts"],
                "c2_m15_receipts": physical["c2_m15_raw_bar_receipts"],
                "prior_h1_m15_receipts": physical[
                    "pre_c2_h1_m15_raw_bar_receipts"
                ],
                "m3_ps_proxy_cisd_observed_time": physical["details"].get(
                    "cisd_confirmed_at_utc"
                ),
                "m3_ps_proxy_opposing_series_open": physical["details"].get(
                    "opposing_series_opened_at_utc"
                ),
                "h1_swing_source_bar_id_groups": row["h1_swing_source_ids"],
                "h1_target_candidates_untouched_asof": row[
                    "source_unconsumed_h1_highs"
                ],
                "eq_full_if_author_bullish_swing": row["c2_eq_full_conditional"],
                "eq_close_low_if_author_against_swing": row[
                    "c2_eq_close_to_low_conditional"
                ],
                "methodological_questions": QUESTIONS,
                "independent_reviewer_a_answers": None,
                "independent_reviewer_b_answers": None,
                "disagreement_resolution": None,
                "source_primary_reference_verified": False,
                "ttrades_author_complete": False,
                "cognitive_27_fields_proven": False,
                "eligible_for_pnl": False,
            }
            dossier["packet_evidence_sha256"] = _digest(dossier)
            packets.append(dossier)
    if sum(n_by_category.values()) != len(full_index) or (
        n_by_category != r7["category_counts"]
    ):
        raise ValueError("R19 reviewer sampling is not from full source universe")
    if len({p["case_id_sha256"] for p in packets}) != len(packets):
        raise ValueError("R19 duplicate independently reviewable packet")
    return {
        "schema": SCHEMA,
        "market": expected_market,
        "frozen_r3_sha256": _digest(r3),
        "frozen_r7_sha256": _digest(r7),
        "all_cases_census": len(full_index),
        "per_category_requested": per_category,
        "category_counts_full": n_by_category,
        "review_packets_selected": len(packets),
        "selection_policy": "BLIND_TIME_RANK_FIRST_MID_LAST_BY_PHYSICAL_CATEGORY_NO_PNL",
        "required_independent_reviewers": 2,
        "independent_reviews_completed": 0,
        "source_author_complete": 0,
        "cognitive_admissions": 0,
        "economic_gates_evaluated": False,
        "holdout_7y_accessed": False,
        "sizing_used": False,
        "case_index": full_index,
        "review_packets": packets,
        "verdict": "BLIND_REVIEW_EVIDENCE_PACK_ONLY_NOT_TTRADES_SIGNAL",
    }
