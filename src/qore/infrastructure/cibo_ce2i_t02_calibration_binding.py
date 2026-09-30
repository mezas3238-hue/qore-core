"""Frozen burned-data binding for T02 Structural Leverage.

Derived only from the sealed Phase18 burned calibration artifact. The binding
never reads the preregistered 2017H1 holdout and never changes Trader geometry.
A context mismatch or empirically ineligible lineage yields no T02 evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_advanced_capital_tools import (
    StructuralLeverageEvidence,
)

T02_CONTEXT_WORKFLOW_RUN_ID = 36450667459
T02_CONTEXT_ARTIFACT_ID = 10983002685
T02_CONTEXT_ARTIFACT_DIGEST = (
    "sha256:168c48e011ef3be8acaa2d69540279bcd4126e6f5d8002c80e4708c2741813d8"
)
T02_CONTEXT_CALIBRATION_SHA256 = (
    "495810a3333537a4d7c159d4112e71b379de77096bda100fb838f3c539e11cb3"
)
T02_CALIBRATOR_GIT_SHA = "16ef0327f84423c9449e7d59679b7bd864880e8c"
T02_RUNTIME_MINIMUM_OOS_SAMPLE = 30


@dataclass(frozen=True, slots=True)
class T02BurnedContextRule:
    lineage: TraderLineage
    selected_field: str
    selected_value: str
    source_artifact_id: int
    validation_candidate_rows: int
    validation_baseline_stop_rate: Decimal
    validation_candidate_stop_rate: Decimal
    validation_baseline_p95_loss_r: Decimal
    validation_candidate_p95_loss_r: Decimal
    eligible_for_structural_leverage: bool

    @property
    def meets_runtime_minimum_sample(self) -> bool:
        return self.validation_candidate_rows >= T02_RUNTIME_MINIMUM_OOS_SAMPLE


T02_BURNED_CONTEXT_RULES: tuple[T02BurnedContextRule, ...] = (
    T02BurnedContextRule(
        TraderLineage.R34_XAUUSD,
        "family",
        "LONG_DELAYED_RECLAIM_MEDIUM_BODY",
        10972757083,
        35,
        Decimal("0.3441734417344173441734417344"),
        Decimal("0.3142857142857142857142857143"),
        Decimal("1.10"),
        Decimal("1.10"),
        True,
    ),
    T02BurnedContextRule(
        TraderLineage.R38_EURUSD,
        "target_route",
        "PRIOR_CANDLE_DIRECTIONAL_BOUNDARY:H1",
        10972572540,
        27,
        Decimal("0.3872832369942196531791907514"),
        Decimal("0.3333333333333333333333333333"),
        Decimal("1.10"),
        Decimal("1.10"),
        True,
    ),
    T02BurnedContextRule(
        TraderLineage.R43_GBPUSD,
        "side",
        "long",
        10972906353,
        186,
        Decimal("0.3829201101928374655647382920"),
        Decimal("0.3548387096774193548387096774"),
        Decimal("1.10"),
        Decimal("1.10"),
        True,
    ),
    T02BurnedContextRule(
        TraderLineage.R38_GBPJPY,
        "side",
        "long",
        10972846579,
        172,
        Decimal("0.3593314763231197771587743733"),
        Decimal("0.3197674418604651162790697674"),
        Decimal("1.10"),
        Decimal("1.10"),
        True,
    ),
    T02BurnedContextRule(
        TraderLineage.R42_AUDJPY,
        "fragility_flag_count",
        "2",
        10972467350,
        73,
        Decimal("0.4326923076923076923076923077"),
        Decimal("0.4383561643835616438356164384"),
        Decimal("1.10"),
        Decimal("1.10"),
        False,
    ),
    T02BurnedContextRule(
        TraderLineage.VT08_FOREX,
        "side",
        "long",
        10972037659,
        11,
        Decimal("0.44"),
        Decimal("0.6363636363636363636363636364"),
        Decimal("1"),
        Decimal("1"),
        False,
    ),
    T02BurnedContextRule(
        TraderLineage.VT31_NAS100,
        "risk_ref_bucket",
        "mid",
        10971913368,
        13,
        Decimal("0.7337461300309597523219814241"),
        Decimal("0.6153846153846153846153846154"),
        Decimal("1"),
        Decimal("1"),
        False,
    ),
)


def t02_calibration_source_ref() -> str:
    return (
        f"burned:t02:context:artifact:{T02_CONTEXT_ARTIFACT_ID}:"
        f"sha256:{T02_CONTEXT_CALIBRATION_SHA256}"
    )


def t02_context_rule(lineage: TraderLineage) -> T02BurnedContextRule:
    matches = tuple(
        row for row in T02_BURNED_CONTEXT_RULES if row.lineage is lineage
    )
    if len(matches) != 1:
        raise ValueError("T02 burned context registry must contain each lineage once")
    return matches[0]


def build_t02_structural_leverage_evidence(
    *,
    opportunity: TraderOpportunityEnvelope,
    observed_at: datetime,
    released_risk_capacity_usd: Decimal = Decimal(0),
    protected_capacity_usd: Decimal = Decimal(0),
) -> StructuralLeverageEvidence | None:
    """Bind one causal opportunity to the frozen burned T02 context rule."""

    rule = t02_context_rule(opportunity.trader_id)
    if not rule.eligible_for_structural_leverage:
        return None
    if opportunity.context_value(rule.selected_field) != rule.selected_value:
        return None
    return StructuralLeverageEvidence(
        evidence_id=(
            f"t02-burned-context:{T02_CONTEXT_CALIBRATION_SHA256}:"
            f"{opportunity.signal_fingerprint}"
        ),
        structural_invalidation_id=(
            f"{opportunity.signal_fingerprint}:trader-structural-stop"
        ),
        observed_at=observed_at,
        sample_size=rule.validation_candidate_rows,
        baseline_stop_rate=rule.validation_baseline_stop_rate,
        candidate_stop_rate=rule.validation_candidate_stop_rate,
        baseline_tail_loss_r=rule.validation_baseline_p95_loss_r,
        candidate_tail_loss_r=rule.validation_candidate_p95_loss_r,
        released_risk_capacity_usd=released_risk_capacity_usd,
        protected_capacity_usd=protected_capacity_usd,
        evidence_oos=True,
        structural_stop_verified=True,
        stop_geometry_unchanged=True,
    )
