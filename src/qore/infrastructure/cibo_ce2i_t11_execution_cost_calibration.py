"""Provider-bound linear execution-cost calibration for CE2I T11.

This bridge combines the immutable Architect-B manifest with empirical forward
fill calibration to freeze observed linear execution costs per symbol:

    pre-decision quoted spread
  + observed commission
  + p95 adverse realized slippage

It deliberately does not invent gross edge or nonlinear market impact. T11
therefore remains fail-closed for policy promotion until those causal inputs are
separately identified.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import ceil

from qore.infrastructure.cibo_arch_b_forward_economic_manifest import (
    ArchBForwardEconomicManifest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_provider_economics_evidence import (
    CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS,
)
from qore.infrastructure.cibo_ce2i_provider_execution_calibration import (
    CiboProviderExecutionCalibration,
)


@dataclass(frozen=True, slots=True)
class T11SymbolLinearExecutionCost:
    qore_symbol: str
    observation_count: int
    p95_quoted_spread_cost_per_volume_usd: Decimal
    p95_commission_cost_per_volume_usd: Decimal
    p95_adverse_slippage_cost_per_volume_usd: Decimal
    p95_linear_execution_cost_per_volume_usd: Decimal

    def __post_init__(self) -> None:
        if not self.qore_symbol:
            raise CiboCapitalManagementError(
                "T11 linear execution symbol is required"
            )
        if (
            not isinstance(self.observation_count, int)
            or isinstance(self.observation_count, bool)
            or self.observation_count <= 0
        ):
            raise CiboCapitalManagementError(
                "T11 linear execution observation count must be positive int"
            )
        components = (
            self.p95_quoted_spread_cost_per_volume_usd,
            self.p95_commission_cost_per_volume_usd,
            self.p95_adverse_slippage_cost_per_volume_usd,
        )
        if any(
            not isinstance(value, Decimal)
            or not value.is_finite()
            or value < 0
            for value in components
        ):
            raise CiboCapitalManagementError(
                "T11 linear execution cost components must be non-negative"
            )
        if self.p95_linear_execution_cost_per_volume_usd != sum(
            components,
            Decimal(0),
        ):
            raise CiboCapitalManagementError(
                "T11 linear execution cost total drift"
            )


@dataclass(frozen=True, slots=True)
class CiboT11ExecutionCostCalibration:
    manifest_sha256: str
    execution_calibration_sha256: str
    symbols: tuple[T11SymbolLinearExecutionCost, ...]
    required_symbol_coverage_met: bool
    provider_execution_model_ready: bool
    linear_cost_model_ready: bool
    gross_edge_model_ready: bool
    market_impact_model_ready: bool
    historical_2017_execution_terms_proven: bool
    t11_policy_ready: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        _sha(self.manifest_sha256, "manifest_sha256")
        _sha(
            self.execution_calibration_sha256,
            "execution_calibration_sha256",
        )
        names = tuple(item.qore_symbol for item in self.symbols)
        if names != tuple(sorted(names)) or len(names) != len(set(names)):
            raise CiboCapitalManagementError(
                "T11 linear execution symbols must be sorted unique"
            )
        required = set(CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.symbols)
        expected_coverage = required.issubset(names)
        if self.required_symbol_coverage_met != expected_coverage:
            raise CiboCapitalManagementError(
                "T11 linear execution symbol coverage drift"
            )
        for name in (
            "required_symbol_coverage_met",
            "provider_execution_model_ready",
            "linear_cost_model_ready",
            "gross_edge_model_ready",
            "market_impact_model_ready",
            "historical_2017_execution_terms_proven",
            "t11_policy_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T11 execution calibration {name} must be bool"
                )
        expected_linear = (
            self.provider_execution_model_ready
            and self.required_symbol_coverage_met
            and bool(self.symbols)
        )
        if self.linear_cost_model_ready != expected_linear:
            raise CiboCapitalManagementError(
                "T11 linear execution readiness drift"
            )
        if (
            self.gross_edge_model_ready
            or self.market_impact_model_ready
            or self.historical_2017_execution_terms_proven
            or self.t11_policy_ready
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T11 linear calibration cannot promote unresolved policy inputs"
            )


def calibrate_t11_linear_execution_cost(
    *,
    manifest: ArchBForwardEconomicManifest,
    execution_calibration: CiboProviderExecutionCalibration,
) -> CiboT11ExecutionCostCalibration:
    """Freeze observed linear costs without fabricating T11 marginal utility."""

    if not isinstance(manifest, ArchBForwardEconomicManifest):
        raise CiboCapitalManagementError(
            "T11 linear execution calibration requires Architect-B manifest"
        )
    if not isinstance(
        execution_calibration,
        CiboProviderExecutionCalibration,
    ):
        raise CiboCapitalManagementError(
            "T11 linear execution calibration requires provider calibration"
        )
    if execution_calibration.manifest_sha256 != manifest.fingerprint():
        raise CiboCapitalManagementError(
            "T11 linear execution manifest/calibration SHA drift"
        )

    execution_by_symbol = {
        item.qore_symbol: item
        for item in execution_calibration.symbol_summaries
    }
    manifest_by_symbol: dict[str, list[object]] = {}
    for row in manifest.rows:
        manifest_by_symbol.setdefault(row.qore_symbol, []).append(row)

    summaries: list[T11SymbolLinearExecutionCost] = []
    for symbol in sorted(manifest_by_symbol):
        rows = manifest_by_symbol[symbol]
        execution = execution_by_symbol.get(symbol)
        if execution is None:
            continue
        spreads = tuple(
            (row.provider_ask - row.provider_bid)
            / row.provider_tick_size
            * row.provider_tick_value
            for row in rows
        )
        commissions = tuple(
            row.provider_commission_per_volume_usd for row in rows
        )
        spread_p95 = _p95(spreads)
        commission_p95 = _p95(commissions)
        slippage_p95 = (
            execution.p95_adverse_slippage_cost_per_volume_usd
        )
        summaries.append(
            T11SymbolLinearExecutionCost(
                qore_symbol=symbol,
                observation_count=len(rows),
                p95_quoted_spread_cost_per_volume_usd=spread_p95,
                p95_commission_cost_per_volume_usd=commission_p95,
                p95_adverse_slippage_cost_per_volume_usd=slippage_p95,
                p95_linear_execution_cost_per_volume_usd=(
                    spread_p95 + commission_p95 + slippage_p95
                ),
            )
        )

    required = set(CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS.symbols)
    coverage = required.issubset(
        item.qore_symbol for item in summaries
    )
    provider_ready = (
        manifest.ready_for_scientific_consumption
        and execution_calibration.execution_model_ready
    )
    linear_ready = provider_ready and coverage and bool(summaries)

    blockers: list[str] = []
    if not manifest.ready_for_scientific_consumption:
        blockers.append("T11_FORWARD_MANIFEST_NOT_SCIENTIFICALLY_READY")
    if not execution_calibration.execution_model_ready:
        blockers.append("T11_PROVIDER_EXECUTION_MODEL_NOT_READY")
    if not coverage:
        blockers.append("T11_REQUIRED_SYMBOL_COST_COVERAGE_INCOMPLETE")
    blockers.extend(
        (
            "T11_GROSS_EDGE_MODEL_NOT_IDENTIFIED",
            "T11_MARKET_IMPACT_MODEL_NOT_IDENTIFIED",
            "T11_HISTORICAL_2017_EXECUTION_TERMS_NOT_PROVEN",
        )
    )

    return CiboT11ExecutionCostCalibration(
        manifest_sha256=manifest.fingerprint(),
        execution_calibration_sha256=execution_calibration.fingerprint(),
        symbols=tuple(summaries),
        required_symbol_coverage_met=coverage,
        provider_execution_model_ready=provider_ready,
        linear_cost_model_ready=linear_ready,
        gross_edge_model_ready=False,
        market_impact_model_ready=False,
        historical_2017_execution_terms_proven=False,
        t11_policy_ready=False,
        productive_authority=False,
        blockers=tuple(dict.fromkeys(blockers)),
    )


def _p95(values: tuple[Decimal, ...]) -> Decimal:
    if not values:
        raise CiboCapitalManagementError(
            "T11 linear execution percentile requires values"
        )
    ordered = tuple(sorted(values))
    index = max(0, ceil(Decimal("0.95") * Decimal(len(ordered))) - 1)
    return ordered[index]


def _sha(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"T11 execution calibration {name} must be canonical SHA-256"
        )
