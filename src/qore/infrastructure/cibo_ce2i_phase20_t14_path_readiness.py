"""Bind existing DEMO behavior-ledger position paths to Phase20 T14.

The cTrader DEMO runtime already writes append-only position path samples and
settlement events. This module links those observations to sealed Phase20
decisions by signal fingerprint and measures whether a causal T14 evidence
stream exists. It never changes a position or grants de-risking authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import (
    LiveBehaviorEvent,
)


@dataclass(frozen=True, slots=True)
class Phase20T14PathReadiness:
    stream_bound: bool
    observed_path_samples: int
    path_positions: int
    longitudinal_path_positions: int
    reconciled_stop_positions: int
    execution_cost_bound_positions: int
    protection_change_positions: int
    volume_change_positions: int
    qualifying_intervention_positions: int
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "stream_bound",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"Phase20 T14 {name} must be bool"
                )
        for name in (
            "observed_path_samples",
            "path_positions",
            "longitudinal_path_positions",
            "reconciled_stop_positions",
            "execution_cost_bound_positions",
            "protection_change_positions",
            "volume_change_positions",
            "qualifying_intervention_positions",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T14 {name} must be non-negative int"
                )
        for name in (
            "longitudinal_path_positions",
            "reconciled_stop_positions",
            "execution_cost_bound_positions",
            "protection_change_positions",
            "volume_change_positions",
            "qualifying_intervention_positions",
        ):
            if getattr(self, name) > self.path_positions:
                raise CiboCapitalManagementError(
                    f"Phase20 T14 {name} cannot exceed path positions"
                )
        if self.stream_bound and self.longitudinal_path_positions == 0:
            raise CiboCapitalManagementError(
                "Phase20 T14 bound stream requires longitudinal position paths"
            )
        if not self.stream_bound and not self.blockers:
            raise CiboCapitalManagementError(
                "Phase20 T14 unbound stream must name blockers"
            )


def assess_phase20_t14_path_readiness(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    events: tuple[LiveBehaviorEvent, ...],
) -> Phase20T14PathReadiness:
    """Measure post-entry path evidence already emitted by the DEMO runtime."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T14 path readiness requires canonical forward book"
        )
    if any(not isinstance(item, LiveBehaviorEvent) for item in events):
        raise CiboCapitalManagementError(
            "Phase20 T14 path readiness requires canonical behavior events"
        )

    signal_decisions: dict[str, tuple[str, datetime]] = {}
    for decision in evidence_book.decisions:
        if (
            decision.decision_at
            < FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at
            or decision.sealed_at is None
            or (
                decision.seal_deadline_at is not None
                and not decision.sealed_within_deadline
            )
            or _evidence_kind(decision.canonical_payload_json)
            != "FORWARD_OBSERVED"
        ):
            continue
        for signal in decision.signal_fingerprints:
            previous = signal_decisions.get(signal)
            identity = (decision.evidence_sha256, decision.decision_at)
            if previous is not None and previous != identity:
                raise CiboCapitalManagementError(
                    "Phase20 T14 signal maps to multiple forward decisions"
                )
            signal_decisions[signal] = identity

    grouped_paths: dict[tuple[str, int], list[LiveBehaviorEvent]] = {}
    grouped_settlements: dict[tuple[str, int], list[LiveBehaviorEvent]] = {}
    for event in sorted(events, key=lambda item: item.observed_at):
        signal = event.signal_fingerprint
        position_id = event.position_id
        if signal is None or position_id is None:
            continue
        binding = signal_decisions.get(signal)
        if binding is None:
            continue
        _sha, decision_at = binding
        if event.observed_at < decision_at:
            raise CiboCapitalManagementError(
                "Phase20 T14 behavior event predates bound forward decision"
            )
        key = (signal, position_id)
        if event.event == "CTRADER_DEMO_POSITION_PATH_SAMPLE":
            grouped_paths.setdefault(key, []).append(event)
        if "SETTLEMENT" in event.event.upper():
            grouped_settlements.setdefault(key, []).append(event)

    path_positions = len(grouped_paths)
    path_samples = sum(len(rows) for rows in grouped_paths.values())
    longitudinal = 0
    reconciled_stop = 0
    cost_bound = 0
    protection_change = 0
    volume_change = 0
    qualifying = 0

    for key, rows in grouped_paths.items():
        ordered = tuple(sorted(rows, key=lambda item: item.observed_at))
        if len(ordered) >= 2:
            longitudinal += 1
        stops = tuple(_decimal_payload(item, "stop_loss") for item in ordered)
        volumes = tuple(_decimal_payload(item, "volume") for item in ordered)
        latest_stop = stops[-1]
        has_stop = latest_stop is not None and latest_stop > 0
        if has_stop:
            reconciled_stop += 1
        stop_values = {item for item in stops if item is not None}
        volume_values = {item for item in volumes if item is not None}
        stop_changed = len(stop_values) >= 2
        volume_changed = len(volume_values) >= 2
        if stop_changed:
            protection_change += 1
        if volume_changed:
            volume_change += 1

        settlement_rows = grouped_settlements.get(key, ())
        has_execution_cost = any(
            _decimal_payload(item, "commission") is not None
            for item in settlement_rows
        )
        if has_execution_cost:
            cost_bound += 1

        if (
            len(ordered) >= 2
            and has_stop
            and has_execution_cost
            and (stop_changed or volume_changed)
        ):
            qualifying += 1

    stream_bound = (
        longitudinal > 0
        and reconciled_stop > 0
        and cost_bound > 0
    )
    blockers: list[str] = []
    if path_positions == 0:
        blockers.append("NO_FORWARD_BOUND_POSITION_PATH_SAMPLES")
    if longitudinal == 0:
        blockers.append("NO_LONGITUDINAL_POST_ENTRY_POSITION_PATH")
    if reconciled_stop == 0:
        blockers.append("NO_RECONCILED_CURRENT_STOP_PATH")
    if cost_bound == 0:
        blockers.append("NO_EXECUTION_COST_BOUND_PATH_POSITION")
    if qualifying == 0:
        blockers.append("NO_OBSERVED_T14_PROTECTION_OR_VOLUME_TRANSITION")

    return Phase20T14PathReadiness(
        stream_bound=stream_bound,
        observed_path_samples=path_samples,
        path_positions=path_positions,
        longitudinal_path_positions=longitudinal,
        reconciled_stop_positions=reconciled_stop,
        execution_cost_bound_positions=cost_bound,
        protection_change_positions=protection_change,
        volume_change_positions=volume_change,
        qualifying_intervention_positions=qualifying,
        blockers=tuple(blockers),
    )


def _evidence_kind(payload_json: str) -> object:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 T14 forward payload is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T14 forward payload must be object"
        )
    return payload.get("evidence_kind")


def _decimal_payload(
    event: LiveBehaviorEvent,
    key: str,
) -> Decimal | None:
    raw = event.payload.get(key)
    if raw is None:
        return None
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            f"Phase20 T14 behavior {key} is not Decimal-compatible"
        ) from error
    if not value.is_finite():
        raise CiboCapitalManagementError(
            f"Phase20 T14 behavior {key} must be finite"
        )
    return value
