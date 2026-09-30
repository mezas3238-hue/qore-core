"""Canonical Phase20D capital/Risk snapshot binding.

Forward qualification must bind the exact current state consumed by CIBO rather
than trusting caller-supplied labels. This module derives deterministic SHA-256
identities from the durable CIBO capital ledger and the reconciled sovereign
Risk snapshot/envelope.

Research-only. It performs no capital reservation, Risk authorization or broker
mutation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

from qore.infrastructure.account_wide_risk import (
    AccountRiskSnapshot,
    RiskCapitalConstraintEnvelope,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_capital_source_ledger_store import (
    VersionedCapitalSourceLedger,
)


@dataclass(frozen=True, slots=True)
class Phase20ForwardSnapshotBundle:
    capital_snapshot_id: str
    capital_snapshot_observed_at: datetime
    risk_snapshot_id: str
    risk_snapshot_observed_at: datetime
    hard_risk_headroom_usd: Decimal
    margin_headroom_usd: Decimal

    def __post_init__(self) -> None:
        for name in ("capital_snapshot_id", "risk_snapshot_id"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.startswith("sha256:")
                or len(value) != 71
            ):
                raise CiboCapitalManagementError(
                    f"Phase20D {name} must be canonical SHA-256 identity"
                )
        for name in (
            "capital_snapshot_observed_at",
            "risk_snapshot_observed_at",
        ):
            _aware(getattr(self, name), name=name)
        for name in ("hard_risk_headroom_usd", "margin_headroom_usd"):
            value = getattr(self, name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Phase20D {name} must be finite non-negative Decimal"
                )


def build_phase20_forward_snapshot_bundle(
    *,
    account_snapshot: AccountRiskSnapshot,
    risk_constraints: RiskCapitalConstraintEnvelope,
    capital_state: VersionedCapitalSourceLedger,
    captured_at: datetime,
) -> Phase20ForwardSnapshotBundle:
    """Bind current capital and Risk state to deterministic content digests."""

    if not isinstance(account_snapshot, AccountRiskSnapshot):
        raise CiboCapitalManagementError(
            "Phase20D account snapshot must be AccountRiskSnapshot"
        )
    if not isinstance(risk_constraints, RiskCapitalConstraintEnvelope):
        raise CiboCapitalManagementError(
            "Phase20D Risk constraints must be canonical envelope"
        )
    if not isinstance(capital_state, VersionedCapitalSourceLedger):
        raise CiboCapitalManagementError(
            "Phase20D capital state must be versioned durable ledger"
        )
    _aware(captured_at, name="captured_at")
    if risk_constraints.account_binding_id != account_snapshot.account_binding_id:
        raise CiboCapitalManagementError(
            "Phase20D Risk/account binding mismatch"
        )
    if risk_constraints.reconciled_at != account_snapshot.reconciled_at:
        raise CiboCapitalManagementError(
            "Phase20D Risk/account reconciliation timestamp mismatch"
        )
    if captured_at < account_snapshot.reconciled_at:
        raise CiboCapitalManagementError(
            "Phase20D capture cannot predate reconciled account state"
        )

    capital_payload = {
        "schema": "CIBO_PHASE20D_CAPITAL_SNAPSHOT_V1",
        "generation": capital_state.generation,
        "captured_at": captured_at.isoformat(),
        "accounts": [
            {
                "source_id": item.source_id,
                "source": item.source.value,
                "proven_amount_usd": _decimal(item.proven_amount_usd),
                "reserved_usd": _decimal(item.reserved_usd),
                "deployed_usd": _decimal(item.deployed_usd),
                "consumed_usd": _decimal(item.consumed_usd),
                "cumulative_released_usd": _decimal(
                    item.cumulative_released_usd
                ),
            }
            for item in sorted(
                capital_state.ledger.accounts,
                key=lambda item: item.source_id,
            )
        ],
        "reservations": [
            {
                "reservation_id": item.reservation_id,
                "source_id": item.source_id,
                "amount_usd": _decimal(item.amount_usd),
                "state": item.state.value,
                "returned_capacity_usd": _decimal(
                    item.returned_capacity_usd
                ),
                "consumed_capacity_usd": _decimal(
                    item.consumed_capacity_usd
                ),
            }
            for item in sorted(
                capital_state.ledger.reservations,
                key=lambda item: item.reservation_id,
            )
        ],
    }
    provider = account_snapshot.provider_budget
    risk_payload = {
        "schema": "CIBO_PHASE20D_RISK_SNAPSHOT_V1",
        "account": {
            "account_binding_id": account_snapshot.account_binding_id,
            "equity": _decimal(account_snapshot.equity),
            "margin_used": _decimal(account_snapshot.margin_used),
            "free_margin": _decimal(account_snapshot.free_margin),
            "open_stop_worst_case_loss": _decimal(
                account_snapshot.open_stop_worst_case_loss
            ),
            "open_floating_loss": _decimal(
                account_snapshot.open_floating_loss
            ),
            "pending_broker_worst_case_loss": _decimal(
                account_snapshot.pending_broker_worst_case_loss
            ),
            "qore_authorizable_headroom": _decimal(
                account_snapshot.qore_authorizable_headroom
            ),
            "provider_budget": {
                "provider_headroom": _decimal(provider.provider_headroom),
                "max_risk_at_any_time": _decimal(
                    provider.max_risk_at_any_time
                ),
                "active_mll": _decimal(provider.active_mll),
                "hard_breach": provider.hard_breach,
            },
            "reconciled_at": account_snapshot.reconciled_at.isoformat(),
        },
        "constraints": {
            "account_binding_id": risk_constraints.account_binding_id,
            "aggregate_pre_order_worst_case_usd": _decimal(
                risk_constraints.aggregate_pre_order_worst_case_usd
            ),
            "active_reserved_stop_risk_usd": _decimal(
                risk_constraints.active_reserved_stop_risk_usd
            ),
            "active_reserved_margin_usd": _decimal(
                risk_constraints.active_reserved_margin_usd
            ),
            "provider_remaining_headroom_usd": _decimal(
                risk_constraints.provider_remaining_headroom_usd
            ),
            "internal_qore_remaining_headroom_usd": _decimal(
                risk_constraints.internal_qore_remaining_headroom_usd
            ),
            "max_risk_remaining_usd": _decimal(
                risk_constraints.max_risk_remaining_usd
            ),
            "hard_risk_headroom_usd": _decimal(
                risk_constraints.hard_risk_headroom_usd
            ),
            "margin_headroom_usd": _decimal(
                risk_constraints.margin_headroom_usd
            ),
            "provider_hard_breach": risk_constraints.provider_hard_breach,
            "survival_blocked": risk_constraints.survival_blocked,
            "reason": risk_constraints.reason,
            "reconciled_at": risk_constraints.reconciled_at.isoformat(),
        },
    }
    return Phase20ForwardSnapshotBundle(
        capital_snapshot_id=_payload_sha256(capital_payload),
        capital_snapshot_observed_at=captured_at,
        risk_snapshot_id=_payload_sha256(risk_payload),
        risk_snapshot_observed_at=account_snapshot.reconciled_at,
        hard_risk_headroom_usd=risk_constraints.hard_risk_headroom_usd,
        margin_headroom_usd=risk_constraints.margin_headroom_usd,
    )


def _payload_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"


def _decimal(value: Decimal) -> str:
    return format(value, "f")


def _aware(value: datetime, *, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"Phase20D {name} must be timezone-aware"
        )
