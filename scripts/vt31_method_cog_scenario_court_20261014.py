#!/usr/bin/env python3
"""Human-reviewable VT31 methodological/cognitive scenario court.

This is NOT a historical quantitative backtest or an automatic certification:
it tests explicit judgment/abstention cases of the *research* TTrades COG,
not the frozen G3 runtime COG; a separate human/source review is required.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_cog_evidence_v2_20261014 import TTRADES_AM, inspect_cog_evidence
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import (
    COG_VERSION,
    propose_ttrades_am_cognition,
)

NY = ZoneInfo("America/New_York")
PREREG = "d8d1aa4354b4f63602dc5706c0eed3a735ecafe6"


def _bar(
    t: datetime, *, o: str = "100", high: str = "102",
    low: str = "98", close: str = "101",
) -> M1Bar:
    return M1Bar(
        t, t + timedelta(minutes=1),
        Decimal(o), Decimal(high), Decimal(low), Decimal(close),
    )


def _fixture(*, month: int, side: Side) -> tuple[
    tuple[M1Bar, ...], tuple[M1Bar, ...],
]:
    """Source-specific synthetic case; not a historical market or author example."""
    d = 1 if month == 7 else 15
    start = datetime(2025, month, d, 9, tzinfo=NY).astimezone(UTC)
    nine = [_bar(start + timedelta(minutes=i)) for i in range(60)]
    nine[10] = _bar(nine[10].opened_at, high="110")
    nine[20] = _bar(nine[20].opened_at, low="90")
    ten = (
        _bar(start + timedelta(minutes=60), close="100"),
        _bar(
            start + timedelta(minutes=61),
            o="96", high="99", low="89", close="95",
        ),
        _bar(
            start + timedelta(minutes=62),
            o="94", high="106", low="93", close="105",
        ),
        _bar(
            start + timedelta(minutes=63),
            o="105", high="107", low="104", close="106",
        ),
    )
    if side is Side.LONG:
        nine[57] = _bar(nine[57].opened_at, high="104")
    else:
        nine[57] = _bar(nine[57].opened_at, low="96")
        ten = (
            _bar(start + timedelta(minutes=60), close="100"),
            _bar(
                start + timedelta(minutes=61),
                o="104", high="111", low="103", close="105",
            ),
            _bar(
                start + timedelta(minutes=62),
                o="106", high="107", low="94", close="95",
            ),
            _bar(
                start + timedelta(minutes=63),
                o="95", high="96", low="93", close="94",
            ),
        )
    return tuple(nine), ten


def _record_proposal(
    name: str,
    *,
    nine: tuple[M1Bar, ...],
    ten: tuple[M1Bar, ...],
    expected_action: str,
    expected_state: str,
    expected_reason: str | None = None,
    as_of: datetime | None = None,
    session: SessionId = SessionId.NY_AM,
) -> dict[str, Any]:
    at = as_of or ten[-1].closed_at
    response = propose_ttrades_am_cognition(
        as_of=at, history=nine + ten, session=session,
    )
    dto = response.decision
    action = (
        dto.side.value if dto is not None
        else "REJECT" if response.state == "REJECTED"
        else "WAIT"
    )
    reason_ok = (
        expected_reason is None or expected_reason in response.reasons
    )
    matching = (
        action == expected_action
        and response.state == expected_state
        and reason_ok
        and not response.method_certified
        and not response.cognition_certified
        and not response.execution_authorized
    )
    if not matching:
        raise ValueError(f"COGNITIVE_SCENARIO_DISAGREEMENT:{name}:{action}:{response.state}")
    return {
        "case": name,
        "source": "SYNTHETIC_M1_CONTEXT_NOT_AUTHOR_LABELLED",
        "profile": TTRADES_AM,
        "cognitive_version": COG_VERSION,
        "visible_as_of_utc": at.isoformat(),
        "visible_as_of_ny": at.astimezone(NY).isoformat(),
        "expected_action": expected_action,
        "actual_action": action,
        "state": response.state,
        "reason_codes": list(response.reasons),
        "expected_reason": expected_reason,
        "opposite_h1_dol": str(dto.draw_target) if dto else None,
        "structure_mss_at": (
            dto.structure_break_confirmed_at.isoformat() if dto else None
        ),
        "decision_time_not_in_future": (
            dto is None or dto.observed_at == at
        ),
        "case_procedurally_consistent": matching,
        "author_source_fidelity_certified": False,
        "cognitive_autonomy_of_frozen_g3_verified": False,
        "human_independent_review_completed": False,
        "execution_authorized": False,
    }


def _wrong_dol_case(nine: tuple[M1Bar, ...], ten: tuple[M1Bar, ...]) -> dict[str, Any]:
    """Independent source witness must refuse tampered DTO; not a new COG result."""
    at = ten[-1].closed_at
    response = propose_ttrades_am_cognition(
        as_of=at, history=nine + ten,
    )
    if response.decision is None:
        raise ValueError("POSITIVE_COG_DECISION_REQUIRED_FOR_DOL_ADVERSARIAL")
    fake = replace(response.decision, draw_target=Decimal("150"))
    inspected = inspect_cog_evidence(
        profile=TTRADES_AM, session=SessionId.NY_AM,
        as_of=at, history=nine + ten, cognition=fake,
    )
    if (
        inspected.state != "REJECTED"
        or "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" not in inspected.rejected
    ):
        raise ValueError("WRONG_DOL_NOT_CAUGHT_BY_INDEPENDENT_SOURCE")
    return {
        "case": "WRONG_DOL_DTO",
        "source": "SYNTHETIC_MUTATED_DTO_UNTRUSTED",
        "profile": TTRADES_AM,
        "cognitive_version": COG_VERSION,
        "visible_as_of_utc": at.isoformat(),
        "visible_as_of_ny": at.astimezone(NY).isoformat(),
        "expected_action": "REJECT",
        "actual_action": "REJECT",
        "state": "REJECTED",
        "reason_codes": list(inspected.rejected),
        "expected_reason": "DOL_NOT_OPPOSITE_9AM_H1_EXTREME",
        "opposite_h1_dol": None,
        "structure_mss_at": None,
        "decision_time_not_in_future": True,
        "case_procedurally_consistent": True,
        "author_source_fidelity_certified": False,
        "cognitive_autonomy_of_frozen_g3_verified": False,
        "human_independent_review_completed": False,
        "execution_authorized": False,
    }


def scenario_dossier() -> dict[str, Any]:
    nine, ten = _fixture(month=7, side=Side.LONG)
    short_nine, short_ten = _fixture(month=1, side=Side.SHORT)
    no_raid = (
        ten[0],
        _bar(ten[1].opened_at),
        ten[2],
    )
    double = (
        ten[0],
        _bar(ten[1].opened_at, high="111", low="89"),
        ten[2],
    )
    weak_mss = (
        ten[0], ten[1],
        _bar(ten[2].opened_at, o="94", high="103", low="93", close="100"),
    )
    cases = [
        _record_proposal(
            "LONG_RAID_MSS_DOL", nine=nine, ten=ten[:3],
            expected_action="LONG", expected_state="CONTEXT_ATTESTED_NOT_CERTIFIED",
        ),
        _record_proposal(
            "SHORT_MIRROR_DST", nine=short_nine, ten=short_ten[:3],
            expected_action="SHORT", expected_state="CONTEXT_ATTESTED_NOT_CERTIFIED",
        ),
        _record_proposal(
            "NO_SWEEP_WAIT", nine=nine, ten=no_raid,
            expected_action="WAIT", expected_state="UNKNOWN",
            expected_reason="NO_PRIOR_9AM_H1_RAID_YET",
        ),
        _record_proposal(
            "TWO_SIDES_SAME_M1_UNKNOWN", nine=nine, ten=double,
            expected_action="WAIT", expected_state="UNKNOWN",
            expected_reason="BOTH_H1_SIDES_SWEPT_UNKNOWN_INTRABAR_ORDER",
        ),
        _record_proposal(
            "WEAK_OR_UNCONFIRMED_MSS_WAIT", nine=nine, ten=weak_mss,
            expected_action="WAIT", expected_state="UNKNOWN",
            expected_reason="QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN",
        ),
        _record_proposal(
            "INCOMPLETE_9AM_WAIT", nine=nine[:59], ten=ten[:3],
            expected_action="WAIT", expected_state="UNKNOWN",
        ),
        _record_proposal(
            "FUTURE_M1_REJECT", nine=nine, ten=ten,
            as_of=ten[2].closed_at,
            expected_action="REJECT", expected_state="REJECTED",
            expected_reason="FUTURE_M1_FORBIDDEN",
        ),
        _record_proposal(
            "WRONG_PROFILE_LONDON_REJECT", nine=nine, ten=ten[:3],
            session=SessionId.LONDON,
            expected_action="REJECT", expected_state="REJECTED",
            expected_reason="PROFILE_ONLY_TTRADES_NY_AM",
        ),
        _record_proposal(
            "STALE_RETURN_WAIT", nine=nine, ten=ten,
            expected_action="WAIT", expected_state="UNKNOWN",
            expected_reason="RETURN_M1_NOT_FRESH_AT_ASOF",
        ),
        _wrong_dol_case(nine, ten[:3]),
    ]
    return {
        "title": "VT31_RESEARCH_COG_SEMANTIC_JUDGMENT_DOSSIER",
        "prereg_commit": PREREG,
        "cases": cases,
        "case_check_mode": "INDIVIDUAL_SEMANTIC_PROCEDURE_NOT_STATISTICAL_SCORE",
        "review_subject": "QORE_TTRADES_NYAM_RESEARCH_COG_NOT_FROZEN_G3_COG",
        "original_g3_cog_directly_examined": False,
        "methodology_author_certified": False,
        "cognitive_method_certified": False,
        "human_cog_ops_signatures": False,
        "certification_decision": "PENDING_PRIMARY_SOURCE_AND_G3_COG_HUMAN_REVIEW",
        "trader_lab_economic_gate_decision": "OUT_OF_SCOPE",
        "orders_or_sizing": 0,
        "financial_results": None,
        "fresh_oos_consumed": False,
        "live_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = scenario_dossier()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "cases": [f"{x['case']}:{x['actual_action']}" for x in data["cases"]],
        "certification_decision": data["certification_decision"],
        "original_g3_cog_directly_examined":
            data["original_g3_cog_directly_examined"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
