from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r39_guards as _r39
import test_universal_cross_asset_conformance_final_owner_r40_guards as _r40
import test_universal_cross_asset_conformance_final_owner_r62_guards as _r62
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _DANGEROUS_CALLABLE,
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _Value,
)

_IMPORTLIB_NAMESPACE: _Value = frozenset({_Atom("importlib")})


class _R62BExecutionEgressAndOrderingScanner(
    _r62._R62OpaqueDangerousArgumentScanner
):
    """Close execution egress, importlib, and failed-star keyword gaps.

    CPython evaluates a keyword value expression even when an earlier starred
    positional expansion is definitely non-iterable, while later positional
    expressions remain unreachable. Preserve the outer call failure but scan
    the reachable keyword expressions so nested dynamic execution is not lost.

    Also fail closed when a function body returns a sensitive callable and when
    the statically known ``importlib.import_module`` callable is invoked or
    rebound. No arbitrary function-return interpretation is introduced.
    """

    def _scan_import(
        self,
        node: ast.Import,
        environment: dict[str, _Value],
    ) -> None:
        super()._scan_import(node, environment)
        for alias in node.names:
            if alias.name == "importlib":
                environment[alias.asname or "importlib"] = _IMPORTLIB_NAMESPACE
            elif alias.name.startswith("importlib.") and alias.asname is None:
                environment["importlib"] = _IMPORTLIB_NAMESPACE

    def _scan_import_from(
        self,
        node: ast.ImportFrom,
        environment: dict[str, _Value],
    ) -> None:
        super()._scan_import_from(node, environment)
        if node.level != 0 or node.module != "importlib":
            return
        for alias in node.names:
            if alias.name == "import_module":
                environment[alias.asname or alias.name] = _DANGEROUS_CALLABLE
            elif alias.name == "*":
                self._mark_binding(node.lineno)

    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node.value, ast.Name):
            base = environment.get(node.value.id, _UNKNOWN)
            if (
                _r12._contains_kind(base, "importlib")
                and node.attr == "import_module"
            ):
                return _DANGEROUS_CALLABLE
        return super()._evaluate_attribute(node, environment)

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.Return):
            if node.value is not None:
                value = self._scan_expression(node.value, environment)
                if self._is_sensitive_value(value):
                    self._mark_binding(node.lineno)
            return
        super()._scan_statement(node, environment)

    def _scan_call_arguments(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> tuple[list[_Value], bool]:
        positional: list[list[_Value] | None] = [None for _ in node.args]
        ordered: list[tuple[int, int, int, int | None, ast.expr, bool]] = []

        for index, argument in enumerate(node.args):
            if isinstance(argument, ast.Starred):
                expression = argument.value
                is_starred = True
            else:
                expression = argument
                is_starred = False
            ordered.append(
                (
                    getattr(argument, "lineno", node.lineno),
                    getattr(argument, "col_offset", 0),
                    index,
                    index,
                    expression,
                    is_starred,
                )
            )

        keyword_offset = len(node.args)
        for keyword_index, keyword in enumerate(node.keywords):
            expression = keyword.value
            ordered.append(
                (
                    getattr(expression, "lineno", node.lineno),
                    getattr(expression, "col_offset", 0),
                    keyword_offset + keyword_index,
                    None,
                    expression,
                    False,
                )
            )

        ordered.sort(key=lambda item: (item[0], item[1], item[2]))
        evaluated_keyword_nodes: set[int] = set()

        for _, _, _, argument_index, expression, is_starred in ordered:
            value = self._scan_expression(expression, environment)
            if _r35._r35_failed(value):
                return [], True
            if argument_index is None:
                evaluated_keyword_nodes.add(id(expression))
                continue

            if is_starred:
                items = _r35._r35_exact_sequence_items(value)
                if items is not None:
                    positional[argument_index] = list(items)
                elif _r40._r40_definitely_non_iterable(value):
                    for keyword in node.keywords:
                        if id(keyword.value) in evaluated_keyword_nodes:
                            continue
                        keyword_value = self._scan_expression(
                            keyword.value,
                            environment,
                        )
                        evaluated_keyword_nodes.add(id(keyword.value))
                        if _r35._r35_failed(keyword_value):
                            break
                    return [], True
                else:
                    positional[argument_index] = [_r39._UNKNOWN_POSITIONAL_SHAPE]
            else:
                positional[argument_index] = [value]

        arguments: list[_Value] = []
        for values in positional:
            arguments.extend(values if values is not None else [_UNKNOWN])
        return arguments, False


def _r62b_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62BExecutionEgressAndOrderingScanner().scan(source)


def test_r62b_cpython_failed_star_evaluates_keywords_not_later_positionals() -> None:
    events: list[str] = []

    def record(label: str) -> str:
        events.append(label)
        return label

    def consume(*arguments: object, **keywords: object) -> None:
        del arguments, keywords

    try:
        consume(*None, record("positional"))  # type: ignore[misc]
    except TypeError:
        pass
    assert events == []

    try:
        consume(*None, candidate=record("keyword"))  # type: ignore[misc]
    except TypeError:
        pass
    assert events == ["keyword"]


def test_r62b_failed_star_preserves_reachable_keyword_dynamic_execution() -> None:
    source = """\
def consume(*arguments, **keywords):
    return arguments, keywords

consume(*None, candidate=eval("1+1"))
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r62b_failed_star_does_not_promote_unexecuted_callable_value() -> None:
    source = """\
def consume(*arguments, **keywords):
    return arguments, keywords

consume(*None, candidate=eval)
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ()


def test_r62b_failed_star_still_skips_later_positional_execution() -> None:
    source = """\
def consume(*arguments):
    return arguments

consume(*None, eval("1+1"))
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ()


def test_r62b_safe_keyword_expression_after_failed_star_stays_clean() -> None:
    source = """\
def consume(*arguments, **keywords):
    return arguments, keywords

consume(*None, candidate=len("abc"))
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ()


def test_r62b_direct_return_of_dangerous_callable_fails_closed() -> None:
    source = """\
def get_eval():
    return eval

get_eval()("1+1")
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r62b_computed_return_of_dangerous_callable_fails_closed() -> None:
    source = """\
import builtins
def get_eval():
    return getattr(builtins, "eval")

get_eval()("1+1")
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ("binding:3",)


def test_r62b_safe_callable_return_does_not_false_positive() -> None:
    source = """\
def get_len():
    return len

get_len()("abc")
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ()


def test_r62b_importlib_import_module_is_dynamic_execution() -> None:
    source = """\
import importlib
importlib.import_module("math")
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62b_importlib_module_and_callable_aliases_remain_dangerous() -> None:
    source = """\
import importlib as il
loader = il.import_module
loader("math")
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == (
        "binding:2",
        "call:3",
    )


def test_r62b_from_importlib_alias_remains_dangerous() -> None:
    source = """\
from importlib import import_module as loader
loader("math")
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62b_safe_importlib_attribute_does_not_false_positive() -> None:
    source = """\
import importlib
value = importlib.util
"""

    assert _r62b_dynamic_execution_markers_from_source(source) == ()


def test_r62b_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62b_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
