#!/usr/bin/env python3
"""VT31 COG V4: isolated PREPARE / COMMIT, research WAIT/REJECT only.

No modification of original G3, existing V2, or V3. A rejected proposal never
mutates the committed V2 state: deep-copy the complete candidate, execute the
public method on the clone, and commit only after source proofs + WAIT.
Precode prereg a7e502fc2f17da23b229f5241a827d95992d22ba.
"""
from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    Side,
    utc,
)
from scripts.vt31_m0_m4_context_memory_cog_candidate_20261015 import (
    VT31M0M4CognitiveCandidate,
    tape_sha256,
)
from scripts.vt31_m0m4_continuous_tape_seal_cog_v3_20261015 import (
    ObservedTapeSeal,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)

PREREG = "a7e502fc2f17da23b229f5241a827d95992d22ba"
VERSION = "VT31_COG_V4_ISOLATED_TWO_PHASE_COMMIT_RESEARCH_20261016"
WAIT = "WAIT"
REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class TransactionVerdict:
    action: str
    reason: str
    session: str
    revision: int
    committed_m1_count: int | None
    committed_sha256: str | None
    v2_reason: str | None = None
    prepare_invoked: bool = False
    committed: bool = False
    author_method_certified: bool = False
    cognition_certified: bool = False
    policy_owner_signed: bool = False
    dual_human_review_signed: bool = False
    live_or_oms_authorized: bool = False
    broker_orders: int = 0
    lot_sizing: int = 0

    def record(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "action": self.action,
            "reason": self.reason,
            "session": self.session,
            "revision": self.revision,
            "committed_m1_count": self.committed_m1_count,
            "committed_sha256": self.committed_sha256,
            "v2_reason": self.v2_reason,
            "prepare_invoked": self.prepare_invoked,
            "committed": self.committed,
            "author_method_certified": False,
            "cognition_certified": False,
            "policy_owner_signed": False,
            "dual_human_review_signed": False,
            "live_or_oms_authorized": False,
            "broker_orders": 0,
            "lot_sizing": 0,
        }


class VT31TwoPhaseCognitiveCandidate:
    """Single VT31 stateful research actor. No operational decision DTO."""

    def __init__(self) -> None:
        self._committed = VT31M0M4CognitiveCandidate()
        self._seal: ObservedTapeSeal | None = None
        self._revision = 0

    @property
    def seal(self) -> ObservedTapeSeal | None:
        return self._seal

    @property
    def context(self):
        return self._committed.context

    @property
    def revision(self) -> int:
        return self._revision

    def _result(
        self, action: str, reason: str, session: SessionId | object,
        *, v2_reason: str | None = None,
        prepared: bool = False, committed: bool = False,
    ) -> TransactionVerdict:
        return TransactionVerdict(
            action=action,
            reason=reason,
            session=session.value if isinstance(session, SessionId) else "INVALID",
            revision=self._revision,
            committed_m1_count=self._seal.count if self._seal else None,
            committed_sha256=self._seal.sha256_total if self._seal else None,
            v2_reason=v2_reason,
            prepare_invoked=prepared,
            committed=committed,
        )

    def capture_context(
        self, *, session: SessionId, closed_m1: tuple[M1Bar, ...],
        as_of: datetime,
    ) -> TransactionVerdict:
        if self._seal is not None:
            return self._result(REJECT, "M0_CONTEXT_ALREADY_COMMITTED", session)
        if not isinstance(closed_m1, tuple) or not all(
            isinstance(row, M1Bar) for row in closed_m1
        ):
            return self._result(REJECT, "M0_TYPED_M1_TUPLE_REQUIRED", session)
        try:
            staged = copy.deepcopy(self._committed)
            response = staged.capture_context(
                session=session, closed_m1=closed_m1, as_of=as_of,
            )
            if response.action != WAIT:
                return self._result(
                    REJECT, "M0_SOURCE_ADMISSION_REJECTED", session,
                    v2_reason=response.reason, prepared=True,
                )
            if staged.context is None:
                # TTrades MIN10 conflict and ICT London/NY PM remain WAIT only.
                return self._result(
                    WAIT, "M0_CONTEXT_UNKNOWN_OR_MIN10_WAIT", session,
                    v2_reason=response.reason, prepared=True,
                )
            at = utc(as_of)
            digest = tape_sha256(closed_m1)
        except Exception:
            return self._result(
                REJECT, "M0_PREPARE_FAILED_NO_STATE_MUTATION", session,
                prepared=True,
            )
        next_seal = ObservedTapeSeal(
            last_as_of=at, count=len(closed_m1), sha256_total=digest,
        )
        self._committed = staged
        self._seal = next_seal
        self._revision += 1
        return self._result(
            WAIT, "M0_SOURCE_CONTEXT_COMMITTED_RESEARCH_ONLY", session,
            v2_reason=response.reason, prepared=True, committed=True,
        )

    def assess_later_retest(
        self, *, session: SessionId, closed_m1: tuple[M1Bar, ...],
        as_of: datetime, family_evidence: dict[str, Any] | None = None,
    ) -> TransactionVerdict:
        current = self._seal
        if current is None:
            return self._result(WAIT, "M0_CONTEXT_NOT_COMMITTED", session)
        if session is not SessionId.NY_AM or self._committed.context is None:
            return self._result(REJECT, "SESSION_MISMATCH_AFTER_M0", session)
        if not isinstance(closed_m1, tuple) or any(
            not isinstance(c, M1Bar) for c in closed_m1
        ):
            return self._result(REJECT, "M1_TYPED_TUPLE_REQUIRED", session)
        try:
            at = utc(as_of)
        except (TypeError, ValueError):
            return self._result(REJECT, "ASOF_NOT_TIMEZONE_AWARE", session)
        if at <= current.last_as_of or len(closed_m1) <= current.count:
            return self._result(REJECT, "M1_NOT_STRICTLY_NEWER", session)
        try:
            prefix_digest = tape_sha256(closed_m1[:current.count])
        except Exception:
            return self._result(REJECT, "M1_PREFIX_HASH_FAILED", session)
        if prefix_digest != current.sha256_total:
            return self._result(REJECT, "PREVIOUSLY_SEEN_M1_MUTATED", session)
        if family_evidence is not None:
            if not isinstance(family_evidence, dict):
                return self._result(REJECT, "M4_SOURCE_MAPPING_REQUIRED", session)
            if any(
                key in family_evidence
                and not isinstance(family_evidence[key], tuple)
                for key in ("opposing_candles", "zone_candles", "swing_legs")
            ):
                return self._result(
                    REJECT, "M4_SERIES_MUST_BE_TUPLES", session,
                )

        # PREPARE: entire V2 instance is copied; no direct read/write of its
        # private clock, source, engine, or other internals.
        try:
            staged = copy.deepcopy(self._committed)
            response = staged.assess_later_retest(
                session=session,
                closed_m1=closed_m1,
                as_of=at,
                family_evidence=copy.deepcopy(family_evidence),
            )
            if response.action != WAIT:
                return self._result(
                    REJECT, "M4_REJECT_DISCARDED_PREPARED_STATE", session,
                    v2_reason=response.reason, prepared=True,
                )
            if staged.context != self._committed.context:
                return self._result(
                    REJECT, "M0_CONTEXT_CHANGED_DURING_PREPARE", session,
                    prepared=True,
                )
            digest = tape_sha256(closed_m1)
        except Exception:
            return self._result(
                REJECT, "V2_PREPARE_EXCEPTION_DISCARDED", session,
                prepared=True,
            )
        next_seal = ObservedTapeSeal(
            last_as_of=at, count=len(closed_m1), sha256_total=digest,
        )
        # COMMIT: there are no external actions between either assignment.
        self._committed = staged
        self._seal = next_seal
        self._revision += 1
        return self._result(
            WAIT, "M1_SOURCE_CONTEXT_ATOMIC_COMMIT_METHOD_PENDING", session,
            v2_reason=response.reason, prepared=True, committed=True,
        )


def transactional_m0_dossier() -> dict[str, Any]:
    rows = []
    for month in (1, 7):
        for side in (Side.LONG, Side.SHORT):
            for compatible in (False, True):
                hist, at = ttrades_fixture(
                    month=month, side=side, min10_valid=compatible,
                )
                actor = VT31TwoPhaseCognitiveCandidate()
                v = actor.capture_context(
                    session=SessionId.NY_AM, closed_m1=hist, as_of=at,
                )
                if (actor.seal is not None) != compatible:
                    raise ValueError("TWO_PHASE_M0_SOURCE_INTEGRITY_DRIFT")
                rows.append({
                    "case": f"NYAM_{month}_{side.value}_{compatible}",
                    **v.record(),
                })
    return {
        "title": VERSION, "prereg_sha": PREREG,
        "synthetic_m1_only": True, "cases": rows,
        "methodology_certified": False, "cognition_certified": False,
        "human_cog_ops_reviews_complete": False,
        "owner_policy_signed": False, "m3_m4_m5_author_approved": False,
        "native_cog_integrated": False, "orders": 0, "sizing": 0, "live": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    path = parser.parse_args().out
    payload = transactional_m0_dossier()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "cases": len(payload["cases"]),
        "committed": sum(row["committed"] for row in payload["cases"]),
        "methodology_certified": False,
        "cognition_certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
