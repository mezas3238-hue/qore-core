from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"expected patch anchor missing: {path}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, addition: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + addition.rstrip() + "\n", encoding="utf-8")


def patch_mt5_gateway() -> None:
    path = "src/qore/infrastructure/fundednext_mt5.py"
    replace_once(
        path,
        "from qore.infrastructure.fundednext_execution_bridge import extract_risk_provenance\n"
        "from qore.infrastructure.fundednext_mt5_mutation_ledger import (",
        "from qore.infrastructure.fundednext_execution_bridge import extract_risk_provenance\n"
        "from qore.infrastructure.fundednext_production_binding import (\n"
        "    FundedNextProductionAccountBinding,\n"
        "    FundedNextProductionBindingError,\n"
        "    validate_fundednext_gateway_account,\n"
        ")\n"
        "from qore.infrastructure.fundednext_mt5_mutation_ledger import (",
    )
    replace_once(
        path,
        "from qore.infrastructure.market_test_environment import (\n"
        "    MarketRuntimeEnvironment,\n"
        "    MarketTestAccountIdentity,\n"
        ")",
        "from qore.infrastructure.market_test_environment import MarketTestAccountIdentity",
    )
    replace_once(
        path,
        "        rule_verification: StellarInstantRuleVerification,\n"
        "        owner_submission_enabled: bool = False,",
        "        rule_verification: StellarInstantRuleVerification,\n"
        "        production_binding: FundedNextProductionAccountBinding | None = None,\n"
        "        owner_submission_enabled: bool = False,",
    )
    replace_once(
        path,
        "        _validate_account(account)\n",
        "        _validate_account(account, production_binding=production_binding)\n",
    )
    replace_once(
        path,
        "        self._rules = rule_verification\n"
        "        self._owner_submission_enabled = owner_submission_enabled",
        "        self._rules = rule_verification\n"
        "        self._production_binding = production_binding\n"
        "        self._owner_submission_enabled = owner_submission_enabled",
    )
    old = '''def _validate_account(account: MarketTestAccountIdentity) -> None:\n    if not isinstance(account, MarketTestAccountIdentity):\n        raise Mt5ExecutionValidationError("MT5 account identity must be explicit")\n    if account.provider_key != _PROVIDER_KEY:\n        raise Mt5ExecutionValidationError(\n            "MT5 account must use fundednext-stellar-instant-mt5 provider key"\n        )\n    if account.environment not in {\n        MarketRuntimeEnvironment.DEMO,\n        MarketRuntimeEnvironment.TEST,\n    }:\n        raise Mt5ExecutionValidationError(\n            "FundedNext simulated proprietary account must remain TEST/DEMO in QORE"\n        )\n'''
    new = '''def _validate_account(\n    account: MarketTestAccountIdentity,\n    *,\n    production_binding: FundedNextProductionAccountBinding | None,\n) -> None:\n    try:\n        validate_fundednext_gateway_account(\n            account,\n            production_binding=production_binding,\n        )\n    except FundedNextProductionBindingError as error:\n        raise Mt5ExecutionValidationError(str(error)) from error\n'''
    replace_once(path, old, new)


def patch_operational_gateway() -> None:
    path = "src/qore/infrastructure/fundednext_operational.py"
    replace_once(
        path,
        "from qore.infrastructure.fundednext_mt5 import (",
        "from qore.infrastructure.fundednext_production_binding import (\n"
        "    FundedNextProductionAccountBinding,\n"
        ")\n"
        "from qore.infrastructure.fundednext_mt5 import (",
    )
    replace_once(
        path,
        "        rule_verification: StellarInstantRuleVerification,\n"
        "        safety: OperationalSafetyController,\n"
        "        owner_submission_enabled: bool = False,",
        "        rule_verification: StellarInstantRuleVerification,\n"
        "        safety: OperationalSafetyController,\n"
        "        production_binding: FundedNextProductionAccountBinding | None = None,\n"
        "        owner_submission_enabled: bool = False,",
    )
    replace_once(
        path,
        "            rule_verification=rule_verification,\n"
        "            owner_submission_enabled=owner_submission_enabled,",
        "            rule_verification=rule_verification,\n"
        "            production_binding=production_binding,\n"
        "            owner_submission_enabled=owner_submission_enabled,",
    )


def patch_mt5_transport() -> None:
    path = "src/qore/infrastructure/fundednext_mt5_transport.py"
    replace_once(
        path,
        "from datetime import UTC, datetime, timedelta\n",
        "from dataclasses import dataclass\nfrom datetime import UTC, datetime, timedelta\n",
    )
    replace_once(
        path,
        '''class Mt5OrderResultLike(Protocol):\n    retcode: int\n    order: int\n    comment: str\n\n\nclass Mt5OrderLike(Protocol):''',
        '''class Mt5OrderResultLike(Protocol):\n    retcode: int\n    order: int\n    comment: str\n\n\nclass Mt5OrderCheckResultLike(Protocol):\n    retcode: int\n    comment: str\n\n\nclass Mt5OrderLike(Protocol):''',
    )
    replace_once(
        path,
        '''    def order_send(self, request: dict[str, object]) -> Mt5OrderResultLike | None: ...\n''',
        '''    def order_check(\n        self,\n        request: dict[str, object],\n    ) -> Mt5OrderCheckResultLike | None: ...\n\n    def order_send(self, request: dict[str, object]) -> Mt5OrderResultLike | None: ...\n''',
    )
    replace_once(
        path,
        "class MetaTrader5FundedNextTransport:\n",
        '''@dataclass(frozen=True, slots=True)\nclass Mt5OrderCheckEvidence:\n    client_order_id: str\n    provider_symbol: str\n    retcode: int\n    comment: str\n    checked_at: datetime\n\n    @property\n    def ok(self) -> bool:\n        return self.retcode == 0\n\n\nclass MetaTrader5FundedNextTransport:\n''',
    )
    replace_once(
        path,
        '''    def submit_order(\n        self,\n        plan: FundedNextMt5OrderPlan,\n    ) -> FundedNextMt5TransportReceipt:\n''',
        '''    def check_order(self, plan: FundedNextMt5OrderPlan) -> Mt5OrderCheckEvidence:\n        """Ask MT5 to validate the exact future payload without mutation."""\n\n        self._require_bound_account()\n        if not isinstance(plan, FundedNextMt5OrderPlan):\n            raise Mt5ExecutionValidationError("MT5 shadow check requires canonical plan")\n        request = self._submission_payload(plan)\n        result = self._api.order_check(request)\n        if result is None:\n            raise Mt5ExecutionBlockedError("mt5-order-check-no-result")\n        return Mt5OrderCheckEvidence(\n            client_order_id=plan.client_order_id,\n            provider_symbol=plan.provider_symbol,\n            retcode=int(result.retcode),\n            comment=str(result.comment),\n            checked_at=datetime.now(UTC),\n        )\n\n    def submit_order(\n        self,\n        plan: FundedNextMt5OrderPlan,\n    ) -> FundedNextMt5TransportReceipt:\n''',
    )


def patch_no_send_probe() -> None:
    path = "scripts/fundednext_mt5_no_send_probe.py"
    replace_once(path, "import json\nimport sys\n", "import json\nimport subprocess\nimport sys\n")
    replace_once(
        path,
        'EXPECTED_SERVER = "FundedNext-Server"\n\n\ndef _fail',
        '''EXPECTED_SERVER = "FundedNext-Server"\n\n\ndef _git_sha() -> str:\n    result = subprocess.run(\n        ["git", "rev-parse", "HEAD"],\n        check=True,\n        capture_output=True,\n        text=True,\n    )\n    sha = result.stdout.strip().lower()\n    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):\n        raise RuntimeError("git_head_is_not_full_sha")\n    return sha\n\n\ndef _fail''',
    )
    replace_once(
        path,
        '''def main() -> int:\n    if not mt5.initialize():\n''',
        '''def main() -> int:\n    try:\n        git_sha = _git_sha()\n    except Exception as exc:\n        return _fail(\n            "git_sha_unavailable",\n            details={"type": type(exc).__name__, "message": str(exc)},\n        )\n    if not mt5.initialize():\n''',
    )
    replace_once(
        path,
        '''            "ok": True,\n            "timestamp_utc": datetime.now(UTC).isoformat(),\n''',
        '''            "ok": True,\n            "git_sha": git_sha,\n            "timestamp_utc": datetime.now(UTC).isoformat(),\n''',
    )


def patch_manifest() -> None:
    path = "src/qore/infrastructure/fundednext_pilot_manifest.py"
    replace_once(
        path,
        '_SCHEMA = "qore.fundednext.stellar-instant-2k-pilot-readiness.v2"',
        '_SCHEMA = "qore.fundednext.stellar-instant-2k-pilot-readiness.v3"',
    )
    replace_once(
        path,
        '''        "mt5_transport": root / "src/qore/infrastructure/fundednext_mt5_transport.py",\n''',
        '''        "mt5_transport": root / "src/qore/infrastructure/fundednext_mt5_transport.py",\n        "production_binding": (\n            root / "src/qore/infrastructure/fundednext_production_binding.py"\n        ),\n        "runtime_supervisor": (\n            root / "src/qore/infrastructure/fundednext_runtime_supervisor.py"\n        ),\n        "shadow_probe": root / "scripts/fundednext_mt5_shadow_probe.py",\n        "runtime_guard": root / "scripts/fundednext_runtime_guard.py",\n        "runtime_readiness": root / "scripts/fundednext_runtime_readiness.py",\n        "windows_autostart_installer": (\n            root / "scripts/install_fundednext_runtime_task.ps1"\n        ),\n        "reboot_recovery_probe": (\n            root / "scripts/fundednext_reboot_recovery_probe.ps1"\n        ),\n''',
    )
    replace_once(
        path,
        '''            "mt5_transport": "fundednext-metatrader5-transport-dynamic-filling-v2",\n            "account_bound_execution": "fundednext-account-bound-execution-v1",\n''',
        '''            "mt5_transport": "fundednext-metatrader5-transport-order-check-v3",\n            "production_binding": "fundednext-production-binding-v1",\n            "runtime_supervisor": "fundednext-runtime-supervisor-v1",\n            "account_bound_execution": "fundednext-account-bound-execution-v2",\n''',
    )
    replace_once(
        path,
        '''            "code_complete_for_account_binding": True,\n            "concrete_mt5_gateway_bound": False,\n''',
        '''            "code_complete_for_account_binding": True,\n            "production_binding_contract_implemented": True,\n            "shadow_order_check_implemented": True,\n            "runtime_supervisor_implemented": True,\n            "runtime_guard_implemented": True,\n            "windows_autostart_installer_implemented": True,\n            "reboot_recovery_probe_implemented": True,\n            "exact_sha_runtime_readiness_verifier_implemented": True,\n            "first_execution_engineering_closeout_complete": True,\n            "concrete_mt5_gateway_bound": False,\n''',
    )


def patch_transport_tests() -> None:
    path = "tests/infrastructure/test_fundednext_mt5_transport.py"
    replace_once(
        path,
        '''        self.next_result: _Result | None = _Result(self.TRADE_RETCODE_DONE, 9001)\n        self.active_orders: tuple[_Order, ...] = ()\n''',
        '''        self.next_result: _Result | None = _Result(self.TRADE_RETCODE_DONE, 9001)\n        self.next_check_result: _Result | None = _Result(0, 0, "Done")\n        self.active_orders: tuple[_Order, ...] = ()\n''',
    )
    replace_once(
        path,
        '''        self.last_request: dict[str, object] | None = None\n''',
        '''        self.last_request: dict[str, object] | None = None\n        self.order_send_calls = 0\n        self.order_check_calls = 0\n''',
    )
    replace_once(
        path,
        '''    def order_send(self, request: dict[str, object]) -> _Result | None:\n        self.last_request = request\n        return self.next_result\n''',
        '''    def order_check(self, request: dict[str, object]) -> _Result | None:\n        self.order_check_calls += 1\n        self.last_request = request\n        return self.next_check_result\n\n    def order_send(self, request: dict[str, object]) -> _Result | None:\n        self.order_send_calls += 1\n        self.last_request = request\n        return self.next_result\n''',
    )
    append_once(
        path,
        "def test_shadow_order_check_never_calls_order_send() -> None:",
        '''def test_shadow_order_check_never_calls_order_send() -> None:\n    api = _Api()\n    transport = _transport(api)\n    evidence = transport.check_order(_plan())\n    assert evidence.ok is True\n    assert evidence.retcode == 0\n    assert api.order_check_calls == 1\n    assert api.order_send_calls == 0\n    assert api.last_request is not None\n    assert api.last_request["type_filling"] == api.ORDER_FILLING_IOC\n''',
    )


def patch_readiness_tests() -> None:
    path = "tests/infrastructure/test_fundednext_runtime_readiness.py"
    replace_once(
        path,
        '''    payload = module.build_readiness(\n''',
        '''    build_readiness = getattr(module, "build_readiness")\n    payload = build_readiness(\n''',
    )
    replace_once(
        path,
        '''    payload = module.build_readiness(\n''',
        '''    build_readiness = getattr(module, "build_readiness")\n    payload = build_readiness(\n''',
    )


def patch_workflow() -> None:
    path = ".github/workflows/fundednext-stellar-instant-2k-pilot.yml"
    replace_once(
        path,
        '''      - agent/fundednext-stellar-instant-canonical-execution-001\n''',
        '''      - agent/fundednext-stellar-instant-canonical-execution-001\n      - agent/fundednext-first-execution-closeout-001\n''',
    )
    replace_once(
        path,
        "      - name: Compile\n        run: python -m compileall -q src tests\n",
        "      - name: Compile\n        run: python -m compileall -q src tests scripts\n",
    )
    replace_once(path, "        run: mypy src tests\n", "        run: mypy src tests scripts\n")
    replace_once(
        path,
        '''            tests/infrastructure/test_fundednext_mt5_transport.py \\\n            tests/infrastructure/test_fundednext_operational.py \\\n''',
        '''            tests/infrastructure/test_fundednext_mt5_transport.py \\\n            tests/infrastructure/test_fundednext_production_binding.py \\\n            tests/infrastructure/test_fundednext_runtime_supervisor.py \\\n            tests/infrastructure/test_fundednext_runtime_readiness.py \\\n            tests/infrastructure/test_fundednext_operational.py \\\n''',
    )
    replace_once(
        path,
        '''          assert payload["schema"] == "qore.fundednext.stellar-instant-2k-pilot-readiness.v2"\n''',
        '''          assert payload["schema"] == "qore.fundednext.stellar-instant-2k-pilot-readiness.v3"\n''',
    )
    replace_once(
        path,
        '''          assert readiness["durable_shared_risk_implemented"] is True\n          assert readiness["ready_for_owner_activation"] is False\n''',
        '''          assert readiness["durable_shared_risk_implemented"] is True\n          assert readiness["production_binding_contract_implemented"] is True\n          assert readiness["shadow_order_check_implemented"] is True\n          assert readiness["runtime_supervisor_implemented"] is True\n          assert readiness["runtime_guard_implemented"] is True\n          assert readiness["windows_autostart_installer_implemented"] is True\n          assert readiness["reboot_recovery_probe_implemented"] is True\n          assert readiness["exact_sha_runtime_readiness_verifier_implemented"] is True\n          assert readiness["first_execution_engineering_closeout_complete"] is True\n          assert readiness["ready_for_owner_activation"] is False\n''',
    )
    marker = "      - name: Upload pilot evidence\n"
    safety = '''      - name: Verify read-only runtime probes contain no order_send call\n        run: |\n          python - <<'PY'\n          import ast\n          from pathlib import Path\n\n          for name in (\n              "scripts/fundednext_mt5_no_send_probe.py",\n              "scripts/fundednext_mt5_shadow_probe.py",\n              "scripts/fundednext_runtime_guard.py",\n              "scripts/fundednext_runtime_readiness.py",\n          ):\n              tree = ast.parse(Path(name).read_text(encoding="utf-8"), filename=name)\n              calls = [\n                  node\n                  for node in ast.walk(tree)\n                  if isinstance(node, ast.Call)\n                  and isinstance(node.func, ast.Attribute)\n                  and node.func.attr == "order_send"\n              ]\n              assert not calls, f"read-only probe calls order_send: {name}"\n          PY\n\n'''
    replace_once(path, marker, safety + marker)


def main() -> None:
    patch_mt5_gateway()
    patch_operational_gateway()
    patch_mt5_transport()
    patch_no_send_probe()
    patch_manifest()
    patch_transport_tests()
    patch_readiness_tests()
    patch_workflow()


if __name__ == "__main__":
    main()
