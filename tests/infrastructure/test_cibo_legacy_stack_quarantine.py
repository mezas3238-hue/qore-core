from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_quarantine() -> ModuleType:
    path = Path("scripts/cibo_legacy_stack_quarantine.py")
    spec = importlib.util.spec_from_file_location(
        "cibo_legacy_stack_quarantine",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load legacy-stack quarantine script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


quarantine = _load_quarantine()


def test_legacy_stack_is_quarantined_from_current_runtime() -> None:
    report = quarantine.build_quarantine_report()

    assert report["schema"] == "CIBO_LEGACY_STACK_QUARANTINE_V1"
    assert report["legacy_module_count"] > 0
    assert report["productive_runtime_import_detected"] is False
    assert report["forbidden_external_edges"] == []
    assert report["legacy_productive_authority"] is False
    assert report["pass"] is True


def test_only_genc13_may_reuse_executive_memory_substrate() -> None:
    report = quarantine.build_quarantine_report()
    allowed = report["allowed_external_edges"]

    assert all(
        row == {
            "importer": "src/qore/infrastructure/cibo_meta_capital_memory.py",
            "imported_module": "cibo_executive_memory",
        }
        for row in allowed
    )
