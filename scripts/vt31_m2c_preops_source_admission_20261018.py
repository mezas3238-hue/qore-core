#!/usr/bin/env python3
"""M2 PRE-OPS RESEARCH gate on PRECOMMITTED original G3 first-M1 DTO fixtures.

No source modification, no live G3/OPS bridge, no broker, no orders, no sizing.
Fixture is future-known to the replay harness: the guard itself sees only
M1 CLOSED through current as_of and the one event at its matching as_of.
No author certification, not a production trader-coordinator deployment.
"""
from __future__ import annotations

import argparse
import json
from array import array
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    SessionId,
)
from scripts.vt31_ict_cleanroom_cog_real_3y_fast_v1 import _stream
from scripts.vt31_m2_298_unknown_closed_m1_gap_forensic_20261017 import (
    ORIGINAL_M2_CASEBOOK,
    minute,
    sealed_prior_casebook,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    hash_file,
)

PREREG = "788e1951e1c721db3c23c25b5f892c92b15faa16"
VERSION = "VT31_M2C_RESEARCH_PREOPS_FROZEN_G3_FIRST_M1_3_SESSIONS_V1"
VALID_HOUR = {
    SessionId.LONDON: 3,
    SessionId.NY_AM: 10,
    SessionId.NY_PM: 14,
}
EXPECTED = {
    "SOURCE_CONTEXT_COMPLETE_UNCERTIFIED": 445,
    "WAIT_SOURCE_M1_GAP": 298,
    "WAIT_CASH_CALENDAR_POLICY_UNSIGNED": 18,
}


@dataclass(frozen=True, slots=True)
class PreOpsAdmission:
    """No path in this RESEARCH gate may return an authorized OPS DTO."""

    ny_day: str
    session: str
    as_of_utc: str
    original_g3_draw_family: str
    source_m2_status: str
    independent_missing_m1: int | None
    ops_cognition: None = None
    ops_authorized: bool = False
    method_owner_signed: bool = False
    author_method_certified: bool = False
    broker_orders: int = 0
    sizing: int = 0


class M2PreOpsResearchGate:
    """Time monotonic ingestion of actual M1 only; pre-OPS DTO veto stage.

    A research replay injects one FROZEN ORIGINAL G3 DTO at its own as_of.
    This component never generates cognitive decisions, calls OPS, or
    consults any future market bars or historical full-day coverage bits.
    """

    def __init__(self) -> None:
        self._observed_opens: array = array("q")
        self._last_open: int | None = None
        self._emitted: set[tuple[str, str]] = set()

    @property
    def total_observed_m1(self) -> int:
        return len(self._observed_opens)

    def observe_closed_m1(self, *, opened_at: str, closed_at: str) -> None:
        opened, closed = minute(opened_at), minute(closed_at)
        if (
            closed - opened != 1
            or self._last_open is not None and opened <= self._last_open
        ):
            raise ValueError("M2C_REJECT_NONMONOTONIC_OR_NOT_CLOSED_M1")
        self._observed_opens.append(opened)
        self._last_open = opened

    def admit_committed_cog_event(self, case: dict[str, Any]) -> PreOpsAdmission:
        """Deny before any OPS, never use a sealed source label as policy."""
        if not case["original_G3_QORE_DTO_present_not_trade"]:
            raise ValueError("M2C_NO_POSITIVE_ORIGINAL_G3_DTO")
        at = minute(case["first_closed_M1_utc"])
        if self._last_open is None or self._last_open + 1 != at:
            raise ValueError("M2C_ORIGINAL_G3_EVENT_NOT_AT_OBSERVED_LATEST_CLOSE")
        local = datetime.fromtimestamp((at - 1) * 60, UTC).astimezone(NEW_YORK)
        session = SessionId(case["session"])
        if local.hour != VALID_HOUR[session] or local.minute != 0:
            raise ValueError("M2C_NOT_FIRST_M1_OF_SOURCE_SESSION")
        day = local.date().isoformat()
        if day != case["ny_day"]:
            raise ValueError("M2C_ASOF_DOES_NOT_MATCH_NY_LOCAL_DAY")
        key = (day, session.value)
        if key in self._emitted:
            raise ValueError("M2C_DUPLICATE_SESSION_COG_ASOF_EVENT")
        if case["native_M0_source_wait"] is not None:
            raise ValueError("M2C_COG_BYPASSED_NATIVE_SOURCE_WAIT")
        if case["nyam_h1_09_completed_at_10_if_applicable"] is not (
            True if session is SessionId.NY_AM else None
        ):
            raise ValueError("M2C_PROFILE_H1_M0_GATE_CONTRADICTION")

        state = case["M2_QORE_independent_attestation_state"]
        family = case["original_g3_draw_family"]
        reason: str
        missing: int | None = None
        if state == "REJECTED":
            if (
                not family.startswith("PRIOR_NY_CASH_SESSION_")
                or "COG_DOL_ANNOUNCED_BEFORE_SOURCE_CLOSE"
                not in case["M2_QORE_independent_attestation_reasons"]
            ):
                raise ValueError("M2C_OTHER_REJECTED_SOURCE_NOT_A_CASH_POLICY_FIXTURE")
            reason = "WAIT_CASH_CALENDAR_POLICY_UNSIGNED"
        elif state in {"CONFIRMED", "UNKNOWN"}:
            pools = [
                p for p in case["source_pool_six_independent_M1_witnesses"]
                if p["family"] == family
            ]
            if len(pools) != 1:
                raise ValueError("M2C_NO_UNIQUE_SOURCE_FAMILY")
            pool = pools[0]
            if pool["level"] is None:
                raise ValueError("M2C_POSITIVE_G3_HAS_NO_INDEPENDENT_DOL_LEVEL")
            if case["original_G3_draw_price"] != pool["level"]:
                raise ValueError("M2C_G3_AND_SOURCE_LEVEL_PRICE_CONTRADICTION")
            source_end = minute(pool["source_end"])
            if source_end >= at:
                raise ValueError("M2C_DOL_SOURCE_END_NOT_BEFORE_ASOF")
            # Only the prefix ALREADY OBSERVED through as_of exists in tape.
            stamps = self._observed_opens
            left = bisect_left(stamps, source_end)
            observed_count = len(stamps) - left
            expected_count = at - source_end
            if observed_count > expected_count:
                raise ValueError("M2C_SOURCE_COVERAGE_EXCEEDS_REAL_TIME")
            missing = expected_count - observed_count
            if state == "CONFIRMED":
                if missing != 0 or pool["state"] != "UNCONSUMED":
                    raise AssertionError("M2C_CONFIRMED_SOURCE_REAL_M1_GAP_CONTRADICTION")
                reason = "SOURCE_CONTEXT_COMPLETE_UNCERTIFIED"
            else:
                if (
                    missing <= 0
                    or pool["state"] != "UNKNOWN"
                    or pool["reason"] != "POST_SOURCE_M1_COVERAGE_GAPPED"
                ):
                    raise AssertionError("M2C_UNKNOWN_SOURCE_GAP_NOT_REPRODUCED")
                reason = "WAIT_SOURCE_M1_GAP"
        else:
            raise ValueError("M2C_ORIGINAL_POSITIVE_WITH_UNEXPECTED_SOURCE_STATE")

        self._emitted.add(key)
        return PreOpsAdmission(
            ny_day=day,
            session=session.value,
            as_of_utc=datetime.fromtimestamp(at * 60, UTC).isoformat(),
            original_g3_draw_family=family,
            source_m2_status=reason,
            independent_missing_m1=missing,
        )


def frozen_original_g3_first_m1_events(
    m2: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    """Fixture loader only. Never pass full fixture into gate state itself."""
    cohort = sealed_prior_casebook(m2)
    events: dict[int, dict[str, Any]] = {}
    for case in cohort:
        if not case["original_G3_QORE_DTO_present_not_trade"]:
            continue
        at = minute(case["first_closed_M1_utc"])
        if at in events:
            raise ValueError("M2C_DUPLICATE_DTO_ASOF_IN_FROZEN_CASEBOOK")
        events[at] = case
    if len(events) != 761:
        raise AssertionError("M2C_ORIGINAL_G3_FIRST_M1_DTO_COUNT_DRIFT")
    return events


def replay_real_m2_preops(
    market: Path, *, original_m2_casebook: Path,
) -> dict[str, Any]:
    """Full M1 market streamed chronologically; DTO fixture accessed at as_of.

    This is NOT independent reproduction of G3 decisions and is NOT live
    coordinator integration. It verifies an M2 pre-OPS research gate on
    immutable earlier G3 event fixtures under genuine causal M1 feed.
    """
    if hash_file(market) != MARKET_SHA:
        raise ValueError("M2C_ORIGINAL_NAS100_M1_SHA_MISMATCH")
    old = json.loads(original_m2_casebook.read_text(encoding="utf-8"))
    fixtures = frozen_original_g3_first_m1_events(old)
    tape = M2PreOpsResearchGate()
    outcomes: list[dict[str, Any]] = []
    for row in _stream(market):
        tape.observe_closed_m1(
            opened_at=row["opened_at"],
            closed_at=row["closed_at"],
        )
        at = minute(row["closed_at"])
        if at in fixtures:
            case = fixtures.pop(at)
            decision = tape.admit_committed_cog_event(case)
            if decision.ops_cognition is not None or decision.ops_authorized:
                raise AssertionError("M2C_UNCERTIFIED_G3_REACHED_OPS")
            outcomes.append(asdict(decision))
    if tape.total_observed_m1 != M1_TOTAL or fixtures:
        raise AssertionError("M2C_ORIGINAL_M1_OR_G3_ASOF_MISSING")
    counts = Counter(x["source_m2_status"] for x in outcomes)
    if dict(counts) != EXPECTED:
        raise AssertionError("M2C_SOURCE_ADMISSION_FALSIFIED_PREDECLARED_DISTRIBUTION")
    by_session = defaultdict(Counter)
    for x in outcomes:
        by_session[x["session"]][x["source_m2_status"]] += 1
    if set(by_session) != {x.value for x in SessionId}:
        raise AssertionError("M2C_ALL_THREE_SOURCE_WINDOWS_REQUIRED")
    source = json.dumps(outcomes, sort_keys=True, separators=(",", ":")).encode()
    return {
        "version": VERSION,
        "preregistered_before_code_commit": PREREG,
        "original_source_sha256": MARKET_SHA,
        "canonical_NAS100_M1_consumed": tape.total_observed_m1,
        "original_2325_day_session_G3_casebook_sha256": ORIGINAL_M2_CASEBOOK,
        "replay_g3_events_previously_committed_not_generated_live": True,
        "gate_receives_only_current_asof_event_and_past_M1": True,
        "pre_OPS_first_minute_761_source_cases": len(outcomes),
        "source_gate_decisions": dict(sorted(counts.items())),
        "per_session_M2_preops_decisions": {
            k: dict(sorted(v.items())) for k, v in sorted(by_session.items())
        },
        "full_761_pre_OPS_gate_casebook_sha256": sha256(source).hexdigest(),
        "full_761_pre_OPS_gate_casebook": outcomes,
        "method_source_context_complete_is_author_certified": False,
        "owner_method_profile_signed": False,
        "g3_original_cognition_replayed_live_in_this_run": False,
        "original_g3_OPS_invoked_by_this_preops_gate": False,
        "native_runtime_preops_gate_integrated": False,
        "M2_author_source_certified": False,
        "M3_M4_M5_author_certified": False,
        "M6_two_independent_human_signatures": False,
        "M7_London_NYAM_NYPM_certified": False,
        "VT31_certified": False,
        "orders": 0,
        "sizing": 0,
        "PnL": None,
        "live_demo_vps_authorized": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--original-m2-casebook", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = replay_real_m2_preops(
        args.market,
        original_m2_casebook=args.original_m2_casebook,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "M1": result["canonical_NAS100_M1_consumed"],
        "source_status": result["source_gate_decisions"],
        "session_status": result["per_session_M2_preops_decisions"],
        "casebook_sha": result["full_761_pre_OPS_gate_casebook_sha256"],
        "ops_admitted": False,
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
