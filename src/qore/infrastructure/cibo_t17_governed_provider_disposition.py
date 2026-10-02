"""Governed-provider terminal disposition for CIBO CE2I T17.

This closes T17 only for the currently governed provider universe when the
checked-in provider evidence proves that no admissible limited-downside path
exists. It is not a global market claim and grants no runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

DISPOSITION_ID = "CIBO_T17_GOVERNED_PROVIDER_DISPOSITION_V1"
TERMINAL_DISPOSITION = "COMPLETED_PROVIDER_INELIGIBLE"
_PROVIDER_SCHEMA = "CIBO_B_CTRADER_DEMO_PROVIDER_EVIDENCE_V2026_10_01"
_STRUCTURAL_SCHEMA = "CIBO_B_T17_STRUCTURAL_DISPOSITION_V1"


@dataclass(frozen=True, slots=True)
class CiboT17GovernedProviderDisposition:
    disposition_id: str
    provider_scope: tuple[str, ...]
    terminal_disposition: str
    provider_ineligible: bool
    evidence_refs: tuple[str, ...]
    reopen_conditions: tuple[str, ...]
    global_market_claim: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.disposition_id != DISPOSITION_ID:
            raise CiboCapitalManagementError(
                "T17 governed-provider disposition identity drift"
            )
        if self.provider_scope != (
            "ctrader-demo",
            "fundednext-stellar-instant-cfd",
        ):
            raise CiboCapitalManagementError(
                "T17 governed-provider scope drift"
            )
        expected = TERMINAL_DISPOSITION if self.provider_ineligible else ""
        if self.terminal_disposition != expected:
            raise CiboCapitalManagementError(
                "T17 governed-provider terminal disposition drift"
            )
        if not self.evidence_refs:
            raise CiboCapitalManagementError(
                "T17 governed-provider evidence refs required"
            )
        if self.provider_ineligible and not self.reopen_conditions:
            raise CiboCapitalManagementError(
                "T17 provider-ineligible closure needs reopen conditions"
            )
        if self.global_market_claim or self.productive_authority:
            raise CiboCapitalManagementError(
                "T17 governed-provider closure cannot overclaim authority"
            )


def assess_t17_governed_provider_disposition(
    *,
    provider_evidence: dict[str, Any],
    structural_disposition: dict[str, Any],
) -> CiboT17GovernedProviderDisposition:
    if provider_evidence.get("schema") != _PROVIDER_SCHEMA:
        raise CiboCapitalManagementError(
            "T17 governed-provider provider-evidence schema drift"
        )
    if structural_disposition.get("schema") != _STRUCTURAL_SCHEMA:
        raise CiboCapitalManagementError(
            "T17 governed-provider structural schema drift"
        )

    account = _mapping(provider_evidence, "account_capability")
    universe = _mapping(provider_evidence, "governed_universe")
    governance = _mapping(provider_evidence, "governance")
    ctd = _mapping(structural_disposition, "ctrader_demo")
    fundednext = _mapping(
        structural_disposition,
        "fundednext_stellar_instant_cfd",
    )
    paths = _mapping(structural_disposition, "admissible_paths")
    conclusion = _mapping(structural_disposition, "conclusion")
    structural_governance = _mapping(
        structural_disposition,
        "governance",
    )

    symbols = _strings(universe, "symbols")
    unsupported = _strings(universe, "gsl_unsupported_symbols")
    if not symbols:
        raise CiboCapitalManagementError(
            "T17 governed-provider symbol universe empty"
        )

    ctrader_ineligible = all(
        (
            account.get("taxonomy_binding_complete") is True,
            account.get("is_limited_risk") is False,
            _strings(account, "option_taxonomy_candidates") == (),
            universe.get("provider_universe_gsl_coverage_complete") is True,
            _strings(universe, "gsl_supported_symbols") == (),
            _strings(universe, "gsl_unknown_symbols") == (),
            set(unsupported) == set(symbols),
            universe.get("limited_risk_candidate_identified") is False,
            ctd.get("taxonomy_binding_complete") is True,
            ctd.get("account_limited_risk") is False,
            ctd.get("limited_risk_candidate_identified") is False,
            ctd.get("option_structure_proven") is False,
            ctd.get("defined_risk_spread_proven") is False,
        )
    )
    if not ctrader_ineligible:
        raise CiboCapitalManagementError(
            "T17 cTrader provider-ineligibility not proven"
        )

    source_urls = _strings(fundednext, "source_urls")
    if not source_urls or any(
        not (
            url.startswith("https://fundednext.com/")
            or url.startswith("https://help.fundednext.com/")
        )
        for url in source_urls
    ):
        raise CiboCapitalManagementError(
            "T17 FundedNext official source binding invalid"
        )
    asset_classes = _strings(
        fundednext,
        "comprehensive_cfd_asset_classes",
    )
    if not asset_classes:
        raise CiboCapitalManagementError(
            "T17 FundedNext CFD asset classes missing"
        )
    fundednext_ineligible = (
        fundednext.get("evidence_type") == "OFFICIAL_PROVIDER_POLICY"
        and fundednext.get(
            "option_or_defined_risk_instrument_class_listed"
        )
        is False
        and not any("option" in item.lower() for item in asset_classes)
    )
    if not fundednext_ineligible:
        raise CiboCapitalManagementError(
            "T17 FundedNext provider-ineligibility not proven"
        )

    expected_false = (
        "option_contracts_available",
        "defined_risk_option_spreads_available",
        "limited_risk_account_available",
        "guaranteed_stop_loss_available_on_governed_ctrader_universe",
    )
    if any(paths.get(key) is not False for key in expected_false):
        raise CiboCapitalManagementError(
            "T17 admissible-path disposition conflicts with provider facts"
        )
    if conclusion.get("structurally_disabled") is not True:
        raise CiboCapitalManagementError(
            "T17 structural conclusion must remain disabled"
        )
    if conclusion.get("global_market_claim") is not False:
        raise CiboCapitalManagementError(
            "T17 structural conclusion cannot be a global market claim"
        )

    for block in (governance, structural_governance):
        if any(
            block.get(key) is not False
            for key in (
                "broker_mutation_performed",
                "productive_authority",
                "live_authority",
                "real_capital_authority",
                "holdout_2017h1_opened",
            )
            if key in block
        ):
            raise CiboCapitalManagementError(
                "T17 governed-provider evidence violates governance"
            )

    reopen_conditions = tuple(
        item
        for item in conclusion.get("reopen_conditions", [])
        if isinstance(item, str) and item
    )
    if not reopen_conditions:
        raise CiboCapitalManagementError(
            "T17 governed-provider reopen conditions missing"
        )

    return CiboT17GovernedProviderDisposition(
        disposition_id=DISPOSITION_ID,
        provider_scope=(
            "ctrader-demo",
            "fundednext-stellar-instant-cfd",
        ),
        terminal_disposition=TERMINAL_DISPOSITION,
        provider_ineligible=True,
        evidence_refs=(
            "docs/research/"
            "CIBO-B-CTRADER-DEMO-PROVIDER-EVIDENCE-2026-10-01.json",
            "docs/research/"
            "CIBO-B-T17-STRUCTURAL-DISPOSITION-V1.json",
            *source_urls,
        ),
        reopen_conditions=reopen_conditions,
    )


def _mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise CiboCapitalManagementError(
            f"T17 governed-provider {key} object missing"
        )
    return value


def _strings(payload: dict[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise CiboCapitalManagementError(
            f"T17 governed-provider {key} list invalid"
        )
    return tuple(value)
