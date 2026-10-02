from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED_CORE = ROOT / "src" / "qore" / "infrastructure" / "core_stack_v2"

FORBIDDEN_SPECIALIST_IMPORT_PREFIXES = (
    "qore.infrastructure.traders",
    "qore.infrastructure.trader_lab",
)


def _imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return tuple(modules)


def test_shared_core_never_imports_specialist_trader_cognition_or_labs() -> None:
    """Shared cognition is QORE-wide; specialist cognition may only sit downstream.

    Trader adapters/laboratories may consume Shared outputs, but the Shared Core
    package itself must never depend on VT31, VT08, Capitalizer, or any future
    specialist trader implementation/lab.  This keeps the frozen authority flow:

        MARKET/CIBO -> SHARED -> ADAPTER -> TRADER COGNITION -> METHODOLOGY
    """

    offenders: list[str] = []
    for path in sorted(SHARED_CORE.glob("*.py")):
        for module in _imported_modules(path):
            if module.startswith(FORBIDDEN_SPECIALIST_IMPORT_PREFIXES):
                offenders.append(f"{path.relative_to(ROOT)} -> {module}")

    assert offenders == [], (
        "Shared Core crossed the specialist-cognition boundary:\n"
        + "\n".join(offenders)
    )
