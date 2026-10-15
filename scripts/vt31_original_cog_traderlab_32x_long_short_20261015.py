#!/usr/bin/env python3
"""Read-only genuine VT31 COG 1x/32x native Trader Lab LONG+SHORT semantic parity.

The reflection is a preregistered SYNTHETIC structural mirror. Never measured
CPU acceleration, never source fidelity authorization, broker fill or Lab L3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from datetime import UTC, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
)
from scripts.vt31_original_cog_trader_lab_fast_forward_20261015 import (
    FACTOR,
    _canonical,
    _native_g3_replay,
    native_schedule,
)
from scripts.vt31_original_g3_cog_qualitative_court_20261014 import (
    source_fingerprint,
)
from scripts.vt31_original_g3_cog_short_sessions_qualitative_20261015 import (
    short_fixture,
)

PREREG = "38030ba2d8cabbf73fa1c2c2c5d3b7d7cf67961f"
MIRROR_CENTER = Decimal("230")


def mirror_long_history(
    short_history: tuple[M1Bar, ...],
) -> tuple[M1Bar, ...]:
    """Reflect each OHLC without touching timestamp/order/conditional results."""
    return tuple(
        M1Bar(
            opened_at=bar.opened_at, closed_at=bar.closed_at,
            open=MIRROR_CENTER-bar.open,
            high=MIRROR_CENTER-bar.low,
            low=MIRROR_CENTER-bar.high,
            close=MIRROR_CENTER-bar.close,
        )
        for bar in short_history
    )


def case(
    *, session: SessionId, month: int, side: Side, no_mss: bool,
) -> dict[str, Any]:
    short_bars, as_of = short_fixture(session=session, month=month)
    bars = mirror_long_history(short_bars) if side is Side.LONG else short_bars
    if no_mss:
        # Only the last close changes; wick extrema and source are fixed.
        bars = bars[:-1] + (
            replace(bars[-1], close=Decimal(
                "133" if side is Side.LONG else "97"
            )),
        )
    if bars[-1].closed_at != as_of:
        raise ValueError("PREREG_M1_LAST_ASOF_MISMATCH")
    schedule = native_schedule(bars)
    native_clock = tuple(x.simulated_now for x in schedule.steps)
    if native_clock != tuple(x.closed_at for x in bars):
        raise ValueError("TRADERLAB_NATIVE_AVAILABILITY_MISMATCH")
    sim_elapsed = bars[-1].closed_at - bars[0].closed_at
    compressed = sum(
        (x.wall_clock_advance for x in schedule.steps), timedelta(0),
    )
    if compressed*FACTOR != sim_elapsed:
        raise ValueError("TRADERLAB_SIMULATED_TIME_COMPRESSION_NOT_32X")
    seq = _native_g3_replay(bars, session, fast_schedule=None)
    ff = _native_g3_replay(bars, session, fast_schedule=schedule)
    if seq != ff:
        raise ValueError(
            f"ORIGINAL_COG_STATE_OR_SOURCE_DRIFT_32X:"
            f"{session.value}:{month}:{side.value}:{no_mss}"
        )
    a, z = seq["cog_original_traces"]
    expected = "WAIT" if no_mss else side.value
    if a["action"] != "WAIT" or z["action"] != expected:
        raise ValueError(
            f"ORIGINAL_G3_COG_EXPECTED_JUDGMENT_FAILED:"
            f"{session.value}:{month}:{side.value}:{no_mss}:"
            f"{a['action']}->{z['action']}:{z['missing']}"
        )
    if not no_mss:
        target = "150" if side is Side.LONG else "80"
        pivot = "134" if side is Side.LONG else "96"
        if (
            z["target"] != target or z["structure_level"] != pivot
            or z["mss_confirmed_at"] != as_of.astimezone(UTC).isoformat()
            or z["target_family"] != (
                "PRIOR_NY_CASH_SESSION_HIGH"
                if side is Side.LONG else "PRIOR_NY_CASH_SESSION_LOW"
            )
        ):
            raise ValueError(
                f"ORIGINAL_COG_PIVOT_OR_DOL_NOT_SYMMETRIC:"
                f"{session.value}:{month}:{side.value}:{z}"
            )
    if any(x["trade_authorized"] or not x["research_only"] for x in (a,z)):
        raise ValueError("G3_COG_ORIGINAL_ISSUED_TRADING_AUTHORITY")
    return {
        "identity": f"{session.value}_{month}_{side.value}_"
                    f"{'NO_MSS_WAIT' if no_mss else 'MSS_CONFIRMED'}",
        "session": session.value, "month": month, "side": side.value,
        "mirror_source": side is Side.LONG,
        "counterfactual_change_only_last_close": no_mss,
        "m1_count": len(bars),
        "m1_sha256": seq["m1_source_sha256"],
        "trace_sha256": seq["cog_trace_sha256"],
        "original_cog_trace_before_and_after": seq["cog_original_traces"],
        "ff_canonical_source_and_trace_identical": seq == ff,
        "ff_acceleration_factor_simulated": schedule.acceleration_factor,
        "ff_all_m1_closed_at_preserved": True,
        "elapsed_normal_us": int(
            sim_elapsed // timedelta(microseconds=1)
        ),
        "elapsed_simulated_ff_us": int(
            compressed // timedelta(microseconds=1)
        ),
        "qualified_vt31_trader_lab_L3": False,
        "certified_author_method": False, "certified_cognition": False,
        "orders": 0, "trader_sizing": 0,
    }


def bidirectional_dossier() -> dict[str, Any]:
    cases = [
        case(session=s, month=m, side=side, no_mss=absent)
        for m in (1, 7)
        for s in (SessionId.LONDON, SessionId.NY_AM, SessionId.NY_PM)
        for side in (Side.LONG, Side.SHORT)
        for absent in (False, True)
    ]
    if len(cases) != 24 or len({x["identity"] for x in cases}) != 24:
        raise ValueError("EXPECTED_24_DISTINCT_PRE_REGISTERED_SCENARIOS")
    digest = hashlib.sha256(_canonical(cases)).hexdigest()
    return {
        "title": "VT31_TRADERLAB_NATIVE_32X_ORIGINAL_COG_24_SCENARIO_PARITY",
        "prereg_commit": PREREG,
        "original_g3_code_sha": source_fingerprint(),
        "cases": cases,
        "dataset": "SYNTHETIC_PRESPECIFIED_NOT_3Y_MARKET",
        "cases_causal_trace_sha256": digest,
        "all_24_parity": all(
            x["ff_canonical_source_and_trace_identical"] for x in cases
        ),
        "native_traderlab_schedule_used": True,
        "observed_CPU_speedup_32x": False,
        "qualified_real_vt31_L3": False,
        "methodology_certified": False,
        "cognition_certified": False,
        "dual_cog_ops_signatures_verified": False,
        "economic_metrics": None, "live_authorized": False,
        "broker_orders": 0, "sizing": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    out = p.parse_args().out
    record = bidirectional_dossier()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True)+"\n")
    print(json.dumps({
        "cases": len(record["cases"]),
        "short": sum(x["side"]=="SHORT" for x in record["cases"]),
        "long": sum(x["side"]=="LONG" for x in record["cases"]),
        "wait": sum(
            x["counterfactual_change_only_last_close"]
            for x in record["cases"]
        ),
        "all_equal": record["all_24_parity"],
        "certified": record["methodology_certified"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
