from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r56_guards as _r56
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _owner_paths,
)


class _R57Python312ScopeClassifier(_r56._R56RuntimeScopeClassifier):
    def _visit_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
    ) -> None:
        if isinstance(node, ast.GeneratorExp):
            # Generator expressions are not inlined by PEP 709 in Python 3.12.
            # R56's nested-scope treatment is correct for this form, including
            # the rule that the leftmost iterable executes in the outer scope.
            super()._visit_comprehension(node)
            return

        # Python 3.12 / PEP 709 inlines list/set/dict comprehensions. Calls to
        # locals()/vars() in their body therefore observe the containing scope.
        # Keep iteration-target isolation in the scanner environment, but do
        # not reclassify call execution as a nested runtime scope.
        first = node.generators[0]
        self.visit(first.iter)
        for condition in first.ifs:
            self.visit(condition)
        for generator in node.generators[1:]:
            self.visit(generator.iter)
            for condition in generator.ifs:
                self.visit(condition)
        if isinstance(node, ast.DictComp):
            self.visit(node.key)
            self.visit(node.value)
        else:
            self.visit(node.elt)


def _r57_module_call_positions(source: str) -> set[tuple[int, int]]:
    classifier = _R57Python312ScopeClassifier()
    classifier.visit(ast.parse(source))
    return classifier.module_call_positions


class _R57Python312ScopeScanner(_r56._R56ScopePreservingFallbackScanner):
    def scan(self, source: str) -> tuple[str, ...]:
        self._r56_module_calls = _r57_module_call_positions(source)
        self._r56_call_scope_stack = []
        return super(_r56._R56ScopePreservingFallbackScanner, self).scan(source)


def _r57_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R57Python312ScopeScanner().scan(source)


def test_r57_python312_inlined_module_comprehensions_keep_module_vars() -> None:
    sources = (
        'values = [vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)]\n',
        'values = {vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)}\n',
        'values = {_: vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)}\n',
    )

    for source in sources:
        assert _r57_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r57_generator_expression_keeps_nested_vars_scope() -> None:
    source = (
        'values = (vars()["__builtins__"].__dict__["eval"]("1+1") '
        'for _ in (0,))\n'
    )

    assert _r57_dynamic_execution_markers_from_source(source) == ()


def test_r57_generator_leftmost_iterable_uses_enclosing_module_scope() -> None:
    source = (
        'values = (item for item in '
        '(vars()["__builtins__"].__dict__["eval"]("1+1"),))\n'
    )

    assert _r57_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r57_inlined_comprehension_inside_function_is_not_module_vars() -> None:
    source = """\
def run():
    return [vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)]
"""

    assert _r57_dynamic_execution_markers_from_source(source) == ()


def test_r57_r56_inherited_scope_fixes_remain_authoritative() -> None:
    source = """\
def run():
    global eval
    result = eval("1+1")
    eval = lambda value: value
    return result

factory = lambda value=eval("2+2"): value
"""

    markers = _r57_dynamic_execution_markers_from_source(source)
    assert "call:3" in markers
    assert "call:7" in markers


def test_r57_r55_fallback_fixes_remain_authoritative() -> None:
    source = """\
flag = True
mapping = {} if flag else {"missing": len}
mapping.get("missing", eval)("1+1")

class Safe:
    pass
getattr(Safe, "missing", exec)("pass")
"""

    markers = _r57_dynamic_execution_markers_from_source(source)
    assert "call:3" in markers
    assert "call:7" in markers


def test_r57_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r57_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
