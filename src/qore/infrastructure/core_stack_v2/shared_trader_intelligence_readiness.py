"""Machine-readable readiness gate for proactive Shared↔Trader intelligence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class SharedTraderIntelligenceReadinessStatus(StrEnum):
    NOT_READY = "NOT_READY"
    RESEARCH_READY = "RESEARCH_READY"
    PRE_ADMISSION_READY = "PRE_ADMISSION_READY"


@dataclass(frozen=True, slots=True)
class SharedTraderIntelligenceReadinessAssessment:
    status: SharedTraderIntelligenceReadinessStatus
    blockers: tuple[str, ...]
    contracts_frozen: bool
    sovereignty_tests_pass: bool
    anti_leakage_tests_pass: bool
    alert_lifecycle_tests_pass: bool
    position_lineage_tests_pass: bool
    historical_causal_replay_pass: bool
    opportunity_discovery_oos_pass: bool
    regime_transition_oos_pass: bool
    continuation_positive_tail_oos_pass: bool
    position_threat_oos_pass: bool
    control_treatment_attribution_pass: bool
    false_alert_gate_pass: bool
    missed_alert_gate_pass: bool
    winner_preservation_gate_pass: bool
    stress_validation_pass: bool
    temporal_replication_pass: bool
    runtime_sla_pass: bool
    trader_integration_certified_separately: bool
    cibo_read_only_contract_certified: bool
    governed_productive_promotion: bool
    productive_trader_behavior_change_authorized: bool = False
    productive_cibo_behavior_change_authorized: bool = False
    productive_risk_behavior_change_authorized: bool = False
    execution_behavior_change_authorized: bool = False

    def __post_init__(self) -> None:
        if self.blockers != tuple(sorted(set(self.blockers))):
            raise ValueError("STI readiness blockers must be unique and canonical")
        if (
            self.productive_trader_behavior_change_authorized
            or self.productive_cibo_behavior_change_authorized
            or self.productive_risk_behavior_change_authorized
            or self.execution_behavior_change_authorized
        ):
            raise ValueError(
                "STI readiness assessment cannot itself authorize runtime behavior"
            )
        if (
            self.status
            is SharedTraderIntelligenceReadinessStatus.PRE_ADMISSION_READY
            and self.blockers
        ):
            raise ValueError("PRE_ADMISSION_READY cannot retain blockers")
        if (
            self.status
            is not SharedTraderIntelligenceReadinessStatus.PRE_ADMISSION_READY
            and not self.blockers
        ):
            raise ValueError("non-ready STI assessment requires blockers")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["status"] = self.status.value
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def assess_shared_trader_intelligence_readiness(
    *,
    contracts_frozen: bool,
    sovereignty_tests_pass: bool,
    anti_leakage_tests_pass: bool,
    alert_lifecycle_tests_pass: bool,
    position_lineage_tests_pass: bool,
    historical_causal_replay_pass: bool,
    opportunity_discovery_oos_pass: bool,
    regime_transition_oos_pass: bool,
    continuation_positive_tail_oos_pass: bool,
    position_threat_oos_pass: bool,
    control_treatment_attribution_pass: bool,
    false_alert_gate_pass: bool,
    missed_alert_gate_pass: bool,
    winner_preservation_gate_pass: bool,
    stress_validation_pass: bool,
    temporal_replication_pass: bool,
    runtime_sla_pass: bool,
    trader_integration_certified_separately: bool,
    cibo_read_only_contract_certified: bool,
    governed_productive_promotion: bool,
) -> SharedTraderIntelligenceReadinessAssessment:
    blockers: list[str] = []

    checks = (
        (
            contracts_frozen,
            "TYPED_CONTRACTS_NOT_FROZEN",
        ),
        (
            sovereignty_tests_pass,
            "SOVEREIGNTY_TESTS_NOT_PASS",
        ),
        (
            anti_leakage_tests_pass,
            "ANTI_LEAKAGE_TESTS_NOT_PASS",
        ),
        (
            alert_lifecycle_tests_pass,
            "ALERT_LIFECYCLE_TESTS_NOT_PASS",
        ),
        (
            position_lineage_tests_pass,
            "POSITION_LINEAGE_TESTS_NOT_PASS",
        ),
        (
            historical_causal_replay_pass,
            "HISTORICAL_CAUSAL_REPLAY_NOT_PASS",
        ),
        (
            opportunity_discovery_oos_pass,
            "OPPORTUNITY_DISCOVERY_OOS_NOT_PASS",
        ),
        (
            regime_transition_oos_pass,
            "REGIME_TRANSITION_OOS_NOT_PASS",
        ),
        (
            continuation_positive_tail_oos_pass,
            "CONTINUATION_POSITIVE_TAIL_OOS_NOT_PASS",
        ),
        (
            position_threat_oos_pass,
            "POSITION_THREAT_OOS_NOT_PASS",
        ),
        (
            control_treatment_attribution_pass,
            "CONTROL_TREATMENT_ATTRIBUTION_NOT_PASS",
        ),
        (
            false_alert_gate_pass,
            "FALSE_ALERT_GATE_NOT_PASS",
        ),
        (
            missed_alert_gate_pass,
            "MISSED_ALERT_GATE_NOT_PASS",
        ),
        (
            winner_preservation_gate_pass,
            "WINNER_PRESERVATION_GATE_NOT_PASS",
        ),
        (
            stress_validation_pass,
            "STRESS_VALIDATION_NOT_PASS",
        ),
        (
            temporal_replication_pass,
            "TEMPORAL_REPLICATION_NOT_PASS",
        ),
        (
            runtime_sla_pass,
            "RUNTIME_SLA_NOT_PASS",
        ),
        (
            trader_integration_certified_separately,
            "TRADER_INTEGRATION_NOT_SEPARATELY_CERTIFIED",
        ),
        (
            cibo_read_only_contract_certified,
            "CIBO_READ_ONLY_CONTRACT_NOT_CERTIFIED",
        ),
        (
            governed_productive_promotion,
            "GOVERNED_PRODUCTIVE_PROMOTION_MISSING",
        ),
    )
    for passed, blocker in checks:
        if not passed:
            blockers.append(blocker)

    ordered_blockers = tuple(sorted(blockers))
    if not ordered_blockers:
        status = (
            SharedTraderIntelligenceReadinessStatus.PRE_ADMISSION_READY
        )
    else:
        research_foundation_ready = all(
            (
                contracts_frozen,
                sovereignty_tests_pass,
                anti_leakage_tests_pass,
                alert_lifecycle_tests_pass,
                position_lineage_tests_pass,
            )
        )
        if research_foundation_ready:
            status = SharedTraderIntelligenceReadinessStatus.RESEARCH_READY
        else:
            status = SharedTraderIntelligenceReadinessStatus.NOT_READY

    return SharedTraderIntelligenceReadinessAssessment(
        status=status,
        blockers=ordered_blockers,
        contracts_frozen=contracts_frozen,
        sovereignty_tests_pass=sovereignty_tests_pass,
        anti_leakage_tests_pass=anti_leakage_tests_pass,
        alert_lifecycle_tests_pass=alert_lifecycle_tests_pass,
        position_lineage_tests_pass=position_lineage_tests_pass,
        historical_causal_replay_pass=historical_causal_replay_pass,
        opportunity_discovery_oos_pass=opportunity_discovery_oos_pass,
        regime_transition_oos_pass=regime_transition_oos_pass,
        continuation_positive_tail_oos_pass=(
            continuation_positive_tail_oos_pass
        ),
        position_threat_oos_pass=position_threat_oos_pass,
        control_treatment_attribution_pass=(
            control_treatment_attribution_pass
        ),
        false_alert_gate_pass=false_alert_gate_pass,
        missed_alert_gate_pass=missed_alert_gate_pass,
        winner_preservation_gate_pass=winner_preservation_gate_pass,
        stress_validation_pass=stress_validation_pass,
        temporal_replication_pass=temporal_replication_pass,
        runtime_sla_pass=runtime_sla_pass,
        trader_integration_certified_separately=(
            trader_integration_certified_separately
        ),
        cibo_read_only_contract_certified=(
            cibo_read_only_contract_certified
        ),
        governed_productive_promotion=governed_productive_promotion,
    )
