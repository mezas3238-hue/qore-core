"""Postdecision settlement adapter for the CIBO single-account ceiling replay.

Historical outcome rows are postdecision-only. Five frozen Turtle lanes encode
their replay outcome as net_010_r (gross structural R minus the lane's fixed
0.10R research friction), even though the Phase22 transport historically named
that field gross_structural_outcome_r. This adapter restores structural gross R
before applying the sovereign provider economics exactly once. No settlement
field is accepted by any predecision API.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Any

from qore.infrastructure.account_wide_risk import RiskDecision
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_single_account_manifest_economics import (
    manifest_row_provider_cost_per_volume_usd,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_run import (
    CiboSovereignCeilingDecisionReceipt,
    CiboSovereignCeilingSettlementReceipt,
)

_TURTLE_NET_010_TRADER_IDS = frozenset(
    {
        "R34_XAUUSD",
        "R38_EURUSD",
        "R43_GBPUSD",
        "R38_GBPJPY",
        "R42_AUDJPY",
    }
)
_TURTLE_EMBEDDED_RESEARCH_FRICTION_R = Decimal("0.10")


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CiboCapitalManagementError(f"{name} must be a mapping")
    return value


def _decimal(value: object, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            f"{name} must be Decimal-compatible"
        ) from error
    if not result.is_finite():
        raise CiboCapitalManagementError(f"{name} must be finite")
    return result


def _datetime(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(f"{name} must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")
    return result


def _canonical_exit_reason(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CiboCapitalManagementError(
            "manifest settlement exit_reason is required"
        )
    return value.strip().upper().replace("-", "_")


def _structural_gross_r(
    *,
    trader_id: str,
    encoded_outcome_r: Decimal,
) -> tuple[Decimal, Decimal]:
    """Decode frozen outcome semantics without changing the Trader outcome."""

    if trader_id not in _TURTLE_NET_010_TRADER_IDS:
        return encoded_outcome_r, Decimal(0)
    with localcontext() as context:
        context.prec = 100
        normalization = _TURTLE_EMBEDDED_RESEARCH_FRICTION_R
        return encoded_outcome_r + normalization, normalization


def _sha256(payload: Mapping[str, object]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CiboManifestOutcomeSettlement:
    signal_fingerprint: str
    trader_id: str
    entry_at: datetime
    exit_at: datetime
    exit_reason: str
    gross_structural_outcome_r: Decimal
    provider_cost_usd: Decimal
    gross_pnl_usd: Decimal
    realized_net_pnl_usd: Decimal
    receipt: CiboSovereignCeilingSettlementReceipt

    def __post_init__(self) -> None:
        if (
            not self.signal_fingerprint
            or not self.trader_id
            or not self.exit_reason
        ):
            raise CiboCapitalManagementError(
                "manifest settlement identity is required"
            )
        if (
            self.entry_at.tzinfo is None
            or self.entry_at.utcoffset() is None
            or self.exit_at.tzinfo is None
            or self.exit_at.utcoffset() is None
            or self.exit_at < self.entry_at
        ):
            raise CiboCapitalManagementError(
                "manifest settlement chronology is invalid"
            )
        for name in (
            "gross_structural_outcome_r",
            "provider_cost_usd",
            "gross_pnl_usd",
            "realized_net_pnl_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"manifest settlement {name} must be finite Decimal"
                )
        if self.provider_cost_usd < 0:
            raise CiboCapitalManagementError(
                "manifest settlement provider cost cannot be negative"
            )
        if not isinstance(
            self.receipt,
            CiboSovereignCeilingSettlementReceipt,
        ):
            raise CiboCapitalManagementError(
                "manifest settlement receipt must be canonical"
            )


def manifest_row_to_sovereign_settlement(
    *,
    row: Mapping[str, Any],
    decision: CiboSovereignCeilingDecisionReceipt,
) -> CiboManifestOutcomeSettlement:
    """Apply one postdecision structural outcome to sovereign authorized size."""

    if not isinstance(decision, CiboSovereignCeilingDecisionReceipt):
        raise CiboCapitalManagementError(
            "manifest settlement requires canonical sovereign decision"
        )
    if decision.risk_decision not in {
        RiskDecision.ALLOW.value,
        RiskDecision.REDUCE.value,
    }:
        raise CiboCapitalManagementError(
            "manifest settlement requires Risk-authorized decision"
        )
    if (
        str(row.get("signal_fingerprint", ""))
        != decision.signal_fingerprint
        or str(row.get("trader_id", "")) != decision.trader_id
    ):
        raise CiboCapitalManagementError(
            "manifest settlement decision lineage drift"
        )
    if row.get("outcome_available_to_predecision") is not False:
        raise CiboCapitalManagementError(
            "manifest settlement predecision outcome flag must be false"
        )

    outcome = _mapping(
        row.get("settlement_outcome_research_only"),
        "settlement_outcome_research_only",
    )
    if (
        outcome.get("not_available_to_predecision") is not True
        or outcome.get("used_for_decision") is not False
    ):
        raise CiboCapitalManagementError(
            "manifest outcome governance flags are invalid"
        )
    entry_at = _datetime(outcome.get("entry_at"), "outcome entry_at")
    exit_at = _datetime(outcome.get("exit_at"), "outcome exit_at")
    exit_reason = _canonical_exit_reason(outcome.get("exit_reason"))
    if entry_at < decision.decided_at or exit_at < decision.decided_at:
        raise CiboCapitalManagementError(
            "manifest settlement cannot predate sovereign decision"
        )

    encoded_outcome_r = _decimal(
        outcome.get("gross_structural_outcome_r"),
        "gross_structural_outcome_r",
    )
    gross_r, structural_normalization_r = _structural_gross_r(
        trader_id=decision.trader_id,
        encoded_outcome_r=encoded_outcome_r,
    )
    provider_cost_per_volume = (
        manifest_row_provider_cost_per_volume_usd(row)
    )
    with localcontext() as context:
        context.prec = 100
        provider_cost = (
            provider_cost_per_volume * decision.authorized_volume
        )
        gross_pnl = gross_r * decision.authorized_stop_risk_usd
        net_pnl = gross_pnl - provider_cost
    digest_payload = {
        "signal_fingerprint": decision.signal_fingerprint,
        "trader_id": decision.trader_id,
        "decision_id": decision.decision_id,
        "entry_at": entry_at.isoformat(),
        "exit_at": exit_at.isoformat(),
        "exit_reason": exit_reason,
        "encoded_source_outcome_r": format(encoded_outcome_r, "f"),
        "structural_normalization_r": format(
            structural_normalization_r,
            "f",
        ),
        "gross_structural_outcome_r": format(gross_r, "f"),
        "authorized_volume": format(decision.authorized_volume, "f"),
        "authorized_stop_risk_usd": format(
            decision.authorized_stop_risk_usd,
            "f",
        ),
        "provider_cost_per_volume_usd": format(
            provider_cost_per_volume,
            "f",
        ),
        "provider_cost_usd": format(provider_cost, "f"),
        "realized_net_pnl_usd": format(net_pnl, "f"),
        "outcome_available_to_predecision": False,
    }
    receipt = CiboSovereignCeilingSettlementReceipt(
        signal_fingerprint=decision.signal_fingerprint,
        trader_id=decision.trader_id,
        settled_at=exit_at,
        realized_net_pnl_usd=net_pnl,
        settlement_sha256=_sha256(digest_payload),
        outcome_available_to_predecision=False,
    )
    return CiboManifestOutcomeSettlement(
        signal_fingerprint=decision.signal_fingerprint,
        trader_id=decision.trader_id,
        entry_at=entry_at,
        exit_at=exit_at,
        exit_reason=exit_reason,
        gross_structural_outcome_r=gross_r,
        provider_cost_usd=provider_cost,
        gross_pnl_usd=gross_pnl,
        realized_net_pnl_usd=net_pnl,
        receipt=receipt,
    )
