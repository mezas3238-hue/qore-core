#!/usr/bin/env python3
"""Research-only, native-M1 TTrades NY AM cognitive proposal (not an order).

Source context: #929 TTrades 09 H1 witness. QORE pivot/impulse semantics
remain a named *proxy*, not a certified author instruction. Only a fresh
first return with independently attestable MSS may mint a proposed DTO.
Frozen G3 COG/OPS and source V2 are not modified.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from statistics import median
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    G3_MSS_FRAMEWORK_POLICY,
    NEW_YORK,
    CognitiveDecision,
    M1Bar,
    SessionId,
    Side,
    utc,
)
from scripts.vt31_mc_p2_ttrades_native_h1_evidence_20261014 import (
    compare_native_with_existing_cog,
    native_ttrades_am_context,
)

PROFILE = "TTRADES_NY_AM_2025"
COG_VERSION = "VT31_TTRADES_NY_AM_NATIVE_COG_V1_QORE_MSS_PROXY"
TARGET_FAMILY = "TTRADES_09H_OPPOSITE_EXTREME_QORE_PROFILE"


@dataclass(frozen=True, slots=True)
class NativeCogProposal:
    state: str
    as_of: datetime
    reasons: tuple[str, ...]
    decision: CognitiveDecision | None
    native_state: str
    independent_v2_state: str | None = None
    method_certified: bool = False
    cognition_certified: bool = False
    execution_authorized: bool = False

    def record(self) -> dict[str, Any]:
        def serialize(value: Any) -> Any:
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, tuple):
                return [serialize(x) for x in value]
            if isinstance(value, dict):
                return {k: serialize(v) for k, v in value.items()}
            return value

        return serialize(asdict(self))


def _ny_begin(at: datetime, hour: int) -> datetime:
    return at.astimezone(NEW_YORK).replace(
        hour=hour, minute=0, second=0, microsecond=0,
    ).astimezone(at.tzinfo)


def _mss_proxy(
    bars: tuple[M1Bar, ...], side: Side,
) -> tuple[Decimal, datetime] | None:
    """Latest strictly confirmed 3-M1 pivot crossed by last closed M1.

    This duplicates QORE proxy semantics for independent proposal; it does
    NOT call the original COG producer or revise frozen G3 source.
    """
    recent = bars[-95:]
    if len(recent) < 10:
        return None
    now, before = recent[-1], recent[-2]
    if utc(before.closed_at) != utc(now.opened_at):
        return None
    reference = median(
        abs(b.close - b.open) for b in recent[-7:-2]
    )
    body = abs(now.close - now.open)
    if reference <= 0 or body < reference * Decimal("1.25"):
        return None
    for i in range(len(recent) - 3, 0, -1):
        left, pivot, right = recent[i - 1:i + 2]
        if (
            utc(left.closed_at) != utc(pivot.opened_at)
            or utc(pivot.closed_at) != utc(right.opened_at)
            or utc(right.closed_at) >= utc(now.closed_at)
        ):
            continue
        if side is Side.LONG:
            if (
                pivot.high > left.high and pivot.high > right.high
                and before.close <= pivot.high < now.close
                and now.close > now.open
            ):
                return pivot.high, utc(right.closed_at)
        elif (
            pivot.low < left.low and pivot.low < right.low
            and before.close >= pivot.low > now.close
            and now.close < now.open
        ):
            return pivot.low, utc(right.closed_at)
    return None


def propose_ttrades_am_cognition(
    *, as_of: datetime, history: tuple[M1Bar, ...],
    session: SessionId = SessionId.NY_AM,
) -> NativeCogProposal:
    """Emit a research-only DTO ONLY at the fresh, closed M1 return+MSS.

    Zero COG circularity: independent original source checks run again on
    the emitted DTO. A consumer cannot turn this output into execution.
    """
    at = utc(as_of)

    def result(
        state: str, *reasons: str,
        decision: CognitiveDecision | None = None,
        native_state: str = "NOT_EVALUATED",
        v2: str | None = None,
    ) -> NativeCogProposal:
        return NativeCogProposal(
            state, at, tuple(reasons), decision, native_state, v2,
        )

    if session is not SessionId.NY_AM:
        return result("REJECTED", "PROFILE_ONLY_TTRADES_NY_AM")
    if at.second or at.microsecond:
        return result("REJECTED", "ASOF_NOT_MINUTE_ALIGNED")
    if not history:
        return result("UNKNOWN", "NO_CLOSED_M1")
    if any(utc(b.closed_at) > at for b in history):
        return result("REJECTED", "FUTURE_M1_FORBIDDEN")
    if any(
        utc(a.opened_at) >= utc(b.opened_at)
        for a, b in zip(history, history[1:], strict=False)
    ):
        return result("REJECTED", "UNORDERED_OR_DUPLICATED_M1")
    if utc(history[-1].closed_at) != at:
        return result("UNKNOWN", "LATEST_ASOF_M1_MISSING")
    start9, start10 = _ny_begin(at, 9), _ny_begin(at, 10)
    nine = tuple(
        b for b in history if start9 <= utc(b.opened_at) < start10
    )
    ten = tuple(
        b for b in history if start10 <= utc(b.opened_at) < at
    )
    native = native_ttrades_am_context(
        as_of=at, nine=nine, ten=ten,
    )
    if native.state != "RETURN_INSIDE_OBSERVED":
        state = "REJECTED" if native.state == "REJECTED" else "UNKNOWN"
        return result(state, *native.reasons, native_state=native.state)
    if native.return_inside_at != at:
        return result(
            "UNKNOWN", "RETURN_M1_NOT_FRESH_AT_ASOF",
            native_state=native.state,
        )
    if (
        native.first_sweep_at is None
        or native.first_sweep_at >= at
        or native.opposite_h1_dol is None
        or native.candidate_side not in ("LONG", "SHORT")
    ):
        return result(
            "UNKNOWN", "INCOMPLETE_NATIVE_RAID_RETURN_PROOF",
            native_state=native.state,
        )
    side = Side(native.candidate_side)
    if len(nine) != 60 or not ten:
        return result("UNKNOWN", "NATIVE_H1_M1_MISSING", native_state=native.state)
    level = _mss_proxy(nine + ten, side)
    if level is None:
        return result(
            "UNKNOWN", "QORE_MSS_PROXY_NOT_CONFIRMED_ON_FIRST_RETURN",
            native_state=native.state,
        )
    pivot_price, pivot_at = level
    try:
        decision = CognitiveDecision(
            session=SessionId.NY_AM, side=side,
            observed_at=at,
            draw_target=native.opposite_h1_dol,
            draw_family=TARGET_FAMILY,
            draw_level_observed_at=utc(nine[-1].closed_at),
            structure_level=pivot_price,
            structure_level_confirmed_at=pivot_at,
            structure_break_confirmed_at=at,
            source_provenance=(
                "TTRADES_2025_9H_RAID_RETURN_SOURCE_AND_QORE_MSS_PROXY"
            ),
            cognitive_version=COG_VERSION,
            mss_anchor_close=ten[-1].close,
            framework_policy=G3_MSS_FRAMEWORK_POLICY,
        )
    except ValueError:
        return result(
            "REJECTED", "CANDIDATE_VIOLATES_COG_DTO_CAUSAL_CONTRACT",
            native_state=native.state,
        )
    independent = compare_native_with_existing_cog(
        native=native, cognition=decision, history=nine + ten,
    )
    if independent.state != "CONTEXT_ATTESTED_NOT_CERTIFIED":
        state = (
            "REJECTED" if independent.state in
            ("REJECTED", "COG_SOURCE_REJECTED") else "UNKNOWN"
        )
        return result(
            state, *independent.reasons, native_state=native.state,
            v2=independent.v2_state,
        )
    return result(
        "CONTEXT_ATTESTED_NOT_CERTIFIED",
        "TTRADES_H1_SOURCE_AND_QORE_MSS_PROXY_CONTEXT_ONLY",
        decision=decision,
        native_state=native.state,
        v2=independent.v2_state,
    )
