#!/usr/bin/env python3
"""Original VT31 G3 COG on one REAL chronological M1 stream across 3 sessions.

The M0/M1 admission decisions are ONLINE: they never see later session bars.
The 775x3 sealed prior coverage ledger is used only AFTER streaming for audit.
Research ONLY; even a positive native G3 assessment is not an ICT/TTrades
author-certified MSS or a trade.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    NEW_YORK,
    M1Bar,
    SessionId,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.operations import (
    IctSilverBulletOperations,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.trader import VT31Trader
from scripts.vt31_ict_cleanroom_cog_real_3y_fast_v1 import (
    _bar,
    _stream,
)
from scripts.vt31_trisession_real_m1_causal_coverage_20261015 import (
    _complete_hour,
    _digest,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    hash_file,
)

PREREG = "71770492abec4d4429ba69097c35570854b0beaf"
LEDGER_SHA = "7dba2c0ed15255ef1b4b5e5a277199940e785aa7e99c36a5d095bb18d4de501d"
VERSION = "VT31_TRI_SESSION_ONLINE_ORIGINAL_G3_COG_M1_ASOF_H1_WAIT_V1"
SOURCE_GAP = "SOURCE_GAP_WAIT"
SOURCE_START = "SOURCE_START_MISSING_WAIT"
SOURCE_H1 = "SOURCE_09H_INCOMPLETE_WAIT"
SESSION_HOURS = {
    3: SessionId.LONDON,
    10: SessionId.NY_AM,
    14: SessionId.NY_PM,
}


@dataclass
class SessionWitness:
    day: str
    session: SessionId
    last_m1_close: datetime | None = None
    observed_m1: int = 0
    actual_g3_invocations: int = 0
    positive_g3_observations: int = 0
    first_positive_asof: str | None = None
    first_positive_side: str | None = None
    first_positive_dol_family: str | None = None
    terminal_wait_reason: str | None = None
    h1_complete_at_10_ny: bool | None = None

    def record(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "session": self.session.value,
            "observed_m1": self.observed_m1,
            "actual_g3_invocations": self.actual_g3_invocations,
            "positive_g3_observations_not_trades": self.positive_g3_observations,
            "first_positive_asof": self.first_positive_asof,
            "first_positive_side": self.first_positive_side,
            "first_positive_dol_family": self.first_positive_dol_family,
            "online_terminal_wait_reason": self.terminal_wait_reason,
            "h1_complete_at_10_ny": self.h1_complete_at_10_ny,
            "author_method_certified": False,
            "cognition_certified": False,
            "trade_authorized": False,
            "sizing": 0,
        }


def _hour9_closed_before_10(
    day: str, nine: tuple[M1Bar, ...],
) -> bool:
    # This is evaluated at the first observed 10h M1 (its local 10:00
    # opening); 09:59 M1 closed at 10:00, never a future observation.
    return _complete_hour(day=day, hour=9, bars=nine)


def replay_online_g3(
    rows: Any, *, expected_m1: int, native_trader_g3: bool = False,
    native_strict_source_admission: bool = False,
) -> tuple[dict[tuple[str, SessionId], SessionWitness], dict[str, Any]]:
    """NO sealed ledger parameter: impossible to import future coverage.

    The ORIGINAL G3 engine is instantiated ONCE and shared across all M1 and
    all three sessions. Each research OPS is explicitly G3 (native
    VT31Trader currently bootstraps LEGACY OPS, an M7 integration blocker).
    Every market M1 enters original cognition exactly once.
    """
    if native_strict_source_admission and not native_trader_g3:
        raise ValueError("STRICT_NATIVE_ADMISSION_REQUIRES_NATIVE_G3")
    cog = VT31CleanroomCognition(
        framework_policy=G3_MSS_FRAMEWORK_POLICY,
    )
    trader = (
        VT31Trader(
            cognition=cog,
            framework_policy=G3_MSS_FRAMEWORK_POLICY,
            strict_source_admission=native_strict_source_admission,
        )
        if native_trader_g3 else None
    )
    research_ops: dict[tuple[str, SessionId], IctSilverBulletOperations] = {}
    consumed = 0
    witnesses: dict[tuple[str, SessionId], SessionWitness] = {}
    nine_hours: dict[str, list[M1Bar]] = defaultdict(list)
    previous_opened: datetime | None = None
    n = 0
    calls_by_session: Counter[str] = Counter()
    positive_by_session: Counter[str] = Counter()
    source_veto_by_session: Counter[str] = Counter()
    for row in rows:
        bar = _bar(row)
        if (
            previous_opened is not None
            and bar.opened_at <= previous_opened
        ):
            raise ValueError("G3_ONLINE_M1_DUPLICATE_OR_NON_MONOTONIC")
        previous_opened = bar.opened_at
        n += 1
        ny = bar.opened_at.astimezone(NEW_YORK)
        day = ny.date().isoformat()
        if ny.hour == 9:
            nine_hours[day].append(bar)
            if len(nine_hours[day]) > 60:
                raise ValueError("ONLINE_NY_09H_HAS_MORE_THAN_60_M1")
        session = SESSION_HOURS.get(ny.hour)
        if session is None:
            if trader is not None:
                outside = trader.on_closed_m1(bar)
                if outside.cognition is not None:
                    raise AssertionError("OUT_OF_WINDOW_COG_IN_NATIVE_G3")
            else:
                cog.observe_closed_m1(bar)
            consumed += 1
            continue
        key = (day, session)
        if key not in witnesses:
            witnesses[key] = SessionWitness(day=day, session=session)
        witness = witnesses[key]
        witness.observed_m1 += 1

        strict_result = None
        if native_strict_source_admission:
            if trader is None:
                raise AssertionError("STRICT_SOURCE_ADMISSION_NEEDS_NATIVE_TRADER")
            strict_result = trader.on_closed_m1(bar)
            consumed += 1
            if session is SessionId.NY_AM and (
                witness.h1_complete_at_10_ny is None
            ):
                witness.h1_complete_at_10_ny = (
                    strict_result.source_h1_09_complete
                )
            if strict_result.source_wait_reason is not None:
                witness.terminal_wait_reason = (
                    strict_result.source_wait_reason
                )
                source_veto_by_session[
                    f"{session.value}:{witness.terminal_wait_reason}"
                ] += 1
                witness.last_m1_close = bar.closed_at
                continue

        if not native_strict_source_admission and (
            session is SessionId.NY_AM
            and witness.h1_complete_at_10_ny is None
        ):
            witness.h1_complete_at_10_ny = _hour9_closed_before_10(
                day, tuple(nine_hours.get(day, ())),
            )
            if not witness.h1_complete_at_10_ny:
                witness.terminal_wait_reason = SOURCE_H1
        if not native_strict_source_admission and (
            witness.terminal_wait_reason is None
            and witness.last_m1_close is None
        ):
            if ny.minute != 0:
                witness.terminal_wait_reason = SOURCE_START
        elif (
            not native_strict_source_admission
            and witness.terminal_wait_reason is None
            and witness.last_m1_close != bar.opened_at
        ):
            witness.terminal_wait_reason = SOURCE_GAP

        if (
            not native_strict_source_admission
            and witness.terminal_wait_reason is not None
        ):
            # Deliberately not the original on_closed_m1: it cannot
            # bootstrap/gap a partial OPS source safely.
            if trader is not None:
                trader.research_observe_incomplete_source_m1(bar)
            else:
                cog.observe_closed_m1(bar)
            consumed += 1
            source_veto_by_session[
                f"{session.value}:{witness.terminal_wait_reason}"
            ] += 1
            witness.last_m1_close = bar.closed_at
            continue

        if trader is not None:
            result = (
                strict_result if native_strict_source_admission
                else trader.on_closed_m1(bar)
            )
            assessment = result.cognition
            if assessment is None:
                raise AssertionError("NATIVE_G3_MUST_INVOKE_COG")
            ops = trader._windows[key]
            research_ops[key] = ops
            if (
                result.observed_at != bar.closed_at
                or not result.research_only or result.order_authorized
                or result.position_authorized
            ):
                raise AssertionError("NATIVE_G3_BROKER_ORDER_OR_ASOF")
        else:
            cog.observe_closed_m1(bar)
            assessment = cog.assess(session=session, as_of=bar.closed_at)
            ops = research_ops.get(key)
            if ops is None:
                ops = IctSilverBulletOperations(
                    session=session, day=bar.opened_at,
                    framework_policy=G3_MSS_FRAMEWORK_POLICY,
                )
                research_ops[key] = ops
            ops.on_closed_m1(bar, cognition=assessment.decision)
        if not native_strict_source_admission:
            consumed += 1
        if assessment.as_of != bar.closed_at:
            raise AssertionError("G3_ONLINE_COG_ASOF_MUST_EQUAL_CLOSED_M1")
        witness.actual_g3_invocations += 1
        calls_by_session[session.value] += 1
        decision = assessment.decision
        if decision is not None:
            if decision.observed_at != bar.closed_at:
                raise AssertionError("G3_CAUSAL_DECISION_BACKDATED_OR_FUTURE")
            if decision.framework_policy != G3_MSS_FRAMEWORK_POLICY:
                raise AssertionError("WRONG_G3_ORIGINAL_COG_PROFILE")
            witness.positive_g3_observations += 1
            positive_by_session[session.value] += 1
            if witness.first_positive_asof is None:
                witness.first_positive_asof = bar.closed_at.isoformat()
                witness.first_positive_side = decision.side.value
                witness.first_positive_dol_family = decision.draw_family
        witness.last_m1_close = bar.closed_at

    if n != expected_m1 or consumed != n:
        raise AssertionError("ORIGINAL_M1_AND_ONE_G3_COG_INPUT_COUNT_DRIFT")
    if trader is not None and trader.total_closed_m1 != n:
        raise AssertionError("NATIVE_G3_ONE_TRADER_INPUT_COUNT_DRIFT")
    if any(ops.framework_policy != G3_MSS_FRAMEWORK_POLICY
           for ops in research_ops.values()):
        raise AssertionError("ORIGINAL_G3_OPS_POLICY_MISMATCH")
    return witnesses, {
        "source_bars_consumed": n,
        "one_trader": "VT31",
        "one_cognition": True,
        "framework_policy": cog.framework_policy,
        "original_ops_G3_research_windows": len(research_ops),
        "native_VT31Trader_G3_integration_complete": native_trader_g3,
        "native_strict_preCOG_M0_source_admission": native_strict_source_admission,
        "M7_blocker_native_coordinator_still_defaults_OPS_to_LEGACY": (
            not native_trader_g3
        ),
        "one_G3_COG_many_session_day_G3_OPS_research_only": True,
        "actual_original_g3_calls_all_observed_days": dict(
            sorted(calls_by_session.items())
        ),
        "actual_original_g3_positives_all_observed_days": dict(
            sorted(positive_by_session.items())
        ),
        "source_veto_M1_all_observed_days": dict(
            sorted(source_veto_by_session.items())
        ),
        "no_execution_or_sizing": True,
    }


def sealed_ledger_index(
    ledger: dict[str, Any],
) -> dict[tuple[str, SessionId], dict[str, Any]]:
    """Strictly post hoc independent ledger validation; no runtime inputs."""
    if (
        ledger.get("casebook_json_sha256") != LEDGER_SHA
        or ledger.get("source_sha256") != MARKET_SHA
        or ledger.get("total_canonical_m1") != M1_TOTAL
        or ledger.get("evaluations") != 2325
        or ledger.get("anchor_ny_am_days") != 775
        or _digest(ledger["all_2325_day_session_records"]) != LEDGER_SHA
    ):
        raise ValueError("POSTHOC_LEDGER_DATA_SHA_OR_COHORT_MISMATCH")
    index: dict[tuple[str, SessionId], dict[str, Any]] = {}
    for entry in ledger["all_2325_day_session_records"]:
        key = (entry["ny_day"], SessionId(entry["session"]))
        if key in index:
            raise ValueError("DUPLICATED_DAY_SESSION_IN_SEALED_LEDGER")
        index[key] = entry
    if (
        len(index) != 2325
        or len({day for day, _ in index}) != 775
        or any(sum(session is item for _, session in index) != 775
               for item in SessionId)
    ):
        raise ValueError("THREE_SESSION_LEDGER_INCOMPLETE")
    return index


def adjudicate_posthoc(
    traces: dict[tuple[str, SessionId], SessionWitness],
    ledger: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    """Existing ledger enters ONLY after G3 has consumed all 1M closed M1."""
    index = sealed_ledger_index(ledger)
    rows = []
    for (day, session), expected in sorted(
        index.items(), key=lambda x: (x[0][0], x[0][1].value),
    ):
        tr = traces.get((day, session), SessionWitness(day, session))
        if tr.observed_m1 != expected["observed_window_m1"]:
            raise AssertionError(
                f"ONLINE_SOURCE_VS_SEALED_LEDGER_M1_MISMATCH:{day}:{session}"
            )
        # All complete source windows MUST have exactly 60 closed-candle
        # original G3 calls, without extra calls for nonexistent minutes.
        if expected["window_m1_complete"] and (
            session is not SessionId.NY_AM
            or expected["h1_09_ttrades_complete"] is True
        ) and tr.actual_g3_invocations != 60:
            raise AssertionError(f"COMPLETE_WINDOW_G3_ASOF_CALLS_MISSING:{day}:{session}")
        if (
            session is SessionId.NY_AM
            and expected["h1_09_ttrades_complete"] is False
            and tr.actual_g3_invocations != 0
        ):
            raise AssertionError(f"NYAM_INCOMPLETE_SOURCE_H1_INVOKED_COG:{day}")
        if (
            tr.positive_g3_observations > tr.actual_g3_invocations
            or tr.actual_g3_invocations > tr.observed_m1
        ):
            raise AssertionError("COG_POSITIVES_OR_CALLS_EXCEED_SOURCE")
        rows.append({
            "ny_day": day,
            "session": session.value,
            "frozen_source_state": expected["state"],
            "frozen_source_complete": expected["window_m1_complete"],
            "frozen_h1_09_complete_if_nyam": expected["h1_09_ttrades_complete"],
            "earlier_hypothesis_in_later_incomplete_source": (
                tr.positive_g3_observations > 0
                and not expected["window_m1_complete"]
            ),
            **tr.record(),
        })

    summary: dict[str, Any] = {}
    for session in SessionId:
        its = [r for r in rows if r["session"] == session.value]
        summary[session.value] = {
            "anchor_days": len(its),
            "original_G3_cog_call_events_not_trades": sum(
                r["actual_g3_invocations"] for r in its
            ),
            "original_G3_positive_M1_observations_not_trades": sum(
                r["positive_g3_observations_not_trades"] for r in its
            ),
            "days_with_G3_positive_hypothesis_not_trades": sum(
                r["positive_g3_observations_not_trades"] > 0 for r in its
            ),
            "days_with_earlier_positive_but_later_incomplete_source": sum(
                r["earlier_hypothesis_in_later_incomplete_source"]
                for r in its
            ),
            "online_H1_veto_days": sum(
                r["online_terminal_wait_reason"] == SOURCE_H1 for r in its
            ),
            "online_window_gap_or_late_start_veto_days": sum(
                r["online_terminal_wait_reason"] in {SOURCE_GAP, SOURCE_START}
                for r in its
            ),
            "doctrine_ict_or_ttrades_certified": False,
        }
    if len(rows) != 2325:
        raise AssertionError("ONLINE_G3_THREE_SESSION_775_COHORT_DRIFT")
    return {
        "version": VERSION,
        "preregistered_before_code_commit": PREREG,
        "source_hash": MARKET_SHA,
        "prior_independent_ledger_sha": LEDGER_SHA,
        "three_sessions_online_causal_G3_diagnostics": summary,
        "runtime_single_persistent_original_G3": runtime,
        "full_2325_day_session_G3_casebook_sha256": sha256(
            json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "full_2325_day_session_G3_casebook": rows,
        "posthoc_coverage_ledger_never_used_in_online_admission": True,
        "original_G3_positive_is_research_QORE_not_author_MSS": True,
        "original_OPS_never_broker_execution": True,
        "owner_approved_profile": False,
        "author_certified_London": False,
        "author_certified_NYAM": False,
        "author_certified_NYPM": False,
        "m2_m3_m4_m5_complete": False,
        "two_human_signatures_M6": False,
        "m7_trader_certified": False,
        "trade_count": 0,
        "sizing": 0,
        "PnL_PF_DD_Sortino": None,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--market", required=True, type=Path)
    p.add_argument("--coverage-ledger", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("ORIGINAL_MARKET_AUTHENTIC_SHA_MISMATCH")
    begun = time.monotonic()
    traces, runtime = replay_online_g3(_stream(args.market), expected_m1=M1_TOTAL)
    # Post hoc only: no ledger was even loaded during online M1 replay.
    ledger = json.loads(args.coverage_ledger.read_text())
    out = adjudicate_posthoc(traces, ledger, runtime)
    out["elapsed_processing_seconds_not_economics"] = round(
        time.monotonic() - begun, 4,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "session_summary": out["three_sessions_online_causal_G3_diagnostics"],
        "casebook_sha256": out["full_2325_day_session_G3_casebook_sha256"],
        "one_trader_G3": runtime["one_trader"],
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
