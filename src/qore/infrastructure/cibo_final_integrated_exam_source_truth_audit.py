"""Deterministic repository audit feeding Final Integrated Exam P1."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from qore.infrastructure.cibo_arch_a_final_source_truth_control import (
    FinalSourceTruthManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_LEDGER_SCHEMA = "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1"
_REQUIRED_OPEN_IDS = (
    "FINAL_INTEGRATED_CIBO_EXAM",
    "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
)
_ROLE_PATHS = (
    (
        "master_ledger",
        "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json",
    ),
    (
        "source_truth_reconciliation",
        "docs/research/CIBO-A-B-SOURCE-OF-TRUTH-RECONCILIATION-V1.md",
    ),
    (
        "final_integrated_exam_protocol",
        "docs/research/CIBO-FINAL-INTEGRATED-CERTIFICATION-EXAM-PROTOCOL-V1.md",
    ),
    (
        "world_cup_exam_protocol",
        "docs/research/CIBO-WORLD-CUP-MAXIMUM-CAPABILITY-EXAM-PROTOCOL-V1.md",
    ),
    (
        "certification_sequence",
        "docs/research/CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md",
    ),
    (
        "architect_a_science",
        "src/qore/infrastructure/cibo_arch_a_internal_readiness.py",
    ),
    (
        "architect_b_phase22",
        "src/qore/infrastructure/cibo_phase22_execution_manifest.py",
    ),
)
_SCAN_PATHS = tuple(
    dict.fromkeys(
        [path for _role, path in _ROLE_PATHS]
        + [
            "docs/research/CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md",
            "docs/research/CIBO-SOVEREIGN-CAPITAL-AMPLIFICATION-WORLD-CUP-MISSION-V1.md",
            "docs/research/CIBO-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING-MASTER-ROADMAP-V3.md",
        ]
    )
)
_STALE_PATTERNS = (
    (
        "CURRENT_LEDGER_64_7_57",
        re.compile(
            r"current machine ledger is\s+64 mandatory / 7 terminal / 57 open",
            re.IGNORECASE,
        ),
    ),
    (
        "V1_2017H1_STILL_PROTECTED",
        re.compile(
            r"CIBO_USD60_6M_HOLDOUT_2017H1_V1.{0,120}"
            r"(?:remain|remains) protected",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "V1_2017H1_SEALED_UNTOUCHED",
        re.compile(
            r"2017H1.{0,100}SEALED_UNTOUCHED",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "WORLD_CUP_NOT_MANDATORY",
        re.compile(
            r"WORLD_CUP_MAXIMUM_CAPABILITY_EXAM.{0,180}"
            r"(?:not part of|not.*mandatory)",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)


def _file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CiboCapitalManagementError(
            f"final source-truth cannot read canonical file: {path}"
        ) from error


def _load_ledger(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(_read_text(path))
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "final source-truth ledger invalid JSON"
        ) from error
    if not isinstance(payload, dict) or payload.get("schema") != _LEDGER_SCHEMA:
        raise CiboCapitalManagementError(
            "final source-truth ledger schema drift"
        )
    rows = payload.get("workstreams")
    if (
        not isinstance(rows, list)
        or any(not isinstance(item, dict) for item in rows)
    ):
        raise CiboCapitalManagementError(
            "final source-truth ledger workstreams invalid"
        )
    return payload


def build_final_source_truth_manifest_from_repository(
    *,
    repo_root: Path,
    integrated_git_sha: str,
    architect_a_head_sha: str,
    architect_b_head_sha: str,
    phase22_handoff_manifest_sha256: str,
) -> FinalSourceTruthManifest:
    """Compute P1 inputs from repository bytes instead of manual assertions."""

    root = repo_root.resolve()
    missing = tuple(
        path
        for path in _SCAN_PATHS
        if not (root / path).is_file()
    )

    ledger_path = root / _ROLE_PATHS[0][1]
    if not ledger_path.is_file():
        raise CiboCapitalManagementError(
            "final source-truth master ledger missing"
        )
    ledger = _load_ledger(ledger_path)
    rows = ledger["workstreams"]
    mandatory = [item for item in rows if item.get("mandatory") is True]
    terminal = [
        item for item in mandatory
        if item.get("terminal_disposition") is not None
    ]
    open_ids = tuple(
        str(item.get("id"))
        for item in mandatory
        if item.get("terminal_disposition") is None
    )
    if len(mandatory) != 64 or len(terminal) != 62:
        raise CiboCapitalManagementError(
            "final source-truth requires exact 64/62 pre-exam topology"
        )
    if open_ids != _REQUIRED_OPEN_IDS:
        raise CiboCapitalManagementError(
            "final source-truth requires exact two open exams"
        )

    summary = ledger.get("current_summary")
    expected_summary = {
        "mandatory_count": 64,
        "terminal_count": 62,
        "open_count": 2,
        "zero_open_work_pass": False,
        "final_certification_candidate": False,
    }
    if summary != expected_summary:
        raise CiboCapitalManagementError(
            "final source-truth ledger summary drift"
        )

    blockers = tuple(
        str(item.get("id"))
        for item in mandatory
        if (
            item.get("certification_blocking") is True
            and item.get("terminal_disposition") == "EXTERNAL_DEPENDENCY_BLOCKED"
        )
    )

    file_sha256s: list[tuple[str, str]] = []
    for role, relative in _ROLE_PATHS:
        path = root / relative
        if path.is_file():
            file_sha256s.append((role, _file_sha256(path)))
        else:
            file_sha256s.append(
                (role, "sha256:" + "0" * 64)
            )

    stale: list[str] = []
    for relative in _SCAN_PATHS:
        path = root / relative
        if not path.is_file():
            continue
        text = _read_text(path)
        for pattern_id, pattern in _STALE_PATTERNS:
            if pattern.search(text):
                stale.append(f"{relative}:{pattern_id}")

    return FinalSourceTruthManifest(
        schema="qore.cibo.final-source-truth-manifest.v2",
        integrated_git_sha=integrated_git_sha,
        architect_a_head_sha=architect_a_head_sha,
        architect_b_head_sha=architect_b_head_sha,
        phase22_handoff_manifest_sha256=phase22_handoff_manifest_sha256,
        mandatory_count=len(mandatory),
        terminal_count=len(terminal),
        open_ids=open_ids,
        file_sha256s=tuple(file_sha256s),
        unaccounted_files=missing,
        certification_critical_external_blockers=blockers,
        stale_current_state_claims=tuple(sorted(set(stale))),
    )
