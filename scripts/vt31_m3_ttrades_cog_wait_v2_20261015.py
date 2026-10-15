#!/usr/bin/env python3
"""VT31 TTrades M3 V2 cognitive WAIT state-machine; no trading decisions.

Research-only, causal stream of real closed M1. The TTrades source #929
controls raid and first-return context. QORE _mss_proxy is diagnostic only:
observing it NEVER authorizes an entry or certifies authorial displacement.
Original G3 and existing #933 native COG stay untouched.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import M1Bar, Side
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    native_ttrades_am_context,
)
from scripts.vt31_ttrades_am_method_m1_census_20261014 import (
    M1_TOTAL,
    MARKET_SHA,
    collect_hours,
    complete_hour,
    hash_file,
    market_rows,
    run_census,
)
from scripts.vt31_ttrades_am_native_cog_v1_20261014 import _mss_proxy

NY = ZoneInfo("America/New_York")
PREREG = "2d0cae42542892caff398c4d68d33cecf107f395"
MODEL = "VT31_TTRADES_AM_M3_COG_V2_WAIT_SOURCE_ONLY"
PRESET = {
    "MSS_ATTESTED_CONTEXT_ONLY": 128,
    "FIRST_RETURN_NO_QORE_MSS": 483,
    "SWEEP_NO_RETURN": 92,
    "NO_SWEEP": 65,
    "INCOMPLETE_M1_HOURS": 6,
    "REJECTED_SOURCE": 1,
}
TERMINAL = frozenset({
    "UNKNOWN_INTRABAR_OR_SOURCE", "INVALIDATED_OPPOSITE_RAID", "EXPIRED",
})


@dataclass(frozen=True, slots=True)
class CognitiveWaitSnapshot:
    state: str
    as_of: datetime | None
    source_native_state: str
    first_sweep_at: datetime | None
    first_return_at: datetime | None
    bias: str | None
    opposite_09h_dol_observed: bool
    first_qore_proxy_observed_at: datetime | None
    explicit_wait: bool
    source_profile: str = "TTRADES_NY_AM_2025"
    qore_proxy_authorial_certified: bool = False
    cognitive_decision_emitted: bool = False
    entry_authorized: bool = False
    method_certified: bool = False
    cognition_certified: bool = False


class TTradesAmWaitCognitionV2:
    """Deterministic WAIT/UNKNOWN/REJECT state, fed with *closed* M1 only."""

    def __init__(self) -> None:
        self.day: str | None = None
        self._nine: list[M1Bar] = []
        self._ten: list[M1Bar] = []
        self._last: datetime | None = None
        self._state = "UNKNOWN_INCOMPLETE_H1"
        self._source = "NOT_READY"
        self._sweep: datetime | None = None
        self._return: datetime | None = None
        self._side: str | None = None
        self._target_observed = False
        self._proxy_at: datetime | None = None

    def observe_closed_m1(self, bar: M1Bar) -> CognitiveWaitSnapshot:
        if (
            bar.opened_at.tzinfo is None
            or bar.closed_at.tzinfo is None
            or bar.closed_at-bar.opened_at != timedelta(minutes=1)
        ):
            raise ValueError("M1_CLOSED_AWARE_BAR_REQUIRED")
        opened = bar.opened_at.astimezone(UTC)
        closed = bar.closed_at.astimezone(UTC)
        if self._last is not None and opened < self._last:
            raise ValueError("DUPLICATED_OVERLAPPED_OR_OUT_OF_ORDER_M1")
        local = opened.astimezone(NY)
        day = local.date().isoformat()
        if self.day is None:
            self.day = day
        if day != self.day:
            raise ValueError("FRESH_COG_INSTANCE_REQUIRED_FOR_NEW_NY_DATE")
        if local.hour not in (9, 10):
            raise ValueError("COG_V2_REQUIRES_ONLY_09_AND_10_NY_HOURS")
        self._last = closed
        if local.hour == 9:
            if self._ten:
                raise ValueError("LATE_H1_09_M1_SOURCE_FORBIDDEN")
            self._nine.append(bar)
            return self.snapshot()
        self._ten.append(bar)
        self._evaluate_asof()
        return self.snapshot()

    def _evaluate_asof(self) -> None:
        if self._state in TERMINAL:
            return
        if self._last is None or not self._ten:
            return
        at = self._last
        if len(self._nine) != 60:
            self._state = "UNKNOWN_INCOMPLETE_H1"
            self._source = "H1_09_MISSING"
            return
        # This independently reconstructs source H1/first raid/first return.
        source = native_ttrades_am_context(
            as_of=at, nine=tuple(self._nine), ten=tuple(self._ten),
        )
        self._source = source.state
        if source.state == "REJECTED":
            self._state = "INVALIDATED_OPPOSITE_RAID"
            return
        if source.state == "UNKNOWN":
            self._state = "UNKNOWN_INTRABAR_OR_SOURCE"
            return
        if source.state == "AWAIT_SWEEP":
            self._state = "WAIT_FOR_SWEEP"
        elif source.state == "AWAIT_RETURN":
            self._state = "WAIT_FOR_RETURN"
        elif source.state == "RETURN_INSIDE_OBSERVED":
            if (
                source.candidate_side not in ("LONG", "SHORT")
                or source.opposite_h1_dol is None
                or source.return_inside_at is None
                or source.first_sweep_at is None
            ):
                self._state = "UNKNOWN_INTRABAR_OR_SOURCE"
                return
            if self._return is not None and (
                self._return != source.return_inside_at
                or self._sweep != source.first_sweep_at
                or self._side != source.candidate_side
            ):
                raise AssertionError("NATIVE_FIRST_RAID_OR_RETURN_IDENTITY_MUTATED")
            self._return = source.return_inside_at
            self._sweep = source.first_sweep_at
            self._side = source.candidate_side
            self._target_observed = True
            # QORE-specific evidence, always lower trust than author source.
            if self._proxy_at is None:
                observed = _mss_proxy(
                    tuple(self._nine+self._ten), Side(self._side),
                )
                if observed is not None:
                    self._proxy_at = at
            self._state = (
                "QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED"
                if self._proxy_at is not None else "WAIT_FOR_CONFIRMATION"
            )
        else:
            self._state = "UNKNOWN_INTRABAR_OR_SOURCE"
        # Fin de la ventana. Sin propuesta cognitiva validada de M4.
        if at.astimezone(NY).hour == 11 and self._proxy_at is None:
            self._state = "EXPIRED"

    def snapshot(self) -> CognitiveWaitSnapshot:
        """Read-only: repeated snapshot() must never change state."""
        return CognitiveWaitSnapshot(
            state=self._state, as_of=self._last,
            source_native_state=self._source, first_sweep_at=self._sweep,
            first_return_at=self._return, bias=self._side,
            opposite_09h_dol_observed=self._target_observed,
            first_qore_proxy_observed_at=self._proxy_at,
            explicit_wait=self._state in {
                "WAIT_FOR_SWEEP", "WAIT_FOR_RETURN", "WAIT_FOR_CONFIRMATION",
            },
        )


def audit_483_real_first_returns(
    groups: dict[str, dict[int, tuple[M1Bar, ...]]],
) -> dict[str, Any]:
    census = run_census(groups)
    if census["observed_days_total"] != 775 or census["state_counts"] != PRESET:
        raise AssertionError("FROZEN_COG_SOURCE_CENSUS_CHANGED")
    records: list[dict[str, Any]] = []
    first_by_class: dict[str, dict[str, Any]] = {}
    states = Counter()
    for line in census["source_classifications"]:
        if line["classification"] != "FIRST_RETURN_NO_QORE_MSS":
            continue
        day = line["ny_day"]
        nine, ten = groups[day][9], groups[day][10]
        if not (complete_hour(day, 9, nine) and complete_hour(day, 10, ten)):
            raise AssertionError("NATIVE_FROZEN_483_WITH_MISSING_H1")
        return_time = datetime.fromisoformat(line["as_of"]).astimezone(UTC)
        engine = TTradesAmWaitCognitionV2()
        for bar in nine:
            engine.observe_closed_m1(bar)
        status_at_return: CognitiveWaitSnapshot | None = None
        first_terminal: CognitiveWaitSnapshot | None = None
        for bar in ten:
            snap = engine.observe_closed_m1(bar)
            if snap.as_of == return_time:
                status_at_return = snap
            # Diagnostic event order is fixed at FIRST late proxy or expiry.
            # Continue observing through 11:00 to detect later invalidation.
            if first_terminal is None and snap.state in {
                "QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED", "EXPIRED",
            }:
                first_terminal = snap
        end = engine.snapshot()
        if first_terminal is None:
            raise AssertionError("V2_NO_FIRST_TERMINAL_SOURCE_CONTEXT")
        if (
            status_at_return is None
            or status_at_return.state != "WAIT_FOR_CONFIRMATION"
            or status_at_return.first_return_at != return_time
            or status_at_return.cognitive_decision_emitted
        ):
            raise AssertionError(
                f"V2_NOT_WAITING_ON_FIRST_RETURN_CASE day={day} "
                f"expected={return_time.isoformat()} "
                f"observed={status_at_return!r} end={end!r}"
            )
        # With no source invalidation, frozen comparative source #952 found
        # either later QORE proxy (449) or natural expiry without proxy (34).
        if first_terminal.state not in {
            "QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED", "EXPIRED",
        }:
            raise AssertionError("V2_INCONSISTENT_WITH_FROZEN_M3_CASE_STATES")
        states[first_terminal.state] += 1
        record = {
            "ny_day": day,
            "first_return_at": return_time.isoformat(),
            "v2_state_at_first_return": status_at_return.state,
            "v2_first_phase_terminal_state": first_terminal.state,
            "v2_first_phase_terminal_at": (
                first_terminal.as_of.isoformat() if first_terminal.as_of else None
            ),
            "v2_end_of_window_state": end.state,
            "v2_first_proxy_at": (
                first_terminal.first_qore_proxy_observed_at.isoformat()
                if first_terminal.first_qore_proxy_observed_at else None
            ),
            "v2_persisted_first_raid_at": (
                end.first_sweep_at.isoformat() if end.first_sweep_at else None
            ),
            "v2_persisted_bias": end.bias,
            "native_cog_method_certified": False,
            "trade_created": False,
            "case_is_evidence_not_profit": True,
        }
        records.append(record)
        first_by_class.setdefault(first_terminal.state, record)
    if len(records) != 483 or sum(states.values()) != 483:
        raise AssertionError("FROZEN_REAL_483_NOT_EXHAUSTED")
    if states != {
        "QORE_PROXY_OBSERVED_AUTHOR_DISPLACEMENT_UNVERIFIED": 449,
        "EXPIRED": 34,
    }:
        raise AssertionError("V2_STATEFUL_COG_NOT_PARITY_WITH_P3_WAIT_SOURCE")
    return {
        "model": MODEL, "prereg_sha": PREREG,
        "source_m1_sha256": MARKET_SHA,
        "source_scope": "DEVELOPMENT_ALREADY_USED_NO_OOS",
        "frozen_first_returns": 483,
        "v2_cognitive_states": dict(sorted(states.items())),
        "first_real_example_each_state": first_by_class,
        "all_real_483_cog_records": records,
        "v2_explicit_wait_implemented": True,
        "v2_never_constructs_CognitiveDecision": True,
        "v2_proxy_is_QORE_NOT_TTRADES_AUTHOR": True,
        "m3_method_certified": False,
        "m3_cognitive_certified": False,
        "m4_entry_families_certified": False,
        "m5_invalidation_certified": False,
        "m6_independent_signatures": "PENDING",
        "broker_orders_fills": 0,
        "economic_metrics": None,
        "trader_sizing": False,
        "live_authorized": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if hash_file(args.market) != MARKET_SHA:
        raise ValueError("NAS100_SHA256_SOURCE_MISMATCH")
    groups, total = collect_hours(market_rows(args.market))
    if total != M1_TOTAL:
        raise AssertionError("FROZEN_SOURCE_M1_COUNT_DRIFT")
    report = audit_483_real_first_returns(groups)
    report["source_m1_total"] = total
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({
        "source_m1_total": total,
        "frozen_first_returns": report["frozen_first_returns"],
        "v2_states": report["v2_cognitive_states"],
        "first_real_examples": report["first_real_example_each_state"],
        "m3_method_certified": report["m3_method_certified"],
        "v2_never_constructs_CognitiveDecision": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
