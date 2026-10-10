"""P0-A proposal: VT08 5M source CandidateEvent V1, research-only.

Boundary ONLY: methodology -> cognitive architect. No order, quantity,
execution approval, risk sizing, broker instruction or live authorization.
The sole machine-complete family in this first implementation is narrow B01
positional-entry. Other TTrades entry identities MUST remain unexecutable
until individually proven and pre-registered. See Issue #762 / #763.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

SCHEMA = "VT08_5M_CANDIDATE_EVENT_V1"
REVIEW_STATUS = "PROPOSED_AWAITING_ARCHITECT_B_REVIEW"
MARKETS = frozenset({"EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD"})
OWNER_ANCHORS_NY = frozenset({1, 5, 9})
FAMILIES = frozenset({
    "reversal-entry", "continuation-entry", "confident-entry",
    "positional-entry", "open-entry", "poi-continuation-entry",
})
NARROW_MACHINE_COMPLETE = frozenset({"positional-entry"})
LTF_PROFILES = frozenset({"M15_STANDARD", "M5_FRACTAL", "M3_FRACTAL"})
NY = ZoneInfo("America/New_York")


class CandidateEventContractError(ValueError):
    """Causal/authority violation: do not pass the event to cognition."""


def _aware(value: datetime, name: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise CandidateEventContractError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


def _price(value: Decimal, name: str) -> None:
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise CandidateEventContractError(f"{name} must be a positive finite Decimal")


def _digest(value: str, name: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise CandidateEventContractError(f"{name} requires lowercase sha256")


def _canonical_price(value: Decimal) -> str:
    return format(value.normalize(), "f")


@dataclass(frozen=True, slots=True)
class Vt08CandidateEventV1:
    """Immutable source event, never a permission to EXECUTE.

    Times represent evidence available at the decision, not completed trades.
    The H4 expiry concerns *pending entry* only; filled lifecycle stays a
    separately marked QORE containment. No PnL or outcome features allowed.
    """

    market: str
    source_family: str
    ltf_profile: str
    side: str
    scenario: str
    h4_anchor_at: datetime
    decision_at: datetime
    evidence_as_of: datetime
    candle2_closed_at: datetime
    opposing_series_opened_at: datetime
    cisd_confirmed_at: datetime
    ps_confirmed_at: datetime
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal
    pending_expiry_at: datetime
    source_methodology_sha256: str
    evidence_sha256: str
    source_rule_ref: str = "vt08-r3.9-b01-positional"
    entry_basis: str = "H4_OPEN_EXACT_FILL_QORE_CONTAINMENT"
    stop_basis: str = "PROTECTED_SWING_NO_OFFSET_QORE_CONTAINMENT"
    target_basis: str = "FIXED_2R_QORE_CONTAINMENT"
    filled_lifecycle: str = "CLOSE_NEXT_H4_QORE_CONTAINMENT"
    research_only: bool = True

    def __post_init__(self) -> None:
        if self.market not in MARKETS:
            raise CandidateEventContractError("market outside 5M research scope")
        if self.source_family not in FAMILIES:
            raise CandidateEventContractError("unrecognized source family")
        if self.source_family not in NARROW_MACHINE_COMPLETE:
            raise CandidateEventContractError(
                "source identity is not an executable bundle"
            )
        if self.ltf_profile != "M15_STANDARD":
            raise CandidateEventContractError(
                "B01 positional executable path is M15 only"
            )
        if self.side not in {"long", "short"} or self.scenario != "C2_COMPLETED":
            raise CandidateEventContractError("B01 positional side/scenario invalid")
        if not self.research_only:
            raise CandidateEventContractError("research-only authority required")
        if self.source_rule_ref != "vt08-r3.9-b01-positional":
            raise CandidateEventContractError("unapproved source bundle")
        if (
            self.entry_basis != "H4_OPEN_EXACT_FILL_QORE_CONTAINMENT"
            or self.stop_basis != "PROTECTED_SWING_NO_OFFSET_QORE_CONTAINMENT"
            or self.target_basis != "FIXED_2R_QORE_CONTAINMENT"
            or self.filled_lifecycle != "CLOSE_NEXT_H4_QORE_CONTAINMENT"
        ):
            raise CandidateEventContractError("replay containment drifted")
        for n in ("entry_price", "stop_price", "target_price"):
            _price(getattr(self, n), n)
        for n in ("source_methodology_sha256", "evidence_sha256"):
            _digest(getattr(self, n), n)
        anchor = _aware(self.h4_anchor_at, "h4_anchor_at")
        decision = _aware(self.decision_at, "decision_at")
        as_of = _aware(self.evidence_as_of, "evidence_as_of")
        c2 = _aware(self.candle2_closed_at, "candle2_closed_at")
        opposed = _aware(self.opposing_series_opened_at, "opposing_series_opened_at")
        cisd = _aware(self.cisd_confirmed_at, "cisd_confirmed_at")
        ps = _aware(self.ps_confirmed_at, "ps_confirmed_at")
        expiry = _aware(self.pending_expiry_at, "pending_expiry_at")
        local = anchor.astimezone(NY)
        if (
            local.hour not in OWNER_ANCHORS_NY
            or local.minute
            or local.second
            or local.microsecond
        ):
            raise CandidateEventContractError("not an exact 01/05/09 NY H4 open")
        if anchor != decision or as_of != decision:
            raise CandidateEventContractError(
                "narrow positional entry must be causal at H4 open"
            )
        if not (opposed < cisd == ps <= c2 == decision):
            raise CandidateEventContractError("CISD/PS/C2 not confirmed as-of entry")
        if expiry != anchor + timedelta(hours=4):
            raise CandidateEventContractError("pending H4 expiry containment mismatch")
        if self.side == "long" and not (
            self.stop_price < self.entry_price < self.target_price
        ):
            raise CandidateEventContractError("long entry/SL/TP geometry invalid")
        if self.side == "short" and not (
            self.target_price < self.entry_price < self.stop_price
        ):
            raise CandidateEventContractError("short entry/SL/TP geometry invalid")
        risk = abs(self.entry_price - self.stop_price)
        if self.target_price != (
            self.entry_price + 2 * risk if self.side == "long"
            else self.entry_price - 2 * risk
        ):
            raise CandidateEventContractError("fixed-2R *research containment* drifted")

    def source_payload(self) -> dict[str, object]:
        """Deterministic JSON-ready payload. No future prices or PnL."""
        time_fields = (
            "h4_anchor_at", "decision_at", "evidence_as_of", "candle2_closed_at",
            "opposing_series_opened_at", "cisd_confirmed_at",
            "ps_confirmed_at", "pending_expiry_at",
        )
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "market": self.market,
            "ny_date": self.h4_anchor_at.astimezone(NY).date().isoformat(),
            "anchor_ny_hour": self.h4_anchor_at.astimezone(NY).hour,
            "source_family": self.source_family,
            "ltf_profile": self.ltf_profile,
            "side": self.side,
            "scenario": self.scenario,
            "source_rule_ref": self.source_rule_ref,
            "entry_basis": self.entry_basis,
            "stop_basis": self.stop_basis,
            "target_basis": self.target_basis,
            "filled_lifecycle": self.filled_lifecycle,
            "source_methodology_sha256": self.source_methodology_sha256,
            "evidence_sha256": self.evidence_sha256,
            "research_only": self.research_only,
            "execution_authorized": False,
            "live_authorized": False,
        }
        for name in time_fields:
            payload[name] = _aware(getattr(self, name), name).isoformat(
                timespec="microseconds"
            )
        for name in ("entry_price", "stop_price", "target_price"):
            payload[name] = _canonical_price(getattr(self, name))
        return payload

    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.source_payload(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def envelope(self) -> dict[str, object]:
        fingerprint = self.fingerprint()
        return {
            "event_id": f"vt08-5m:{fingerprint}",
            "event_fingerprint": fingerprint,
            **self.source_payload(),
        }


def from_narrow_b01_candidate(
    candidate: object, *, evidence_sha256: str
) -> Vt08CandidateEventV1:
    """Projection from the unchanged, validated A-side 5M B01 candidate only."""
    from qore.infrastructure.trader_lab.vt08_cognitive_expansion_5m_evaluator_v1 import (
        Vt08ExpansionCandidate,
    )

    if type(candidate) is not Vt08ExpansionCandidate:
        raise CandidateEventContractError("require frozen Vt08ExpansionCandidate")
    if not candidate.research_only:
        raise CandidateEventContractError("no operational candidate is accepted")
    if candidate.candle2.closed_at != candidate.decision_at:
        raise CandidateEventContractError("C2 did not close at decision")
    return Vt08CandidateEventV1(
        market=candidate.symbol, source_family="positional-entry",
        ltf_profile="M15_STANDARD", side=candidate.side.value,
        scenario="C2_COMPLETED", h4_anchor_at=candidate.decision_at,
        decision_at=candidate.decision_at, evidence_as_of=candidate.decision_at,
        candle2_closed_at=candidate.candle2.closed_at,
        opposing_series_opened_at=candidate.protected_swing.opposing_series_opened_at,
        cisd_confirmed_at=candidate.protected_swing.confirmed_at,
        ps_confirmed_at=candidate.protected_swing.confirmed_at,
        entry_price=candidate.setup.entry_price,
        stop_price=candidate.setup.invalidation_price,
        target_price=candidate.setup.take_profit_price,
        pending_expiry_at=candidate.decision_at + timedelta(hours=4),
        source_methodology_sha256=candidate.vt08_methodology_fingerprint,
        evidence_sha256=evidence_sha256,
    )
