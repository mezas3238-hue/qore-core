"""GEN-C13 governed meta-capital memory and counterfactual skeptic.

GEN-C13 reuses the existing CiboMemoryStore. It records post-outcome capital
episodes with immutable decision provenance and permits counterfactual research
only after the real outcome is reconciled. Counterfactuals cannot rewrite
historical decisions, identify causal effects by assumption or mutate a
productive policy.

Research/shadow only. No sizing, Risk, execution, LIVE or promotion authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import NAMESPACE_URL, uuid5

from qore.infrastructure.account_wide_risk import (
    TraderIdentity,
    canonical_trader_identity,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_executive_memory import (
    CiboMemoryFreshness,
    CiboMemoryFreshnessState,
    CiboMemoryItem,
    CiboMemoryKind,
    CiboMemoryProvenance,
    CiboMemorySourceRef,
)
from qore.modules.cibo.cognitive_contracts import CiboCognitiveEvidenceRef

GENC13_POLICY_ID = "CIBO_GENC13_META_CAPITAL_MEMORY_SKEPTIC_V1"
GENC13_FROZEN_AT = datetime(2026, 9, 30, 7, 50, tzinfo=UTC)
GENC13_POLICY_SHA256 = (
    "sha256:237b3f87efa82570eab3155fa9f72cc1add404a019d4d101faae3467a32fc793"
)


class Genc13CapitalPhenotype(StrEnum):
    OVERCOMPOUNDING = "OVERCOMPOUNDING"
    UNDERCOMPOUNDING = "UNDERCOMPOUNDING"
    PREMATURE_EXPANSION = "PREMATURE_EXPANSION"
    LATE_EXPANSION = "LATE_EXPANSION"
    EXCESS_RESERVE = "EXCESS_RESERVE"
    INSUFFICIENT_RESERVE = "INSUFFICIENT_RESERVE"
    CAPITAL_CONCENTRATION = "CAPITAL_CONCENTRATION"
    OPTIONALITY_DESTRUCTION = "OPTIONALITY_DESTRUCTION"
    PROFIT_GIVEBACK = "PROFIT_GIVEBACK"
    CAPITAL_STARVATION = "CAPITAL_STARVATION"
    CAPITAL_WASTE = "CAPITAL_WASTE"
    PREMATURE_RELEASE = "PREMATURE_RELEASE"
    LATE_RELEASE = "LATE_RELEASE"
    SUCCESSFUL_EXPANSION = "SUCCESSFUL_EXPANSION"


class Genc13CounterfactualKind(StrEnum):
    DEPLOY_LESS = "DEPLOY_LESS"
    DEPLOY_MORE = "DEPLOY_MORE"
    RESERVE_INSTEAD = "RESERVE_INSTEAD"
    COMPOUND_EARLIER = "COMPOUND_EARLIER"
    COMPOUND_LATER = "COMPOUND_LATER"
    FLOOR_EARLIER = "FLOOR_EARLIER"
    FLOOR_LATER = "FLOOR_LATER"
    RELEASE_EARLIER = "RELEASE_EARLIER"
    RELEASE_LATER = "RELEASE_LATER"


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCapitalManagementError(
            f"GEN-C13 {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"GEN-C13 {name} must be canonical SHA-256"
        )


def _finite(value: Decimal, name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCapitalManagementError(
            f"GEN-C13 {name} must be finite Decimal"
        )


def _nonnegative(value: Decimal, name: str) -> None:
    _finite(value, name)
    if value < 0:
        raise CiboCapitalManagementError(
            f"GEN-C13 {name} must be non-negative"
        )


@dataclass(frozen=True, slots=True)
class Genc13CapitalEpisode:
    episode_id: str
    account_identity: CiboAccountCapitalIdentity
    trader_id: TraderIdentity
    decision_id: str
    decision_sha256: str
    decision_at: datetime
    outcome_at: datetime
    outcome_sha256: str
    capital_state_before_sha256: str
    capital_state_after_sha256: str
    action_code: str
    allocated_capital_usd: Decimal
    peak_plausible_loss_usd: Decimal
    capital_minutes: Decimal
    realized_pnl_usd: Decimal
    decision_frozen_before_outcome: bool = True
    outcome_reconciled: bool = True
    historical_decision_mutated: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.episode_id or not self.decision_id or not self.action_code:
            raise CiboCapitalManagementError(
                "GEN-C13 episode identity/action is required"
            )
        if not isinstance(
            self.account_identity,
            CiboAccountCapitalIdentity,
        ):
            raise CiboCapitalManagementError(
                "GEN-C13 episode account identity is invalid"
            )
        canonical_trader_identity(self.trader_id)
        _aware(self.decision_at, "decision_at")
        _aware(self.outcome_at, "outcome_at")
        if self.outcome_at <= self.decision_at:
            raise CiboCapitalManagementError(
                "GEN-C13 outcome must follow frozen decision"
            )
        for name in (
            "decision_sha256",
            "outcome_sha256",
            "capital_state_before_sha256",
            "capital_state_after_sha256",
        ):
            _sha(getattr(self, name), name)
        for name in (
            "allocated_capital_usd",
            "peak_plausible_loss_usd",
            "capital_minutes",
        ):
            _nonnegative(getattr(self, name), name)
        _finite(self.realized_pnl_usd, "realized_pnl_usd")
        if self.capital_minutes <= 0:
            raise CiboCapitalManagementError(
                "GEN-C13 capital_minutes must be positive"
            )
        for name in (
            "decision_frozen_before_outcome",
            "outcome_reconciled",
            "historical_decision_mutated",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"GEN-C13 episode {name} must be bool"
                )
        if (
            not self.decision_frozen_before_outcome
            or not self.outcome_reconciled
            or self.historical_decision_mutated
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "GEN-C13 episode provenance/governance drift"
            )

    def fingerprint(self) -> str:
        payload = {
            "episode_id": self.episode_id,
            "account": {
                "provider_key": self.account_identity.provider_key,
                "account_ref": self.account_identity.account_ref,
                "environment": self.account_identity.environment.value,
                "provider_program": self.account_identity.provider_program,
            },
            "trader_id": canonical_trader_identity(self.trader_id),
            "decision_id": self.decision_id,
            "decision_sha256": self.decision_sha256,
            "decision_at": self.decision_at.isoformat(),
            "outcome_at": self.outcome_at.isoformat(),
            "outcome_sha256": self.outcome_sha256,
            "capital_state_before_sha256": self.capital_state_before_sha256,
            "capital_state_after_sha256": self.capital_state_after_sha256,
            "action_code": self.action_code,
            "allocated_capital_usd": format(self.allocated_capital_usd, "f"),
            "peak_plausible_loss_usd": format(
                self.peak_plausible_loss_usd,
                "f",
            ),
            "capital_minutes": format(self.capital_minutes, "f"),
            "realized_pnl_usd": format(self.realized_pnl_usd, "f"),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class Genc13PhenotypeEvidence:
    phenotype: Genc13CapitalPhenotype
    evidence_sha256: str
    identified_at: datetime
    causal_attribution_claimed: bool = False

    def __post_init__(self) -> None:
        if type(self.phenotype) is not Genc13CapitalPhenotype:
            raise CiboCapitalManagementError(
                "GEN-C13 phenotype is invalid"
            )
        _sha(self.evidence_sha256, "phenotype evidence_sha256")
        _aware(self.identified_at, "phenotype identified_at")
        if type(self.causal_attribution_claimed) is not bool:
            raise CiboCapitalManagementError(
                "GEN-C13 phenotype causal_attribution_claimed must be bool"
            )
        if self.causal_attribution_claimed:
            raise CiboCapitalManagementError(
                "GEN-C13 phenotype cannot assume causal attribution"
            )


@dataclass(frozen=True, slots=True)
class Genc13CounterfactualStudy:
    study_id: str
    episode_id: str
    kind: Genc13CounterfactualKind
    created_at: datetime
    simulation_evidence_sha256: str
    counterfactual_decision_sha256: str
    ending_capital_delta_usd: Decimal
    max_drawdown_delta_usd: Decimal
    optionality_delta_usd: Decimal
    post_outcome_research: bool = True
    causal_effect_identified: bool = False
    historical_decision_rewritten: bool = False
    production_recommendation: bool = False
    config_mutation_authority: bool = False

    def __post_init__(self) -> None:
        if not self.study_id or not self.episode_id:
            raise CiboCapitalManagementError(
                "GEN-C13 counterfactual identity is required"
            )
        if type(self.kind) is not Genc13CounterfactualKind:
            raise CiboCapitalManagementError(
                "GEN-C13 counterfactual kind is invalid"
            )
        _aware(self.created_at, "counterfactual created_at")
        _sha(
            self.simulation_evidence_sha256,
            "simulation_evidence_sha256",
        )
        _sha(
            self.counterfactual_decision_sha256,
            "counterfactual_decision_sha256",
        )
        for name in (
            "ending_capital_delta_usd",
            "max_drawdown_delta_usd",
            "optionality_delta_usd",
        ):
            _finite(getattr(self, name), name)
        for name in (
            "post_outcome_research",
            "causal_effect_identified",
            "historical_decision_rewritten",
            "production_recommendation",
            "config_mutation_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"GEN-C13 counterfactual {name} must be bool"
                )
        if (
            not self.post_outcome_research
            or self.causal_effect_identified
            or self.historical_decision_rewritten
            or self.production_recommendation
            or self.config_mutation_authority
        ):
            raise CiboCapitalManagementError(
                "GEN-C13 counterfactual governance drift"
            )


@dataclass(frozen=True, slots=True)
class Genc13SkepticReport:
    report_id: str
    episode: Genc13CapitalEpisode
    phenotypes: tuple[Genc13PhenotypeEvidence, ...]
    counterfactuals: tuple[Genc13CounterfactualStudy, ...]
    generated_at: datetime
    hypothesis_worth_preregistering: bool
    winning_counterfactual_id: None = None
    historical_policy_mutated: bool = False
    automatic_promotion: bool = False
    productive_authority: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if not self.report_id:
            raise CiboCapitalManagementError(
                "GEN-C13 skeptic report identity is required"
            )
        if not isinstance(self.episode, Genc13CapitalEpisode):
            raise CiboCapitalManagementError(
                "GEN-C13 skeptic report episode is invalid"
            )
        _aware(self.generated_at, "report generated_at")
        if self.generated_at < self.episode.outcome_at:
            raise CiboCapitalManagementError(
                "GEN-C13 skeptic report must be post-outcome"
            )
        if any(
            not isinstance(item, Genc13PhenotypeEvidence)
            for item in self.phenotypes
        ):
            raise CiboCapitalManagementError(
                "GEN-C13 skeptic phenotype evidence is invalid"
            )
        phenotype_ids = tuple(item.phenotype for item in self.phenotypes)
        if len(phenotype_ids) != len(set(phenotype_ids)):
            raise CiboCapitalManagementError(
                "GEN-C13 skeptic phenotypes must be unique"
            )
        if any(
            item.identified_at < self.episode.outcome_at
            for item in self.phenotypes
        ):
            raise CiboCapitalManagementError(
                "GEN-C13 phenotype cannot predate reconciled outcome"
            )
        if any(
            not isinstance(item, Genc13CounterfactualStudy)
            for item in self.counterfactuals
        ):
            raise CiboCapitalManagementError(
                "GEN-C13 skeptic counterfactual is invalid"
            )
        study_ids = tuple(item.study_id for item in self.counterfactuals)
        if len(study_ids) != len(set(study_ids)):
            raise CiboCapitalManagementError(
                "GEN-C13 counterfactual ids must be unique"
            )
        if any(
            item.episode_id != self.episode.episode_id
            or item.created_at < self.episode.outcome_at
            for item in self.counterfactuals
        ):
            raise CiboCapitalManagementError(
                "GEN-C13 counterfactual must bind post-outcome episode"
            )
        if type(self.hypothesis_worth_preregistering) is not bool:
            raise CiboCapitalManagementError(
                "GEN-C13 preregistration flag must be bool"
            )
        for name in (
            "historical_policy_mutated",
            "automatic_promotion",
            "productive_authority",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"GEN-C13 skeptic report {name} must be bool"
                )
        if (
            self.winning_counterfactual_id is not None
            or self.historical_policy_mutated
            or self.automatic_promotion
            or self.productive_authority
            or self.certification_ready
        ):
            raise CiboCapitalManagementError(
                "GEN-C13 skeptic report cannot select/promote/mutate"
            )


def build_genc13_memory_item(
    *,
    report: Genc13SkepticReport,
    recorded_at: datetime,
) -> CiboMemoryItem:
    """Export one report into the existing governed executive memory."""

    if not isinstance(report, Genc13SkepticReport):
        raise CiboCapitalManagementError(
            "GEN-C13 memory export requires skeptic report"
        )
    _aware(recorded_at, "memory recorded_at")
    if recorded_at < report.generated_at:
        raise CiboCapitalManagementError(
            "GEN-C13 memory cannot predate skeptic report"
        )
    failure_phenotypes = {
        Genc13CapitalPhenotype.OVERCOMPOUNDING,
        Genc13CapitalPhenotype.PREMATURE_EXPANSION,
        Genc13CapitalPhenotype.INSUFFICIENT_RESERVE,
        Genc13CapitalPhenotype.CAPITAL_CONCENTRATION,
        Genc13CapitalPhenotype.OPTIONALITY_DESTRUCTION,
        Genc13CapitalPhenotype.PROFIT_GIVEBACK,
        Genc13CapitalPhenotype.CAPITAL_STARVATION,
        Genc13CapitalPhenotype.CAPITAL_WASTE,
        Genc13CapitalPhenotype.PREMATURE_RELEASE,
        Genc13CapitalPhenotype.LATE_RELEASE,
    }
    kind = (
        CiboMemoryKind.FAILURE_LESSON
        if any(
            item.phenotype in failure_phenotypes
            for item in report.phenotypes
        )
        else CiboMemoryKind.ECONOMIC
    )
    report_sha = _report_sha256(report)
    item_id = uuid5(
        NAMESPACE_URL,
        f"qore:cibo:genc13:{report.report_id}:{report_sha}",
    )
    phenotype_codes = ",".join(
        sorted(item.phenotype.value.lower() for item in report.phenotypes)
    ) or "none"
    content = (
        f"capital episode {report.episode.episode_id}; "
        f"action {report.episode.action_code.lower()}; "
        f"phenotypes {phenotype_codes}; "
        "counterfactuals are post-outcome research only"
    )
    evidence_refs = tuple(
        CiboCognitiveEvidenceRef(value=value)
        for value in sorted(
            {
                f"cibo://genc13/episode/{report.episode.fingerprint()[7:]}",
                *(
                    f"cibo://genc13/phenotype/{item.evidence_sha256[7:]}"
                    for item in report.phenotypes
                ),
                *(
                    f"cibo://genc13/counterfactual/"
                    f"{item.simulation_evidence_sha256[7:]}"
                    for item in report.counterfactuals
                ),
            }
        )
    )
    return CiboMemoryItem(
        item_id=item_id,
        kind=kind,
        subject_code="meta-capital",
        content=content,
        provenance=CiboMemoryProvenance(
            source_ref=CiboMemorySourceRef(
                value=f"cibo://genc13/report/{report_sha[7:]}"
            ),
            effective_at=report.episode.outcome_at,
            recorded_at=recorded_at,
        ),
        freshness=CiboMemoryFreshness(
            state=CiboMemoryFreshnessState.CURRENT,
            as_of=recorded_at,
        ),
        evidence_refs=evidence_refs,
        confidence=None,
        limitations=(
            "post-outcome-research-only",
            "no-causal-effect-assumed",
            "no-production-authority",
        ),
    )


def _report_sha256(report: Genc13SkepticReport) -> str:
    payload = {
        "report_id": report.report_id,
        "episode_sha256": report.episode.fingerprint(),
        "phenotypes": [
            {
                "phenotype": item.phenotype.value,
                "evidence_sha256": item.evidence_sha256,
                "identified_at": item.identified_at.isoformat(),
            }
            for item in report.phenotypes
        ],
        "counterfactuals": [
            {
                "study_id": item.study_id,
                "kind": item.kind.value,
                "simulation_evidence_sha256": (
                    item.simulation_evidence_sha256
                ),
                "counterfactual_decision_sha256": (
                    item.counterfactual_decision_sha256
                ),
                "ending_capital_delta_usd": format(
                    item.ending_capital_delta_usd,
                    "f",
                ),
                "max_drawdown_delta_usd": format(
                    item.max_drawdown_delta_usd,
                    "f",
                ),
                "optionality_delta_usd": format(
                    item.optionality_delta_usd,
                    "f",
                ),
            }
            for item in report.counterfactuals
        ],
        "generated_at": report.generated_at.isoformat(),
        "hypothesis_worth_preregistering": (
            report.hypothesis_worth_preregistering
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()
