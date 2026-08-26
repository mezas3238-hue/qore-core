from __future__ import annotations

import ast
import importlib.util
from dataclasses import dataclass
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).parents[2]
_INFRASTRUCTURE_ROOT = _REPOSITORY_ROOT / "src" / "qore" / "infrastructure"
_FULL_CLOSURE_ORACLE_PATH = Path(__file__).with_name(
    "test_universal_cross_asset_conformance_full_closure.py"
)

_LEGACY_OWNER_STEMS = {
    "fixed_income_economics",
    "rate_term_structure",
    "universal_instrument_identity",
    "universal_instrument_identity_graph",
    "universal_market_topology",
    "universal_valuation_observation",
}
_NON_D04_QUALIFICATION_STEMS = {"dataset_integrity_qualification"}
_DYNAMIC_EXECUTION_CALL_NAMES = {"__import__", "eval", "exec"}
_GENERIC_AUTHORITY_MODULE_NAMES = {
    "qore.infrastructure.derivative_contract_semantics",
    "qore.infrastructure.product_composition_semantics",
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.universal_valuation_observation",
}
_PRODUCT_QUALIFICATION_MODULE_NAMES = {
    "qore.infrastructure.cfd_contract_qualification",
    "qore.infrastructure.rainbow_option_composition_semantics",
    "qore.infrastructure.uit_contract_qualification",
    "qore.infrastructure.warrant_convertible_qualification_semantics",
}
_FORBIDDEN_DIRECTIONAL_IMPORTS = {
    "qore.infrastructure.insurance_linked_risk_transfer_semantics": {
        "qore.infrastructure.event_contract_semantics",
    },
    "qore.infrastructure.event_contract_semantics": {
        "qore.infrastructure.insurance_linked_risk_transfer_semantics",
    },
    "qore.infrastructure.shariah_cross_family_semantics": {
        "qore.infrastructure.sukuk_structural_semantics",
    },
    "qore.infrastructure.sukuk_structural_semantics": {
        "qore.infrastructure.shariah_cross_family_semantics",
    },
    "qore.infrastructure.supply_chain_finance_semantics": {
        "qore.infrastructure.advanced_payable_scf_semantics",
    },
}


def _owner_paths() -> tuple[Path, ...]:
    discovered = set(_INFRASTRUCTURE_ROOT.glob("*_semantics.py"))
    discovered.update(
        path
        for path in _INFRASTRUCTURE_ROOT.glob("*_qualification.py")
        if path.stem not in _NON_D04_QUALIFICATION_STEMS
    )
    discovered.update(
        _INFRASTRUCTURE_ROOT / f"{stem}.py" for stem in _LEGACY_OWNER_STEMS
    )
    return tuple(sorted(discovered))


def _owner_path(module_name: str) -> Path:
    return _INFRASTRUCTURE_ROOT / f"{module_name.rsplit('.', 1)[-1]}.py"


def _resolved_imported_modules_from_source(
    source: str,
    *,
    package: str,
) -> tuple[str, ...]:
    tree = ast.parse(source)
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue

        imported_module: str | None
        if node.level > 0:
            relative_name = "." * node.level + (node.module or "")
            imported_module = importlib.util.resolve_name(relative_name, package)
        else:
            imported_module = node.module
        if imported_module is None:
            continue

        imports.append(imported_module)
        if node.module is None or imported_module == "qore.infrastructure":
            imports.extend(
                f"{imported_module}.{alias.name}"
                for alias in node.names
                if alias.name != "*"
            )

    return tuple(imports)


@dataclass(frozen=True, slots=True)
class _Atom:
    kind: str
    text: str | None = None


type _Value = frozenset[_Atom]
_UNKNOWN: _Value = frozenset({_Atom("unknown")})
_BUILTINS_NAMESPACE: _Value = frozenset({_Atom("builtins")})
_DANGEROUS_CALLABLE: _Value = frozenset({_Atom("dangerous")})
_OPERATOR_MODULE: _Value = frozenset({_Atom("operator")})
_GETATTR_HELPER: _Value = frozenset({_Atom("helper", "getattr")})
_VARS_HELPER: _Value = frozenset({_Atom("helper", "vars")})

_IMPLICIT_BINDINGS: dict[str, _Value] = {
    "builtins": _BUILTINS_NAMESPACE,
    "__builtins__": _BUILTINS_NAMESPACE,
    "eval": _DANGEROUS_CALLABLE,
    "exec": _DANGEROUS_CALLABLE,
    "__import__": _DANGEROUS_CALLABLE,
    "getattr": _GETATTR_HELPER,
    "vars": _VARS_HELPER,
}


def _single(kind: str, text: str | None = None) -> _Value:
    return frozenset({_Atom(kind, text)})


def _string_value(value: str) -> _Value:
    return _single("string", value)


def _merge_values(*values: _Value) -> _Value:
    merged: set[_Atom] = set()
    for value in values:
        merged.update(value)
    return frozenset(merged) if merged else _UNKNOWN


def _contains_kind(value: _Value, kind: str, text: str | None = None) -> bool:
    return any(
        atom.kind == kind and (text is None or atom.text == text)
        for atom in value
    )


def _static_strings(value: _Value) -> set[str]:
    return {
        atom.text
        for atom in value
        if atom.kind == "string" and atom.text is not None
    }


def _target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_target_names(element))
        return names
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return set()


class _LocalBindingCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.names.add(alias.asname or alias.name.split(".", 1)[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                self.names.add(alias.asname or alias.name)


def _function_local_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    collector = _LocalBindingCollector()
    for argument in (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ):
        collector.names.add(argument.arg)
    if node.args.vararg is not None:
        collector.names.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        collector.names.add(node.args.kwarg.arg)
    for statement in node.body:
        collector.visit(statement)
    return collector.names


class _DynamicExecutionScanner:
    def __init__(self) -> None:
        self._markers: list[str] = []

    def scan(self, source: str) -> tuple[str, ...]:
        tree = ast.parse(source)
        environment = dict(_IMPLICIT_BINDINGS)
        self._scan_block(tree.body, environment)
        return tuple(dict.fromkeys(self._markers))

    def _mark_call(self, line_number: int) -> None:
        self._markers.append(f"call:{line_number}")

    def _mark_binding(self, line_number: int) -> None:
        self._markers.append(f"binding:{line_number}")

    def _is_sensitive_value(self, value: _Value) -> bool:
        return _contains_kind(value, "dangerous") or _contains_kind(
            value,
            "builtins",
        )

    def _assign_target(
        self,
        target: ast.AST,
        value: _Value,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(target, ast.Name):
            environment[target.id] = value
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._assign_target(element, value, environment)
            return
        if isinstance(target, ast.Starred):
            self._assign_target(target.value, value, environment)

    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        base = self._scan_expression(node.value, environment)
        result: set[_Atom] = set()

        for atom in base:
            if atom.kind == "builtins":
                if node.attr == "__dict__":
                    result.add(_Atom("builtins"))
                elif node.attr in _DYNAMIC_EXECUTION_CALL_NAMES:
                    result.add(_Atom("dangerous"))
                else:
                    result.add(_Atom("unknown"))
            elif atom.kind == "dangerous" and node.attr == "__call__":
                result.add(_Atom("dangerous"))
            elif atom.kind == "operator" and node.attr in {
                "getitem",
                "itemgetter",
                "attrgetter",
            }:
                result.add(_Atom("helper", node.attr))
            else:
                result.add(_Atom("unknown"))

        return frozenset(result) if result else _UNKNOWN

    def _evaluate_subscript(
        self,
        node: ast.Subscript,
        environment: dict[str, _Value],
    ) -> _Value:
        base = self._scan_expression(node.value, environment)
        key = self._scan_expression(node.slice, environment)
        result: set[_Atom] = set()

        if _contains_kind(base, "dangerous"):
            result.add(_Atom("dangerous"))
        if _contains_kind(base, "builtins"):
            for key_value in _static_strings(key):
                if key_value in _DYNAMIC_EXECUTION_CALL_NAMES:
                    result.add(_Atom("dangerous"))
                else:
                    result.add(_Atom("unknown"))
        if not result:
            result.add(_Atom("unknown"))
        return frozenset(result)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        result: set[_Atom] = set()

        if (
            helper.kind == "helper"
            and helper.text == "getattr"
            and len(arguments) >= 2
        ):
            target, attribute = arguments[0], arguments[1]
            attributes = _static_strings(attribute)
            if _contains_kind(target, "builtins"):
                for attribute_name in attributes:
                    if attribute_name == "__dict__":
                        result.add(_Atom("builtins"))
                    elif attribute_name in _DYNAMIC_EXECUTION_CALL_NAMES:
                        result.add(_Atom("dangerous"))
                    else:
                        result.add(_Atom("unknown"))
            if (
                _contains_kind(target, "dangerous")
                and "__call__" in attributes
            ):
                result.add(_Atom("dangerous"))

        elif helper.kind == "helper" and helper.text == "vars" and arguments:
            if _contains_kind(arguments[0], "builtins"):
                result.add(_Atom("builtins"))

        elif (
            helper.kind == "helper"
            and helper.text == "getitem"
            and len(arguments) >= 2
        ):
            if _contains_kind(arguments[0], "builtins"):
                for key in _static_strings(arguments[1]):
                    if key in _DYNAMIC_EXECUTION_CALL_NAMES:
                        result.add(_Atom("dangerous"))
                    else:
                        result.add(_Atom("unknown"))

        elif (
            helper.kind == "helper"
            and helper.text in {"itemgetter", "attrgetter"}
            and arguments
        ):
            for key in _static_strings(arguments[0]):
                result.add(_Atom(helper.text, key))

        elif helper.kind == "itemgetter" and arguments:
            if _contains_kind(arguments[0], "builtins"):
                if helper.text in _DYNAMIC_EXECUTION_CALL_NAMES:
                    result.add(_Atom("dangerous"))
                else:
                    result.add(_Atom("unknown"))

        elif helper.kind == "attrgetter" and arguments:
            if _contains_kind(arguments[0], "builtins"):
                if helper.text in _DYNAMIC_EXECUTION_CALL_NAMES:
                    result.add(_Atom("dangerous"))
                elif helper.text == "__dict__":
                    result.add(_Atom("builtins"))
                else:
                    result.add(_Atom("unknown"))

        return frozenset(result) if result else _UNKNOWN

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
            arguments = [
                self._scan_expression(argument, environment)
                for argument in node.args
            ]
            for keyword in node.keywords:
                self._scan_expression(keyword.value, environment)
            if _contains_kind(receiver, "builtins"):
                for key in _static_strings(arguments[0]):
                    if key in _DYNAMIC_EXECUTION_CALL_NAMES:
                        return _DANGEROUS_CALLABLE
            return _UNKNOWN

        function = self._scan_expression(node.func, environment)
        arguments = [
            self._scan_expression(argument, environment)
            for argument in node.args
        ]
        for keyword in node.keywords:
            self._scan_expression(keyword.value, environment)

        if _contains_kind(function, "dangerous"):
            self._mark_call(node.lineno)

        results: list[_Value] = []
        for helper in function:
            if helper.kind in {
                "helper",
                "itemgetter",
                "attrgetter",
            }:
                results.append(
                    self._evaluate_special_call(helper, arguments)
                )
            else:
                results.append(_UNKNOWN)
        return _merge_values(*results)

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Name):
            return environment.get(
                node.id,
                _IMPLICIT_BINDINGS.get(node.id, _UNKNOWN),
            )
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return _string_value(node.value)
            return _UNKNOWN
        if isinstance(node, ast.Attribute):
            return self._evaluate_attribute(node, environment)
        if isinstance(node, ast.Subscript):
            return self._evaluate_subscript(node, environment)
        if isinstance(node, ast.Call):
            return self._evaluate_call(node, environment)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._scan_expression(node.left, environment)
            right = self._scan_expression(node.right, environment)
            combinations = {
                _Atom("string", left_value + right_value)
                for left_value in _static_strings(left)
                for right_value in _static_strings(right)
            }
            return frozenset(combinations) if combinations else _UNKNOWN
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return _merge_values(
                *(
                    self._scan_expression(element, environment)
                    for element in node.elts
                )
            )
        if isinstance(node, ast.Dict):
            values = [
                self._scan_expression(value, environment)
                for value in node.values
            ]
            values.extend(
                self._scan_expression(key, environment)
                for key in node.keys
                if key is not None
            )
            return _merge_values(*values)
        if isinstance(node, ast.Starred):
            return self._scan_expression(node.value, environment)
        if isinstance(node, ast.IfExp):
            self._scan_expression(node.test, environment)
            return _merge_values(
                self._scan_expression(node.body, environment),
                self._scan_expression(node.orelse, environment),
            )
        if isinstance(node, ast.BoolOp):
            return _merge_values(
                *(
                    self._scan_expression(value, environment)
                    for value in node.values
                )
            )
        if isinstance(node, ast.NamedExpr):
            value = self._scan_expression(node.value, environment)
            if self._is_sensitive_value(value):
                self._mark_binding(node.lineno)
            self._assign_target(node.target, value, environment)
            return value
        if isinstance(node, ast.Lambda):
            child_environment = environment.copy()
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            ):
                child_environment[argument.arg] = _UNKNOWN
            if node.args.vararg is not None:
                child_environment[node.args.vararg.arg] = _UNKNOWN
            if node.args.kwarg is not None:
                child_environment[node.args.kwarg.arg] = _UNKNOWN
            self._scan_expression(node.body, child_environment)
            return _UNKNOWN

        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self._scan_expression(child, environment)
        return _UNKNOWN

    def _scan_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        for decorator in node.decorator_list:
            self._scan_expression(decorator, environment)
        for default in node.args.defaults:
            self._scan_expression(default, environment)
        for default in node.args.kw_defaults:
            if default is not None:
                self._scan_expression(default, environment)

        child_environment = environment.copy()
        for name in _function_local_names(node):
            child_environment[name] = _UNKNOWN
        self._scan_block(node.body, child_environment)
        environment[node.name] = _UNKNOWN

    def _scan_import(
        self,
        node: ast.Import,
        environment: dict[str, _Value],
    ) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".", 1)[0]
            if alias.name == "builtins":
                environment[local_name] = _BUILTINS_NAMESPACE
            elif alias.name == "operator":
                environment[local_name] = _OPERATOR_MODULE
            else:
                environment[local_name] = _UNKNOWN

    def _scan_import_from(
        self,
        node: ast.ImportFrom,
        environment: dict[str, _Value],
    ) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname or alias.name
            if node.module == "builtins":
                if alias.name == "__dict__":
                    environment[local_name] = _BUILTINS_NAMESPACE
                elif alias.name in _DYNAMIC_EXECUTION_CALL_NAMES:
                    environment[local_name] = _DANGEROUS_CALLABLE
                elif alias.name == "getattr":
                    environment[local_name] = _GETATTR_HELPER
                elif alias.name == "vars":
                    environment[local_name] = _VARS_HELPER
                else:
                    environment[local_name] = _UNKNOWN
            elif node.module == "operator" and alias.name in {
                "getitem",
                "itemgetter",
                "attrgetter",
            }:
                environment[local_name] = _single("helper", alias.name)
            else:
                environment[local_name] = _UNKNOWN

    def _merge_environments(
        self,
        environment: dict[str, _Value],
        *branches: dict[str, _Value],
    ) -> None:
        names = set(environment)
        for branch in branches:
            names.update(branch)
        for name in names:
            environment[name] = _merge_values(
                *(branch.get(name, _UNKNOWN) for branch in branches)
            )

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._scan_function(node, environment)
            return
        if isinstance(node, ast.ClassDef):
            for decorator in node.decorator_list:
                self._scan_expression(decorator, environment)
            child_environment = environment.copy()
            self._scan_block(node.body, child_environment)
            environment[node.name] = _UNKNOWN
            return
        if isinstance(node, ast.Import):
            self._scan_import(node, environment)
            return
        if isinstance(node, ast.ImportFrom):
            self._scan_import_from(node, environment)
            return
        if isinstance(node, ast.Assign):
            value = self._scan_expression(node.value, environment)
            if self._is_sensitive_value(value):
                self._mark_binding(node.lineno)
            for target in node.targets:
                self._assign_target(target, value, environment)
            return
        if isinstance(node, ast.AnnAssign):
            value = (
                self._scan_expression(node.value, environment)
                if node.value is not None
                else _UNKNOWN
            )
            if self._is_sensitive_value(value):
                self._mark_binding(node.lineno)
            self._assign_target(node.target, value, environment)
            return
        if isinstance(node, ast.AugAssign):
            current = self._scan_expression(node.target, environment)
            update = self._scan_expression(node.value, environment)
            if isinstance(node.op, ast.Add):
                combinations = {
                    _Atom("string", left + right)
                    for left in _static_strings(current)
                    for right in _static_strings(update)
                }
                value = (
                    frozenset(combinations)
                    if combinations
                    else _UNKNOWN
                )
            else:
                value = _UNKNOWN
            self._assign_target(node.target, value, environment)
            return
        if isinstance(node, ast.Expr):
            self._scan_expression(node.value, environment)
            return
        if isinstance(node, ast.Return):
            if node.value is not None:
                self._scan_expression(node.value, environment)
            return
        if isinstance(node, ast.If):
            self._scan_expression(node.test, environment)
            body_environment = environment.copy()
            else_environment = environment.copy()
            self._scan_block(node.body, body_environment)
            self._scan_block(node.orelse, else_environment)
            self._merge_environments(
                environment,
                body_environment,
                else_environment,
            )
            return
        if isinstance(node, (ast.For, ast.AsyncFor)):
            self._scan_expression(node.iter, environment)
            body_environment = environment.copy()
            self._assign_target(node.target, _UNKNOWN, body_environment)
            self._scan_block(node.body, body_environment)
            else_environment = environment.copy()
            self._scan_block(node.orelse, else_environment)
            self._merge_environments(
                environment,
                environment.copy(),
                body_environment,
                else_environment,
            )
            return
        if isinstance(node, ast.While):
            self._scan_expression(node.test, environment)
            body_environment = environment.copy()
            else_environment = environment.copy()
            self._scan_block(node.body, body_environment)
            self._scan_block(node.orelse, else_environment)
            self._merge_environments(
                environment,
                environment.copy(),
                body_environment,
                else_environment,
            )
            return
        if isinstance(node, ast.Try):
            branches: list[dict[str, _Value]] = []
            body_environment = environment.copy()
            self._scan_block(node.body, body_environment)
            branches.append(body_environment)
            for handler in node.handlers:
                handler_environment = environment.copy()
                if handler.name is not None:
                    handler_environment[handler.name] = _UNKNOWN
                self._scan_block(handler.body, handler_environment)
                branches.append(handler_environment)
            else_environment = body_environment.copy()
            self._scan_block(node.orelse, else_environment)
            branches.append(else_environment)
            final_environment = environment.copy()
            self._scan_block(node.finalbody, final_environment)
            branches.append(final_environment)
            self._merge_environments(environment, *branches)
            return
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                self._scan_expression(item.context_expr, environment)
                if item.optional_vars is not None:
                    self._assign_target(
                        item.optional_vars,
                        _UNKNOWN,
                        environment,
                    )
            self._scan_block(node.body, environment)
            return
        if isinstance(node, ast.Delete):
            for target in node.targets:
                for name in _target_names(target):
                    environment[name] = _UNKNOWN
            return

        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self._scan_expression(child, environment)

    def _scan_block(
        self,
        statements: list[ast.stmt],
        environment: dict[str, _Value],
    ) -> None:
        for statement in statements:
            self._scan_statement(statement, environment)


def _dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _DynamicExecutionScanner().scan(source)


def test_r6_composite_builtins_alias_bindings_fail_closed() -> None:
    source = """
import builtins as b
c, d = b, builtins
x = [b]
c.eval("1+1")
d.exec("1+1")
x[0].eval("1+1")
"""

    markers = _dynamic_execution_markers_from_source(source)

    assert "binding:3" in markers
    assert "binding:4" in markers


def test_r6_subscript_extraction_of_dangerous_callable_fails_closed() -> None:
    source = """
x = [eval][0]
x("1+1")
"""

    markers = _dynamic_execution_markers_from_source(source)

    assert "binding:2" in markers


def test_r6_callable_attribute_execution_fails_closed() -> None:
    source = """
eval.__call__("1+1")
exec.__call__("pass")
__import__.__call__("math")
getattr(eval, "__call__")("2+2")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (2, 3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r8_nested_getattr_builtins_dict_execution_fails_closed() -> None:
    source = """
import builtins as b
getattr(getattr(b, "__dict__"), "eval")("1+1")
getattr(getattr(b, "__dict__"), "exec")("pass")
getattr(getattr(b, "__dict__"), "__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r9_vars_builtins_namespace_lookup_fails_closed() -> None:
    source = """
import builtins as b
vars(b)["eval"]("1+1")
vars(b)["exec"]("pass")
vars(b)["__import__"]("math")
getattr(vars(b), "eval")("2+2")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 5, 6):
        assert f"call:{line_number}" in markers


def test_r9_builtins_mapping_lookup_methods_fail_closed() -> None:
    source = """
import builtins as b
b.__dict__.get("eval")("1+1")
vars(b).get("exec")("pass")
b.__dict__.__getitem__("__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r9_safe_vars_and_mapping_lookups_do_not_false_positive() -> None:
    source = """
class Safe:
    eval = staticmethod(lambda value: value)

safe = {"eval": lambda value: value}
safe["eval"]("x")
safe.get("eval")("x")
vars(Safe)["eval"]("x")
"""

    assert _dynamic_execution_markers_from_source(source) == ()


def test_r10_imported_builtins_dict_namespace_fails_closed() -> None:
    source = """
from builtins import __dict__ as namespace
namespace["eval"]("1+1")
namespace.get("exec")("pass")
namespace.__getitem__("__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r10_constant_string_lookup_aliases_fail_closed() -> None:
    source = """
import builtins

dict_name = "__" + "dict__"
eval_key = "ev" + "al"
exec_key = "exec"
import_key = "__import__"
forwarded_key = eval_key
getattr(builtins, forwarded_key)("1+1")
getattr(builtins, dict_name)[exec_key]("pass")
builtins.__dict__.get(import_key)("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (9, 10, 11):
        assert f"call:{line_number}" in markers


def test_r10_operator_getitem_aliases_fail_closed() -> None:
    source = """
import builtins
import operator
import operator as op
from operator import getitem as lookup
operator.getitem(builtins.__dict__, "eval")("1+1")
op.getitem(vars(builtins), "exec")("pass")
lookup(builtins.__dict__, "__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (6, 7, 8):
        assert f"call:{line_number}" in markers


def test_r10_safe_constant_and_operator_lookups_do_not_false_positive() -> None:
    source = """
import operator

key = "eval"
safe = {"eval": lambda value: value}
safe[key]("x")
safe.get(key)("x")
operator.getitem(safe, key)("x")
"""

    assert _dynamic_execution_markers_from_source(source) == ()


def test_r11_operator_accessors_and_aliases_fail_closed() -> None:
    source = """
import builtins
import operator
from operator import attrgetter as attrs
from operator import itemgetter as items

item_lookup = operator.itemgetter
attr_lookup = attrs
item_lookup("eval")(builtins.__dict__)("1+1")
items("exec")(vars(builtins))("pass")
attr_lookup("__import__")(builtins)("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (9, 10, 11):
        assert f"call:{line_number}" in markers


def test_r11_helper_aliases_and_rewrites_fail_closed() -> None:
    source = """
import builtins
import operator
from builtins import getattr as get_attr
from builtins import vars as namespace
key = "ev"
key += "al"
get_attr(builtins, key)("1+1")
key = "exec"
get_attr(builtins, key)("pass")
lookup = operator.getitem
lookup(namespace(builtins), "__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (8, 10, 12):
        assert f"call:{line_number}" in markers


def test_r11_lexical_shadowing_does_not_false_positive() -> None:
    source = """
class Safe:
    @staticmethod
    def eval(value):
        return value

def imports_only():
    import builtins as b
    from builtins import eval as evaluator
    import operator as op
    return b, evaluator, op

def uses_safe_values(b, evaluator, op):
    safe = {"eval": lambda value: value}
    b.eval("x")
    evaluator("x")
    op.getitem(safe, "eval")("x")
"""

    assert _dynamic_execution_markers_from_source(source) == ()


def test_r6_absolute_package_from_import_expands_for_directionality() -> None:
    source = (
        "from qore.infrastructure import "
        "rainbow_option_composition_semantics\n"
    )
    imported = set(
        _resolved_imported_modules_from_source(
            source,
            package="qore.infrastructure",
        )
    )

    assert "qore.infrastructure.rainbow_option_composition_semantics" in imported


def test_r6_owner_and_oracle_reject_dynamic_execution_extraction_shapes() -> None:
    violations: dict[str, tuple[str, ...]] = {}

    for path in _owner_paths():
        markers = _dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        )
        if markers:
            violations[str(path)] = markers

    oracle_markers = _dynamic_execution_markers_from_source(
        _FULL_CLOSURE_ORACLE_PATH.read_text(encoding="utf-8")
    )
    if oracle_markers:
        violations[str(_FULL_CLOSURE_ORACLE_PATH)] = oracle_markers

    assert violations == {}


def test_r6_directionality_uses_expanded_absolute_and_relative_imports() -> None:
    violations: list[tuple[str, str]] = []

    for module_name in sorted(_GENERIC_AUTHORITY_MODULE_NAMES):
        imported_modules = _resolved_imported_modules_from_source(
            _owner_path(module_name).read_text(encoding="utf-8"),
            package="qore.infrastructure",
        )
        for imported in imported_modules:
            if imported in _PRODUCT_QUALIFICATION_MODULE_NAMES:
                violations.append((module_name, imported))

    for module_name, forbidden_imports in sorted(
        _FORBIDDEN_DIRECTIONAL_IMPORTS.items()
    ):
        imported_modules = _resolved_imported_modules_from_source(
            _owner_path(module_name).read_text(encoding="utf-8"),
            package="qore.infrastructure",
        )
        for imported in imported_modules:
            if imported in forbidden_imports:
                violations.append((module_name, imported))

    assert violations == []
