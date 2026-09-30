"""Audit/quarantine the legacy CIBO cognitive/executive research stack.

The legacy stack may depend on itself and tests may exercise it. The only
approved current-generation consumer is GEN-C13's reuse of the immutable
executive-memory substrate. Any other src/qore consumer makes the audit fail.

This script grants no runtime authority.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(".")
OUTPUT = Path("artifacts/cibo_legacy_stack_quarantine_v1.json")

LEGACY_MODULES = frozenset(
    {
        "cibo_adaptive_reasoning_runtime",
        "cibo_operational_supervision_evidence",
        "cibo_reasoning_policy",
        "cibo_reasoning_probe",
        "cibo_reasoning_runtime",
        "cibo_supervised_runtime",
        "cibo_trader_capability_profile",
        "cibo_trader_development_review",
        "cibo_trader_lab_authority",
        "cibo_trader_manager",
        "openai_cibo_reasoning_engine",
        "openai_cibo_adaptive_reasoning_engine",
        "openai_cibo_routed_reasoning_engine",
    }
)

LEGACY_PREFIXES = (
    "cibo_cognitive_",
    "cibo_executive_",
)

RETAINED_SHARED_SUBSTRATE = frozenset({"cibo_executive_memory"})
ALLOWED_CURRENT_CONSUMERS = frozenset(
    {"src/qore/infrastructure/cibo_meta_capital_memory.py"}
)


@dataclass(frozen=True, slots=True)
class ImportEdge:
    importer: str
    imported_module: str


def _module_name(path: Path) -> str:
    return path.stem


def _is_legacy_module(name: str) -> bool:
    return (
        name in LEGACY_MODULES
        or any(name.startswith(prefix) for prefix in LEGACY_PREFIXES)
    )


def _target_module(imported: str) -> str | None:
    prefix = "qore.infrastructure."
    if not imported.startswith(prefix):
        return None
    leaf = imported.removeprefix(prefix).split(".", maxsplit=1)[0]
    return leaf if _is_legacy_module(leaf) else None


def _edges() -> tuple[ImportEdge, ...]:
    edges: list[ImportEdge] = []
    for path in sorted((ROOT / "src/qore").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=path.as_posix())
        relative = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                target = _target_module(node.module)
                if target is not None:
                    edges.append(
                        ImportEdge(
                            importer=relative,
                            imported_module=target,
                        )
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target = _target_module(alias.name)
                    if target is not None:
                        edges.append(
                            ImportEdge(
                                importer=relative,
                                imported_module=target,
                            )
                        )
    return tuple(edges)


def build_quarantine_report() -> dict[str, object]:
    edges = _edges()
    legacy_paths = {
        f"src/qore/infrastructure/{name}.py"
        for name in (
            set(LEGACY_MODULES)
            | {
                path.stem
                for path in (ROOT / "src/qore/infrastructure").glob("*.py")
                if _is_legacy_module(path.stem)
            }
        )
    }
    external_edges = tuple(
        edge for edge in edges if edge.importer not in legacy_paths
    )
    allowed_external = tuple(
        edge
        for edge in external_edges
        if edge.importer in ALLOWED_CURRENT_CONSUMERS
        and edge.imported_module in RETAINED_SHARED_SUBSTRATE
    )
    forbidden_external = tuple(
        edge for edge in external_edges if edge not in allowed_external
    )

    present_legacy = tuple(
        sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "src/qore/infrastructure").glob("*.py")
            if _is_legacy_module(path.stem)
        )
    )
    report = {
        "schema": "CIBO_LEGACY_STACK_QUARANTINE_V1",
        "legacy_module_count": len(present_legacy),
        "legacy_modules": list(present_legacy),
        "retained_shared_substrate": sorted(RETAINED_SHARED_SUBSTRATE),
        "allowed_current_consumers": sorted(ALLOWED_CURRENT_CONSUMERS),
        "import_edges": [
            {
                "importer": edge.importer,
                "imported_module": edge.imported_module,
            }
            for edge in edges
        ],
        "allowed_external_edges": [
            {
                "importer": edge.importer,
                "imported_module": edge.imported_module,
            }
            for edge in allowed_external
        ],
        "forbidden_external_edges": [
            {
                "importer": edge.importer,
                "imported_module": edge.imported_module,
            }
            for edge in forbidden_external
        ],
        "productive_runtime_import_detected": bool(forbidden_external),
        "legacy_productive_authority": False,
        "pass": not forbidden_external,
    }
    return report


def main() -> int:
    report = build_quarantine_report()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["pass"] is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
