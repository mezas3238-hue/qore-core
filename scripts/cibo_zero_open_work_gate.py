"""Machine-readable absolute closure gate for CIBO certification.

Routine mode always writes the gate verdict and exits zero when the audit itself
is valid. Final certification mode (--enforce-certification) exits non-zero if
any mandatory CIBO work remains open.

The gate does not grant certification. It only prevents certification while
open work, missing artifacts, unresolved markers or certification-blocking
external dependencies remain.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import io
import json
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LEDGER_PATH = Path("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
OUTPUT_PATH = Path("artifacts/cibo_zero_open_work_gate_v1.json")
PRE_EXAM_OUTPUT_PATH = Path("artifacts/cibo_zero_open_work_gate_pre_exam_v1.json")

_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_GATE_SCHEMA = "QORE_CIBO_ZERO_OPEN_WORK_GATE_V1"

_TERMINAL = frozenset(
    {
        "COMPLETED_AND_PROVEN",
        "FALSIFIED_AND_CLOSED",
        "SUPERSEDED_WITH_PROVEN_LINEAGE",
        "EXTERNAL_DEPENDENCY_BLOCKED",
    }
)

_PRE_EXAM_EXCLUDED_WORKSTREAM_IDS = frozenset(
    {
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    }
)

_REQUIRED_CANONICAL_ARTIFACTS = (
    "docs/research/CIBO-ABSOLUTE-CLOSURE-AMENDMENT-V1.md",
    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json",
    "docs/research/CIBO-SOVEREIGN-CAPITAL-AMPLIFICATION-WORLD-CUP-MISSION-V1.md",
    "docs/research/CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md",
    "docs/research/CIBO-CE2I-ADR-002-CAPITAL-MANAGEMENT-AUTHORITY.md",
    "docs/research/CIBO-CE2I-ADR-003-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING.md",
    "docs/research/CIBO-CAPITAL-MANAGEMENT-AUTHORITY-CE2I-MASTER-ROADMAP-V2.md",
    "docs/research/CIBO-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING-MASTER-ROADMAP-V3.md",
    "docs/research/CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md",
    "docs/research/CIBO-WORLD-CUP-MAXIMUM-CAPABILITY-EXAM-PROTOCOL-V1.md",
    "docs/research/CIBO-GENERATION-CURRENT-CONTROL-CI-EVIDENCE-V1.json",
)

_INVENTORY_GLOBS = (
    "src/qore/infrastructure/cibo_*.py",
    "scripts/cibo_*.py",
    "tests/infrastructure/test_cibo*.py",
    ".github/workflows/*cibo*.yml",
    "docs/research/CIBO*.md",
    "docs/research/CIBO*.json",
)

_MARKER_SCAN_GLOBS = (
    "src/qore/infrastructure/cibo_*.py",
    "scripts/cibo_*.py",
    ".github/workflows/*cibo*.yml",
)

_COMMENT_MARKERS = (
    "TODO",
    "FIXME",
    "UNRESOLVED",
)

_WORKSTREAM_CLASSIFIERS = (
    (
        "*cibo_ce2i_qualification_evidence_protocol*",
        "SOURCE_OF_TRUTH_RECONCILIATION",
    ),
    ("*cibo_arch_b_forward_economic_manifest*", "FORWARD_QUALIFICATION"),
    ("*cibo_phase20_arch_b_forward_economic_manifest*", "FORWARD_QUALIFICATION"),
    ("*cibo_ce2i_phase20_t02_structural_oos*", "T02"),
    ("*cibo_ce2i_phase20_t03_margin_population*", "T03"),
    ("*cibo_t03_provider_equivalent_candidate_screen*", "T03"),
    ("*cibo_ce2i_phase20_t11_execution_population*", "T11"),
    ("*cibo_ce2i_phase20_t11_cost_binding*", "T11"),
    ("*cibo_ce2i_execution_efficiency*", "T11"),
    ("*cibo_ce2i_t11_execution_cost_calibration*", "T11"),
    ("*cibo_ctrader_demo_account_capability*", "PROVIDER_ECONOMICS"),
    ("*cibo_ctrader_demo_capability_registry*", "PROVIDER_ECONOMICS"),
    ("*cibo_ctrader_demo_instrument_taxonomy*", "PROVIDER_ECONOMICS"),
    ("*cibo_ce2i_provider_execution_calibration*", "PROVIDER_ECONOMICS"),
    ("*cibo_phase20_provider_execution_calibration*", "PROVIDER_ECONOMICS"),
    ("*cibo_usd60_exam_readiness*", "USD60_CAPABILITY_PROGRAM"),
    ("*cibo_integrated_capital_forward_binding*", "INTEGRATED_CAPITAL_TRUTH"),
    ("*cibo_ce2i_calibration_freeze_manifest*", "FRESH_OOS"),
    ("*cibo_calibration_freeze_manifest*", "FRESH_OOS"),
    ("*cibo_research_memory*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_risk_integration_closure*", "RISK_INTEGRATION"),
    ("*cibo_ce2i_t17_limited_risk_capability*", "T17"),
    ("*cibo_t17_limited_risk_capability_probe*", "T17"),
    ("*cibo_ce2i_t16_preregistered_hedge_universe*", "T16"),
    ("*cibo_cma_compound_authority_boundary*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cma-compound-boundary*", "CMA_FOUNDATION_INTEGRATION"),
    ("*CMA-COMPOUND-AUTHORITY-BOUNDARY*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_legacy_stack_quarantine*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*legacy-stack-quarantine*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_compound_causal_ablation*", "CAPITAL_AMPLIFICATION"),
    ("*compound-causal-ablation*", "CAPITAL_AMPLIFICATION"),
    ("*cibo_as_is_economic_baseline*", "AS_IS_ECONOMIC_BASELINE"),
    ("*cibo_expansion_utility_gate*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_t04_t10_economic_gate*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_temporal_utility_replication*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_a1_strict_temporal_population_lineage*", "TEMPORAL_REPLICATION"),
    ("*cibo_ce2i_oos_stress_admission*", "ADVERSARIAL_STRESS"),
    ("*cibo_t09_t18_scarcity_safety_gate*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_t14_t15_utility_gate*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_compound_temporal_replication*", "TEMPORAL_REPLICATION"),
    ("*COMPOUND-TEMPORAL-REPLICATION*", "TEMPORAL_REPLICATION"),
    ("*cibo_compound_adversarial_stress*", "ADVERSARIAL_STRESS"),
    ("*cibo_arch_a_mechanism_stress_gate*", "ADVERSARIAL_STRESS"),
    ("*COMPOUND-ADVERSARIAL-STRESS*", "ADVERSARIAL_STRESS"),
    ("*cibo_genc3_genc6_economic_gate*", "CAPITAL_AMPLIFICATION"),
    ("*cibo_genc_strict_temporal_replication*", "TEMPORAL_REPLICATION"),
    ("*GEN-C3-GEN-C6-NONCOMPENSATORY*", "CAPITAL_AMPLIFICATION"),
    ("*cibo_genc11_genc13_utility_gate*", "CAPITAL_AMPLIFICATION"),
    ("*GEN-C11-GEN-C13-NONCOMPENSATORY*", "CAPITAL_AMPLIFICATION"),
    ("*cibo_genc9_economic_gate*", "GEN-C9"),
    ("*GEN-C9-NONCOMPENSATORY-ECONOMIC-GATE*", "GEN-C9"),
    ("*cibo_compound_path_monte_carlo*", "PATH_DEPENDENT_MONTE_CARLO"),
    ("*cibo_compound_real_population_binding*", "PATH_DEPENDENT_MONTE_CARLO"),
    ("*cibo_governed_capital_science*", "GEN-C14"),
    ("*genc14-autonomous-capital-science*", "GEN-C14"),
    ("*GEN-C14-GOVERNED-AUTONOMOUS-CAPITAL-SCIENCE*", "GEN-C14"),
    ("*cibo_meta_capital_memory*", "GEN-C13"),
    ("*genc13-meta-capital-memory*", "GEN-C13"),
    ("*GEN-C13-META-CAPITAL-MEMORY*", "GEN-C13"),
    ("*cibo_genc12_economic_gate*", "GEN-C12"),
    ("*cibo_crisis_capital_intelligence*", "GEN-C12"),
    ("*genc12-crisis-capital*", "GEN-C12"),
    ("*GEN-C12-CRISIS-CAPITAL-INTELLIGENCE*", "GEN-C12"),
    ("*cibo_multi_period_capital_mpc*", "GEN-C11"),
    ("*genc11-multi-period-mpc*", "GEN-C11"),
    ("*GEN-C11-ROBUST-MULTI-PERIOD-MPC*", "GEN-C11"),
    ("*cibo_capital_digital_twin*", "GEN-C10"),
    ("*cibo_genc10_transition_uncertainty_calibration*", "GEN-C10"),
    ("*genc10-capital-digital-twin*", "GEN-C10"),
    ("*GEN-C10-CAPITAL-DIGITAL-TWIN*", "GEN-C10"),
    ("*cibo_robust_growth_ruin_capacity*", "GEN-C9"),
    ("*cibo-genc9-robust-growth*", "GEN-C9"),
    ("*cibo_integrated_capital_scope_store*", "INTEGRATED_CAPITAL_TRUTH"),
    ("*cibo_integrated_capital_recovery*", "INTEGRATED_CAPITAL_TRUTH"),
    ("*cibo_integrated_capital_component_adapter*", "INTEGRATED_CAPITAL_TRUTH"),
    ("*cibo_integrated_capital_transaction_store*", "INTEGRATED_CAPITAL_TRUTH"),
    ("*cibo_compound_funding_coordination*", "INTEGRATED_CAPITAL_TRUTH"),
    ("*cibo_integrated_capital_truth*", "INTEGRATED_CAPITAL_TRUTH"),
    ("*cibo_protected_base_policy_gate*", "PROTECTED_BASE_CAPITAL"),
    ("*cibo_protected_base_temporal_replication*", "PROTECTED_BASE_CAPITAL"),
    ("*PROTECTED-BASE-NONCOMPENSATORY*", "PROTECTED_BASE_CAPITAL"),
    ("*cibo_protected_base_overlay*", "PROTECTED_BASE_CAPITAL"),
    ("*protected-base-overlay*", "PROTECTED_BASE_CAPITAL"),
    ("tests/infrastructure/test_cibo/*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_adaptive_reasoning*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_reasoning_*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_supervised_runtime*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_operational_supervision_evidence*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_trader_capability_profile*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_trader_development_review*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_trader_lab_authority*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_trader_manager*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_adaptive_router_492*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_fundednext_seed*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_fundednext_cma_binding*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_fundednext_runtime_authority*", "RISK_INTEGRATION"),
    ("*cibo_trader_opportunity_adapter*", "CAPITAL_AMPLIFICATION"),
    ("*cibo_direct_trader_opportunities*", "CAPITAL_AMPLIFICATION"),
    ("*cibo_ce2i_sizing_reconstruction_report*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_arch_a_internal_readiness*", "ZERO_OPEN_WORK_GATE"),
    ("*ARCH-A-INTERNAL-READINESS*", "ZERO_OPEN_WORK_GATE"),
    ("*cibo_final_integrated_exam*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_world_cup_maximum_capability_exam*", "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"),
    ("*cibo_world_cup_entry_controls*", "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"),
    ("*cibo-world-cup-maximum-capability-exam*", "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM"),
    ("*final-integrated-exam*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_final_exam_control_receipt*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_receipt_bound_final_integrated_exam_v2*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_arch_a_final_exam_closure_controls*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_arch_a_final_exam_scientific_controls*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_arch_a_final_source_truth_control*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_arch_a_phase22_pre_outcome*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_arch_a_final_pre_exam_control*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_arch_a_final_exam_system_controls*", "FINAL_INTEGRATED_CIBO_EXAM"),
    ("*cibo_final_certification_contract*", "SOURCE_OF_TRUTH_RECONCILIATION"),
    ("*phase18*", "HISTORICAL_PHASE18_REPLAY_EVIDENCE"),
    ("*phase19*", "BURNED_PHASE19_RESEARCH_EVIDENCE"),
    ("*cibo_cma_*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_capital_management_authority*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_capital_source_ledger*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_capital_state_machine*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_account_capital_mission*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_account_sizing_authority*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_capital_efficiency_reconstruction*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_capital_efficiency_sizing_lab*", "CMA_FOUNDATION_INTEGRATION"),
    ("*cibo_ce2i_burned*", "CE2I_CALIBRATION_GOVERNANCE"),
    ("*cibo_ce2i_calibration*", "CE2I_CALIBRATION_GOVERNANCE"),
    ("*cibo_ce2i_advanced*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_causal_expectation*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_chronological_replay*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_expansion_proposal*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_final_certification*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_full_surface*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_multi_source*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_policy_pipeline*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_portfolio_*", "CE2I_CROSS_TOOL_INFRASTRUCTURE"),
    ("*cibo_ce2i_regime_selector*", "T12"),
    ("*cibo_ce2i_tool_registry*", "SOURCE_OF_TRUTH_RECONCILIATION"),
    ("*cibo_ce2i_usd60*", "USD60_CAPABILITY_PROGRAM"),
    ("*cibo_cognitive_*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_executive_*", "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK"),
    ("*cibo_instrument_capability_registry*", "PROVIDER_ECONOMICS"),
    ("*cibo_ctrader_demo_sizing*", "PROVIDER_ECONOMICS"),
    ("*cibo_economic_floor*", "PROTECTED_BASE_CAPITAL"),
    ("*cibo_marginal_leverage_utility*", "T04"),
    ("*cibo_live_opportunity*", "CAPITAL_AMPLIFICATION"),
    ("*cibo_compound_cycle*", "COMPOUND_ENGINE"),
    ("*cibo_compound_market_cycle*", "COMPOUND_ENGINE"),
    ("*compound-engine-integrated-cycle*", "COMPOUND_ENGINE"),
    ("*zero_open_work*", "ZERO_OPEN_WORK_GATE"),
    ("*generation_current_control*", "AS_IS_CONTROL"),
    ("*adaptive_compound_speed*", "GEN-C8"),
    ("*GEN-C8-ADAPTIVE-COMPOUND-SPEED*", "GEN-C8"),
    ("*profit_preservation*", "GEN-C7"),
    ("*GEN-C7-PROFIT-PRESERVATION*", "GEN-C7"),
    ("*internal_capital_market*", "INTERNAL_CAPITAL_MARKET"),
    ("*sequential_compounding*", "GEN-C5"),
    ("*marginal_capital_utility*", "GEN-C4"),
    ("*compound_floor*", "GEN-C2"),
    ("*core_compound_portfolio*", "COMPOUND_PORTFOLIO"),
    ("*compound_portfolio*", "COMPOUND_PORTFOLIO"),
    ("*compound_capital*", "COMPOUND_ENGINE"),
    ("*t20_capital_release*", "T20"),
    ("*cibo_t08_factor_correlation_lineage*", "T08"),
    ("*phase20_t08*", "T08"),
    ("*phase20_t09_t18*", "T09"),
    ("*phase20_t12*", "T12"),
    ("*phase20_t13*", "T13"),
    ("*phase20_t14*", "T14"),
    ("*phase20_t15*", "T15"),
    ("*dynamic_derisking*", "T14"),
    ("*optionality*", "T15"),
    ("*opportunity_competition*", "T09"),
    ("*opportunity_graph*", "T09"),
    ("*recycling*", "T05"),
    ("*execution_efficiency*", "T11"),
    ("*t02*", "T02"),
    ("*capital_efficient_exposure*", "T03"),
    ("*provider*", "PROVIDER_ECONOMICS"),
    ("*phase20*", "FORWARD_QUALIFICATION"),
    ("*phase21*", "FORWARD_QUALIFICATION"),
    ("*phase22*", "FORWARD_QUALIFICATION"),
    ("*holdout*", "FORWARD_QUALIFICATION"),
    ("*monte_carlo*", "PATH_DEPENDENT_MONTE_CARLO"),
    ("*stress*", "ADVERSARIAL_STRESS"),
    ("*risk*", "RISK_INTEGRATION"),
    ("docs/research/CIBO*", "SOURCE_OF_TRUTH_RECONCILIATION"),
    (".github/workflows/*cibo*", "SOURCE_OF_TRUTH_RECONCILIATION"),
)

_LEDGER_OPEN_STATE_MARKERS = (
    "OPEN_REQUIRED",
    "PARTIAL",
    "ARCHITECTURE_DEFINED",
    "ARCHITECTURE_ONLY",
    "NOT_IMPLEMENTED",
    "PENDING",
    "COLLECTING",
    "BLOCKED_BY_",
    "IMPLEMENTATION_IN_PROGRESS",
    "REVALIDATION_REQUIRED",
)


class CiboZeroOpenWorkGateError(ValueError):
    """Raised when the closure ledger or gate contract is malformed."""


@dataclass(frozen=True, slots=True)
class GateVerdict:
    scope: str
    passed: bool
    mandatory_workstream_count: int
    terminal_workstream_count: int
    open_workstream_ids: tuple[str, ...]
    certification_blocking_external_dependency_ids: tuple[str, ...]
    missing_required_artifacts: tuple[str, ...]
    high_signal_marker_hits: tuple[str, ...]
    inventory_paths: tuple[str, ...]
    inventory_assignments: tuple[tuple[str, str], ...]
    orphan_candidate_paths: tuple[str, ...]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": _GATE_SCHEMA,
            "scope": self.scope,
            "pass": self.passed,
            "mandatory_workstream_count": self.mandatory_workstream_count,
            "terminal_workstream_count": self.terminal_workstream_count,
            "open_workstream_ids": list(self.open_workstream_ids),
            "certification_blocking_external_dependency_ids": list(
                self.certification_blocking_external_dependency_ids
            ),
            "missing_required_artifacts": list(self.missing_required_artifacts),
            "high_signal_marker_hits": list(self.high_signal_marker_hits),
            "inventory_paths": list(self.inventory_paths),
            "inventory_assignments": [
                {"path": path, "workstream_id": workstream_id}
                for path, workstream_id in self.inventory_assignments
            ],
            "orphan_candidate_paths": list(self.orphan_candidate_paths),
            "reasons": list(self.reasons),
        }


def _load_ledger(path: Path = LEDGER_PATH) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CiboZeroOpenWorkGateError(
            "CIBO closure ledger is unreadable"
        ) from error
    if not isinstance(raw, dict) or raw.get("schema") != _SCHEMA:
        raise CiboZeroOpenWorkGateError(
            "CIBO closure ledger schema mismatch"
        )
    terminal = raw.get("terminal_dispositions")
    if not isinstance(terminal, list) or set(terminal) != set(_TERMINAL):
        raise CiboZeroOpenWorkGateError(
            "CIBO closure ledger terminal disposition set drift"
        )
    workstreams = raw.get("workstreams")
    if not isinstance(workstreams, list) or not workstreams:
        raise CiboZeroOpenWorkGateError(
            "CIBO closure ledger requires workstreams"
        )
    return raw


def _validate_current_summary(
    raw: dict[str, Any],
    *,
    mandatory_count: int,
    terminal_count: int,
) -> dict[str, Any]:
    summary = raw.get("current_summary")
    if not isinstance(summary, dict):
        raise CiboZeroOpenWorkGateError(
            "CIBO closure ledger current_summary is required"
        )
    required = (
        "mandatory_count",
        "terminal_count",
        "open_count",
        "zero_open_work_pass",
        "final_certification_candidate",
    )
    missing = tuple(key for key in required if key not in summary)
    if missing:
        raise CiboZeroOpenWorkGateError(
            f"CIBO current_summary missing fields: {missing}"
        )
    expected_open = mandatory_count - terminal_count
    expected = {
        "mandatory_count": mandatory_count,
        "terminal_count": terminal_count,
        "open_count": expected_open,
    }
    for key, value in expected.items():
        actual = summary[key]
        if (
            not isinstance(actual, int)
            or isinstance(actual, bool)
            or actual != value
        ):
            raise CiboZeroOpenWorkGateError(
                f"CIBO current_summary {key} drift"
            )
    for key in (
        "zero_open_work_pass",
        "final_certification_candidate",
    ):
        if type(summary[key]) is not bool:
            raise CiboZeroOpenWorkGateError(
                f"CIBO current_summary {key} must be bool"
            )
    if summary["zero_open_work_pass"] != (expected_open == 0):
        raise CiboZeroOpenWorkGateError(
            "CIBO current_summary zero-open verdict drift"
        )
    if summary["final_certification_candidate"] and expected_open != 0:
        raise CiboZeroOpenWorkGateError(
            "CIBO final-certification candidate cannot retain open work"
        )
    return summary


def _validate_workstream(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise CiboZeroOpenWorkGateError(
            "CIBO workstream row must be object"
        )
    required = (
        "id",
        "kind",
        "mandatory",
        "certification_blocking",
        "current_maturity",
        "terminal_disposition",
        "evidence_refs",
        "blockers",
        "next_gate",
    )
    missing = tuple(key for key in required if key not in row)
    if missing:
        raise CiboZeroOpenWorkGateError(
            f"CIBO workstream missing fields: {missing}"
        )
    if not isinstance(row["id"], str) or not row["id"]:
        raise CiboZeroOpenWorkGateError(
            "CIBO workstream id must be non-empty string"
        )
    for key in ("mandatory", "certification_blocking"):
        if type(row[key]) is not bool:
            raise CiboZeroOpenWorkGateError(
                f"CIBO workstream {key} must be bool"
            )
    if not isinstance(row["current_maturity"], str):
        raise CiboZeroOpenWorkGateError(
            "CIBO workstream current_maturity must be string"
        )
    disposition = row["terminal_disposition"]
    if disposition is not None and disposition not in _TERMINAL:
        raise CiboZeroOpenWorkGateError(
            "CIBO workstream terminal disposition is invalid"
        )
    for key in ("evidence_refs", "blockers"):
        value = row[key]
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item for item in value
        ):
            raise CiboZeroOpenWorkGateError(
                f"CIBO workstream {key} must be string list"
            )
    if not isinstance(row["next_gate"], str) or not row["next_gate"]:
        raise CiboZeroOpenWorkGateError(
            "CIBO workstream next_gate must be non-empty string"
        )
    return row


def _classify_inventory(
    inventory: tuple[str, ...],
    *,
    ledger_ids: frozenset[str],
) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
    assignments: list[tuple[str, str]] = []
    orphan_candidates: list[str] = []
    for relative in inventory:
        workstream_id: str | None = None
        for pattern, candidate in _WORKSTREAM_CLASSIFIERS:
            if fnmatch.fnmatch(relative, pattern):
                workstream_id = candidate
                break
        if workstream_id is None:
            workstream_id = "ORPHAN_INVENTORY"
            orphan_candidates.append(relative)
        if workstream_id not in ledger_ids:
            raise CiboZeroOpenWorkGateError(
                f"inventory classifier points outside ledger: {workstream_id}"
            )
        assignments.append((relative, workstream_id))
    return tuple(assignments), tuple(orphan_candidates)


def _inventory_paths(repo_root: Path) -> tuple[str, ...]:
    found: set[str] = set()
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(repo_root).as_posix()
        if any(
            fnmatch.fnmatch(relative, pattern)
            for pattern in _INVENTORY_GLOBS
        ):
            found.add(relative)
    return tuple(sorted(found))


def _scan_high_signal_markers(
    repo_root: Path,
    inventory: tuple[str, ...],
) -> tuple[str, ...]:
    hits: list[str] = []
    for relative in inventory:
        if not any(
            fnmatch.fnmatch(relative, pattern)
            for pattern in _MARKER_SCAN_GLOBS
        ):
            continue
        path = repo_root / relative
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if relative.endswith(".py"):
            hits.extend(_python_marker_hits(relative, source))
        else:
            hits.extend(_text_comment_marker_hits(relative, source))
    return tuple(sorted(set(hits)))


def _python_marker_hits(relative: str, source: str) -> list[str]:
    hits: list[str] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            for marker in _COMMENT_MARKERS:
                if marker in token.string:
                    hits.append(
                        f"{relative}:{token.start[0]}:{marker}"
                    )
    except tokenize.TokenError as error:
        raise CiboZeroOpenWorkGateError(
            f"cannot tokenize mandatory Python source: {relative}"
        ) from error

    try:
        tree = ast.parse(source, filename=relative)
    except SyntaxError as error:
        raise CiboZeroOpenWorkGateError(
            f"cannot parse mandatory Python source: {relative}"
        ) from error
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "NotImplementedError":
            hits.append(
                f"{relative}:{getattr(node, 'lineno', 0)}:"
                "NotImplementedError"
            )
    return hits


def _text_comment_marker_hits(relative: str, source: str) -> list[str]:
    hits: list[str] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            continue
        for marker in _COMMENT_MARKERS:
            if marker in stripped:
                hits.append(f"{relative}:{line_number}:{marker}")
    return hits


def evaluate_gate(
    *,
    repo_root: Path = Path("."),
    ledger_path: Path = LEDGER_PATH,
    excluded_mandatory_ids: frozenset[str] = frozenset(),
    scope: str = "STRICT",
) -> GateVerdict:
    raw = _load_ledger(ledger_path)
    rows = tuple(_validate_workstream(row) for row in raw["workstreams"])
    ids = tuple(str(row["id"]) for row in rows)
    if len(ids) != len(set(ids)):
        raise CiboZeroOpenWorkGateError(
            "CIBO closure ledger contains duplicate workstream ids"
        )

    all_mandatory = tuple(row for row in rows if row["mandatory"])
    unknown_exclusions = excluded_mandatory_ids - frozenset(ids)
    if unknown_exclusions:
        raise CiboZeroOpenWorkGateError(
            f"CIBO zero-open scope excludes unknown ids: {sorted(unknown_exclusions)}"
        )
    if scope not in {"STRICT", "PRE_EXAM"}:
        raise CiboZeroOpenWorkGateError("CIBO zero-open scope is invalid")
    mandatory = tuple(
        row
        for row in all_mandatory
        if str(row["id"]) not in excluded_mandatory_ids
    )
    open_ids: list[str] = []
    blocking_external: list[str] = []
    reasons: list[str] = []

    for row in mandatory:
        disposition = row["terminal_disposition"]
        maturity = str(row["current_maturity"])
        blockers = tuple(str(item) for item in row["blockers"])

        if disposition is None:
            open_ids.append(str(row["id"]))
            continue

        evidence_refs = tuple(str(item) for item in row["evidence_refs"])
        if not evidence_refs:
            raise CiboZeroOpenWorkGateError(
                "terminal workstream requires evidence references"
            )

        if disposition == "EXTERNAL_DEPENDENCY_BLOCKED":
            if bool(row["certification_blocking"]):
                blocking_external.append(str(row["id"]))
            if not blockers:
                raise CiboZeroOpenWorkGateError(
                    "external-dependency disposition requires blocker evidence"
                )
            continue

        if blockers:
            raise CiboZeroOpenWorkGateError(
                "closed terminal workstream cannot retain blockers"
            )
        if any(marker in maturity for marker in _LEDGER_OPEN_STATE_MARKERS):
            raise CiboZeroOpenWorkGateError(
                "closed terminal workstream cannot retain open maturity marker"
            )

    summary = _validate_current_summary(
        raw,
        mandatory_count=len(all_mandatory),
        terminal_count=sum(
            1
            for row in all_mandatory
            if row["terminal_disposition"] is not None
        ),
    )

    missing_artifacts = tuple(
        path
        for path in _REQUIRED_CANONICAL_ARTIFACTS
        if not (repo_root / path).is_file()
    )
    inventory = _inventory_paths(repo_root)
    assignments, orphan_candidates = _classify_inventory(
        inventory,
        ledger_ids=frozenset(ids),
    )
    marker_hits = _scan_high_signal_markers(repo_root, inventory)

    if open_ids:
        reasons.append("UNCLOSED_REQUIRED_WORKSTREAM")
    if blocking_external:
        reasons.append("CERTIFICATION_BLOCKING_EXTERNAL_DEPENDENCY")
    if missing_artifacts:
        reasons.append("MISSING_REQUIRED_ARTIFACT")
    if marker_hits:
        reasons.append("HIGH_SIGNAL_UNRESOLVED_CODE_MARKER")
    if orphan_candidates:
        reasons.append("UNCLASSIFIED_ORPHAN_CANDIDATE")

    passed = not (
        open_ids
        or blocking_external
        or missing_artifacts
        or marker_hits
        or orphan_candidates
    )
    if summary["final_certification_candidate"] and not passed:
        raise CiboZeroOpenWorkGateError(
            "CIBO final-certification candidate contradicts gate evidence"
        )
    return GateVerdict(
        scope=scope,
        passed=passed,
        mandatory_workstream_count=len(mandatory),
        terminal_workstream_count=sum(
            1 for row in mandatory if row["terminal_disposition"] is not None
        ),
        open_workstream_ids=tuple(open_ids),
        certification_blocking_external_dependency_ids=tuple(
            blocking_external
        ),
        missing_required_artifacts=missing_artifacts,
        high_signal_marker_hits=marker_hits,
        inventory_paths=inventory,
        inventory_assignments=assignments,
        orphan_candidate_paths=orphan_candidates,
        reasons=tuple(reasons),
    )


def evaluate_pre_exam_gate(
    *,
    repo_root: Path = Path("."),
    ledger_path: Path = LEDGER_PATH,
) -> GateVerdict:
    """Audit ordinary-certification closure before the final exam itself runs."""

    return evaluate_gate(
        repo_root=repo_root,
        ledger_path=ledger_path,
        excluded_mandatory_ids=_PRE_EXAM_EXCLUDED_WORKSTREAM_IDS,
        scope="PRE_EXAM",
    )


def _write(verdict: GateVerdict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(verdict.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--enforce-certification",
        action="store_true",
        help="Exit non-zero when the zero-open-work gate does not pass.",
    )
    parser.add_argument(
        "--pre-exam",
        action="store_true",
        help=("Exclude only FINAL_INTEGRATED_CIBO_EXAM and "
              "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM from the closure scope."),
    )
    args = parser.parse_args()
    verdict = evaluate_pre_exam_gate() if args.pre_exam else evaluate_gate()
    output_path = PRE_EXAM_OUTPUT_PATH if args.pre_exam else OUTPUT_PATH
    _write(verdict, output_path)
    print(json.dumps(verdict.as_dict(), sort_keys=True))
    if args.enforce_certification and not verdict.passed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
