"""MC18 counterfactual failure-probability calibration primitives.

The raw Counterfactual World Engine remains unchanged. A calibration may only
be attached after a separately preregistered consumed-development experiment
passes its frozen gates. This module carries no trading authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Final

from qore.infrastructure.core_stack_v2.counterfactual_world_engine import (
    CounterfactualWorldDistribution,
    CounterfactualWorldKind,
)

FAILURE_WORLD_KINDS: Final = frozenset(
    {
        CounterfactualWorldKind.LIQUIDITY_FAILS,
        CounterfactualWorldKind.LEADER_REVERSES,
        CounterfactualWorldKind.RELATIONSHIP_BREAKS,
        CounterfactualWorldKind.FAILED_AUCTION_REVERSAL,
    }
)


@dataclass(frozen=True, slots=True)
class CounterfactualFailureCalibration:
    calibration_id: str
    intercept: float
    coefficient: float
    fitted_on: str
    target_definition: str
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.calibration_id.strip() or not self.fitted_on.strip():
            raise ValueError("calibration identity and development source are required")
        if not self.target_definition.strip():
            raise ValueError("calibration target definition is required")
        if not math.isfinite(self.intercept):
            raise ValueError("calibration intercept must be finite")
        if not math.isfinite(self.coefficient) or self.coefficient <= 0.0:
            raise ValueError("calibration must preserve positive monotonicity")
        if self.productive_authority:
            raise ValueError("MC18 calibration is research-only")

    def fingerprint(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()


def raw_failure_probability_bps(
    distribution: CounterfactualWorldDistribution,
) -> int:
    value = sum(
        path.probability_bps
        for path in distribution.paths
        if path.kind in FAILURE_WORLD_KINDS
    )
    if not 0 <= value <= 10_000:
        raise ValueError("counterfactual failure mass must be within 0..10000")
    return value


def calibrated_failure_probability_bps(
    raw_probability_bps: int,
    calibration: CounterfactualFailureCalibration,
) -> int:
    if type(raw_probability_bps) is not int or not 0 <= raw_probability_bps <= 10_000:
        raise ValueError("raw_probability_bps must be int within 0..10000")
    x = raw_probability_bps / 10_000.0
    z = calibration.intercept + calibration.coefficient * x
    if z >= 0:
        probability = 1.0 / (1.0 + math.exp(-z))
    else:
        exp_z = math.exp(z)
        probability = exp_z / (1.0 + exp_z)
    return max(0, min(10_000, int(round(probability * 10_000))))
