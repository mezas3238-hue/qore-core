"""Pre-outcome freeze for the two unresolved CE2I T11 nonlinear inputs.

Gross edge:
- uses the already frozen Phase19 TRAIN prior as the immutable model;
- validates only on later fresh OOS outcomes;
- never refits from the validation population.

Market impact:
- remains cTrader DEMO only;
- every child order is provider minimum volume;
- aggregate exposure levels are created by 1x and 2x simultaneous minimum-volume
  child orders rather than by sending an oversized individual order;
- calibration and validation episodes are temporally disjoint.

This module freezes the experiment before any new T11 population is consumed.
It does not execute broker mutations and grants no productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_train_prior import (
    prior_digest_sha256,
)

PROTOCOL_ID = "CIBO_ARCH2_T11_NONLINEAR_INPUT_FREEZE_V1"
FROZEN_AT = datetime(2026, 10, 1, 23, 20, tzinfo=UTC)

REQUIRED_SYMBOLS = (
    "AUDJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "NAS100",
    "XAUUSD",
)

GROSS_EDGE_MODEL_ID = "PHASE19_TRAIN_PRIOR_MEDIAN_OF_MEANS_5_NO_REFIT"
GROSS_EDGE_REQUIRED_LINEAGES = 7
GROSS_EDGE_MINIMUM_OUTCOMES_PER_LINEAGE = (
    FROZEN_PHASE20D_QUALIFICATION_PLAN.minimum_outcomes_per_lineage
)
GROSS_EDGE_REQUIRED_FOLDS = FROZEN_PHASE20D_QUALIFICATION_PLAN.fold_count

MARKET_IMPACT_MODEL_ID = "CTRADER_DEMO_MIN_VOLUME_MICROBUNDLE_QUADRATIC_V1"
MARKET_IMPACT_CHILD_ORDER_VOLUME_POLICY = "PROVIDER_MINIMUM_VOLUME_ONLY"
MARKET_IMPACT_AGGREGATE_CHILD_COUNTS = (1, 2)
MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL = 8
MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL = 4
MARKET_IMPACT_REQUIRED_TEMPORAL_FOLDS = 4


@dataclass(frozen=True, slots=True)
class T11GrossEdgeFreeze:
    model_id: str
    frozen_train_prior_sha256: str
    required_lineages: int
    minimum_outcomes_per_lineage: int
    required_folds: int
    estimator_refit_allowed: bool
    validation_outcomes_may_change_model: bool
    fresh_oos_required: bool
    temporal_stability_required: bool
    holdout_mining_allowed: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.model_id != GROSS_EDGE_MODEL_ID:
            raise CiboCapitalManagementError("T11 gross-edge model identity drift")
        if self.frozen_train_prior_sha256 != prior_digest_sha256():
            raise CiboCapitalManagementError("T11 gross-edge TRAIN prior digest drift")
        if self.required_lineages != GROSS_EDGE_REQUIRED_LINEAGES:
            raise CiboCapitalManagementError("T11 gross-edge lineage threshold drift")
        if (
            self.minimum_outcomes_per_lineage
            != GROSS_EDGE_MINIMUM_OUTCOMES_PER_LINEAGE
        ):
            raise CiboCapitalManagementError("T11 gross-edge sample threshold drift")
        if self.required_folds != GROSS_EDGE_REQUIRED_FOLDS:
            raise CiboCapitalManagementError("T11 gross-edge fold threshold drift")
        if (
            self.estimator_refit_allowed
            or self.validation_outcomes_may_change_model
            or not self.fresh_oos_required
            or not self.temporal_stability_required
            or self.holdout_mining_allowed
            or self.productive_authority
        ):
            raise CiboCapitalManagementError("T11 gross-edge governance drift")


@dataclass(frozen=True, slots=True)
class T11MarketImpactFreeze:
    model_id: str
    required_symbols: tuple[str, ...]
    child_order_volume_policy: str
    aggregate_child_counts: tuple[int, ...]
    calibration_episodes_per_level_per_symbol: int
    validation_episodes_per_level_per_symbol: int
    required_temporal_folds: int
    provider_key: str
    environment: str
    matched_side_required: bool
    matched_symbol_required: bool
    temporally_disjoint_validation_required: bool
    nonnegative_quadratic_coefficient_required: bool
    each_child_order_minimum_volume_required: bool
    realized_settlement_cost_required: bool
    deposit_asset_usd_required: bool
    balanced_long_short_pairs_required: bool
    alternating_level_order_required: bool
    fundednext_allowed: bool
    vps_allowed: bool
    live_allowed: bool
    real_capital_allowed: bool
    phase22_outcomes_allowed_for_calibration: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.model_id != MARKET_IMPACT_MODEL_ID:
            raise CiboCapitalManagementError("T11 impact model identity drift")
        if self.required_symbols != REQUIRED_SYMBOLS:
            raise CiboCapitalManagementError("T11 impact symbol universe drift")
        if self.child_order_volume_policy != MARKET_IMPACT_CHILD_ORDER_VOLUME_POLICY:
            raise CiboCapitalManagementError("T11 impact child-volume policy drift")
        if self.aggregate_child_counts != MARKET_IMPACT_AGGREGATE_CHILD_COUNTS:
            raise CiboCapitalManagementError("T11 impact aggregate levels drift")
        if self.aggregate_child_counts != tuple(sorted(set(self.aggregate_child_counts))):
            raise CiboCapitalManagementError("T11 impact levels must be sorted unique")
        if min(self.aggregate_child_counts) != 1 or len(self.aggregate_child_counts) < 2:
            raise CiboCapitalManagementError("T11 impact requires at least two levels")
        if (
            self.calibration_episodes_per_level_per_symbol
            != MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL
            or self.validation_episodes_per_level_per_symbol
            != MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL
            or self.required_temporal_folds != MARKET_IMPACT_REQUIRED_TEMPORAL_FOLDS
        ):
            raise CiboCapitalManagementError("T11 impact sampling threshold drift")
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError("T11 impact provider/environment drift")
        required_true = (
            self.matched_side_required,
            self.matched_symbol_required,
            self.temporally_disjoint_validation_required,
            self.nonnegative_quadratic_coefficient_required,
            self.each_child_order_minimum_volume_required,
            self.realized_settlement_cost_required,
            self.deposit_asset_usd_required,
            self.balanced_long_short_pairs_required,
            self.alternating_level_order_required,
        )
        if not all(required_true):
            raise CiboCapitalManagementError("T11 impact scientific controls weakened")
        prohibited = (
            self.fundednext_allowed,
            self.vps_allowed,
            self.live_allowed,
            self.real_capital_allowed,
            self.phase22_outcomes_allowed_for_calibration,
            self.productive_authority,
        )
        if any(prohibited):
            raise CiboCapitalManagementError("T11 impact authority/governance drift")


@dataclass(frozen=True, slots=True)
class T11NonlinearInputFreeze:
    protocol_id: str
    frozen_at: datetime
    gross_edge: T11GrossEdgeFreeze
    market_impact: T11MarketImpactFreeze
    gross_edge_population_consumed_at_freeze: bool
    market_impact_population_consumed_at_freeze: bool
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.protocol_id != PROTOCOL_ID:
            raise CiboCapitalManagementError("T11 nonlinear freeze identity drift")
        if self.frozen_at != FROZEN_AT:
            raise CiboCapitalManagementError("T11 nonlinear freeze time drift")
        if self.frozen_at.tzinfo is None or self.frozen_at.utcoffset() is None:
            raise CiboCapitalManagementError("T11 nonlinear freeze time must be aware")
        if (
            self.gross_edge_population_consumed_at_freeze
            or self.market_impact_population_consumed_at_freeze
            or self.productive_authority
        ):
            raise CiboCapitalManagementError("T11 nonlinear freeze is not pre-outcome")

    def fingerprint(self) -> str:
        payload = asdict(self)
        payload["frozen_at"] = self.frozen_at.isoformat()
        raw = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


T11_NONLINEAR_INPUT_FREEZE = T11NonlinearInputFreeze(
    protocol_id=PROTOCOL_ID,
    frozen_at=FROZEN_AT,
    gross_edge=T11GrossEdgeFreeze(
        model_id=GROSS_EDGE_MODEL_ID,
        frozen_train_prior_sha256=prior_digest_sha256(),
        required_lineages=GROSS_EDGE_REQUIRED_LINEAGES,
        minimum_outcomes_per_lineage=GROSS_EDGE_MINIMUM_OUTCOMES_PER_LINEAGE,
        required_folds=GROSS_EDGE_REQUIRED_FOLDS,
        estimator_refit_allowed=False,
        validation_outcomes_may_change_model=False,
        fresh_oos_required=True,
        temporal_stability_required=True,
        holdout_mining_allowed=False,
    ),
    market_impact=T11MarketImpactFreeze(
        model_id=MARKET_IMPACT_MODEL_ID,
        required_symbols=REQUIRED_SYMBOLS,
        child_order_volume_policy=MARKET_IMPACT_CHILD_ORDER_VOLUME_POLICY,
        aggregate_child_counts=MARKET_IMPACT_AGGREGATE_CHILD_COUNTS,
        calibration_episodes_per_level_per_symbol=(
            MARKET_IMPACT_CALIBRATION_EPISODES_PER_LEVEL_PER_SYMBOL
        ),
        validation_episodes_per_level_per_symbol=(
            MARKET_IMPACT_VALIDATION_EPISODES_PER_LEVEL_PER_SYMBOL
        ),
        required_temporal_folds=MARKET_IMPACT_REQUIRED_TEMPORAL_FOLDS,
        provider_key="ctrader-demo",
        environment="demo",
        matched_side_required=True,
        matched_symbol_required=True,
        temporally_disjoint_validation_required=True,
        nonnegative_quadratic_coefficient_required=True,
        each_child_order_minimum_volume_required=True,
        realized_settlement_cost_required=True,
        deposit_asset_usd_required=True,
        balanced_long_short_pairs_required=True,
        alternating_level_order_required=True,
        fundednext_allowed=False,
        vps_allowed=False,
        live_allowed=False,
        real_capital_allowed=False,
        phase22_outcomes_allowed_for_calibration=False,
    ),
    gross_edge_population_consumed_at_freeze=False,
    market_impact_population_consumed_at_freeze=False,
)
