"""Architect A internal-readiness contract for CIBO.

This module proves only that Architect A has exhausted the engineering,
preregistration and test surface that A itself owns. It is not scientific
closure, integration, certification or production authority.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_ce2i_phase20_policy_candidate import (
    FROZEN_PHASE20_POLICY_CANDIDATE,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
    phase20d_qualification_plan_sha256,
)

LEDGER_PATH = Path("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
SCHEMA = "QORE_CIBO_ARCH_A_INTERNAL_READINESS_V1"
SCIENTIFIC_INTAKE_SCHEMA = "QORE_CIBO_ARCH_A_SCIENTIFIC_INTAKE_V1"
SCIENTIFIC_BATCH_SCHEMA = "QORE_CIBO_ARCH_A_SCIENTIFIC_BATCH_PLAN_V1"
MECHANISM_EVIDENCE_SCHEMA = "QORE_CIBO_ARCH_A_MECHANISM_EVIDENCE_RECEIPT_V1"
ARCH_B_FORWARD_MANIFEST_ID = (
    "CIBO_ARCH_B_FORWARD_ECONOMIC_EVIDENCE_MANIFEST_V1"
)

A_WORKSTREAM_IDS = (
    "T04", "T05", "T06", "T07", "T08", "T09", "T10", "T12", "T13",
    "T14", "T15", "T18", "T19", "GEN-C1", "GEN-C2", "GEN-C3", "GEN-C4",
    "GEN-C5", "GEN-C6", "GEN-C7", "GEN-C8", "GEN-C9", "GEN-C10",
    "GEN-C11", "GEN-C12", "GEN-C13", "GEN-C14", "COMPOUND_ENGINE",
    "COMPOUND_PORTFOLIO", "INTERNAL_CAPITAL_MARKET", "CAPITAL_GENERATIONS",
    "PROTECTED_BASE_CAPITAL", "PROFIT_PROTECTION", "PATH_DEPENDENT_MONTE_CARLO",
    "ADVERSARIAL_STRESS", "TEMPORAL_REPLICATION", "CAPITAL_AMPLIFICATION",
    "AS_IS_ECONOMIC_BASELINE",
)



_SCIENTIFIC_WAVE_1 = (
    "T04", "T06", "T07", "T08", "T09", "T10", "T12", "T13", "T14",
    "T15", "T18", "GEN-C4", "GEN-C7", "GEN-C9", "GEN-C10", "GEN-C12",
    "AS_IS_ECONOMIC_BASELINE",
)
_SCIENTIFIC_WAVE_2 = (
    "GEN-C2", "GEN-C5", "GEN-C6", "GEN-C8", "GEN-C11", "GEN-C13",
    "COMPOUND_ENGINE", "COMPOUND_PORTFOLIO", "INTERNAL_CAPITAL_MARKET",
    "CAPITAL_GENERATIONS", "PROTECTED_BASE_CAPITAL", "PROFIT_PROTECTION",
    "PATH_DEPENDENT_MONTE_CARLO",
)
_SCIENTIFIC_WAVE_3 = (
    "GEN-C3", "GEN-C14", "ADVERSARIAL_STRESS", "TEMPORAL_REPLICATION",
)
_SCIENTIFIC_WAVE_4 = ("CAPITAL_AMPLIFICATION",)
_SCIENTIFIC_WAVES = (
    _SCIENTIFIC_WAVE_1,
    _SCIENTIFIC_WAVE_2,
    _SCIENTIFIC_WAVE_3,
    _SCIENTIFIC_WAVE_4,
)

_REQUIRED_MECHANISM_EVIDENCE_KINDS = (
    "FORWARD_CAPITAL_TRUTH_CHRONOLOGY",
    "T08_FACTOR_CORRELATION_LINEAGE",
    "T09_T18_TRUE_SCARCITY_LINEAGE",
    "T15_RESERVATION_COUNTERFACTUAL_LINEAGE",
    "GENC10_TWIN_TRANSITION_LINEAGE",
    "GENC11_TRANSITION_CALIBRATION",
    "GENC12_CRISIS_FACTOR_SET",
    "GENC13_MEMORY_HYPOTHESIS",
    "PROTECTED_BASE_POLICY_IDENTITY",
    "COMPOUND_STRESS_LINEAGE",
    "STRICT_TEMPORAL_POPULATION_LINEAGE",
)

_INTERNAL_DEBT_MARKERS = (
    "REGISTRY_RECONCILIATION_REQUIRED", "CI_PENDING", "NOT_IMPLEMENTED",
    "ARCHITECTURE_ONLY", "PREREGISTRATION_REQUIRED", "PROTOCOL_REQUIRED",
    "TEST_REQUIRED", "ENGINE_REQUIRED", "CHILD_CI_REQUIRED",
    "REVALIDATION_REQUIRED", "MISSING_IMPLEMENTATION",
)


class ArchitectAReadinessError(RuntimeError):
    """Raised when the canonical ledger cannot be audited safely."""


@dataclass(frozen=True, slots=True)
class ArchitectAInternalReadinessReport:
    schema: str
    passed: bool
    workstream_count: int
    terminal_count: int
    empirical_open_count: int
    terminal_ids: tuple[str, ...]
    empirical_open_ids: tuple[str, ...]
    internal_debt_ids: tuple[str, ...]
    missing_workstream_ids: tuple[str, ...]
    evidence_missing_ids: tuple[str, ...]
    scientific_closure_claimed: bool = False
    integration_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ArchitectAReadinessError(
                "Architect A internal-readiness schema drift"
            )
        for name in (
            "passed",
            "scientific_closure_claimed",
            "integration_authority",
            "production_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise ArchitectAReadinessError(
                    f"Architect A internal-readiness {name} must be bool"
                )
        for name in (
            "workstream_count",
            "terminal_count",
            "empirical_open_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ArchitectAReadinessError(
                    f"Architect A internal-readiness {name} must be non-negative int"
                )
        if self.workstream_count != len(A_WORKSTREAM_IDS):
            raise ArchitectAReadinessError(
                "Architect A internal-readiness workstream count drift"
            )
        for name in (
            "terminal_ids",
            "empirical_open_ids",
            "internal_debt_ids",
            "missing_workstream_ids",
            "evidence_missing_ids",
        ):
            values = getattr(self, name)
            if (
                not isinstance(values, tuple)
                or any(
                    not isinstance(item, str) or item not in A_WORKSTREAM_IDS
                    for item in values
                )
                or len(values) != len(set(values))
            ):
                raise ArchitectAReadinessError(
                    f"Architect A internal-readiness {name} are invalid"
                )
        if self.terminal_count != len(self.terminal_ids):
            raise ArchitectAReadinessError(
                "Architect A internal-readiness terminal count drift"
            )
        if self.empirical_open_count != len(self.empirical_open_ids):
            raise ArchitectAReadinessError(
                "Architect A internal-readiness empirical-open count drift"
            )
        terminal = set(self.terminal_ids)
        empirical = set(self.empirical_open_ids)
        missing = set(self.missing_workstream_ids)
        if terminal & empirical or terminal & missing or empirical & missing:
            raise ArchitectAReadinessError(
                "Architect A internal-readiness disposition overlap"
            )
        if terminal | empirical | missing != set(A_WORKSTREAM_IDS):
            raise ArchitectAReadinessError(
                "Architect A internal-readiness workstream coverage drift"
            )
        expected_pass = not (
            self.internal_debt_ids
            or self.missing_workstream_ids
            or self.evidence_missing_ids
        )
        if self.passed != expected_pass:
            raise ArchitectAReadinessError(
                "Architect A internal-readiness pass/evidence drift"
            )
        if (
            self.scientific_closure_claimed
            or self.integration_authority
            or self.production_authority
        ):
            raise ArchitectAReadinessError(
                "Architect A internal-readiness cannot claim closure/authority"
            )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_architect_a_internal_readiness(
    ledger_path: Path = LEDGER_PATH,
) -> ArchitectAInternalReadinessReport:
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    rows = payload.get("workstreams")
    if not isinstance(rows, list):
        raise ArchitectAReadinessError("canonical workstreams array is required")

    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise ArchitectAReadinessError("canonical workstream row is invalid")
        row_id = str(row["id"])
        if row_id in by_id:
            raise ArchitectAReadinessError(f"duplicate workstream id: {row_id}")
        by_id[row_id] = row

    missing = tuple(item for item in A_WORKSTREAM_IDS if item not in by_id)
    internal_debt: list[str] = []
    evidence_missing: list[str] = []
    terminal: list[str] = []
    empirical_open: list[str] = []

    for row_id in A_WORKSTREAM_IDS:
        row = by_id.get(row_id)
        if row is None:
            continue
        if row.get("mandatory") is not True:
            raise ArchitectAReadinessError(
                f"Architect A workstream must remain mandatory: {row_id}"
            )

        blockers_raw = row.get("blockers", [])
        blockers = (
            tuple(str(item) for item in blockers_raw)
            if isinstance(blockers_raw, list)
            else ()
        )
        searchable = " ".join(
            (
                str(row.get("current_maturity", "")),
                *blockers,
                str(row.get("next_gate", "")),
            )
        ).upper()
        if any(marker in searchable for marker in _INTERNAL_DEBT_MARKERS):
            internal_debt.append(row_id)

        evidence = row.get("evidence_refs")
        if not isinstance(evidence, list) or not evidence:
            evidence_missing.append(row_id)

        if row.get("terminal_disposition") is None:
            empirical_open.append(row_id)
            if not blockers:
                internal_debt.append(row_id)
        else:
            terminal.append(row_id)
            if blockers:
                internal_debt.append(row_id)

    internal_debt = list(dict.fromkeys(internal_debt))
    passed = not missing and not internal_debt and not evidence_missing
    return ArchitectAInternalReadinessReport(
        schema=SCHEMA,
        passed=passed,
        workstream_count=len(A_WORKSTREAM_IDS),
        terminal_count=len(terminal),
        empirical_open_count=len(empirical_open),
        terminal_ids=tuple(terminal),
        empirical_open_ids=tuple(empirical_open),
        internal_debt_ids=tuple(internal_debt),
        missing_workstream_ids=missing,
        evidence_missing_ids=tuple(evidence_missing),
    )

@dataclass(frozen=True, slots=True)
class ArchitectAScientificIntakeReport:
    schema: str
    manifest_sha256: str
    qualification_status: str
    decision_epochs: int
    candidate_rows: int
    complete_lineage_rows: int
    complete_lineage_coverage: str
    fold_ids: tuple[str, ...]
    trader_lineage_count: int
    selected_rows: int
    blocking_gap_count: int
    ready_for_batch_science: bool
    blockers: tuple[str, ...]
    scientific_closure_claimed: bool = False
    integration_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != SCIENTIFIC_INTAKE_SCHEMA:
            raise ArchitectAReadinessError(
                "Architect A scientific intake schema drift"
            )
        _require_sha(self.manifest_sha256, "manifest_sha256")
        for name in (
            "decision_epochs",
            "candidate_rows",
            "complete_lineage_rows",
            "trader_lineage_count",
            "selected_rows",
            "blocking_gap_count",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ArchitectAReadinessError(
                    f"Architect A scientific intake {name} must be non-negative int"
                )
        if type(self.ready_for_batch_science) is not bool:
            raise ArchitectAReadinessError(
                "Architect A scientific intake readiness must be bool"
            )
        if (
            not isinstance(self.blockers, tuple)
            or any(not isinstance(item, str) or not item for item in self.blockers)
            or len(self.blockers) != len(set(self.blockers))
        ):
            raise ArchitectAReadinessError(
                "Architect A scientific intake blockers are invalid"
            )
        if self.ready_for_batch_science != (not self.blockers):
            raise ArchitectAReadinessError(
                "Architect A scientific intake readiness/blocker drift"
            )
        if (
            self.scientific_closure_claimed
            or self.integration_authority
            or self.production_authority
        ):
            raise ArchitectAReadinessError(
                "Architect A scientific intake cannot claim closure/authority"
            )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_architect_a_scientific_intake(
    payload: dict[str, Any],
) -> ArchitectAScientificIntakeReport:
    """Validate Architect-B forward manifest before launching A science.

    This is an intake gate only. It never interprets the population as proof,
    never changes the frozen policy and never grants certification or runtime
    authority.
    """

    if not isinstance(payload, dict):
        raise ArchitectAReadinessError(
            "Architect B forward manifest payload must be object"
        )

    manifest_sha256 = _require_sha(
        payload.get("manifest_sha256"),
        "manifest_sha256",
    )
    unsigned = dict(payload)
    unsigned.pop("manifest_sha256", None)
    if manifest_sha256 != forward_manifest_payload_sha256(unsigned):
        raise ArchitectAReadinessError(
            "Architect B forward manifest digest drift"
        )

    if payload.get("manifest_id") != ARCH_B_FORWARD_MANIFEST_ID:
        raise ArchitectAReadinessError(
            "Architect B forward manifest identity drift"
        )

    frozen = FROZEN_PHASE20_POLICY_CANDIDATE
    plan = FROZEN_PHASE20D_QUALIFICATION_PLAN
    if (
        payload.get("frozen_candidate_id") != frozen.candidate_id
        or payload.get("frozen_code_sha") != frozen.code_sha
        or payload.get("frozen_parameter_sha256") != frozen.parameter_sha256()
    ):
        raise ArchitectAReadinessError(
            "Architect B frozen Phase20 lineage drift"
        )
    if (
        payload.get("qualification_plan_id") != plan.plan_id
        or payload.get("qualification_plan_sha256")
        != phase20d_qualification_plan_sha256()
        or payload.get("baseline_policy_id") != plan.baseline_policy_id
    ):
        raise ArchitectAReadinessError(
            "Architect B qualification-plan lineage drift"
        )

    decision_epochs = _require_nonnegative_int(
        payload.get("decision_epochs"),
        "decision_epochs",
    )
    candidate_rows = _require_nonnegative_int(
        payload.get("candidate_rows"),
        "candidate_rows",
    )
    complete_lineage_rows = _require_nonnegative_int(
        payload.get("complete_lineage_rows"),
        "complete_lineage_rows",
    )
    rows = _require_list(payload.get("rows"), "rows")
    gaps = _require_list(payload.get("gaps"), "gaps")
    if complete_lineage_rows != len(rows):
        raise ArchitectAReadinessError(
            "Architect B complete-lineage count drift"
        )
    if complete_lineage_rows + len(gaps) != candidate_rows:
        raise ArchitectAReadinessError(
            "Architect B complete/gap coverage drift"
        )

    fold_ids: set[str] = set()
    lineage_counts: dict[str, int] = {}
    selected_rows = 0
    row_keys: set[tuple[str, str]] = set()
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            raise ArchitectAReadinessError(
                "Architect B forward manifest row must be object"
            )
        decision_sha = _require_sha(
            raw_row.get("decision_evidence_sha256"),
            "decision_evidence_sha256",
        )
        signal = _require_nonempty_str(
            raw_row.get("signal_fingerprint"),
            "signal_fingerprint",
        )
        key = (decision_sha, signal)
        if key in row_keys:
            raise ArchitectAReadinessError(
                "Architect B forward manifest duplicate row identity"
            )
        row_keys.add(key)

        fold_id = _require_nonempty_str(raw_row.get("fold_id"), "fold_id")
        if fold_id not in {"WF1", "WF2", "WF3", "WF4"}:
            raise ArchitectAReadinessError(
                "Architect B forward manifest fold identity is invalid"
            )
        fold_ids.add(fold_id)

        trader_id = _require_nonempty_str(
            raw_row.get("trader_id"),
            "trader_id",
        )
        lineage_counts[trader_id] = lineage_counts.get(trader_id, 0) + 1

        if raw_row.get("candidate_id") != frozen.candidate_id:
            raise ArchitectAReadinessError(
                "Architect B row candidate identity drift"
            )
        if raw_row.get("code_sha") != frozen.code_sha:
            raise ArchitectAReadinessError(
                "Architect B row code lineage drift"
            )
        if raw_row.get("parameter_sha256") != frozen.parameter_sha256():
            raise ArchitectAReadinessError(
                "Architect B row parameter lineage drift"
            )
        if raw_row.get("baseline_policy_id") != plan.baseline_policy_id:
            raise ArchitectAReadinessError(
                "Architect B row baseline lineage drift"
            )
        for name in (
            "provider_economics_sha256",
            "executed_risk_sha256",
            "settlement_sha256",
            "release_evidence_sha256",
        ):
            _require_sha(raw_row.get(name), name)
        policy_selected = raw_row.get("policy_selected")
        if type(policy_selected) is not bool:
            raise ArchitectAReadinessError(
                "Architect B row policy_selected must be bool"
            )
        selected_rows += int(policy_selected)

    gap_keys: set[tuple[str, str]] = set()
    blocking_gap_count = 0
    for raw_gap in gaps:
        if not isinstance(raw_gap, dict):
            raise ArchitectAReadinessError(
                "Architect B forward manifest gap must be object"
            )
        decision_sha = _require_sha(
            raw_gap.get("decision_evidence_sha256"),
            "gap decision_evidence_sha256",
        )
        signal = _require_nonempty_str(
            raw_gap.get("signal_fingerprint"),
            "gap signal_fingerprint",
        )
        key = (decision_sha, signal)
        if key in gap_keys:
            raise ArchitectAReadinessError(
                "Architect B forward manifest duplicate gap identity"
            )
        gap_keys.add(key)
        blocking = raw_gap.get("blocking")
        if type(blocking) is not bool:
            raise ArchitectAReadinessError(
                "Architect B forward manifest gap blocking must be bool"
            )
        reasons = raw_gap.get("reasons")
        if (
            not isinstance(reasons, list)
            or not reasons
            or any(not isinstance(item, str) or not item for item in reasons)
        ):
            raise ArchitectAReadinessError(
                "Architect B forward manifest gap reasons are invalid"
            )
        blocking_gap_count += int(blocking)

    qualification_status = _require_nonempty_str(
        payload.get("qualification_status"),
        "qualification_status",
    )
    ready_from_b = payload.get("ready_for_scientific_consumption")
    if type(ready_from_b) is not bool:
        raise ArchitectAReadinessError(
            "Architect B scientific-consumption flag must be bool"
        )
    if payload.get("certification_ready") is not False:
        raise ArchitectAReadinessError(
            "Architect B manifest cannot claim certification"
        )
    if payload.get("productive_authority") is not False:
        raise ArchitectAReadinessError(
            "Architect B manifest cannot grant productive authority"
        )

    coverage = (
        Decimal(complete_lineage_rows) / Decimal(candidate_rows)
        if candidate_rows
        else Decimal(0)
    )
    blockers: list[str] = []
    if qualification_status not in {"PASS", "FAIL"}:
        blockers.append("PHASE20D_EMPIRICAL_DISPOSITION_REQUIRED")
    if decision_epochs < plan.minimum_decision_epochs:
        blockers.append("DECISION_EPOCH_MINIMUM_NOT_MET")
    if candidate_rows < plan.minimum_candidate_outcomes:
        blockers.append("CANDIDATE_OUTCOME_MINIMUM_NOT_MET")
    if complete_lineage_rows <= 0:
        blockers.append("COMPLETE_LINEAGE_REQUIRED")
    if blocking_gap_count:
        blockers.append("BLOCKING_LINEAGE_GAPS_PRESENT")
    if coverage < plan.minimum_candidate_outcome_coverage:
        blockers.append("CANDIDATE_COVERAGE_MINIMUM_NOT_MET")
    if fold_ids != {"WF1", "WF2", "WF3", "WF4"}:
        blockers.append("WF1_WF4_COVERAGE_REQUIRED")
    if len(lineage_counts) < plan.minimum_global_lineages:
        blockers.append("GLOBAL_LINEAGE_MINIMUM_NOT_MET")
    if any(
        count < plan.minimum_outcomes_per_lineage
        for count in lineage_counts.values()
    ):
        blockers.append("OUTCOMES_PER_LINEAGE_MINIMUM_NOT_MET")
    if selected_rows < plan.minimum_selected_outcomes:
        blockers.append("SELECTED_OUTCOME_MINIMUM_NOT_MET")
    if not ready_from_b:
        blockers.append("ARCH_B_NOT_READY_FOR_SCIENTIFIC_CONSUMPTION")

    blockers = list(dict.fromkeys(blockers))
    if ready_from_b and blockers:
        raise ArchitectAReadinessError(
            "Architect B scientific readiness contradicts manifest evidence"
        )

    return ArchitectAScientificIntakeReport(
        schema=SCIENTIFIC_INTAKE_SCHEMA,
        manifest_sha256=manifest_sha256,
        qualification_status=qualification_status,
        decision_epochs=decision_epochs,
        candidate_rows=candidate_rows,
        complete_lineage_rows=complete_lineage_rows,
        complete_lineage_coverage=format(coverage, "f"),
        fold_ids=tuple(sorted(fold_ids)),
        trader_lineage_count=len(lineage_counts),
        selected_rows=selected_rows,
        blocking_gap_count=blocking_gap_count,
        ready_for_batch_science=not blockers,
        blockers=tuple(blockers),
    )


def forward_manifest_payload_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return "sha256:" + sha256(raw).hexdigest()


def _require_sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise ArchitectAReadinessError(
            f"Architect A scientific intake {name} must be canonical SHA-256"
        )
    return value


def _require_nonempty_str(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ArchitectAReadinessError(
            f"Architect A scientific intake {name} is required"
        )
    return value


def _require_nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ArchitectAReadinessError(
            f"Architect A scientific intake {name} must be non-negative int"
        )
    return value


def _require_list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ArchitectAReadinessError(
            f"Architect A scientific intake {name} must be list"
        )
    return value

@dataclass(frozen=True, slots=True)
class ArchitectAScientificBatchPlan:
    schema: str
    remaining_workstream_count: int
    remaining_workstream_ids: tuple[str, ...]
    wave_1_ids: tuple[str, ...]
    wave_2_ids: tuple[str, ...]
    wave_3_ids: tuple[str, ...]
    wave_4_ids: tuple[str, ...]
    population_batch_ready: bool
    complete_without_execution: bool
    blockers: tuple[str, ...]
    scientific_closure_claimed: bool = False
    integration_authority: bool = False
    production_authority: bool = False
    mechanism_specific_evidence_required: bool = True
    required_mechanism_evidence_kinds: tuple[str, ...] = (
        _REQUIRED_MECHANISM_EVIDENCE_KINDS
    )

    def __post_init__(self) -> None:
        if self.schema != SCIENTIFIC_BATCH_SCHEMA:
            raise ArchitectAReadinessError(
                "Architect A scientific batch schema drift"
            )
        waves = (
            self.wave_1_ids,
            self.wave_2_ids,
            self.wave_3_ids,
            self.wave_4_ids,
        )
        flattened = tuple(item for wave in waves for item in wave)
        if (
            self.remaining_workstream_count != len(self.remaining_workstream_ids)
            or flattened != self.remaining_workstream_ids
            or len(flattened) != len(set(flattened))
            or any(item not in A_WORKSTREAM_IDS for item in flattened)
        ):
            raise ArchitectAReadinessError(
                "Architect A scientific batch workstream drift"
            )
        for name in (
            "population_batch_ready",
            "complete_without_execution",
            "mechanism_specific_evidence_required",
        ):
            if type(getattr(self, name)) is not bool:
                raise ArchitectAReadinessError(
                    f"Architect A scientific batch {name} must be bool"
                )
        if not self.mechanism_specific_evidence_required:
            raise ArchitectAReadinessError(
                "Architect A scientific batch must retain mechanism-specific evidence gate"
            )
        if (
            self.required_mechanism_evidence_kinds
            != _REQUIRED_MECHANISM_EVIDENCE_KINDS
        ):
            raise ArchitectAReadinessError(
                "Architect A scientific batch mechanism-evidence contract drift"
            )
        if self.population_batch_ready and self.complete_without_execution:
            raise ArchitectAReadinessError(
                "Architect A scientific batch state is contradictory"
            )
        if (
            not isinstance(self.blockers, tuple)
            or any(not isinstance(item, str) or not item for item in self.blockers)
            or len(self.blockers) != len(set(self.blockers))
        ):
            raise ArchitectAReadinessError(
                "Architect A scientific batch blockers are invalid"
            )
        expected_ready = (
            self.remaining_workstream_count > 0
            and not self.blockers
            and not self.complete_without_execution
        )
        if self.population_batch_ready != expected_ready:
            raise ArchitectAReadinessError(
                "Architect A scientific batch readiness/blocker drift"
            )
        if (
            self.scientific_closure_claimed
            or self.integration_authority
            or self.production_authority
        ):
            raise ArchitectAReadinessError(
                "Architect A scientific batch cannot claim closure/authority"
            )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_architect_a_scientific_batch_plan(
    readiness: ArchitectAInternalReadinessReport,
    intake: ArchitectAScientificIntakeReport,
) -> ArchitectAScientificBatchPlan:
    if not isinstance(readiness, ArchitectAInternalReadinessReport):
        raise ArchitectAReadinessError(
            "Architect A scientific batch requires canonical readiness report"
        )
    if not isinstance(intake, ArchitectAScientificIntakeReport):
        raise ArchitectAReadinessError(
            "Architect A scientific batch requires canonical intake report"
        )

    blockers: list[str] = []
    if not readiness.passed:
        blockers.append("ARCH_A_INTERNAL_READINESS_REQUIRED")
    if not intake.ready_for_batch_science:
        blockers.append("ARCH_B_SCIENTIFIC_INTAKE_REQUIRED")

    remaining = set(readiness.empirical_open_ids)
    waves = tuple(
        tuple(item for item in wave if item in remaining)
        for wave in _SCIENTIFIC_WAVES
    )
    flattened = tuple(item for wave in waves for item in wave)
    if set(flattened) != remaining:
        missing = tuple(sorted(remaining - set(flattened)))
        raise ArchitectAReadinessError(
            "Architect A scientific batch missing dependency-wave mapping: "
            + ",".join(missing)
        )

    complete = not remaining
    return ArchitectAScientificBatchPlan(
        schema=SCIENTIFIC_BATCH_SCHEMA,
        remaining_workstream_count=len(flattened),
        remaining_workstream_ids=flattened,
        wave_1_ids=waves[0],
        wave_2_ids=waves[1],
        wave_3_ids=waves[2],
        wave_4_ids=waves[3],
        population_batch_ready=(
            bool(flattened) and not blockers
        ),
        complete_without_execution=complete,
        blockers=tuple(blockers),
    )

@dataclass(frozen=True, slots=True)
class ArchitectAMechanismEvidenceReceipt:
    schema: str
    forward_manifest_sha256: str
    evidence_refs: tuple[tuple[str, str], ...]
    present_kinds: tuple[str, ...]
    missing_kinds: tuple[str, ...]
    ready_for_full_mechanism_science: bool
    blockers: tuple[str, ...]
    scientific_closure_claimed: bool = False
    integration_authority: bool = False
    production_authority: bool = False

    def __post_init__(self) -> None:
        if self.schema != MECHANISM_EVIDENCE_SCHEMA:
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence schema drift"
            )
        _require_sha(self.forward_manifest_sha256, "forward_manifest_sha256")
        if (
            not isinstance(self.evidence_refs, tuple)
            or any(
                not isinstance(item, tuple)
                or len(item) != 2
                or item[0] not in _REQUIRED_MECHANISM_EVIDENCE_KINDS
                for item in self.evidence_refs
            )
        ):
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence refs are invalid"
            )
        kinds = tuple(item[0] for item in self.evidence_refs)
        if len(kinds) != len(set(kinds)):
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence kinds must be unique"
            )
        for _kind, digest in self.evidence_refs:
            _require_sha(digest, "mechanism evidence sha256")
        expected_present = tuple(
            item
            for item in _REQUIRED_MECHANISM_EVIDENCE_KINDS
            if item in set(kinds)
        )
        expected_missing = tuple(
            item
            for item in _REQUIRED_MECHANISM_EVIDENCE_KINDS
            if item not in set(kinds)
        )
        if self.present_kinds != expected_present:
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence present-kind drift"
            )
        if self.missing_kinds != expected_missing:
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence missing-kind drift"
            )
        if type(self.ready_for_full_mechanism_science) is not bool:
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence readiness must be bool"
            )
        if (
            not isinstance(self.blockers, tuple)
            or any(not isinstance(item, str) or not item for item in self.blockers)
            or len(self.blockers) != len(set(self.blockers))
        ):
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence blockers are invalid"
            )
        expected_ready = not self.missing_kinds and not self.blockers
        if self.ready_for_full_mechanism_science != expected_ready:
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence readiness/blocker drift"
            )
        if (
            self.scientific_closure_claimed
            or self.integration_authority
            or self.production_authority
        ):
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence cannot claim closure/authority"
            )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_architect_a_mechanism_evidence(
    payload: dict[str, Any],
    intake: ArchitectAScientificIntakeReport,
) -> ArchitectAMechanismEvidenceReceipt:
    if not isinstance(payload, dict):
        raise ArchitectAReadinessError(
            "Architect A mechanism-evidence payload must be object"
        )
    if not isinstance(intake, ArchitectAScientificIntakeReport):
        raise ArchitectAReadinessError(
            "Architect A mechanism-evidence requires canonical intake"
        )
    if payload.get("schema") != MECHANISM_EVIDENCE_SCHEMA:
        raise ArchitectAReadinessError(
            "Architect A mechanism-evidence payload schema drift"
        )
    manifest_sha = _require_sha(
        payload.get("forward_manifest_sha256"),
        "forward_manifest_sha256",
    )
    if manifest_sha != intake.manifest_sha256:
        raise ArchitectAReadinessError(
            "Architect A mechanism-evidence forward-manifest lineage drift"
        )
    if payload.get("scientific_closure_claimed") not in {None, False}:
        raise ArchitectAReadinessError(
            "Architect A mechanism-evidence cannot claim scientific closure"
        )
    if payload.get("integration_authority") not in {None, False}:
        raise ArchitectAReadinessError(
            "Architect A mechanism-evidence cannot grant integration authority"
        )
    if payload.get("production_authority") not in {None, False}:
        raise ArchitectAReadinessError(
            "Architect A mechanism-evidence cannot grant production authority"
        )

    raw_refs = payload.get("evidence_refs")
    if not isinstance(raw_refs, list):
        raise ArchitectAReadinessError(
            "Architect A mechanism-evidence refs must be list"
        )
    refs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in raw_refs:
        if not isinstance(raw, dict):
            raise ArchitectAReadinessError(
                "Architect A mechanism-evidence ref must be object"
            )
        kind = _require_nonempty_str(raw.get("kind"), "evidence kind")
        if kind not in _REQUIRED_MECHANISM_EVIDENCE_KINDS:
            raise ArchitectAReadinessError(
                f"Architect A mechanism-evidence unknown kind: {kind}"
            )
        if kind in seen:
            raise ArchitectAReadinessError(
                f"Architect A mechanism-evidence duplicate kind: {kind}"
            )
        seen.add(kind)
        digest = _require_sha(raw.get("sha256"), f"{kind} sha256")
        refs.append((kind, digest))

    ordered_refs = tuple(
        (kind, next(digest for ref_kind, digest in refs if ref_kind == kind))
        for kind in _REQUIRED_MECHANISM_EVIDENCE_KINDS
        if kind in seen
    )
    present = tuple(kind for kind, _digest in ordered_refs)
    missing = tuple(
        kind
        for kind in _REQUIRED_MECHANISM_EVIDENCE_KINDS
        if kind not in seen
    )
    blockers = tuple(
        ["ARCH_B_SCIENTIFIC_INTAKE_REQUIRED"]
        if not intake.ready_for_batch_science
        else []
    )
    return ArchitectAMechanismEvidenceReceipt(
        schema=MECHANISM_EVIDENCE_SCHEMA,
        forward_manifest_sha256=manifest_sha,
        evidence_refs=ordered_refs,
        present_kinds=present,
        missing_kinds=missing,
        ready_for_full_mechanism_science=(
            intake.ready_for_batch_science and not missing
        ),
        blockers=blockers,
    )

