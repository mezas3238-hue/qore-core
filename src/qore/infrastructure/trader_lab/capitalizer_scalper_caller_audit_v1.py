"""Static, fail-open-to-UNKNOWN caller census for Scalper source contracts.

This research-only audit identifies literal Python import/call relationships. It
cannot prove dynamic dispatch absent, and it never grants source or trade authority.
It intentionally scans the complete source tree and records unresolved call forms.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from importlib.util import resolve_name
from pathlib import Path
from typing import Any

IDENTITY = "QORE_SCALPER_ENTRY_CALLER_CENSUS_V1"
TEMPORAL_FIELDS = ("h1_state_until", "h1_state_from", "m15_setup_confirmed_at", "m1_trigger_confirmed_at")
TARGETS = (
    "qore.infrastructure.trader_lab.capitalizer_dual_source_entry_acceptance_v1."
    "assess_dual_source_entry",
    "qore.infrastructure.trader_lab.capitalizer_source_strategy_grammar_v2."
    "assess_source_strategy",
    "qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49."
    "build_market_capacity",
    "qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49."
    "_earliest_m1_trigger",
    "qore.infrastructure.trader_lab.capitalizer_ttrades_m1_cisd_observer_v48."
    "observe_first_m1_cisd",
    "qore.infrastructure.trader_lab.capitalizer_ttrades_m1_fvg_cisd_continuation_v48."
    "observe_first_m1_fvg_cisd_continuation",
    "qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics."
    "build_market",
    "qore.infrastructure.trader_lab.capitalizer_master_cognitive_frame."
    "build_master_cognitive_frame",
    "qore.infrastructure.trader_lab.capitalizer_v50_master_cognitive_adapter."
    "adapt_v50_to_master_context",
)


@dataclass(frozen=True, slots=True)
class CallerSite:
    caller: str
    callee: str
    path: str
    line: int


@dataclass(frozen=True, slots=True)
class TemporalAccess:
    owner: str
    field: str
    path: str
    line: int
    access_kind: str


@dataclass(frozen=True, slots=True)
class TargetAudit:
    target: str
    static_call_sites: tuple[CallerSite, ...]
    root_reachable: bool
    classification: str


@dataclass(frozen=True, slots=True)
class CallerCensus:
    identity: str
    source_files_scanned: int
    call_sites_scanned: int
    known_direct_edges: int
    dynamic_call_sites: tuple[str, ...]
    temporal_metadata_accesses: tuple[TemporalAccess, ...]
    targets: tuple[TargetAudit, ...]
    static_analysis_complete: bool = False
    can_certify_source_fidelity: bool = False
    can_authorize_execution: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("unexpected static caller audit identity")
        if (
            self.static_analysis_complete
            or self.can_certify_source_fidelity
            or self.can_authorize_execution
        ):
            raise ValueError("static census cannot claim closed-world runtime authority")


def _module(path: Path, root: Path) -> str:
    parts = path.relative_to(root).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _qualified_import(node: ast.ImportFrom, current_module: str) -> str:
    if not node.level:
        return node.module or ""
    package = current_module.rpartition(".")[0]
    return resolve_name("." * node.level + (node.module or ""), package)


class _Scanner(ast.NodeVisitor):
    def __init__(self, module: str, path: str) -> None:
        self.module = module
        self.path = path
        self.aliases: dict[str, str] = {}
        self.scopes: list[str] = []
        self.calls: list[CallerSite] = []
        self.dynamic: list[str] = []
        self.temporal: list[TemporalAccess] = []
        self.count = 0

    def visit_Import(self, node: ast.Import) -> None:
        for imported in node.names:
            self.aliases[imported.asname or imported.name.split(".")[0]] = (
                imported.name if imported.asname else imported.name.split(".")[0]
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        resolved = _qualified_import(node, self.module)
        for imported in node.names:
            if imported.name != "*":
                self.aliases[imported.asname or imported.name] = (
                    f"{resolved}.{imported.name}"
                )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def _resolve(self, expression: ast.expr) -> str | None:
        if isinstance(expression, ast.Name):
            return self.aliases.get(expression.id, f"{self.module}.{expression.id}")
        if isinstance(expression, ast.Attribute):
            prefix = self._resolve(expression.value)
            return f"{prefix}.{expression.attr}" if prefix else None
        return None

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in TEMPORAL_FIELDS:
            owner = (
                ".".join((self.module, *self.scopes))
                if self.scopes else self.module
            )
            self.temporal.append(
                TemporalAccess(
                    owner=owner,
                    field=node.attr,
                    path=self.path,
                    line=node.lineno,
                    access_kind=("READ" if isinstance(node.ctx, ast.Load) else "WRITE"),
                )
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.count += 1
        caller = ".".join((self.module, *self.scopes)) if self.scopes else self.module
        resolved = self._resolve(node.func)
        if resolved is not None:
            self.calls.append(
                CallerSite(
                    caller=caller,
                    callee=resolved,
                    path=self.path,
                    line=node.lineno,
                )
            )
        if isinstance(node.func, ast.Name) and node.func.id in {
            "getattr", "eval", "exec",
        }:
            self.dynamic.append(f"{self.path}:{node.lineno}:{node.func.id}")
        self.generic_visit(node)


def _reachable(
    graph: dict[str, set[str]], roots: tuple[str, ...]
) -> set[str]:
    visited: set[str] = set()
    queue = deque(roots)
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(sorted(graph.get(current, set()) - visited))
    return visited


def audit_callers(
    root: Path,
    *,
    targets: tuple[str, ...] = TARGETS,
    roots: tuple[str, ...] = (),
) -> CallerCensus:
    """Scan all source modules. Negative evidence is never labelled DEAD CODE."""

    if not root.is_dir():
        raise ValueError("source directory does not exist")
    files = sorted(root.rglob("*.py"))
    if not files:
        raise ValueError("no Python modules found")
    sites: list[CallerSite] = []
    dynamic: list[str] = []
    temporal: list[TemporalAccess] = []
    count = 0
    edges: dict[str, set[str]] = defaultdict(set)

    for path in files:
        module = _module(path, root)
        source = path.read_text(encoding="utf-8")
        scanner = _Scanner(module, str(path.relative_to(root)))
        scanner.visit(ast.parse(source, filename=str(path)))
        count += scanner.count
        sites.extend(scanner.calls)
        dynamic.extend(scanner.dynamic)
        temporal.extend(scanner.temporal)
        for item in scanner.calls:
            edges[item.caller].add(item.callee)

    selected = set(roots) if roots else {
        "qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49."
        "build_market_capacity",
        "qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics."
        "build_market",
    }
    reached = _reachable(edges, tuple(sorted(selected)))
    rows: list[TargetAudit] = []
    for target in targets:
        matches = tuple(
            sorted(
                (item for item in sites if item.callee == target),
                key=lambda item: (item.path, item.line, item.caller),
            )
        )
        is_reachable = target in reached
        rows.append(
            TargetAudit(
                target=target,
                static_call_sites=matches,
                root_reachable=is_reachable,
                classification=(
                    "REACHABLE_FROM_SELECTED_RESEARCH_ENTRYPOINT"
                    if is_reachable
                    else "STATIC_CALLER_FOUND_OUTSIDE_SELECTED_ENTRYPOINT"
                    if matches
                    else "NO_STATIC_CALLER_FOUND_RUNTIME_UNRESOLVED"
                ),
            )
        )
    return CallerCensus(
        identity=IDENTITY,
        source_files_scanned=len(files),
        call_sites_scanned=count,
        known_direct_edges=len(sites),
        dynamic_call_sites=tuple(sorted(dynamic)),
        temporal_metadata_accesses=tuple(sorted(
            temporal, key=lambda item: (item.field, item.path, item.line)
        )),
        targets=tuple(rows),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=Path("src"))
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    report = audit_callers(args.source_root)
    payload: dict[str, Any] = asdict(report)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(
        f"{IDENTITY}: modules={report.source_files_scanned} "
        f"calls={report.call_sites_scanned} "
        f"direct_sites={report.known_direct_edges} "
        f"dynamic_markers={len(report.dynamic_call_sites)}"
    )
    for item in report.targets:
        print(
            f"{item.target}: {item.classification} "
            f"call_sites={len(item.static_call_sites)}"
        )
        for site in item.static_call_sites[:15]:
            print(f"  {site.path}:{site.line} <- {site.caller}")
    sensitive = (
        item for item in report.temporal_metadata_accesses
        if item.field == "h1_state_until" and item.access_kind == "READ"
    )
    for item in sensitive:
        print(f"H1_FUTURE_EXPIRY_READ {item.path}:{item.line} <- {item.owner}")
    print("DISCLAIMER: no static caller does not prove unused runtime code.")


if __name__ == "__main__":
    main()
