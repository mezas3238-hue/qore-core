"""Build exact-SHA component certification evidence for CIBO + Account-Wide Risk."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from qore.infrastructure.fundednext_live_guard import (
    CERTIFIED_LIVE_DIRECTIONS,
    FOREX_OPEN_COMMISSION_PER_LOT_USD,
    LIVE_ENTRY_ANCHORS_NY,
)
from qore.infrastructure.fundednext_operational_risk_policy import (
    QORE_INTERNAL_ATTACK_HEAT_FRACTION,
    QORE_INTERNAL_ATTACK_MIN_EARNED_CUSHION_FRACTION,
    QORE_INTERNAL_BANK_HEAT_FRACTION,
    QORE_INTERNAL_NORMAL_HEAT_FRACTION,
    QORE_INTERNAL_SAFETY_BUFFER_FRACTION,
    QORE_OPERATIONAL_RISK_POLICY_VERSION,
    operational_risk_policy_fingerprint,
)
from qore.infrastructure.fundednext_stellar_instant import (
    MAXIMUM_LOSS_FRACTION,
    SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION,
)
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_CIBO_MARKETS,
    R315_CIBO_VERSION,
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    Vt08ForexCiboPosture,
    cibo_policy_fingerprint,
)
from qore.infrastructure.vt08_forex_fundednext_sizing import R315_BASE_RISK_BPS

_SCHEMA = "qore.fundednext.cibo-risk-operational-certification.v3"


def build_certification(*, git_sha: str) -> dict[str, object]:
    if len(git_sha) != 40:
        raise ValueError("git_sha must be a full commit SHA")
    return {
        "schema": _SCHEMA,
        "git_sha": git_sha,
        "status": "CIBO_RISK_COMPONENT_CERTIFIED",
        "scope": {
            "trader": "VT08_FOREX",
            "markets": list(R315_CIBO_MARKETS),
            "certified_live_directions": {
                symbol: sorted(sides)
                for symbol, sides in sorted(CERTIFIED_LIVE_DIRECTIONS.items())
            },
            "live_causal_entry_anchor_ny": list(LIVE_ENTRY_ANCHORS_NY),
            "methodology_fingerprint": R315_METHOD_FINGERPRINT,
            "frozen_trader_risk_fingerprint": R315_RISK_FINGERPRINT,
            "base_risk_bps": {
                symbol: str(R315_BASE_RISK_BPS[symbol])
                for symbol in sorted(R315_BASE_RISK_BPS)
            },
            "opening_commission_per_lot_usd_reserved_in_risk": str(
                FOREX_OPEN_COMMISSION_PER_LOT_USD
            ),
        },
        "provider": {
            "program": "STELLAR_INSTANT",
            "maximum_loss_fraction": str(MAXIMUM_LOSS_FRACTION),
            "trailing_mll": True,
            "daily_loss_limit": None,
            "cumulative_open_risk_fraction": (
                None
                if SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION is None
                else str(SEPARATE_MAX_RISK_AT_ANY_TIME_FRACTION)
            ),
            "cumulative_open_risk_guard_enforced": True,
            "cumulative_open_risk_is_maximum_loss": False,
        },
        "cibo": {
            "version": R315_CIBO_VERSION,
            "policy_fingerprint": cibo_policy_fingerprint(),
            "postures": [item.value for item in Vt08ForexCiboPosture],
            "capital_authority": False,
            "attack_can_override_risk": False,
            "attack_changes_per_trade_bps": False,
        },
        "account_wide_risk": {
            "final_capital_authority": True,
            "decisions": ["ALLOW", "REDUCE", "REJECT"],
            "provider_headroom_enforced": True,
            "provider_max_risk_at_any_time_enforced": True,
            "qore_internal_headroom_enforced": True,
            "pending_risk_included": True,
            "open_stop_risk_included": True,
            "broker_executable_price_risk_recheck_required": True,
            "opening_commission_reserved": True,
            "durable_reservations_required": True,
            "restart_reconciliation_required": True,
        },
        "qore_internal_policy": {
            "version": QORE_OPERATIONAL_RISK_POLICY_VERSION,
            "fingerprint": operational_risk_policy_fingerprint(),
            "maximum_loss_fraction": str(MAXIMUM_LOSS_FRACTION),
            "uses_provider_mll_without_second_trailing_wall": True,
            "safety_buffer_fraction": str(QORE_INTERNAL_SAFETY_BUFFER_FRACTION),
            "bank_heat_fraction": str(QORE_INTERNAL_BANK_HEAT_FRACTION),
            "normal_heat_fraction": str(QORE_INTERNAL_NORMAL_HEAT_FRACTION),
            "attack_heat_fraction": str(QORE_INTERNAL_ATTACK_HEAT_FRACTION),
            "attack_min_earned_cushion_fraction": str(
                QORE_INTERNAL_ATTACK_MIN_EARNED_CUSHION_FRACTION
            ),
            "explicitly_not_provider_rule": True,
        },
        "governance": {
            "component_certification_grants_order_send_authority": False,
            "component_certification_grants_live_activation": False,
            "pr_may_be_merged": False,
            "pr_may_be_marked_ready": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = build_certification(git_sha=args.git_sha)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
