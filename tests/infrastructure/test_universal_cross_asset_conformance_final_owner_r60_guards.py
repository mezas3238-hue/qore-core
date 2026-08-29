from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r39_guards as _r39
import test_universal_cross_asset_conformance_final_owner_r59_guards as _r59
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _owner_paths,
    _Value,
)


class _R60StarredHelperArgumentScanner(
    _r59._R59Python312ComprehensionLocalsScanner
):
    """Expand starred positional arguments for generic helper calls.

    R38+ introduced exact positional-star expansion for selected mapping-call
    paths, but the inherited generic helper path still consumed one abstract
    value per syntactic ``node.args`` entry.  That let inline calls such as
    ``getattr(*(builtins, "eval"))`` collapse two runtime positional arguments
    into one abstract argument and evade dangerous-callable extraction.

    Preserve every inherited non-starred path.  For starred generic calls,
    reuse the authoritative positional expansion/failure machinery already
    present in the scanner chain.  Unknown starred shapes on helper/accessor
    calls fail closed as an explicit review marker rather than degrading
    silently to ``_UNKNOWN``.
    """

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if not any(isinstance(argument, ast.Starred) for argument in node.args):
            return super()._evaluate_call(node, environment)

        # Mapping get/__getitem__ calls already have specialized starred-argument
        # semantics in the inherited R38+ chain.  Preserve that path exactly.
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and node.args
        ):
            return super()._evaluate_call(node, environment)

        # R56+ tracks whether vars()/locals()-sensitive calls execute at module
        # scope.  The generic starred path must preserve that runtime-scope
        # classification while replacing only positional argument assembly.
        self._r56_call_scope_stack.append(
            (node.lineno, node.col_offset) in self._r56_module_calls
        )
        try:
            function = self._scan_expression(node.func, environment)
            if _r35._r35_failed(function):
                return _r35._FAILURE_VALUE

            arguments, failed = self._scan_call_arguments(node, environment)
            if failed:
                return _r35._FAILURE_VALUE

            if _r12._contains_kind(function, "dangerous"):
                self._mark_call(node.lineno)

            helper_atoms = tuple(
                helper
                for helper in function
                if helper.kind in {"helper", "itemgetter", "attrgetter"}
            )
            if helper_atoms and _r39._r39_has_unknown_positional_shape(arguments):
                self._markers.append(f"starred-helper:{node.lineno}")
                return _UNKNOWN

            results: list[_Value] = []
            for helper in function:
                if helper.kind in {"helper", "itemgetter", "attrgetter"}:
                    results.append(self._evaluate_special_call(helper, arguments))
                else:
                    results.append(_UNKNOWN)
            return _r12._merge_values(*results)
        finally:
            self._r56_call_scope_stack.pop()


def _r60_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R60StarredHelperArgumentScanner().scan(source)


def test_r60_claude_getattr_inline_starred_tuple_cannot_hide_eval() -> None:
    source = """\
import builtins
getattr(*(builtins, "eval"))("1+1")
"""

    assert _r60_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r60_claude_operator_getitem_inline_starred_tuple_cannot_hide_eval() -> None:
    source = """\
import builtins
import operator
operator.getitem(*(builtins.__dict__, "eval"))("1+1")
"""

    assert _r60_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r60_exact_safe_starred_helper_shape_does_not_false_positive() -> None:
    source = """\
import builtins
getattr(*(builtins, "len"))("abc")
"""

    assert _r60_dynamic_execution_markers_from_source(source) == ()


def test_r60_unknown_starred_helper_shape_fails_closed_for_review() -> None:
    source = """\
def reveal(arguments):
    return getattr(*arguments)
"""

    assert _r60_dynamic_execution_markers_from_source(source) == (
        "starred-helper:2",
    )


def test_r60_non_iterable_star_fails_before_later_dangerous_argument() -> None:
    source = """\
getattr(*None, eval("1+1"))
"""

    assert _r60_dynamic_execution_markers_from_source(source) == ()


def test_r60_r59_python312_scope_regression_remains_authoritative() -> None:
    source = (
        'values = [vars()["__builtins__"].__dict__["eval"]("1+1") '
        'for _ in (0,)]\n'
    )

    assert _r60_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r60_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r60_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
