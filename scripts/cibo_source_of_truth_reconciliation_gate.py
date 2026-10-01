#!/usr/bin/env python3
"""Canonical source-of-truth reconciliation gate for integrated CIBO.

This gate verifies that the machine ledger, A/B acceptance matrix, child-delta
accounting, integrated evidence register and current governance documents agree
about the integrated state. It validates truthfulness of the checkpoint; it
does not require all scientific workstreams to be closed and grants no
certification or productive authority.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json"
ACCEPTANCE = ROOT / "docs/research/CIBO-AB-INTEGRATION-ACCEPTANCE-V1.json"
ACCOUNTING = ROOT / "docs/research/CIBO-AB-CHILD-DELTA-ACCOUNTING-V1.json"
EVIDENCE = ROOT / "docs/research/CIBO-AB-INTEGRATED-EVIDENCE-REGISTER-V1.json"
ROADMAP = (
    ROOT
    / "docs/research/CIBO-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING-MASTER-ROADMAP-V3.md"
)
WORLD_CUP = (
    ROOT
    / "docs/research/CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md"
)
SEQUENCE = (
    ROOT
    / "docs/research/CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md"
)
SOURCE_DOC = ROOT / "docs/research/CIBO-SOURCE-OF-TRUTH-RECONCILIATION-V1.md"
OUTPUT = ROOT / "artifacts/cibo_source_of_truth_reconciliation_v1.json"

_SCHEMA = "CIBO_SOURCE_OF_TRUTH_RECONCILIATION_GATE_V1"
_ACCEPTANCE_SCHEMA = "CIBO_AB_INTEGRATION_ACCEPTANCE_V1"
_ACCOUNTING_SCHEMA = "CIBO_AB_CHILD_DELTA_ACCOUNTING_V1"
_EVIDENCE_SCHEMA = "CIBO_AB_INTEGRATED_EVIDENCE_REGISTER_V1"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_EXAMS = (
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _pending_by_owner(register: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = register.get("pending_candidates")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("owner")): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("owner"), str)
    }


def validate_reconciliation(repo_root: Path = ROOT) -> list[str]:
    del repo_root  # paths are intentionally canonical to the checked-out repo
    errors: list[str] = []
    ledger = _load(LEDGER)
    acceptance = _load(ACCEPTANCE)
    accounting = _load(ACCOUNTING)
    evidence = _load(EVIDENCE)

    if acceptance.get("schema") != _ACCEPTANCE_SCHEMA:
        errors.append("acceptance schema drift")
    if accounting.get("schema") != _ACCOUNTING_SCHEMA:
        errors.append("child-delta schema drift")
    if evidence.get("schema") != _EVIDENCE_SCHEMA:
        errors.append("evidence-register schema drift")

    workstreams = ledger.get("workstreams")
    if not isinstance(workstreams, list):
        return errors + ["ledger workstreams missing"]
    rows = [row for row in workstreams if isinstance(row, dict)]
    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("ledger workstream ids are not unique")

    mandatory = [row for row in rows if row.get("mandatory") is True]
    terminal = [
        str(row["id"])
        for row in mandatory
        if isinstance(row.get("terminal_disposition"), str)
        and row["terminal_disposition"]
    ]
    open_ids = [
        str(row["id"])
        for row in mandatory
        if not row.get("terminal_disposition")
    ]
    if len(mandatory) != 64:
        errors.append("integrated mandatory workstream count must remain 64")

    summary = ledger.get("current_summary")
    expected_summary = {
        "mandatory_count": len(mandatory),
        "terminal_count": len(terminal),
        "open_count": len(open_ids),
    }
    if not isinstance(summary, dict):
        errors.append("ledger current_summary missing")
    else:
        for key, expected in expected_summary.items():
            if summary.get(key) != expected:
                errors.append(f"ledger summary {key} drift")
        if summary.get("zero_open_work_pass") is not (len(open_ids) == 0):
            errors.append("ledger zero-open truth drift")
        if open_ids and summary.get("final_certification_candidate") is True:
            errors.append("ledger final candidate cannot coexist with open work")

    by_id = {
        str(row.get("id")): row
        for row in rows
        if isinstance(row.get("id"), str)
    }
    for workstream_id in _REQUIRED_EXAMS:
        row = by_id.get(workstream_id)
        if row is None:
            errors.append(f"required exam missing: {workstream_id}")
            continue
        if row.get("mandatory") is not True:
            errors.append(f"required exam not mandatory: {workstream_id}")
        if row.get("certification_blocking") is not True:
            errors.append(f"required exam not certification-blocking: {workstream_id}")

    matrix_terminal = acceptance.get("integrated_terminal_ids")
    if not isinstance(matrix_terminal, list):
        errors.append("acceptance terminal union missing")
    elif set(matrix_terminal) != set(terminal):
        errors.append("acceptance terminal union differs from ledger")

    if acceptance.get("certification_ready") is True and open_ids:
        errors.append("acceptance claims certification with open work")
    if acceptance.get("productive_authority") is not False:
        errors.append("acceptance productive authority must remain false")

    pending = _pending_by_owner(evidence)
    for matrix_key, owner in (
        ("architect_a", "ARCHITECT_A"),
        ("architect_b", "ARCHITECT_B"),
    ):
        matrix_row = acceptance.get(matrix_key)
        accounting_row = accounting.get(matrix_key)
        pending_row = pending.get(owner)
        if not isinstance(matrix_row, dict):
            errors.append(f"{matrix_key} acceptance row missing")
            continue
        latest = str(matrix_row.get("latest_observed_head_sha", ""))
        if _SHA1_RE.fullmatch(latest) is None:
            errors.append(f"{matrix_key} latest head invalid")
        if not isinstance(accounting_row, dict):
            errors.append(f"{matrix_key} child accounting row missing")
        elif accounting_row.get("head_sha") != latest:
            errors.append(f"{matrix_key} child-accounting HEAD drift")
        if not isinstance(pending_row, dict):
            errors.append(f"{owner} evidence pending row missing")
        elif pending_row.get("latest_head_sha") != latest:
            errors.append(f"{owner} evidence-register HEAD drift")

    if accounting.get("all_child_delta_files_accounted") is not True:
        errors.append("child delta inventory is not fully accounted")
    for key in ("architect_a", "architect_b"):
        row = accounting.get(key)
        if not isinstance(row, dict):
            continue
        if row.get("unaccounted_files") != []:
            errors.append(f"{key} contains unaccounted child files")
    if accounting.get("productive_authority") is not False:
        errors.append("child accounting productive authority must be false")
    if accounting.get("certification_claim") is not False:
        errors.append("child accounting certification claim must be false")

    if evidence.get("certification_claim") is not False:
        errors.append("evidence register certification claim must be false")
    if evidence.get("productive_authority") is not False:
        errors.append("evidence register productive authority must be false")

    risk = by_id.get("RISK_INTEGRATION")
    if not isinstance(risk, dict) or risk.get("terminal_disposition") != "COMPLETED_AND_PROVEN":
        errors.append("Risk mechanical closure missing from canonical ledger")
    accepted_batches = evidence.get("accepted_batches")
    risk_evidence = False
    if isinstance(accepted_batches, list):
        for batch in accepted_batches:
            if not isinstance(batch, dict):
                continue
            items = batch.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if (
                    isinstance(item, dict)
                    and item.get("id") == "RISK_INTEGRATION"
                    and item.get("status") == "SUCCESS"
                ):
                    risk_evidence = True
    if not risk_evidence:
        errors.append("Risk terminal ledger lacks accepted SUCCESS evidence")

    docs = {
        "roadmap": ROADMAP.read_text(encoding="utf-8"),
        "world_cup": WORLD_CUP.read_text(encoding="utf-8"),
        "sequence": SEQUENCE.read_text(encoding="utf-8"),
        "source_doc": SOURCE_DOC.read_text(encoding="utf-8"),
    }
    required_phrases = {
        "roadmap": (
            "current 64-mandatory-workstream law supersedes older wording",
            "FINAL_INTEGRATED_CIBO_EXAM",
            "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
            "STRICT ZERO-OPEN",
        ),
        "world_cup": (
            "integrated 64-workstream closure law",
            "mandatory and must become terminal",
            "Final Integrated CIBO Exam",
            "STRICT zero-open",
        ),
        "sequence": (
            "PRE_EXAM PASS",
            "FINAL_INTEGRATED_CIBO_EXAM TERMINAL",
            "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM TERMINAL",
            "STRICT ZERO-OPEN PASS",
        ),
        "source_doc": (
            "GitHub HEAD",
            "code",
            "tests",
            "GitHub Actions evidence",
            "canonical artifacts / ledgers",
            "ADRs and roadmaps",
            "PR body",
        ),
    }
    for name, phrases in required_phrases.items():
        text_value = docs[name]
        for phrase in phrases:
            if phrase not in text_value:
                errors.append(f"{name} missing canonical phrase: {phrase}")

    return errors


def build_report(*, git_sha: str) -> dict[str, Any]:
    if _SHA1_RE.fullmatch(git_sha) is None:
        raise ValueError("git_sha must be lowercase 40-hex")
    errors = validate_reconciliation()
    ledger = _load(LEDGER)
    summary = ledger["current_summary"]
    acceptance = _load(ACCEPTANCE)
    accounting = _load(ACCOUNTING)
    return {
        "schema": _SCHEMA,
        "git_sha": git_sha,
        "pass": not errors,
        "errors": errors,
        "mandatory_count": summary["mandatory_count"],
        "terminal_count": summary["terminal_count"],
        "open_count": summary["open_count"],
        "architect_a_head_sha": acceptance["architect_a"]["latest_observed_head_sha"],
        "architect_b_head_sha": acceptance["architect_b"]["latest_observed_head_sha"],
        "all_child_delta_files_accounted": accounting["all_child_delta_files_accounted"],
        "world_cup_mandatory": True,
        "productive_authority": False,
        "certification_claim": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = build_report(git_sha=args.git_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
