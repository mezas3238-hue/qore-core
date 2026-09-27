"""Frozen TRAIN-only causal expectation priors for Phase20 allocation research.

The priors are derived exclusively from the Phase19 TRAIN segment. They never
consume Phase19J validation rows, current/future outcomes, provider-history
fabrication or post-entry path at decision time.

Estimator:
- expected structural R: median of five chronological block means;
- expected capital minutes: TRAIN median observed duration.

The robust median-of-means estimator preserves within-block asymmetric tails
while preventing one extreme chronological block from dominating the prior.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_causal_expectation import (
    CausalExpectationBasis,
    CausalOpportunityExpectation,
)

_PRIOR_IDENTITY = "CIBO_PHASE20_TRAIN_PRIOR_V1"
_ESTIMATOR = "CHRONOLOGICAL_MEDIAN_OF_MEANS_5"
_DURATION_ESTIMATOR = "TRAIN_MEDIAN_MINUTES"
_TRAIN_START = "2021-09-23T05:00:00+00:00"
_TRAIN_END = "2022-03-09T17:00:00+00:00"
_BLOCK_COUNT = 5


@dataclass(frozen=True, slots=True)
class FrozenTraderExpectationPrior:
    trader_id: TraderLineage
    train_rows: int
    expected_structural_r: Decimal
    expected_capital_minutes: Decimal
    chronological_block_means_r: tuple[Decimal, ...]
    arithmetic_mean_r_diagnostic: Decimal

    def __post_init__(self) -> None:
        if type(self.trader_id) is not TraderLineage:
            raise CiboCapitalManagementError(
                "TRAIN prior trader_id must be TraderLineage"
            )
        if (
            not isinstance(self.train_rows, int)
            or isinstance(self.train_rows, bool)
            or self.train_rows <= 0
        ):
            raise CiboCapitalManagementError(
                "TRAIN prior row count must be positive int"
            )
        for name in (
            "expected_structural_r",
            "expected_capital_minutes",
            "arithmetic_mean_r_diagnostic",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCapitalManagementError(
                    f"TRAIN prior {name} must be finite Decimal"
                )
        if self.expected_capital_minutes <= 0:
            raise CiboCapitalManagementError(
                "TRAIN prior expected capital minutes must be positive"
            )
        if len(self.chronological_block_means_r) != _BLOCK_COUNT:
            raise CiboCapitalManagementError(
                "TRAIN prior must retain exactly five chronological blocks"
            )
        if any(
            not isinstance(item, Decimal) or not item.is_finite()
            for item in self.chronological_block_means_r
        ):
            raise CiboCapitalManagementError(
                "TRAIN prior block means must be finite Decimal"
            )


FROZEN_TRAIN_PRIORS: tuple[FrozenTraderExpectationPrior, ...] = (
    FrozenTraderExpectationPrior(
        trader_id=TraderLineage.R38_GBPJPY,
        train_rows=97,
        expected_structural_r=Decimal("0.2772449399623627771422912858"),
        expected_capital_minutes=Decimal("55"),
        chronological_block_means_r=(
            Decimal("0.4213472089990746575852153153947368421053"),
            Decimal("-0.02156712091342630972697089597894736842105"),
            Decimal("0.2772449399623627771422912858"),
            Decimal("0.4501877287467870042363611308326315789474"),
            Decimal("0.004487512732975745256864457415"),
        ),
        arithmetic_mean_r_diagnostic=Decimal(
            "0.2245777069455983725544393847321649484536"
        ),
    ),
    FrozenTraderExpectationPrior(
        trader_id=TraderLineage.R43_GBPUSD,
        train_rows=84,
        expected_structural_r=Decimal(
            "0.04540176351632619076884529877058823529412"
        ),
        expected_capital_minutes=Decimal("45"),
        chronological_block_means_r=(
            Decimal("-0.28309343302261668937489943910625"),
            Decimal("0.2193936982005561890840902133588235294118"),
            Decimal("-0.2087119335479914092191165514058823529412"),
            Decimal("0.04540176351632619076884529877058823529412"),
            Decimal("0.2936974469360075492882436600529411764706"),
        ),
        arithmetic_mean_r_diagnostic=Decimal(
            "0.01686644819549295010329373247023809523810"
        ),
    ),
    FrozenTraderExpectationPrior(
        trader_id=TraderLineage.R42_AUDJPY,
        train_rows=81,
        expected_structural_r=Decimal(
            "0.15558135309771811105602414900375"
        ),
        expected_capital_minutes=Decimal("80"),
        chronological_block_means_r=(
            Decimal("0.19220751997141239845643133770625"),
            Decimal("0.15558135309771811105602414900375"),
            Decimal("0.10689619036911310326340218443125"),
            Decimal("0.37432704297511458933689536034375"),
            Decimal("-0.2132543768554608537800923142647058823529"),
        ),
        arithmetic_mean_r_diagnostic=Decimal(
            "0.1189983863712456385128701131019753086420"
        ),
    ),
    FrozenTraderExpectationPrior(
        trader_id=TraderLineage.R38_EURUSD,
        train_rows=75,
        expected_structural_r=Decimal("-0.07406596871747924540112516922"),
        expected_capital_minutes=Decimal("40"),
        chronological_block_means_r=(
            Decimal("-0.3154957264957264957264957265306666666667"),
            Decimal("-0.07406596871747924540112516922"),
            Decimal("0.2559861601096236527125736695"),
            Decimal("-0.28203779977889001299478001785"),
            Decimal("2.391435990706824040157373490773333333333"),
        ),
        arithmetic_mean_r_diagnostic=Decimal(
            "0.3951645311648703877495092493345333333333"
        ),
    ),
    FrozenTraderExpectationPrior(
        trader_id=TraderLineage.R34_XAUUSD,
        train_rows=85,
        expected_structural_r=Decimal(
            "0.01123928933790496197574842467647058823529"
        ),
        expected_capital_minutes=Decimal("30"),
        chronological_block_means_r=(
            Decimal("0.01123928933790496197574842467647058823529"),
            Decimal("-0.2704193392178274126822980526176470588235"),
            Decimal("-0.2597080427408693287297642440311764705882"),
            Decimal("0.4588280222882347179038347166147058823529"),
            Decimal("0.4177790944859605624595295872470588235294"),
        ),
        arithmetic_mean_r_diagnostic=Decimal(
            "0.07154380483068070018541008637788235294118"
        ),
    ),
    FrozenTraderExpectationPrior(
        trader_id=TraderLineage.VT08_FOREX,
        train_rows=24,
        expected_structural_r=Decimal(
            "-0.09821428571428571428571428572"
        ),
        expected_capital_minutes=Decimal("105"),
        chronological_block_means_r=(
            Decimal("0.8477987421383647798742138365"),
            Decimal("-0.4"),
            Decimal("-0.5027997299551248957547357134434"),
            Decimal("0.2"),
            Decimal("-0.09821428571428571428571428572"),
        ),
        arithmetic_mean_r_diagnostic=Decimal(
            "-0.02557812957473308044605811040904166666667"
        ),
    ),
    FrozenTraderExpectationPrior(
        trader_id=TraderLineage.VT31_NAS100,
        train_rows=77,
        expected_structural_r=Decimal(
            "0.2981877694835413223925389858666666666667"
        ),
        expected_capital_minutes=Decimal("6"),
        chronological_block_means_r=(
            Decimal("-0.24775588675934902097114461748"),
            Decimal("0.2981877694835413223925389858666666666667"),
            Decimal("-0.67235739167461856537486789589375"),
            Decimal("1.624208687572984123661587019499333333333"),
            Decimal("0.58863815968897997308276687775625"),
        ),
        arithmetic_mean_r_diagnostic=Decimal(
            "0.3088324784764601155788455133518181818182"
        ),
    ),
)


def frozen_train_prior_for(
    trader_id: TraderLineage,
) -> FrozenTraderExpectationPrior:
    if type(trader_id) is not TraderLineage:
        raise CiboCapitalManagementError(
            "TRAIN prior lookup requires TraderLineage"
        )
    matches = tuple(
        item for item in FROZEN_TRAIN_PRIORS if item.trader_id is trader_id
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "TRAIN prior coverage must contain exactly one Trader row"
        )
    return matches[0]


def build_frozen_train_expectation(
    *,
    trader_id: TraderLineage,
    stop_risk_usd: Decimal,
    as_of: datetime,
) -> CausalOpportunityExpectation:
    """Convert a frozen TRAIN structural-R prior into current USD expectation."""

    if (
        not isinstance(stop_risk_usd, Decimal)
        or not stop_risk_usd.is_finite()
        or stop_risk_usd <= 0
    ):
        raise CiboCapitalManagementError(
            "TRAIN prior current stop risk must be finite positive Decimal"
        )
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise CiboCapitalManagementError(
            "TRAIN prior expectation as_of must be timezone-aware"
        )
    prior = frozen_train_prior_for(trader_id)
    return CausalOpportunityExpectation(
        evidence_id=(
            f"{_PRIOR_IDENTITY}:{prior_digest_sha256()}:{trader_id.value}"
        ),
        as_of=as_of,
        basis=CausalExpectationBasis.FROZEN_HISTORICAL_PRIOR,
        expected_net_value_usd=prior.expected_structural_r * stop_risk_usd,
        expected_capital_minutes=prior.expected_capital_minutes,
    )


def prior_digest_sha256() -> str:
    payload = {
        "identity": _PRIOR_IDENTITY,
        "estimator": _ESTIMATOR,
        "duration_estimator": _DURATION_ESTIMATOR,
        "training_window": {
            "start": _TRAIN_START,
            "end": _TRAIN_END,
        },
        "block_count": _BLOCK_COUNT,
        "rows": [
            {
                "trader_id": item.trader_id.value,
                "train_rows": item.train_rows,
                "expected_structural_r": format(
                    item.expected_structural_r,
                    "f",
                ),
                "expected_capital_minutes": format(
                    item.expected_capital_minutes,
                    "f",
                ),
                "chronological_block_means_r": [
                    format(value, "f")
                    for value in item.chronological_block_means_r
                ],
                "arithmetic_mean_r_diagnostic": format(
                    item.arithmetic_mean_r_diagnostic,
                    "f",
                ),
            }
            for item in FROZEN_TRAIN_PRIORS
        ],
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return f"sha256:{sha256(raw).hexdigest()}"
