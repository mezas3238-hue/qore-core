from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r27_guards as _r27
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r38_guards as _r38
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _merge_values,
    _owner_paths,
    _Value,
)

_EXACT_NON_STRING_CONSTANT_KIND = "exact-non-string-constant"
_UNKNOWN_POSITIONAL_SHAPE_KIND = "unknown-positional-shape"
_UNKNOWN_POSITIONAL_SHAPE = frozenset({_Atom(_UNKNOWN_POSITIONAL_SHAPE_KIND)})
_R39_EXACT_NON_STRING_BUILTINS_KEY_KINDS = frozenset(
    {
        *_r38._EXACT_NON_STRING_KEY_KINDS,
        _EXACT_NON_STRING_CONSTANT_KIND,
    }
)


def _r39_builtins_get_value(key: _Value, default: _Value) -> _Value:
    inherited = _r38._r38_builtins_get_value(key, default)
    if inherited != _UNKNOWN:
        return inherited

    if key and all(
        atom.kind in _R39_EXACT_NON_STRING_BUILTINS_KEY_KINDS for atom in key
    ):
        return default
    return _UNKNOWN


def _r39_has_unknown_positional_shape(arguments: list[_Value]) -> bool:
    return any(
        _contains_kind(argument, _UNKNOWN_POSITIONAL_SHAPE_KIND)
        for argument in arguments
    )


class _R39StarredFailureAndContainerScanner(
    _r38._R38ArgumentExpansionAndMappingScanner
):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node, ast.Constant)
            and node.value is not None
            and not isinstance(node.value, (str, bool, int))
        ):
            return frozenset({_Atom(_EXACT_NON_STRING_CONSTANT_KIND)})

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
                        if _r27._r27_definitely_non_iterable(expanded):
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
                elif _r27._r27_definitely_non_iterable(value):
                    return [], True
                else:
                    positional[argument_index] = [_UNKNOWN_POSITIONAL_SHAPE]
            else:
                positional[argument_index] = [value]

        arguments: list[_Value] = []
        for values in positional:
            arguments.extend(values if values is not None else [_UNKNOWN])
        return arguments, False

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and node.args
        ):
            receiver = self._scan_expression(node.func.value, environment)
            if _r35._r35_failed(receiver):
                return _r35._FAILURE_VALUE

            kind = _r15._container_kind(receiver)
            if node.func.attr == "get" and kind == "sequence":
                return _r35._FAILURE_VALUE

            arguments, failed = self._scan_call_arguments(node, environment)
            if failed:
                return _r35._FAILURE_VALUE
            if not arguments:
                return _UNKNOWN
            if _r39_has_unknown_positional_shape(arguments):
                return _UNKNOWN

            if kind == "mapping" or (
                kind == "sequence" and node.func.attr == "__getitem__"
            ):
                matched, selected = _r38._r38_selected_slots(
                    receiver,
                    arguments[0],
                )
                if matched:
                    return selected

                selectable_tokens = _r38._r38_selection_tokens(
                    receiver,
                    arguments[0],
                )
                if not selectable_tokens:
                    return _UNKNOWN

                if (
                    kind == "mapping"
                    and node.func.attr == "get"
                    and len(arguments) >= 2
                ):
                    return arguments[1]
                return _UNKNOWN

            if _contains_kind(receiver, "builtins"):
                if node.func.attr == "get":
                    if len(arguments) >= 2:
                        return _r39_builtins_get_value(
                            arguments[0],
                            arguments[1],
                        )
                    return _r15._builtins_member_value(arguments[0])
                return _r15._builtins_member_value(arguments[0])

            return _UNKNOWN

        return super()._evaluate_call(node, environment)


def _r39_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R39StarredFailureAndContainerScanner().scan(source)


def test_r39_non_iterable_starred_tuple_stops_later_execution() -> None:
    source = """\
missing = 5
value = (*missing, eval("1+1"))
"""

    assert _r39_dynamic_execution_markers_from_source(source) == ()


def test_r39_non_iterable_starred_call_stops_later_arguments() -> None:
    source = """\
missing = 5
{"present": len}.get(*missing, eval)("x")
"""

    assert _r39_dynamic_execution_markers_from_source(source) == ()


def test_r39_sequence_dunder_getitem_selects_contained_builtins() -> None:
    source = """\
import builtins
[builtins].__getitem__(0).eval("1+1")
"""

    assert _r39_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r39_mapping_dunder_getitem_does_not_become_builtins_namespace() -> None:
    source = """\
import builtins
{"eval": builtins}.__getitem__("eval")("1+1")
"""

    assert _r39_dynamic_execution_markers_from_source(source) == ()


def test_r39_builtins_get_exact_float_and_other_non_string_misses() -> None:
    source = """\
import builtins
builtins.__dict__.get(0.0, eval)("1+1")
builtins.__dict__.get(b"eval", exec)("pass")
builtins.__dict__.get(0j, __import__)("math")
"""

    assert _r39_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
        "call:4",
    )


def test_r39_unselectable_normal_mapping_key_does_not_invent_default() -> None:
    source = """\
{0.0: len}.get(0.0, eval)("x")
"""

    assert _r39_dynamic_execution_markers_from_source(source) == ()


def test_r39_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r39_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
