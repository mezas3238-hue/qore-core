"""Build the immutable readiness manifest for the FundedNext Stellar Instant pilot."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from qore.infrastructure.fundednext_live_guard import (
    CERTIFIED_LIVE_DIRECTIONS,
    FOREX_OPEN_COMMISSION_PER_LOT_USD,
    LIVE_ENTRY_ANCHORS_NY,
)
from qore.infrastructure.fundednext_operational_risk_policy import (
    QORE_OPERATIONAL_RISK_POLICY_VERSION,
    operational_risk_policy_fingerprint,
)
from qore.infrastructure.fundednext_stellar_instant import (
    MAXIMUM_LOSS_FRACTION,
    PILOT_INITIAL_BALANCE,
    SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION,
)
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_CIBO_VERSION,
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    cibo_policy_fingerprint,
)

_SCHEMA = "qore.fundednext.stellar-instant-2k-pilot-readiness.v2"


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_manifest(*, root: Path, git_sha: str) -> dict[str, object]:
    if len(git_sha) != 40:
        raise ValueError("git_sha must be a full commit SHA")
    files = {
        "provider_contract": root / "src/qore/infrastructure/fundednext_stellar_instant.py",
        "account_wide_risk": root / "src/qore/infrastructure/account_wide_risk.py",
        "operational_risk_policy": (
            root / "src/qore/infrastructure/fundednext_operational_risk_policy.py"
        ),
        "durable_risk_ledger": root / "src/qore/infrastructure/account_wide_risk_ledger.py",
        "execution_bridge": root / "src/qore/infrastructure/fundednext_execution_bridge.py",
        "mt5_boundary": root / "src/qore/infrastructure/fundednext_mt5.py",
        "mt5_transport": root / "src/qore/infrastructure/fundednext_mt5_transport.py",
        "live_authorization": root / "src/qore/infrastructure/fundednext_live_authorization.py",
        "live_activation_verifier": root / "src/qore/infrastructure/fundednext_live_activation.py",
        "live_guard": root / "src/qore/infrastructure/fundednext_live_guard.py",
        "live_safety": root / "src/qore/infrastructure/fundednext_live_safety.py",
        "live_mt5_gateway": root / "src/qore/infrastructure/fundednext_live_mt5.py",
        "mt5_mutation_ledger": root / "src/qore/infrastructure/fundednext_mt5_mutation_ledger.py",
        "position_exit_ledger": root / "src/qore/infrastructure/fundednext_position_exit_ledger.py",
        "account_bound_execution": root / "src/qore/infrastructure/fundednext_operational.py",
        "runtime_pipeline": root / "src/qore/infrastructure/fundednext_runtime_pipeline.py",
        "runtime_state": root / "src/qore/infrastructure/fundednext_runtime_state.py",
        "runtime_service": root / "scripts/qore_fundednext_runtime.py",
        "runtime_installer": root / "scripts/install_fundednext_runtime.ps1",
        "runtime_watchdog": root / "scripts/qore_fundednext_watchdog.ps1",
        "runtime_reboot_verifier": root / "scripts/finalize_fundednext_activation.ps1",
        "owner_live_activation": root / "scripts/authorize_fundednext_live.ps1",
        "no_send_probe": root / "scripts/fundednext_mt5_no_send_probe.py",
        "order_check_probe": root / "scripts/fundednext_mt5_order_check_probe.py",
        "vt08_forex_cibo": root / "src/qore/infrastructure/vt08_forex_cibo_operational.py",
        "vt08_forex_sizing": root / "src/qore/infrastructure/vt08_forex_fundednext_sizing.py",
        "cibo_risk_certification": (
            root / "src/qore/infrastructure/fundednext_cibo_risk_certification.py"
        ),
        "vt08_forex_executable": root / "src/qore/infrastructure/traders/vt08_b01_r3_8.py",
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
            "cumulative_open_risk_fraction": (
                None
                if SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION is None
                else str(SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION)
            ),
            "cumulative_open_risk_guard_present": True,
            "cumulative_open_risk_is_maximum_loss": False,
            "trailing_mll": True,
            "mll_capped_at_initial_balance": True,
            "payout_lowers_mll": False,
            "execution_leverage_source": "MT5_SYMBOL_INFO_AND_ORDER_CALC_MARGIN",
            "opening_commission_per_lot_usd_reserved_in_risk": str(
                FOREX_OPEN_COMMISSION_PER_LOT_USD
            ),
            "automation_and_vps_entitlements_required_for_live": True,
            "provider_rules_revalidated_jit_before_order_send": True,
            "synthetic_inactivity_trade_forbidden": True,
        },
        "qore_internal_risk_policy": {
            "version": QORE_OPERATIONAL_RISK_POLICY_VERSION,
            "fingerprint": operational_risk_policy_fingerprint(),
            "explicitly_not_provider_rule": True,
            "risk_is_final_capital_authority": True,
        },
        "topology": {
            "traders": {"VT08_FOREX": ["AUDJPY", "GBPUSD", "GBPJPY"]},
            "certified_live_directions": {
                symbol: sorted(sides)
                for symbol, sides in sorted(CERTIFIED_LIVE_DIRECTIONS.items())
            },
            "live_causal_entry_anchor_ny": list(LIVE_ENTRY_ANCHORS_NY),
            "risk_scope": "ACCOUNT_WIDE",
            "signal_flow": (
                "VT08_FOREX -> CAUSAL_DAILY_GATE -> CIBO -> BROKER_EXACT_SIZING -> "
                "ACCOUNT_WIDE_RISK -> RiskAuthorization -> LIVE_RISK_RECHECK -> MT5"
            ),
            "index_execution_enabled": False,
        },
        "certification_state": {
            "vt08_forex_demo_approved": True,
            "vt08_forex_certificate_run_id": 34772576642,
            "vt08_forex_certificate_artifact_id": 10322482424,
            "vt08_forex_methodology_fingerprint": R315_METHOD_FINGERPRINT,
            "vt08_forex_risk_policy_fingerprint": R315_RISK_FINGERPRINT,
            "cibo_forex_policy": "R3.15_OPERATIONAL_POSTURE_UNDER_SOVEREIGN_RISK",
            "cibo_forex_version": R315_CIBO_VERSION,
            "cibo_forex_fingerprint": cibo_policy_fingerprint(),
            "cibo_forex_normal_bank_attack_implemented": True,
            "account_wide_risk_component_certifiable": True,
        },
        "component_versions": {
            "provider_contract": "stellar-instant-6pct-trailing-plus-3pct-open-risk-v4",
            "account_wide_risk": "account-wide-risk-v1",
            "operational_risk_policy": QORE_OPERATIONAL_RISK_POLICY_VERSION,
            "durable_risk_ledger": "account-wide-risk-ledger-v1",
            "execution_bridge": "fundednext-canonical-execution-v2",
            "live_authorization": "fundednext-production-exact-sha-authorization-v2",
            "live_activation_verifier": "fundednext-strict-evidence-verifier-v1",
            "live_guard": "fundednext-live-guard-v1",
            "live_safety": "fundednext-live-safety-v1",
            "live_mt5_gateway": "fundednext-production-risk-recheck-gateway-v2",
            "position_exit_ledger": "fundednext-h4-position-exit-ledger-v1",
            "runtime_service": "fundednext-vt08-cibo-risk-resident-runtime-v2",
            "vt08_forex_cibo": R315_CIBO_VERSION,
        },
        "component_sha256": {name: _digest(path) for name, path in files.items()},
        "governance": {
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
            "certified_direction_guard_implemented": True,
            "causal_daily_selection_live_subset_implemented": True,
            "shared_risk_implemented": True,
            "durable_shared_risk_implemented": True,
            "broker_exact_sizing_implemented": True,
            "opening_commission_reserved_in_risk_implemented": True,
            "broker_executable_risk_recheck_implemented": True,
            "current_price_open_position_risk_implemented": True,
            "canonical_execution_bridge_implemented": True,
            "dynamic_filling_mode_validation_implemented": True,
            "production_account_authorization_contract_implemented": True,
            "strict_activation_evidence_digest_verification_implemented": True,
            "ea_and_vps_entitlement_gates_implemented": True,
            "tracked_worktree_sha_guard_implemented": True,
            "broker_native_order_check_shadow_implemented": True,
            "certified_direction_order_check_probe_implemented": True,
            "resident_vt08_cibo_risk_runtime_implemented": True,
            "durable_h4_containment_exit_implemented": True,
            "dual_copy_trailing_mll_checkpoint_implemented": True,
            "single_writer_and_stale_lock_recovery_implemented": True,
            "durable_runtime_heartbeat_implemented": True,
            "durable_scoped_kill_switches_implemented": True,
            "windows_autostart_watchdog_implemented": True,
            "post_reboot_reconciliation_proof_implemented": True,
            "owner_live_activation_transition_implemented": True,
            "provider_inactivity_guard_implemented": True,
            "news_policy_telemetry_implemented": True,
            "resident_scripts_compiled_in_ci": True,
            "ready_for_vps_shadow_closeout": True,
            "actual_account_bound_on_this_sha": False,
            "actual_symbol_info_verified_on_this_sha": False,
            "no_send_passed_on_this_sha": False,
            "shadow_mode_passed_on_this_sha": False,
            "reboot_recovery_passed_on_this_sha": False,
            "ready_for_owner_activation": False,
            "ready_to_operate_stellar_instant": False,
        },
        "remaining_activation_evidence": [
            "deploy this exact final green SHA to the already-installed C:\\QORE checkout",
            "fresh exact-SHA NO-SEND and certified-direction order_check evidence",
            "exact-SHA resident SHADOW heartbeat/watchdog evidence",
            "exact-SHA reboot/recovery reconciliation evidence",
            "explicit Owner verification of EA and VPS entitlements plus current provider rules",
            "separate explicit Owner live-capital activation; no synthetic test order",
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
