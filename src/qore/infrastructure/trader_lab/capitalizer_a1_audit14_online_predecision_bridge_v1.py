"""Outcome-blind, source-anchored Audit14 -> A1 first-online evidence boundary.

Audit14's paired rows contain realized gross R and exit reasons. This bridge
NEVER reads, serializes, or forwards those fields to the cognitive decision.
It does not replace the V49 source-universe generator or authorize PAPER orders:
the upstream H1/M15 population is still V49-anchored and the independent native
M1 close, broker BID/ASK, author POI, and full nine-market world are unproven.

This module specifically prepares for A1 to consider B's changed first-online
clock without mislabeling frozen V49 fills as online Master Frame outcomes.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_v50_g_causal_decision_trace import (
    source_opportunity_id,
)

IDENTITY = "QORE_SCALPER_A1_AUDIT14_ONLINE_OUTCOME_BLIND_HANDOFF_V1"
FAMILIES = frozenset(("LIQUIDITY_SWEEP_CISD", "FVG_RETRACE_CISD"))
STATUSES = frozenset((
    "ELIGIBLE", "OUTSIDE_SOURCE_SESSION", "OUTSIDE_DEVELOPMENT_WINDOW",
    "INVALID_M15_STOP_AT_ONLINE_CLOSE",
    "NO_UNTOUCHED_H1_OBJECTIVE_AT_ONLINE_CLOSE",
    "NO_SESSION_M1_AFTER_ONLINE_ENTRY", "ECONOMIC_REPLAY_UNAVAILABLE",
))
# Exact source-side Audit14 schema. Ex-post columns must remain present for
# pairing/integrity, but they are NEVER accessed or included in the projection.
AUDIT14_FIELDS = frozenset((
    "source_opportunity_id", "symbol", "session", "operating_date",
    "v49_entry_at", "online_entry_at", "online_family", "source_family",
    "frozen_381", "first_online_differs", "status",
    "rejection_is_diagnostic_not_a_hard_veto",
    "original_gross_r", "candidate_gross_r", "candidate_entry_price",
    "candidate_stop_price", "candidate_target_price", "candidate_exit_reason",
    "session_at_online", "source_anchored_H1_M15_not_regenerated",
    "source_author_POI_not_independently_certified", "physical_bid_ask_available",
))


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("online provenance requires explicit ISO timestamps")
    result = datetime.fromisoformat(value)
    if result.utcoffset() is None:
        raise ValueError("online provenance requires timezone-aware clocks")
    return result


def _price(value: object) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("native-price claim must be a string")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid candidate price") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError("candidate price must be positive and finite")
    return result


@dataclass(frozen=True, slots=True)
class A1FirstOnlinePredecisionWitness:
    source_opportunity_id: str
    symbol: str
    session: str
    operating_date: str
    original_decision_at: str
    online_decision_at: str
    online_family: str
    h1_state_from: str
    m15_confirmed_at: str
    h1_direction: str
    candidate_entry_price: str
    m15_stop_price: str
    target_price: str | None
    status: str
    differs_from_v49: bool
    frozen_381_cohort: bool
    source_h1_m15_regenerated: bool = False
    source_author_poi_certified: bool = False
    online_native_m1_independently_verified: bool = False
    broker_bid_ask_verified: bool = False
    alters_trade_admission: bool = False
    full_master_frame_invoked: bool = False
    live_authorized: bool = False

    def __post_init__(self) -> None:
        if self.online_family not in FAMILIES or self.status not in STATUSES:
            raise ValueError("unsupported online route or candidate status")
        h1, m15 = _timestamp(self.h1_state_from), _timestamp(self.m15_confirmed_at)
        online, original = (
            _timestamp(self.online_decision_at),
            _timestamp(self.original_decision_at),
        )
        if not h1 <= m15 < online <= original:
            raise ValueError("first-online event cannot precede H1/M15 or use future M1")
        entry, stop = _price(self.candidate_entry_price), _price(self.m15_stop_price)
        if self.h1_direction not in ("BULLISH", "BEARISH"):
            raise ValueError("unrecognized H1 direction")
        if self.status == "ELIGIBLE":
            if self.target_price is None:
                raise ValueError("eligible source must carry an as-of target claim")
            target = _price(self.target_price)
            if not (
                (stop < entry < target) if self.h1_direction == "BULLISH"
                else (target < entry < stop)
            ):
                raise ValueError("eligible stop/target geometry inconsistent")
        elif self.target_price is not None:
            raise ValueError("ineligible source cannot forward an executable target")
        if any((
            self.source_h1_m15_regenerated, self.source_author_poi_certified,
            self.online_native_m1_independently_verified,
            self.broker_bid_ask_verified, self.alters_trade_admission,
            self.full_master_frame_invoked, self.live_authorized,
        )):
            raise ValueError("source-anchored observation cannot claim certification")


def sanitize_audit14_row(
    *, original: V49Opportunity, raw: Mapping[str, Any],
) -> A1FirstOnlinePredecisionWitness:
    """Whitelist strictly predecision source information; discard future outcomes."""
    if set(raw) != AUDIT14_FIELDS:
        raise ValueError("Audit14 schema changed: require independent review")
    sid = source_opportunity_id(original)
    if any((
        raw["source_opportunity_id"] != sid,
        raw["symbol"] != original.symbol,
        raw["session"] != original.session,
        raw["operating_date"] != original.operating_date,
        raw["v49_entry_at"] != original.m1_trigger_confirmed_at,
        raw["source_family"] != original.m1_trigger_family,
        raw["candidate_stop_price"] != original.m15_protected_swing_price,
    )):
        raise ValueError("Audit14 row cannot be joined to frozen V49 source")
    online_at = _timestamp(raw["online_entry_at"])
    orig_at = _timestamp(original.m1_trigger_confirmed_at)
    if type(raw["first_online_differs"]) is not bool or (
        raw["first_online_differs"] != (
            online_at != orig_at or raw["online_family"] != original.m1_trigger_family
        )
    ):
        raise ValueError("first-online discrepancy flag does not match source")
    if type(raw["frozen_381"]) is not bool:
        raise ValueError("static CISD cohort must be a bool")
    status = raw["status"]
    if status not in STATUSES or (
        raw["rejection_is_diagnostic_not_a_hard_veto"] is not
        (status != "ELIGIBLE")
    ):
        raise ValueError("Audit14 diagnostic status must never become a hard veto")
    if (
        raw["source_anchored_H1_M15_not_regenerated"] is not True
        or raw["source_author_POI_not_independently_certified"] is not True
        or raw["physical_bid_ask_available"] is not False
    ):
        raise ValueError("Audit14 has changed its evidence or provenance contract")
    if status == "ELIGIBLE" and raw["session_at_online"] != original.session:
        raise ValueError("eligible online session differs from frozen source")
    # Deliberately do NOT read original.h1_state_until: future expiry is not
    # visible at the online decision. Also do NOT read candidate_gross_r,
    # original_gross_r or candidate_exit_reason, even for eligible candidates.
    witness = A1FirstOnlinePredecisionWitness(
        source_opportunity_id=sid, symbol=original.symbol, session=original.session,
        operating_date=original.operating_date,
        original_decision_at=original.m1_trigger_confirmed_at,
        online_decision_at=raw["online_entry_at"], online_family=raw["online_family"],
        h1_state_from=original.h1_state_from,
        m15_confirmed_at=original.m15_setup_confirmed_at,
        h1_direction=original.h1_state_direction,
        candidate_entry_price=raw["candidate_entry_price"],
        m15_stop_price=original.m15_protected_swing_price,
        target_price=raw["candidate_target_price"],
        status=status, differs_from_v49=raw["first_online_differs"],
        frozen_381_cohort=raw["frozen_381"],
    )
    return witness


def reconcile_audit14_online_witnesses(
    *, originals: Iterable[V49Opportunity],
    rows: Iterable[Mapping[str, Any]],
    full_nine_market: bool = True,
) -> tuple[tuple[A1FirstOnlinePredecisionWitness, ...], dict[str, Any]]:
    """Lossless ID reconciliation, with non-executable diagnostic status counts."""
    source = tuple(originals)
    by_id = {source_opportunity_id(item): item for item in source}
    if len(by_id) != len(source):
        raise ValueError("duplicate frozen V49 source identity")
    witnesses: list[A1FirstOnlinePredecisionWitness] = []
    seen: set[str] = set()
    for row in rows:
        sid = row.get("source_opportunity_id")
        if not isinstance(sid, str) or sid in seen or sid not in by_id:
            raise ValueError("unknown/duplicate online source ID")
        seen.add(sid)
        witnesses.append(sanitize_audit14_row(original=by_id[sid], raw=row))
    if seen != set(by_id):
        raise ValueError("online ledger omitted original source IDs")
    symbols = {item.symbol for item in source}
    if full_nine_market and (len(source) != 2876 or len(symbols) != 9):
        raise ValueError("not the sealed nine-market 2876-source population")
    count = Counter(item.status for item in witnesses)
    report: dict[str, Any] = {
        "identity": IDENTITY,
        "source_ids_reconciled": len(witnesses),
        "markets": len(symbols),
        "online_differs_from_v49": sum(item.differs_from_v49 for item in witnesses),
        "static_cisd_381_cohort": sum(item.frozen_381_cohort for item in witnesses),
        "candidate_status_counts": dict(sorted(count.items())),
        "ex_post_outcomes_forwarded": False,
        "realized_r_or_mfe_used_for_admission": False,
        "source_universe_regenerated": False,
        "online_native_closes_independently_verified": False,
        "physical_bid_ask_present": False,
        "paper_trades_executed": 0,
        "master_frame_invoked": False,
        "live_authorized": False,
    }
    return tuple(witnesses), report


def safe_witness_dict(witness: A1FirstOnlinePredecisionWitness) -> dict[str, Any]:
    """Make the exact future-free projection available to later evidence collectors."""
    return asdict(witness)
