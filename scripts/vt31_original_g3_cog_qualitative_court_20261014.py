#!/usr/bin/env python3
"""Qualitative, per-situation audit of the ACTUAL ORIGINAL VT31 G3 COG engine.

Directly invokes frozen VT31CleanroomCognition.observe_closed_m1/assess.
No alternative TTrades producer, market-return tests, fills, sizing or trading.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha1, sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VERSION, VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY, M1Bar, SessionId, Side,
)

PREREG = "d5a783d7bf4b7ffe4c91b9feffabdf53146a962c"
FROZEN_G3_COG_GIT_BLOB = "d0ab4c15d6e9d24e53224d27bdb2cd96af914fb9"
SOURCE_ID = "ORIGINAL_VT31_ICT_CLEANROOM_G3_COG_V1"


def source_fingerprint() -> dict[str, str]:
    source = (
        Path(__file__).resolve().parent.parent
        / "src/qore/infrastructure/traders/vt31_ict_cleanroom/cognition.py"
    )
    data = source.read_bytes()
    git_blob = sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if git_blob != FROZEN_G3_COG_GIT_BLOB:
        raise ValueError("ORIGINAL_G3_COG_SOURCE_MUTATED")
    return {
        "git_blob_sha1": git_blob,
        "source_sha256": sha256(data).hexdigest(),
    }


def _bar(
    at: datetime, *, o: str = "100", high: str = "101",
    low: str = "99", close: str = "100.5",
) -> M1Bar:
    return M1Bar(
        opened_at=at,
        closed_at=at + timedelta(minutes=1),
        open=Decimal(o), high=Decimal(high),
        low=Decimal(low), close=Decimal(close),
    )


def london_fixture() -> tuple[tuple[M1Bar, ...], datetime]:
    """Controlled ORIGINAL-G3-consumed input, not author-labelled evidence."""
    prior_start = datetime(2026, 1, 2, 14, 30, tzinfo=UTC)
    current_start = datetime(2026, 1, 5, 5, 0, tzinfo=UTC)
    prior = tuple(
        _bar(
            prior_start + timedelta(minutes=i),
            o="110",
            high="150" if i == 33 else "114",
            low="80" if i == 45 else "108",
            close="111",
        )
        for i in range(390)
    )
    asia = tuple(
        _bar(current_start + timedelta(minutes=i))
        for i in range(180)
    )
    start = current_start + timedelta(minutes=180)
    london = (
        _bar(start, o="100", high="103", low="99", close="101"),
        _bar(
            start + timedelta(minutes=1),
            o="101", high="103", low="100", close="100.5",
        ),
        _bar(start + timedelta(minutes=2), o="101", high="105", low="100", close="102"),
        _bar(start + timedelta(minutes=3), o="101", high="104", low="100", close="101"),
        _bar(start + timedelta(minutes=4), o="101", high="104", low="100", close="104"),
        _bar(start + timedelta(minutes=5), o="101", high="109", low="101", close="107"),
    )
    return prior + asia + london, london[-1].closed_at


def _run(
    market: tuple[M1Bar, ...], at: datetime, *,
    framework: str | None = None,
) -> tuple[VT31CleanroomCognition, dict[str, Any]]:
    cog = (
        VT31CleanroomCognition(framework_policy=framework)
        if framework is not None else VT31CleanroomCognition()
    )
    for item in market:
        cog.observe_closed_m1(item)
    result = cog.assess(session=SessionId.LONDON, as_of=at)
    dto = result.decision
    snapshot = {
        "observed_closed_m1_count": result.causal_closed_m1_count,
        "state": result.state,
        "action": dto.side.value if dto else "WAIT",
        "missing": list(result.missing),
        "verified_htf": list(result.verified_htf),
        "source_pool_count": result.source_pool_count,
        "structure_shift_detected": result.structure_shift_detected,
        "decision": {
            "source_provenance": dto.source_provenance,
            "draw_family": dto.draw_family,
            "draw_target": str(dto.draw_target),
            "mss_structure_level": str(dto.structure_level),
            "mss_confirmed_at": dto.structure_break_confirmed_at.isoformat(),
            "pivot_confirmed_at": dto.structure_level_confirmed_at.isoformat(),
            "framework_policy": dto.framework_policy,
            "mss_anchor_close": (
                str(dto.mss_anchor_close)
                if dto.mss_anchor_close is not None else None
            ),
            "available_at": dto.observed_at.isoformat(),
        } if dto else None,
        "research_only": result.research_only,
        "trade_authorized": result.trade_authorized,
    }
    if not result.research_only or result.trade_authorized:
        raise ValueError("ORIGINAL_G3_COG_MUST_HAVE_ZERO_TRADE_AUTHORITY")
    if dto and (dto.observed_at != at or dto.structure_break_confirmed_at > at):
        raise ValueError("ORIGINAL_COG_FUTURE_FACT_OR_BACKDATED_DECISION")
    return cog, snapshot


def original_cog_scenario_dossier() -> dict[str, Any]:
    original, at = london_fixture()
    cases: list[dict[str, Any]] = []

    def add(
        name: str, observation: dict[str, Any], *,
        expected_action: str,
        expected_reason: str | None = None,
        expected_target: str | None = None,
        interpretation: str,
    ) -> None:
        if observation["action"] != expected_action:
            raise ValueError(f"ORIGINAL_COG_JUDGMENT_CONTRADICTION:{name}:ACTION")
        if (
            expected_reason is not None
            and expected_reason not in observation["missing"]
        ):
            raise ValueError(f"ORIGINAL_COG_JUDGMENT_CONTRADICTION:{name}:REASON")
        if (
            expected_target is not None and (
                observation["decision"] is None
                or observation["decision"]["draw_target"] != expected_target
            )
        ):
            raise ValueError(f"ORIGINAL_COG_JUDGMENT_CONTRADICTION:{name}:DOL")
        cases.append({
            "name": name,
            "profile": "ICT_GENERAL_2023_LONDON_QORE_COG_PROXY",
            "as_of": at.isoformat(),
            "expected_action": expected_action,
            "expected_source_reason": expected_reason,
            "observed": observation,
            "qualitative_adjudication": interpretation,
            "author_method_certified": False,
            "original_g3_cog_integrity_witnessed": True,
            "human_independent_review": False,
            "execution_authorized": False,
        })

    cog, positive = _run(original, at)
    add(
        "LONDON_SOURCE_LONG", positive,
        expected_action="LONG", expected_target="150",
        interpretation="PROCEDURAL_CONSISTENT_WITH_MARKET_SOURCE_NOT_AUTHOR_CERT",
    )
    again = cog.assess(session=SessionId.LONDON, as_of=at)
    if again.decision is None or positive["decision"] is None:
        raise ValueError("REPEAT_ASOF_LOST_ORIGINAL_DECISION")
    if (
        again.decision.draw_target != Decimal(positive["decision"]["draw_target"])
        or again.decision.side is not Side.LONG
    ):
        raise ValueError("REPEAT_ASOF_DECISION_CHANGED_WITHOUT_NEW_FACTS")
    add(
        "LONDON_HOLD_SAME_ASOF", positive,
        expected_action="LONG", expected_target="150",
        interpretation="CAUSAL_MEMORY_IDEMPOTENT_AT_SAME_ASOF",
    )

    no_prior = original[390:]
    _, incomplete = _run(no_prior, at)
    add(
        "NO_PREVIOUS_CASH_POOL", incomplete,
        expected_action="WAIT", expected_reason="LIQUIDITY_POOL",
        interpretation="EXPECTED_ABSTENTION_NO_VALID_PRIOR_DOL",
    )

    _, early = _run(original[:-1], original[-2].closed_at)
    add(
        "MSS_NOT_YET_CONFIRMED", early,
        expected_action="WAIT", expected_reason="CONFIRMED_DISPLACEMENT_MSS",
        interpretation="EXPECTED_ABSTENTION_PIVOT_NOT_BROKEN",
    )

    current = tuple(x for x in original if x.opened_at >= at - timedelta(minutes=6))
    _, no_htf = _run(original[:390] + current, at)
    add(
        "HTF_CONTEXT_MISSING", no_htf,
        expected_action="WAIT", expected_reason="H1_CLOSED_CONTEXT",
        interpretation="EXPECTED_ABSTENTION_NO_CONTEMPORARY_H1_M15",
    )
    if "M15_CLOSED_CONTEXT" not in no_htf["missing"]:
        raise ValueError("MISSING_HTF_CONTEXT_M15_NOT_RECOGNIZED")

    def after_bar(bar: M1Bar, case: str, interpretation: str) -> None:
        engine, first = _run(original, at)
        if first["action"] != "LONG":
            raise ValueError("ORIGINAL_POSITIVE_CONTEXT_DISAPPEARED")
        engine.observe_closed_m1(bar)
        updated = engine.assess(
            session=SessionId.LONDON, as_of=bar.closed_at,
        )
        if updated.decision is not None or updated.trade_authorized:
            raise ValueError("STALE_OR_REVOKED_COG_STILL_ACTIVE:" + case)
        add(
            case,
            {
                "observed_closed_m1_count": updated.causal_closed_m1_count,
                "state": updated.state, "action": "WAIT",
                "missing": list(updated.missing),
                "verified_htf": list(updated.verified_htf),
                "source_pool_count": updated.source_pool_count,
                "structure_shift_detected": updated.structure_shift_detected,
                "decision": None,
                "research_only": updated.research_only,
                "trade_authorized": updated.trade_authorized,
            },
            expected_action="WAIT", interpretation=interpretation,
        )

    after_bar(
        _bar(at, o="107", high="152", low="106", close="110"),
        "AFTER_DOL_CONSUMED", "EXPECTED_ABSTENTION_TARGET_NO_LONGER_AVAILABLE",
    )
    after_bar(
        _bar(at, o="107", high="108", low="100", close="102"),
        "AFTER_PIVOT_REVERSAL", "EXPECTED_ABSTENTION_MSS_INVALIDATED",
    )

    engine, first = _run(original, at)
    later = _bar(at, o="107", high="110", low="105", close="109")
    engine.observe_closed_m1(later)
    error: str | None = None
    try:
        engine.assess(session=SessionId.LONDON, as_of=at)
    except ValueError as exc:
        error = str(exc)
    if not error or "exactly latest closed M1" not in error:
        raise ValueError("FUTURE_RETRO_ASOF_NOT_REJECTED")
    add(
        "FUTURE_RETRO_ASOF", {
            **first, "state": "CAUSAL_INPUT_REJECTED",
            "action": "REJECT",
            "decision": None, "missing": [error],
        },
        expected_action="REJECT",
        interpretation="CAUSAL_INPUT_REJECTED_NO_BACKDATED_ASSESSMENT",
    )

    _, opt_g3 = _run(
        original, at, framework=G3_MSS_FRAMEWORK_POLICY,
    )
    if (
        opt_g3["decision"] is None
        or opt_g3["decision"]["mss_anchor_close"] != "107"
        or opt_g3["decision"]["framework_policy"] != G3_MSS_FRAMEWORK_POLICY
    ):
        raise ValueError("G3_ACTUAL_MSS_M1_CLOSE_NOT_PINNED")
    add(
        "G3_MSS_ANCHOR", opt_g3,
        expected_action="LONG", expected_target="150",
        interpretation="MSS_PRICE_OBSERVED_FROM_CLOSED_M1_NOT_FUTURE_C3",
    )

    add(
        "LONDON_NOT_TTRADES_PROFILE", positive,
        expected_action="LONG", expected_target="150",
        interpretation="ICT_GENERAL_LONDON_IS_NOT_TTRADES_NYAM_AUTHOR_ATTESTATION",
    )
    return {
        "kind": "VT31_ORIGINAL_G3_COG_AUTHENTIC_QUALITATIVE_CASES",
        "prereg_commit": PREREG,
        "source_engine": SOURCE_ID,
        "source_engine_version": VERSION,
        "original_source_hash": source_fingerprint(),
        "evidence_mode": "SEMANTIC_CAUSAL_DECISION_AND_ABSTENTION_NO_PNL",
        "cases": cases,
        "methodology_status": "PENDING_SOURCE_FIDELITY_AND_FULL_FAMILY_DOCTRINE",
        "cognitive_status": "PENDING_COMPLETE_PROFILE_TESTS_AND_HUMAN_REVIEW",
        "research_source_behavior_observed": True,
        "original_cog_directly_invoked": True,
        "same_live_g3_original_code_unchanged": True,
        "human_cog_ops_signature_proven": False,
        "financial_results": None,
        "fresh_holdout_used": False,
        "orders_executed": 0,
        "trader_sizing_actions": 0,
        "trader_certified": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    opt = parser.parse_args()
    result = original_cog_scenario_dossier()
    opt.out.parent.mkdir(parents=True, exist_ok=True)
    opt.out.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "original_cog_directly_invoked": result["original_cog_directly_invoked"],
        "cases": [
            [x["name"], x["observed"]["action"]] for x in result["cases"]
        ],
        "methodology_status": result["methodology_status"],
        "cognitive_status": result["cognitive_status"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
