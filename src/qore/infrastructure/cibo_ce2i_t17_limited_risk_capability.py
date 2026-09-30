"""Provider-bound T17 limited-risk / Guaranteed Stop Loss capability assessment.

This bridge combines account-level Limited Risk evidence with the observed
cTrader DEMO provider economics for the CIBO trading universe. It can identify
whether a provider-native guaranteed-downside candidate exists. It does not
equate GSL with an option or defined-risk spread, does not prove execution
quality or economic utility, and never grants productive authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
)
from qore.infrastructure.cibo_ctrader_demo_provider_economics import (
    CTraderProviderEconomicsProbe,
)


@dataclass(frozen=True, slots=True)
class CiboT17LimitedRiskCapabilityAssessment:
    account_limited_risk: bool | None
    observed_symbols: int
    gsl_supported_symbols: tuple[str, ...]
    gsl_unsupported_symbols: tuple[str, ...]
    gsl_unknown_symbols: tuple[str, ...]
    provider_universe_gsl_coverage_complete: bool
    limited_risk_candidate_identified: bool
    option_structure_proven: bool
    defined_risk_spread_proven: bool
    gsl_execution_economics_proven: bool
    fresh_oos_utility_demonstrated: bool
    t17_policy_ready: bool
    productive_authority: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.account_limited_risk is not None and (
            type(self.account_limited_risk) is not bool
        ):
            raise CiboCapitalManagementError(
                "T17 account_limited_risk must be bool/null"
            )
        if (
            not isinstance(self.observed_symbols, int)
            or isinstance(self.observed_symbols, bool)
            or self.observed_symbols < 0
        ):
            raise CiboCapitalManagementError(
                "T17 observed_symbols must be non-negative int"
            )
        all_symbols = (
            self.gsl_supported_symbols
            + self.gsl_unsupported_symbols
            + self.gsl_unknown_symbols
        )
        if len(all_symbols) != len(set(all_symbols)):
            raise CiboCapitalManagementError(
                "T17 GSL symbol partitions must be disjoint"
            )
        if len(all_symbols) != self.observed_symbols:
            raise CiboCapitalManagementError(
                "T17 GSL symbol partition count drift"
            )
        expected_coverage = (
            self.observed_symbols > 0 and not self.gsl_unknown_symbols
        )
        if self.provider_universe_gsl_coverage_complete != expected_coverage:
            raise CiboCapitalManagementError(
                "T17 GSL provider-universe coverage drift"
            )
        expected_candidate = (
            self.account_limited_risk is True
            and expected_coverage
            and len(self.gsl_supported_symbols) == self.observed_symbols
        )
        if self.limited_risk_candidate_identified != expected_candidate:
            raise CiboCapitalManagementError(
                "T17 limited-risk candidate identity drift"
            )
        for name in (
            "provider_universe_gsl_coverage_complete",
            "limited_risk_candidate_identified",
            "option_structure_proven",
            "defined_risk_spread_proven",
            "gsl_execution_economics_proven",
            "fresh_oos_utility_demonstrated",
            "t17_policy_ready",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T17 {name} must be bool"
                )
        if (
            self.option_structure_proven
            or self.defined_risk_spread_proven
            or self.gsl_execution_economics_proven
            or self.fresh_oos_utility_demonstrated
            or self.t17_policy_ready
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T17 capability assessment cannot promote unresolved policy evidence"
            )


def assess_t17_limited_risk_capability(
    *,
    account: CTraderDemoAccountCapabilityObservation,
    provider: CTraderProviderEconomicsProbe,
) -> CiboT17LimitedRiskCapabilityAssessment:
    """Identify a provider-native GSL candidate while preserving fail-closed T17."""

    if not isinstance(account, CTraderDemoAccountCapabilityObservation):
        raise CiboCapitalManagementError(
            "T17 limited-risk assessment requires account capability evidence"
        )
    if not isinstance(provider, CTraderProviderEconomicsProbe):
        raise CiboCapitalManagementError(
            "T17 limited-risk assessment requires provider economics evidence"
        )
    if account.account_ref != provider.account_ref:
        raise CiboCapitalManagementError(
            "T17 limited-risk account/provider binding mismatch"
        )

    supported = tuple(
        sorted(
            row.qore_symbol
            for row in provider.symbols
            if row.guaranteed_stop_loss is True
        )
    )
    unsupported = tuple(
        sorted(
            row.qore_symbol
            for row in provider.symbols
            if row.guaranteed_stop_loss is False
        )
    )
    unknown = tuple(
        sorted(
            row.qore_symbol
            for row in provider.symbols
            if row.guaranteed_stop_loss is None
        )
    )
    count = len(provider.symbols)
    coverage = count > 0 and not unknown
    candidate = (
        account.is_limited_risk is True
        and coverage
        and len(supported) == count
    )

    blockers: list[str] = []
    if account.is_limited_risk is None:
        blockers.append("T17_LIMITED_RISK_ACCOUNT_FIELD_UNKNOWN")
    elif account.is_limited_risk is False:
        blockers.append("T17_ACCOUNT_NOT_LIMITED_RISK")
    if not coverage:
        blockers.append("T17_GSL_PROVIDER_UNIVERSE_COVERAGE_INCOMPLETE")
    if unsupported:
        blockers.append(
            "T17_GSL_UNAVAILABLE_ON_PROVIDER_SYMBOLS:"
            + ",".join(unsupported)
        )
    if candidate:
        blockers.extend(
            (
                "T17_GSL_CANDIDATE_EXECUTION_ECONOMICS_NOT_PROVEN",
                "T17_GSL_CANDIDATE_FRESH_OOS_UTILITY_NOT_PROVEN",
            )
        )
    blockers.extend(
        (
            "T17_OPTION_STRUCTURE_NOT_PROVEN",
            "T17_DEFINED_RISK_SPREAD_NOT_PROVEN",
        )
    )

    return CiboT17LimitedRiskCapabilityAssessment(
        account_limited_risk=account.is_limited_risk,
        observed_symbols=count,
        gsl_supported_symbols=supported,
        gsl_unsupported_symbols=unsupported,
        gsl_unknown_symbols=unknown,
        provider_universe_gsl_coverage_complete=coverage,
        limited_risk_candidate_identified=candidate,
        option_structure_proven=False,
        defined_risk_spread_proven=False,
        gsl_execution_economics_proven=False,
        fresh_oos_utility_demonstrated=False,
        t17_policy_ready=False,
        productive_authority=False,
        blockers=tuple(blockers),
    )
