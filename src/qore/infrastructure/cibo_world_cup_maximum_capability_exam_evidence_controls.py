"""Fail-closed evidence admission for World Cup controls WC03-WC10.

This module freezes what evidence is required. It does not create competition
evidence and cannot convert ordinary Phase22 evidence into World Cup evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_final_integrated_exam import (
    FinalIntegratedExamReport,
    FinalIntegratedExamStatus,
)
from qore.infrastructure.cibo_world_cup_maximum_capability_exam import (
    WorldCupControlReceipt,
    bind_world_cup_control_artifact,
    final_integrated_exam_report_sha256,
    world_cup_policy_identity_sha256,
)

_PROTECTED_PHASE22_POPULATION_PREFIX = "CIBO_USD60_6M_HOLDOUT_"
_EVIDENCE_KIND = "WORLD_CUP_MAXIMUM_CAPABILITY_CONTROL"
_SCHEMA = "qore.cibo.world-cup-evidence-control.v1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUIRED_STRESS_FAMILIES = (
    "LOSSES_FIRST",
    "WINNER_DROUGHT",
    "LOSS_CLUSTERING",
    "CORRELATION_CONVERGENCE",
    "LIQUIDITY_SHOCK",
    "VOLATILITY_SHOCK",
    "MARGIN_HIKE",
    "SLIPPAGE_SHOCK",
    "GAP_THROUGH_STOP",
    "MULTIPLE_TRADERS_LOSE_TOGETHER",
    "PROFIT_GIVEBACK",
    "FAKE_DIVERSIFICATION",
    "CONVEX_STRUCTURES_FAIL_REPEATEDLY",
    "PROVIDER_DEGRADATION",
    "CAPITAL_LOCKUP",
    "OPPORTUNITY_SCARCITY",
)
_REQUIRED_FOLDS = ("WF1", "WF2", "WF3", "WF4")


def _sha(value: str, name: str) -> str:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCapitalManagementError(
            f"World Cup evidence {name} must be canonical sha256"
        )
    return value


@dataclass(frozen=True, slots=True)
class WorldCupEvidenceBase:
    competition_population_id: str
    evidence_sha256: str
    observed_at: datetime
    protected_holdout_reused: bool = False
    synthetic_evidence_used: bool = False
    outcome_aware_refit: bool = False
    post_hoc_selection_used: bool = False
    hidden_leverage_used: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.competition_population_id, str)
            or not self.competition_population_id
        ):
            raise CiboCapitalManagementError(
                "World Cup competition population identity required"
            )
        if self.competition_population_id.startswith(
            _PROTECTED_PHASE22_POPULATION_PREFIX
        ):
            raise CiboCapitalManagementError(
                "World Cup cannot reuse a protected Phase22 holdout"
            )
        _sha(self.evidence_sha256, "evidence_sha256")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "World Cup evidence observed_at must be timezone-aware"
            )
        if any(
            (
                self.protected_holdout_reused,
                self.synthetic_evidence_used,
                self.outcome_aware_refit,
                self.post_hoc_selection_used,
                self.hidden_leverage_used,
            )
        ):
            raise CiboCapitalManagementError(
                "World Cup evidence governance contamination"
            )


@dataclass(frozen=True, slots=True)
class WorldCupProviderEvidence(WorldCupEvidenceBase):
    provider_adapter_sha256: str = ""
    provider_economics_sha256: str = ""
    competition_provider_bound: bool = False
    provider_economics_complete: bool = False

    def __post_init__(self) -> None:
        WorldCupEvidenceBase.__post_init__(self)
        _sha(self.provider_adapter_sha256, "provider_adapter_sha256")
        _sha(self.provider_economics_sha256, "provider_economics_sha256")
        if not self.competition_provider_bound or not self.provider_economics_complete:
            raise CiboCapitalManagementError(
                "World Cup provider evidence is incomplete"
            )


@dataclass(frozen=True, slots=True)
class WorldCupDigitalTwinEvidence(WorldCupEvidenceBase):
    digital_twin_sha256: str = ""
    capital_conservation_sha256: str = ""
    competition_digital_twin_bound: bool = False
    capital_conservation_proven: bool = False
    no_capital_creation: bool = False
    no_duplicated_profit: bool = False
    no_reused_released_capacity: bool = False
    no_double_counted_netting: bool = False
    margin_feasible: bool = False
    chronology_monotonic: bool = False
    future_information_used: bool = False

    def __post_init__(self) -> None:
        WorldCupEvidenceBase.__post_init__(self)
        _sha(self.digital_twin_sha256, "digital_twin_sha256")
        _sha(self.capital_conservation_sha256, "capital_conservation_sha256")
        if not all(
            (
                self.competition_digital_twin_bound,
                self.capital_conservation_proven,
                self.no_capital_creation,
                self.no_duplicated_profit,
                self.no_reused_released_capacity,
                self.no_double_counted_netting,
                self.margin_feasible,
                self.chronology_monotonic,
            )
        ) or self.future_information_used:
            raise CiboCapitalManagementError(
                "World Cup Digital Twin conservation contract failed"
            )


@dataclass(frozen=True, slots=True)
class WorldCupAsIsControlEvidence(WorldCupEvidenceBase):
    as_is_control_sha256: str = ""
    as_is_control_frozen: bool = False

    def __post_init__(self) -> None:
        WorldCupEvidenceBase.__post_init__(self)
        _sha(self.as_is_control_sha256, "as_is_control_sha256")
        if not self.as_is_control_frozen:
            raise CiboCapitalManagementError(
                "World Cup AS-IS control must be frozen"
            )


@dataclass(frozen=True, slots=True)
class WorldCupCausalAttributionEvidence(WorldCupEvidenceBase):
    attribution_sha256: str = ""
    causal_attribution_complete: bool = False

    def __post_init__(self) -> None:
        WorldCupEvidenceBase.__post_init__(self)
        _sha(self.attribution_sha256, "attribution_sha256")
        if not self.causal_attribution_complete:
            raise CiboCapitalManagementError(
                "World Cup causal attribution incomplete"
            )


@dataclass(frozen=True, slots=True)
class WorldCupPathMonteCarloEvidence(WorldCupEvidenceBase):
    path_monte_carlo_sha256: str = ""
    path_structure_preserved: bool = False

    def __post_init__(self) -> None:
        WorldCupEvidenceBase.__post_init__(self)
        _sha(self.path_monte_carlo_sha256, "path_monte_carlo_sha256")
        if not self.path_structure_preserved:
            raise CiboCapitalManagementError(
                "World Cup path Monte Carlo destroyed path structure"
            )


@dataclass(frozen=True, slots=True)
class WorldCupStressEvidence(WorldCupEvidenceBase):
    stress_report_sha256: str = ""
    executed_stress_families: tuple[str, ...] = ()
    stress_noncompensatory_pass: bool = False

    def __post_init__(self) -> None:
        WorldCupEvidenceBase.__post_init__(self)
        _sha(self.stress_report_sha256, "stress_report_sha256")
        if self.executed_stress_families != _REQUIRED_STRESS_FAMILIES:
            raise CiboCapitalManagementError(
                "World Cup stress family coverage drift"
            )
        if not self.stress_noncompensatory_pass:
            raise CiboCapitalManagementError(
                "World Cup stress non-compensatory gate failed"
            )


@dataclass(frozen=True, slots=True)
class WorldCupTemporalReplicationEvidence(WorldCupEvidenceBase):
    temporal_report_sha256: str = ""
    fold_ids: tuple[str, ...] = ()
    fold_passes: tuple[bool, ...] = ()
    four_fold_replication_pass: bool = False

    def __post_init__(self) -> None:
        WorldCupEvidenceBase.__post_init__(self)
        _sha(self.temporal_report_sha256, "temporal_report_sha256")
        if self.fold_ids != _REQUIRED_FOLDS:
            raise CiboCapitalManagementError(
                "World Cup temporal fold identity drift"
            )
        if self.fold_passes != (True, True, True, True):
            raise CiboCapitalManagementError(
                "World Cup temporal replication requires 4/4 PASS"
            )
        if not self.four_fold_replication_pass:
            raise CiboCapitalManagementError(
                "World Cup four-fold replication gate failed"
            )


@dataclass(frozen=True, slots=True)
class WorldCupSurvivalProductivityEvidence(WorldCupEvidenceBase):
    survival_productivity_sha256: str = ""
    survival_nonworse: bool = False
    tail_nonworse: bool = False
    plausible_loss_nonworse: bool = False
    capital_productivity_improved: bool = False

    def __post_init__(self) -> None:
        WorldCupEvidenceBase.__post_init__(self)
        _sha(
            self.survival_productivity_sha256,
            "survival_productivity_sha256",
        )
        if not all(
            (
                self.survival_nonworse,
                self.tail_nonworse,
                self.plausible_loss_nonworse,
                self.capital_productivity_improved,
            )
        ):
            raise CiboCapitalManagementError(
                "World Cup survival/productivity non-compensatory gate failed"
            )


def _artifact(
    *,
    receipt_id: str,
    integrated_git_sha: str,
    final_sha256: str,
    evidence: WorldCupEvidenceBase,
    fields: dict[str, bool],
    source_refs: dict[str, str],
) -> str:
    payload: dict[str, Any] = {
        "schema": _SCHEMA,
        "evidence_binding_id": receipt_id,
        "evidence_kind": _EVIDENCE_KIND,
        "producer_gate_id": f"CIBO_WORLD_CUP_{receipt_id}_V1",
        "integrated_git_sha": integrated_git_sha,
        "world_cup_policy_identity_sha256": world_cup_policy_identity_sha256(),
        "final_integrated_exam_report_sha256": final_sha256,
        "certification_stage": "POST_FINAL_INTEGRATED",
        "observed_at": evidence.observed_at.isoformat(),
        "status": "PASS",
        "failures": [],
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "outcome_aware_refit": False,
        "post_hoc_selection_used": False,
        "aspirational_return_target_used": False,
        "hidden_leverage_used": False,
        "protected_holdout_reused": False,
        "future_information_used": False,
        "operational_authority_claimed": False,
        "competition_population_id": evidence.competition_population_id,
        "evidence_sha256": evidence.evidence_sha256,
        "source_refs": source_refs,
        **fields,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def build_world_cup_evidence_controls(
    *,
    integrated_git_sha: str,
    final_integrated_exam: FinalIntegratedExamReport,
    provider: WorldCupProviderEvidence,
    digital_twin: WorldCupDigitalTwinEvidence,
    as_is: WorldCupAsIsControlEvidence,
    attribution: WorldCupCausalAttributionEvidence,
    monte_carlo: WorldCupPathMonteCarloEvidence,
    stress: WorldCupStressEvidence,
    temporal: WorldCupTemporalReplicationEvidence,
    survival_productivity: WorldCupSurvivalProductivityEvidence,
) -> tuple[WorldCupControlReceipt, ...]:
    if not isinstance(final_integrated_exam, FinalIntegratedExamReport):
        raise CiboCapitalManagementError(
            "World Cup controls require canonical Final Integrated report"
        )
    if (
        final_integrated_exam.status is not FinalIntegratedExamStatus.PASS
        or final_integrated_exam.blockers
    ):
        raise CiboCapitalManagementError(
            "World Cup controls require Final Integrated PASS"
        )
    if final_integrated_exam.integrated_head_sha != integrated_git_sha:
        raise CiboCapitalManagementError(
            "World Cup controls Final Integrated HEAD drift"
        )

    evidence_items: tuple[WorldCupEvidenceBase, ...] = (
        provider,
        digital_twin,
        as_is,
        attribution,
        monte_carlo,
        stress,
        temporal,
        survival_productivity,
    )
    population_ids = {
        item.competition_population_id for item in evidence_items
    }
    if len(population_ids) != 1:
        raise CiboCapitalManagementError(
            "World Cup controls require one competition population identity"
        )

    final_sha = final_integrated_exam_report_sha256(final_integrated_exam)
    specs = (
        (
            "WC03_COMPETITION_PROVIDER_ADAPTER",
            provider,
            {
                "competition_provider_bound": True,
                "provider_economics_complete": True,
            },
            {
                "provider_adapter_sha256": provider.provider_adapter_sha256,
                "provider_economics_sha256": provider.provider_economics_sha256,
            },
        ),
        (
            "WC04_WORLD_CUP_DIGITAL_TWIN",
            digital_twin,
            {
                "competition_digital_twin_bound": True,
                "capital_conservation_proven": True,
                "no_capital_creation": True,
                "no_duplicated_profit": True,
                "no_reused_released_capacity": True,
                "no_double_counted_netting": True,
                "margin_feasible": True,
                "chronology_monotonic": True,
            },
            {
                "digital_twin_sha256": digital_twin.digital_twin_sha256,
                "capital_conservation_sha256": (
                    digital_twin.capital_conservation_sha256
                ),
            },
        ),
        (
            "WC05_AS_IS_CONTROL",
            as_is,
            {"as_is_control_frozen": True},
            {"as_is_control_sha256": as_is.as_is_control_sha256},
        ),
        (
            "WC06_AMPLIFICATION_CAUSAL_ATTRIBUTION",
            attribution,
            {"causal_attribution_complete": True},
            {"attribution_sha256": attribution.attribution_sha256},
        ),
        (
            "WC07_PATH_DEPENDENT_MONTE_CARLO",
            monte_carlo,
            {"path_structure_preserved": True},
            {"path_monte_carlo_sha256": monte_carlo.path_monte_carlo_sha256},
        ),
        (
            "WC08_ADVERSARIAL_STRESS",
            stress,
            {"stress_noncompensatory_pass": True},
            {
                "stress_report_sha256": stress.stress_report_sha256,
                "stress_family_set_sha256": _sha_tuple(
                    stress.executed_stress_families
                ),
            },
        ),
        (
            "WC09_TEMPORAL_REPLICATION",
            temporal,
            {"four_fold_replication_pass": True},
            {
                "temporal_report_sha256": temporal.temporal_report_sha256,
                "fold_set_sha256": _sha_tuple(temporal.fold_ids),
            },
        ),
        (
            "WC10_SURVIVAL_CAPITAL_PRODUCTIVITY",
            survival_productivity,
            {
                "survival_nonworse": True,
                "tail_nonworse": True,
                "plausible_loss_nonworse": True,
                "capital_productivity_improved": True,
            },
            {
                "survival_productivity_sha256": (
                    survival_productivity.survival_productivity_sha256
                ),
            },
        ),
    )

    return tuple(
        bind_world_cup_control_artifact(
            receipt_id=receipt_id,
            source_artifact_json=_artifact(
                receipt_id=receipt_id,
                integrated_git_sha=integrated_git_sha,
                final_sha256=final_sha,
                evidence=evidence,
                fields=fields,
                source_refs=source_refs,
            ),
        )
        for receipt_id, evidence, fields, source_refs in specs
    )


def _sha_tuple(values: tuple[str, ...]) -> str:
    raw = json.dumps(
        list(values),
        sort_keys=False,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    import hashlib

    return "sha256:" + hashlib.sha256(raw).hexdigest()
