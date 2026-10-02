"""A2 Phase22 receipt for the INTERNAL_CAPITAL_MARKET cross-lane boundary.

GEN-C6 belongs to A1 as a hypothesis, while the global INTERNAL_CAPITAL_MARKET
engine belongs to A2. This module emits a read-only receipt proving that a
Phase22-bound scarcity population used the frozen GEN-C6 policy without capital
creation, double spend, or runtime authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from decimal import Decimal

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_internal_capital_market import (
    GENC6_POLICY_ID,
    Genc6InternalCapitalMarketDecision,
    genc6_policy_sha256,
)

RECEIPT_ID = "CIBO_A2_INTERNAL_CAPITAL_MARKET_PHASE22_RECEIPT_V1"
SOURCE_WORKSTREAM = "INTERNAL_CAPITAL_MARKET"
_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _sha(value: str, name: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"A2 internal capital market {name} must be canonical SHA-256"
        )


@dataclass(frozen=True, slots=True)
class A2InternalCapitalMarketPhase22Receipt:
    receipt_id: str
    source_workstream: str
    source_head: str
    artifact_sha256: str
    canonical_phase22_manifest_sha256: str
    source_population_sha256: str
    decision_population_sha256: str
    policy_id: str
    policy_sha256: str
    decision_count: int
    true_scarcity_decision_count: int
    exact_policy_identity: bool
    true_scarcity_binding: bool
    capital_conservation_proven: bool
    double_spend_detected: bool
    outcome_freeze_preserved: bool
    productive_authority: bool = False
    live_authorized: bool = False
    real_capital_authorized: bool = False
    integration_authority: bool = False
    a1_closes_source_workstream: bool = False

    def __post_init__(self) -> None:
        if self.receipt_id != RECEIPT_ID:
            raise CiboCompoundCapitalError(
                "A2 internal capital market receipt identity drift"
            )
        if self.source_workstream != SOURCE_WORKSTREAM:
            raise CiboCompoundCapitalError(
                "A2 internal capital market source workstream drift"
            )
        if _SHA1_RE.fullmatch(self.source_head) is None:
            raise CiboCompoundCapitalError(
                "A2 internal capital market source HEAD invalid"
            )
        for name in (
            "artifact_sha256",
            "canonical_phase22_manifest_sha256",
            "source_population_sha256",
            "decision_population_sha256",
            "policy_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.policy_id != GENC6_POLICY_ID:
            raise CiboCompoundCapitalError(
                "A2 internal capital market policy identity drift"
            )
        if self.policy_sha256 != genc6_policy_sha256():
            raise CiboCompoundCapitalError(
                "A2 internal capital market policy digest drift"
            )
        if (
            not isinstance(self.decision_count, int)
            or isinstance(self.decision_count, bool)
            or self.decision_count <= 0
            or self.true_scarcity_decision_count != self.decision_count
        ):
            raise CiboCompoundCapitalError(
                "A2 internal capital market requires non-empty true-scarcity population"
            )
        required_true = (
            self.exact_policy_identity,
            self.true_scarcity_binding,
            self.capital_conservation_proven,
            self.outcome_freeze_preserved,
        )
        prohibited = (
            self.double_spend_detected,
            self.productive_authority,
            self.live_authorized,
            self.real_capital_authorized,
            self.integration_authority,
            self.a1_closes_source_workstream,
        )
        if not all(required_true) or any(prohibited):
            raise CiboCompoundCapitalError(
                "A2 internal capital market receipt governance/science incomplete"
            )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def build_a2_internal_capital_market_phase22_receipt(
    *,
    decisions: tuple[Genc6InternalCapitalMarketDecision, ...],
    source_head: str,
    artifact_sha256: str,
    canonical_phase22_manifest_sha256: str,
    source_population_sha256: str,
) -> A2InternalCapitalMarketPhase22Receipt:
    """Bind a frozen true-scarcity decision population for A1 read-only use."""

    if (
        not isinstance(decisions, tuple)
        or not decisions
        or any(
            not isinstance(item, Genc6InternalCapitalMarketDecision)
            for item in decisions
        )
    ):
        raise CiboCompoundCapitalError(
            "A2 internal capital market requires canonical decision tuple"
        )
    if _SHA1_RE.fullmatch(source_head) is None:
        raise CiboCompoundCapitalError(
            "A2 internal capital market source HEAD invalid"
        )
    for value, name in (
        (artifact_sha256, "artifact_sha256"),
        (canonical_phase22_manifest_sha256, "canonical_phase22_manifest_sha256"),
        (source_population_sha256, "source_population_sha256"),
    ):
        _sha(value, name)

    decision_ids = tuple(item.decision_id for item in decisions)
    if len(decision_ids) != len(set(decision_ids)):
        raise CiboCompoundCapitalError(
            "A2 internal capital market duplicate decision identity"
        )

    for item in decisions:
        if (
            item.policy_id != GENC6_POLICY_ID
            or item.policy_sha256 != genc6_policy_sha256()
        ):
            raise CiboCompoundCapitalError(
                "A2 internal capital market decision policy drift"
            )
        if not item.true_scarcity:
            raise CiboCompoundCapitalError(
                "A2 internal capital market Phase22 receipt accepts true scarcity only"
            )
        if item.outcome_present_at_seal:
            raise CiboCompoundCapitalError(
                "A2 internal capital market decision used outcome at seal"
            )
        if any(
            (
                item.runtime_authority,
                item.risk_authority,
                item.execution_authority,
                item.live_authority,
                item.real_capital_authority,
            )
        ):
            raise CiboCompoundCapitalError(
                "A2 internal capital market decision grants forbidden authority"
            )
        for amount in (
            item.control_amount_usd,
            item.treatment_amount_usd,
            item.reserve_amount_usd,
        ):
            if (
                not isinstance(amount, Decimal)
                or not amount.is_finite()
                or amount < 0
                or amount > item.available_capital_usd
            ):
                raise CiboCompoundCapitalError(
                    "A2 internal capital market capital conservation violated"
                )

    population_payload = [
        {
            "decision_id": item.decision_id,
            "scarcity_event_id": item.scarcity_event_id,
            "decision_at": item.decision_at.isoformat(),
            "candidate_set_sha256": item.candidate_set_sha256,
            "legal_action_set_sha256": item.legal_action_set_sha256,
            "portfolio_state_sha256": item.portfolio_state_sha256,
            "t19_ledger_sha256": item.t19_ledger_sha256,
            "available_capital_usd": format(item.available_capital_usd, "f"),
            "control_action": item.control_action.value,
            "control_candidate_id": item.control_candidate_id,
            "control_amount_usd": format(item.control_amount_usd, "f"),
            "treatment_action": item.treatment_action.value,
            "treatment_candidate_id": item.treatment_candidate_id,
            "treatment_amount_usd": format(item.treatment_amount_usd, "f"),
            "reserve_amount_usd": format(item.reserve_amount_usd, "f"),
            "true_scarcity": item.true_scarcity,
            "policy_sha256": item.policy_sha256,
        }
        for item in sorted(decisions, key=lambda row: (row.decision_at, row.decision_id))
    ]
    raw = json.dumps(
        population_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    decision_population_sha256 = "sha256:" + hashlib.sha256(raw).hexdigest()

    return A2InternalCapitalMarketPhase22Receipt(
        receipt_id=RECEIPT_ID,
        source_workstream=SOURCE_WORKSTREAM,
        source_head=source_head,
        artifact_sha256=artifact_sha256,
        canonical_phase22_manifest_sha256=canonical_phase22_manifest_sha256,
        source_population_sha256=source_population_sha256,
        decision_population_sha256=decision_population_sha256,
        policy_id=GENC6_POLICY_ID,
        policy_sha256=genc6_policy_sha256(),
        decision_count=len(decisions),
        true_scarcity_decision_count=len(decisions),
        exact_policy_identity=True,
        true_scarcity_binding=True,
        capital_conservation_proven=True,
        double_spend_detected=False,
        outcome_freeze_preserved=True,
    )
