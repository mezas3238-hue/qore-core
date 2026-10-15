#!/usr/bin/env python3
"""Original VT31 G3 COG versus TTrades NY-AM source: SEMANTIC contradiction.

Synthetic closed M1 facts, *actual* VT31CleanroomCognition producer, and
independent TTrades attester. No PnL, sizing, broker order, live or tuning.
"""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.cognition import (
    VT31CleanroomCognition,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
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
    london_fixture,
    source_fingerprint,
)

PREREG = "6ed6fb5e43d86b1457766a701a49f07b4f06ea88"
NY = ZoneInfo("America/New_York")


def bar(
    opened_at: datetime, *, o: str = "100", high: str = "102",
    low: str = "98", close: str = "100.5",
) -> M1Bar:
    return M1Bar(
        opened_at, opened_at + timedelta(minutes=1),
        Decimal(o), Decimal(high), Decimal(low), Decimal(close),
    )


def nyam_source_fixture() -> tuple[
    tuple[M1Bar, ...], tuple[M1Bar, ...], tuple[M1Bar, ...],
]:
    """Exact H1 opposite high 110 vs previous NY cash high 150."""
    prior_all, _ = london_fixture()
    prior = prior_all[:390]
    current_start = datetime(2026, 1, 5, 0, tzinfo=NY).astimezone(UTC)
    current = [
        bar(current_start + timedelta(minutes=i))
        for i in range(600)
    ]
    # 09:00-10:00 NY is indexes 540:600 of current calendar day.
    current[550] = bar(current[550].opened_at, high="110")
    current[560] = bar(current[560].opened_at, low="90")
    current[597] = bar(current[597].opened_at, high="104")
    nine = tuple(current[540:600])
    ten = (
        bar(current_start + timedelta(minutes=600), close="100"),
        bar(
            current_start + timedelta(minutes=601),
            o="96", high="99", low="89", close="95",
        ),
        bar(
            current_start + timedelta(minutes=602),
            o="94", high="106", low="93", close="105",
        ),
    )
    return prior + tuple(current) + ten, nine, ten


def original_nyam_source_conflict() -> dict:
    original_stream, nine, ten = nyam_source_fixture()
    at = ten[-1].closed_at
    native = native_ttrades_am_context(as_of=at, nine=nine, ten=ten)
    if (
        native.state != "RETURN_INSIDE_OBSERVED"
        or native.candidate_side != "LONG"
        or native.opposite_h1_dol != Decimal("110")
        or native.first_sweep_at != ten[1].closed_at
        or native.return_inside_at != at
    ):
        raise ValueError("INDEPENDENT_TTRADES_NYAM_SOURCE_WITNESS_NOT_EXPECTED")

    engine = VT31CleanroomCognition()
    for x in original_stream:
        engine.observe_closed_m1(x)
    observed = engine.assess(session=SessionId.NY_AM, as_of=at)
    dto = observed.decision
    if dto is None:
        raise ValueError(
            "ORIGINAL_NYAM_COG_HAS_NO_DECISION:"
            + repr(observed.missing)
        )
    if dto.draw_target != Decimal("150"):
        raise ValueError(
            "ORIGINAL_G3_NYAM_DOL_CHANGED_FROM_FROZEN_EXPECTATION:"
            + str(dto.draw_target)
        )
    if dto.structure_break_confirmed_at != at:
        raise ValueError("ORIGINAL_MSS_ANCHOR_NOT_ASOF")
    source_check = inspect_cog_evidence(
        profile=TTRADES_AM,
        session=SessionId.NY_AM,
        as_of=at,
        history=original_stream,
        cognition=dto,
    )
    if (
        source_check.state != "REJECTED"
        or "DOL_NOT_OPPOSITE_9AM_H1_EXTREME" not in source_check.rejected
    ):
        raise ValueError("TTRADES_INDEPENDENT_DOL_DISAGREEMENT_NOT_FALSIFIED")
    assert not observed.trade_authorized and observed.research_only
    return {
        "prereg_commit": PREREG,
        "original_g3_cog_code_sha": source_fingerprint(),
        "original_engine_called_not_a_proxy": True,
        "session": "NY_AM",
        "profile_under_author_source_audit": "TTRADES_NY_AM_2025",
        "as_of": at.isoformat(),
        "as_of_ny": at.astimezone(NY).isoformat(),
        "current_ny9_h1_high": str(max(x.high for x in nine)),
        "current_ny9_h1_low": str(min(x.low for x in nine)),
        "first_low_raid_closed_at": ten[1].closed_at.isoformat(),
        "return_mss_closed_at": at.isoformat(),
        "observed_actual_original_cog_state": observed.state,
        "observed_actual_original_cog_side": dto.side.value,
        "observed_actual_original_cog_dol": str(dto.draw_target),
        "observed_actual_original_cog_dol_family": dto.draw_family,
        "observed_actual_original_cog_pivot": str(dto.structure_level),
        "observed_actual_original_cog_provenance": dto.source_provenance,
        "ttrades_independent_source_context_state": native.state,
        "ttrades_source_side": native.candidate_side,
        "ttrades_source_required_opposite_h1_dol": str(
            native.opposite_h1_dol
        ),
        "independent_source_v2_state": source_check.state,
        "independent_source_v2_rejections": list(source_check.rejected),
        "methodology_profile_qualitative_verdict":
            "TTRADES_NYAM_DOL_SOURCE_NONCONFORMANT",
        "ict_general_dol_logic_independently_falsified": False,
        "cog_temporal_inference_functional_for_this_case": True,
        "cog_ttrades_author_fidelity_certified": False,
        "cog_overall_certified": False,
        "methodology_overall_certified": False,
        "operator_orders": 0, "lot_sizing": 0,
        "financial_evidence": None,
        "market_replay_3y_used": False,
        "live_authorized": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = original_nyam_source_conflict()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        k: result[k] for k in (
            "observed_actual_original_cog_side",
            "observed_actual_original_cog_dol",
            "ttrades_source_required_opposite_h1_dol",
            "methodology_profile_qualitative_verdict",
        )
    }, sort_keys=True))


if __name__ == "__main__":
    main()
