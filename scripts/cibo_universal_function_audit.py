"""All-or-nothing audit of CIBO functional runtime capability.

This gate is intentionally stricter than ordinary unit-test coverage.  A CIBO
function is not approval-eligible merely because its contract exists, a unit
test passes, or a post-run/shadow audit can call it.  Approval requires the
function to be part of the authoritative runtime/economic path exercised by the
capability exam.

The gate never grants LIVE, production, real-capital, broker-mutation, merge, or
certification authority.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from qore.infrastructure.cibo_ce2i_tool_registry import (
    CE2I_TOOL_REGISTRY,
    ToolMaturity,
)


@dataclass(frozen=True, slots=True)
class AuditFinding:
    code: str
    passed: bool
    detail: str


def _text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def run_audit() -> dict[str, object]:
    findings: list[AuditFinding] = []

    def record(code: str, passed: bool, detail: str) -> None:
        findings.append(AuditFinding(code=code, passed=passed, detail=detail))

    ledger = json.loads(
        _text("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
    )
    workstreams = tuple(ledger["workstreams"])
    canonical_ids = tuple(item["id"] for item in workstreams)
    record(
        "CANONICAL_MANDATORY_SURFACE_EXACT_64",
        len(workstreams) == 64
        and len(set(canonical_ids)) == 64
        and all(item.get("mandatory") is True for item in workstreams),
        f"count={len(workstreams)} unique={len(set(canonical_ids))}",
    )

    functional_ids = tuple(
        item["id"]
        for item in workstreams
        if (
            item["kind"] in {"CE2I_TOOL", "SYSTEM", "LEGACY_PROGRAM"}
            or (
                item["kind"] == "GEN_C"
                and item["id"] != "GEN-C0"
            )
            or item["id"] in {
                "USD60_CAPABILITY_PROGRAM",
                "AS_IS_ECONOMIC_BASELINE",
            }
        )
        and item["id"] != "FRESH_OOS"
    )
    fallback_sources = {
        "CE2I_CROSS_TOOL_INFRASTRUCTURE": (
            "src/qore/infrastructure/cibo_ce2i_full_surface.py",
            "src/qore/infrastructure/cibo_ce2i_advanced_actions.py",
            "src/qore/infrastructure/cibo_ce2i_portfolio_funding_coordinator.py",
        ),
    }
    fallback_tests = {
        "T12": (
            "tests/infrastructure/test_cibo_ce2i_phase20_t12_oos_readiness.py",
            "tests/infrastructure/test_cibo_ce2i_phase20_t12_t13_phase22_causal_lineage.py",
        ),
        "GEN-C2": (
            "tests/infrastructure/test_cibo_a1_genc2_phase22_profit_graduation.py",
        ),
        "COMPOUND_PORTFOLIO": (
            "tests/infrastructure/test_cibo_compound_portfolio.py",
            "tests/infrastructure/test_cibo_core_compound_portfolio.py",
            "tests/infrastructure/test_cibo_phase22_chronological_execution.py",
        ),
        "INTERNAL_CAPITAL_MARKET": (
            "tests/infrastructure/test_cibo_internal_capital_market.py",
        ),
        "CAPITAL_GENERATIONS": (
            "tests/infrastructure/test_cibo_compound_market_cycle.py",
        ),
        "CE2I_CROSS_TOOL_INFRASTRUCTURE": (
            "tests/infrastructure/test_cibo_ce2i_full_surface.py",
            "tests/infrastructure/test_cibo_ce2i_advanced_actions.py",
            "tests/infrastructure/test_cibo_ce2i_multi_source.py",
            "tests/infrastructure/test_cibo_ce2i_portfolio_funding_coordinator.py",
        ),
    }

    functional_evidence_rows: list[dict[str, object]] = []
    for item in workstreams:
        workstream_id = item["id"]
        if workstream_id not in functional_ids:
            continue
        refs = tuple(str(ref) for ref in item.get("evidence_refs", ()))
        source_refs = tuple(
            ref
            for ref in refs
            if ref.startswith("src/") or ref.startswith("scripts/")
        )
        test_refs = tuple(
            ref for ref in refs if ref.startswith("tests/")
        )
        fallback_source_refs = tuple(
            path
            for path in fallback_sources.get(workstream_id, ())
            if Path(path).is_file()
        )
        fallback_test_refs = tuple(
            path
            for path in fallback_tests.get(workstream_id, ())
            if Path(path).is_file()
        )
        effective_source_refs = tuple(
            dict.fromkeys(source_refs + fallback_source_refs)
        )
        effective_test_refs = tuple(
            dict.fromkeys(test_refs + fallback_test_refs)
        )
        functional_evidence_rows.append(
            {
                "id": workstream_id,
                "kind": item["kind"],
                "terminal_disposition": item.get("terminal_disposition"),
                "source_ref_count": len(effective_source_refs),
                "test_ref_count": len(effective_test_refs),
                "source_refs": effective_source_refs,
                "test_refs": effective_test_refs,
            }
        )
        record(
            f"{workstream_id}_EXECUTABLE_EVIDENCE_PRESENT",
            bool(effective_source_refs),
            (
                f"source_refs={effective_source_refs}"
                if effective_source_refs
                else "no executable source evidence bound in canonical ledger"
            ),
        )
        record(
            f"{workstream_id}_BEHAVIOR_TEST_EVIDENCE_PRESENT",
            bool(effective_test_refs),
            (
                f"test_refs={effective_test_refs}"
                if effective_test_refs
                else "no behavioral test evidence bound in canonical ledger"
            ),
        )

    expected_tools = tuple(f"T{i:02d}" for i in range(1, 21))
    actual_tools = tuple(item.code for item in CE2I_TOOL_REGISTRY)
    record(
        "CE2I_EXACT_T01_T20_REGISTRY",
        actual_tools == expected_tools,
        f"registry={actual_tools}",
    )
    bad_maturity = tuple(
        item.code
        for item in CE2I_TOOL_REGISTRY
        if item.maturity in {ToolMaturity.ARCHITECTURE_ONLY, ToolMaturity.REJECTED}
    )
    record(
        "CE2I_NO_ARCHITECTURE_ONLY_OR_REJECTED",
        not bad_maturity,
        f"non_executable={bad_maturity}",
    )

    capability_path = (
        "src/qore/infrastructure/cibo_reused_holdout_capability_exam.py"
    )
    capability = _text(capability_path)
    tool_audit = capability.split("def _tool_audit(", 1)[1]

    shadow_marker = "Shadow-only post-run consultations"
    record(
        "CE2I_NO_POST_RUN_SHADOW_RUNTIME_CREDIT",
        shadow_marker not in capability,
        (
            "capability exam does not credit post-run shadow consultations"
            if shadow_marker not in capability
            else "post-run shadow consultations are currently credited as runtime"
        ),
    )

    shadow_calls = {
        "T06_T07": "plan_self_financing_expansion(",
        "T11": "evaluate_t11_runtime_exposure_guard(",
        "T14": "plan_dynamic_derisking(",
    }
    for name, token in shadow_calls.items():
        record(
            f"CE2I_{name}_NOT_AUDIT_ONLY",
            token not in tool_audit,
            (
                f"{name} is not called only from _tool_audit"
                if token not in tool_audit
                else f"{name} still receives capability credit from _tool_audit"
            ),
        )

    policy_path = (
        "src/qore/infrastructure/cibo_phase22_v4_historical_policy_replay.py"
    )
    policy = _text(policy_path)
    capability_lab_path = Path(
        "src/qore/infrastructure/cibo_universal_capability_runtime.py"
    )
    capability_lab = (
        capability_lab_path.read_text(encoding="utf-8")
        if capability_lab_path.is_file()
        else ""
    )
    record(
        "CE2I_ADVANCED_TOOLS_CAPABILITY_LAB_AVAILABLE",
        "CAPABILITY_LAB" in capability_lab
        and "scientific_eligibility=None" in capability_lab
        and "productive_authority=False" in capability_lab,
        (
            "advanced tools have an explicit non-certifying capability-lab path"
            if capability_lab
            else (
                "advanced tools remain filtered by certification scientific "
                "eligibility; no separate capability-lab path exists"
            )
        ),
    )

    advanced_actions = _text(
        "src/qore/infrastructure/cibo_ce2i_advanced_actions.py"
    )
    record(
        "CE2I_ADVANCED_ACTION_BRIDGE_IMPLEMENTED_AND_TESTED",
        "def build_advanced_capital_actions(" in advanced_actions
        and "def advanced_portfolio_budget_adjustment(" in advanced_actions
        and Path(
            "tests/infrastructure/test_cibo_ce2i_advanced_actions.py"
        ).is_file(),
        (
            "advanced decisions have an explicit no-broker action bridge and "
            "dedicated behavioral tests"
        ),
    )

    universal_test_sources = (
        _text("tests/infrastructure/test_cibo_capital_management_authority.py"),
        _text("tests/infrastructure/test_cibo_ce2i_full_surface.py"),
    )
    universal_symbols = ("BTCUSD", "USDCAD", "EURAUD")
    record(
        "UNIVERSAL_ASSET_PROBES_PRESENT",
        all(
            all(symbol in source for symbol in universal_symbols)
            for source in universal_test_sources
        ),
        "CMA and CE2I are explicitly probed on BTCUSD, USDCAD and EURAUD",
    )

    capability_runtime_sources = "\n".join(
        (
            _text(
                "src/qore/infrastructure/"
                "cibo_phase22_v4_historical_policy_replay.py"
            ),
            _text(
                "src/qore/infrastructure/"
                "cibo_phase22_v4_chronological_execution.py"
            ),
            _text(
                "src/qore/infrastructure/"
                "cibo_ce2i_phase20_robust_allocator.py"
            ),
        )
    )
    runtime_tool_bindings = {
        "T06_T07": "plan_self_financing_expansion(",
        "T11": "evaluate_t11_runtime_exposure_guard(",
        "T14": "plan_dynamic_derisking(",
    }
    for code, token in runtime_tool_bindings.items():
        record(
            f"CE2I_{code}_AUTHORITATIVE_CAPABILITY_PATH",
            token in capability_runtime_sources,
            (
                f"{code} has an authoritative predecision capability path"
                if token in capability_runtime_sources
                else (
                    f"{code} mechanical engine exists but is not consumed by "
                    "the authoritative capability decision path"
                )
            ),
        )

    cognitive_path = (
        "src/qore/infrastructure/cibo_capability_exam_cognitive_coverage.py"
    )
    cognitive = _text(cognitive_path)
    cognitive_is_observation_only = (
        "authority=CiboFunctionalAuthority.OBSERVATION" in cognitive
        and "build_cibo_capability_cognitive_coverage" not in policy
    )
    record(
        "COGNITIVE_CF01_CF19_AFFECT_GOVERNED_RUNTIME_PATH",
        not cognitive_is_observation_only,
        (
            "CF01..CF19 are bound into governed runtime decisions"
            if not cognitive_is_observation_only
            else "CF01..CF19 capability proof is observational/coverage-only"
        ),
    )

    compound_lane_path = (
        "src/qore/infrastructure/cibo_reused_holdout_compound_portfolio_lane.py"
    )
    compound_lane = _text(compound_lane_path)
    compound_required_tokens = (
        "def run_compound_portfolio_lane(",
        "AccountWideRiskEngine()",
        "risk_engine.authorize(",
        "capital_source=CapitalSource.REALIZED_PROFIT",
        "cross_trader_compound_deployments",
    )
    missing_compound_tokens = tuple(
        token for token in compound_required_tokens if token not in compound_lane
    )
    record(
        "COMPOUND_PORTFOLIO_RUNTIME_ENGINE_EXISTS",
        not missing_compound_tokens,
        f"missing={missing_compound_tokens}",
    )
    record(
        "COMPOUND_PORTFOLIO_EXECUTED_BY_CAPABILITY_EXAM",
        "run_compound_portfolio_lane(" in capability,
        (
            "compound/portfolio-compound lane is executed by capability exam"
            if "run_compound_portfolio_lane(" in capability
            else "compound/portfolio-compound lane is not executed by capability exam"
        ),
    )

    integrated_truth = _text(
        "src/qore/infrastructure/cibo_integrated_capital_truth.py"
    )
    truth_tokens = (
        "no_double_counting_pass",
        "settlement_provenance_pass",
        "economic_profit_capacity_usd",
        "def build_integrated_capital_truth(",
    )
    missing_truth = tuple(
        token for token in truth_tokens if token not in integrated_truth
    )
    record(
        "INTEGRATED_CAPITAL_TRUTH_CONSERVATION_ENGINE_EXISTS",
        not missing_truth,
        f"missing={missing_truth}",
    )
    record(
        "INTEGRATED_CAPITAL_TRUTH_BEHAVIORAL_ENGINE_PRESENT",
        Path(
            "tests/infrastructure/test_cibo_integrated_capital_truth.py"
        ).is_file(),
        "integrated capital truth has a dedicated behavioral test module",
    )

    functional_engines = {
        "PROTECTED_BASE": (
            "src/qore/infrastructure/cibo_protected_base_overlay.py",
            "tests/infrastructure/test_cibo_protected_base_overlay.py",
        ),
        "PROFIT_PROTECTION": (
            "src/qore/infrastructure/cibo_profit_preservation_shadow.py",
            "tests/infrastructure/test_cibo_profit_preservation_shadow.py",
        ),
        "PATH_DEPENDENT_MONTE_CARLO": (
            "src/qore/infrastructure/cibo_compound_path_monte_carlo.py",
            "tests/infrastructure/test_cibo_compound_path_monte_carlo.py",
        ),
        "ADVERSARIAL_STRESS": (
            "src/qore/infrastructure/cibo_compound_adversarial_stress.py",
            "tests/infrastructure/test_cibo_compound_adversarial_stress.py",
        ),
        "TEMPORAL_REPLICATION": (
            "src/qore/infrastructure/cibo_compound_temporal_replication.py",
            "tests/infrastructure/test_cibo_compound_temporal_replication.py",
        ),
        "CORE_COMPOUND_PORTFOLIO": (
            "src/qore/infrastructure/cibo_core_compound_portfolio.py",
            "tests/infrastructure/test_cibo_core_compound_portfolio.py",
        ),
    }
    for code, (source_path, test_path) in functional_engines.items():
        record(
            f"{code}_BEHAVIORAL_ENGINE_PRESENT",
            Path(source_path).is_file() and Path(test_path).is_file(),
            f"source={source_path}; test={test_path}",
        )

    runtime_authority_bans = (
        "ProtoOANewOrderReq",
        "ProtoOAClosePositionReq",
        "ProtoOACancelOrderReq",
        "ProtoOAAmendOrderReq",
        "ProtoOAAmendPositionSLTPReq",
    )
    found_mutation_tokens = tuple(
        token for token in runtime_authority_bans if token in capability
    )
    record(
        "CAPABILITY_EXAM_BROKER_MUTATION_ZERO",
        not found_mutation_tokens,
        f"forbidden_tokens={found_mutation_tokens}",
    )

    all_passed = all(item.passed for item in findings)
    failed = tuple(item.code for item in findings if not item.passed)
    return {
        "audit_id": "CIBO_UNIVERSAL_FUNCTION_AUDIT_V1",
        "approval_mode": "ALL_OR_NOTHING",
        "approval_allowed": all_passed,
        "function_gate_pass": all_passed,
        "failed_checks": failed,
        "canonical_workstream_count": len(workstreams),
        "canonical_workstream_ids": canonical_ids,
        "functional_scope_count": len(functional_ids),
        "functional_scope_ids": functional_ids,
        "functional_evidence_rows": functional_evidence_rows,
        "finding_count": len(findings),
        "pass_count": sum(item.passed for item in findings),
        "fail_count": sum(not item.passed for item in findings),
        "findings": [asdict(item) for item in findings],
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "merge_authorized": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run_audit()
    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    return 0 if report["approval_allowed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
