from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r33_guards as _r33
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _owner_paths,
    _Value,
)


class _R34BoolAliasSliceScanner(_r33._R33ExactSliceScanner):
    def _static_slice_component(
        self,
        node: ast.expr | None,
        environment: dict[str, _Value],
    ) -> tuple[bool, int | None]:
        if node is None:
            return True, None

        scanned = self._scan_expression(node, environment)

        if isinstance(node, ast.Constant) and isinstance(node.value, (bool, int)):
            return True, int(node.value)

        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, (ast.UAdd, ast.USub))
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (bool, int))
        ):
            literal = int(node.operand.value)
            return True, literal if isinstance(node.op, ast.UAdd) else -literal

        if len(scanned) == 1:
            atom = next(iter(scanned))
            if atom.kind in {"integer", "bool-index"} and atom.text is not None:
                return True, int(atom.text)

        return False, None


def _r34_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R34BoolAliasSliceScanner().scan(source)


def test_r34_exact_deepseek_bool_alias_upper_bound_witness() -> None:
    source = """\
flag = True
for *fns, tail in ((eval, len),):
    fns[:flag][0]("1+1")
"""

    assert _r34_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r34_false_alias_upper_bound_excludes_dangerous_slot() -> None:
    source = """\
flag = False
for *fns, tail in ((eval, len),):
    fns[:flag][0]("1+1")
"""

    assert _r34_dynamic_execution_markers_from_source(source) == ()


def test_r34_true_alias_lower_bound_recovers_dangerous_suffix() -> None:
    source = """\
start = True
for *fns, tail in ((len, eval, str),):
    fns[start:][0]("1+1")
"""

    assert _r34_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r34_true_alias_step_preserves_exact_sequence_selection() -> None:
    source = """\
step = True
for *fns, tail in ((eval, len, str),):
    fns[::step][0]("1+1")
"""

    assert _r34_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r34_false_alias_step_matches_zero_step_failure() -> None:
    source = """\
step = False
for *fns, tail in ((eval, len),):
    fns[::step][0]("1+1")
"""

    assert _r34_dynamic_execution_markers_from_source(source) == ()


def test_r34_rebound_bool_alias_uses_latest_exact_value() -> None:
    source = """\
flag = True
flag = False
for *fns, tail in ((eval, len),):
    fns[:flag][0]("1+1")
"""

    assert _r34_dynamic_execution_markers_from_source(source) == ()


def test_r34_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r34_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
