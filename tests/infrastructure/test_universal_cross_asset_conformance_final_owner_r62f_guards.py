from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r62e_guards as _r62e
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _owner_paths,
    _static_strings,
    _Value,
)

_R62F_NAMESPACE_HELPERS = frozenset({"globals", "locals", "vars"})


def _r62f_selected_mapping(
    *,
    semantic_atoms: set[_Atom],
    slots: dict[str, _Atom],
) -> _Value:
    atoms = set(semantic_atoms)
    atoms.add(_Atom("container-kind", "mapping"))
    atoms.update(
        _r15._selected_slot_atom(f"s:{name}", value)
        for name, value in slots.items()
    )
    return frozenset(atoms)


_R62F_MODULE_NAMESPACE: _Value = _r62f_selected_mapping(
    semantic_atoms={_Atom(_r62e._R62E_MODULE_NAMESPACE_KIND)},
    slots={
        "__builtins__": _Atom("builtins"),
        "builtins": _Atom("builtins"),
    },
)

_R62F_BUILTINS_MAPPING: _Value = _r62f_selected_mapping(
    semantic_atoms={_Atom("builtins")},
    slots={
        "__import__": _Atom("dangerous"),
        "eval": _Atom("dangerous"),
        "exec": _Atom("dangerous"),
        "getattr": _Atom("helper", "getattr"),
        "globals": _Atom("helper", "globals"),
        "locals": _Atom("helper", "locals"),
        "vars": _Atom("helper", "vars"),
    },
)


class _R62FDirectRetainedNamespaceEgressScanner(
    _r62e._R62ERetainedNamespaceDefaultScanner
):
    """Preserve bounded namespace slots until direct execution is visible.

    R62E made zero-argument ``globals``/``locals``/``vars`` results sensitive
    when stored as callable defaults. The same abstract namespace can also flow
    directly into a static ``["builtins"]`` selection. Model that selected slot
    explicitly so inherited R15 mapping selection and R12 dangerous-call logic
    remain authoritative.

    The builtins mapping likewise exposes the bounded namespace-producing helper
    identities. Enrich only ``builtins.__dict__``, ``vars(builtins)``, and their
    exact getattr/attrgetter equivalents with selected slots. No arbitrary
    mapping, return-value, or runtime execution interpretation is introduced.
    """

    def _scan_import_from(
        self,
        node: ast.ImportFrom,
        environment: dict[str, _Value],
    ) -> None:
        super()._scan_import_from(node, environment)
        if node.level != 0 or node.module != "builtins":
            return

        for alias in node.names:
            local_name = alias.asname or alias.name
            if alias.name in _R62F_NAMESPACE_HELPERS:
                environment[local_name] = _r62e._r62e_helper_value(alias.name)
            elif alias.name == "__dict__":
                environment[local_name] = _R62F_BUILTINS_MAPPING

    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        if node.attr == "__dict__" and isinstance(node.value, ast.Name):
            base = environment.get(
                node.value.id,
                _r12._IMPLICIT_BINDINGS.get(node.value.id, _UNKNOWN),
            )
            if _contains_kind(base, "builtins"):
                return _R62F_BUILTINS_MAPPING
        return super()._evaluate_attribute(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text in _R62F_NAMESPACE_HELPERS
            and not arguments
        ):
            return _R62F_MODULE_NAMESPACE

        if (
            helper.kind == "helper"
            and helper.text == "vars"
            and arguments
            and _contains_kind(arguments[0], "builtins")
        ):
            return _R62F_BUILTINS_MAPPING

        if (
            helper.kind == "helper"
            and helper.text == "getattr"
            and len(arguments) >= 2
            and _contains_kind(arguments[0], "builtins")
            and "__dict__" in _static_strings(arguments[1])
        ):
            return _R62F_BUILTINS_MAPPING

        if (
            helper.kind == "attrgetter"
            and helper.text == "__dict__"
            and arguments
            and _contains_kind(arguments[0], "builtins")
        ):
            return _R62F_BUILTINS_MAPPING

        return super()._evaluate_special_call(helper, arguments)


def _r62f_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62FDirectRetainedNamespaceEgressScanner().scan(source)


def _r62f_runtime_result(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(source, namespace)
    return namespace["result"]


def test_r62f_predecessor_reproduces_direct_namespace_false_negatives() -> None:
    sources = (
        "import builtins\nresult = globals()[\"builtins\"].eval(\"1+1\")\n",
        "import builtins\nresult = locals()[\"builtins\"].eval(\"1+1\")\n",
        "import builtins\nresult = vars()[\"builtins\"].eval(\"1+1\")\n",
        "result = globals()[\"__builtins__\"][\"eval\"](\"1+1\")\n",
        (
            "import builtins\n"
            "result = builtins.__dict__[\"globals\"]()[\"builtins\"]"
            ".eval(\"1+1\")\n"
        ),
        (
            "import builtins\n"
            "result = vars(builtins)[\"globals\"]()[\"builtins\"]"
            ".eval(\"1+1\")\n"
        ),
        (
            "import builtins\n"
            "result = getattr(builtins, \"globals\")()[\"builtins\"]"
            ".eval(\"1+1\")\n"
        ),
    )

    for source in sources:
        assert _r62f_runtime_result(source) == 2
        assert _r62e._r62e_dynamic_execution_markers_from_source(source) == ()


def test_r62f_direct_namespace_helpers_fail_closed() -> None:
    sources = (
        "import builtins\nresult = globals()[\"builtins\"].eval(\"1+1\")\n",
        "import builtins\nresult = locals()[\"builtins\"].exec(\"result = 2\")\n",
        "import builtins\nresult = vars()[\"builtins\"].eval(\"1+1\")\n",
        "result = globals()[\"__builtins__\"][\"eval\"](\"1+1\")\n",
    )

    assert _r62f_runtime_result(sources[0]) == 2
    assert _r62f_runtime_result(sources[1]) is None
    assert _r62f_runtime_result(sources[2]) == 2
    assert _r62f_runtime_result(sources[3]) == 2
    for source in sources:
        expected_line = 1 if source.startswith("result =") else 2
        assert _r62f_dynamic_execution_markers_from_source(source) == (
            f"call:{expected_line}",
        )


def test_r62f_builtins_mapping_namespace_helper_derivations_fail_closed() -> None:
    sources = (
        (
            "import builtins\n"
            "result = builtins.__dict__[\"globals\"]()[\"builtins\"]"
            ".eval(\"1+1\")\n"
        ),
        (
            "import builtins\n"
            "result = builtins.__dict__.get(\"globals\")()[\"builtins\"]"
            ".eval(\"1+1\")\n"
        ),
        (
            "import builtins\n"
            "result = builtins.__dict__.__getitem__(\"globals\")()"
            "[\"builtins\"].eval(\"1+1\")\n"
        ),
        (
            "import builtins\n"
            "result = vars(builtins)[\"globals\"]()[\"builtins\"]"
            ".eval(\"1+1\")\n"
        ),
        (
            "import builtins\n"
            "result = getattr(builtins, \"globals\")()[\"builtins\"]"
            ".eval(\"1+1\")\n"
        ),
    )

    for source in sources:
        assert _r62f_runtime_result(source) == 2
        assert _r62f_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62f_imported_namespace_helper_and_mapping_aliases_fail_closed() -> None:
    imported_helper = (
        "from builtins import globals as current_globals\n"
        "import builtins\n"
        "result = current_globals()[\"builtins\"].eval(\"1+1\")\n"
    )
    imported_mapping = (
        "from builtins import __dict__ as namespace\n"
        "result = namespace[\"globals\"]()[\"__builtins__\"]"
        "[\"eval\"](\"1+1\")\n"
    )

    assert _r62f_runtime_result(imported_helper) == 2
    assert _r62f_runtime_result(imported_mapping) == 2
    assert _r62f_dynamic_execution_markers_from_source(imported_helper) == (
        "call:3",
    )
    assert _r62f_dynamic_execution_markers_from_source(imported_mapping) == (
        "call:2",
    )


def test_r62f_operator_builtins_mapping_derivations_fail_closed() -> None:
    source = """\
import builtins
import operator
result = operator.getitem(builtins.__dict__, "globals")()["builtins"].eval("1+1")
"""

    assert _r62f_runtime_result(source) == 2
    assert _r62f_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r62f_safe_namespace_selections_stay_clean() -> None:
    sources = (
        "import builtins\nresult = globals().get(\"missing\")\n",
        "import builtins\nresult = locals().get(\"missing\")\n",
        "import builtins\nresult = vars().get(\"missing\")\n",
        "import builtins\nresult = builtins.__dict__.get(\"len\")\n",
    )

    for source in sources:
        _r62f_runtime_result(source)
        assert _r62f_dynamic_execution_markers_from_source(source) == ()


def test_r62f_shadowed_namespace_helpers_stay_clean() -> None:
    source = """\
def globals():
    return {"builtins": object()}
def locals():
    return {"builtins": object()}
def vars():
    return {"builtins": object()}
result = (globals(), locals(), vars())
"""

    result = _r62f_runtime_result(source)
    assert isinstance(result, tuple)
    assert _r62f_dynamic_execution_markers_from_source(source) == ()


def test_r62f_vars_with_explicit_safe_argument_stays_clean() -> None:
    source = """\
class Safe:
    pass
safe = Safe()
result = vars(safe)
"""

    assert _r62f_runtime_result(source) == {}
    assert _r62f_dynamic_execution_markers_from_source(source) == ()


def test_r62f_r62e_default_regressions_remain_authoritative() -> None:
    namespace_default = """\
import builtins
def hold(namespace=globals()):
    return None
result = hold.__defaults__[0]["builtins"].eval("1+1")
"""
    helper_default = """\
def hold(candidate=globals):
    return None
namespace = hold.__defaults__[0]()
result = namespace["__builtins__"]["eval"]("1+1")
"""
    safe_default = (
        "def hold(candidate=len):\n"
        "    return None\n"
        "result = hold.__defaults__[0](\"abc\")\n"
    )

    assert _r62f_runtime_result(namespace_default) == 2
    assert _r62f_runtime_result(helper_default) == 2
    assert _r62f_runtime_result(safe_default) == 3
    assert _r62f_dynamic_execution_markers_from_source(namespace_default) == (
        "binding:2",
    )
    assert _r62f_dynamic_execution_markers_from_source(helper_default) == (
        "binding:1",
    )
    assert _r62f_dynamic_execution_markers_from_source(safe_default) == ()


def test_r62f_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62f_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
