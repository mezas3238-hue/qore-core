"""Compose raw causal observations into source-faithful Failure to Manipulate."""

from __future__ import annotations

from qore.infrastructure.trader_lab.capitalizer_source_cisd_ftm_v2 import (
    CapitalizerCISDObservation,
    CapitalizerFailureToManipulateObservation,
    assess_failure_to_manipulate,
)
from qore.infrastructure.trader_lab.capitalizer_source_daily_bias_v2 import (
    CapitalizerDailyBiasObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_liquidity_take_v2 import (
    CapitalizerLiquidityTakeObservation,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerProtectedSwingObservation,
)


def compose_failure_to_manipulate(
    *,
    liquidity_take: CapitalizerLiquidityTakeObservation,
    expected_reversal_cisd: CapitalizerCISDObservation | None,
    continuation_protected_swing: CapitalizerProtectedSwingObservation | None,
    daily_bias: CapitalizerDailyBiasObservation,
) -> CapitalizerFailureToManipulateObservation:
    """Build FTM only from completed causal observations."""

    return assess_failure_to_manipulate(
        taken_side=liquidity_take.side,
        level_taken=liquidity_take.level_taken,
        post_sweep_closure_observed=liquidity_take.closed_bar_observed,
        expected_reversal_cisd=expected_reversal_cisd,
        continuation_protected_swing=continuation_protected_swing,
        daily_bias=daily_bias,
    )
