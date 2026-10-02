"""Canonical four-front terminal recommendation bundle for CIBO Architect 2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_arch2_forward_qualification_reconciliation import (
    build_arch2_forward_qualification_reconciliation,
)
from qore.infrastructure.cibo_arch2_provider_economics_terminal_recommendation import (
    build_provider_economics_terminal_recommendation,
)
from qore.infrastructure.cibo_arch2_t03_current_contract_falsification import (
    T03_CURRENT_CONTRACT_FALSIFICATION,
)
from qore.infrastructure.cibo_arch2_t16_terminal_falsification import (
    T16_TERMINAL_FALSIFICATION_RECEIPT,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

_BUNDLE_ID = "CIBO_ARCH2_TERMINAL_RECOMMENDATION_BUNDLE_V1"
_EXPECTED = (
    ("T03", "FALSIFIED_AND_CLOSED"),
    ("T16", "FALSIFIED_AND_CLOSED"),
    ("PROVIDER_ECONOMICS", "SUPERSEDED_WITH_PROVEN_LINEAGE"),
    ("FORWARD_QUALIFICATION", "SUPERSEDED_WITH_PROVEN_LINEAGE"),
)


@dataclass(frozen=True, slots=True)
class Architect2TerminalRecommendation:
    workstream_id: str
    recommendation: str
    evidence_sha256: str
    integrator_audit_required: bool = True
    canonical_ledger_modified: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if (self.workstream_id, self.recommendation) not in _EXPECTED:
            raise CiboCapitalManagementError(
                "Architect-2 terminal recommendation identity/disposition drift"
            )
        if (
            not self.evidence_sha256.startswith("sha256:")
            or len(self.evidence_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "Architect-2 terminal recommendation evidence digest invalid"
            )
        if (
            not self.integrator_audit_required
            or self.canonical_ledger_modified
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "Architect-2 terminal recommendation authority drift"
            )


@dataclass(frozen=True, slots=True)
class Architect2TerminalRecommendationBundle:
    bundle_id: str
    recommendations: tuple[Architect2TerminalRecommendation, ...]
    canonical_ledger_modified: bool = False
    phase22_v2_consumed: bool = False
    merge_authority: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.bundle_id != _BUNDLE_ID:
            raise CiboCapitalManagementError(
                "Architect-2 terminal bundle identity drift"
            )
        surface = tuple(
            (item.workstream_id, item.recommendation)
            for item in self.recommendations
        )
        if surface != _EXPECTED:
            raise CiboCapitalManagementError(
                "Architect-2 terminal bundle exact four-front surface required"
            )
        if any(
            (
                self.canonical_ledger_modified,
                self.phase22_v2_consumed,
                self.merge_authority,
                self.productive_authority,
            )
        ):
            raise CiboCapitalManagementError(
                "Architect-2 terminal bundle exceeded authority"
            )

    def fingerprint(self) -> str:
        return _fingerprint(asdict(self))


def build_architect2_terminal_recommendation_bundle(
) -> Architect2TerminalRecommendationBundle:
    provider = build_provider_economics_terminal_recommendation()
    forward = build_arch2_forward_qualification_reconciliation()

    if not provider.current_empirical_provider_plane_ready:
        raise CiboCapitalManagementError(
            "Provider Economics terminal recommendation is not evidence-ready"
        )
    if not all(
        (
            forward.old_qualification_plan_bound_as_superseded,
            forward.old_qualification_plan_sha_bound,
            forward.provider_execution_plane_ready,
            forward.dual_evidence_activation_ready,
            forward.frozen_before_holdout_outcomes,
            forward.historical_fill_fabrication_forbidden,
        )
    ):
        raise CiboCapitalManagementError(
            "Forward Qualification terminal recommendation is not evidence-ready"
        )

    return Architect2TerminalRecommendationBundle(
        bundle_id=_BUNDLE_ID,
        recommendations=(
            Architect2TerminalRecommendation(
                workstream_id="T03",
                recommendation=T03_CURRENT_CONTRACT_FALSIFICATION.recommendation,
                evidence_sha256=_fingerprint(
                    asdict(T03_CURRENT_CONTRACT_FALSIFICATION)
                ),
            ),
            Architect2TerminalRecommendation(
                workstream_id="T16",
                recommendation=T16_TERMINAL_FALSIFICATION_RECEIPT.recommendation,
                evidence_sha256=T16_TERMINAL_FALSIFICATION_RECEIPT.fingerprint(),
            ),
            Architect2TerminalRecommendation(
                workstream_id="PROVIDER_ECONOMICS",
                recommendation=provider.recommendation,
                evidence_sha256=_fingerprint(asdict(provider)),
            ),
            Architect2TerminalRecommendation(
                workstream_id="FORWARD_QUALIFICATION",
                recommendation=forward.forward_qualification_recommendation,
                evidence_sha256=_fingerprint(asdict(forward)),
            ),
        ),
    )


def _fingerprint(payload: Any) -> str:
    raw = json.dumps(
        _canonical(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


ARCHITECT2_TERMINAL_RECOMMENDATION_BUNDLE = (
    build_architect2_terminal_recommendation_bundle()
)
