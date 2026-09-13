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
    PILOT_SYMBOL_MAP,
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
        "mt5_boundary": root / "src/qore/infrastructure/fundednext_mt5.py",
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
            "trailing_mll": True,
            "mll_capped_at_initial_balance": True,
            "payout_lowers_mll": False,
            "activation_reverification_required": True,
            "documentation_leverage_conflict": True,
            "execution_leverage_source": "MT5_SYMBOL_INFO",
        },
        "topology": {
            "traders": {
                "VT08_FOREX": ["AUDJPY", "GBPUSD", "GBPJPY"],
                "VT08_INDEX": ["NAS100", "SP500", "US30"],
            },
            "cibo_instances": ["CIBO_FOREX", "CIBO_INDEX"],
            "risk_scope": "ACCOUNT_WIDE",
            "signal_flow": (
                "VT08 -> CIBO_REQUEST -> ACCOUNT_WIDE_RISK -> "
                "RiskAuthorization -> MT5"
            ),
            "provider_symbols": dict(PILOT_SYMBOL_MAP),
        },
        "certification_state": {
            "vt08_forex_demo_approved": True,
            "vt08_forex_certificate_run_id": 34772576642,
            "vt08_forex_certificate_artifact_id": 10322482424,
            "vt08_forex_certificate_json_sha256": (
                "a4eb567592cedb4e92926881fb7a859c7b455329f00a4227d6886bbb1a33cf98"
            ),
            "vt08_index_demo_approved": False,
            "vt08_index_work_in_progress": True,
            "cibo_forex_policy": "R3.15_CERTIFIED_CAPABILITY_ONLY",
            "cibo_r3_17_promoted": False,
            "cibo_index_policy": "UNAPPROVED",
        },
        "component_versions": {
            "provider_contract": "stellar-instant-2026-09-13-v1",
            "account_wide_risk": "account-wide-risk-v1",
            "mt5_boundary": "fundednext-mt5-boundary-v1",
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
            "shared_risk_implemented": True,
            "mt5_boundary_implemented": True,
            "concrete_mt5_gateway_bound": False,
            "actual_account_bound": False,
            "actual_symbol_info_verified": False,
            "dry_run_passed_on_actual_account": False,
            "shadow_mode_passed_on_actual_account": False,
            "ready_to_operate_stellar_instant": False,
        },
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
