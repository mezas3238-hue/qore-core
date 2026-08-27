from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r27_guards as _r27
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r38_guards as _r38
import test_universal_cross_asset_conformance_final_owner_r39_guards as _r39
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _merge_values,
    _owner_paths,
    _Value,
)

_R40_DEFINITELY_NON_ITERABLE_KINDS = frozenset(
    {
        *_r27._R27_DEFINITELY_NON_ITERABLE_KINDS,
        "bool-index",
        "none",
    }
)


def _r40_definitely_non_iterable(value: _Value) -> bool:
    return bool(value) and all(
        atom.kind in _R40_DEFINITELY_NON_ITERABLE_KINDS for atom in value
    )


def _r40_value_from_itemgetter_token(token: str) -> _Value:
    if token == _r38._NONE_KEY_TOKEN:
        return frozenset({_Atom("none")})
    return _r15._value_from_itemgetter_token(token)


class _R40StarredAndNoneOperatorScanner(_r39._R39StarredFailureAndContainerScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, (ast.Tuple, ast.List)):
            values: list[_Value] = []
            exact = True

            for element in node.elts:
                if isinstance(element, ast.Starred):
                    expanded = self._scan_expression(element.value, environment)
                    if _r35._r35_failed(expanded):
                        return _r35._FAILURE_VALUE
                    items = _r35._r35_exact_sequence_items(expanded)
                    if items is None:
                        if _r40_definitely_non_iterable(expanded):
                            return _r35._FAILURE_VALUE
                        exact = False
                        values.append(expanded)
                    else:
                        values.extend(items)
                    continue

                value = self._scan_expression(element, environment)
                if _r35._r35_failed(value):
                    return _r35._FAILURE_VALUE
                values.append(value)

            if not exact:
                return _merge_values(
                    _UNKNOWN,
                    *(_r15._semantic_atoms(value) for value in values),
                )
            return _r38._r38_sequence_value(values)

        return super()._scan_expression(node, environment)

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

        for _, _, _, argument_index, expression, is_starred in ordered:
            value = self._scan_expression(expression, environment)
            if _r35._r35_failed(value):
                return [], True
            if argument_index is None:
                continue

            if is_starred:
                items = _r35._r35_exact_sequence_items(value)
                if items is not None:
                    positional[argument_index] = list(items)
                elif _r40_definitely_non_iterable(value):
                    return [], True
                else:
                    positional[argument_index] = [_r39._UNKNOWN_POSITIONAL_SHAPE]
            else:
                positional[argument_index] = [value]

        arguments: list[_Value] = []
        for values in positional:
            arguments.extend(values if values is not None else [_UNKNOWN])
        return arguments, False

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text == "getitem"
            and len(arguments) >= 2
            and _r15._container_kind(arguments[0]) is not None
        ):
            matched, selected = _r38._r38_selected_slots(
                arguments[0],
                arguments[1],
            )
            if matched:
                return selected
            if _r38._r38_selection_tokens(arguments[0], arguments[1]):
                return _UNKNOWN

        if (
            helper.kind == "itemgetter"
            and helper.text is not None
            and arguments
            and _r15._container_kind(arguments[0]) is not None
        ):
            key = _r40_value_from_itemgetter_token(helper.text)
            matched, selected = _r38._r38_selected_slots(arguments[0], key)
            if matched:
                return selected
            if _r38._r38_selection_tokens(arguments[0], key):
                return _UNKNOWN

        result = super()._evaluate_special_call(helper, arguments)

        if helper.kind == "helper" and helper.text == "itemgetter" and arguments:
            additions = frozenset(
                _Atom("itemgetter", token)
                for token in _r38._r38_key_tokens(arguments[0])
            )
            if additions:
                return _merge_values(result, additions)

        return result


def _r40_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R40StarredAndNoneOperatorScanner().scan(source)


def test_r40_deepseek_none_and_bool_starred_fail_before_later_arguments() -> None:
    source = """\
def f(*args):
    pass

f(*None, eval("1+1"))
f(*True, exec("pass"))
none_alias = None
f(*none_alias, eval("1+1"))
"""

    assert _r40_dynamic_execution_markers_from_source(source) == ()


def test_r40_reachable_argument_before_non_iterable_star_remains_marked() -> None:
    source = """\
def f(*args):
    pass

f(eval("1+1"), *False, exec("pass"))
"""

    assert _r40_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r40_none_and_bool_starred_composites_fail_before_later_elements() -> None:
    source = """\
a = (*None, eval("1+1"))
b = [*True, exec("pass")]
"""

    assert _r40_dynamic_execution_markers_from_source(source) == ()


def test_r40_deepseek_operator_getitem_none_key_selects_exact_slot() -> None:
    source = """\
import operator
operator.getitem({None: eval}, None)("1+1")
"""

    assert _r40_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r40_deepseek_operator_itemgetter_none_key_selects_exact_slot() -> None:
    source = """\
import operator
operator.itemgetter(None)({None: exec})("pass")
"""

    assert _r40_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r40_none_operator_accessors_ignore_co_present_dangerous_values() -> None:
    source = """\
import operator
operator.getitem({None: len, "eval": eval}, None)("x")
operator.itemgetter(None)({None: len, "exec": exec})("x")
"""

    assert _r40_dynamic_execution_markers_from_source(source) == ()


def test_r40_operator_signed_sequence_selection_remains_exact() -> None:
    source = """\
import operator
operator.getitem([len, eval], -1)("1+1")
operator.itemgetter(-1)([len, eval])("1+1")
"""

    assert _r40_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
    )


def test_r40_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r40_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
