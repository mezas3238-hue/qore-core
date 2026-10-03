"""Exact min/max/weighted constants for CIBO Compound and Compound Portfolio.

The statistic is a capital-conversion constant:

    K = useful_output_capital_usd / source_capital_usd

For a population of observations the weighted average is not an arithmetic
average of ratios. It is the exact capital-weighted ratio:

    K_weighted = sum(useful_output_capital_usd) / sum(source_capital_usd)

This keeps large and small capital observations economically proportional.
The module is descriptive only and grants no Risk, sizing, execution, broker,
LIVE, Production, real-capital, certification, or merge authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from enum import StrEnum

from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError

COMPOUND_CONSTANT_QUANTUM = Decimal("0.000000000001")


def _constant_ratio(output: Decimal, source: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 80
        return (output / source).quantize(
            COMPOUND_CONSTANT_QUANTUM,
            rounding=ROUND_HALF_EVEN,
        )


class CompoundConstantSystem(StrEnum):
    CIBO_COMPOUND = "CIBO_COMPOUND"
    COMPOUND_PORTFOLIO = "COMPOUND_PORTFOLIO"


def _money(value: Decimal, name: str, *, positive: bool = False) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise CiboCompoundCapitalError(f"{name} must be finite Decimal")
    if positive and value <= 0:
        raise CiboCompoundCapitalError(f"{name} must be positive")
    if not positive and value < 0:
        raise CiboCompoundCapitalError(f"{name} must be nonnegative")


@dataclass(frozen=True, slots=True)
class CompoundConstantObservation:
    """One exact capital-source to useful-output observation."""

    observation_id: str
    source_capital_usd: Decimal
    useful_output_capital_usd: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.observation_id, str) or not self.observation_id:
            raise CiboCompoundCapitalError("compound constant observation_id required")
        _money(self.source_capital_usd, "compound constant source capital", positive=True)
        _money(
            self.useful_output_capital_usd,
            "compound constant useful output capital",
        )

    @property
    def constant(self) -> Decimal:
        return _constant_ratio(
            self.useful_output_capital_usd,
            self.source_capital_usd,
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.observation_id,
            format(self.source_capital_usd, "f"),
            format(self.useful_output_capital_usd, "f"),
            format(self.constant, "f"),
        )


@dataclass(frozen=True, slots=True)
class CompoundConstantSummary:
    """Exact minimum, maximum and capital-weighted average constant."""

    system: CompoundConstantSystem
    observations: tuple[CompoundConstantObservation, ...]
    minimum_constant: Decimal
    maximum_constant: Decimal
    weighted_average_constant: Decimal
    minimum_observation_ids: tuple[str, ...]
    maximum_observation_ids: tuple[str, ...]
    total_source_capital_usd: Decimal
    total_useful_output_capital_usd: Decimal
    descriptive_only: bool = True
    runtime_authority: bool = False

    def __post_init__(self) -> None:
        if type(self.system) is not CompoundConstantSystem:
            raise CiboCompoundCapitalError("compound constant system invalid")
        if not isinstance(self.observations, tuple) or not self.observations:
            raise CiboCompoundCapitalError("compound constant observations required")
        if any(type(item) is not CompoundConstantObservation for item in self.observations):
            raise CiboCompoundCapitalError("compound constant observations must be canonical")
        ids = tuple(item.observation_id for item in self.observations)
        if len(ids) != len(set(ids)):
            raise CiboCompoundCapitalError("compound constant observation ids must be unique")
        for name in (
            "minimum_constant",
            "maximum_constant",
            "weighted_average_constant",
            "total_source_capital_usd",
            "total_useful_output_capital_usd",
        ):
            value = getattr(self, name)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise CiboCompoundCapitalError(f"compound constant {name} invalid")
        expected_min = min(item.constant for item in self.observations)
        expected_max = max(item.constant for item in self.observations)
        expected_source = sum(
            (item.source_capital_usd for item in self.observations),
            Decimal(0),
        )
        expected_output = sum(
            (item.useful_output_capital_usd for item in self.observations),
            Decimal(0),
        )
        expected_weighted = _constant_ratio(expected_output, expected_source)
        if self.minimum_constant != expected_min:
            raise CiboCompoundCapitalError("compound constant minimum identity drift")
        if self.maximum_constant != expected_max:
            raise CiboCompoundCapitalError("compound constant maximum identity drift")
        if self.total_source_capital_usd != expected_source:
            raise CiboCompoundCapitalError("compound constant source-total identity drift")
        if self.total_useful_output_capital_usd != expected_output:
            raise CiboCompoundCapitalError("compound constant output-total identity drift")
        if self.weighted_average_constant != expected_weighted:
            raise CiboCompoundCapitalError("compound constant weighted-average identity drift")
        expected_min_ids = tuple(
            sorted(
                item.observation_id
                for item in self.observations
                if item.constant == expected_min
            )
        )
        expected_max_ids = tuple(
            sorted(
                item.observation_id
                for item in self.observations
                if item.constant == expected_max
            )
        )
        if self.minimum_observation_ids != expected_min_ids:
            raise CiboCompoundCapitalError("compound constant minimum ids drift")
        if self.maximum_observation_ids != expected_max_ids:
            raise CiboCompoundCapitalError("compound constant maximum ids drift")
        if not (
            self.minimum_constant
            <= self.weighted_average_constant
            <= self.maximum_constant
        ):
            raise CiboCompoundCapitalError("compound weighted constant outside observed range")
        if self.descriptive_only is not True or self.runtime_authority is not False:
            raise CiboCompoundCapitalError("compound constants are descriptive-only")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.system.value,
            tuple(item.logical_values() for item in self.observations),
            format(self.minimum_constant, "f"),
            format(self.maximum_constant, "f"),
            format(self.weighted_average_constant, "f"),
            self.minimum_observation_ids,
            self.maximum_observation_ids,
            format(self.total_source_capital_usd, "f"),
            format(self.total_useful_output_capital_usd, "f"),
            self.descriptive_only,
            self.runtime_authority,
        )


def summarize_compound_constants(
    *,
    system: CompoundConstantSystem,
    observations: tuple[CompoundConstantObservation, ...],
) -> CompoundConstantSummary:
    """Build exact min/max/capital-weighted constant statistics."""

    if type(system) is not CompoundConstantSystem:
        raise CiboCompoundCapitalError("compound constant system invalid")
    if not isinstance(observations, tuple) or not observations:
        raise CiboCompoundCapitalError("compound constant observations required")
    if any(type(item) is not CompoundConstantObservation for item in observations):
        raise CiboCompoundCapitalError("compound constant observations must be canonical")
    ordered = tuple(sorted(observations, key=lambda item: item.observation_id))
    minimum = min(item.constant for item in ordered)
    maximum = max(item.constant for item in ordered)
    source = sum((item.source_capital_usd for item in ordered), Decimal(0))
    output = sum((item.useful_output_capital_usd for item in ordered), Decimal(0))
    weighted = _constant_ratio(output, source)
    return CompoundConstantSummary(
        system=system,
        observations=ordered,
        minimum_constant=minimum,
        maximum_constant=maximum,
        weighted_average_constant=weighted,
        minimum_observation_ids=tuple(
            item.observation_id for item in ordered if item.constant == minimum
        ),
        maximum_observation_ids=tuple(
            item.observation_id for item in ordered if item.constant == maximum
        ),
        total_source_capital_usd=source,
        total_useful_output_capital_usd=output,
    )
