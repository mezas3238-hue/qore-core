from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r30_guards as _r30
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _integer_value,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _selected_slot_atom,
    _selected_slots,
    _sequence_length,
)


def _r31_sequence_value(values: tuple[_Value, ...]) -> _Value:
    metadata: set[_Atom] = {
        _Atom("container-kind", "sequence"),
        _Atom("sequence-length", str(len(values))),
    }
    for index, value in enumerate(values):
        token = f"i:{index}"
        for value_atom in value:
            metadata.add(_selected_slot_atom(token, value_atom))
        if _contains_kind(value, "dangerous"):
            metadata.add(_Atom("dangerous-index", str(index)))
        if _contains_kind(value, "builtins"):
            metadata.add(_Atom("builtins-index", str(index)))

    return frozenset(metadata)


class _R31OrderedBindingScanner(_r30._R30OrderedPerItemIterationScanner):
    def _is_sensitive_value(self, value: _Value) -> bool:
        return (
            super()._is_sensitive_value(value)
            or _contains_kind(value, "dangerous-index")
            or _contains_kind(value, "builtins-index")
        )

    def _scan_reachable_target_execution(
        self,
        target: ast.AST,
        value: _Value,
        environment: dict[str, _Value],
    ) -> bool | None:
        if isinstance(target, (ast.Attribute, ast.Subscript)):
            self._scan_assignment_target_execution(target, environment)
            if self._is_sensitive_value(value):
                self._mark_binding(target.lineno)
            return True

        return super()._scan_reachable_target_execution(
            target,
            value,
            environment,
        )

    def _assign_iterated_target(
        self,
        target: ast.AST,
        value: _Value,
        environment: dict[str, _Value],
    ) -> None:
        if not isinstance(target, (ast.Tuple, ast.List)):
            super()._assign_iterated_target(target, value, environment)
            return

        length = _sequence_length(value)
        starred = [
            index
            for index, element in enumerate(target.elts)
            if isinstance(element, ast.Starred)
        ]
        if length is None or len(starred) != 1:
            super()._assign_iterated_target(target, value, environment)
            return

        starred_index = starred[0]
        fixed_count = len(target.elts) - 1
        if length < fixed_count:
            super()._assign_iterated_target(target, value, environment)
            return

        for index, element in enumerate(target.elts[:starred_index]):
            matched, selected = _selected_slots(value, _integer_value(index))
            self._assign_iterated_target(
                element,
                selected if matched else _UNKNOWN,
                environment,
            )

        trailing = len(target.elts) - starred_index - 1
        star_values: list[_Value] = []
        for index in range(starred_index, length - trailing):
            matched, selected = _selected_slots(value, _integer_value(index))
            star_values.append(selected if matched else _UNKNOWN)

        starred_target = target.elts[starred_index]
        assert isinstance(starred_target, ast.Starred)
        self._assign_iterated_target(
            starred_target.value,
            _r31_sequence_value(tuple(star_values)),
            environment,
        )

        for offset, element in enumerate(
            target.elts[starred_index + 1 :],
            start=1,
        ):
            source_index = length - trailing + offset - 1
            matched, selected = _selected_slots(
                value,
                _integer_value(source_index),
            )
            self._assign_iterated_target(
                element,
                selected if matched else _UNKNOWN,
                environment,
            )


def _r31_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R31OrderedBindingScanner().scan(source)


def test_r31_prior_sensitive_starred_subscript_binding_survives_nested_failure() -> None:
    source = """\
bucket = {}
for *bucket["items"], (fn, safe) in ((eval, (1,)),):
    pass
"""

    assert _r31_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r31_comprehension_sensitive_binding_survives_later_nested_failure() -> None:
    source = """\
bucket = {}
values = [None for *bucket["items"], (fn, safe) in ((eval, (1,)),)]
"""

    assert _r31_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r31_starred_name_sequence_is_not_directly_callable_dangerous() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    fns("1+1")
"""

    assert _r31_dynamic_execution_markers_from_source(source) == ()


def test_r31_starred_name_sequence_selection_preserves_dangerous_element() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    fns[0]("1+1")
"""

    assert _r31_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r31_starred_name_sequence_iteration_preserves_dangerous_element() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    for fn in fns:
        fn("1+1")
"""

    assert _r31_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r31_sensitive_starred_subscript_still_fails_closed() -> None:
    source = """\
bucket = {}
for *bucket["items"], tail in ((eval, len),):
    pass
"""

    assert _r31_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r31_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r31_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
