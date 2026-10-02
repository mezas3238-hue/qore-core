"""Canonical source adapters for CIBO Scientific Closure 41.

The closure package is deliberately downstream of existing frozen evaluators.
This module converts only canonical, already-evaluated source objects into the
machine-readable 41-workstream evidence contract.  It does not execute
Phase22, reinterpret WAITING states, tune thresholds, mutate the master ledger,
or grant productive authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from qore.infrastructure.cibo_arch2_fresh_oos_terminal_intake import (
    Architect2FreshOOSTerminalIntake,
)
from qore.infrastructure.cibo_arch2_t02_terminal_disposition import (
    T02TerminalDispositionAssessment,
)
from qore.infrastructure.cibo_arch2_t11_gross_edge_oos import (
    T11GrossEdgeFreshOOSResult,
)
from qore.infrastructure.cibo_arch2_t11_market_impact_terminal_receipt import (
    T11MarketImpactTerminalReceipt,
)
from qore.infrastructure.cibo_arch2_t11_terminal_disposition import (
    T11TerminalDispositionAssessment,
    T11TerminalRecommendation,
)
from qore.infrastructure.cibo_arch2_t20_terminal_receipt import (
    T20TerminalReceipt,
)
from qore.infrastructure.cibo_arch_a_internal_readiness import (
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM,
    ArchitectAPhase22V2ScientificDispositionReceipt,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_usd60_six_month_certification import (
    FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL,
    CiboMaximumCapabilityClassification,
    CiboMaximumCapabilityGateSet,
    classify_cibo_maximum_capability,
)
from qore.infrastructure.cibo_integrated_capital_truth import (
    IntegratedCapitalTruth,
)
from qore.infrastructure.cibo_phase22_demo_empirical_provider_receipt import (
    ARTIFACT_DIGEST as PROVIDER_ARTIFACT_DIGEST,
)
from qore.infrastructure.cibo_scientific_closure_41 import (
    CANONICAL_POLICY_IDENTITY,
    CANONICAL_PROVIDER_IDENTITY,
    COMPLETED,
    FALSIFIED,
    FRESH_OOS_ID,
    OPEN_PREIMAGE,
    SCIENTIFIC_CLOSURE_41_IDS,
    ScientificClosure41Evidence,
    ScientificClosure41Package,
    build_scientific_closure_41_package,
)

DEPENDENCY_SCHEMA = "QORE_CIBO_SCIENTIFIC_CLOSURE_41_DEPENDENCIES_V1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# Legacy source surfaces remain importable because several already-built gates
# still emit these canonical receipt types. They are not the current ownership
# split for certification closure.
ARCHITECT_A_35_IDS = tuple(
    _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM
)
SPECIAL_6_IDS = (
    "T02",
    "T11",
    "T20",
    "FRESH_OOS",
    "USD60_CAPABILITY_PROGRAM",
    "INTEGRATED_CAPITAL_TRUTH",
)

GROUP2_CAPITAL_13_IDS = (
    "COMPOUND_ENGINE",
    "COMPOUND_PORTFOLIO",
    "INTERNAL_CAPITAL_MARKET",
    "CAPITAL_GENERATIONS",
    "PROTECTED_BASE_CAPITAL",
    "PROFIT_PROTECTION",
    "PATH_DEPENDENT_MONTE_CARLO",
    "ADVERSARIAL_STRESS",
    "TEMPORAL_REPLICATION",
    "CAPITAL_AMPLIFICATION",
    "AS_IS_ECONOMIC_BASELINE",
    "USD60_CAPABILITY_PROGRAM",
    "INTEGRATED_CAPITAL_TRUTH",
)
_GROUP2_SET = frozenset(GROUP2_CAPITAL_13_IDS)
GROUP1_28_IDS = tuple(
    workstream_id
    for workstream_id in SCIENTIFIC_CLOSURE_41_IDS
    if workstream_id not in _GROUP2_SET
)
ARCHITECT_A_GROUP2_11_IDS = tuple(
    workstream_id
    for workstream_id in GROUP2_CAPITAL_13_IDS
    if workstream_id in _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM
)

if (
    len(GROUP1_28_IDS) != 28
    or len(GROUP2_CAPITAL_13_IDS) != 13
    or set(GROUP1_28_IDS) & set(GROUP2_CAPITAL_13_IDS)
    or set(GROUP1_28_IDS) | set(GROUP2_CAPITAL_13_IDS)
    != set(SCIENTIFIC_CLOSURE_41_IDS)
    or len(ARCHITECT_A_GROUP2_11_IDS) != 11
):
    raise RuntimeError("Scientific closure 41 group ownership partition drift")

_SPECIAL_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "T02": (
        "T02_FORWARD_STRUCTURAL_AUDIT",
        "T02_PROVIDER_BOUND_ECONOMIC_ABLATION",
    ),
    "T11": (
        "SEALED_DEMO_PROVIDER_EXECUTION_AND_SLIPPAGE",
        "T11_MARKET_IMPACT_EVALUATION",
        "T11_FRESH_OOS_GROSS_EDGE",
    ),
    "T20": (
        "T20_FORWARD_RELEASE_QUALIFICATION",
        "T20_TERMINAL_RELEASE_RECEIPT",
    ),
    "FRESH_OOS": (
        "PHASE22_DURABLE_EXECUTION_CONSUMPTION_RECEIPT",
        "PHASE22_V4_HOLDOUT_QUALIFICATION_REPORT",
    ),
    "USD60_CAPABILITY_PROGRAM": (
        "USD60_FROZEN_MAXIMUM_CAPABILITY_GATE_SET",
        "USD60_MAXIMUM_CAPABILITY_CLASSIFICATION",
    ),
    "INTEGRATED_CAPITAL_TRUTH": (
        "SOURCE_LEDGER_AND_COMPOUND_STATE_BINDING",
        "SETTLEMENT_PROVENANCE",
        "ZERO_EQUIVALENCE_RESIDUAL",
        "ZERO_NONCONSUMED_RESIDUAL",
        "ZERO_DOUBLE_COUNTING",
    ),
}


@dataclass(frozen=True, slots=True)
class CanonicalScientificBinding:
    """Immutable artifact metadata shared by one canonical source adapter."""

    scientific_hypothesis: str
    evidence_refs: tuple[str, ...]
    evidence_sha256s: tuple[str, ...]
    population_identity: str
    causal_lineage: str
    economic_result: str
    stress_result: str
    temporal_replication_result: str
    integrity_result: str
    evaluated_at: datetime
    evidence_origin: str = "CANONICAL_GATE_RECEIPT"

    def __post_init__(self) -> None:
        if not self.scientific_hypothesis.strip():
            raise CiboCapitalManagementError(
                "Canonical scientific binding hypothesis required"
            )
        if (
            not self.evidence_refs
            or len(self.evidence_refs) != len(set(self.evidence_refs))
            or any(not item for item in self.evidence_refs)
        ):
            raise CiboCapitalManagementError(
                "Canonical scientific binding evidence refs invalid"
            )
        if len(self.evidence_sha256s) != len(set(self.evidence_sha256s)):
            raise CiboCapitalManagementError(
                "Canonical scientific binding duplicate digest"
            )
        for digest in self.evidence_sha256s:
            if _SHA256_RE.fullmatch(digest) is None:
                raise CiboCapitalManagementError(
                    "Canonical scientific binding evidence digest invalid"
                )
        if not self.population_identity.strip():
            raise CiboCapitalManagementError(
                "Canonical scientific binding population identity required"
            )
        if _SHA256_RE.fullmatch(self.causal_lineage) is None:
            raise CiboCapitalManagementError(
                "Canonical scientific binding causal lineage invalid"
            )
        for name in (
            "economic_result",
            "stress_result",
            "temporal_replication_result",
        ):
            if getattr(self, name) not in {"PASS", "FAIL", "NOT_APPLICABLE"}:
                raise CiboCapitalManagementError(
                    f"Canonical scientific binding {name} invalid"
                )
        if self.integrity_result not in {"PASS", "FAIL"}:
            raise CiboCapitalManagementError(
                "Canonical scientific binding integrity result invalid"
            )
        if (
            self.evaluated_at.tzinfo is None
            or self.evaluated_at.utcoffset() is None
        ):
            raise CiboCapitalManagementError(
                "Canonical scientific binding evaluated_at must be aware"
            )


def scientific_closure_41_dependency_manifest() -> dict[str, object]:
    """Describe the frozen evidence consumers without inventing future digests."""

    rows: list[dict[str, object]] = []
    for workstream_id in SCIENTIFIC_CLOSURE_41_IDS:
        if workstream_id in _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM:
            requirements = _PHASE22_V2_EVIDENCE_REQUIREMENTS_BY_WORKSTREAM[
                workstream_id
            ]
        else:
            requirements = _SPECIAL_REQUIREMENTS[workstream_id]
        row: dict[str, object] = {
            "workstream_id": workstream_id,
            "owner_group": (
                "GROUP2_CAPITAL_COMPOUND"
                if workstream_id in _GROUP2_SET
                else "GROUP1_V4_FRESH_CE2I_GENC"
            ),
            "required_evidence_kinds": list(requirements),
            "future_artifact_digest_policy": "REQUIRED_AT_INTAKE",
        }
        if workstream_id == "T11":
            row["already_sealed_provider_artifact_sha256"] = (
                PROVIDER_ARTIFACT_DIGEST
            )
        rows.append(row)
    return {
        "schema": DEPENDENCY_SCHEMA,
        "workstream_count": 41,
        "group1_v4_fresh_ce2i_genc_count": 28,
        "group2_capital_compound_count": 13,
        "legacy_architect_a_existing_consumer_count": 35,
        "legacy_special_canonical_adapter_count": 6,
        "workstreams": rows,
        "unknown_future_digests_fabricated": False,
        "productive_authority": False,
    }


def adapt_architect_a_scientific_receipt(
    *,
    receipt: ArchitectAPhase22V2ScientificDispositionReceipt,
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    if not isinstance(
        receipt,
        ArchitectAPhase22V2ScientificDispositionReceipt,
    ):
        raise CiboCapitalManagementError(
            "Closure 41 Architect-A adapter requires canonical receipt"
        )
    if receipt.workstream_id not in ARCHITECT_A_GROUP2_11_IDS:
        raise CiboCapitalManagementError(
            "Closure 41 Group-2 capital adapter ownership drift"
        )
    if receipt.recommended_disposition not in {COMPLETED, FALSIFIED}:
        raise CiboCapitalManagementError(
            "Closure 41 Architect-A receipt is not terminal"
        )
    if receipt.source_gate_status not in {"PASS", "FAIL"}:
        raise CiboCapitalManagementError(
            "Closure 41 Architect-A source gate is not terminal"
        )
    return _build_evidence(
        workstream_id=receipt.workstream_id,
        phase22_manifest_sha256=receipt.phase22_manifest_sha256,
        source_gate_status=receipt.source_gate_status,
        recommendation=receipt.recommended_disposition,
        terminal_reason=(
            "Canonical Architect-A frozen scientific gate disposition."
        ),
        failed_dimensions=receipt.failed_dimensions,
        source_kind="ARCHITECT_A_PHASE22_V2_SCIENTIFIC_DISPOSITION",
        source_object=receipt,
        source_refs=(receipt.source_gate_id,),
        source_digests=(receipt.source_gate_evidence_sha256,),
        binding=binding,
    )


def adapt_t02_terminal_assessment(
    *,
    assessment: T02TerminalDispositionAssessment,
    phase22_manifest_sha256: str,
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    if not isinstance(assessment, T02TerminalDispositionAssessment):
        raise CiboCapitalManagementError(
            "Closure 41 T02 adapter requires canonical assessment"
        )
    if not assessment.terminal_ready or assessment.recommendation not in {
        COMPLETED,
        FALSIFIED,
    }:
        raise CiboCapitalManagementError(
            "Closure 41 T02 assessment remains non-terminal"
        )
    return _build_special(
        workstream_id="T02",
        recommendation=assessment.recommendation,
        source_kind="T02_TERMINAL_DISPOSITION_ASSESSMENT",
        source_object=assessment,
        phase22_manifest_sha256=phase22_manifest_sha256,
        binding=binding,
    )


def adapt_t11_terminal_assessment(
    *,
    assessment: T11TerminalDispositionAssessment,
    phase22_manifest_sha256: str,
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    if not isinstance(assessment, T11TerminalDispositionAssessment):
        raise CiboCapitalManagementError(
            "Closure 41 T11 adapter requires canonical assessment"
        )
    if assessment.recommendation is (
        T11TerminalRecommendation.WAITING_ON_GROSS_EDGE_FRESH_OOS
    ):
        raise CiboCapitalManagementError(
            "Closure 41 T11 assessment remains non-terminal"
        )
    recommendation = assessment.recommendation.value
    if recommendation not in {COMPLETED, FALSIFIED}:
        raise CiboCapitalManagementError(
            "Closure 41 T11 terminal recommendation invalid"
        )
    return _build_special(
        workstream_id="T11",
        recommendation=recommendation,
        source_kind="T11_TERMINAL_DISPOSITION_ASSESSMENT",
        source_object=assessment,
        phase22_manifest_sha256=phase22_manifest_sha256,
        binding=binding,
        source_digests=(PROVIDER_ARTIFACT_DIGEST,),
    )


def adapt_t11_terminal_receipts(
    *,
    market_impact: T11MarketImpactTerminalReceipt,
    gross_edge: T11GrossEdgeFreshOOSResult | None,
    phase22_manifest_sha256: str,
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    """Consume sealed T11 receipts without executing a new provider experiment."""

    if not isinstance(market_impact, T11MarketImpactTerminalReceipt):
        raise CiboCapitalManagementError(
            "Closure 41 T11 receipt adapter requires market-impact receipt"
        )
    if gross_edge is not None and not isinstance(
        gross_edge,
        T11GrossEdgeFreshOOSResult,
    ):
        raise CiboCapitalManagementError(
            "Closure 41 T11 gross-edge receipt invalid"
        )

    if market_impact.terminal_recommendation == FALSIFIED:
        recommendation = FALSIFIED
    elif market_impact.terminal_recommendation == COMPLETED:
        if gross_edge is None:
            raise CiboCapitalManagementError(
                "Closure 41 T11 market impact passed; fresh gross edge required"
            )
        recommendation = (
            COMPLETED if gross_edge.fresh_oos_validated else FALSIFIED
        )
    else:
        raise CiboCapitalManagementError(
            "Closure 41 T11 market-impact receipt disposition invalid"
        )

    source_digests: tuple[str, ...] = (
        PROVIDER_ARTIFACT_DIGEST,
        market_impact.report_sha256,
        market_impact.protocol_sha256,
        market_impact.experiment_plan_sha256,
    )
    if gross_edge is not None:
        source_digests = (*source_digests, gross_edge.fingerprint())

    return _build_special(
        workstream_id="T11",
        recommendation=recommendation,
        source_kind="T11_TERMINAL_RECEIPT_CHAIN",
        source_object={
            "market_impact": market_impact,
            "gross_edge": gross_edge,
        },
        phase22_manifest_sha256=phase22_manifest_sha256,
        binding=binding,
        source_digests=source_digests,
    )


def adapt_t20_terminal_receipt(
    *,
    receipt: T20TerminalReceipt,
    phase22_manifest_sha256: str,
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    if not isinstance(receipt, T20TerminalReceipt):
        raise CiboCapitalManagementError(
            "Closure 41 T20 adapter requires canonical terminal receipt"
        )
    if not receipt.terminal_ready or receipt.recommendation != COMPLETED:
        raise CiboCapitalManagementError(
            "Closure 41 T20 receipt remains non-terminal"
        )
    return _build_special(
        workstream_id="T20",
        recommendation=COMPLETED,
        source_kind="T20_TERMINAL_RELEASE_RECEIPT",
        source_object=receipt,
        phase22_manifest_sha256=phase22_manifest_sha256,
        binding=binding,
    )


def adapt_fresh_oos_terminal_intake(
    *,
    intake: Architect2FreshOOSTerminalIntake,
    phase22_manifest_sha256: str,
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    if not isinstance(intake, Architect2FreshOOSTerminalIntake):
        raise CiboCapitalManagementError(
            "Closure 41 fresh-OOS adapter requires canonical intake"
        )
    if (
        not intake.fresh_oos_terminal_ready
        or intake.terminal_recommendation not in {COMPLETED, FALSIFIED}
    ):
        raise CiboCapitalManagementError(
            "Closure 41 fresh-OOS intake remains non-terminal"
        )
    return _build_special(
        workstream_id="FRESH_OOS",
        recommendation=intake.terminal_recommendation,
        source_kind="PHASE22_FRESH_OOS_TERMINAL_INTAKE",
        source_object=intake,
        phase22_manifest_sha256=phase22_manifest_sha256,
        binding=binding,
        source_digests=(
            intake.execution_manifest_sha256,
            intake.outcome_bundle_sha256,
            intake.qualification_plan_sha256,
        ),
    )


def adapt_usd60_capability_classification(
    *,
    gates: CiboMaximumCapabilityGateSet,
    hard_integrity_breach: bool,
    architecture_or_calibration_intervention_possible: bool,
    phase22_manifest_sha256: str,
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    if not isinstance(gates, CiboMaximumCapabilityGateSet):
        raise CiboCapitalManagementError(
            "Closure 41 USD60 adapter requires canonical gate set"
        )
    classification = classify_cibo_maximum_capability(
        gates,
        hard_integrity_breach=hard_integrity_breach,
        architecture_or_calibration_intervention_possible=(
            architecture_or_calibration_intervention_possible
        ),
    )
    if classification is (
        CiboMaximumCapabilityClassification.INTERVENTION_CONTINUE_ENGINEERING
    ):
        raise CiboCapitalManagementError(
            "Closure 41 USD60 capability remains non-terminal"
        )

    protocol = FROZEN_CIBO_USD60_SIX_MONTH_PROTOCOL
    if (
        protocol.initial_capital_usd != Decimal("60")
        or protocol.duration_months != 6
        or protocol.trader_lineage_count != 7
        or protocol.economic_target_usd is not None
    ):
        raise CiboCapitalManagementError(
            "Closure 41 USD60 frozen protocol identity drift"
        )
    if hard_integrity_breach and binding.integrity_result != "FAIL":
        raise CiboCapitalManagementError(
            "Closure 41 USD60 hard integrity failure must remain explicit"
        )
    recommendation = (
        COMPLETED
        if classification is CiboMaximumCapabilityClassification.CERTIFIED
        else FALSIFIED
    )
    return _build_special(
        workstream_id="USD60_CAPABILITY_PROGRAM",
        recommendation=recommendation,
        source_kind="USD60_MAXIMUM_CAPABILITY_GATE_SET",
        source_object={
            "gates": gates,
            "classification": classification,
            "hard_integrity_breach": hard_integrity_breach,
            "architecture_or_calibration_intervention_possible": (
                architecture_or_calibration_intervention_possible
            ),
            "protocol_id": protocol.protocol_id,
        },
        phase22_manifest_sha256=phase22_manifest_sha256,
        binding=binding,
    )


def adapt_integrated_capital_truth(
    *,
    truth: IntegratedCapitalTruth,
    phase22_manifest_sha256: str,
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    if not isinstance(truth, IntegratedCapitalTruth):
        raise CiboCapitalManagementError(
            "Closure 41 integrated-capital adapter requires canonical truth"
        )
    if (
        truth.equivalence_residual_usd != 0
        or truth.nonconsumed_residual_usd != 0
        or not truth.settlement_provenance_pass
        or not truth.admission_coverage_pass
        or not truth.no_double_counting_pass
        or truth.fungible_cross_dimension_total_computed
    ):
        raise CiboCapitalManagementError(
            "Closure 41 integrated-capital truth is not reconciled"
        )
    return _build_special(
        workstream_id="INTEGRATED_CAPITAL_TRUTH",
        recommendation=COMPLETED,
        source_kind="INTEGRATED_CAPITAL_TRUTH",
        source_object=truth,
        phase22_manifest_sha256=phase22_manifest_sha256,
        binding=binding,
        source_digests=(
            truth.source_ledger_sha256,
            truth.compound_cycle_state_sha256,
        ),
    )


def _build_special(
    *,
    workstream_id: str,
    recommendation: str,
    source_kind: str,
    source_object: object,
    phase22_manifest_sha256: str,
    binding: CanonicalScientificBinding,
    source_digests: tuple[str, ...] = (),
) -> ScientificClosure41Evidence:
    source_status = "PASS" if recommendation == COMPLETED else "FAIL"
    return _build_evidence(
        workstream_id=workstream_id,
        phase22_manifest_sha256=phase22_manifest_sha256,
        source_gate_status=source_status,
        recommendation=recommendation,
        terminal_reason=f"Canonical {source_kind} terminal disposition.",
        failed_dimensions=(),
        source_kind=source_kind,
        source_object=source_object,
        source_refs=(f"source://{source_kind}",),
        source_digests=source_digests,
        binding=binding,
    )


def _build_evidence(
    *,
    workstream_id: str,
    phase22_manifest_sha256: str,
    source_gate_status: str,
    recommendation: str,
    terminal_reason: str,
    failed_dimensions: tuple[str, ...],
    source_kind: str,
    source_object: object,
    source_refs: tuple[str, ...],
    source_digests: tuple[str, ...],
    binding: CanonicalScientificBinding,
) -> ScientificClosure41Evidence:
    if not isinstance(binding, CanonicalScientificBinding):
        raise CiboCapitalManagementError(
            "Closure 41 adapter requires canonical binding"
        )
    expected = COMPLETED if source_gate_status == "PASS" else FALSIFIED
    if recommendation != expected:
        raise CiboCapitalManagementError(
            "Closure 41 source result/disposition drift"
        )
    source_sha = _source_sha256(source_object)
    refs = tuple(dict.fromkeys((*binding.evidence_refs, *source_refs)))
    digests = tuple(
        dict.fromkeys(
            (
                *binding.evidence_sha256s,
                *source_digests,
                source_sha,
            )
        )
    )
    return ScientificClosure41Evidence(
        workstream_id=workstream_id,
        previous_disposition=(
            OPEN_PREIMAGE
            if workstream_id == FRESH_OOS_ID
            else "EXTERNAL_DEPENDENCY_BLOCKED"
        ),
        scientific_hypothesis=binding.scientific_hypothesis,
        evidence_refs=refs,
        evidence_sha256s=digests,
        population_identity=binding.population_identity,
        policy_identity=CANONICAL_POLICY_IDENTITY,
        provider_identity=CANONICAL_PROVIDER_IDENTITY,
        causal_lineage=binding.causal_lineage,
        economic_result=binding.economic_result,
        stress_result=binding.stress_result,
        temporal_replication_result=binding.temporal_replication_result,
        integrity_result=binding.integrity_result,
        source_gate_status=source_gate_status,
        terminal_reason=terminal_reason,
        evaluated_at=binding.evaluated_at,
        phase22_manifest_sha256=phase22_manifest_sha256,
        evidence_origin=binding.evidence_origin,
        failed_dimensions=failed_dimensions,
        synthetic_evidence_used=False,
        future_leakage_detected=False,
        outcome_aware_evidence=False,
        post_outcome_retuning_detected=False,
        productive_authority=False,
        live_authorized=False,
        real_capital_authorized=False,
        certification_authorized=False,
    )


def _source_sha256(value: object) -> str:
    raw = json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _jsonable(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return _jsonable(value.value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    raise CiboCapitalManagementError(
        "Closure 41 canonical source contains unsupported value"
    )
