from __future__ import annotations

from scripts.cibo_legacy_stack_quarantine import build_quarantine_report


def test_legacy_stack_is_quarantined_from_current_runtime() -> None:
    report = build_quarantine_report()

    assert report["schema"] == "CIBO_LEGACY_STACK_QUARANTINE_V1"
    assert report["legacy_module_count"] > 0
    assert report["productive_runtime_import_detected"] is False, report["forbidden_external_edges"]
    assert report["forbidden_external_edges"] == []
    assert report["legacy_productive_authority"] is False
    assert report["pass"] is True


def test_only_genc13_may_reuse_executive_memory_substrate() -> None:
    report = build_quarantine_report()
    allowed = report["allowed_external_edges"]

    assert all(
        row == {
            "importer": "src/qore/infrastructure/cibo_meta_capital_memory.py",
            "imported_module": "cibo_executive_memory",
        }
        for row in allowed
    )
