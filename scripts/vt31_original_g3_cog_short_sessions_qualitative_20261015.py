#!/usr/bin/env python3
"""Genuine original VT31 COG: SHORT cognition across ICT source windows/DST.

Pre-registered, qualitative M1-only cases. No order, sizing, PnL or model tuning.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    NEW_YORK,
    M1Bar,
    SessionId,
)
from scripts.vt31_cog_evidence_v2_20261014 import (
    TTRADES_AM,
    inspect_cog_evidence,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    source_fingerprint,
)

PREREG = "93d1bf72403e49cf56b3f290e149038215420709"
MSS_EXPECTED = Decimal("96")
DOL_EXPECTED = Decimal("80")


def _m1(
    open_at: datetime, *, o: str = "100", high: str = "102",
    low: str = "98", close: str = "100.5",
) -> M1Bar:
    return M1Bar(
        opened_at=open_at,
        closed_at=open_at + timedelta(minutes=1),
        open=Decimal(o), high=Decimal(high),
        low=Decimal(low), close=Decimal(close),
    )


def short_fixture(
    *, session: SessionId, month: int,
) -> tuple[tuple[M1Bar, ...], datetime]:
    """One winter + one summer deterministic source, never filtered by outcome."""
    if month not in (1, 7):
        raise ValueError("ONLY_PREREGISTERED_EST_EDT_FIXTURES")
    if session not in (SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM):
        raise ValueError("ONLY_ORIGINAL_3_ICT_SESSIONS")
    d = 5 if month == 1 else 13
    prior_d = 2 if month == 1 else 10
    prior_open = datetime(2026, month, prior_d, 9, 30, tzinfo=NEW_YORK).astimezone(UTC)
    previous = tuple(
        _m1(
            prior_open + timedelta(minutes=i), o="110",
            high="150" if i == 33 else "114",
            low="80" if i == 45 else "108", close="111",
        ) for i in range(390)
    )
    day_start = datetime(2026, month, d, 0, tzinfo=NEW_YORK).astimezone(UTC)
    source_hours = {
        SessionId.LONDON: (3, 2),
        SessionId.NY_AM: (10, 1),
        SessionId.NY_PM: (14, 1),
    }
    hour, _ = source_hours[session]
    last_m1_index = hour * 60 + (5 if session is SessionId.LONDON else 2)
    current = [
        _m1(day_start + timedelta(minutes=i))
        for i in range(last_m1_index+1)
    ]
    # Prior TTrades H1 source identity when AM only; not silently universal.
    if session in (SessionId.NY_AM, SessionId.NY_PM):
        current[550] = _m1(current[550].opened_at, high="110")
        current[560] = _m1(current[560].opened_at, low="90")

    if session is SessionId.LONDON:
        pivot_i, penultimate_i = 182, 184
        current[181] = _m1(current[181].opened_at, low="99")
        current[pivot_i] = _m1(current[pivot_i].opened_at, low="96")
        current[183] = _m1(current[183].opened_at, low="98")
        current[penultimate_i] = _m1(current[penultimate_i].opened_at, close="100")
    else:
        pivot_i = hour * 60 - 3
        current[pivot_i] = _m1(current[pivot_i].opened_at, low="96")
        # Post-09h (or pre-NYPM) high raid in 10:01 for the AM witness.
        current[last_m1_index-1] = _m1(
            current[last_m1_index-1].opened_at,
            o="104", high="111", low="103", close="105",
        )
    current[last_m1_index] = _m1(
        current[last_m1_index].opened_at,
        o="105", high="106", low="93", close="94",
    )
    stream = previous + tuple(current)
    return stream, current[-1].closed_at


def _run(
    sequence: tuple[M1Bar, ...],
    session: SessionId,
) -> tuple[VT31CleanroomCognition, Any]:
    engine = VT31CleanroomCognition()
    for bar in sequence:
        engine.observe_closed_m1(bar)
    return engine, engine.assess(session=session, as_of=sequence[-1].closed_at)


def run_short_mirror_tribunal() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for month in (1, 7):
        for session in (SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM):
            source, at = short_fixture(session=session, month=month)
            engine, assessment = _run(source, session)
            dto = assessment.decision
            if not (
                dto is not None
                and dto.side.value == "SHORT"
                and dto.draw_target == DOL_EXPECTED
                and dto.draw_family == "PRIOR_NY_CASH_SESSION_LOW"
                and dto.structure_level == MSS_EXPECTED
                and dto.structure_break_confirmed_at == at
                and assessment.research_only
                and not assessment.trade_authorized
            ):
                raise ValueError(
                    f"ORIGINAL_G3_SHORT_FAILED:{session.value}:{month}:"
                    f"{assessment.state}:{assessment.missing}:"
                    f"{dto}"
                )
            local = at.astimezone(NEW_YORK)
            offset = int(local.utcoffset().total_seconds()/3600)
            if offset != (-5 if month == 1 else -4):
                raise ValueError("US_DST_CONVERSION_MISMATCH")
            # Contrafactual varies just the final close, leaves all source
            # bars/levels/wicks unchanged; no profit information.
            no_mss = source[:-1] + (replace(source[-1], close=Decimal("97")),)
            _, no_shift = _run(no_mss, session)
            if no_shift.decision is not None:
                raise ValueError(f"SHORT_MSS_CLOSE_ONLY_CONTRAFACTUAL_FAILED:{session.value}:{month}")
            _, before = _run(source[:-1], session)
            if before.decision is not None:
                raise ValueError(f"COG_FABRICATED_SHORT_BEFORE_MSS:{session.value}:{month}")

            def after(bar: M1Bar) -> Any:
                fresh, first = _run(source, session)
                if first.decision is None:
                    raise ValueError("G3_POSITIVE_SOURCE_DISAPPEARED")
                fresh.observe_closed_m1(bar)
                return fresh.assess(session=session, as_of=bar.closed_at)

            swept = after(_m1(at, o="94", high="95", low="79", close="94"))
            rev = after(_m1(at, o="94", high="98", low="93", close="97"))
            for label, new_case in (("DOL_CONSUMED", swept), ("MSS_REVERSED", rev)):
                if new_case.decision is not None and (
                    new_case.decision.side.value == "SHORT"
                    and new_case.decision.draw_target == DOL_EXPECTED
                ):
                    raise ValueError(f"SHORT_INVALIDATION_FAILED:{label}:{session.value}:{month}")

            engine.observe_closed_m1(_m1(at, o="94", high="96", low="93", close="95"))
            stale_rejected = False
            try:
                engine.assess(session=session, as_of=at)
            except ValueError as exc:
                stale_rejected = "exactly latest closed M1" in str(exc)
            if not stale_rejected:
                raise ValueError("ORIGINAL_COG_RETROACTIVE_INPUT_NOT_REJECTED")

            ttrades: dict[str, Any] | None = None
            if session is SessionId.NY_AM:
                current = tuple(
                    bar for bar in source
                    if bar.opened_at.astimezone(NEW_YORK).date() == local.date()
                )
                nine = tuple(
                    bar for bar in current
                    if bar.opened_at.astimezone(NEW_YORK).hour == 9
                )
                ten = tuple(
                    bar for bar in current
                    if bar.opened_at.astimezone(NEW_YORK).hour == 10
                )
                native = native_ttrades_am_context(as_of=at, nine=nine, ten=ten)
                checked = inspect_cog_evidence(
                    profile=TTRADES_AM, session=session,
                    as_of=at, history=source, cognition=dto,
                )
                if not (
                    native.state == "RETURN_INSIDE_OBSERVED"
                    and native.candidate_side == "SHORT"
                    and native.opposite_h1_dol == Decimal("90")
                    and checked.state == "REJECTED"
                    and "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" in checked.rejected
                ):
                    raise ValueError(f"SHORT_TTRADES_SOURCE_CONFLICT_NOT_SEEN:{month}")
                ttrades = {
                    "native_state": native.state,
                    "ttrades_h1_target": str(native.opposite_h1_dol),
                    "original_cog_target": str(dto.draw_target),
                    "source_v2": checked.state,
                    "source_rejected_reasons": list(checked.rejected),
                    "method_claim": "TTRADES_NYAM_SHORT_NOT_SOURCE_CONFORMANT",
                }

            cases.append({
                "scenario": f"ORIGINAL_G3_{session.value}_SHORT_{month}_DST",
                "session": session.value,
                "profile_evaluated": (
                    "TTRADES_NY_AM_2025_SEPARATE_SOURCE_AUDIT"
                    if session is SessionId.NY_AM
                    else "ICT_GENERAL_2023_QORE_RUNTIME"
                ),
                "observed_as_of": at.isoformat(),
                "observed_ny": local.isoformat(),
                "observed_utc_offset": offset,
                "original_cog_side": dto.side.value,
                "original_cog_draw_family": dto.draw_family,
                "original_cog_target": str(dto.draw_target),
                "original_cog_mss_level": str(dto.structure_level),
                "original_cog_mss_at": dto.structure_break_confirmed_at.isoformat(),
                "closed_m1_count": len(source),
                "change_only_final_mss_close_to_97": "WAIT",
                "abstain_before_mss": "WAIT",
                "swept_dol_cannot_retain_original_short_80": True,
                "pivot_close_reversal_cannot_retain_original_short_80": True,
                "retroactive_asof_rejected": True,
                "ttrades_am_source_check": ttrades,
                "methodology_certified": False,
                "cognition_certified": False,
                "human_independent_reviewed": False,
                "trading_authorized": False,
            })

    return {
        "title": "ORIGINAL_VT31_G3_COG_SHORT_3_SESSIONS_EST_EDT_NO_PNL",
        "prereg_commit": PREREG,
        "original_source": source_fingerprint(),
        "original_cog_directly_invoked": True,
        "cases": cases,
        "source_fidelity_ict_general_completed": False,
        "source_fidelity_ttrades_nyam_completed": False,
        "methodology_certified": False,
        "cognitive_certified": False,
        "owner_human_cog_ops_signatures_attested": False,
        "market_3y_replayed": False,
        "economic_scores": None,
        "broker_orders": 0,
        "trader_sizing": 0,
        "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    destination = p.parse_args().out
    data = run_short_mirror_tribunal()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "tested": [[x["session"], x["observed_utc_offset"], x["original_cog_side"]]
                   for x in data["cases"]],
        "source_discrepancy_cases": [
            x["scenario"] for x in data["cases"] if x["ttrades_am_source_check"]
        ],
        "method_certified": False,
        "cog_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
