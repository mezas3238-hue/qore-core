from __future__ import annotations

import test_universal_cross_asset_conformance_final_owner_guards as _final
import test_universal_cross_asset_conformance_final_owner_r4_guards as _r4
import test_universal_cross_asset_conformance_final_owner_r52_guards as _r52


def _r53_resolved_owner_imports(module_name: str) -> tuple[str, ...]:
    return _r4._resolved_imported_modules_from_source(
        _final._owner_path(module_name).read_text(encoding="utf-8"),
        package="qore.infrastructure",
    )


def test_r53_r52_already_closes_builtins_alias_container_shapes() -> None:
    source = """\
import builtins as b
c, d = b, builtins
c.eval("1+1")
d.exec("1+1")
x = [b]
x[0].eval("1+1")
"""

    markers = _r52._r52_dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 6):
        assert f"call:{line_number}" in markers


def test_r53_r52_already_closes_subscripted_dangerous_callable() -> None:
    source = """\
x = [eval][0]
x("1+1")
"""

    markers = _r52._r52_dynamic_execution_markers_from_source(source)

    assert "call:2" in markers


def test_r53_absolute_package_import_expands_product_module_for_directionality() -> None:
    source = "from qore.infrastructure import rainbow_option_composition_semantics\n"

    imported = set(
        _r4._resolved_imported_modules_from_source(
            source,
            package="qore.infrastructure",
        )
    )

    assert "qore.infrastructure.rainbow_option_composition_semantics" in imported


def test_r53_generic_and_cross_family_directionality_use_expanded_imports() -> None:
    violations: list[tuple[str, str]] = []

    for module_name in sorted(_final._GENERIC_AUTHORITY_MODULE_NAMES):
        for imported in _r53_resolved_owner_imports(module_name):
            if imported in _final._PRODUCT_QUALIFICATION_MODULE_NAMES:
                violations.append((module_name, imported))

    for module_name, forbidden_imports in sorted(
        _final._FORBIDDEN_DIRECTIONAL_IMPORTS.items()
    ):
        for imported in _r53_resolved_owner_imports(module_name):
            if imported in forbidden_imports:
                violations.append((module_name, imported))

    assert violations == []
