#!/usr/bin/env python3
"""TTrades NY AM semantic dossier with ACTUAL #933 native cognition on 3Y M1.

This is a method-and-cognition audit, NOT backtest/PnL, not certification.
The primary author's qualitative displacement ≠ frozen QORE 1.25x MSS proxy.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar
from scripts.vt31_cog_evidence_v2_20261014 import (
    TTRADES_AM,
    inspect_cog_evidence,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_ttrades_am_cognitive_fidelity_witness_20261014 import (
    assess_ttrades_am_context,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
    run_census,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    COG_VERSION,
    PROFILE,
    TARGET_FAMILY,
    propose_ttrades_am_cognition,
)

MODEL = "VT31_TTRADES_AM_SEMANTIC_REVIEW_REAL_COG_V1"
PREREG_COMMIT = "973ce267c9cbe00281fca717ad5a62d9eddb250c"
CANONICAL_CLASSES = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
CAUSAL_CLASS_TO_NATIVE = {
    "MSS_ATTESTED_CONTEXT_ONLY": "RETURN_INSIDE_OBSERVED",
    "FIRST_RETURN_NO_QORE_MSS": "RETURN_INSIDE_OBSERVED",
    "SWEEP_NO_RETURN": "AWAIT_RETURN",
    "NO_SWEEP": "AWAIT_SWEEP",
}
NO_ENTRY = frozenset({
    "FIRST_RETURN_NO_QORE_MSS", "SWEEP_NO_RETURN",
    "NO_SWEEP", "INCOMPLETE_M1_HOURS", "REJECTED_SOURCE",
})


def inspect_real_day(
    *, day: str, nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...], census: dict[str, Any],
) -> dict[str, Any]:
    """Separate as-of cognitive producer evidence from method source verdict."""
    category = census["classification"]
    if category not in CANONICAL_CLASSES:
        raise ValueError("UNKNOWN_PREREGISTERED_CASE_CATEGORY")
    base: dict[str, Any] = {
        "ny_day": day,
        "classification": category,
        "source_profile": PROFILE,
        "method_source": "TTRADES_AM_NQ_JUN_19_2025",
        "real_cog_producer": COG_VERSION,
        "source_cog_case_authentic": True,
        "methodology_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "trader_order_or_fill": False,
        "quantitative_performance_not_examined": True,
        "m4_four_families": "NOT_EVALUATED",
        "m5_swing_stop": "NOT_EVALUATED",
        "m6_independent_authority": "PENDING",
    }
    if category == "INCOMPLETE_M1_HOURS":
        if (complete_hour(day, 9, nine)
                and complete_hour(day, 10, ten)):
            raise AssertionError("CENSUS_MARKED_COMPLETE_SOURCE_INCOMPLETE")
        return {
            **base, "as_of": None,
            "native_cog_emitted_proposal": False,
            "semantic_m0_identity": "TTRADES_ONLY_NOT_ICT_GENERAL",
            "semantic_m1_causal": "UNKNOWN_INCOMPLETE_SOURCE",
            "semantic_m2_raid_and_dol": "NOT_EVALUABLE_NO_COMPLETE_09_10_HOURS",
            "semantic_m3_mss_displacement": "NOT_EVALUABLE",
            "native_source_state": "NOT_EVALUABLE",
            "cog_state": "NOT_RUN_WITH_INCOMPLETE_REFERENCE",
            "cog_reasons": ["REQUIRE_COMPLETE_9_AND_10_SOURCE_FIRST"],
            "semantic_abstention": "NO_PROPOSAL_NO_FAKE_TRADE",
        }
    if not complete_hour(day, 9, nine) or not complete_hour(day, 10, ten):
        raise AssertionError("FULL_CENSUS_CASE_WITH_GAPPED_M1")
    at = datetime.fromisoformat(census["as_of"]).astimezone(UTC)
    prefix = tuple(b for b in ten if b.closed_at <= at)
    if not prefix or prefix[-1].closed_at != at:
        raise AssertionError("CASE_ASOF_NOT_CLOSED_NATIVE_PREFIX")
    real = propose_ttrades_am_cognition(
        as_of=at, history=nine+prefix,
    )
    if real.as_of != at:
        raise AssertionError("COGNITIVE_PRODUCER_BACKDATED_ASOF")
    if bool(real.decision) != census["has_source_cognitive_proposal"]:
        raise AssertionError("ORIGINAL_CENSUS_COG_EMISSION_CHANGED")
    native = native_ttrades_am_context(
        as_of=at, nine=nine, ten=prefix,
    )
    witness_again = real.native_state == native.state
    if not witness_again:
        raise AssertionError("NATIVE_CONTEXT_NOT_EQUAL_INDEPENDENT_REPLAY")
    if category in CAUSAL_CLASS_TO_NATIVE:
        if native.state != CAUSAL_CLASS_TO_NATIVE[category]:
            raise AssertionError("PRE_REGISTERED_NATIVE_SOURCE_STATE_DRIFT")
    if category == "MSS_ATTESTED_CONTEXT_ONLY" and (
        real.state != "CONTEXT_ATTESTED_NOT_CERTIFIED"
    ):
        raise AssertionError("SOURCE_CONTEXT_COG_STATE_CHANGED")
    if category == "FIRST_RETURN_NO_QORE_MSS" and (
        real.state != "UNKNOWN"
        or "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN" not in real.reasons
    ):
        raise AssertionError("COG_FIRST_RETURN_NO_QORE_MSS_MUST_ABSTAIN")
    if category in {"NO_SWEEP", "SWEEP_NO_RETURN"} and (
        real.state != "UNKNOWN" or real.decision is not None
    ):
        raise AssertionError("COG_MUST_ABSTAIN_WITHOUT_AUTHOR_SOURCE")
    if category == "REJECTED_SOURCE" and (
        real.state != "REJECTED" or real.decision is not None
    ):
        raise AssertionError("REJECTED_NATIVE_SOURCE_MUST_NOT_PROPOSE")
    report: dict[str, Any] = {
        **base,
        "as_of": at.isoformat(),
        "native_cog_emitted_proposal": real.decision is not None,
        "source_events_asof_only": True,
        "native_source_state": native.state,
        "first_raid": native.first_sweep_side,
        "first_raid_causal_at": (
            native.first_sweep_at.isoformat()
            if native.first_sweep_at else None
        ),
        "first_return_causal_at": (
            native.return_inside_at.isoformat()
            if native.return_inside_at else None
        ),
        "expected_direction_from_raid": native.candidate_side,
        "top_level_cog_state": real.state,
        "cog_reasons": list(real.reasons),
        "semantic_m0_identity": "TTRADES_ONLY_NOT_ICT_GENERAL",
        "semantic_m1_causal": "CLOSED_M1_ASOF_IN_SCOPE",
        "semantic_m3_mss_displacement": "QORE_PROXY_NOT_AUTHOR_CERTIFIED",
        "semantic_abstention": (
            "SOURCE_CONDITION_UNFULFILLED_NO_INTENT"
            if real.decision is None else "COG_CONTEXT_ONLY_NO_ORDER"
        ),
        "cog_top_level_explicit_wait": real.state == "WAIT",
        "cog_native_source_wait": native.state in {
            "AWAIT_SWEEP", "AWAIT_RETURN",
        },
    }
    if real.decision is None:
        report["semantic_m2_raid_and_dol"] = (
            "SOURCE_ABSTENTION_NO_DRAW_ASSERTED"
            if category != "REJECTED_SOURCE"
            else "SOURCE_REJECTED_NO_DRAW_ASSERTED"
        )
        report["independent_926"] = "NOT_APPLICABLE_NO_COG_DTO"
        report["independent_v2"] = None
    else:
        dto = real.decision  # AUTHENTIC #933 only, never constructed here.
        if dto.cognitive_version != COG_VERSION:
            raise AssertionError("COG_IDENTITY_NOT_TTRADES_PROFILE")
        if dto.draw_family != TARGET_FAMILY or dto.observed_at != at:
            raise AssertionError("COG_WRONG_DRAW_FAMILY_OR_TIME")
        if (
            native.opposite_h1_dol is None
            or dto.draw_target != native.opposite_h1_dol
            or dto.side.value != native.candidate_side
            or native.first_sweep_at is None
            or dto.structure_break_confirmed_at <= native.first_sweep_at
        ):
            raise AssertionError("COG_H1_OPPOSITE_DOL_OR_RAID_INCONSISTENCY")
        proof = assess_ttrades_am_context(
            cognition=dto, previous_ny_9am=nine,
            current_ny_10am=prefix,
        )
        v2 = inspect_cog_evidence(
            profile=TTRADES_AM, session=dto.session,
            as_of=at, history=nine+prefix, cognition=dto,
        )
        report["independent_926"] = proof.status
        report["independent_926_reasons"] = list(proof.reason_codes)
        report["independent_v2"] = v2.state
        report["independent_v2_reasons"] = list(v2.rejected+v2.unknown)
        report["mss_at"] = dto.structure_break_confirmed_at.isoformat()
        report["cog_direction_matches_first_raid"] = True
        report["cog_dol_matches_opposite_09_h1"] = True
        report["semantic_m2_raid_and_dol"] = (
            "AUTHORIAL_H1_RAID_TARGET_CONTEXT_CONFORMANT"
            if (proof.status == "CONTEXT_CONFORMANT_ONLY"
                and v2.state == "CONFIRMED")
            else "EXTERNAL_SOURCE_WITNESS_CONTRADICTION"
        )
    return report


def semantic_casebook(
    groups: dict[str, dict[int, tuple[M1Bar, ...]]],
) -> dict[str, Any]:
    census = run_census(groups)  # the frozen 2026-10-14 source census.
    if census["observed_days_total"] != 775:
        raise AssertionError("PREREGISTERED_SOURCE_DAYS_CHANGED")
    if census["state_counts"] != CANONICAL_CLASSES:
        raise AssertionError("PREREGISTERED_DAILY_SOURCE_CLASSES_CHANGED")
    records: list[dict[str, Any]] = []
    first_by_class: dict[str, dict[str, Any]] = {}
    for observation in census["source_classifications"]:
        d = observation["ny_day"]
        hours = groups[d]
        case = inspect_real_day(
            day=d, nine=hours[9], ten=hours[10],
            census=observation,
        )
        records.append(case)
        first_by_class.setdefault(case["classification"], case)
    if len(first_by_class) != len(CANONICAL_CLASSES):
        raise AssertionError("NOT_ALL_PREREGISTERED_CASE_CATEGORIES_OBSERVED")
    disagreements = [
        x for x in records
        if x.get("semantic_m2_raid_and_dol")
        == "EXTERNAL_SOURCE_WITNESS_CONTRADICTION"
    ]
    incorrect_abstention = [
        x for x in records
        if x["classification"] in NO_ENTRY
        and x["native_cog_emitted_proposal"]
    ]
    if incorrect_abstention:
        raise AssertionError("COG_MINTED_INTENT_ON_NO_TRADE_SOURCE_CASE")
    if any(x["methodology_certified"] or x["cognition_certified"]
           for x in records):
        raise AssertionError("CENSUS_IS_NOT_METHOD_CERTIFICATION")
    label_counts = Counter(x["semantic_m2_raid_and_dol"] for x in records)
    return {
        "model": MODEL,
        "prereg_sha": PREREG_COMMIT,
        "method_primary_source": (
            "https://ttrades.com/the-am-silver-bullet-strategy-on-nq/"
        ),
        "profile": PROFILE,
        "market_sha256": MARKET_SHA,
        "source_scope": "NAS100_3Y_ALREADY_EXPLORED_DEVELOPMENT_NOT_OOS",
        "source_days": len(records),
        "original_case_categories": dict(sorted(CANONICAL_CLASSES.items())),
        "source_decision_evidence_by_category": dict(
            sorted(label_counts.items())
        ),
        "casebook_selection": "LEXICOGRAPHIC_FIRST_NY_DAY_PER_CATEGORY",
        "first_genuine_m1_case_per_category": first_by_class,
        "all_days_native_semantic_cases": records,
        "source_witness_disagreements_by_day": [
            {"ny_day": x["ny_day"],
             "independent_926_reasons": x.get("independent_926_reasons"),
             "independent_v2_reasons": x.get("independent_v2_reasons")}
            for x in disagreements
        ],
        "m3_authorial_displacement": "NOT_ATTESTED_QORE_PIVOT_PROXY",
        "m4_displacement_fvg_ob_breaker": "NOT_EVALUATED",
        "m5_stop_swing_exit_policy": "NOT_EVALUATED",
        "m6_independent_approvals": "PENDING",
        "casebook_is_quantitative_certification": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "trader_certified": False,
        "economic_metrics_computed": False,
        "broker_ack_fills_orders": 0,
        "trader_sizing": False,
        "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    arg = p.parse_args()
    if hash_file(arg.market) != MARKET_SHA:
        raise ValueError("SOURCE_NAS100_M1_SHA_MISMATCH")
    groups, total = collect_hours(market_rows(arg.market))
    if total != M1_TOTAL:
        raise AssertionError("SOURCE_BAR_COUNT_CHANGED")
    record = semantic_casebook(groups)
    record["source_m1_total"] = total
    arg.out.parent.mkdir(parents=True, exist_ok=True)
    arg.out.write_text(
        json.dumps(record, indent=2, ensure_ascii=False)+"\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "profile": record["profile"],
        "source_days": record["source_days"],
        "casebook_selection": record["casebook_selection"],
        "categories": record["original_case_categories"],
        "source_decision_evidence_by_category": (
            record["source_decision_evidence_by_category"]
        ),
        "genuine_m1_case_exemplars": {
            key: {
                "date": case["ny_day"],
                "as_of": case.get("as_of"),
                "cog_state": case.get("top_level_cog_state", case.get("cog_state")),
                "native_state": case["native_source_state"],
                "source_m2": case["semantic_m2_raid_and_dol"],
                "cog_reasons": case.get("cog_reasons"),
                "independent_926": case.get("independent_926"),
            } for key, case in record["first_genuine_m1_case_per_category"].items()
        },
        "source_witness_disagreement_dates": len(
            record["source_witness_disagreements_by_day"]
        ),
        "m3_authorial_displacement": record["m3_authorial_displacement"],
        "methodology_certified": False,
        "cognition_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
