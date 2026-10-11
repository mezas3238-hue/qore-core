"""Fail-closed H4/M15 linkage review for London LON-A (research only).

Do NOT treat a candidate series or a declared Candle2/3 label as certified.
This audit checks time, provenance, containment and raw price consistency.
Author-exact protected swing, price entry, SL, target, PnL are deliberately absent.
Source: https://ttrades.com/how-change-in-the-state-of-delivery-cisd-confirms-swing-points/
Issue #785; nested CISD may be known BEFORE its H4 closes and can only be
retrospectively assessed AFTER HTF closure, never filled at the old M15 price.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Mapping, Any

from qore.infrastructure.trader_lab.qore_london_lona_first_online_chronology_gate_v1 import _utc

IDENTITY = "LONA_GATE_A_H4_M15_CAUSAL_LINK_AUDIT_NOT_AUTHOR_EXACT"
SYMBOLS = frozenset({"EURUSD", "GBPUSD"})


def _p(value: object) -> Decimal:
    try:
        if not isinstance(value, str):
            raise ValueError("PRICE_NOT_STRING")
        out = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("INVALID_PRICE") from exc
    if not out.is_finite() or out <= 0:
        raise ValueError("INVALID_PRICE")
    return out


@dataclass(frozen=True)
class H4Reference:
    symbol: str
    provider_id: str
    opened_at_utc: str
    closed_at_utc: str
    first_known_utc: str
    high: str
    low: str
    closure_claim: str  # C2/C3/UNKNOWN: UNVERIFIED! Not a certified candle.

    def validate(self) -> None:
        if self.symbol not in SYMBOLS or not self.provider_id:
            raise ValueError("UNSUPPORTED_SYMBOL_OR_PROVIDER")
        start, end, known = (
            _utc(self.opened_at_utc), _utc(self.closed_at_utc),
            _utc(self.first_known_utc)
        )
        if end - start != timedelta(hours=4):
            raise ValueError("NOT_EXACTLY_H4_UTC_REFERENCE")
        if known < end:
            raise ValueError("H4_FUTURE_CLOSE_LEAK")
        if self.closure_claim not in {"C2", "C3", "UNKNOWN"}:
            raise ValueError("UNSUPPORTED_CLOSURE_CLAIM")
        if _p(self.low) > _p(self.high):
            raise ValueError("INVERTED_H4_RANGE")


def adjudicate_schematic_swing(
    *, symbol: str, decision_at_utc: str,
    h4: H4Reference,
    candidates: tuple[Mapping[str, Any], ...],
    direction: str,
) -> dict[str, object]:
    """Checks temporal geometry only. Even a clean link is NOT a trade.

    Each event is emitted by the observational, not author-certified, CISD
    sequence observer and must still be independently adjudicated by author.
    """
    decision = _utc(decision_at_utc)
    if direction not in {"BULLISH", "BEARISH"} or symbol not in SYMBOLS:
        raise ValueError("INVALID_DIRECTION_OR_SYMBOL")
    blockers: list[str] = []
    try:
        h4.validate()
    except ValueError as exc:
        blockers.append(f"BAD_H4_REFERENCE:{exc}")
    if h4.symbol != symbol:
        blockers.append("H4_CROSS_SYMBOL")
    if _utc(h4.first_known_utc) > decision:
        blockers.append("H4_NOT_YET_KNOWN_AT_DECISION")
    output: list[dict[str, object]] = []
    if blockers:
        return {
            "identity": IDENTITY, "status": "BLOCKED_CONTEXT",
            "blockers": sorted(set(blockers)),
            "observed_candidates": [],
            "future_candidates_ignored": 0,
            "author_exact": False, "protected_swing_certified": False,
            "entry_authorized": False, "economic_replay_authorized": False,
            "live_authorized": False,
        }

    h4_start, h4_end = _utc(h4.opened_at_utc), _utc(h4.closed_at_utc)
    ignored_future = 0
    for item in candidates:
        cid = str(item.get("candidate_id", "UNKNOWN"))
        reasons: list[str] = []
        try:
            known = _utc(str(item["cross_first_known_utc"]))
            crossing = _utc(str(item["cross_bar_close_utc"]))
            first_series = _utc(str(item["first_series_bar_open_utc"]))
            last_series_close = _utc(str(item["last_series_bar_close_utc"]))
            extreme = _p(item["raw_series_extreme_not_protected_swing"])
        except (ValueError, KeyError) as exc:
            output.append({"candidate_id": cid, "status": "REJECTED_BAD_PROVENANCE",
                           "reasons": [str(exc)], "decision_not_before_utc": None})
            continue
        if known > decision:
            ignored_future += 1
            continue
        if item.get("direction") != direction:
            reasons.append("OPPOSITE_DIRECTION")
        if item.get("source_id") != h4.provider_id:
            reasons.append("PROVIDER_ID_MISMATCH")
        if not (h4_start <= first_series < last_series_close <= crossing <= h4_end):
            reasons.append("CISD_SERIES_NOT_FULLY_INSIDE_H4")
        if known < crossing:
            reasons.append("FUTURE_M15_CLOSE_LEAK")
        if not _p(h4.low) <= extreme <= _p(h4.high):
            reasons.append("SERIES_EXTREME_OUTSIDE_H4_HIGH_LOW")
        if item.get("multiple_series_cross_same_bar") is True:
            reasons.append("MULTIPLE_SERIES_NOT_ADJUDICATED")
        if item.get("post_series_extreme_worse_before_cross") is True:
            reasons.append("EXTREME_EXTENDED_BEFORE_CROSS_NEEDS_AUTHOR_REVIEW")
        # A label supplied by upstream never independently proves C2/C3.
        if h4.closure_claim == "UNKNOWN":
            reasons.append("H4_C2_C3_CLOSURE_UNDETERMINED")
        first_tradeable_time = max(known, _utc(h4.first_known_utc), crossing)
        output.append({
            "candidate_id": cid,
            "status": "REVIEW_ONLY" if not reasons else "UNRESOLVED_CAUSAL_OR_GEOMETRY",
            "reasons": reasons,
            "decision_not_before_utc": first_tradeable_time.isoformat(),
            "m15_cross_known_utc": known.isoformat(),
            "h4_closure_known_utc": h4.first_known_utc,
            "cross_inside_closed_h4": not (
                "CISD_SERIES_NOT_FULLY_INSIDE_H4" in reasons
            ),
            "h4_c2_c3_label_unverified": True,
            "protected_swing_certified": False,
            "fill_price": None,
        })
    return {
        "identity": IDENTITY,
        "status": "OBSERVATIONAL_ONLY",
        "blockers": [],
        "observed_candidates": output,
        "future_candidates_ignored": ignored_future,
        "author_exact": False,
        "protected_swing_certified": False,
        "entry_authorized": False,
        "economic_replay_authorized": False,
        "live_authorized": False,
    }
