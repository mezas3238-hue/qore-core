"""Architect-B scoped zero-open-work gate for CIBO.

This gate answers only whether Architect B has assigned every owned workstream a
terminal scientific disposition. It deliberately distinguishes scope closure
from global CIBO certification: EXTERNAL_DEPENDENCY_BLOCKED is terminal for B's
current GitHub-only work, but remains certification-blocking.

It never edits the Master Ledger, opens the 2017H1 holdout, grants runtime
authority, or treats a successful workflow as economic certification.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PACKAGE_PATH = Path(
    "docs/research/CIBO-ARCH-B-TERMINAL-DISPOSITION-PACKAGE-V1.json"
)
OUTPUT_PATH = Path("artifacts/cibo_arch_b_zero_open_work_gate_v1.json")

_SCHEMA = "CIBO_ARCH_B_TERMINAL_DISPOSITION_PACKAGE_V1"
_GATE_SCHEMA = "QORE_CIBO_ARCH_B_ZERO_OPEN_WORK_GATE_V1"

_B_IDS = (
    "T01",
    "T02",
    "T03",
    "T11",
    "T16",
    "T17",
    "T20",
    "PROVIDER_ECONOMICS",
    "FORWARD_QUALIFICATION",
    "FRESH_OOS",
    "RISK_INTEGRATION",
    "CMA_FOUNDATION_INTEGRATION",
    "LEGACY_CIBO_COGNITIVE_EXECUTIVE_STACK",
    "USD60_CAPABILITY_PROGRAM",
    "INTEGRATED_CAPITAL_TRUTH",
)

_TERMINAL = frozenset(
    {
        "COMPLETED_AND_PROVEN",
        "FALSIFIED_AND_CLOSED",
        "SUPERSEDED_WITH_PROVEN_LINEAGE",
        "EXTERNAL_DEPENDENCY_BLOCKED",
    }
)


class ArchitectBZeroOpenWorkGateError(ValueError):
    """Raised when the Architect-B closure package is malformed."""


@dataclass(frozen=True, slots=True)
class ArchitectBGateVerdict:
    passed: bool
    b_workstream_count: int
    terminal_count: int
    open_workstream_ids: tuple[str, ...]
    completed_or_falsified_ids: tuple[str, ...]
    external_dependency_blocked_ids: tuple[str, ...]
    certification_blocking_ids: tuple[str, ...]
    certification_ready: bool
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": _GATE_SCHEMA,
            "pass": self.passed,
            "b_workstream_count": self.b_workstream_count,
            "terminal_count": self.terminal_count,
            "open_workstream_ids": list(self.open_workstream_ids),
            "completed_or_falsified_ids": list(
                self.completed_or_falsified_ids
            ),
            "external_dependency_blocked_ids": list(
                self.external_dependency_blocked_ids
            ),
            "certification_blocking_ids": list(
                self.certification_blocking_ids
            ),
            "certification_ready": self.certification_ready,
            "reasons": list(self.reasons),
        }


def _load_package(path: Path = PACKAGE_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ArchitectBZeroOpenWorkGateError(
            "Architect-B terminal package is unreadable"
        ) from error
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        raise ArchitectBZeroOpenWorkGateError(
            "Architect-B terminal package schema mismatch"
        )
    governance = payload.get("governance")
    if not isinstance(governance, dict):
        raise ArchitectBZeroOpenWorkGateError(
            "Architect-B governance block is required"
        )
    required_false = (
        "master_ledger_modified",
        "holdout_2017h1_opened",
        "live_authority",
        "productive_authority",
        "real_capital_authority",
    )
    if any(governance.get(name) is not False for name in required_false):
        raise ArchitectBZeroOpenWorkGateError(
            "Architect-B closure governance violation"
        )
    if governance.get("draft_unmerged") is not True:
        raise ArchitectBZeroOpenWorkGateError(
            "Architect-B closure must remain DRAFT/unmerged"
        )
    return payload


def evaluate_gate(
    *, package_path: Path = PACKAGE_PATH
) -> ArchitectBGateVerdict:
    payload = _load_package(package_path)
    dispositions = payload.get("dispositions")
    if not isinstance(dispositions, list):
        raise ArchitectBZeroOpenWorkGateError(
            "Architect-B dispositions must be a list"
        )

    by_id: dict[str, dict[str, Any]] = {}
    for raw in dispositions:
        if not isinstance(raw, dict):
            raise ArchitectBZeroOpenWorkGateError(
                "Architect-B disposition row must be object"
            )
        workstream_id = raw.get("id")
        if not isinstance(workstream_id, str) or not workstream_id:
            raise ArchitectBZeroOpenWorkGateError(
                "Architect-B disposition id is required"
            )
        if workstream_id in by_id:
            raise ArchitectBZeroOpenWorkGateError(
                "Architect-B disposition ids must be unique"
            )
        by_id[workstream_id] = raw

    if tuple(by_id) != _B_IDS:
        raise ArchitectBZeroOpenWorkGateError(
            "Architect-B disposition set/order drift"
        )

    open_ids: list[str] = []
    completed_or_falsified: list[str] = []
    external: list[str] = []
    certification_blocking: list[str] = []

    for workstream_id in _B_IDS:
        row = by_id[workstream_id]
        recommendation = row.get("recommendation")
        blocking = row.get("certification_blocking")
        blockers = row.get("blockers")

        if recommendation not in _TERMINAL:
            open_ids.append(workstream_id)
            continue
        if type(blocking) is not bool:
            raise ArchitectBZeroOpenWorkGateError(
                "Architect-B certification_blocking must be bool"
            )
        if not isinstance(blockers, list) or any(
            not isinstance(item, str) or not item for item in blockers
        ):
            raise ArchitectBZeroOpenWorkGateError(
                "Architect-B blockers must be string list"
            )

        if recommendation == "EXTERNAL_DEPENDENCY_BLOCKED":
            if not blocking or not blockers:
                raise ArchitectBZeroOpenWorkGateError(
                    "external dependency must remain blocking with evidence"
                )
            external.append(workstream_id)
            certification_blocking.append(workstream_id)
        else:
            if blocking or blockers:
                raise ArchitectBZeroOpenWorkGateError(
                    "proven/falsified B closure cannot retain blockers"
                )
            completed_or_falsified.append(workstream_id)

    passed = not open_ids
    certification_ready = passed and not certification_blocking
    reasons: list[str] = []
    if open_ids:
        reasons.append("ARCHITECT_B_UNCLOSED_WORKSTREAM")
    if certification_blocking:
        reasons.append(
            "ARCHITECT_B_TERMINAL_EXTERNAL_DEPENDENCIES_STILL_BLOCK_CERTIFICATION"
        )

    return ArchitectBGateVerdict(
        passed=passed,
        b_workstream_count=len(_B_IDS),
        terminal_count=len(_B_IDS) - len(open_ids),
        open_workstream_ids=tuple(open_ids),
        completed_or_falsified_ids=tuple(completed_or_falsified),
        external_dependency_blocked_ids=tuple(external),
        certification_blocking_ids=tuple(certification_blocking),
        certification_ready=certification_ready,
        reasons=tuple(reasons),
    )


def _write(verdict: ArchitectBGateVerdict) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(verdict.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-b-zero-open",
        action="store_true",
        help="Fail only when Architect B still has unclassified/open work.",
    )
    args = parser.parse_args()
    verdict = evaluate_gate()
    _write(verdict)
    print(json.dumps(verdict.as_dict(), sort_keys=True))
    if args.require_b_zero_open and not verdict.passed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
