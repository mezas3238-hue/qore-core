from __future__ import annotations

import ast

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _DANGEROUS_CALLABLE,
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _owner_paths,
    _R12DynamicExecutionScanner,
    _static_integers,
    _static_strings,
    _Value,
)

_DYNAMIC_EXECUTION_CALL_NAMES = {"__import__", "eval", "exec"}


def _merge_atoms(value: _Value, *atoms: _Atom) -> _Value:
    merged = set(value)
    merged.update(atoms)
    return frozenset(merged)


def _sequence_lengths(value: _Value) -> set[int]:
    return {
        int(atom.text)
        for atom in value
        if atom.kind == "sequence-length" and atom.text is not None
    }


def _selects_dangerous_index(receiver: _Value, index: int) -> bool:
    if _contains_kind(receiver, "dangerous-index", str(index)):
        return True
    if index >= 0:
        return False
    return any(
        0 <= length + index < length
        and _contains_kind(receiver, "dangerous-index", str(length + index))
        for length in _sequence_lengths(receiver)
    )


class _R13DynamicExecutionScanner(_R12DynamicExecutionScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        value = super()._scan_expression(node, environment)
        if isinstance(node, (ast.Tuple, ast.List)):
            return _merge_atoms(value, _Atom("sequence-length", str(len(node.elts))))
        return value

    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        result = super()._evaluate_attribute(node, environment)
        base = self._scan_expression(node.value, environment)
        if _contains_kind(base, "builtins") and node.attr in {"get", "__getitem__"}:
            return _merge_atoms(result, _Atom("helper", f"builtins-map:{node.attr}"))
        return result

    def _evaluate_subscript(
        self,
        node: ast.Subscript,
        environment: dict[str, _Value],
    ) -> _Value:
        base = self._scan_expression(node.value, environment)
        key = self._scan_expression(node.slice, environment)
        result: set[_Atom] = set()

        if _contains_kind(base, "builtins"):
            for key_value in _static_strings(key):
                if key_value in _DYNAMIC_EXECUTION_CALL_NAMES:
                    result.add(_Atom("dangerous"))
                else:
                    result.add(_Atom("unknown"))

        for index in _static_integers(key):
            if _selects_dangerous_index(base, index):
                result.add(_Atom("dangerous"))
            if _contains_kind(base, "dangerous-key", f"i:{index}"):
                result.add(_Atom("dangerous"))

        for key_value in _static_strings(key):
            if _contains_kind(base, "dangerous-key", f"s:{key_value}"):
                result.add(_Atom("dangerous"))

        return frozenset(result) if result else _UNKNOWN

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text is not None
            and helper.text.startswith("builtins-map:")
            and arguments
        ):
            if any(
                key in _DYNAMIC_EXECUTION_CALL_NAMES
                for key in _static_strings(arguments[0])
            ):
                return _DANGEROUS_CALLABLE
            return _UNKNOWN

        result = super()._evaluate_special_call(helper, arguments)
        additions: list[_Atom] = []

        if (
            helper.kind == "helper"
            and helper.text == "getitem"
            and len(arguments) >= 2
        ):
            receiver, key = arguments[0], arguments[1]
            if any(
                _selects_dangerous_index(receiver, index)
                for index in _static_integers(key)
            ):
                additions.append(_Atom("dangerous"))

        if (
            helper.kind == "itemgetter"
            and helper.text is not None
            and helper.text.startswith("i:")
            and arguments
        ):
            index = int(helper.text[2:])
            if _selects_dangerous_index(arguments[0], index):
                additions.append(_Atom("dangerous"))

        return _merge_atoms(result, *additions) if additions else result


def _r13_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R13DynamicExecutionScanner().scan(source)


def test_r13_negative_operator_indices_fail_closed() -> None:
    source = """\
import operator
operator.itemgetter(-1)([eval])(\"1+1\")
operator.getitem([eval], -1)(\"1+1\")
"""

    assert _r13_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
    )


def test_r13_builtins_mapping_method_aliases_fail_closed() -> None:
    source = """\
import builtins
a = builtins.__dict__.get
a(\"eval\")(\"1+1\")
b = vars(builtins).__getitem__
b(\"__import__\")(\"math\")
"""

    assert _r13_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:5",
    )


def test_r13_safe_selected_positions_do_not_false_positive() -> None:
    source = """\
import operator
[len, eval][0](\"x\")
operator.itemgetter(-1)([eval, len])(\"x\")
operator.getitem([eval, len], -1)(\"x\")
"""

    assert _r13_dynamic_execution_markers_from_source(source) == ()


def test_r13_preserves_prior_dangerous_lookup_detection() -> None:
    source = """\
import builtins
import operator
builtins.getattr(builtins, \"eval\")(\"1+1\")
vars(builtins).get(\"exec\")(\"pass\")
operator.itemgetter(0)([eval])(\"1+1\")
getattr(builtins, f\"e{'val'}\")(\"1+1\")
"""

    assert _r13_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:4",
        "call:5",
        "call:6",
    )


def test_r13_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r13_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
