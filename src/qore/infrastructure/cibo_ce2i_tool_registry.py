"""CE2I capital-tool registry for CIBO CMA research.

The registry is declarative. It gives future capital tools a stable identity and
evidence/authority contract before any tool can affect DEMO or LIVE behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToolMaturity(StrEnum):
    ARCHITECTURE_ONLY = "ARCHITECTURE_ONLY"
    CONTRACT_IMPLEMENTED = "CONTRACT_IMPLEMENTED"
    RESEARCH_VALIDATED = "RESEARCH_VALIDATED"
    HOLDOUT_VALIDATED = "HOLDOUT_VALIDATED"
    SHADOW_VALIDATED = "SHADOW_VALIDATED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class Ce2iToolContract:
    code: str
    name: str
    purpose: str
    required_evidence: tuple[str, ...]
    eligible_capital_sources: tuple[str, ...]
    risk_effect: str
    margin_effect: str
    portfolio_effect: str
    rollback_condition: str
    roadmap_phase: int
    maturity: ToolMaturity

    def __post_init__(self) -> None:
        for field in (
            "code",
            "name",
            "purpose",
            "risk_effect",
            "margin_effect",
            "portfolio_effect",
            "rollback_condition",
        ):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be non-empty")
        if not self.required_evidence:
            raise ValueError("required_evidence cannot be empty")
        if not self.eligible_capital_sources:
            raise ValueError("eligible_capital_sources cannot be empty")
        if self.roadmap_phase < 0:
            raise ValueError("roadmap_phase cannot be negative")
        if type(self.maturity) is not ToolMaturity:
            raise ValueError("maturity must be ToolMaturity")


def _tool(
    code: str,
    name: str,
    purpose: str,
    evidence: tuple[str, ...],
    sources: tuple[str, ...],
    risk: str,
    margin: str,
    portfolio: str,
    rollback: str,
    phase: int,
    maturity: ToolMaturity = ToolMaturity.ARCHITECTURE_ONLY,
) -> Ce2iToolContract:
    return Ce2iToolContract(
        code=code,
        name=name,
        purpose=purpose,
        required_evidence=evidence,
        eligible_capital_sources=sources,
        risk_effect=risk,
        margin_effect=margin,
        portfolio_effect=portfolio,
        rollback_condition=rollback,
        roadmap_phase=phase,
        maturity=maturity,
    )


CE2I_TOOL_REGISTRY: tuple[Ce2iToolContract, ...] = (
    _tool(
        "T01",
        "Minimal Seed",
        "Enter a valid Trader opportunity with the smallest viable executable exposure.",
        ("TRADER_OPPORTUNITY_ENVELOPE", "PROVIDER_VOLUME_RULES", "RISK_HEADROOM"),
        ("ORIGINAL_BASE_CAPITAL",),
        "MINIMIZE_NEW_BASE_STOP_RISK",
        "MINIMIZE_INITIAL_MARGIN",
        "PRESERVE_FUTURE_CAPACITY",
        "NO_EXECUTABLE_MINIMUM_OR_HARD_LIMIT_BREACH",
        5,
        ToolMaturity.CONTRACT_IMPLEMENTED,
    ),
    _tool(
        "T02",
        "Structural Leverage",
        "Increase exposure only when verified structural precision supports it.",
        ("VERIFIED_STRUCTURAL_INVALIDATION", "OUT_OF_SAMPLE_STOP_EVIDENCE"),
        ("RELEASED_RISK_CAPACITY", "PROTECTED_ECONOMIC_FLOOR"),
        "CONSTANT_OR_LOWER_BASE_LOSS_TARGET",
        "MAY_INCREASE_MARGIN",
        "INCREASES_DIRECTIONAL_EXPOSURE",
        "EXPECTANCY_OR_SURVIVABILITY_DEGRADES",
        9,
    ),
    _tool(
        "T03",
        "Margin Efficiency",
        "Choose an economically equivalent expression with lower margin consumption.",
        ("NORMALIZED_EXPOSURE", "PROVIDER_MARGIN_ECONOMICS"),
        ("RELEASED_MARGIN_CAPACITY", "ORIGINAL_BASE_CAPITAL"),
        "NO_SILENT_RISK_INCREASE",
        "TARGET_LOWER_MARGIN_PER_EXPOSURE",
        "PRESERVE_MORE_PORTFOLIO_CAPACITY",
        "NORMALIZATION_OR_EXECUTION_ADVANTAGE_DISAPPEARS",
        12,
    ),
    _tool(
        "T04",
        "Risk Efficiency",
        "Maximize robust output per true monetary stop-risk dollar.",
        ("CHRONOLOGICAL_EXPECTANCY", "TRUE_STOP_RISK"),
        ("ORIGINAL_BASE_CAPITAL", "REALIZED_PROFIT"),
        "OPTIMIZE_RETURN_PER_RISK",
        "BOUNDED_BY_MARGIN",
        "COMPARE_INCREMENTAL_PORTFOLIO_RISK",
        "TAIL_RISK_OR_DRAWDOWN_WORSENS_BEYOND_GATE",
        9,
    ),
    _tool(
        "T05",
        "Capital Recycling",
        "Reuse capacity only after authoritative release and reconciliation.",
        ("CAPITAL_SOURCE_LEDGER", "POSITION_RECONCILIATION"),
        ("RELEASED_RISK_CAPACITY", "RELEASED_MARGIN_CAPACITY"),
        "NO_NEW_BASE_CAPITAL_REQUIRED",
        "REUSES_RELEASED_MARGIN",
        "INCREASES_CAPITAL_VELOCITY",
        "SOURCE_NOT_RECONCILED_OR_DOUBLE_SPEND_RISK",
        10,
        ToolMaturity.CONTRACT_IMPLEMENTED,
    ),
    _tool(
        "T06",
        "Profit-Funded Expansion",
        "Deploy realized net profit as bounded expansion funding.",
        ("REALIZED_NET_PROFIT", "COST_RESERVE", "RISK_AUTHORIZATION"),
        ("REALIZED_PROFIT",),
        "EXPANSION_RISK_CAPPED_BY_REALIZED_CAPACITY",
        "MAY_INCREASE_MARGIN",
        "INCREASES_EXPOSURE_WITHOUT_NEW_BASE_SOURCE",
        "REALIZED_CAPACITY_EXHAUSTED_OR_TAIL_GATE_FAILS",
        11,
        ToolMaturity.CONTRACT_IMPLEMENTED,
    ),
    _tool(
        "T07",
        "Protected-Capacity Expansion",
        "Use reconciled protected economic floor as bounded funding capacity.",
        ("PROTECTED_ECONOMIC_FLOOR", "BROKER_CONFIRMED_PROTECTION", "COST_RESERVE"),
        ("PROTECTED_ECONOMIC_FLOOR",),
        "EXPANSION_RISK_CAPPED_BY_PROTECTED_CAPACITY",
        "MAY_INCREASE_MARGIN",
        "INCREASES_EXPOSURE_AFTER_BASE_PROTECTION",
        "PROTECTION_DEGRADES_OR_RECONCILIATION_IS_STALE",
        11,
        ToolMaturity.CONTRACT_IMPLEMENTED,
    ),
    _tool(
        "T08",
        "Portfolio Netting",
        "Measure real net/factor exposure instead of nominal trade count.",
        ("FACTOR_MAP", "POSITION_EXPOSURES", "CORRELATION_STATE"),
        ("TRUE_PORTFOLIO_NETTING",),
        "REDUCE_DUPLICATED_FACTOR_RISK",
        "MAY_RELEASE_OR_CONSUME_MARGIN",
        "CHANGES_INCREMENTAL_PORTFOLIO_EXPOSURE",
        "CORRELATION_OR_FACTOR_ASSUMPTION_BREAKS",
        13,
    ),
    _tool(
        "T09",
        "Opportunity Competition",
        "Allocate scarce capital among simultaneous valid opportunities.",
        ("CAPITAL_OPPORTUNITY_GRAPH", "CAPITAL_SOURCE_LEDGER", "OPPORTUNITY_SET"),
        ("ORIGINAL_BASE_CAPITAL", "REALIZED_PROFIT", "RELEASED_RISK_CAPACITY"),
        "ALLOCATE_WITHIN_HARD_ACCOUNT_LIMITS",
        "COMPETE_FOR_MARGIN",
        "PORTFOLIO_LEVEL_ALLOCATION",
        "STARVATION_OR_TAIL_RISK_GATE_FAILS",
        14,
    ),
    _tool(
        "T10",
        "Capital Velocity",
        "Optimize output per unit of capital-at-risk time.",
        ("TIME_AT_RISK", "REALIZED_OUTPUT", "CAPITAL_RELEASE_TIMESTAMPS"),
        ("RELEASED_RISK_CAPACITY", "RELEASED_MARGIN_CAPACITY"),
        "NO_AUTOMATIC_RISK_INCREASE",
        "TARGET_SHORTER_CAPITAL_BLOCK_TIME",
        "PRESERVE_FUTURE_OPPORTUNITY_CAPACITY",
        "VELOCITY_GAIN_REQUIRES_EXPECTANCY_DEGRADATION",
        9,
    ),
    _tool(
        "T11",
        "Execution-Efficient Exposure",
        "Stop adding size when marginal execution cost destroys edge.",
        ("VOLUME_COST_CURVE", "SPREAD", "SLIPPAGE", "COMMISSION", "LATENCY"),
        ("ORIGINAL_BASE_CAPITAL", "REALIZED_PROFIT", "PROTECTED_ECONOMIC_FLOOR"),
        "CAP_AT_NET_EXPECTANCY_OPTIMUM",
        "CAP_AT_EXECUTION_EFFICIENT_VOLUME",
        "PREVENT_OVER-SIZING",
        "MARGINAL_NET_EXPECTANCY_NON_POSITIVE",
        12,
    ),
    _tool(
        "T12",
        "Regime-Adaptive Capitalization",
        "Select eligible capital tools from current market/account regime.",
        ("CAUSAL_REGIME_STATE", "TOOL_ELIGIBILITY", "ACCOUNT_STATE"),
        ("ORIGINAL_BASE_CAPITAL", "REALIZED_PROFIT", "RELEASED_RISK_CAPACITY"),
        "TOOL_DEPENDENT",
        "TOOL_DEPENDENT",
        "TOOL_DEPENDENT",
        "REGIME_EVIDENCE_STALE_OR_TOOL_INELIGIBLE",
        15,
    ),
    _tool(
        "T13",
        "Drawdown Reserve",
        "Keep capital unused when reserve has greater survival/optionality value.",
        ("DRAWDOWN_STATE", "LOSS_CLUSTER_STATE", "FUTURE_OPPORTUNITY_DENSITY"),
        ("ORIGINAL_BASE_CAPITAL", "REALIZED_PROFIT"),
        "REDUCE_DEPLOYED_RISK",
        "REDUCE_MARGIN_USAGE",
        "INCREASE_RESERVE_AND_SURVIVAL_CAPACITY",
        "RESERVE_POLICY_UNDERPERFORMS_OUT_OF_SAMPLE",
        16,
    ),
    _tool(
        "T14",
        "Dynamic De-risking",
        "Reduce consumed capital risk while retaining useful participation.",
        ("POSITION_PATH", "CURRENT_PROTECTION", "EXECUTION_COST"),
        ("REDUCED_OTHER_EXPOSURE",),
        "REDUCE_CURRENT_WORST_CASE_LOSS",
        "MAY_RELEASE_MARGIN",
        "RELEASE_CAPACITY",
        "DE_RISKING_DESTROYS_EXPECTANCY_BEYOND_GATE",
        17,
    ),
    _tool(
        "T15",
        "Capital Optionality",
        "Value preserved capacity for the next valid opportunity.",
        ("CURRENT_CAPACITY", "OPPORTUNITY_ARRIVAL_EVIDENCE", "PORTFOLIO_STATE"),
        ("ORIGINAL_BASE_CAPITAL", "REALIZED_PROFIT", "RELEASED_MARGIN_CAPACITY"),
        "MAY_PREFER_LOWER_CURRENT_RISK",
        "MAY_PREFER_LOWER_CURRENT_MARGIN",
        "MAXIMIZE_NEXT_OPPORTUNITY_CAPACITY",
        "OPTIONALITY_SIGNAL_HAS_NO_OUT_OF_SAMPLE_VALUE",
        16,
    ),
    _tool(
        "T16",
        "Hedged Exposure / Risk Transfer",
        "Transfer selected unwanted risk when net economics improve.",
        ("HEDGE_INSTRUMENT", "BASIS_RISK", "HEDGE_COST", "CORRELATION_STABILITY"),
        ("CERTIFIED_LIMITED_DOWNSIDE_CAPACITY", "REALIZED_PROFIT"),
        "TARGET_LOWER_NET_UNWANTED_RISK",
        "MAY_INCREASE_GROSS_MARGIN",
        "ALTER_FACTOR_EXPOSURE",
        "HEDGE_COST_OR_BASIS_RISK_ERASES_BENEFIT",
        17,
    ),
    _tool(
        "T17",
        "Convex / Limited-Downside Exposure",
        "Use separately certified bounded-downside structures.",
        ("INSTRUMENT_CERTIFICATION", "PRICING", "SETTLEMENT", "EXECUTION_SUPPORT"),
        ("CERTIFIED_LIMITED_DOWNSIDE_CAPACITY",),
        "EXPLICITLY_BOUNDED_DOWNSIDE",
        "INSTRUMENT_DEPENDENT",
        "ASYMMETRIC_PAYOFF",
        "PRICING_OR_EXECUTION_CERTIFICATION_FAILS",
        17,
    ),
    _tool(
        "T18",
        "Cross-Trader Capital Allocation",
        "Move available capacity toward the best current portfolio use.",
        ("CAPITAL_OPPORTUNITY_GRAPH", "TRADER_OPPORTUNITY_SET", "FACTOR_STATE"),
        ("ORIGINAL_BASE_CAPITAL", "REALIZED_PROFIT", "RELEASED_RISK_CAPACITY"),
        "ACCOUNT_LEVEL_ALLOCATION",
        "ACCOUNT_LEVEL_ALLOCATION",
        "REALLOCATE_ACROSS_TRADERS",
        "PORTFOLIO_TAIL_OR_STARVATION_GATE_FAILS",
        14,
    ),
    _tool(
        "T19",
        "Capacity Reservation",
        "Atomically reserve proven capacity before deployment.",
        ("CAPITAL_SOURCE_LEDGER",),
        ("ORIGINAL_BASE_CAPITAL", "REALIZED_PROFIT", "PROTECTED_ECONOMIC_FLOOR"),
        "PREVENT_DOUBLE_SPEND",
        "RESERVE_BEFORE_MARGIN_CONSUMPTION",
        "COORDINATE_CONCURRENT_OPPORTUNITIES",
        "RESERVATION_RECONCILIATION_FAULT",
        6,
        ToolMaturity.CONTRACT_IMPLEMENTED,
    ),
    _tool(
        "T20",
        "Capital Release",
        "Return reconciled unused/deployed capacity to the available pool.",
        ("CAPITAL_SOURCE_LEDGER", "RELEASE_EVIDENCE"),
        ("RELEASED_RISK_CAPACITY", "RELEASED_MARGIN_CAPACITY"),
        "LOWER_RESERVED_OR_DEPLOYED_RISK",
        "RELEASE_MARGIN_WHEN_APPLICABLE",
        "RESTORE_AVAILABLE_CAPACITY",
        "RELEASE_NOT_RECONCILED",
        6,
        ToolMaturity.CONTRACT_IMPLEMENTED,
    ),
)


def tool_by_code(code: str) -> Ce2iToolContract:
    found = tuple(tool for tool in CE2I_TOOL_REGISTRY if tool.code == code)
    if len(found) != 1:
        raise KeyError(code)
    return found[0]


def validate_registry() -> None:
    codes = tuple(tool.code for tool in CE2I_TOOL_REGISTRY)
    if len(codes) != len(set(codes)):
        raise ValueError("duplicate CE2I tool code")
    names = tuple(tool.name for tool in CE2I_TOOL_REGISTRY)
    if len(names) != len(set(names)):
        raise ValueError("duplicate CE2I tool name")
