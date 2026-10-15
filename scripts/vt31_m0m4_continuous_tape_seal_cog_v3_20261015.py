#!/usr/bin/env python3
"""VT31 COG V3: rolling M1 source seal between M0 and successive M4 observations.

An immutable full-prefix seal is advanced ONLY on an accepted research WAIT.
The underlying V2 research candidate is unchanged. No orders or sizing.
Prereg: 3a1c637811c6c2c648abc688d45bff22ddbc4c54.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    M1Bar,
    SessionId,
    utc,
)
from scripts.vt31_m0_m4_context_memory_cog_candidate_20261015 import (
    VT31M0M4CognitiveCandidate,
    tape_sha256,
)
from scripts.vt31_ttrades_source_first_g3_cognitive_proposal_20261015 import (
    ttrades_fixture,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import Side

PREREG = "3a1c637811c6c2c648abc688d45bff22ddbc4c54"
VERSION = "VT31_COG_V3_CONTINUOUS_M1_SOURCE_SEAL_RESEARCH_NO_OMS"
WAIT = "WAIT"
REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class ObservedTapeSeal:
    last_as_of: datetime
    count: int
    sha256_total: str


@dataclass(frozen=True, slots=True)
class SealVerdict:
    action: str
    reason: str
    session: str
    original_v2_reason: str | None = None
    delegated_to_v2: bool = False
    context_stored: bool = False
    seal_count: int | None = None
    seal_sha256: str | None = None
    methodology_certified: bool = False
    cognition_certified: bool = False
    independent_cog_ops_human_signed: bool = False
    production_integrated: bool = False
    broker_orders: int = 0
    trader_sizing: int = 0

    def record(self) -> dict[str, Any]:
        return {
            "version": VERSION, "action": self.action, "reason": self.reason,
            "session": self.session, "original_v2_reason": self.original_v2_reason,
            "delegated_to_v2": self.delegated_to_v2,
            "context_stored": self.context_stored,
            "seal_count": self.seal_count, "seal_sha256": self.seal_sha256,
            "methodology_certified": False, "cognition_certified": False,
            "independent_cog_ops_human_signed": False,
            "production_integrated": False,
            "broker_orders": 0, "trader_sizing": 0,
        }


class VT31ContinuousSealCandidate:
    """Research-only V3 wrapper. No G3 COG/OPS writer/authorizing DTO."""

    def __init__(self) -> None:
        self._inner = VT31M0M4CognitiveCandidate()
        self._seal: ObservedTapeSeal | None = None

    @property
    def seal(self) -> ObservedTapeSeal | None:
        return self._seal

    @property
    def context(self):
        return self._inner.context

    def _out(
        self, action: str, reason: str, session: SessionId | object,
        *, v2: str | None = None, delegated: bool = False,
    ) -> SealVerdict:
        return SealVerdict(
            action=action, reason=reason,
            session=session.value if isinstance(session, SessionId) else "INVALID",
            original_v2_reason=v2, delegated_to_v2=delegated,
            context_stored=self._inner.context is not None,
            seal_count=self._seal.count if self._seal else None,
            seal_sha256=self._seal.sha256_total if self._seal else None,
        )

    def capture_context(
        self, *, session: SessionId, closed_m1: tuple[M1Bar, ...],
        as_of: datetime,
    ) -> SealVerdict:
        if self._seal is not None:
            return self._out(REJECT, "M0_SEALED_CONTEXT_CANNOT_BE_RECAPTURED", session)
        # M0 remains exactly the V2 policy and original G3 source-first witness.
        v2 = self._inner.capture_context(
            session=session, closed_m1=closed_m1, as_of=as_of,
        )
        if v2.action == WAIT and self._inner.context is not None:
            self._seal = ObservedTapeSeal(
                last_as_of=utc(as_of),
                count=len(closed_m1),
                sha256_total=tape_sha256(closed_m1),
            )
        return self._out(
            v2.action,
            "M0_FULL_TAPE_SEALED_M4_AUTHOR_STILL_PENDING"
            if self._seal is not None else v2.reason,
            session, v2=v2.reason, delegated=True,
        )

    def assess_later_retest(
        self, *, session: SessionId, closed_m1: tuple[M1Bar, ...],
        as_of: datetime, family_evidence: dict[str, Any] | None = None,
    ) -> SealVerdict:
        seal = self._seal
        if seal is None:
            return self._out(WAIT, "M0_SOURCE_CONTEXT_NOT_ESTABLISHED", session)
        if session is not SessionId.NY_AM or self._inner.context is None:
            return self._out(REJECT, "V3_SEALED_SESSION_OR_M0_CONTEXT_MISMATCH", session)
        if not isinstance(closed_m1, tuple) or any(
            not isinstance(c, M1Bar) for c in closed_m1
        ):
            return self._out(REJECT, "M1_SOURCE_TUPLE_REQUIRED", session)
        try:
            at = utc(as_of)
        except (TypeError, ValueError):
            return self._out(REJECT, "ASOF_MUST_BE_TIMEZONE_AWARE", session)
        if at <= seal.last_as_of or len(closed_m1) <= seal.count:
            return self._out(REJECT, "M1_TIME_NOT_STRICTLY_ADVANCING", session)
        try:
            unchanged = tape_sha256(closed_m1[:seal.count]) == seal.sha256_total
        except (TypeError, ValueError):
            return self._out(REJECT, "SOURCE_M1_UNSERIALIZABLE", session)
        if not unchanged:
            return self._out(REJECT, "SOURCE_OBSERVED_TAPE_FORK", session)

        if family_evidence is not None:
            if not isinstance(family_evidence, dict):
                return self._out(REJECT, "M4_EVIDENCE_MAPPING_REQUIRED", session)
            for key in ("opposing_candles", "zone_candles", "swing_legs"):
                if key in family_evidence and not isinstance(
                    family_evidence[key], tuple
                ):
                    return self._out(
                        REJECT, "M4_EVIDENCE_SERIES_NOT_IMMUTABLE_TUPLE", session,
                    )

        # V2 currently moves its private last_assessed before checking M4.
        # This narrow compatibility adapter implements transactional REJECT.
        # Its only mutable M4 field is _last_assessed; _source is frozen
        # after M0. A future V2 change requires prereg + new tests.
        previous_time = self._inner._last_assessed
        previous_source = self._inner.context
        try:
            v2 = self._inner.assess_later_retest(
                session=session, closed_m1=closed_m1,
                as_of=at, family_evidence=family_evidence,
            )
        except (TypeError, ValueError, AttributeError):
            self._inner._last_assessed = previous_time
            if self._inner.context is not previous_source:
                raise RuntimeError("V2_SOURCE_CHANGED_DURING_REJECT")
            return self._out(
                REJECT, "V2_M4_UNTRUSTED_INPUT_REJECTED", session,
                delegated=True,
            )
        if self._inner.context is not previous_source:
            raise RuntimeError("V2_SOURCE_CONTEXT_MUTATED_AFTER_M0")
        if v2.action != WAIT:
            self._inner._last_assessed = previous_time
            return self._out(
                REJECT, v2.reason, session,
                v2=v2.reason, delegated=True,
            )
        if self._inner._last_assessed != at:
            raise RuntimeError("V2_WAIT_DID_NOT_OBSERVE_CURRENT_M1")
        self._seal = ObservedTapeSeal(
            last_as_of=at,
            count=len(closed_m1),
            sha256_total=tape_sha256(closed_m1),
        )
        return self._out(
            WAIT, "M1_SOURCE_CONTINUITY_SEALED_AUTHOR_METHOD_PENDING",
            session, v2=v2.reason, delegated=True,
        )


def prereg_context_dossier() -> dict[str, Any]:
    cases = []
    for month in (1, 7):
        for side in (Side.LONG, Side.SHORT):
            for valid in (False, True):
                tape, at = ttrades_fixture(
                    month=month, side=side, min10_valid=valid,
                )
                actor = VT31ContinuousSealCandidate()
                verdict = actor.capture_context(
                    session=SessionId.NY_AM, closed_m1=tape, as_of=at,
                )
                if (actor.seal is not None) != valid:
                    raise ValueError("V3_CONTEXT_SEALED_WITHOUT_VALID_M0")
                cases.append({
                    "case": f"{side.value}_{month}_M0_{valid}",
                    **verdict.record(),
                })
    return {
        "title": VERSION, "prereg_commit": PREREG,
        "cases": cases, "synthetic_m1_source_only": True,
        "native_cog_integrated": False,
        "author_m3_m4_m5_certified": False,
        "owner_m0_signed": False, "independent_cog_ops_human_signed": False,
        "methodology_certified": False, "cognition_certified": False,
        "broker_orders": 0, "sizing": 0, "live": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    path = parser.parse_args().out
    data = prereg_context_dossier()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    print(json.dumps({
        "cases": len(data["cases"]),
        "sealed_contexts": sum(c["seal_count"] is not None for c in data["cases"]),
        "certified": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
