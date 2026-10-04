"""Static authority/outcome firewall for Shared Lab Data Reality source."""

from __future__ import annotations

import ast
from dataclasses import dataclass


FORBIDDEN_IMPORT_FRAGMENTS: tuple[str, ...] = (
    "ctrader",
    "execution",
    "trader_lab",
    "modules.risk",
    "modules.portfolio",
    "modules.cibo",
    "traders",
)

FORBIDDEN_CALL_FRAGMENTS: tuple[str, ...] = (
    "open_order",
    "close_order",
    "modify_order",
    "open_position",
    "close_position",
    "modify_position",
    "grant_risk",
    "authorize_risk",
    "set_volume",
    "set_sizing",
    "open_holdout",
)

FORBIDDEN_OUTCOME_IDENTIFIERS: tuple[str, ...] = (
    "future_pnl",
    "realized_pnl",
    "trade_outcome",
    "winner_label",
    "profit_target_tuning",
)


@dataclass(frozen=True, slots=True)
class FirewallViolation:
    kind: str
    value: str
    lineno: int


def _call_name(node: ast.Call) -> str:
    target = node.func
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = target
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def inspect_authority_firewall(source: str) -> tuple[FirewallViolation, ...]:
    tree = ast.parse(source)
    violations: list[FirewallViolation] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                lowered = alias.name.lower()
                if any(fragment in lowered for fragment in FORBIDDEN_IMPORT_FRAGMENTS):
                    violations.append(FirewallViolation("FORBIDDEN_IMPORT", alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").lower()
            if any(fragment in module for fragment in FORBIDDEN_IMPORT_FRAGMENTS):
                violations.append(FirewallViolation("FORBIDDEN_IMPORT", node.module or "", node.lineno))
        elif isinstance(node, ast.Call):
            name = _call_name(node).lower()
            if any(fragment in name for fragment in FORBIDDEN_CALL_FRAGMENTS):
                violations.append(FirewallViolation("PRODUCTIVE_CALL", name, node.lineno))
        elif isinstance(node, ast.Name):
            lowered = node.id.lower()
            if lowered in FORBIDDEN_OUTCOME_IDENTIFIERS:
                violations.append(FirewallViolation("OUTCOME_AWARE_IDENTIFIER", node.id, node.lineno))

    return tuple(violations)
