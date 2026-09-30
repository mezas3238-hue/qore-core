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
import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LEDGER_PATH = Path("docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json")
OUTPUT_PATH = Path("artifacts/cibo_zero_open_work_gate_v1.json")

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

_REQUIRED_CANONICAL_ARTIFACTS = (
    "docs/research/CIBO-ABSOLUTE-CLOSURE-AMENDMENT-V1.md",
    "docs/research/CIBO-MASTER-OPEN-WORK-LEDGER-V1.json",
    "docs/research/CIBO-SOVEREIGN-CAPITAL-AMPLIFICATION-WORLD-CUP-MISSION-V1.md",
    "docs/research/CIBO-WORLD-CUP-SOVEREIGN-CAPITAL-AMPLIFICATION-GAP-MATRIX-V1.md",
    "docs/research/CIBO-CE2I-ADR-002-CAPITAL-MANAGEMENT-AUTHORITY.md",
    "docs/research/CIBO-CE2I-ADR-003-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING.md",
    "docs/research/CIBO-CAPITAL-MANAGEMENT-AUTHORITY-CE2I-MASTER-ROADMAP-V2.md",
    "docs/research/CIBO-SOVEREIGN-CAPITAL-INTELLIGENCE-COMPOUNDING-MASTER-ROADMAP-V3.md",
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

_HIGH_SIGNAL_MARKERS = (
    "TODO",
    "FIXME",
    "NotImplementedError",
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
    passed: bool
    mandatory_workstream_count: int
    terminal_workstream_count: int
    open_workstream_ids: tuple[str, ...]
    certification_blocking_external_dependency_ids: tuple[str, ...]
    missing_required_artifacts: tuple[str, ...]
    high_signal_marker_hits: tuple[str, ...]
    inventory_paths: tuple[str, ...]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": _GATE_SCHEMA,
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
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for marker in _HIGH_SIGNAL_MARKERS:
                if marker in line:
                    hits.append(f"{relative}:{line_number}:{marker}")
    return tuple(sorted(set(hits)))


def evaluate_gate(
    *,
    repo_root: Path = Path("."),
    ledger_path: Path = LEDGER_PATH,
) -> GateVerdict:
    raw = _load_ledger(ledger_path)
    rows = tuple(_validate_workstream(row) for row in raw["workstreams"])
    ids = tuple(str(row["id"]) for row in rows)
    if len(ids) != len(set(ids)):
        raise CiboZeroOpenWorkGateError(
            "CIBO closure ledger contains duplicate workstream ids"
        )

    mandatory = tuple(row for row in rows if row["mandatory"])
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

        if disposition == "EXTERNAL_DEPENDENCY_BLOCKED":
            if bool(row["certification_blocking"]):
                blocking_external.append(str(row["id"]))
            if not blockers:
                raise CiboZeroOpenWorkGateError(
                    "external-dependency disposition requires blocker evidence"
                )

        if disposition == "COMPLETED_AND_PROVEN":
            if any(marker in maturity for marker in _LEDGER_OPEN_STATE_MARKERS):
                raise CiboZeroOpenWorkGateError(
                    "completed workstream cannot retain open maturity marker"
                )
            if blockers:
                raise CiboZeroOpenWorkGateError(
                    "completed workstream cannot retain blockers"
                )

    missing_artifacts = tuple(
        path
        for path in _REQUIRED_CANONICAL_ARTIFACTS
        if not (repo_root / path).is_file()
    )
    inventory = _inventory_paths(repo_root)
    marker_hits = _scan_high_signal_markers(repo_root, inventory)

    if open_ids:
        reasons.append("UNCLOSED_REQUIRED_WORKSTREAM")
    if blocking_external:
        reasons.append("CERTIFICATION_BLOCKING_EXTERNAL_DEPENDENCY")
    if missing_artifacts:
        reasons.append("MISSING_REQUIRED_ARTIFACT")
    if marker_hits:
        reasons.append("HIGH_SIGNAL_UNRESOLVED_CODE_MARKER")

    passed = not (
        open_ids
        or blocking_external
        or missing_artifacts
        or marker_hits
    )
    return GateVerdict(
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
        reasons=tuple(reasons),
    )


def _write(verdict: GateVerdict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
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
    args = parser.parse_args()
    verdict = evaluate_gate()
    _write(verdict)
    print(json.dumps(verdict.as_dict(), sort_keys=True))
    if args.enforce_certification and not verdict.passed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
