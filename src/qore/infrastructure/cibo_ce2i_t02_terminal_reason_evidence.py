"""Explicit terminal-reason evidence for CE2I T02 fresh OOS.

T02 stop-incidence research must never infer a stop from negative PnL, exit
price proximity, or a generic protection-order type. A structural-stop label is
accepted only from an explicit terminal reason with immutable lineage.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.client_position_lifecycle import (
    ClientPositionExitReason,
)


class T02TerminalReason(StrEnum):
    STRUCTURAL_STOP = "STRUCTURAL_STOP"
    TAKE_PROFIT = "TAKE_PROFIT"
    CORE_POLICY_EXIT = "CORE_POLICY_EXIT"
    AUTHORIZED_MANUAL = "AUTHORIZED_MANUAL"
    PROVIDER_STOP_OUT = "PROVIDER_STOP_OUT"
    OTHER_EXPLICIT = "OTHER_EXPLICIT"


class T02TerminalReasonSource(StrEnum):
    QORE_POSITION_LIFECYCLE = "QORE_POSITION_LIFECYCLE"
    PROVIDER_NATIVE_EXPLICIT = "PROVIDER_NATIVE_EXPLICIT"


@dataclass(frozen=True, slots=True)
class T02TerminalReasonEvidence:
    evidence_id: str
    decision_evidence_sha256: str
    signal_fingerprint: str
    position_id: int
    settlement_deal_ids: tuple[int, ...]
    reason: T02TerminalReason
    source: T02TerminalReasonSource
    source_ref: str
    observed_at: datetime
    explicit_reason: bool = True
    inferred_from_pnl: bool = False
    inferred_from_price: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.signal_fingerprint or not self.source_ref:
            raise CiboCapitalManagementError(
                "T02 terminal reason identity/source ref required"
            )
        _sha(self.decision_evidence_sha256, "decision_evidence_sha256")
        if (
            not isinstance(self.position_id, int)
            or isinstance(self.position_id, bool)
            or self.position_id <= 0
        ):
            raise CiboCapitalManagementError(
                "T02 terminal reason position_id invalid"
            )
        if (
            not self.settlement_deal_ids
            or len(self.settlement_deal_ids)
            != len(set(self.settlement_deal_ids))
            or any(
                not isinstance(item, int)
                or isinstance(item, bool)
                or item <= 0
                for item in self.settlement_deal_ids
            )
        ):
            raise CiboCapitalManagementError(
                "T02 terminal reason settlement deal ids invalid"
            )
        if type(self.reason) is not T02TerminalReason:
            raise CiboCapitalManagementError(
                "T02 terminal reason enum invalid"
            )
        if type(self.source) is not T02TerminalReasonSource:
            raise CiboCapitalManagementError(
                "T02 terminal reason source invalid"
            )
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise CiboCapitalManagementError(
                "T02 terminal reason observed_at must be timezone-aware"
            )
        for name in (
            "explicit_reason",
            "inferred_from_pnl",
            "inferred_from_price",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T02 terminal reason {name} must be bool"
                )
        if not self.explicit_reason:
            raise CiboCapitalManagementError(
                "T02 terminal reason must be explicit"
            )
        if self.inferred_from_pnl or self.inferred_from_price:
            raise CiboCapitalManagementError(
                "T02 terminal reason cannot be inferred from PnL/price"
            )
        if self.productive_authority:
            raise CiboCapitalManagementError(
                "T02 terminal reason evidence has no productive authority"
            )

    @property
    def stopped_at_structural_stop(self) -> bool:
        return self.reason is T02TerminalReason.STRUCTURAL_STOP

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["reason"] = self.reason.value
        payload["source"] = self.source.value
        payload["observed_at"] = self.observed_at.isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def t02_terminal_reason_from_qore_lifecycle(
    *,
    evidence_id: str,
    decision_evidence_sha256: str,
    signal_fingerprint: str,
    position_id: int,
    settlement_deal_ids: tuple[int, ...],
    exit_reason: ClientPositionExitReason,
    lifecycle_evidence_ref: str,
    observed_at: datetime,
) -> T02TerminalReasonEvidence:
    """Bind QORE's explicit lifecycle exit reason without outcome inference."""

    if type(exit_reason) is not ClientPositionExitReason:
        raise CiboCapitalManagementError(
            "T02 lifecycle exit reason must use canonical enum"
        )
    mapping = {
        ClientPositionExitReason.STOP_LOSS: T02TerminalReason.STRUCTURAL_STOP,
        ClientPositionExitReason.TAKE_PROFIT: T02TerminalReason.TAKE_PROFIT,
        ClientPositionExitReason.CORE_POLICY: T02TerminalReason.CORE_POLICY_EXIT,
        ClientPositionExitReason.AUTHORIZED_MANUAL: (
            T02TerminalReason.AUTHORIZED_MANUAL
        ),
    }
    return T02TerminalReasonEvidence(
        evidence_id=evidence_id,
        decision_evidence_sha256=decision_evidence_sha256,
        signal_fingerprint=signal_fingerprint,
        position_id=position_id,
        settlement_deal_ids=settlement_deal_ids,
        reason=mapping[exit_reason],
        source=T02TerminalReasonSource.QORE_POSITION_LIFECYCLE,
        source_ref=lifecycle_evidence_ref,
        observed_at=observed_at,
    )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"T02 terminal reason {name} must be canonical SHA-256"
        )
