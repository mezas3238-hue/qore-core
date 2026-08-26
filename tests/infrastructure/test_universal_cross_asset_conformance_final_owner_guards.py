from __future__ import annotations

import ast
import importlib.util
from dataclasses import fields
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).parents[2]
_INFRASTRUCTURE_ROOT = _REPOSITORY_ROOT / "src" / "qore" / "infrastructure"
_FULL_CLOSURE_ORACLE_PATH = Path(__file__).with_name(
    "test_universal_cross_asset_conformance_full_closure.py"
)

_EXPECTED_D04_OWNER_MODULE_NAMES = {
    "qore.infrastructure.advanced_payable_scf_semantics",
    "qore.infrastructure.cash_money_market_semantics",
    "qore.infrastructure.cfd_contract_qualification",
    "qore.infrastructure.commodity_contract_delivery_semantics",
    "qore.infrastructure.crypto_perpetual_funding_semantics",
    "qore.infrastructure.crypto_staking_tokenization_semantics",
    "qore.infrastructure.derivative_contract_semantics",
    "qore.infrastructure.equity_fund_corporate_action_semantics",
    "qore.infrastructure.event_contract_semantics",
    "qore.infrastructure.fixed_income_economics",
    "qore.infrastructure.fixed_income_securitization_semantics",
    "qore.infrastructure.futures_deliverable_basket_semantics",
    "qore.infrastructure.futures_final_settlement_semantics",
    "qore.infrastructure.fx_semantics",
    "qore.infrastructure.insurance_linked_risk_transfer_semantics",
    "qore.infrastructure.loan_credit_facility_semantics",
    "qore.infrastructure.option_exotic_semantics",
    "qore.infrastructure.product_composition_semantics",
    "qore.infrastructure.rainbow_option_composition_semantics",
    "qore.infrastructure.rate_term_structure",
    "qore.infrastructure.rates_otc_semantics",
    "qore.infrastructure.securities_financing_semantics",
    "qore.infrastructure.shariah_cross_family_semantics",
    "qore.infrastructure.specialized_commodity_semantics",
    "qore.infrastructure.structured_hybrid_synthetic_semantics",
    "qore.infrastructure.structured_note_payoff_semantics",
    "qore.infrastructure.sukuk_structural_semantics",
    "qore.infrastructure.supply_chain_finance_semantics",
    "qore.infrastructure.uit_contract_qualification",
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.universal_instrument_identity_graph",
    "qore.infrastructure.universal_market_topology",
    "qore.infrastructure.universal_valuation_observation",
    "qore.infrastructure.volatility_variance_semantics",
    "qore.infrastructure.warrant_convertible_qualification_semantics",
}

_LEGACY_D04_OWNER_MODULE_NAMES = {
    "qore.infrastructure.fixed_income_economics",
    "qore.infrastructure.rate_term_structure",
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.universal_instrument_identity_graph",
    "qore.infrastructure.universal_market_topology",
    "qore.infrastructure.universal_valuation_observation",
}

_NON_D04_QUALIFICATION_MODULE_NAMES = {
    "qore.infrastructure.dataset_integrity_qualification",
}

_DYNAMIC_EXECUTION_CALL_NAMES = {
    "__import__",
    "eval",
    "exec",
}

_VENDOR_OR_RUNTIME_IMPORT_FRAGMENTS = (
    "oanda_",
    "ctrader_",
    "tradovate",
    "tradestation",
    "tastytrade",
    "ibkr_adapter",
    "provider_runtime",
    "supervised_provider_harness",
    "client_execution_agent",
    "execution_orchestration",
    "execution_boundary",
    "order_intent",
    "controlled_execution",
)

_NETWORK_IMPORT_ROOTS = {
    "aiohttp",
    "httpx",
    "requests",
    "socket",
    "urllib",
    "websockets",
}

_SFT_CURRENT_STATE_NAME_FRAGMENTS = {
    "Account",
    "Balance",
    "Current",
    "Exposure",
    "Inventory",
    "Position",
    "Risk",
    "State",
}

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

_EXPECTED_ECONOMIC_IDENTITY_FIELDS = (
    "identity_id",
    "kind",
    "family",
    "construction",
    "evidence_ref",
)


def _module_name(path: Path) -> str:
    return f"qore.infrastructure.{path.stem}"


def _owner_path(module_name: str) -> Path:
    return _INFRASTRUCTURE_ROOT / f"{module_name.rsplit('.', 1)[-1]}.py"


def _discovered_d04_owner_module_names() -> set[str]:
    semantic_names = {
        _module_name(path) for path in _INFRASTRUCTURE_ROOT.glob("*_semantics.py")
    }
    qualification_names = {
        _module_name(path) for path in _INFRASTRUCTURE_ROOT.glob("*_qualification.py")
    }
    qualification_names -= _NON_D04_QUALIFICATION_MODULE_NAMES
    return semantic_names | qualification_names | _LEGACY_D04_OWNER_MODULE_NAMES


def _assignment_target_names(target: ast.expr) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(
            name
            for element in target.elts
            for name in _assignment_target_names(element)
        )
    return ()


def _dangerous_callable_reference(
    expression: ast.expr,
    *,
    builtins_aliases: set[str],
    dangerous_direct_names: set[str],
) -> str | None:
    if isinstance(expression, ast.Name) and expression.id in dangerous_direct_names:
        return expression.id
    if (
        isinstance(expression, ast.Attribute)
        and expression.attr in _DYNAMIC_EXECUTION_CALL_NAMES
        and isinstance(expression.value, ast.Name)
        and expression.value.id in builtins_aliases
    ):
        return f"{expression.value.id}.{expression.attr}"
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "getattr"
        and len(expression.args) >= 2
    ):
        target, attribute = expression.args[0], expression.args[1]
        attribute_value = (
            attribute.value
            if isinstance(attribute, ast.Constant)
            and isinstance(attribute.value, str)
            else None
        )
        if (
            isinstance(target, ast.Name)
            and target.id in builtins_aliases
            and attribute_value in _DYNAMIC_EXECUTION_CALL_NAMES
        ):
            return f"getattr:{target.id}:{attribute_value}"
    if (
        isinstance(expression, ast.Subscript)
        and isinstance(expression.value, ast.Name)
        and expression.value.id == "__builtins__"
        and isinstance(expression.slice, ast.Constant)
        and isinstance(expression.slice.value, str)
        and expression.slice.value in _DYNAMIC_EXECUTION_CALL_NAMES
    ):
        return f"__builtins__:{expression.slice.value}"
    return None


def _dynamic_import_or_execution_markers_from_source(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    markers: list[str] = []
    builtins_aliases = {"builtins", "__builtins__"}
    importlib_aliases = {"importlib"}
    dangerous_direct_names = set(_DYNAMIC_EXECUTION_CALL_NAMES)
    import_module_names = {"import_module"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "builtins":
                    builtins_aliases.add(alias.asname or alias.name)
                if alias.name == "importlib" or alias.name.startswith("importlib."):
                    markers.append(f"import:{alias.name}")
                    if alias.name == "importlib":
                        importlib_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if module is not None and (
                module == "importlib" or module.startswith("importlib.")
            ):
                markers.append(f"from:{module}")
                for alias in node.names:
                    if alias.name == "import_module":
                        import_module_names.add(alias.asname or alias.name)
            if module == "builtins":
                for alias in node.names:
                    if alias.name in _DYNAMIC_EXECUTION_CALL_NAMES:
                        markers.append(f"from:builtins:{alias.name}")
                        dangerous_direct_names.add(alias.asname or alias.name)

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value: ast.expr | None = None
            targets: tuple[ast.expr, ...] = ()
            if isinstance(node, ast.Assign):
                value = node.value
                targets = tuple(node.targets)
            elif isinstance(node, ast.AnnAssign):
                value = node.value
                targets = (node.target,)
            elif isinstance(node, ast.NamedExpr):
                value = node.value
                targets = (node.target,)
            if value is None:
                continue
            source_marker = _dangerous_callable_reference(
                value,
                builtins_aliases=builtins_aliases,
                dangerous_direct_names=dangerous_direct_names,
            )
            if source_marker is None:
                continue
            for target in targets:
                for target_name in _assignment_target_names(target):
                    if target_name not in dangerous_direct_names:
                        dangerous_direct_names.add(target_name)
                        markers.append(f"bind:{target_name}<-{source_marker}")
                        changed = True

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name):
                if function.id in dangerous_direct_names:
                    markers.append(f"call:{function.id}")
                elif function.id in import_module_names:
                    markers.append(f"call:{function.id}")
                elif function.id == "getattr" and len(node.args) >= 2:
                    target, attribute = node.args[0], node.args[1]
                    attribute_value = (
                        attribute.value
                        if isinstance(attribute, ast.Constant)
                        and isinstance(attribute.value, str)
                        else None
                    )
                    if (
                        isinstance(target, ast.Name)
                        and target.id in builtins_aliases
                        and attribute_value in _DYNAMIC_EXECUTION_CALL_NAMES
                    ):
                        markers.append("call:getattr:" + attribute_value)
            elif isinstance(function, ast.Attribute):
                if (
                    function.attr in _DYNAMIC_EXECUTION_CALL_NAMES
                    and isinstance(function.value, ast.Name)
                    and function.value.id in builtins_aliases
                ):
                    markers.append(f"call:{function.value.id}.{function.attr}")
                elif (
                    function.attr == "import_module"
                    and isinstance(function.value, ast.Name)
                    and function.value.id in importlib_aliases
                ):
                    markers.append(f"call:{function.value.id}.import_module")
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "__builtins__"
            and isinstance(node.slice, ast.Constant)
        ):
            slice_value = node.slice.value if isinstance(node.slice.value, str) else None
            if slice_value in _DYNAMIC_EXECUTION_CALL_NAMES:
                markers.append("subscript:__builtins__:" + slice_value)

    return tuple(markers)


def _dynamic_import_or_execution_markers(path: Path) -> tuple[str, ...]:
    return _dynamic_import_or_execution_markers_from_source(
        path.read_text(encoding="utf-8")
    )


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
        elif isinstance(node, ast.ImportFrom):
            imported_module: str | None
            if node.level > 0:
                relative_name = "." * node.level + (node.module or "")
                imported_module = importlib.util.resolve_name(relative_name, package)
            else:
                imported_module = node.module
            if imported_module is None:
                continue
            imports.append(imported_module)
            if node.level > 0 and node.module is None:
                imports.extend(
                    f"{imported_module}.{alias.name}"
                    for alias in node.names
                    if alias.name != "*"
                )

    return tuple(imports)


def _resolved_owner_imports(module_name: str) -> tuple[str, ...]:
    return _resolved_imported_modules_from_source(
        _owner_path(module_name).read_text(encoding="utf-8"),
        package="qore.infrastructure",
    )


def _is_forbidden_provider_runtime_or_network_import(imported: str) -> bool:
    root = imported.split(".", 1)[0]
    return root in _NETWORK_IMPORT_ROOTS or any(
        fragment in imported for fragment in _VENDOR_OR_RUNTIME_IMPORT_FRAGMENTS
    )


def test_final_owner_discovery_is_exact_across_semantics_and_qualifications() -> None:
    live_qualification_names = {
        _module_name(path) for path in _INFRASTRUCTURE_ROOT.glob("*_qualification.py")
    }
    assert _NON_D04_QUALIFICATION_MODULE_NAMES <= live_qualification_names
    assert _discovered_d04_owner_module_names() == _EXPECTED_D04_OWNER_MODULE_NAMES


def test_final_owner_surface_forbids_dynamic_import_or_code_execution() -> None:
    violations: dict[str, tuple[str, ...]] = {}
    for module_name in sorted(_EXPECTED_D04_OWNER_MODULE_NAMES):
        path = _owner_path(module_name)
        markers = _dynamic_import_or_execution_markers(path)
        if markers:
            violations[module_name] = markers

    oracle_markers = _dynamic_import_or_execution_markers(_FULL_CLOSURE_ORACLE_PATH)
    if oracle_markers:
        violations[str(_FULL_CLOSURE_ORACLE_PATH)] = oracle_markers

    assert violations == {}


def test_dynamic_execution_scanner_closes_builtins_alias_bypasses() -> None:
    source = """
import builtins as b
from builtins import eval as evaluate
b.exec("pass")
evaluate("1 + 1")
getattr(b, "__import__")("math")
__builtins__["eval"]("2 + 2")
"""
    markers = _dynamic_import_or_execution_markers_from_source(source)

    assert "from:builtins:eval" in markers
    assert "call:b.exec" in markers
    assert "call:evaluate" in markers
    assert "call:getattr:__import__" in markers
    assert "subscript:__builtins__:eval" in markers


def test_dynamic_execution_scanner_closes_callable_rebinding_bypasses() -> None:
    source = """
import builtins as b
first = eval
second = first
third: object = b.exec
fourth = getattr(b, "__import__")
fifth = __builtins__["eval"]
first("1 + 1")
second("2 + 2")
third("pass")
fourth("math")
fifth("3 + 3")
"""
    markers = _dynamic_import_or_execution_markers_from_source(source)

    assert "bind:first<-eval" in markers
    assert "bind:second<-first" in markers
    assert "bind:third<-b.exec" in markers
    assert "bind:fourth<-getattr:b:__import__" in markers
    assert "bind:fifth<-__builtins__:eval" in markers
    assert "call:first" in markers
    assert "call:second" in markers
    assert "call:third" in markers
    assert "call:fourth" in markers
    assert "call:fifth" in markers


def test_relative_import_scanner_resolves_owner_dependencies() -> None:
    source = """
from .rainbow_option_composition_semantics import RainbowOptionComposition
from . import uit_contract_qualification
"""
    imported = set(
        _resolved_imported_modules_from_source(
            source,
            package="qore.infrastructure",
        )
    )

    assert "qore.infrastructure.rainbow_option_composition_semantics" in imported
    assert "qore.infrastructure.uit_contract_qualification" in imported


def test_relative_imports_cannot_hide_provider_runtime_or_network_authority() -> None:
    source = """
from . import provider_runtime
from . import execution_boundary
"""
    imported = set(
        _resolved_imported_modules_from_source(
            source,
            package="qore.infrastructure",
        )
    )

    for module_name in (
        "qore.infrastructure.provider_runtime",
        "qore.infrastructure.execution_boundary",
    ):
        assert module_name in imported
        assert _is_forbidden_provider_runtime_or_network_import(module_name)


def test_final_owner_and_oracle_reject_resolved_provider_runtime_network_imports() -> None:
    violations: list[tuple[str, str]] = []
    for module_name in sorted(_EXPECTED_D04_OWNER_MODULE_NAMES):
        for imported in _resolved_owner_imports(module_name):
            if _is_forbidden_provider_runtime_or_network_import(imported):
                violations.append((module_name, imported))

    oracle_imports = _resolved_imported_modules_from_source(
        _FULL_CLOSURE_ORACLE_PATH.read_text(encoding="utf-8"),
        package="tests.infrastructure",
    )
    for imported in oracle_imports:
        if _is_forbidden_provider_runtime_or_network_import(imported):
            violations.append((str(_FULL_CLOSURE_ORACLE_PATH), imported))

    assert violations == []


def test_relative_imports_cannot_bypass_owner_directionality_guards() -> None:
    violations: list[tuple[str, str]] = []

    for module_name in sorted(_GENERIC_AUTHORITY_MODULE_NAMES):
        for imported in _resolved_owner_imports(module_name):
            if imported in _PRODUCT_QUALIFICATION_MODULE_NAMES:
                violations.append((module_name, imported))

    for module_name, forbidden_imports in sorted(_FORBIDDEN_DIRECTIONAL_IMPORTS.items()):
        for imported in _resolved_owner_imports(module_name):
            if imported in forbidden_imports:
                violations.append((module_name, imported))

    assert violations == []


def test_economic_identity_schema_cannot_absorb_listing_or_provider_material() -> None:
    from qore.infrastructure.universal_instrument_identity import EconomicIdentity

    assert tuple(field.name for field in fields(EconomicIdentity)) == (
        _EXPECTED_ECONOMIC_IDENTITY_FIELDS
    )


def test_securities_financing_owner_cannot_add_current_state_authority_shapes() -> None:
    path = _owner_path("qore.infrastructure.securities_financing_semantics")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    class_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    violations = sorted(
        class_name
        for class_name in class_names
        if any(
            fragment in class_name for fragment in _SFT_CURRENT_STATE_NAME_FRAGMENTS
        )
    )

    assert violations == []
