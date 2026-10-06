from __future__ import annotations

import ast
from pathlib import Path

from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    CiboCapitalMission,
    derive_cibo_capital_mission,
)
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment

_UNIVERSAL_CORE = (
    "src/qore/infrastructure/cibo_sovereign_capital_runtime.py",
    "src/qore/infrastructure/cibo_economic_engine_wiring.py",
    "src/qore/infrastructure/cibo_account_sizing_authority.py",
    "src/qore/infrastructure/cibo_capital_management_authority.py",
    "src/qore/infrastructure/cibo_capital_science_runtime_bridge.py",
    "src/qore/infrastructure/cibo_full_economic_digital_twin.py",
    "src/qore/infrastructure/cibo_multi_period_capital_mpc.py",
    "src/qore/infrastructure/cibo_portfolio_allocation_engine.py",
    "src/qore/infrastructure/cibo_native_maximum_intelligence.py",
    "src/qore/infrastructure/cibo_executive_brain.py",
)

_PROVIDER_SPECIFIC_IMPORT_TOKENS = (
    "ctrader",
    "mt4",
    "mt5",
    "fundednext",
    "ftmo",
    "oanda",
    "ibkr",
    "tradestation",
    "tastytrade",
    "match_trader",
)


def _import_targets(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name.lower() for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                targets.append(node.module.lower())
    return tuple(targets)


def test_sovereign_core_has_no_provider_or_platform_specific_imports() -> None:
    root = Path(__file__).resolve().parents[2]
    violations: list[str] = []

    for relative in _UNIVERSAL_CORE:
        path = root / relative
        for target in _import_targets(path):
            if any(token in target for token in _PROVIDER_SPECIFIC_IMPORT_TOKENS):
                violations.append(f"{relative}:{target}")

    assert violations == []


def test_native_max_has_no_closed_trader_admission_list() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "src/qore/infrastructure/cibo_native_maximum_intelligence.py"
    ).read_text(encoding="utf-8")

    assert "native maximum intelligence received unsupported Trader" not in source
    assert "_TURTLE_TRADERS" not in source


def test_generic_provider_identity_maps_across_all_runtime_environments() -> None:
    expected = {
        MarketRuntimeEnvironment.DEMO: CiboCapitalMission.DEMO_CAPABILITY_DISCOVERY,
        MarketRuntimeEnvironment.TEST: CiboCapitalMission.TEST_VALIDATION,
        MarketRuntimeEnvironment.SANDBOX: CiboCapitalMission.SANDBOX_SIMULATION,
        MarketRuntimeEnvironment.PRODUCTION: (
            CiboCapitalMission.PRODUCTION_SURVIVAL_COMPOUND
        ),
    }

    for environment, mission in expected.items():
        identity = CiboAccountCapitalIdentity(
            provider_key="universal-broker",
            account_ref=f"universal-{environment.value}",
            environment=environment,
        )

        policy = derive_cibo_capital_mission(identity)

        assert policy.mission is mission
        assert policy.sovereign_risk_required is True
        assert policy.provider_constraints_required is True
        assert policy.durable_capital_accounting_required is True
