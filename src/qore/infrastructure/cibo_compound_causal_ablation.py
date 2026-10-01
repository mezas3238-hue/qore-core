"""Fail-closed executable gate for CIBO compound causal ablations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

PROTOCOL_ID = "CIBO_COMPOUND_CAUSAL_ABLATION_PROTOCOL_V1"
PROTOCOL_FROZEN_AT = datetime(2026, 9, 30, 17, 42, 30, tzinfo=UTC)
ROOT_CONTROL_ID = "CIBO_GENERATION_CURRENT_CONTROL_V1"
SEALED_HOLDOUT_ID = "CIBO_USD60_6M_HOLDOUT_2017H1_V1"
PHASE22_V2_FRESH_HOLDOUT_ID = (
    "CIBO_USD60_6M_HOLDOUT_2015-10-19_2016-04-19_V2"
)
_PROTECTED_HOLDOUT_IDS = frozenset(
    {
        SEALED_HOLDOUT_ID,
        PHASE22_V2_FRESH_HOLDOUT_ID,
    }
)
_CANONICAL_FOLDS = ("WF1", "WF2", "WF3", "WF4")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class CausalAblationEvidenceKind(StrEnum):
    FORWARD_OBSERVED = "FORWARD_OBSERVED"


class CompoundCausalMechanism(StrEnum):
    PROFIT_GRADUATION = "PROFIT_GRADUATION"
    MARGINAL_CAPITAL_UTILITY = "MARGINAL_CAPITAL_UTILITY"
    SEQUENTIAL_COMPOUNDING = "SEQUENTIAL_COMPOUNDING"
    INTERNAL_CAPITAL_MARKET = "INTERNAL_CAPITAL_MARKET"
    PROFIT_PRESERVATION = "PROFIT_PRESERVATION"
    ADAPTIVE_COMPOUND_SPEED = "ADAPTIVE_COMPOUND_SPEED"
    ROBUST_GROWTH_RUIN_CAPACITY = "ROBUST_GROWTH_RUIN_CAPACITY"
    CAPITAL_DIGITAL_TWIN_USAGE = "CAPITAL_DIGITAL_TWIN_USAGE"
    MULTI_PERIOD_MPC = "MULTI_PERIOD_MPC"
    CRISIS_CAPITAL_INTELLIGENCE = "CRISIS_CAPITAL_INTELLIGENCE"
    META_CAPITAL_MEMORY = "META_CAPITAL_MEMORY"


_MECHANISM_WORKSTREAM = {
    CompoundCausalMechanism.PROFIT_GRADUATION: "GEN-C2",
    CompoundCausalMechanism.MARGINAL_CAPITAL_UTILITY: "GEN-C4",
    CompoundCausalMechanism.SEQUENTIAL_COMPOUNDING: "GEN-C5",
    CompoundCausalMechanism.INTERNAL_CAPITAL_MARKET: "GEN-C6",
    CompoundCausalMechanism.PROFIT_PRESERVATION: "GEN-C7",
    CompoundCausalMechanism.ADAPTIVE_COMPOUND_SPEED: "GEN-C8",
    CompoundCausalMechanism.ROBUST_GROWTH_RUIN_CAPACITY: "GEN-C9",
    CompoundCausalMechanism.CAPITAL_DIGITAL_TWIN_USAGE: "GEN-C10",
    CompoundCausalMechanism.MULTI_PERIOD_MPC: "GEN-C11",
    CompoundCausalMechanism.CRISIS_CAPITAL_INTELLIGENCE: "GEN-C12",
    CompoundCausalMechanism.META_CAPITAL_MEMORY: "GEN-C13",
}


@dataclass(frozen=True, slots=True)
class CompoundCausalAblationPair:
    ablation_id: str
    workstream_id: str
    root_control_id: str
    local_control_policy_id: str
    treatment_policy_id: str
    changed_mechanism: CompoundCausalMechanism
    population_id: str
    control_population_sha256: str
    treatment_population_sha256: str
    control_provider_economics_sha256: str
    treatment_provider_economics_sha256: str
    causal_horizon_sha256: str
    provider_constraints_sha256: str
    qualification_fold_id: str
    preregistered_at: datetime
    first_decision_at: datetime
    evidence_kind: CausalAblationEvidenceKind
    sealed_holdout_read: bool = False
    outcomes_used_to_select_treatment: bool = False
    weighted_score_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.ablation_id or not self.workstream_id:
            raise CiboCompoundCapitalError(
                "compound causal ablation identity/workstream is required"
            )
        if self.root_control_id != ROOT_CONTROL_ID:
            raise CiboCompoundCapitalError(
                "compound causal ablation root control identity drift"
            )
        if not self.local_control_policy_id or not self.treatment_policy_id:
            raise CiboCompoundCapitalError(
                "compound causal ablation local control/treatment is required"
            )
        if self.local_control_policy_id == self.treatment_policy_id:
            raise CiboCompoundCapitalError(
                "compound causal ablation treatment must differ from control"
            )
        if type(self.changed_mechanism) is not CompoundCausalMechanism:
            raise CiboCompoundCapitalError(
                "compound causal ablation mechanism is invalid"
            )
        if _MECHANISM_WORKSTREAM[self.changed_mechanism] != self.workstream_id:
            raise CiboCompoundCapitalError(
                "compound causal ablation mechanism/workstream mismatch"
            )
        if self.population_id in _PROTECTED_HOLDOUT_IDS:
            raise CiboCompoundCapitalError(
                "protected holdout cannot enter development ablation"
            )
        for name in (
            "control_population_sha256",
            "treatment_population_sha256",
            "control_provider_economics_sha256",
            "treatment_provider_economics_sha256",
            "causal_horizon_sha256",
            "provider_constraints_sha256",
        ):
            _sha(getattr(self, name), name)
        if self.control_population_sha256 != self.treatment_population_sha256:
            raise CiboCompoundCapitalError(
                "control/treatment population must be identical"
            )
        if (
            self.control_provider_economics_sha256
            != self.treatment_provider_economics_sha256
        ):
            raise CiboCompoundCapitalError(
                "control/treatment provider economics must be identical"
            )
        if self.qualification_fold_id not in _CANONICAL_FOLDS:
            raise CiboCompoundCapitalError(
                "compound causal ablation fold must be WF1..WF4"
            )
        _aware(self.preregistered_at, "preregistered_at")
        _aware(self.first_decision_at, "first_decision_at")
        if self.preregistered_at < PROTOCOL_FROZEN_AT:
            raise CiboCompoundCapitalError(
                "ablation registration cannot predate protocol freeze"
            )
        if self.first_decision_at < self.preregistered_at:
            raise CiboCompoundCapitalError(
                "compound causal ablation contains pre-registration decision"
            )
        if (
            type(self.evidence_kind) is not CausalAblationEvidenceKind
            or self.evidence_kind is not CausalAblationEvidenceKind.FORWARD_OBSERVED
        ):
            raise CiboCompoundCapitalError(
                "compound causal ablation requires FORWARD_OBSERVED evidence"
            )
        if (
            self.sealed_holdout_read
            or self.outcomes_used_to_select_treatment
            or self.weighted_score_used
            or self.productive_authority
        ):
            raise CiboCompoundCapitalError(
                "compound causal ablation governance drift"
            )


@dataclass(frozen=True, slots=True)
class CompoundCausalAblationGateReport:
    ablation_ids: tuple[str, ...]
    treatment_policy_ids: tuple[str, ...]
    fold_ids: tuple[str, ...]
    pair_count: int
    protocol_id: str = PROTOCOL_ID
    one_mechanism_per_pair: bool = True
    same_population_per_pair: bool = True
    same_provider_economics_per_pair: bool = True
    forward_observed_only: bool = True
    economic_outcomes_evaluated: bool = False
    winner_selected: bool = False
    certification_ready: bool = False

    def __post_init__(self) -> None:
        if self.protocol_id != PROTOCOL_ID:
            raise CiboCompoundCapitalError(
                "compound causal ablation report protocol drift"
            )
        if (
            type(self.pair_count) is not int
            or self.pair_count <= 0
            or self.pair_count != len(self.ablation_ids)
            or self.pair_count != len(self.treatment_policy_ids)
            or self.pair_count != len(self.fold_ids)
        ):
            raise CiboCompoundCapitalError(
                "compound causal ablation report pair-count drift"
            )
        for values, label in (
            (self.ablation_ids, "ablation ids"),
            (self.treatment_policy_ids, "treatment ids"),
            (self.fold_ids, "fold ids"),
        ):
            if not isinstance(values, tuple) or any(
                not isinstance(item, str) or not item for item in values
            ):
                raise CiboCompoundCapitalError(
                    f"compound causal ablation report {label} are invalid"
                )
        if len(self.ablation_ids) != len(set(self.ablation_ids)):
            raise CiboCompoundCapitalError(
                "compound causal ablation report ablation ids must be unique"
            )
        if len(self.treatment_policy_ids) != len(set(self.treatment_policy_ids)):
            raise CiboCompoundCapitalError(
                "compound causal ablation report treatment ids must be unique"
            )
        if any(item not in _CANONICAL_FOLDS for item in self.fold_ids):
            raise CiboCompoundCapitalError(
                "compound causal ablation report fold identity drift"
            )
        for name in (
            "one_mechanism_per_pair",
            "same_population_per_pair",
            "same_provider_economics_per_pair",
            "forward_observed_only",
            "economic_outcomes_evaluated",
            "winner_selected",
            "certification_ready",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCompoundCapitalError(
                    f"compound causal ablation report {name} must be bool"
                )
        if (
            not self.one_mechanism_per_pair
            or not self.same_population_per_pair
            or not self.same_provider_economics_per_pair
            or not self.forward_observed_only
            or self.economic_outcomes_evaluated
            or self.winner_selected
            or self.certification_ready
        ):
            raise CiboCompoundCapitalError(
                "compound causal ablation report governance drift"
            )


def gate_compound_causal_ablation_pairs(
    pairs: tuple[CompoundCausalAblationPair, ...],
) -> CompoundCausalAblationGateReport:
    """Validate frozen N-vs-N+1 bindings without evaluating economic outcomes."""

    if not pairs:
        raise CiboCompoundCapitalError(
            "compound causal ablation batch cannot be empty"
        )
    ids = tuple(item.ablation_id for item in pairs)
    if len(ids) != len(set(ids)):
        raise CiboCompoundCapitalError(
            "compound causal ablation ids must be unique"
        )
    treatment_ids = tuple(item.treatment_policy_id for item in pairs)
    if len(treatment_ids) != len(set(treatment_ids)):
        raise CiboCompoundCapitalError(
            "compound causal ablation treatment identities must be unique"
        )
    return CompoundCausalAblationGateReport(
        ablation_ids=ids,
        treatment_policy_ids=treatment_ids,
        fold_ids=tuple(item.qualification_fold_id for item in pairs),
        pair_count=len(pairs),
    )


def _aware(value: datetime, name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise CiboCompoundCapitalError(
            f"compound causal ablation {name} must be timezone-aware"
        )


def _sha(value: str, name: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise CiboCompoundCapitalError(
            f"compound causal ablation {name} must be canonical SHA-256"
        )
