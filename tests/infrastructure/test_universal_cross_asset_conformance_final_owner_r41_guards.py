from __future__ import annotations

import ast
import math

import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r38_guards as _r38
import test_universal_cross_asset_conformance_final_owner_r39_guards as _r39
import test_universal_cross_asset_conformance_final_owner_r40_guards as _r40
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _merge_values,
    _owner_paths,
    _Value,
)

_FLOAT_CONSTANT_KIND = "exact-float-constant"
_COMPLEX_CONSTANT_KIND = "exact-complex-constant"
_ELLIPSIS_CONSTANT_KIND = "exact-ellipsis-constant"
_ITEMGETTER_FLOAT_PREFIX = "vf:"
_ITEMGETTER_COMPLEX_PREFIX = "vc:"
_R41_DEFINITELY_NON_ITERABLE_KINDS = frozenset(
    {
        *_r40._R40_DEFINITELY_NON_ITERABLE_KINDS,
        _FLOAT_CONSTANT_KIND,
        _COMPLEX_CONSTANT_KIND,
        _ELLIPSIS_CONSTANT_KIND,
    }
)
_R41_EXACT_NON_STRING_BUILTINS_KEY_KINDS = frozenset(
    {
        _FLOAT_CONSTANT_KIND,
        _COMPLEX_CONSTANT_KIND,
        _ELLIPSIS_CONSTANT_KIND,
    }
)


def _r41_float_value(value: float) -> _Value:
    return frozenset({_Atom(_FLOAT_CONSTANT_KIND, value.hex())})


def _r41_complex_value(value: complex) -> _Value:
    return frozenset(
        {
            _Atom(
                _COMPLEX_CONSTANT_KIND,
                f"{value.real.hex()}|{value.imag.hex()}",
            )
        }
    )


def _r41_float_from_atom(atom: _Atom) -> float | None:
    if atom.kind != _FLOAT_CONSTANT_KIND or atom.text is None:
        return None
    return float.fromhex(atom.text)


def _r41_complex_from_atom(atom: _Atom) -> complex | None:
    if atom.kind != _COMPLEX_CONSTANT_KIND or atom.text is None:
        return None
    real_text, separator, imag_text = atom.text.partition("|")
    if not separator:
        return None
    return complex(float.fromhex(real_text), float.fromhex(imag_text))


def _r41_float_key_token(value: float) -> str | None:
    if math.isnan(value):
        return None
    if math.isfinite(value) and value.is_integer():
        return f"i:{int(value)}"
    return f"f:{value.hex()}"


def _r41_numeric_key_token(atom: _Atom) -> str | None:
    float_value = _r41_float_from_atom(atom)
    if float_value is not None:
        return _r41_float_key_token(float_value)

    complex_value = _r41_complex_from_atom(atom)
    if complex_value is None:
        return None
    if math.isnan(complex_value.real) or math.isnan(complex_value.imag):
        return None
    if complex_value.imag == 0.0:
        return _r41_float_key_token(complex_value.real)
    return f"c:{complex_value.real.hex()}|{complex_value.imag.hex()}"


def _r41_key_tokens(value: _Value) -> set[str]:
    tokens = _r38._r38_key_tokens(value)
    for atom in value:
        token = _r41_numeric_key_token(atom)
        if token is not None:
            tokens.add(token)
    return tokens


def _r41_itemgetter_tokens(value: _Value) -> set[str]:
    tokens = _r38._r38_key_tokens(value)
    for atom in value:
        float_value = _r41_float_from_atom(atom)
        if float_value is not None:
            tokens.add(f"{_ITEMGETTER_FLOAT_PREFIX}{float_value.hex()}")
            continue
        complex_value = _r41_complex_from_atom(atom)
        if complex_value is not None:
            tokens.add(
                f"{_ITEMGETTER_COMPLEX_PREFIX}"
                f"{complex_value.real.hex()}|{complex_value.imag.hex()}"
            )
    return tokens


def _r41_selection_tokens(receiver: _Value, key: _Value) -> set[str]:
    tokens = _r38._r38_selection_tokens(receiver, key)
    if _r15._container_kind(receiver) == "mapping":
        tokens.update(_r41_key_tokens(key))
    return tokens


def _r41_selected_slots(receiver: _Value, key: _Value) -> tuple[bool, _Value]:
    wanted_tokens = _r41_selection_tokens(receiver, key)
    selected: set[_Atom] = set()
    matched = False

    for atom in receiver:
        decoded = _r15._decode_selected_slot(atom)
        if decoded is None:
            continue
        token, value_atom = decoded
        if token in wanted_tokens:
            matched = True
            selected.add(value_atom)

    if not matched:
        return False, _UNKNOWN
    return True, frozenset(selected) if selected else _UNKNOWN


def _r41_definitely_non_iterable(value: _Value) -> bool:
    return bool(value) and all(
        atom.kind in _R41_DEFINITELY_NON_ITERABLE_KINDS for atom in value
    )


def _r41_builtins_get_value(key: _Value, default: _Value) -> _Value:
    inherited = _r39._r39_builtins_get_value(key, default)
    if inherited != _UNKNOWN:
        return inherited
    if key and all(
        atom.kind in _R41_EXACT_NON_STRING_BUILTINS_KEY_KINDS for atom in key
    ):
        return default
    return _UNKNOWN


def _r41_value_from_itemgetter_token(token: str) -> _Value:
    if token.startswith(_ITEMGETTER_FLOAT_PREFIX):
        return _r41_float_value(
            float.fromhex(token[len(_ITEMGETTER_FLOAT_PREFIX) :])
        )
    if token.startswith(_ITEMGETTER_COMPLEX_PREFIX):
        payload = token[len(_ITEMGETTER_COMPLEX_PREFIX) :]
        real_text, separator, imag_text = payload.partition("|")
        if separator:
            return _r41_complex_value(
                complex(float.fromhex(real_text), float.fromhex(imag_text))
            )
    if token.startswith("f:"):
        return _r41_float_value(float.fromhex(token[2:]))
    if token.startswith("c:"):
        real_text, separator, imag_text = token[2:].partition("|")
        if separator:
            return _r41_complex_value(
                complex(float.fromhex(real_text), float.fromhex(imag_text))
            )
    return _r40._r40_value_from_itemgetter_token(token)


class _R41NumericStarAndMappingScanner(_r40._R40StarredAndNoneOperatorScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, float):
                return _r41_float_value(node.value)
            if isinstance(node.value, complex):
                return _r41_complex_value(node.value)
            if node.value is Ellipsis:
                return frozenset({_Atom(_ELLIPSIS_CONSTANT_KIND)})

        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, (ast.USub, ast.UAdd))
            and isinstance(node.operand, (ast.Constant, ast.Name))
        ):
            operand = self._scan_expression(node.operand, environment)
            if len(operand) == 1:
                atom = next(iter(operand))
                float_value = _r41_float_from_atom(atom)
                if float_value is not None:
                    return _r41_float_value(
                        -float_value if isinstance(node.op, ast.USub) else float_value
                    )
                complex_value = _r41_complex_from_atom(atom)
                if complex_value is not None:
                    return _r41_complex_value(
                        -complex_value
                        if isinstance(node.op, ast.USub)
                        else complex_value
                    )

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
                        if _r41_definitely_non_iterable(expanded):
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

        if isinstance(node, ast.Dict):
            pairs: list[tuple[_Value, _Value]] = []
            for key_node, value_node in zip(node.keys, node.values, strict=True):
                key_value = (
                    self._scan_expression(key_node, environment)
                    if key_node is not None
                    else _UNKNOWN
                )
                if _r35._r35_failed(key_value):
                    return _r35._FAILURE_VALUE

                value = self._scan_expression(value_node, environment)
                if _r35._r35_failed(value):
                    return _r35._FAILURE_VALUE
                pairs.append((key_value, value))

            selected_by_token: dict[str, _Value] = {}
            for key_value, value in pairs:
                for token in _r41_key_tokens(key_value):
                    selected_by_token[token] = value

            mapping_metadata: set[_Atom] = {_Atom("container-kind", "mapping")}
            for token, selected_value in selected_by_token.items():
                for value_atom in selected_value:
                    mapping_metadata.add(_r15._selected_slot_atom(token, value_atom))
                if _contains_kind(selected_value, "dangerous"):
                    mapping_metadata.add(_Atom("dangerous-key", token))
                if _contains_kind(selected_value, "builtins"):
                    mapping_metadata.add(_Atom("builtins-key", token))

            flattened = [
                _r15._semantic_atoms(item)
                for pair in pairs
                for item in pair
            ]
            return _merge_values(*flattened, frozenset(mapping_metadata))

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
                elif _r41_definitely_non_iterable(value):
                    return [], True
                else:
                    positional[argument_index] = [_r39._UNKNOWN_POSITIONAL_SHAPE]
            else:
                positional[argument_index] = [value]

        arguments: list[_Value] = []
        for values in positional:
            arguments.extend(values if values is not None else [_UNKNOWN])
        return arguments, False

    def _evaluate_non_slice_subscript(
        self,
        receiver: _Value,
        key: _Value,
    ) -> _Value:
        if _r15._container_kind(receiver) == "mapping":
            matched, selected = _r41_selected_slots(receiver, key)
            return selected if matched else _UNKNOWN
        return super()._evaluate_non_slice_subscript(receiver, key)

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
            if _r39._r39_has_unknown_positional_shape(arguments):
                return _UNKNOWN

            if kind == "mapping":
                matched, selected = _r41_selected_slots(receiver, arguments[0])
                if matched:
                    return selected
                if not _r41_selection_tokens(receiver, arguments[0]):
                    return _UNKNOWN
                if node.func.attr == "get" and len(arguments) >= 2:
                    return arguments[1]
                return _UNKNOWN

            if kind == "sequence" and node.func.attr == "__getitem__":
                matched, selected = _r38._r38_selected_slots(
                    receiver,
                    arguments[0],
                )
                return selected if matched else _UNKNOWN

            if _contains_kind(receiver, "builtins"):
                if node.func.attr == "get":
                    if len(arguments) >= 2:
                        return _r41_builtins_get_value(
                            arguments[0],
                            arguments[1],
                        )
                    return _r15._builtins_member_value(arguments[0])
                return _r15._builtins_member_value(arguments[0])

            return _UNKNOWN

        return super()._evaluate_call(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text == "getitem"
            and len(arguments) >= 2
        ):
            kind = _r15._container_kind(arguments[0])
            if kind == "mapping":
                matched, selected = _r41_selected_slots(
                    arguments[0],
                    arguments[1],
                )
                return selected if matched else _UNKNOWN
            if kind == "sequence":
                matched, selected = _r38._r38_selected_slots(
                    arguments[0],
                    arguments[1],
                )
                return selected if matched else _UNKNOWN

        if (
            helper.kind == "itemgetter"
            and helper.text is not None
            and arguments
        ):
            kind = _r15._container_kind(arguments[0])
            if kind is not None:
                key = _r41_value_from_itemgetter_token(helper.text)
                if kind == "mapping":
                    matched, selected = _r41_selected_slots(arguments[0], key)
                    return selected if matched else _UNKNOWN
                if kind == "sequence":
                    matched, selected = _r38._r38_selected_slots(arguments[0], key)
                    return selected if matched else _UNKNOWN

        result = super()._evaluate_special_call(helper, arguments)

        if helper.kind == "helper" and helper.text == "itemgetter" and arguments:
            additions = frozenset(
                _Atom("itemgetter", token)
                for token in _r41_itemgetter_tokens(arguments[0])
            )
            if additions:
                return _merge_values(result, additions)

        return result


def _r41_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R41NumericStarAndMappingScanner().scan(source)


def test_r41_deepseek_numeric_and_ellipsis_star_fail_before_later_arguments() -> None:
    source = """\
def f(*args):
    pass

f(*0.0, eval("1+1"))
f(*0j, exec("pass"))
f(*..., __import__("math"))
missing = 1.5
f(*missing, eval("1+1"))
"""

    assert _r41_dynamic_execution_markers_from_source(source) == ()


def test_r41_numeric_starred_composite_stops_later_elements() -> None:
    source = """\
a = (*0.0, eval("1+1"))
b = [*0j, exec("pass")]
c = (*..., __import__("math"))
"""

    assert _r41_dynamic_execution_markers_from_source(source) == ()


def test_r41_reachable_argument_before_numeric_star_failure_remains_marked() -> None:
    source = """\
def f(*args):
    pass

f(eval("1+1"), *0.0, exec("pass"))
"""

    assert _r41_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r41_bytes_star_is_iterable_and_does_not_suppress_later_execution() -> None:
    source = """\
def f(*args):
    pass

f(*b"ab", eval("1+1"))
"""

    assert _r41_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r41_deepseek_numeric_mapping_keys_use_python_last_write_wins() -> None:
    source = """\
{1: len, 1.0: eval}[1]("1+1")
{1: eval, 1.0: len}[1]("x")
{True: len, 1.0: exec}[1]("pass")
"""

    assert _r41_dynamic_execution_markers_from_source(source) == (
        "call:1",
        "call:3",
    )


def test_r41_exact_float_and_complex_mapping_selection_is_precise() -> None:
    source = """\
{1.5: eval}[1.5]("1+1")
{1.5: len, "eval": eval}[1.5]("x")
{1j: exec}[1j]("pass")
{0: len, 0j: __import__}[False]("math")
"""

    assert _r41_dynamic_execution_markers_from_source(source) == (
        "call:1",
        "call:3",
        "call:4",
    )


def test_r41_operator_accessors_share_numeric_mapping_key_semantics() -> None:
    source = """\
import operator
operator.getitem({1: len, 1.0: eval}, 1)("1+1")
operator.itemgetter(1.0)({1: len, 1.0: exec})("pass")
operator.getitem({1: eval, 1.0: len}, 1)("x")
operator.itemgetter(1.5)({1.5: __import__})("math")
"""

    assert _r41_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
        "call:5",
    )


def test_r41_float_keys_do_not_become_sequence_indices() -> None:
    source = """\
import operator
[len, eval][1.0]("1+1")
operator.getitem([len, eval], 1.0)("1+1")
operator.itemgetter(1.0)([len, eval])("1+1")
"""

    assert _r41_dynamic_execution_markers_from_source(source) == ()


def test_r41_integer_itemgetter_remains_a_valid_sequence_index() -> None:
    source = """\
import operator
operator.itemgetter(1)([len, eval])("1+1")
"""

    assert _r41_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r41_builtins_get_exact_numeric_miss_still_uses_default() -> None:
    source = """\
import builtins
builtins.__dict__.get(0.0, eval)("1+1")
builtins.__dict__.get(1j, exec)("pass")
"""

    assert _r41_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
    )


def test_r41_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r41_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
