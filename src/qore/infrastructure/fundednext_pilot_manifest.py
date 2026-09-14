"""Build the immutable readiness manifest for the FundedNext Stellar Instant pilot."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.fundednext_stellar_instant import (
    MAX_RISK_AT_ANY_TIME_FRACTION,
    MAXIMUM_LOSS_FRACTION,
    PILOT_INITIAL_BALANCE,
)
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_CIBO_VERSION,
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    cibo_policy_fingerprint,
)

_SCHEMA = "qore.fundednext.stellar-instant-2k-pilot-readiness.v1"


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_manifest(*, root: Path, git_sha: str) -> dict[str, object]:
    if len(git_sha) != 40:
        raise ValueError("git_sha must be a full commit SHA")
    files = {
        "provider_contract": root / "src/qore/infrastructure/fundednext_stellar_instant.py",
        "account_wide_risk": root / "src/qore/infrastructure/account_wide_risk.py",
        "durable_risk_ledger": (
            root / "src/qore/infrastructure/account_wide_risk_ledger.py"
        ),
        "execution_bridge": (
            root / "src/qore/infrastructure/fundednext_execution_bridge.py"
        ),
        "mt5_boundary": root / "src/qore/infrastructure/fundednext_mt5.py",
        "mt5_transport": root / "src/qore/infrastructure/fundednext_mt5_transport.py",
        "mt5_mutation_ledger": (
            root / "src/qore/infrastructure/fundednext_mt5_mutation_ledger.py"
        ),
        "account_bound_execution": (
            root / "src/qore/infrastructure/fundednext_operational.py"
        ),
        "vt08_forex_cibo": (
            root / "src/qore/infrastructure/vt08_forex_cibo_operational.py"
        ),
        "vt08_forex_sizing": (
            root / "src/qore/infrastructure/vt08_forex_fundednext_sizing.py"
        ),
        "vt08_forex_executable": root / "src/qore/infrastructure/traders/vt08_b01_r3_8.py",
        "vt08_index_r1_executable": (
            root / "src/qore/infrastructure/traders/vt08_index_c2_positional_r1.py"
        ),
    }
    missing = [name for name, path in files.items() if not path.is_file()]
    if missing:
        raise ValueError(f"required pilot files missing: {','.join(sorted(missing))}")
    return {
        "schema": _SCHEMA,
        "git_sha": git_sha,
        "provider": {
            "provider": "FUNDEDNEXT",
            "program": "STELLAR_INSTANT",
            "platform": "MT5",
            "pilot_initial_balance_usd": str(PILOT_INITIAL_BALANCE),
            "daily_loss_limit": None,
            "maximum_loss_fraction": str(MAXIMUM_LOSS_FRACTION),
            "max_risk_at_any_time_fraction": str(MAX_RISK_AT_ANY_TIME_FRACTION),
            "max_risk_value_is_research_snapshot_not_activation_authority": True,
            "account_specific_risk_limit_reverification_required": True,
            "trailing_mll": True,
            "mll_capped_at_initial_balance": True,
            "payout_lowers_mll": False,
            "activation_reverification_required": True,
            "documentation_leverage_conflict": True,
            "execution_leverage_source": "MT5_SYMBOL_INFO_AND_ORDER_CALC_MARGIN",
            "broker_symbol_source": "LIVE_MT5_ACCOUNT_CATALOG",
        },
        "topology": {
            "traders": {
                "VT08_FOREX": ["AUDJPY", "GBPUSD", "GBPJPY"],
                "VT08_INDEX": ["NAS100", "SP500", "US30"],
            },
            "cibo_instances": ["CIBO_FOREX", "CIBO_INDEX"],
            "risk_scope": "ACCOUNT_WIDE",
            "signal_flow": (
                "VT08_FOREX -> CIBO_FOREX_ALLOW -> BROKER_EXACT_SIZING -> "
                "ACCOUNT_WIDE_RISK -> RiskAuthorization -> CANONICAL_EXECUTION -> MT5"
            ),
            "provider_symbol_resolution": "ACCOUNT_CATALOG_EXACT_OR_UNIQUE_DECORATION",
            "index_execution_enabled": False,
        },
        "certification_state": {
            "vt08_forex_demo_approved": True,
            "vt08_forex_certificate_run_id": 34772576642,
            "vt08_forex_certificate_artifact_id": 10322482424,
            "vt08_forex_certificate_json_sha256": (
                "a4eb567592cedb4e92926881fb7a859c7b455329f00a4227d6886bbb1a33cf98"
            ),
            "vt08_forex_methodology_fingerprint": R315_METHOD_FINGERPRINT,
            "vt08_forex_risk_policy_fingerprint": R315_RISK_FINGERPRINT,
            "vt08_index_demo_approved": False,
            "vt08_index_work_in_progress": True,
            "cibo_forex_policy": "R3.15_CERTIFIED_CAPABILITY_ONLY",
            "cibo_forex_version": R315_CIBO_VERSION,
            "cibo_forex_fingerprint": cibo_policy_fingerprint(),
            "cibo_r3_17_promoted": False,
            "cibo_index_policy": "UNAPPROVED",
        },
        "component_versions": {
            "provider_contract": "stellar-instant-2026-09-14-revalidation-required-v2",
            "account_wide_risk": "account-wide-risk-v1",
            "durable_risk_ledger": "account-wide-risk-ledger-v1",
            "execution_bridge": "fundednext-canonical-execution-v1",
            "mt5_boundary": "fundednext-mt5-boundary-v1",
            "mt5_transport": "fundednext-metatrader5-transport-v1",
            "account_bound_execution": "fundednext-account-bound-execution-v1",
            "vt08_forex_sizing": "vt08-r315-mt5-tick-economics-v1",
            "vt08_forex_cibo": R315_CIBO_VERSION,
        },
        "component_sha256": {name: _digest(path) for name, path in files.items()},
        "governance": {
            "account_purchase_authorized": False,
            "order_submission_authorized": False,
            "real_capital_authorized": False,
            "live_authorized": False,
            "production_authorized": False,
            "pr_may_be_merged": False,
            "pr_may_be_marked_ready": False,
        },
        "technical_readiness": {
            "provider_contract_implemented": True,
            "cibo_forex_gate_implemented": True,
            "shared_risk_implemented": True,
            "durable_shared_risk_implemented": True,
            "canonical_execution_bridge_implemented": True,
            "mt5_boundary_implemented": True,
            "concrete_mt5_transport_implemented": True,
            "account_bound_symbol_resolution_implemented": True,
            "broker_exact_sizing_implemented": True,
            "durable_idempotency_and_unknown_outcome_recovery_implemented": True,
            "scoped_kill_switches_implemented": True,
            "code_complete_for_account_binding": True,
            "concrete_mt5_gateway_bound": False,
            "actual_account_bound": False,
            "actual_symbol_info_verified": False,
            "dry_run_passed_on_actual_account": False,
            "shadow_mode_passed_on_actual_account": False,
            "demo_execution_passed_on_actual_account": False,
            "ready_for_owner_activation": False,
            "ready_to_operate_stellar_instant": False,
        },
        "remaining_activation_evidence": [
            "current account-specific FundedNext rules and Risk Limit",
            "current EA/automation entitlement for the exact account",
            "MT5 account login binding without persisting credentials",
            "live terminal symbol catalog for AUDJPY GBPUSD GBPJPY",
            "live SymbolInfo/tick/margin sizing validation for all retained markets",
            "account equity/trailing-floor/open-position reconciliation",
            "no-send dry-run and shadow cycle on the bound account",
            "DEMO lifecycle/restart test if a compatible DEMO account is available",
            "explicit Owner activation authorization",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = build_manifest(root=Path.cwd(), git_sha=args.git_sha)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
