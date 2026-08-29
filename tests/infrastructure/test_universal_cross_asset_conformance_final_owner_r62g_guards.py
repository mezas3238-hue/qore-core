from __future__ import annotations

import ast
from collections.abc import Iterable

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r62e_guards as _r62e
import test_universal_cross_asset_conformance_final_owner_r62f_guards as _r62f
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _Value,
)

_R62G_BUILTINS_MODULE_KIND = "r62g-builtins-module"
_R62G_BUILTINS_MODULE: _Value = frozenset(
    {_Atom("builtins"), _Atom(_R62G_BUILTINS_MODULE_KIND)}
)


def _r62g_is_builtins_module(value: _Value) -> bool:
    return _r12._contains_kind(
        value,
        _R62G_BUILTINS_MODULE_KIND,
    ) and not _r12._contains_kind(value, "container-kind", "mapping")


class _R62GScopePreservingRetainedNamespaceScanner(
    _r62f._R62FDirectRetainedNamespaceEgressScanner
):
    """Preserve R62E retention without inventing module slots in nested scopes.

    R62F correctly decorates module namespaces with bounded ``builtins`` and
    ``__builtins__`` slots so direct dynamic execution is visible. Zero-argument
    ``locals()`` and ``vars()`` do not, however, expose the module namespace from
    a function, class, generator frame, or an inlined comprehension whose
    containing scope is non-module.

    In those scopes keep R62E's retained-namespace value: it remains sensitive
    when captured as a callable default, but it carries no invented module slots.
    ``globals()`` remains module-scoped from every runtime scope, while module
    ``locals()``/``vars()`` continue to use R62F's selected-slot representation.

    The explicit ``builtins`` import is a module object, not a mapping. Preserve
    that distinction so ``builtins[... ]``/mapping-helper forms do not invent
    execution that CPython rejects before dynamic execution. ``builtins.__dict__``,
    ``vars(builtins)`` and module ``__builtins__`` remain real mappings and keep
    their fail-closed selected-slot semantics.
    """

    def _scan_import(
        self,
        node: ast.Import,
        environment: dict[str, _Value],
    ) -> None:
        super()._scan_import(node, environment)
        for alias in node.names:
            if alias.name != "builtins":
                continue
            local_name = alias.asname or alias.name.split(".", 1)[0]
            environment[local_name] = _R62G_BUILTINS_MODULE

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Name):
            value = environment.get(
                node.id,
                _r12._IMPLICIT_BINDINGS.get(node.id, _UNKNOWN),
            )
            if node.id == "__builtins__" and value == _r12._BUILTINS_NAMESPACE:
                return _r62f._R62F_BUILTINS_MAPPING
            if node.id == "builtins" and value == _r12._BUILTINS_NAMESPACE:
                return _UNKNOWN
        return super()._scan_expression(node, environment)

    def _evaluate_subscript(
        self,
        node: ast.Subscript,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node.value, ast.Name):
            receiver = self._scan_expression(node.value, environment)
            if _r62g_is_builtins_module(receiver):
                self._scan_expression(node.slice, environment)
                return _UNKNOWN
        return super()._evaluate_subscript(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text == "getitem"
            and arguments
            and _r62g_is_builtins_module(arguments[0])
        ):
            return _UNKNOWN
        if (
            helper.kind == "itemgetter"
            and arguments
            and _r62g_is_builtins_module(arguments[0])
        ):
            return _UNKNOWN
        if (
            helper.kind == "helper"
            and helper.text in {"locals", "vars"}
            and not arguments
            and not (
                self._r56_call_scope_stack
                and self._r56_call_scope_stack[-1]
            )
        ):
            return _r62e._R62E_RETAINED_NAMESPACE

        return super()._evaluate_special_call(helper, arguments)

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and isinstance(node.func.value, ast.Name)
        ):
            receiver = self._scan_expression(node.func.value, environment)
            if _r62g_is_builtins_module(receiver):
                for argument in node.args:
                    self._scan_expression(argument, environment)
                for keyword in node.keywords:
                    self._scan_expression(keyword.value, environment)
                return _UNKNOWN
        return super()._evaluate_call(node, environment)


def _r62g_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62GScopePreservingRetainedNamespaceScanner().scan(source)


def _r62g_runtime_key_error(source: str) -> tuple[object, ...]:
    namespace: dict[str, object] = {}
    try:
        exec(source, namespace)
    except KeyError as exc:
        return exc.args
    raise AssertionError("expected KeyError")


def _r62g_runtime_mapping_error(source: str) -> type[Exception]:
    namespace: dict[str, object] = {}
    try:
        exec(source, namespace)
    except (TypeError, AttributeError) as exc:
        return type(exc)
    raise AssertionError("expected module mapping access failure")


def _r62g_runtime_result(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(source, namespace)
    return namespace["result"]


def test_r62g_predecessor_reproduces_nested_locals_vars_false_positive() -> None:
    sources = (
        """\
def run():
    return vars()["__builtins__"].eval("1+1")
result = run()
""",
        """\
def run():
    return locals()["__builtins__"].eval("1+1")
result = run()
""",
    )

    for source in sources:
        assert _r62g_runtime_key_error(source) == ("__builtins__",)
        assert _r62f._r62f_dynamic_execution_markers_from_source(source) == (
            "call:2",
        )


def test_r62g_nested_locals_vars_do_not_invent_module_builtins() -> None:
    sources = (
        """\
def run():
    return vars()["__builtins__"].eval("1+1")
result = run()
""",
        """\
def run():
    return locals()["__builtins__"].eval("1+1")
result = run()
""",
    )

    for source in sources:
        assert _r62g_runtime_key_error(source) == ("__builtins__",)
        assert _r62g_dynamic_execution_markers_from_source(source) == ()


def test_r62g_function_comprehensions_keep_non_module_locals_vars() -> None:
    sources = (
        """\
def run():
    return [vars()["__builtins__"]["eval"]("1+1") for _ in (0,)]
result = run()
""",
        """\
def run():
    return [locals()["__builtins__"]["eval"]("1+1") for _ in (0,)]
result = run()
""",
    )

    for source in sources:
        assert _r62g_runtime_key_error(source) == ("__builtins__",)
        assert _r62g_dynamic_execution_markers_from_source(source) == ()


def test_r62g_module_locals_vars_still_expose_module_builtins() -> None:
    sources = (
        "import builtins\nresult = vars()[\"builtins\"].eval(\"1+1\")\n",
        "import builtins\nresult = locals()[\"builtins\"].eval(\"1+1\")\n",
    )

    for source in sources:
        assert _r62g_runtime_result(source) == 2
        assert _r62g_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62g_nested_globals_remains_module_scoped() -> None:
    source = """\
def run():
    return globals()["__builtins__"]["eval"]("1+1")
result = run()
"""

    assert _r62g_runtime_result(source) == 2
    assert _r62g_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62g_nested_retained_namespace_defaults_remain_fail_closed() -> None:
    sources = (
        """\
def outer():
    import builtins
    def hold(namespace=vars()):
        return None
    return hold
hold = outer()
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
        """\
def outer():
    import builtins
    def hold(namespace=locals()):
        return None
    return hold
hold = outer()
result = hold.__defaults__[0]["builtins"].eval("1+1")
""",
    )

    for source in sources:
        assert _r62g_runtime_result(source) == 2
        assert "binding:3" in _r62g_dynamic_execution_markers_from_source(source)


def test_r62g_module_comprehensions_keep_python312_module_scope() -> None:
    sources: Iterable[str] = (
        'values = [vars()["__builtins__"]["eval"]("1+1") for _ in (0,)]\nresult = values[0]\n',
        'values = [locals()["__builtins__"]["eval"]("1+1") for _ in (0,)]\nresult = values[0]\n',
    )

    for source in sources:
        assert _r62g_runtime_result(source) == 2
        assert "call:1" in _r62g_dynamic_execution_markers_from_source(source)


def test_r62g_builtins_module_mapping_operations_do_not_false_positive() -> None:
    sources = (
        'import builtins\nresult = builtins["eval"]("1+1")\n',
        'import builtins as b\nresult = b["eval"]("1+1")\n',
        'import builtins\nresult = builtins.get("eval")("1+1")\n',
        'import builtins\nresult = builtins.__getitem__("eval")("1+1")\n',
        'import builtins\nimport operator\nresult = operator.getitem(builtins, "eval")("1+1")\n',
        'import builtins\nimport operator\nresult = operator.itemgetter("eval")(builtins)("1+1")\n',
    )

    for source in sources:
        assert _r62g_runtime_mapping_error(source) in {TypeError, AttributeError}
        assert _r62g_dynamic_execution_markers_from_source(source) == ()


def test_r62g_real_builtins_mappings_remain_fail_closed() -> None:
    sources = (
        'import builtins\nresult = builtins.__dict__["eval"]("1+1")\n',
        'import builtins\nresult = vars(builtins)["eval"]("1+1")\n',
        'result = __builtins__["eval"]("1+1")\n',
        (
            'import builtins\nimport operator\n'
            'result = operator.getitem(builtins.__dict__, "eval")("1+1")\n'
        ),
        (
            'import builtins\nimport operator\n'
            'result = operator.itemgetter("eval")(builtins.__dict__)("1+1")\n'
        ),
        'import operator\nresult = operator.getitem(__builtins__, "eval")("1+1")\n',
    )

    for source in sources:
        assert _r62g_runtime_result(source) == 2
        assert _r62g_dynamic_execution_markers_from_source(source)


def test_r62g_unbound_builtins_name_does_not_false_positive() -> None:
    source = 'result = builtins["eval"]("1+1")\n'
    namespace: dict[str, object] = {}
    try:
        exec(source, namespace)
    except NameError:
        pass
    else:
        raise AssertionError("expected NameError")

    assert _r62g_dynamic_execution_markers_from_source(source) == ()


def test_r62g_r62f_and_r62e_regressions_remain_authoritative() -> None:
    direct_r62f = (
        'import builtins\nresult = globals()["builtins"].eval("1+1")\n'
    )
    retained_r62e = """\
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

    assert _r62g_runtime_result(direct_r62f) == 2
    assert _r62g_runtime_result(retained_r62e) == 2
    assert _r62g_runtime_result(safe_default) == 3
    assert _r62g_dynamic_execution_markers_from_source(direct_r62f) == ("call:2",)
    assert _r62g_dynamic_execution_markers_from_source(retained_r62e) == (
        "binding:1",
    )
    assert _r62g_dynamic_execution_markers_from_source(safe_default) == ()


def test_r62g_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62g_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path
