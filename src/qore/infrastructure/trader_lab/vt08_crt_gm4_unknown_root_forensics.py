"""R6 ex-post-only original Atlas V3 G-M4 UNKNOWN causal gap geometry.

Never a decision-time input. Never converts UNKNOWN into a known terminal,
nor infers fills, trades, capital, sizing, PnL or economic edge. Exactly the
preregistered V3/G-M4 identities are admitted.
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import ReplayBar
from qore.infrastructure.trader_lab.vt08_crt_three_source_v1_full_h4_census import (
    H4,
    M5,
    _aggregate,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

SCHEMA = "qore.vt08.crt.gm4_unknown_root_causal_gap_forensics.r6.v1"
MISSING = "UNKNOWN_MISSING_M5_BEFORE_TERMINAL"
BEYOND = "UNKNOWN_ENTRY_ALREADY_BEYOND_BARRIER"


def _utc_iso(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("missing GM4 forensic clock")
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("GM4 forensic timestamps must have timezone")
    return stamp.astimezone(UTC)


def diagnose_gm4_unknowns_expost(
    market: CrtPureMarket,
    bars: tuple[ReplayBar, ...],
    source_rows: tuple[dict[str, Any], ...],
    gm4_rows: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Retrospective causes only. Never pass output to G7 initial decision."""
    if market not in (CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY):
        raise ValueError("BTCUSD original Atlas analysis frozen")
    m5: dict[datetime, ReplayBar] = {}
    for bar in bars:
        stamp = bar.opened_at.astimezone(UTC)
        if stamp in m5:
            raise ValueError("duplicate M5 in retrospective GM4 witness")
        m5[stamp] = bar
    sources = {s["source_event_id"]: s for s in source_rows}
    if len(sources) != len(source_rows):
        raise ValueError("duplicate V3 source in retrospective GM4 witness")
    if {r["source_event_id"] for r in gm4_rows} != set(sources):
        raise ValueError("GM4 source identities do not match frozen V3")

    diagnosed: list[dict[str, Any]] = []
    outcomes: Counter[str] = Counter()
    subtypes: Counter[str] = Counter()
    for row in gm4_rows:
        eid = row["source_event_id"]
        if row["market"] != market.value or row["not_a_trade"] is not True:
            raise ValueError("GM4 evidence market or trade identity invalid")
        if row["no_PnL_or_sizing"] is not True or row["G_M4_PASS"] is not False:
            raise ValueError("GM4 forged profit, sizing or approval")
        if row["terminal_observation_proven"] is not False:
            continue
        if row["terminal_observed_at_utc"] is not None:
            raise ValueError("UNKNOWN may not have observed terminal timestamp")
        outcome = row["price_path_outcome_only_post_decision"]
        if outcome not in (MISSING, BEYOND):
            raise ValueError("unexpected G-M4 UNKNOWN category; require adjudication")
        source = sources[eid]
        clock = _utc_iso(row["source_decision_clock_utc"])
        c3 = _utc_iso(row["parent_c3_utc"])
        if (
            source["market"] != market.value
            or _utc_iso(source["decision_clock_utc"]) != clock
            or _utc_iso(source["c3_H4_opened_at_utc"]) != c3
            or not c3 < clock < c3 + H4
        ):
            raise ValueError("GM4 forensic source/decision clock mismatch")
        diagnosis: dict[str, Any] = {
            "schema": SCHEMA,
            "market": market.value,
            "source_event_id": eid,
            "source_decision_clock_utc": clock.isoformat(),
            "parent_c3_utc": c3.isoformat(),
            "gm4_frozen_unknown_category": outcome,
            "gm4_terminal_remains_UNKNOWN": True,
            "forensics_is_expost_only": True,
            "not_a_trade": True,
            "no_sizing": True,
            "no_capital_authority": True,
            "G_M4_PASS": False,
        }
        if outcome == BEYOND:
            entry_bar = m5.get(clock)
            if entry_bar is None:
                raise ValueError("GM4 BEYOND_BARRIER requires decision M5 open")
            c1_start = c3 - 2 * H4
            c1_m5 = tuple(m5.get(c1_start + i * M5) for i in range(48))
            if any(bar is None for bar in c1_m5):
                raise ValueError("GM4 case lacks frozen H4 C1")
            c1 = _aggregate(tuple(item for item in c1_m5 if item is not None))
            target_double = c1["high_relative"] + c1["low_relative"]
            invalidation = int(source["structural_invalidation_price_if_candidate"])
            entry = entry_bar.open_price
            direction = source["parent_direction"]
            if direction == "BULLISH":
                beyond_stop = entry <= invalidation
                beyond_target = 2 * entry >= target_double
            elif direction == "BEARISH":
                beyond_stop = entry >= invalidation
                beyond_target = 2 * entry <= target_double
            else:
                raise ValueError("unknown frozen source direction")
            if not (beyond_stop or beyond_target):
                raise ValueError("G-M4 entry BEYOND_BARRIER not reproduced on M5")
            subtype = (
                "BOTH_BARRIERS" if beyond_stop and beyond_target
                else "ALREADY_BEYOND_INVALIDATION" if beyond_stop
                else "ALREADY_BEYOND_DESTINATION"
            )
            diagnosis["observed_issue"] = subtype
            diagnosis["decision_m5_present"] = True
        else:
            first_missing = next(
                (c3_bar for i in range(int((c3 + H4 - clock) / M5))
                 if (c3_bar := clock + i * M5) not in m5),
                None,
            )
            if first_missing is None:
                raise ValueError("G-M4 missing M5 not reproduced in C3 clock")
            previous = first_missing - M5
            next_seen = next(
                (stamp for i in range(
                    1, int((c3 + H4 - first_missing) / M5)
                ) if (stamp := first_missing + i * M5) in m5),
                None,
            )
            diagnosis["observed_issue"] = "SOURCE_M5_GAP"
            diagnosis["first_missing_original_m5_opened_at_utc"] = (
                first_missing.isoformat()
            )
            diagnosis["previous_m5_present"] = previous in m5
            diagnosis["next_original_m5_opened_at_within_C3_utc"] = (
                next_seen.isoformat() if next_seen is not None else None
            )
            diagnosis["gap_does_not_prove_price_path"] = True
            subtype = "SOURCE_M5_GAP"
        outcomes[outcome] += 1
        subtypes[subtype] += 1
        diagnosed.append(diagnosis)

    return {
        "schema": SCHEMA,
        "market": market.value,
        "unknown_cases": len(diagnosed),
        "unknown_frozen_reasons": dict(sorted(outcomes.items())),
        "observed_geometry_gap_subtypes": dict(sorted(subtypes.items())),
        "EX_POST_ONLY_NOT_CAUSAL_DECISION": True,
        "GM4_unknown_still_unresolved": len(diagnosed),
        "G_M4_PASS": False,
        "G_M5_ISSUED": False,
        "GLOBAL_CERTIFIED": False,
        "no_sizing": True,
        "not_a_trade": True,
    }, tuple(diagnosed)
