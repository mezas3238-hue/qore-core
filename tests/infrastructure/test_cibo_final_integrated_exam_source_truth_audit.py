from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.cibo_final_integrated_exam_source_truth_audit import (
    build_final_source_truth_manifest_from_repository,
)

HEAD_A = "a" * 40
HEAD_B = "b" * 40
HEAD_I = "c" * 40


def _sha(label: str) -> str:
    return "sha256:" + sha256(label.encode("utf-8")).hexdigest()


def _ledger(*, external: bool = False) -> dict:
    rows = []
    for index in range(62):
        rows.append(
            {
                "id": f"WORK_{index:02d}",
                "kind": "SYSTEM",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "TERMINAL",
                "terminal_disposition": (
                    "EXTERNAL_DEPENDENCY_BLOCKED"
                    if external and index == 0
                    else "COMPLETED_AND_PROVEN"
                ),
                "evidence_refs": ["evidence"],
                "blockers": (
                    ["REAL_DEPENDENCY"]
                    if external and index == 0
                    else []
                ),
                "next_gate": "terminal",
            }
        )
    for exam_id in (
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    ):
        rows.append(
            {
                "id": exam_id,
                "kind": "CERTIFICATION",
                "mandatory": True,
                "certification_blocking": True,
                "current_maturity": "OPEN",
                "terminal_disposition": None,
                "evidence_refs": [],
                "blockers": ["EXAM_REQUIRED"],
                "next_gate": "run",
            }
        )
    return {
        "schema": "QORE_CIBO_MASTER_OPEN_WORK_LEDGER_V1",
        "workstreams": rows,
        "current_summary": {
            "mandatory_count": 64,
            "terminal_count": 62,
            "open_count": 2,
            "zero_open_work_pass": False,
            "final_certification_candidate": False,
        },
    }


def _write_fixture(root: Path, *, external: bool = False) -> None:
    paths = {
        "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json": (
            json.dumps(_ledger(external=external), indent=2, sort_keys=True)
            + "\n"
        ),
        "docs/research/CIBO-A-B-SOURCE-OF-TRUTH-RECONCILIATION-V1.md": (
            "# reconciled\n64 mandatory / 62 terminal / 2 open\n"
        ),
        "docs/research/CIBO-FINAL-INTEGRATED-CERTIFICATION-EXAM-PROTOCOL-V1.md": (
            "# final protocol\n"
        ),
        "docs/research/CIBO-WORLD-CUP-MAXIMUM-CAPABILITY-EXAM-PROTOCOL-V1.md": (
            "# world cup mandatory protocol\n"
        ),
        "docs/research/CIBO-INTEGRATED-CERTIFICATION-SEQUENCE-AMENDMENT-V1.md": (
            "# sequence\n"
        ),
        "src/qore/infrastructure/cibo_arch_a_internal_readiness.py": (
            "# architect a science\n"
        ),
        "src/qore/infrastructure/cibo_phase22_execution_manifest.py": (
            "# architect b phase22\n"
        ),
        "docs/research/CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md": (
            "# gap matrix\n64/62/2 current\n"
        ),
        "docs/research/CIBO-SOVEREIGN-CAPITAL-AMPLIFICATION-WORLD-CUP-MISSION-V1.md": (
            "# mission\nV1 burned; V2 protected; World Cup separate\n"
        ),
        "docs/research/CIBO-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING-MASTER-ROADMAP-V3.md": (
            "# roadmap\n"
        ),
    }
    for relative, content in paths.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def test_source_truth_audit_computes_clean_manifest(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    report = build_final_source_truth_manifest_from_repository(
        repo_root=tmp_path,
        integrated_git_sha=HEAD_I,
        architect_a_head_sha=HEAD_A,
        architect_b_head_sha=HEAD_B,
        phase22_handoff_manifest_sha256=_sha("phase22"),
    )
    assert report.mandatory_count == 64
    assert report.terminal_count == 62
    assert report.open_ids == (
        "FINAL_INTEGRATED_CIBO_EXAM",
        "WORLD_CUP_MAXIMUM_CAPABILITY_EXAM",
    )
    assert report.unaccounted_files == ()
    assert report.certification_critical_external_blockers == ()
    assert report.stale_current_state_claims == ()


def test_source_truth_audit_derives_external_blockers(tmp_path: Path) -> None:
    _write_fixture(tmp_path, external=True)
    report = build_final_source_truth_manifest_from_repository(
        repo_root=tmp_path,
        integrated_git_sha=HEAD_I,
        architect_a_head_sha=HEAD_A,
        architect_b_head_sha=HEAD_B,
        phase22_handoff_manifest_sha256=_sha("phase22"),
    )
    assert report.certification_critical_external_blockers == ("WORK_00",)


def test_source_truth_audit_detects_stale_current_claim(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    path = (
        tmp_path
        / "docs/research/CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md"
    )
    path.write_text(
        "# gap\nThe current machine ledger is 64 mandatory / 7 terminal / 57 open.\n",
        encoding="utf-8",
    )
    report = build_final_source_truth_manifest_from_repository(
        repo_root=tmp_path,
        integrated_git_sha=HEAD_I,
        architect_a_head_sha=HEAD_A,
        architect_b_head_sha=HEAD_B,
        phase22_handoff_manifest_sha256=_sha("phase22"),
    )
    assert report.stale_current_state_claims == (
        "docs/research/CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md:CURRENT_LEDGER_64_7_57",
    )
