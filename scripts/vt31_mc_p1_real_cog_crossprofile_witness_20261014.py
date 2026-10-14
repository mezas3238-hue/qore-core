#!/usr/bin/env python3
"""Adversarial actual VT31CleanroomCognition vs distinct TTrades AM context.

FIXTURES SYNTHETIC; COG output authentic from installed cleanroom production
class. This audits profile identity and causal coherence, not market PnL.
Absolutely no change to G3 COG/OPS, no trading/sizing/holdout permission.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    NEW_YORK,
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_ttrades_am_cognitive_fidelity_witness_20261014 import (
    assess_ttrades_am_context,
    ict_2023_profile_scope,
)


def _bar(
    opened: datetime, *, op: str = "100", high: str = "102",
    low: str = "98", close: str = "100.5",
) -> M1Bar:
    return M1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=1),
        open=Decimal(op), high=Decimal(high),
        low=Decimal(low), close=Decimal(close),
    )


def synthetic_real_cog_case() -> tuple[
    VT31CleanroomCognition, tuple[M1Bar, ...],
    tuple[M1Bar, ...], datetime,
]:
    """One real COG output can have NO mandatory TTrades AM 09H1 raid.

    Deliberately deterministic source-only generated M1; both 09 and 10
    windows are complete prefix and share one NY calendar day.
    """
    friday = datetime(2026, 1, 2, 9, 30, tzinfo=NEW_YORK).astimezone(UTC)
    monday = datetime(2026, 1, 5, 0, 0, tzinfo=NEW_YORK).astimezone(UTC)
    engine = VT31CleanroomCognition(framework_policy=G3_MSS_FRAMEWORK_POLICY)
    # Full prior NY cash H1/H4 as-of pools. Friday high=150 is the genuine
    # unswept draw during Monday NY AM. Never feed data from the future.
    for i in range(390):
        engine.observe_closed_m1(_bar(
            friday + timedelta(minutes=i),
            op="110", high="150" if i == 33 else "114",
            low="80" if i == 45 else "108", close="111",
        ))
    # Monday 00:00–10:00 NY: Asia 180, London 120, 05–09 240, 09–10 60.
    h9: list[M1Bar] = []
    for i in range(600):
        local = (monday + timedelta(minutes=i)).astimezone(NEW_YORK)
        bar = _bar(
            monday + timedelta(minutes=i),
            high="110" if (local.hour, local.minute) == (9, 10) else "102",
            low="90" if (local.hour, local.minute) == (9, 20) else "98",
        )
        engine.observe_closed_m1(bar)
        if local.hour == 9:
            h9.append(bar)
    source_10 = [
        ("100", "103", "99", "101"),
        ("101", "103", "100", "100.5"),
        ("101", "105", "100", "102"),
        ("101", "104", "100", "101"),
        ("101", "104", "100", "104"),
        ("101", "109", "101", "107"),
    ]
    h10: list[M1Bar] = []
    for i, (op, high, low, close) in enumerate(source_10):
        bar = _bar(
            monday + timedelta(minutes=600 + i),
            op=op, high=high, low=low, close=close,
        )
        engine.observe_closed_m1(bar)
        h10.append(bar)
    assert len(h9) == 60 and len(h10) == 6
    at = h10[-1].closed_at
    return engine, tuple(h9), tuple(h10), at


def audit_actual_cog_cross_profile() -> dict[str, object]:
    engine, h9, h10, at = synthetic_real_cog_case()
    assessment = engine.assess(session=SessionId.NY_AM, as_of=at)
    decision = assessment.decision
    # Fail the diagnostic if the future model no longer emits this decision:
    # changed producer should be reviewed, not silently treated as PASS.
    if decision is None:
        return {
            "status": "FIXTURE_DID_NOT_EMIT_MSS_REVIEW_REQUIRED",
            "cog_missing": list(assessment.missing),
            "method_certified": False,
            "cognitive_certified": False,
            "trading_authorized": False,
        }
    context = assess_ttrades_am_context(
        cognition=decision,
        previous_ny_9am=h9, current_ny_10am=h10,
    )
    return {
        "status": "ACTUAL_COG_NOT_TTRADES_AM_SOURCE_CONFORMANT",
        "fixture_market": "SYNTHETIC_UTC_M1_NO_REAL_PRICES_NO_PNL",
        "cog_decision_authentic": True,
        "cog_framework": decision.framework_policy,
        "cog_version": decision.cognitive_version,
        "cog_side": decision.side.value,
        "cog_dol_family": decision.draw_family,
        "cog_target": str(decision.draw_target),
        "cog_mss_anchor": str(decision.mss_anchor_close),
        "cog_structure_break_at": decision.structure_break_confirmed_at.isoformat(),
        "h1_9am_high": str(max(b.high for b in h9)),
        "h1_9am_low": str(min(b.low for b in h9)),
        "h1_10am_high_before_mss": str(max(b.high for b in h10)),
        "h1_10am_low_before_mss": str(min(b.low for b in h10)),
        "ttrades_am_context_state": context.status,
        "ttrades_am_rejection_reasons": list(context.reason_codes),
        "ict_general_london_9am_h1_required": ict_2023_profile_scope(
            SessionId.LONDON,
        )["9am_H1_raid_universal_required"],
        "method_certified": False,
        "cognitive_certified": False,
        "trading_authorized": False,
    }


def main() -> None:
    result = audit_actual_cog_cross_profile()
    print(json.dumps(result, sort_keys=True, indent=2))
    required = {
        "NO_PRE_SIGNAL_9AM_H1_SWEEP",
        "DOL_NOT_OPPOSITE_9AM_H1_EXTREME",
    }
    if (
        result["status"] != "ACTUAL_COG_NOT_TTRADES_AM_SOURCE_CONFORMANT"
        or result["ttrades_am_context_state"] != "REJECTED"
        or not required.issubset(set(result["ttrades_am_rejection_reasons"]))
    ):
        raise SystemExit("COG_VS_TTRADES_CROSS_PROFILE_WITNESS_NOT_REPRODUCED")


if __name__ == "__main__":
    main()
