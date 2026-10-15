#!/usr/bin/env python3
"""Genuine VT31 G3 COG NY-PM qualitative behavior, NOT PnL or certification."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
)
from scripts.vt31_cog_evidence_v2_20261014 import ICT_GENERAL, TTRADES_AM
from scripts.vt31_m0_profile_shadow_attestation_20261015 import (
    classify_source_profile,
)
from scripts.vt31_original_cog_nyam_ttrades_source_conflict_20261014 import (
    bar,
    nyam_source_fixture,
)
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    source_fingerprint,
)

PREREG = "d2cfef4ea238c34f479bd104a03853136f8c66e0"
NY = ZoneInfo("America/New_York")


def ny_pm_original_fixture() -> tuple[tuple[M1Bar, ...], datetime]:
    """Frozen synthetic NYC day through 14:03, causal G3-compatible stream."""
    source, _, ten = nyam_source_fixture()
    prior = source[:390]
    day_before_10 = source[390:-3]
    start10 = ten[0].opened_at
    between = [
        bar(start10 + timedelta(minutes=i)) for i in range(240)
    ]
    between[237] = bar(between[237].opened_at, high="104")
    first_pm = (
        bar(start10 + timedelta(minutes=240), close="100"),
        bar(start10 + timedelta(minutes=241),
            o="96", high="99", low="89", close="95"),
        bar(start10 + timedelta(minutes=242),
            o="94", high="106", low="93", close="105"),
    )
    history = prior + day_before_10 + tuple(between) + first_pm
    return history, first_pm[-1].closed_at


def _engine(history: tuple[M1Bar, ...]) -> VT31CleanroomCognition:
    obj = VT31CleanroomCognition()
    for closed in history:
        obj.observe_closed_m1(closed)
    return obj


def _observation(
    cog: VT31CleanroomCognition, at: datetime,
) -> dict[str, Any]:
    evidence = cog.assess(session=SessionId.NY_PM, as_of=at)
    d = evidence.decision
    return {
        "as_of": at.isoformat(),
        "local_NY_time": at.astimezone(NY).isoformat(),
        "source_state": evidence.state,
        "decision": d.side.value if d else "WAIT",
        "missing": list(evidence.missing),
        "draw_target": str(d.draw_target) if d else None,
        "draw_family": d.draw_family if d else None,
        "mss_level": str(d.structure_level) if d else None,
        "mss_confirmed_at": d.structure_break_confirmed_at.isoformat() if d else None,
        "available_htf": list(evidence.verified_htf),
        "cognition_research_only": evidence.research_only,
        "trade_authorized": evidence.trade_authorized,
    }


def genuine_nypm_cognitive_dossier() -> dict[str, Any]:
    stream, at = ny_pm_original_fixture()
    cog = _engine(stream)
    positive = _observation(cog, at)
    if not (
        positive["decision"] == "LONG"
        and positive["draw_target"] == "150"
        and positive["draw_family"] == "PRIOR_NY_CASH_SESSION_HIGH"
        and positive["mss_level"] == "104"
        and positive["mss_confirmed_at"] == at.isoformat()
        and positive["trade_authorized"] is False
        and "M15" in positive["available_htf"]
        and "H1" in positive["available_htf"]
    ):
        raise ValueError("ACTUAL_ORIGINAL_G3_NYPM_COG_CONTEXT_DID_NOT_CONFORM")
    original_assessment = cog.assess(session=SessionId.NY_PM, as_of=at)
    ict = classify_source_profile(
        selected_profile=ICT_GENERAL, session=SessionId.NY_PM,
        as_of=at, closed_m1=stream, assessment=original_assessment,
    )
    inappropriate = classify_source_profile(
        selected_profile=TTRADES_AM, session=SessionId.NY_PM,
        as_of=at, closed_m1=stream, assessment=original_assessment,
    )
    if (
        ict.state != "ICT_CONTEXT_WITNESS_UNDERDETERMINED"
        or inappropriate.state != "PROFILE_SESSION_REJECTED"
    ):
        raise ValueError("NYPM_METHOD_PROFILE_SCOPE_CONFLATED")

    early = _observation(_engine(stream[:-1]), stream[-2].closed_at)
    if early["decision"] != "WAIT" or (
        "CONFIRMED_DISPLACEMENT_MSS" not in early["missing"]
    ):
        raise ValueError("NYPM_EARLY_COG_FAKES_CONFIRMED_MSS")

    incomplete = tuple(
        b for b in stream
        if b.opened_at < stream[390].opened_at
        or (b.opened_at >= stream[390].opened_at
            and b.opened_at < stream[390 + 600].opened_at)
        or b.opened_at >= stream[-3].opened_at
    )
    lacking_htf = _observation(_engine(incomplete), at)
    if not (
        lacking_htf["decision"] == "WAIT"
        and "M15_CLOSED_CONTEXT" in lacking_htf["missing"]
        and "H1_CLOSED_CONTEXT" in lacking_htf["missing"]
    ):
        raise ValueError("NYPM_COG_FAKES_MISSING_CONTEMPORARY_HTF")

    after_dol = bar(at, o="105", high="151", low="104", close="110")
    swept = _engine(stream)
    swept.observe_closed_m1(after_dol)
    target_gone = _observation(swept, after_dol.closed_at)
    if target_gone["decision"] != "WAIT":
        raise ValueError("NYPM_COG_REUSED_ALREADY_SWEPT_DOL")
    after_reversal = bar(at, o="105", high="106", low="100", close="102")
    reversed_engine = _engine(stream)
    reversed_engine.observe_closed_m1(after_reversal)
    revoked = _observation(reversed_engine, after_reversal.closed_at)
    if revoked["decision"] != "WAIT":
        raise ValueError("NYPM_COG_IGNORED_PIVOT_INVALIDATION")

    future = _engine(stream)
    future.observe_closed_m1(bar(at, o="105", high="107", low="104", close="106"))
    late_error = None
    try:
        future.assess(session=SessionId.NY_PM, as_of=at)
    except ValueError as exc:
        late_error = str(exc)
    if late_error is None or "exactly latest closed M1" not in late_error:
        raise ValueError("NYPM_COG_BACKDATED_AFTER_FUTURE_M1")

    cases = [
        {"case": "NYPM_LONG_SOURCE_DOL", **positive},
        {"case": "NYPM_WAIT_NO_MSS", **early},
        {"case": "NYPM_WAIT_STALE_HTF", **lacking_htf},
        {"case": "NYPM_WAIT_DOL_CONSUMED", **target_gone},
        {"case": "NYPM_WAIT_MSS_REVERSED", **revoked},
        {"case": "NYPM_REJECT_RETRO_ASOF", "decision": "REJECT",
         "reason": late_error, "as_of": at.isoformat(),
         "trade_authorized": False},
    ]
    return {
        "title": "VT31_ACTUAL_G3_NYPM_COG_QUALITATIVE_METHOD_PROFILE_CASES",
        "prereg_commit": PREREG,
        "original_g3_source_hash": source_fingerprint(),
        "real_original_cog_invoked": True,
        "session": SessionId.NY_PM.value,
        "cases": cases,
        "source_profile_ict_general_state": ict.state,
        "source_profile_ttrades_state": inappropriate.state,
        "source_claim_author_certified": False,
        "cognitive_certified": False,
        "methodology_certified": False,
        "reviewer_signatures": False,
        "trade_count_or_pnl": None,
        "orders_executed": 0,
        "trader_sizing": 0,
        "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    out = p.parse_args().out
    report = genuine_nypm_cognitive_dossier()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": [(x["case"], x["decision"]) for x in report["cases"]],
        "profile_ict": report["source_profile_ict_general_state"],
        "profile_ttrades": report["source_profile_ttrades_state"],
        "cognitive_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
