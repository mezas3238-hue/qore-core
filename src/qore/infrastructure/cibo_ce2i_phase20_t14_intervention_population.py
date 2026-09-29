"""Natural post-entry intervention population audit for CE2I T14.

This audit does not invent a CIBO de-risk rule. It observes Trader-owned
management already emitted by the DEMO behavior ledger and asks whether a
causally ordered intervention dataset exists:

forward decision -> pre-intervention path sample -> Trader management event ->
post-intervention path sample with a physical stop/volume change -> later
terminal settlement.

Passive management telemetry is excluded. Eligibility uses identities, event
ordering and physical path changes only; realized PnL magnitudes are never read.
The resulting population can support later causal/OOS research, but does not
identify a CIBO T14 policy or grant management authority.
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
    TRADER_BEHAVIOR_CONTRACTS,
    BehaviorStage,
    LiveBehaviorEvent,
)

_INTERVENTION_TOKENS = (
    "STOP_ADVANCED",
    "_BE_",
    "TRAIL",
    "PARTIAL",
    "BANKED",
    "DOL1",
    "EQ50",
    "RUNNER",
    "PROTECT",
)


@dataclass(frozen=True, slots=True)
class Phase20T14NaturalInterventionPopulation:
    forward_bound_positions: int
    physical_management_positions: int
    management_events: int
    qualifying_interventions: int
    pre_post_path_positions: int
    protection_transition_positions: int
    volume_transition_positions: int
    terminally_settled_after_intervention_positions: int
    eligible_natural_intervention_positions: int
    represented_lineages: tuple[str, ...]
    trader_owned_management_preserved: bool
    cibo_derisk_policy_identified: bool
    fresh_oos_utility_demonstrated: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "forward_bound_positions",
            "physical_management_positions",
            "management_events",
            "qualifying_interventions",
            "pre_post_path_positions",
            "protection_transition_positions",
            "volume_transition_positions",
            "terminally_settled_after_intervention_positions",
            "eligible_natural_intervention_positions",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20 T14 population {name} must be non-negative int"
                )
        if len(self.represented_lineages) != len(
            set(self.represented_lineages)
        ):
            raise CiboCapitalManagementError(
                "Phase20 T14 represented lineages must be unique"
            )
        if any(
            lineage not in TRADER_BEHAVIOR_CONTRACTS
            for lineage in self.represented_lineages
        ):
            raise CiboCapitalManagementError(
                "Phase20 T14 population contains unknown Trader contract"
            )
        if not self.trader_owned_management_preserved:
            raise CiboCapitalManagementError(
                "Phase20 T14 must preserve Trader management sovereignty"
            )
        if (
            self.cibo_derisk_policy_identified
            or self.fresh_oos_utility_demonstrated
        ):
            raise CiboCapitalManagementError(
                "Phase20 T14 population audit cannot promote a policy"
            )
        for name in (
            "physical_management_positions",
            "pre_post_path_positions",
            "protection_transition_positions",
            "volume_transition_positions",
            "terminally_settled_after_intervention_positions",
            "eligible_natural_intervention_positions",
        ):
            if getattr(self, name) > self.forward_bound_positions:
                raise CiboCapitalManagementError(
                    f"Phase20 T14 {name} exceeds bound positions"
                )


def assess_phase20_t14_natural_intervention_population(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
    events: tuple[LiveBehaviorEvent, ...],
) -> Phase20T14NaturalInterventionPopulation:
    """Measure causal before/after Trader interventions without reading PnL."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "Phase20 T14 population requires canonical forward book"
        )
    if any(not isinstance(item, LiveBehaviorEvent) for item in events):
        raise CiboCapitalManagementError(
            "Phase20 T14 population requires canonical behavior events"
        )

    signal_decisions = _forward_signal_decisions(evidence_book)
    grouped: dict[tuple[str, int], list[LiveBehaviorEvent]] = {}
    for event in sorted(events, key=lambda item: item.observed_at):
        signal = event.signal_fingerprint
        position_id = event.position_id
        if signal is None or position_id is None:
            continue
        decision_at = signal_decisions.get(signal)
        if decision_at is None:
            continue
        if event.observed_at < decision_at:
            raise CiboCapitalManagementError(
                "Phase20 T14 behavior event predates forward decision"
            )
        grouped.setdefault((signal, position_id), []).append(event)

    management_positions = 0
    management_events = 0
    qualifying_interventions = 0
    pre_post_positions = 0
    protection_positions = 0
    volume_positions = 0
    settled_positions = 0
    eligible_positions = 0
    represented: set[str] = set()

    for rows in grouped.values():
        ordered = tuple(sorted(rows, key=lambda item: item.observed_at))
        paths = tuple(
            item
            for item in ordered
            if item.event == "CTRADER_DEMO_POSITION_PATH_SAMPLE"
        )
        interventions = tuple(
            item for item in ordered if _is_physical_management_event(item)
        )
        if not interventions:
            continue
        management_positions += 1
        management_events += len(interventions)

        position_pre_post = False
        position_protection = False
        position_volume = False
        position_settled = False
        position_eligible = False

        for intervention in interventions:
            trader = intervention.trader
            if trader is None or trader not in TRADER_BEHAVIOR_CONTRACTS:
                continue
            before = tuple(
                item
                for item in paths
                if item.observed_at < intervention.observed_at
            )
            after = tuple(
                item
                for item in paths
                if item.observed_at > intervention.observed_at
            )
            if not before or not after:
                continue
            pre = before[-1]
            post = after[0]
            stop_changed = _changed(pre, post, "stop_loss")
            volume_changed = _changed(pre, post, "volume")
            if not stop_changed and not volume_changed:
                continue

            qualifying_interventions += 1
            position_pre_post = True
            position_protection = position_protection or stop_changed
            position_volume = position_volume or volume_changed
            terminal_after = any(
                _is_terminal_settlement(item)
                and item.observed_at > intervention.observed_at
                for item in ordered
            )
            if terminal_after:
                position_settled = True
                position_eligible = True
                represented.add(trader)

        pre_post_positions += int(position_pre_post)
        protection_positions += int(position_protection)
        volume_positions += int(position_volume)
        settled_positions += int(position_settled)
        eligible_positions += int(position_eligible)

    blockers: list[str] = []
    if not grouped:
        blockers.append("NO_FORWARD_BOUND_T14_POSITION_EVENTS")
    if management_positions == 0:
        blockers.append("NO_TRADER_OWNED_PHYSICAL_MANAGEMENT_EVENTS")
    if pre_post_positions == 0:
        blockers.append("NO_T14_BEFORE_AFTER_PATH_AROUND_INTERVENTION")
    if qualifying_interventions == 0:
        blockers.append("NO_PHYSICAL_T14_STOP_OR_VOLUME_TRANSITION")
    if settled_positions == 0:
        blockers.append("NO_TERMINAL_SETTLEMENT_AFTER_T14_INTERVENTION")
    if eligible_positions == 0:
        blockers.append("NO_COMPLETE_T14_NATURAL_INTERVENTION_POSITION")
    blockers.extend(
        (
            "NATURAL_TRADER_INTERVENTIONS_DO_NOT_IDENTIFY_CIBO_DERISK_POLICY",
            "FRESH_OOS_DERISK_UTILITY_ANALYSIS_REQUIRED",
        )
    )

    return Phase20T14NaturalInterventionPopulation(
        forward_bound_positions=len(grouped),
        physical_management_positions=management_positions,
        management_events=management_events,
        qualifying_interventions=qualifying_interventions,
        pre_post_path_positions=pre_post_positions,
        protection_transition_positions=protection_positions,
        volume_transition_positions=volume_positions,
        terminally_settled_after_intervention_positions=settled_positions,
        eligible_natural_intervention_positions=eligible_positions,
        represented_lineages=tuple(sorted(represented)),
        trader_owned_management_preserved=True,
        cibo_derisk_policy_identified=False,
        fresh_oos_utility_demonstrated=False,
        blockers=tuple(blockers),
    )


def _forward_signal_decisions(
    evidence_book: VersionedPhase20ForwardEvidenceBook,
) -> dict[str, datetime]:
    result: dict[str, datetime] = {}
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
            previous = result.get(signal)
            if previous is not None and previous != decision.decision_at:
                raise CiboCapitalManagementError(
                    "Phase20 T14 signal maps to multiple decisions"
                )
            result[signal] = decision.decision_at
    return result


def _is_physical_management_event(event: LiveBehaviorEvent) -> bool:
    if event.stage is not BehaviorStage.MANAGEMENT:
        return False
    upper = event.event.upper()
    if upper == "CTRADER_DEMO_MANAGEMENT_OBSERVATION":
        return False
    return any(token in upper for token in _INTERVENTION_TOKENS)


def _is_terminal_settlement(event: LiveBehaviorEvent) -> bool:
    upper = event.event.upper()
    return (
        "SETTLEMENT" in upper
        and "PARTIAL" not in upper
        and "ENTRY_COST" not in upper
    )


def _changed(
    before: LiveBehaviorEvent,
    after: LiveBehaviorEvent,
    key: str,
) -> bool:
    left = _decimal_payload(before, key)
    right = _decimal_payload(after, key)
    return left is not None and right is not None and left != right


def _evidence_kind(payload_json: str) -> object:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "Phase20 T14 population forward payload invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "Phase20 T14 population forward payload must be object"
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
            f"Phase20 T14 population {key} is not Decimal-compatible"
        ) from error
    if not value.is_finite():
        raise CiboCapitalManagementError(
            f"Phase20 T14 population {key} must be finite"
        )
    return value
