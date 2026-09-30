#!/usr/bin/env python3
"""Fail-closed reconciliation gate for CIBO Architect A+B integration.

Normal mode validates the integrity of the staged integration state without
claiming final certification. --enforce-certification additionally requires
zero open mandatory work, no cross-boundary support blockers, and the canonical
ledger's final-certification flags.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SCHEMA = "CIBO_AB_INTEGRATION_ACCEPTANCE_V1"
_CHILD_DELTA_SCHEMA = "CIBO_AB_CHILD_DELTA_ACCOUNTING_V1"
_LOCAL_EVIDENCE_PREFIXES = (
    ".github/",
    "docs/",
    "scripts/",
    "src/",
    "tests/",
)


def validate_state(
    matrix: dict[str, Any],
    ledger: dict[str, Any],
    *,
    enforce_certification: bool = False,
) -> list[str]:
    errors: list[str] = []

    if matrix.get("schema") != _SCHEMA:
        errors.append("integration acceptance schema drift")

    for name in ("common_split_base_sha",):
        if _SHA1_RE.fullmatch(str(matrix.get(name, ""))) is None:
            errors.append(f"{name} must be lowercase 40-hex")

    support_blockers: list[str] = []
    resolved_support_blockers: list[str] = []
    for key in ("architect_a", "architect_b"):
        row = matrix.get(key)
        if not isinstance(row, dict):
            errors.append(f"{key} acceptance row missing")
            continue
        if not isinstance(row.get("pr"), int) or isinstance(row.get("pr"), bool):
            errors.append(f"{key} PR identity invalid")
        for sha_name in ("accepted_head_sha", "latest_observed_head_sha"):
            if _SHA1_RE.fullmatch(str(row.get(sha_name, ""))) is None:
                errors.append(f"{key} {sha_name} must be lowercase 40-hex")
        blockers = row.get("support_blockers")
        if not isinstance(blockers, list):
            errors.append(f"{key} support blockers must be list")
            continue
        if len(blockers) != len(set(blockers)):
            errors.append(f"{key} support blockers contain duplicates")
        if any(not isinstance(item, str) or not item for item in blockers):
            errors.append(f"{key} support blockers must be non-empty strings")
        support_blockers.extend(item for item in blockers if isinstance(item, str))
        staged = row.get("integrator_staged_repair_blockers", [])
        resolved = row.get("integrator_resolved_support_blockers", [])
        for label, values in (
            ("staged repair", staged),
            ("resolved support", resolved),
        ):
            if not isinstance(values, list):
                errors.append(
                    f"{key} integrator {label} blockers must be list"
                )
                continue
            if len(values) != len(set(values)):
                errors.append(
                    f"{key} integrator {label} blockers contain duplicates"
                )
            if any(not isinstance(item, str) or not item for item in values):
                errors.append(
                    f"{key} integrator {label} blockers must be non-empty strings"
                )
            unknown = tuple(item for item in values if item not in blockers)
            if unknown:
                errors.append(
                    f"{key} {label} blocker is not present in upstream blockers: "
                    + ",".join(unknown)
                )
        if isinstance(staged, list) and isinstance(resolved, list):
            overlap = tuple(sorted(set(staged) & set(resolved)))
            if overlap:
                errors.append(
                    f"{key} blocker cannot be both staged and resolved: "
                    + ",".join(overlap)
                )
        if isinstance(resolved, list):
            resolved_support_blockers.extend(
                item for item in resolved if isinstance(item, str)
            )

    effective_support_blockers = tuple(
        item
        for item in support_blockers
        if item not in set(resolved_support_blockers)
    )

    workstreams = ledger.get("workstreams")
    if not isinstance(workstreams, list):
        return errors + ["canonical ledger workstreams missing"]

    by_id = {
        row.get("id"): row
        for row in workstreams
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    for required_exam in (
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    ):
        row = by_id.get(required_exam)
        if row is None:
            errors.append(f"required certification workstream missing: {required_exam}")
            continue
        if row.get("mandatory") is not True:
            errors.append(
                "required certification workstream is not mandatory: "
                f"{required_exam}"
            )
        if row.get("certification_blocking") is not True:
            errors.append(
                f"required certification workstream is not blocking: {required_exam}"
            )

    mandatory = [row for row in workstreams if row.get("mandatory") is True]
    terminal = [
        row["id"]
        for row in mandatory
        if isinstance(row.get("terminal_disposition"), str)
        and row["terminal_disposition"]
    ]
    open_ids = [
        row["id"]
        for row in mandatory
        if not row.get("terminal_disposition")
    ]

    matrix_terminal = matrix.get("integrated_terminal_ids")
    if not isinstance(matrix_terminal, list):
        errors.append("integrated_terminal_ids must be list")
        matrix_terminal = []
    elif len(matrix_terminal) != len(set(matrix_terminal)):
        errors.append("integrated_terminal_ids contain duplicates")

    if set(matrix_terminal) != set(terminal):
        errors.append("integrated terminal set does not match canonical ledger")

    summary = ledger.get("current_summary")
    if not isinstance(summary, dict):
        errors.append("canonical ledger current_summary missing")
    else:
        expected = {
            "mandatory_count": len(mandatory),
            "terminal_count": len(terminal),
            "open_count": len(open_ids),
        }
        for key, value in expected.items():
            if summary.get(key) != value:
                errors.append(f"canonical ledger summary {key} drift")

        zero_open = summary.get("zero_open_work_pass")
        final_candidate = summary.get("final_certification_candidate")
        if type(zero_open) is not bool:
            errors.append("zero_open_work_pass must be bool")
        if type(final_candidate) is not bool:
            errors.append("final_certification_candidate must be bool")
        if open_ids and zero_open is True:
            errors.append("zero-open cannot pass while mandatory work remains open")
        if open_ids and final_candidate is True:
            errors.append("final certification candidate cannot be true with open work")

    for flag in ("integration_ready", "certification_ready", "productive_authority"):
        if type(matrix.get(flag)) is not bool:
            errors.append(f"{flag} must be bool")

    if matrix.get("productive_authority") is True:
        errors.append("integrator acceptance cannot grant productive authority")

    if matrix.get("integration_ready") is True and effective_support_blockers:
        errors.append(
            "integration_ready cannot coexist with unresolved support blockers"
        )

    if matrix.get("certification_ready") is True:
        if matrix.get("integration_ready") is not True:
            errors.append("certification_ready requires integration_ready")
        if effective_support_blockers:
            errors.append(
                "certification_ready cannot coexist with unresolved support blockers"
            )
        if open_ids:
            errors.append("certification_ready requires zero open mandatory work")
        if (
            not isinstance(summary, dict)
            or summary.get("zero_open_work_pass") is not True
        ):
            errors.append("certification_ready requires canonical zero-open pass")
        if (
            not isinstance(summary, dict)
            or summary.get("final_certification_candidate") is not True
        ):
            errors.append(
                "certification_ready requires canonical final-certification candidate"
            )

    if enforce_certification and matrix.get("certification_ready") is not True:
        errors.append("CIBO A+B integration is not certification-ready")

    return errors



def validate_child_delta_accounting(
    matrix: dict[str, Any],
    accounting: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if accounting.get("schema") != _CHILD_DELTA_SCHEMA:
        errors.append("child delta accounting schema drift")
        return errors
    if accounting.get("all_child_delta_files_accounted") is not True:
        errors.append("child delta accounting reports unaccounted files")
    if accounting.get("productive_authority") is not False:
        errors.append("child delta accounting cannot grant productive authority")
    if accounting.get("certification_claim") is not False:
        errors.append("child delta accounting cannot claim certification")

    for matrix_key, accounting_key in (
        ("architect_a", "architect_a"),
        ("architect_b", "architect_b"),
    ):
        mrow = matrix.get(matrix_key)
        arow = accounting.get(accounting_key)
        if not isinstance(mrow, dict) or not isinstance(arow, dict):
            errors.append(f"child delta {accounting_key} row missing")
            continue
        if arow.get("pr") != mrow.get("pr"):
            errors.append(f"child delta {accounting_key} PR drift")
        if arow.get("head_sha") != mrow.get("latest_observed_head_sha"):
            errors.append(f"child delta {accounting_key} HEAD drift")
        changed = arow.get("changed_files")
        present = arow.get("files_present_in_integrator_delta")
        if (
            not isinstance(changed, int)
            or isinstance(changed, bool)
            or changed < 0
            or not isinstance(present, int)
            or isinstance(present, bool)
            or present < 0
            or present > changed
        ):
            errors.append(f"child delta {accounting_key} counts invalid")
            continue
        exclusions = (
            arow.get("deliberate_overrides", [])
            if accounting_key == "architect_a"
            else arow.get("deliberate_noncanonical_snapshots", [])
        )
        if not isinstance(exclusions, list):
            errors.append(f"child delta {accounting_key} exclusions invalid")
            continue
        unaccounted = arow.get("unaccounted_files")
        if not isinstance(unaccounted, list):
            errors.append(f"child delta {accounting_key} unaccounted list invalid")
            continue
        if unaccounted:
            errors.append(f"child delta {accounting_key} has unaccounted files")
        if present + len(exclusions) != changed:
            errors.append(f"child delta {accounting_key} accounting count drift")

    return errors

def validate_local_evidence_paths(
    ledger: dict[str, Any],
    *,
    repo_root: Path,
) -> list[str]:
    errors: list[str] = []
    workstreams = ledger.get("workstreams")
    if not isinstance(workstreams, list):
        return ["canonical ledger workstreams missing"]

    for row in workstreams:
        if not isinstance(row, dict):
            continue
        workstream_id = str(row.get("id", "UNKNOWN"))
        refs = row.get("evidence_refs", [])
        if not isinstance(refs, list):
            errors.append(
                f"{workstream_id} evidence_refs must be a list"
            )
            continue
        for ref in refs:
            if not isinstance(ref, str):
                errors.append(
                    f"{workstream_id} evidence ref must be string"
                )
                continue
            if not ref.startswith(_LOCAL_EVIDENCE_PREFIXES):
                continue
            if not (repo_root / ref).is_file():
                errors.append(
                    f"{workstream_id} local evidence missing: {ref}"
                )
    return errors


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--enforce-certification",
        action="store_true",
        help="fail unless the integrated state is final-certification ready",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    matrix = _load(root / "docs/research/CIBO-AB-INTEGRATION-ACCEPTANCE-V1.json")
    ledger = _load(root / "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
    accounting = _load(
        root / "docs/research/CIBO-AB-CHILD-DELTA-ACCOUNTING-V1.json"
    )
    errors = validate_state(
        matrix,
        ledger,
        enforce_certification=args.enforce_certification,
    )
    errors.extend(validate_child_delta_accounting(matrix, accounting))
    errors.extend(
        validate_local_evidence_paths(
            ledger,
            repo_root=root,
        )
    )
    if errors:
        for error in errors:
            print(f"BLOCKED: {error}")
        return 1

    print("CIBO A+B integration reconciliation: CONSISTENT")
    if not matrix["certification_ready"]:
        print("CIBO A+B final certification: NOT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
