"""Emit an auditable, credential-free FTMO/FundedNext provider contract manifest."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.provider_contracts import (
    CHALLENGE_CONTRACTS,
    ProviderAccountSnapshot,
    TradingPlatform,
    evaluate_provider_budget,
)
from qore.infrastructure.provider_operating import (
    ProviderAccountBinding,
    resolve_execution_route,
)

_SCHEMA = "qore.provider_contracts.ftmo_fundednext.v1"
_VERIFIED_ON = "2026-09-13"
_REPRESENTATIVE_ACCOUNT_SIZES = (
    Decimal("25000"),
    Decimal("50000"),
    Decimal("100000"),
    Decimal("200000"),
)
_PLATFORMS = (
    TradingPlatform.CTRADER,
    TradingPlatform.MT4,
    TradingPlatform.MT5,
    TradingPlatform.MATCH_TRADER,
)


def _decimal_strings(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _decimal_strings(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_decimal_strings(item) for item in value]
    return value


def _contract_payload(contract_id: str) -> dict[str, Any]:
    contract = CHALLENGE_CONTRACTS[contract_id]
    payload = asdict(contract)
    payload["provider"] = contract.provider.value
    payload["program"] = contract.program.value
    payload["stage"] = contract.stage.value
    payload["overall_loss_model"] = contract.overall_loss_model.value
    payload["sources"] = [asdict(source) for source in contract.sources]
    return cast(dict[str, Any], _decimal_strings(payload))


def _baseline_budget(contract_id: str) -> dict[str, Any]:
    contract = CHALLENGE_CONTRACTS[contract_id]
    initial = Decimal("100000")
    snapshot = ProviderAccountSnapshot(
        initial_balance=initial,
        balance=initial,
        equity=initial,
        daily_reset_balance=initial,
        highest_eod_balance=initial,
        trading_days_completed=0,
    )
    budget = evaluate_provider_budget(contract, snapshot)
    return cast(dict[str, Any], _decimal_strings(asdict(budget)))


def _binding_for(
    contract_id: str,
    *,
    platform: TradingPlatform,
    initial_balance: Decimal,
    addon: bool,
) -> ProviderAccountBinding:
    contract = CHALLENGE_CONTRACTS[contract_id]
    return ProviderAccountBinding(
        binding_id=(
            f"manifest:{contract_id}:{platform.value}:{initial_balance}:"
            f"ea-{str(addon).lower()}"
        ),
        contract_id=contract_id,
        provider=contract.provider,
        program=contract.program,
        stage=contract.stage,
        platform=platform,
        initial_balance=initial_balance,
        rules_verified_on=_VERIFIED_ON,
        fundednext_ea_addon_enabled=addon,
    )


def _route_matrix(contract_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for size in _REPRESENTATIVE_ACCOUNT_SIZES:
        for platform in _PLATFORMS:
            for addon in (False, True):
                binding = _binding_for(
                    contract_id,
                    platform=platform,
                    initial_balance=size,
                    addon=addon,
                )
                decision = resolve_execution_route(binding)
                rows.append(
                    {
                        "account_size": str(size),
                        "platform": platform.value,
                        "fundednext_ea_addon_enabled": addon,
                        "route": decision.route.value,
                        "automation_mode": decision.capability.mode.value,
                        "automated_order_submission_allowed": (
                            decision.capability.automated_order_submission_allowed
                        ),
                        "reason": decision.reason,
                        "capability_reason": decision.capability.reason,
                        "activation_reverification_required": (
                            decision.activation_reverification_required
                        ),
                    }
                )
    return rows


def build_manifest() -> dict[str, Any]:
    contracts = sorted(CHALLENGE_CONTRACTS)
    return {
        "schema": _SCHEMA,
        "verified_on": _VERIFIED_ON,
        "contracts": {
            contract_id: {
                "contract": _contract_payload(contract_id),
                "baseline_100k_budget": _baseline_budget(contract_id),
                "routing_matrix": _route_matrix(contract_id),
            }
            for contract_id in contracts
        },
        "routing_adjudication": {
            "ftmo": {
                "status": "AUTOMATION_SUPPORTED_SUBJECT_TO_ACTIVATION_REVERIFY",
                "frozen_automated_platforms": ["ctrader", "mt4", "mt5"],
                "sources": [
                    "https://ftmo.com/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/",
                    "https://ftmo.com/en/faq/which-platforms-can-i-use-for-trading/",
                    "https://ftmo.com/en/trading-platforms/",
                ],
            },
            "fundednext": {
                "status": "PRODUCT_RULE_CONFLICT_FAIL_CLOSED_TO_MANUAL",
                "generic_ea_source": (
                    "https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext"
                ),
                "product_specific_cfd_source": (
                    "https://help.fundednext.com/en/articles/12673301-"
                    "what-rules-do-i-need-to-follow-in-the-stellar-1-step-"
                    "challenge-at-fundednext-cfd"
                ),
                "platform_source": (
                    "https://help.fundednext.com/en/articles/8019808-"
                    "which-platforms-can-i-use-for-trading-at-fundednext"
                ),
                "operational_default": "manual-handoff-until-exact-product-reverified",
            },
        },
        "authority_chain": [
            "provider-rules",
            "provider-risk-budget",
            "qore-risk-policy",
            "cibo-request",
            "risk-authorization",
            "execution",
        ],
        "invariants": {
            "provider_rules_are_external_hard_constraints": True,
            "qore_overlay_may_only_reduce_provider_headroom": True,
            "cibo_request_is_risk_authorization": False,
            "risk_remains_sovereign": True,
            "provider_static_floors_are_not_retrailed_by_qore": True,
            "ftmo_1_step_uses_eod_trailing_overall_loss": True,
            "fundednext_product_rule_conflict_fails_closed_to_manual": True,
            "activation_reverification_required": True,
            "credentials_present": False,
            "orders_submitted": False,
        },
        "governance": {
            "research_only": True,
            "demo_eligible": False,
            "live_authorized": False,
            "production_authorized": False,
            "provider_selected_by_economic_result": False,
        },
    }


def write_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    write_manifest(args.out)


if __name__ == "__main__":
    main()
