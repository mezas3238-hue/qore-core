#!/usr/bin/env python3
"""VT31 original G3 COG + actual TraderLabFastForwardSchedule, 1x/32x parity.

Time compression is SIMULATED, not measured CPU speed. Retained M1 bars are
synthetic and closed. This is neither Lab L3 eligibility nor trader certification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.fast_forward import (
    TraderLabFastForwardSchedule,
    TraderLabFastForwardStep,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
)
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    source_fingerprint,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)

PREREG = "245f26d0ba4e2125924966b1c927e20f364d0bb1"
FACTOR = 32


def _canonical(data: object) -> bytes:
    return json.dumps(
        data, ensure_ascii=True, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _source_digest(history: tuple[M1Bar, ...]) -> str:
    material = [
        {
            "opened": bar.opened_at.astimezone(UTC).isoformat(),
            "closed": bar.closed_at.astimezone(UTC).isoformat(),
            "o": str(bar.open), "h": str(bar.high),
            "l": str(bar.low), "c": str(bar.close),
        }
        for bar in history
    ]
    return hashlib.sha256(_canonical(material)).hexdigest()


def native_schedule(
    bars: tuple[M1Bar, ...],
) -> TraderLabFastForwardSchedule:
    if len(bars) < 2 or any(
        current.closed_at <= previous.closed_at
        or current.opened_at < previous.closed_at
        for previous, current in zip(bars, bars[1:], strict=False)
    ):
        raise ValueError("SOURCE_BAR_CHRONOLOGY_INVALID_FOR_32X")
    return TraderLabFastForwardSchedule(
        steps=tuple(
            TraderLabFastForwardStep(
                simulated_now=bar.closed_at,
                wall_clock_advance=(
                    (bars[i+1].closed_at - bar.closed_at) / FACTOR
                    if i < len(bars)-1 else timedelta(0)
                ),
            )
            for i, bar in enumerate(bars)
        ),
        acceleration_factor=FACTOR,
    )


def _snapshot(assessment: Any) -> dict[str, Any]:
    dto = assessment.decision
    return {
        "as_of": assessment.as_of.astimezone(UTC).isoformat(),
        "session": assessment.session.value,
        "state": assessment.state,
        "missing": list(assessment.missing),
        "action": dto.side.value if dto else "WAIT",
        "target": str(dto.draw_target) if dto else None,
        "target_family": dto.draw_family if dto else None,
        "structure_level": str(dto.structure_level) if dto else None,
        "mss_confirmed_at": (
            dto.structure_break_confirmed_at.astimezone(UTC).isoformat()
            if dto else None
        ),
        "source_provenance": dto.source_provenance if dto else None,
        "research_only": assessment.research_only,
        "trade_authorized": assessment.trade_authorized,
    }


def _native_g3_replay(
    bars: tuple[M1Bar, ...],
    session: SessionId,
    *,
    fast_schedule: TraderLabFastForwardSchedule | None,
) -> dict[str, Any]:
    engine = VT31CleanroomCognition()
    observations = (
        tuple(step.simulated_now for step in fast_schedule.steps)
        if fast_schedule else tuple(x.closed_at for x in bars)
    )
    if len(observations) != len(bars):
        raise ValueError("FAST_FORWARD_M1_EVENT_COUNT_DRIFT")
    traces = []
    for i, (bar, available_at) in enumerate(
        zip(bars, observations, strict=True)
    ):
        if available_at != bar.closed_at or available_at < bar.opened_at:
            raise ValueError("COG_LOOKAHEAD_OR_INGRESS_TIME_DRIFT")
        engine.observe_closed_m1(bar)
        if i in (len(bars)-2, len(bars)-1):
            trace = _snapshot(
                engine.assess(session=session, as_of=available_at)
            )
            if trace["as_of"] != available_at.astimezone(UTC).isoformat():
                raise ValueError("COG_ASOF_BACKDATED")
            if trace["trade_authorized"] or not trace["research_only"]:
                raise ValueError("G3_EXECUTION_AUTHORITY_UNEXPECTED")
            traces.append(trace)
    if len(traces) != 2:
        raise ValueError("MISSING_JUDGMENT_PREFIX")
    return {
        "m1_source_sha256": _source_digest(bars),
        "m1_total": len(bars),
        "closed_m1_availability_visibility": "EXACT_CLOSED_AT",
        "cog_original_traces": traces,
        "cog_trace_sha256": hashlib.sha256(_canonical(traces)).hexdigest(),
    }


def _case(
    *, session: SessionId, month: int, no_mss: bool,
) -> dict[str, Any]:
    bars, at = short_fixture(session=session, month=month)
    if no_mss:
        bars = bars[:-1] + (replace(
            bars[-1], close=bars[-1].close + 3,
        ),)
    if bars[-1].closed_at != at:
        raise ValueError("SOURCE_ASOF_NOT_FROZEN")
    schedule = native_schedule(bars)
    expected_wall = (bars[-1].closed_at - bars[0].closed_at) / FACTOR
    observed_wall = sum(
        (x.wall_clock_advance for x in schedule.steps),
        timedelta(0),
    )
    if observed_wall != expected_wall or (
        tuple(x.simulated_now for x in schedule.steps)
        != tuple(x.closed_at for x in bars)
    ):
        raise ValueError("NATIVE_TRADER_LAB_FAST_FORWARD_CHRONOLOGY_DRIFT")
    normal = _native_g3_replay(bars, session, fast_schedule=None)
    accelerated = _native_g3_replay(bars, session, fast_schedule=schedule)
    if normal != accelerated:
        raise ValueError(
            f"ORIGINAL_VT31_COG_32X_BEHAVIOR_DIVERGED:{month}:{session.value}"
        )
    expected_action = "WAIT" if no_mss else "SHORT"
    actual = normal["cog_original_traces"][-1]
    if (
        actual["action"] != expected_action
        or not normal["cog_original_traces"][0]["action"] == "WAIT"
    ):
        raise ValueError(
            f"COG_PREREG_EXPECTED_JUDGMENT_DRIFT:{session.value}:"
            f"{month}:{no_mss}:{actual}"
        )
    if not no_mss and (
        actual["target"] != "80"
        or actual["structure_level"] != "96"
        or actual["mss_confirmed_at"] != at.astimezone(UTC).isoformat()
    ):
        raise ValueError("ORIGINAL_G3_SHORT_METHOD_LEVEL_DRIFT")
    return {
        "scenario": f"{session.value}_{month}_{'MSS_ABSENT' if no_mss else 'MSS_SHORT'}",
        "original_cog_invoked": True,
        "month": month, "session": session.value,
        "normal_1x": normal,
        "traderlab_simulated_32x": accelerated,
        "native_schedule_class": "TraderLabFastForwardSchedule",
        "native_schedule_all_m1_closed_instants_visited": True,
        "native_schedule_acceleration_factor": schedule.acceleration_factor,
        "normal_simulated_elapsed_microseconds": int(
            (bars[-1].closed_at - bars[0].closed_at)
            // timedelta(microseconds=1)
        ),
        "accelerated_wall_advance_microseconds": int(
            observed_wall // timedelta(microseconds=1)
        ),
        "parity_by_canonical_trace_and_source_sha256": True,
        "simulated_acceleration_not_CPU_performance": True,
        "real_traderlab_candidate_L3_certified": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "orders": 0, "trader_sizing": 0,
    }


def run_original_vt31_traderlab_timewarp() -> dict[str, Any]:
    data = [
        _case(session=session, month=month, no_mss=abstain)
        for month in (1, 7)
        for session in (SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM)
        for abstain in (False, True)
    ]
    return {
        "title": "VT31_TRADER_LAB_NATIVE_SCHEDULE_COG_REAL_1X_32X_SOURCE_PARITY",
        "prereg_commit": PREREG,
        "cog_original_sha": source_fingerprint(),
        "source_data": "SYNTHETIC_PREREG_SHORT_3_ICT_WINDOWS_TWO_DST_SEASONS",
        "cases": data,
        "all_trace_parity": all(
            x["parity_by_canonical_trace_and_source_sha256"] for x in data
        ),
        "actual_native_trader_lab_schedule_used": True,
        "native_l3_real_candidate_qualified": False,
        "speedup_measured_CPU": False,
        "methodology_certified": False, "cognition_certified": False,
        "human_cog_ops_signatures_verified": False,
        "economic_backtest_done": False,
        "return_pf_dd_sharpe_sortino": None,
        "broker_orders": 0, "sizing": 0, "live": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    out = p.parse_args().out
    result = run_original_vt31_traderlab_timewarp()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "cases": [
            (x["scenario"], x["normal_1x"]["cog_original_traces"][-1]["action"])
            for x in result["cases"]
        ],
        "parity": result["all_trace_parity"],
        "native_l3_qualified": result["native_l3_real_candidate_qualified"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
