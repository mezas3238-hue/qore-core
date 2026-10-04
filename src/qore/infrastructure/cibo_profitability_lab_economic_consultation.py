"""Causal CF01-CF19 consultation seam for the CIBO Profitability Lab.

The legacy capability exam proved that faculties existed, but it did not place
them on the economic decision path.  This module makes consultation a required
precondition of each historical economic policy decision without granting any
faculty sizing, Risk, order, execution, or broker authority.

The consultation is deliberately evidence-conservative.  It records that all
faculties were consulted against the predecision state and emits a REQUEST for
missing authority-rooted evidence.  It does not manufacture SUFFICIENT evidence
and never reads the later trade outcome.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from qore.infrastructure.cibo.contracts import (
    CiboEvidenceStatus,
    CiboFunctionalAuthority,
    CiboFunctionalEvidence,
)
from qore.infrastructure.cibo.functional_coordinator import (
    CiboCoordinationDisposition,
    CiboFacultyDomain,
    CiboFunctionalContribution,
    CiboFunctionalCoordinator,
)
from qore.infrastructure.cibo.mission_director import (
    CiboMissionDirector,
    CiboMissionDisposition,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_regime_selector import CiboCapitalRegimeState
from qore.infrastructure.cibo_profitability_lab_function_runtime import (
    CiboNativeFacultyRuntimeObservation,
    evaluate_cibo_native_faculties,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.kernel.result import Success

_FACULTY_SEQUENCE = (
    ("CF01", CiboFacultyDomain.FINANCIAL_WORLD_MONITORING, "financial-world-state-observed"),
    ("CF02", CiboFacultyDomain.MARKET_INTELLIGENCE_MESH, "market-regime-observed"),
    ("CF03", CiboFacultyDomain.TRADER_DIRECTOR, "trader-opportunity-set-observed"),
    ("CF04", CiboFacultyDomain.TRADER_ACADEMY, "trader-capability-evidence-requested"),
    ("CF05", CiboFacultyDomain.OPPORTUNITY_SEARCH, "opportunity-set-observed"),
    ("CF06", CiboFacultyDomain.PORTFOLIO_INTELLIGENCE, "portfolio-utilization-observed"),
    ("CF07", CiboFacultyDomain.ECONOMIC_INTELLIGENCE, "economic-evidence-requested"),
    ("CF08", CiboFacultyDomain.OUTCOME_JOURNAL, "outcome-unavailable-predecision"),
    ("CF09", CiboFacultyDomain.FAILURE_INTELLIGENCE, "failure-outcome-unavailable-predecision"),
    ("CF10", CiboFacultyDomain.QUANTITATIVE_INTELLIGENCE, "quantitative-state-observed"),
    ("CF11", CiboFacultyDomain.RESEARCH_DIRECTOR, "evidence-gap-identified"),
    ("CF12", CiboFacultyDomain.RISK_AWARE_RECOMMENDATION, "risk-authority-external"),
    ("CF13", CiboFacultyDomain.CORE_HEALTH, "runtime-governance-observed"),
    ("CF14", CiboFacultyDomain.EXECUTIVE_PLANNER, "evidence-sequencing-requested"),
    ("CF15", CiboFacultyDomain.CEO_DIALOGUE, "executive-context-observed"),
    ("CF16", CiboFacultyDomain.TRADER_VOICE, "trader-context-observed"),
    ("CF17", CiboFacultyDomain.DECISION_JOURNAL, "predecision-journal-observed"),
    ("CF18", CiboFacultyDomain.SELF_EVALUATION, "self-evaluation-deferred-predecision"),
    ("CF19", CiboFacultyDomain.LEARNING, "learning-deferred-until-settlement"),
)
_FUNCTION_CODE_BY_FACULTY = {
    faculty: function_code for function_code, faculty, _ in _FACULTY_SEQUENCE
}
_OUTPUT_CODE_BY_FACULTY = {
    faculty: output_code for _, faculty, output_code in _FACULTY_SEQUENCE
}


def _payload_sha256(payload: dict[str, object]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CiboFacultyEconomicConsultationReceipt:
    """Faculty-specific causal I/O consumed by the Functional Coordinator.

    These receipts expose real advisory work without elevating a faculty into
    sizing, Risk, execution, broker, or outcome authority.
    """

    function_code: str
    faculty: CiboFacultyDomain
    input_payload: dict[str, object]
    output_payload: dict[str, object]
    input_sha256: str
    output_sha256: str
    downstream_consumer: str = "cibo-functional-coordinator"
    consumer_action: str = "contribution-coordinated"
    decision_context_effect: str = "evidence-request-context"
    advisory_only: bool = True
    economic_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    outcome_used: bool = False

    def __post_init__(self) -> None:
        expected_function = _FUNCTION_CODE_BY_FACULTY.get(self.faculty)
        expected_output = _OUTPUT_CODE_BY_FACULTY.get(self.faculty)
        if self.function_code != expected_function:
            raise CiboCapitalManagementError(
                "faculty consultation function-code mapping drift"
            )
        if not isinstance(self.input_payload, dict) or not self.input_payload:
            raise CiboCapitalManagementError(
                "faculty consultation input payload required"
            )
        if not isinstance(self.output_payload, dict) or not self.output_payload:
            raise CiboCapitalManagementError(
                "faculty consultation output payload required"
            )
        if self.output_payload.get("contribution_code") != expected_output:
            raise CiboCapitalManagementError(
                "faculty consultation output-code mapping drift"
            )
        native_called = self.output_payload.get("native_engine_called")
        native_name = self.output_payload.get("native_engine_name")
        native_status = self.output_payload.get("native_engine_status")
        native_output = self.output_payload.get("native_engine_output")
        native_reason = self.output_payload.get("native_engine_reason")
        if type(native_called) is not bool:
            raise CiboCapitalManagementError(
                "faculty consultation native engine-called flag invalid"
            )
        if not isinstance(native_name, str) or not native_name:
            raise CiboCapitalManagementError(
                "faculty consultation native engine name missing"
            )
        if native_status not in {
            "SUCCESS",
            "FAIL_CLOSED",
            "DEPENDENCY_BLOCKED",
            "JUSTIFIED_NOT_APPLICABLE",
        }:
            raise CiboCapitalManagementError(
                "faculty consultation native engine status invalid"
            )
        if not isinstance(native_output, dict):
            raise CiboCapitalManagementError(
                "faculty consultation native engine output invalid"
            )
        if native_reason is not None and (
            not isinstance(native_reason, str) or not native_reason
        ):
            raise CiboCapitalManagementError(
                "faculty consultation native engine reason invalid"
            )
        if native_status == "JUSTIFIED_NOT_APPLICABLE" and native_called:
            raise CiboCapitalManagementError(
                "not-applicable faculty cannot claim native engine execution"
            )
        if native_status != "JUSTIFIED_NOT_APPLICABLE" and not native_called:
            raise CiboCapitalManagementError(
                "applicable faculty must execute its native engine"
            )
        if self.input_sha256 != _payload_sha256(self.input_payload):
            raise CiboCapitalManagementError(
                "faculty consultation input digest drift"
            )
        if self.output_sha256 != _payload_sha256(self.output_payload):
            raise CiboCapitalManagementError(
                "faculty consultation output digest drift"
            )
        if (
            self.downstream_consumer != "cibo-functional-coordinator"
            or self.consumer_action != "contribution-coordinated"
            or self.decision_context_effect != "evidence-request-context"
        ):
            raise CiboCapitalManagementError(
                "faculty consultation downstream binding drift"
            )
        for name in (
            "advisory_only",
            "economic_authority",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
            "outcome_used",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"faculty consultation {name} must be bool"
                )
        if (
            not self.advisory_only
            or self.economic_authority
            or self.sizing_authority
            or self.risk_authority
            or self.execution_authority
            or self.outcome_used
        ):
            raise CiboCapitalManagementError(
                "faculty consultation advisory authority boundary violated"
            )


@dataclass(frozen=True, slots=True)
class CiboEconomicConsultationReceipt:
    decision_at: datetime
    consultation_id: str
    consulted_faculties: tuple[str, ...]
    opportunity_fingerprints: tuple[str, ...]
    coordination_disposition: str
    coordination_request_code: str | None
    mission_code: str
    mission_faculties: tuple[str, ...]
    mission_disposition: str
    faculty_receipts: tuple[CiboFacultyEconomicConsultationReceipt, ...]
    causal_predecision: bool = True
    all_faculties_consulted: bool = True
    mission_director_invoked: bool = True
    functional_coordinator_invoked: bool = True
    economic_authority: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    execution_authority: bool = False
    outcome_used: bool = False
    broker_mutation: bool = False

    def __post_init__(self) -> None:
        if self.decision_at.tzinfo is None or self.decision_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "economic consultation decision_at must be timezone-aware"
            )
        if (
            not isinstance(self.consultation_id, str)
            or not self.consultation_id.startswith("sha256:")
            or len(self.consultation_id) != 71
        ):
            raise CiboCapitalManagementError(
                "economic consultation id must be canonical SHA-256"
            )
        expected = tuple(
            item.value for item in sorted(CiboFacultyDomain, key=lambda item: item.value)
        )
        if self.consulted_faculties != expected:
            raise CiboCapitalManagementError(
                "economic consultation requires exact CF01-CF19 faculty surface"
            )
        if self.mission_faculties != expected:
            raise CiboCapitalManagementError(
                "economic consultation Mission Director must assign CF01-CF19"
            )
        if not self.mission_code:
            raise CiboCapitalManagementError(
                "economic consultation mission code missing"
            )
        if self.mission_disposition != CiboMissionDisposition.CONTINUE.value:
            raise CiboCapitalManagementError(
                "economic consultation mission must remain CONTINUE/request-only"
            )
        if (
            not isinstance(self.faculty_receipts, tuple)
            or len(self.faculty_receipts) != len(_FACULTY_SEQUENCE)
            or any(
                not isinstance(item, CiboFacultyEconomicConsultationReceipt)
                for item in self.faculty_receipts
            )
        ):
            raise CiboCapitalManagementError(
                "economic consultation requires exact faculty-specific receipts"
            )
        expected_codes = tuple(item[0] for item in _FACULTY_SEQUENCE)
        observed_codes = tuple(item.function_code for item in self.faculty_receipts)
        if observed_codes != expected_codes:
            raise CiboCapitalManagementError(
                "economic consultation faculty receipt order/surface drift"
            )
        if tuple(item.faculty.value for item in self.faculty_receipts) != tuple(
            item[1].value for item in _FACULTY_SEQUENCE
        ):
            raise CiboCapitalManagementError(
                "economic consultation faculty receipt identity drift"
            )
        if len(self.opportunity_fingerprints) != len(
            set(self.opportunity_fingerprints)
        ):
            raise CiboCapitalManagementError(
                "economic consultation opportunity fingerprints must be unique"
            )
        for name in (
            "causal_predecision",
            "all_faculties_consulted",
            "mission_director_invoked",
            "functional_coordinator_invoked",
            "economic_authority",
            "sizing_authority",
            "risk_authority",
            "execution_authority",
            "outcome_used",
            "broker_mutation",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"economic consultation {name} must be bool"
                )
        if not self.causal_predecision or not self.all_faculties_consulted:
            raise CiboCapitalManagementError(
                "economic consultation must be complete and predecision"
            )
        if not self.mission_director_invoked or not self.functional_coordinator_invoked:
            raise CiboCapitalManagementError(
                "economic consultation requires current functional orchestration"
            )
        if any(
            (
                self.economic_authority,
                self.sizing_authority,
                self.risk_authority,
                self.execution_authority,
                self.outcome_used,
                self.broker_mutation,
            )
        ):
            raise CiboCapitalManagementError(
                "economic consultation cannot carry productive/outcome authority"
            )


def consult_cibo_economic_faculties(
    *,
    decision_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    regime_state: CiboCapitalRegimeState,
) -> CiboEconomicConsultationReceipt:
    """Consult all CF01-CF19 on the actual predecision economic path."""

    if decision_at.tzinfo is None or decision_at.utcoffset() is None:
        raise CiboCapitalManagementError(
            "economic consultation decision_at must be timezone-aware"
        )
    if not opportunities:
        raise CiboCapitalManagementError(
            "economic consultation requires at least one opportunity"
        )
    if not isinstance(regime_state, CiboCapitalRegimeState):
        raise CiboCapitalManagementError(
            "economic consultation requires canonical regime state"
        )
    if regime_state.opportunity_count != len(opportunities):
        raise CiboCapitalManagementError(
            "economic consultation regime opportunity count drift"
        )
    fingerprints = tuple(item.signal_fingerprint for item in opportunities)
    if len(fingerprints) != len(set(fingerprints)):
        raise CiboCapitalManagementError(
            "economic consultation duplicate opportunity fingerprint"
        )
    if any(not isinstance(item, TraderOpportunityEnvelope) for item in opportunities):
        raise CiboCapitalManagementError(
            "economic consultation requires TraderOpportunityEnvelope inputs"
        )

    predecision_digest = _predecision_digest(
        decision_at=decision_at,
        opportunities=opportunities,
        regime_state=regime_state,
    )
    evidence_ref = CiboEvidenceRef(
        "lab:predecision:" + predecision_digest[7:]
    )
    faculties = tuple(sorted(CiboFacultyDomain, key=lambda item: item.value))
    mission_result = CiboMissionDirector().direct(
        mission_code="cibo-economic-predecision",
        objective_code="evaluate-economic-predecision",
        constraint_codes=(
            "broker-mutation-forbidden",
            "no-outcome-use",
            "risk-authority-external",
            "sizing-authority-cma-only",
        ),
        assigned_functions=faculties,
        assigned_traders=(),
        readiness_codes=("runtime-predecision-ready",),
        missing_evidence_codes=("authority-rooted-evidence-required",),
        unresolved_uncertainty_codes=("economic-evidence-incomplete",),
        assignment_codes=("consult-all-cibo-functions",),
        hypothesis_codes=("predecision-evidence-supports-action",),
        success_criteria=("complete-cognitive-orchestration",),
        failure_criteria=("missing-cognitive-orchestration",),
        training_codes=(),
        demo_observation_codes=("historical-replay-observation",),
        baseline_codes=(),
        counterfactual_codes=(),
        disposition=CiboMissionDisposition.CONTINUE,
        lineage=("profitability-lab", "predecision"),
        unresolved_risk_codes=("external-risk-decision-pending",),
        planned_at=decision_at,
    )
    if not isinstance(mission_result, Success):
        raise CiboCapitalManagementError(
            "economic Mission Director orchestration failed closed"
        )
    mission = mission_result.value
    mission_faculties = tuple(item.value for item in mission.assigned_functions)
    if mission_faculties != tuple(item.value for item in faculties):
        raise CiboCapitalManagementError(
            "economic Mission Director faculty assignment drift"
        )

    native_rows = evaluate_cibo_native_faculties(
        decision_at=decision_at,
        opportunities=opportunities,
        regime_state=regime_state,
        evidence_ref=evidence_ref,
    )
    native_by_code = {item.function_code: item for item in native_rows}
    expected_codes = tuple(item[0] for item in _FACULTY_SEQUENCE)
    if tuple(native_by_code) != expected_codes:
        raise CiboCapitalManagementError(
            "economic consultation native CF01-CF19 surface drift"
        )
    faculty_receipts = tuple(
        _build_faculty_receipt(
            function_code=function_code,
            faculty=faculty,
            output_code=output_code,
            decision_at=decision_at,
            opportunities=opportunities,
            regime_state=regime_state,
            native_observation=native_by_code[function_code],
        )
        for function_code, faculty, output_code in _FACULTY_SEQUENCE
    )
    contributions = tuple(
        CiboFunctionalContribution(
            faculty=receipt.faculty,
            contribution_code=str(receipt.output_payload["contribution_code"]),
            subject_key=f"economic-decision-{receipt.function_code.lower()}",
            authority=CiboFunctionalAuthority.OBSERVATION,
            evidence=CiboFunctionalEvidence(
                status=CiboEvidenceStatus.INSUFFICIENT,
                evidence_refs=(evidence_ref,),
                as_of=decision_at,
                reasons=("authority-rooted-evidence-required",),
            ),
            authored_at=decision_at,
            provenance=("profitability-lab", "predecision", receipt.faculty.value),
        )
        for receipt in faculty_receipts
    )
    result = CiboFunctionalCoordinator().coordinate(
        contributions,
        coordinated_at=decision_at,
        request_code="economic.evidence.request",
    )
    if not isinstance(result, Success):
        raise CiboCapitalManagementError(
            "economic faculty coordination failed closed"
        )
    coordination = result.value
    consulted = tuple(item.faculty.value for item in coordination.contributions)
    if consulted != tuple(item.value for item in faculties):
        raise CiboCapitalManagementError(
            "economic faculty coordination surface drift"
        )
    if coordination.disposition is not CiboCoordinationDisposition.REQUEST:
        raise CiboCapitalManagementError(
            "economic faculty consultation must preserve evidence request"
        )

    return CiboEconomicConsultationReceipt(
        decision_at=decision_at,
        consultation_id=predecision_digest,
        consulted_faculties=consulted,
        opportunity_fingerprints=tuple(sorted(fingerprints)),
        coordination_disposition=coordination.disposition.value,
        coordination_request_code=coordination.request_code,
        mission_code=mission.mission_code,
        mission_faculties=mission_faculties,
        mission_disposition=mission.disposition.value,
        faculty_receipts=faculty_receipts,
    )


def _build_faculty_receipt(
    *,
    function_code: str,
    faculty: CiboFacultyDomain,
    output_code: str,
    decision_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    regime_state: CiboCapitalRegimeState,
    native_observation: CiboNativeFacultyRuntimeObservation,
) -> CiboFacultyEconomicConsultationReceipt:
    input_payload = _faculty_input_payload(
        faculty=faculty,
        decision_at=decision_at,
        opportunities=opportunities,
        regime_state=regime_state,
    )
    if native_observation.function_code != function_code:
        raise CiboCapitalManagementError(
            "faculty consultation/native runtime function-code drift"
        )
    output_payload: dict[str, object] = {
        "contribution_code": output_code,
        "evidence_status": CiboEvidenceStatus.INSUFFICIENT.value,
        "evidence_reason": "authority-rooted-evidence-required",
        "request_code": "economic.evidence.request",
        "advisory_only": True,
        "native_engine_called": native_observation.engine_called,
        "native_engine_name": native_observation.engine_name,
        "native_engine_status": native_observation.status,
        "native_engine_output": native_observation.output_payload,
        "native_engine_reason": native_observation.reason,
    }
    return CiboFacultyEconomicConsultationReceipt(
        function_code=function_code,
        faculty=faculty,
        input_payload=input_payload,
        output_payload=output_payload,
        input_sha256=_payload_sha256(input_payload),
        output_sha256=_payload_sha256(output_payload),
    )


def _faculty_input_payload(
    *,
    faculty: CiboFacultyDomain,
    decision_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    regime_state: CiboCapitalRegimeState,
) -> dict[str, object]:
    signals = tuple(sorted(item.signal_fingerprint for item in opportunities))
    symbols = tuple(sorted({item.qore_symbol for item in opportunities}))
    providers = tuple(sorted({item.provider_symbol for item in opportunities}))
    traders = tuple(sorted({item.trader_id.value for item in opportunities}))
    geometry = tuple(
        sorted(
            (
                item.signal_fingerprint,
                item.side,
                item.entry_type,
                str(item.intended_entry),
                str(item.stop_loss),
                str(item.take_profit),
            )
            for item in opportunities
        )
    )
    regime = {
        "liquidity": regime_state.liquidity.value,
        "volatility": regime_state.volatility.value,
        "correlation": regime_state.correlation.value,
        "provider_condition": regime_state.provider_condition.value,
    }
    utilization = {
        "risk_utilization": str(regime_state.risk_utilization),
        "margin_utilization": str(regime_state.margin_utilization),
        "drawdown_utilization": str(regime_state.drawdown_utilization),
    }
    if faculty is CiboFacultyDomain.FINANCIAL_WORLD_MONITORING:
        return {"decision_at": decision_at.isoformat(), "regime": regime}
    if faculty is CiboFacultyDomain.MARKET_INTELLIGENCE_MESH:
        return {"symbols": symbols, "regime": regime}
    if faculty is CiboFacultyDomain.TRADER_DIRECTOR:
        return {"traders": traders, "opportunity_count": len(opportunities)}
    if faculty is CiboFacultyDomain.TRADER_ACADEMY:
        return {"traders": traders, "signals": signals}
    if faculty is CiboFacultyDomain.OPPORTUNITY_SEARCH:
        return {"signals": signals, "symbols": symbols}
    if faculty is CiboFacultyDomain.PORTFOLIO_INTELLIGENCE:
        return {
            "opportunity_count": len(opportunities),
            "utilization": utilization,
            "correlation": regime_state.correlation.value,
        }
    if faculty is CiboFacultyDomain.ECONOMIC_INTELLIGENCE:
        return {
            "provider_symbols": providers,
            "provider_condition": regime_state.provider_condition.value,
            "opportunity_geometry": geometry,
        }
    if faculty is CiboFacultyDomain.OUTCOME_JOURNAL:
        return {
            "decision_at": decision_at.isoformat(),
            "signals": signals,
            "outcome_present": False,
        }
    if faculty is CiboFacultyDomain.FAILURE_INTELLIGENCE:
        return {
            "signals": signals,
            "outcome_present": False,
            "predecision_only": True,
        }
    if faculty is CiboFacultyDomain.QUANTITATIVE_INTELLIGENCE:
        return {"utilization": utilization, "opportunity_count": len(opportunities)}
    if faculty is CiboFacultyDomain.RESEARCH_DIRECTOR:
        return {
            "signals": signals,
            "evidence_gap": "authority-rooted-evidence-required",
        }
    if faculty is CiboFacultyDomain.RISK_AWARE_RECOMMENDATION:
        return {
            "utilization": utilization,
            "risk_authority": "external-qore-risk",
        }
    if faculty is CiboFacultyDomain.CORE_HEALTH:
        return {
            "runtime_path": "profitability-lab-predecision",
            "broker_mutation": False,
            "outcome_used": False,
        }
    if faculty is CiboFacultyDomain.EXECUTIVE_PLANNER:
        return {
            "opportunity_count": len(opportunities),
            "evidence_request": "economic.evidence.request",
        }
    if faculty is CiboFacultyDomain.CEO_DIALOGUE:
        return {
            "decision_at": decision_at.isoformat(),
            "decision_context": "research-only-predecision",
        }
    if faculty is CiboFacultyDomain.TRADER_VOICE:
        return {"traders": traders, "signals": signals}
    if faculty is CiboFacultyDomain.DECISION_JOURNAL:
        return {"decision_at": decision_at.isoformat(), "signals": signals}
    if faculty is CiboFacultyDomain.SELF_EVALUATION:
        return {
            "signals": signals,
            "outcome_present": False,
            "evaluation_stage": "predecision",
        }
    if faculty is CiboFacultyDomain.LEARNING:
        return {
            "signals": signals,
            "outcome_present": False,
            "learning_stage": "deferred-until-settlement",
        }
    raise CiboCapitalManagementError("unknown CIBO faculty in economic consultation")


def _predecision_digest(
    *,
    decision_at: datetime,
    opportunities: tuple[TraderOpportunityEnvelope, ...],
    regime_state: CiboCapitalRegimeState,
) -> str:
    payload = {
        "decision_at": decision_at.isoformat(),
        "opportunities": [
            {
                "signal_fingerprint": item.signal_fingerprint,
                "trader_id": item.trader_id.value,
                "qore_symbol": item.qore_symbol,
                "provider_symbol": item.provider_symbol,
                "side": item.side,
                "entry_type": item.entry_type,
                "intended_entry": str(item.intended_entry),
                "stop_loss": str(item.stop_loss),
                "take_profit": str(item.take_profit),
            }
            for item in sorted(
                opportunities,
                key=lambda item: item.signal_fingerprint,
            )
        ],
        "regime": {
            "liquidity": regime_state.liquidity.value,
            "volatility": regime_state.volatility.value,
            "correlation": regime_state.correlation.value,
            "provider_condition": regime_state.provider_condition.value,
            "risk_utilization": str(regime_state.risk_utilization),
            "margin_utilization": str(regime_state.margin_utilization),
            "drawdown_utilization": str(regime_state.drawdown_utilization),
            "opportunity_count": regime_state.opportunity_count,
        },
        "outcome_present": False,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()
