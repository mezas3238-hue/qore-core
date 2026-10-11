"""LON-A first-online *chronology-only* guard; never a trading strategy.

This module deliberately contains NO detectors, alpha, entry, stop, target, P&L
or authorization. It tests which timestamped evidence was knowable at decision
time. Its CLOSED_H4_SAFE_VARIANT is a *conservative QORE engineering policy*
and is NOT certified as TTrades' author-exact execution model.

Canonical London source:
https://ttrades.com/how-to-trade-london-using-ttrades-fractal-model/
Issue: https://github.com/mezas3238-hue/qore-core/issues/785
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

MODEL_ID = "LONA_TTRADES_LONDON_2026_09_12_DAILY_H4_M15"
SAFE_POLICY = "CLOSED_H4_SAFE_VARIANT_QORE_NOT_AUTHOR_EXACT"
REQUIRED = {
    "DAILY_BIAS_CLOSED": ("D1", "LA02"),
    "H4_SWING_CLOSED": ("H4", "LA05"),
    "M15_CISD_CLOSED": ("M15", "LA08"),
}
CONTEXT_ONLY = {
    "DAILY_WICK_PARTIAL": ("D1", "LA04"),
    "H4_WICK_PARTIAL": ("H4", "LA06"),
}
SYMBOLS = frozenset({"EURUSD", "GBPUSD"})


def _utc(value: str) -> datetime:
    """Reject naive and local wall clocks; never silently guess DST/broker time."""
    if not isinstance(value, str):
        raise ValueError("UTC_TIMESTAMP_REQUIRED")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_ISO_TIMESTAMP") from exc
    if instant.tzinfo is None or instant.utcoffset() != timedelta(0):
        raise ValueError("EXPLICIT_UTC_REQUIRED")
    return instant


@dataclass(frozen=True)
class Evidence:
    event_id: str
    symbol: str
    role: str
    timeframe: str
    rule_id: str
    source_id: str
    knowledge_kind: str  # CLOSED_BAR or PARTIAL_OBSERVATION
    bar_open_utc: str
    bar_close_utc: str
    observed_until_utc: str
    first_known_utc: str

    def validate(self) -> None:
        if not self.event_id or not self.source_id:
            raise ValueError("MISSING_EVENT_OR_SOURCE_ID")
        if self.symbol not in SYMBOLS:
            raise ValueError("UNSUPPORTED_SYMBOL")
        expected = REQUIRED.get(self.role) or CONTEXT_ONLY.get(self.role)
        if expected is None or (self.timeframe, self.rule_id) != expected:
            raise ValueError("UNDECLARED_ROLE_OR_MISMATCHED_RULE")
        start = _utc(self.bar_open_utc)
        end = _utc(self.bar_close_utc)
        observed = _utc(self.observed_until_utc)
        known = _utc(self.first_known_utc)
        if not start < end or not start <= observed <= end:
            raise ValueError("BAD_BAR_INTERVAL_OR_OBSERVATION_CUTOFF")
        if self.knowledge_kind == "CLOSED_BAR":
            if self.role not in REQUIRED:
                raise ValueError("WICK_PARTIAL_MUST_NOT_PRETEND_TO_BE_CLOSED")
            if observed != end or known < end:
                raise ValueError("FUTURE_BAR_CLOSE_LEAK")
        elif self.knowledge_kind == "PARTIAL_OBSERVATION":
            if self.role not in CONTEXT_ONLY:
                raise ValueError("PARTIAL_CANNOT_CERTIFY_DAILY_H4_M15")
            if observed >= end or known < observed:
                raise ValueError("FUTURE_INTRABAR_EXTREME_LEAK")
        else:
            raise ValueError("UNKNOWN_KNOWLEDGE_KIND")


def evaluate_chronology(
    *,
    symbol: str,
    decision_at_utc: str,
    evidence: Iterable[Evidence],
) -> dict[str, object]:
    """Pure snapshot. Future evidence cannot change any past decision.

    A passing snapshot proves ONLY closure availability in a conservative
    sequencing policy. It does not prove that the candle is a true protected
    swing, a CISD, a finished wick, or an economically valid setup.
    """
    decision = _utc(decision_at_utc)
    problems: list[str] = []
    if symbol not in SYMBOLS:
        problems.append("UNSUPPORTED_SYMBOL")
    visible: dict[str, Evidence] = {}
    context_visible: list[str] = []
    ignored_future = 0
    seen_event_ids: set[str] = set()
    for item in evidence:
        try:
            known = _utc(item.first_known_utc)
        except ValueError as exc:
            problems.append(f"INVALID_AVAILABLE_AT:{item.event_id}:{exc}")
            continue
        if known > decision:
            ignored_future += 1
            continue  # Critical prefix-invariance rule
        try:
            item.validate()
        except ValueError as exc:
            problems.append(f"INVALID_EVIDENCE:{item.event_id}:{exc}")
            continue
        if item.event_id in seen_event_ids:
            problems.append(f"DUPLICATE_EVENT_ID:{item.event_id}")
            continue
        seen_event_ids.add(item.event_id)
        if item.symbol != symbol:
            problems.append(f"CROSS_SYMBOL_EVIDENCE:{item.event_id}")
            continue
        if item.role in CONTEXT_ONLY:
            context_visible.append(item.event_id)
            continue
        if item.role in visible:
            problems.append(f"DUPLICATE_REQUIRED_ROLE:{item.role}")
        else:
            visible[item.role] = item
    for role in REQUIRED:
        if role not in visible:
            problems.append(f"MISSING_CONFIRMED_ROLE:{role}")
    if len(visible) == len(REQUIRED):
        order = [ _utc(visible[role].first_known_utc) for role in REQUIRED ]
        if order != sorted(order):
            problems.append("DAILY_H4_M15_CHAIN_NOT_FIRST_ONLINE")
    return {
        "model_id": MODEL_ID,
        "policy": SAFE_POLICY,
        "decision_at_utc": decision_at_utc,
        "symbol": symbol,
        "status": "CHRONOLOGY_PASS_ONLY" if not problems else "BLOCKED_CHRONOLOGY",
        "chronology_pass": not problems,
        "blockers": sorted(problems),
        "required_evidence_ids": {role: visible[role].event_id for role in REQUIRED if role in visible},
        "context_observation_ids_not_completion_proof": sorted(context_visible),
        "future_evidence_ignored": ignored_future,
        "wick_completion_certified": False,
        "cisd_geometry_certified": False,
        "author_fidelity_certified": False,
        "economic_replay_authorized": False,
        "live_authorized": False,
    }
