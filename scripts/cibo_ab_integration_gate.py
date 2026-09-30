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

    if matrix.get("integration_ready") is True and support_blockers:
        errors.append("integration_ready cannot coexist with support blockers")

    if matrix.get("certification_ready") is True:
        if matrix.get("integration_ready") is not True:
            errors.append("certification_ready requires integration_ready")
        if support_blockers:
            errors.append("certification_ready cannot coexist with support blockers")
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
    errors = validate_state(
        matrix,
        ledger,
        enforce_certification=args.enforce_certification,
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
