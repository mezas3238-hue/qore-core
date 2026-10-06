"""Read-only reach and contribution sensors for CIBO native cognition.

The sensor plane answers three different questions without collapsing them:

1. Reachability: did a cognitive component execute and how far did its output travel?
2. Decision influence: did it emit a blocker/gate or reach the executive/capital path?
3. Economic causality: did removing only that component change ending capital?

The third question is deliberately UNPROVEN until an individual frozen
counterfactual ablation is executed. The global cognition ablation cannot be
misreported as proof for any individual CF01-CF19 faculty.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_cognitive_attention import (
    ReasoningRouteDecision,
)
from qore.infrastructure.cibo_native_sovereign_capital_runtime import (
    CiboNativeSovereignCapitalDecision,
)


class CiboCognitiveContributionState(StrEnum):
    UNPROVEN = "UNPROVEN"
    ABLATION_PROVEN = "ABLATION_PROVEN"


@dataclass(frozen=True, slots=True)
class CiboCognitiveReachSensor:
    decision_id: str
    component_code: str
    component_kind: str
    stage_order: int
    status: str
    input_sha256: str
    output_sha256: str
    reached_stages: tuple[str, ...]
    downstream_consumer: str
    component_ablation_key: str
    native_engine_called: bool = True
    applicable: bool = True
    downstream_consumed: bool = True
    constraint_or_gate_emitted: bool = False
    reached_executive_synthesis: bool = True
    reached_capital_decision: bool = True
    contribution_state: CiboCognitiveContributionState = (
        CiboCognitiveContributionState.UNPROVEN
    )
    causal_ending_capital_delta_usd: Decimal | None = None
    productive_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "decision_id",
            "component_code",
            "component_kind",
            "status",
            "downstream_consumer",
            "component_ablation_key",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise CiboCapitalManagementError(
                    f"cognitive sensor {name} is required"
                )
        if (
            not isinstance(self.stage_order, int)
            or isinstance(self.stage_order, bool)
            or self.stage_order < 0
        ):
            raise CiboCapitalManagementError(
                "cognitive sensor stage_order must be non-negative int"
            )
        for name in ("input_sha256", "output_sha256"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCapitalManagementError(
                    f"cognitive sensor {name} must be sha256 digest"
                )
        if (
            not isinstance(self.reached_stages, tuple)
            or not self.reached_stages
            or any(
                not isinstance(item, str) or not item
                for item in self.reached_stages
            )
            or len(self.reached_stages) != len(set(self.reached_stages))
        ):
            raise CiboCapitalManagementError(
                "cognitive sensor reached_stages must be unique/non-empty"
            )
        for name in (
            "native_engine_called",
            "applicable",
            "downstream_consumed",
            "constraint_or_gate_emitted",
            "reached_executive_synthesis",
            "reached_capital_decision",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"cognitive sensor {name} must be bool"
                )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "cognitive sensors cannot acquire productive authority"
            )
        if not self.applicable and self.native_engine_called:
            raise CiboCapitalManagementError(
                "non-applicable cognitive component cannot claim execution"
            )
        if self.reached_capital_decision and not self.reached_executive_synthesis:
            raise CiboCapitalManagementError(
                "cognitive sensor cannot reach capital before executive synthesis"
            )
        if self.contribution_state is CiboCognitiveContributionState.UNPROVEN:
            if self.causal_ending_capital_delta_usd is not None:
                raise CiboCapitalManagementError(
                    "unproven cognitive sensor cannot claim economic contribution"
                )
        elif (
            not isinstance(self.causal_ending_capital_delta_usd, Decimal)
            or not self.causal_ending_capital_delta_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "ablation-proven cognitive sensor requires finite causal delta"
            )

    @property
    def max_reached_stage(self) -> str:
        return self.reached_stages[-1]

    def payload(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "component_code": self.component_code,
            "component_kind": self.component_kind,
            "stage_order": self.stage_order,
            "status": self.status,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "reached_stages": list(self.reached_stages),
            "max_reached_stage": self.max_reached_stage,
            "downstream_consumer": self.downstream_consumer,
            "component_ablation_key": self.component_ablation_key,
            "native_engine_called": self.native_engine_called,
            "applicable": self.applicable,
            "downstream_consumed": self.downstream_consumed,
            "constraint_or_gate_emitted": self.constraint_or_gate_emitted,
            "reached_executive_synthesis": self.reached_executive_synthesis,
            "reached_capital_decision": self.reached_capital_decision,
            "contribution_state": self.contribution_state.value,
            "causal_ending_capital_delta_usd": (
                None
                if self.causal_ending_capital_delta_usd is None
                else format(self.causal_ending_capital_delta_usd, "f")
            ),
            "productive_authority": False,
        }


def _sha(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _internal_sensor(
    *,
    decision_id: str,
    code: str,
    order: int,
    status: str,
    input_payload: object,
    output_payload: object,
    reached_stages: tuple[str, ...],
    consumer: str,
    gate: bool = False,
) -> CiboCognitiveReachSensor:
    return CiboCognitiveReachSensor(
        decision_id=decision_id,
        component_code=code,
        component_kind="COGNITIVE_SUBSTRATE",
        stage_order=order,
        status=status,
        input_sha256=_sha(input_payload),
        output_sha256=_sha(output_payload),
        reached_stages=reached_stages,
        downstream_consumer=consumer,
        component_ablation_key="cognition:" + code.lower(),
        native_engine_called=True,
        applicable=True,
        downstream_consumed=True,
        constraint_or_gate_emitted=gate,
        reached_executive_synthesis=True,
        reached_capital_decision=True,
        contribution_state=CiboCognitiveContributionState.UNPROVEN,
        causal_ending_capital_delta_usd=None,
        productive_authority=False,
    )


def build_native_cognitive_reach_sensors(
    native_decision: CiboNativeSovereignCapitalDecision,
) -> tuple[CiboCognitiveReachSensor, ...]:
    """Trace CF01-CF19 and the deeper MAX cognition substrate to capital."""

    if not isinstance(native_decision, CiboNativeSovereignCapitalDecision):
        raise CiboCapitalManagementError(
            "cognitive sensor builder requires Native MAX sovereign decision"
        )

    decision_id = native_decision.capital.decision_id
    consultation = native_decision.consultation
    intelligence = native_decision.intelligence
    episode = intelligence.cognitive_episode
    synthesis = intelligence.synthesis
    blocked = set(intelligence.blocked_function_codes)

    sensors: list[CiboCognitiveReachSensor] = []

    perception_payload = tuple(intelligence.perception_key_counts)
    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="NATIVE_PERCEPTION",
            order=1,
            status="SUCCESS",
            input_payload={
                "consultation_id": consultation.consultation_id,
                "opportunity_count": len(
                    consultation.opportunity_fingerprints
                ),
            },
            output_payload={
                "perception_key_counts": perception_payload,
            },
            reached_stages=(
                "PERCEPTION",
                "NATIVE_MAX",
                "COGNITIVE_EPISODE",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-maximum-intelligence",
        )
    )

    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="MISSION_DIRECTOR",
            order=2,
            status=consultation.mission_disposition,
            input_payload={
                "mission_code": consultation.mission_code,
                "faculties": consultation.mission_faculties,
            },
            output_payload={
                "invoked": consultation.mission_director_invoked,
                "disposition": consultation.mission_disposition,
            },
            reached_stages=(
                "MISSION_DIRECTOR",
                "FUNCTIONAL_COORDINATOR",
                "NATIVE_MAX",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="cibo-functional-coordinator",
        )
    )

    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="FUNCTIONAL_COORDINATOR",
            order=3,
            status=consultation.coordination_disposition,
            input_payload={
                "faculty_count": len(consultation.faculty_receipts),
                "request_code": consultation.coordination_request_code,
            },
            output_payload={
                "invoked": consultation.functional_coordinator_invoked,
                "disposition": consultation.coordination_disposition,
            },
            reached_stages=(
                "FUNCTIONAL_COORDINATOR",
                "SEMANTIC_DIGEST",
                "COGNITIVE_EPISODE",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-maximum-intelligence",
        )
    )

    for index, receipt in enumerate(consultation.faculty_receipts, start=1):
        output = receipt.output_payload
        native_called = output["native_engine_called"]
        native_status = str(output["native_engine_status"])
        applicable = native_status != "JUSTIFIED_NOT_APPLICABLE"
        stages = ["FACULTY_INPUT"]
        if native_called:
            stages.append("NATIVE_FACULTY_ENGINE")
        stages.extend(
            (
                "FUNCTIONAL_COORDINATOR",
                "SEMANTIC_DIGEST",
                "COGNITIVE_EPISODE",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            )
        )
        sensors.append(
            CiboCognitiveReachSensor(
                decision_id=decision_id,
                component_code=receipt.function_code,
                component_kind="FACULTY",
                stage_order=10 + index,
                status=native_status,
                input_sha256=receipt.input_sha256,
                output_sha256=receipt.output_sha256,
                reached_stages=tuple(stages),
                downstream_consumer=receipt.downstream_consumer,
                component_ablation_key=(
                    "cognition:" + receipt.function_code.lower()
                ),
                native_engine_called=native_called,
                applicable=applicable,
                downstream_consumed=True,
                constraint_or_gate_emitted=(
                    receipt.function_code in blocked
                ),
                reached_executive_synthesis=True,
                reached_capital_decision=True,
                contribution_state=(
                    CiboCognitiveContributionState.UNPROVEN
                ),
                causal_ending_capital_delta_usd=None,
                productive_authority=False,
            )
        )

    world = episode.world_snapshot
    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="WORLD_MODEL",
            order=40,
            status="SUCCESS",
            input_payload={
                "semantic_digest": intelligence.semantic_digest,
                "faculty_count": len(consultation.faculty_receipts),
            },
            output_payload={
                "snapshot_id": str(world.snapshot_id),
                "fingerprint": world.fingerprint.value,
                "reference_count": len(world.references),
                "contradiction_count": len(world.contradictions),
            },
            reached_stages=(
                "WORLD_MODEL",
                "ATTENTION",
                "SCENARIOS",
                "INTEGRATED_EPISODE",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-max-attention-and-integration",
        )
    )

    selected = episode.selected_context
    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="ATTENTION_CONTEXT",
            order=41,
            status="SUCCESS",
            input_payload={
                "world_fingerprint": world.fingerprint.value,
            },
            output_payload={
                "ranked_signal_count": len(selected.ranked),
                "ranked_signal_kinds": tuple(
                    item.signal.kind.value for item in selected.ranked
                ),
            },
            reached_stages=(
                "ATTENTION",
                "REASONING_ROUTING",
                "CALIBRATION",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-max-reasoning-routing",
        )
    )

    routing = episode.reasoning_routing
    routing_gate = (
        routing.decision
        is ReasoningRouteDecision.ABSTAIN_INSUFFICIENT_EVIDENCE
    )
    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="REASONING_ROUTING",
            order=42,
            status=routing.decision.value,
            input_payload={
                "ranked_signal_count": len(selected.ranked),
            },
            output_payload={
                "decision": routing.decision.value,
                "reasons": routing.reasons,
                "requested_evidence": routing.requested_evidence,
            },
            reached_stages=(
                "REASONING_ROUTING",
                "CALIBRATION",
                "SCENARIOS",
                "METACOGNITION",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-max-calibration-and-synthesis",
            gate=routing_gate,
        )
    )

    calibration = episode.calibration
    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="CALIBRATION",
            order=43,
            status=calibration.kind,
            input_payload={
                "routing_decision": routing.decision.value,
            },
            output_payload={
                "confidence_band": calibration.confidence_band,
                "abstention_required": calibration.abstention_required,
                "note": calibration.note,
            },
            reached_stages=(
                "CALIBRATION",
                "UNCERTAINTY",
                "SCENARIOS",
                "METACOGNITION",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-max-uncertainty-and-synthesis",
            gate=calibration.abstention_required,
        )
    )

    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="SCENARIO_ENGINE",
            order=44,
            status="SUCCESS",
            input_payload={
                "uncertainty": episode.uncertainty.kind.value,
                "abstention_required": episode.abstention_required,
            },
            output_payload={
                "scenario_count": len(episode.scenarios),
                "families": tuple(
                    scenario.family.value for scenario in episode.scenarios
                ),
                "abstained_count": sum(
                    scenario.abstained for scenario in episode.scenarios
                ),
            },
            reached_stages=(
                "SCENARIOS",
                "INTEGRATED_EPISODE",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-max-integrated-episode",
        )
    )

    causal = episode.causal_claim
    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="CAUSAL_REASONING",
            order=45,
            status=causal.status.value,
            input_payload={
                "semantic_digest": intelligence.semantic_digest,
            },
            output_payload={
                "kind": causal.kind.value,
                "cause": causal.cause.code,
                "effect": causal.effect.code,
                "strength": causal.strength.value,
                "status": causal.status.value,
                "evidence_for_count": len(causal.evidence_for),
                "evidence_against_count": len(causal.evidence_against),
                "contradiction_count": len(causal.contradictions),
            },
            reached_stages=(
                "CAUSALITY",
                "INTEGRATED_EPISODE",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-max-integrated-episode",
        )
    )

    audit = episode.metacognitive_audit
    meta_gate = audit.evidence_sufficiency.value != "sufficient"
    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="METACOGNITION",
            order=46,
            status=audit.evidence_sufficiency.value,
            input_payload={
                "routing_decision": routing.decision.value,
                "calibration_kind": calibration.kind,
            },
            output_payload={
                "evidence_sufficiency": audit.evidence_sufficiency.value,
                "missing_role_count": len(audit.missing_roles),
                "reason_codes": audit.reason_codes,
                "fingerprint": audit.fingerprint.value,
            },
            reached_stages=(
                "METACOGNITION",
                "INTEGRATED_EPISODE",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="native-max-integrated-episode",
            gate=meta_gate,
        )
    )

    integrated = episode.integrated_episode
    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="COGNITIVE_INTEGRATION",
            order=47,
            status="SUCCESS",
            input_payload={
                "world_fingerprint": world.fingerprint.value,
                "causal_fingerprint": causal.fingerprint.value,
                "metacognitive_fingerprint": audit.fingerprint.value,
                "scenario_count": len(episode.scenarios),
            },
            output_payload={
                "integration_id": str(integrated.integration_id),
                "fingerprint": integrated.fingerprint.value,
                "evidence_binding_count": len(
                    integrated.evidence_bindings
                ),
            },
            reached_stages=(
                "INTEGRATED_EPISODE",
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="cibo-executive-brain",
        )
    )

    sensors.append(
        _internal_sensor(
            decision_id=decision_id,
            code="EXECUTIVE_SYNTHESIS",
            order=48,
            status=synthesis.directive.value,
            input_payload={
                "consultation_id": intelligence.consultation_id,
                "semantic_digest": intelligence.semantic_digest,
                "cognitive_episode_fingerprint": (
                    integrated.fingerprint.value
                ),
            },
            output_payload={
                "directive": synthesis.directive.value,
                "reasoning_mode": synthesis.reasoning_mode.value,
                "uncertainty": synthesis.uncertainty.kind.value,
                "observation_count": len(synthesis.observations),
                "limitation_count": len(synthesis.limitations),
            },
            reached_stages=(
                "EXECUTIVE_SYNTHESIS",
                "CAPITAL_DECISION",
            ),
            consumer="cibo-sovereign-capital-runtime",
            gate=episode.abstention_required,
        )
    )

    codes = tuple(item.component_code for item in sensors)
    if len(codes) != len(set(codes)):
        raise CiboCapitalManagementError(
            "cognitive sensor component codes must be unique per decision"
        )
    return tuple(sorted(sensors, key=lambda item: item.stage_order))


def summarize_cognitive_reach_sensors(
    sensors: Iterable[CiboCognitiveReachSensor],
    *,
    full_ending_capital_usd: Decimal | None = None,
    global_cognition_ablation_ending_capital_usd: Decimal | None = None,
    component_ablation_ending_capital_usd: (
        Mapping[str, Decimal] | None
    ) = None,
) -> dict[str, object]:
    """Report reach separately from individual causal contribution."""

    rows = tuple(sensors)
    if any(not isinstance(item, CiboCognitiveReachSensor) for item in rows):
        raise CiboCapitalManagementError(
            "cognitive sensor summary requires canonical sensor receipts"
        )

    if full_ending_capital_usd is not None and (
        not isinstance(full_ending_capital_usd, Decimal)
        or not full_ending_capital_usd.is_finite()
    ):
        raise CiboCapitalManagementError(
            "cognitive sensor full ending capital must be finite Decimal"
        )

    component_ablations = dict(
        component_ablation_ending_capital_usd or {}
    )
    for key, value in component_ablations.items():
        if (
            not isinstance(key, str)
            or not key.startswith("cognition:")
            or not isinstance(value, Decimal)
            or not value.is_finite()
        ):
            raise CiboCapitalManagementError(
                "cognitive component ablation evidence is malformed"
            )

    by_component: dict[str, list[CiboCognitiveReachSensor]] = defaultdict(list)
    for sensor in rows:
        by_component[sensor.component_code].append(sensor)

    components: dict[str, object] = {}
    for code, group in sorted(by_component.items()):
        keys = {item.component_ablation_key for item in group}
        if len(keys) != 1:
            raise CiboCapitalManagementError(
                "cognitive component ablation key drift"
            )
        ablation_key = next(iter(keys))
        without = component_ablations.get(ablation_key)
        delta = (
            None
            if without is None or full_ending_capital_usd is None
            else full_ending_capital_usd - without
        )
        contribution_class = (
            "UNPROVEN"
            if delta is None
            else "POSITIVE_CONTRIBUTOR"
            if delta > 0
            else "ECONOMIC_DRAG"
            if delta < 0
            else "NO_MEASURED_EFFECT"
        )
        components[code] = {
            "event_count": len(group),
            "applicable_count": sum(item.applicable for item in group),
            "native_engine_called_count": sum(
                item.native_engine_called for item in group
            ),
            "downstream_consumed_count": sum(
                item.downstream_consumed for item in group
            ),
            "constraint_or_gate_count": sum(
                item.constraint_or_gate_emitted for item in group
            ),
            "reached_executive_synthesis_count": sum(
                item.reached_executive_synthesis for item in group
            ),
            "reached_capital_decision_count": sum(
                item.reached_capital_decision for item in group
            ),
            "max_reached_stage_counts": {
                stage: sum(
                    item.max_reached_stage == stage for item in group
                )
                for stage in sorted(
                    {item.max_reached_stage for item in group}
                )
            },
            "component_ablation_key": ablation_key,
            "individual_contribution_state": (
                CiboCognitiveContributionState.ABLATION_PROVEN.value
                if without is not None
                else CiboCognitiveContributionState.UNPROVEN.value
            ),
            "ending_capital_without_component_usd": (
                None if without is None else format(without, "f")
            ),
            "individual_delta_ending_capital_vs_full_usd": (
                None if delta is None else format(delta, "f")
            ),
            "economic_contribution_class": contribution_class,
        }

    global_delta = None
    if global_cognition_ablation_ending_capital_usd is not None:
        if (
            full_ending_capital_usd is None
            or not isinstance(
                global_cognition_ablation_ending_capital_usd,
                Decimal,
            )
            or not global_cognition_ablation_ending_capital_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "global cognition ablation requires finite full/ablation capital"
            )
        global_delta = format(
            full_ending_capital_usd
            - global_cognition_ablation_ending_capital_usd,
            "f",
        )

    return {
        "sensor_count": len(rows),
        "component_count": len(components),
        "components": components,
        "global_cognition_ablation": {
            "state": (
                CiboCognitiveContributionState.ABLATION_PROVEN.value
                if global_delta is not None
                else CiboCognitiveContributionState.UNPROVEN.value
            ),
            "delta_ending_capital_vs_full_usd": global_delta,
            "does_not_prove_individual_component_contribution": True,
        },
        "individual_component_ablation_required_for_who_contributes": True,
        "productive_authority": False,
    }
