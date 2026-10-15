"""SINGLE VT31 trader identity coordinating London + New York source windows.

Only one trader and only one cognitive memory. London and NY are internal
session models, not separate trader registrations, balances, positions, or
exposure owners. NY AM and NY PM are two windows of ONE New York model.

Research sensor only. No order routing, broker fills, risk authority, CIBO
or QDLE integration, production flag, or legacy VT31 dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .cognition import CognitiveAssessment, VT31CleanroomCognition
from .contracts import (
    FRAMEWORK_POLICIES,
    G3_MSS_FRAMEWORK_POLICY,
    LEGACY_FRAMEWORK_POLICY,
    NEW_YORK,
    M1Bar,
    MethodologyDecision,
    SessionId,
    utc,
    window_bounds,
)
from .operations import IctSilverBulletOperations

TRADER_ID = "VT31"
INSTRUMENT = "NAS100"
SessionModel = Literal["LONDON", "NEW_YORK"]

SESSION_MODEL: dict[SessionId, SessionModel] = {
    SessionId.LONDON: "LONDON",
    SessionId.NY_AM: "NEW_YORK",
    SessionId.NY_PM: "NEW_YORK",
}


@dataclass(frozen=True, slots=True)
class UnifiedVT31Observation:
    trader_id: str
    instrument: str
    session_model: SessionModel | None
    session_window: SessionId | None
    observed_at: datetime
    cognition: CognitiveAssessment | None
    operational_phase: MethodologyDecision | None
    research_only: bool = True
    order_authorized: bool = False
    position_authorized: bool = False


class VT31Trader:
    """One VT31 instance, two internal models and three ICT time windows.

    Instantiate once in research runtime. Splitting by sessions for scientific
    reports does not create a new trader identity or a separate risk book.
    """

    trader_id = TRADER_ID
    instrument = INSTRUMENT

    def __init__(
        self, *, cognition: VT31CleanroomCognition | None = None,
        framework_policy: str | None = None,
    ) -> None:
        # Opt-in versioned framework binding: legacy default is untouched.
        # A mismatched COG/OPS contract is rejected BEFORE any market M1.
        selected = (
            LEGACY_FRAMEWORK_POLICY
            if framework_policy is None else framework_policy
        )
        if selected not in FRAMEWORK_POLICIES:
            raise ValueError("VT31_UNKNOWN_EXPLICIT_FRAMEWORK_POLICY")
        if cognition is not None and not isinstance(
            cognition, VT31CleanroomCognition
        ):
            raise ValueError("VT31_ORIGINAL_COGNITION_REQUIRED")
        if cognition is not None and cognition.framework_policy != selected:
            raise ValueError("VT31_COG_OPS_FRAMEWORK_MISMATCH_BEFORE_M1")
        self.framework_policy = selected
        self.cognition = (
            cognition if cognition is not None
            else VT31CleanroomCognition(framework_policy=selected)
        )
        self._windows: dict[
            tuple[str, SessionId], IctSilverBulletOperations
        ] = {}
        self.total_closed_m1 = 0
        self.total_source_windows_seen = 0

    def on_closed_m1(self, bar: M1Bar) -> UnifiedVT31Observation:
        if self.cognition.framework_policy != self.framework_policy:
            raise ValueError("VT31_COG_OPS_POLICY_CHANGED_AFTER_CONSTRUCTION")
        if self.framework_policy not in FRAMEWORK_POLICIES:
            raise ValueError("VT31_UNKNOWN_EXPLICIT_FRAMEWORK_POLICY")
        if not isinstance(bar, M1Bar):
            raise ValueError("VT31 accepts only valid cleanroom M1Bar")
        at = utc(bar.closed_at)
        opened = utc(bar.opened_at)
        local_hour = opened.astimezone(NEW_YORK).hour
        # Avoid constructing 3 timezone-aware NY windows on each of the
        # 1,059,784 real M1 bars. These are the ONLY three source hours.
        window: SessionId | None = {
            3: SessionId.LONDON,
            10: SessionId.NY_AM,
            14: SessionId.NY_PM,
        }.get(local_hour)
        if window is not None:
            start, end = window_bounds(opened, window)
            if not start <= opened < end:
                raise AssertionError("DST source-hour detection drift")

        if window is None:
            self.cognition.observe_closed_m1(bar)
            self.total_closed_m1 += 1
            return UnifiedVT31Observation(
                trader_id=TRADER_ID,
                instrument=INSTRUMENT,
                session_model=None,
                session_window=None,
                observed_at=at,
                cognition=None,
                operational_phase=None,
            )

        key = (
            opened.astimezone(NEW_YORK).date().isoformat(),
            window,
        )
        ops = self._windows.get(key)
        if ops is None:
            start, _ = window_bounds(opened, window)
            if opened != start:
                raise ValueError(
                    "cannot bootstrap partial Silver Bullet window silently"
                )
        elif ops.last_closed is not None and opened != ops.last_closed:
            raise ValueError(
                "missing/duplicate M1 in active VT31 source window"
            )

        # Refuse a malformed session bar BEFORE mutating unified cognition.
        # No partly rejected bar may poison shared London/NY market memory.
        self.cognition.observe_closed_m1(bar)
        self.total_closed_m1 += 1
        if ops is None:
            ops = IctSilverBulletOperations(
                session=window, day=opened,
                framework_policy=self.framework_policy,
            )
            self._windows[key] = ops
            self.total_source_windows_seen += 1

        assessment = self.cognition.assess(session=window, as_of=at)
        before_fvg = ops.intrawindow_raw_fvg_count
        before_candidate = ops.first_suitable
        phase = ops.on_closed_m1(bar, cognition=assessment.decision)
        if self.cognition.telemetry is not None:
            self.cognition.telemetry.on_ops(
                at=at, session=window, phase=phase,
                raw_fvg_new=ops.intrawindow_raw_fvg_count > before_fvg,
                candidate_new=(
                    before_candidate is None and ops.first_suitable is not None
                ),
                cognition=assessment.decision,
                candidate=ops.first_suitable,
                missing=assessment.missing,
            )
        return UnifiedVT31Observation(
            trader_id=TRADER_ID,
            instrument=INSTRUMENT,
            session_model=SESSION_MODEL[window],
            session_window=window,
            observed_at=at,
            cognition=assessment,
            operational_phase=phase,
        )

    def research_observe_incomplete_source_m1(
        self, bar: M1Bar
    ) -> None:
        """Ingest missing-coverage source-hour evidence WITHOUT any setup.

        Fast 3Y evidence may contain e.g. 58 of the required 60 M1 for an
        ICT window. Preserve their original market facts in ONE cognitive
        memory but do not create an OPS state, retrospectively choose a FVG,
        or claim a fill. May be called by the scientific replay after the
        hour is *completely classified* as incomplete.
        """
        if self.cognition.framework_policy != self.framework_policy:
            raise ValueError("VT31_COG_OPS_POLICY_CHANGED_AFTER_CONSTRUCTION")
        if not isinstance(bar, M1Bar):
            raise ValueError("requires cleanroom validated M1")
        local_hour = utc(bar.opened_at).astimezone(NEW_YORK).hour
        if local_hour not in (3, 10, 14):
            raise ValueError("incomplete-window feed only for ICT source M1")
        self.cognition.observe_closed_m1(bar)
        self.total_closed_m1 += 1

    def snapshot(self) -> dict[str, object]:
        """Session-separated telemetry; a single trader registry identity."""
        windows = tuple(
            {
                "ny_date": day,
                "session": session.value,
                "model": SESSION_MODEL[session],
                "phase": ops.decision.value,
            }
            for (day, session), ops in sorted(
                self._windows.items(),
                key=lambda item: (item[0][0], item[0][1].value),
            )
        )
        return {
            "schema": "qore.vt31.cleanroom.unified_trader.v1",
            "trader_id": TRADER_ID,
            "registered_trader_count": 1,
            "instrument": INSTRUMENT,
            "session_models": ("LONDON", "NEW_YORK"),
            "ny_windows": ("VT31_NY_AM", "VT31_NY_PM"),
            "single_cognitive_memory": True,
            "explicit_framework_policy": self.framework_policy,
            "G3_opt_in_research_only": (
                self.framework_policy == G3_MSS_FRAMEWORK_POLICY
            ),
            "methodology_certified": False,
            "cognition_certified": False,
            "closed_m1_received": self.total_closed_m1,
            "source_windows_seen": self.total_source_windows_seen,
            "session_windows": windows,
            "independent_certification_by_session_model": True,
            "no_duplicate_session_trader_ids": True,
            "position_or_order_execution_implemented": False,
            "live_authorized": False,
            "certified": False,
        }
