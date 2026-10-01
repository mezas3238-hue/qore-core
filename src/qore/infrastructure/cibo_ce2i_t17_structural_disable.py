"""Provider-bound structural-disable evidence for CE2I T17.

T17 may be structurally disabled only when the currently governed cTrader DEMO
account has complete provider-native taxonomy evidence, no option taxonomy
candidate, is explicitly not a Limited Risk account, and every observed CIBO
provider symbol explicitly reports Guaranteed Stop Loss unavailable.

This is scoped to the observed provider/account universe. It is not a global
claim about cTrader, other brokers, future catalogs, or other accounts, and it
grants no productive authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)

T17_STRUCTURAL_DISABLE_EVIDENCE_ID = (
    "CIBO_T17_PROVIDER_BOUND_STRUCTURAL_DISABLE_EVIDENCE_V1"
)


@dataclass(frozen=True, slots=True)
class CiboT17StructuralDisableEvidence:
    evidence_id: str
    provider_key: str
    environment: str
    account_fingerprint_sha256: str
    taxonomy_binding_complete: bool
    option_taxonomy_candidates: tuple[str, ...]
    account_limited_risk: bool | None
    observed_symbols: int
    gsl_supported_symbols: tuple[str, ...]
    gsl_unsupported_symbols: tuple[str, ...]
    gsl_unknown_symbols: tuple[str, ...]
    provider_universe_gsl_coverage_complete: bool
    limited_risk_candidate_identified: bool
    structurally_disabled_for_current_account: bool
    blockers: tuple[str, ...]
    scope: str = "CURRENT_CTRADER_DEMO_ACCOUNT_AND_GOVERNED_CIBO_SYMBOL_UNIVERSE"
    broker_mutation_performed: bool = False
    holdout_outcomes_used: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if self.evidence_id != T17_STRUCTURAL_DISABLE_EVIDENCE_ID:
            raise CiboCapitalManagementError(
                "T17 structural-disable evidence identity drift"
            )
        if self.provider_key != "ctrader-demo" or self.environment != "demo":
            raise CiboCapitalManagementError(
                "T17 structural-disable evidence provider/environment mismatch"
            )
        if (
            not isinstance(self.account_fingerprint_sha256, str)
            or len(self.account_fingerprint_sha256) != 64
            or any(
                char not in "0123456789abcdef"
                for char in self.account_fingerprint_sha256
            )
        ):
            raise CiboCapitalManagementError(
                "T17 structural-disable account fingerprint invalid"
            )
        for name in (
            "taxonomy_binding_complete",
            "provider_universe_gsl_coverage_complete",
            "limited_risk_candidate_identified",
            "structurally_disabled_for_current_account",
            "broker_mutation_performed",
            "holdout_outcomes_used",
            "productive_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"T17 structural-disable {name} must be bool"
                )
        if self.account_limited_risk is not None and (
            type(self.account_limited_risk) is not bool
        ):
            raise CiboCapitalManagementError(
                "T17 structural-disable account_limited_risk must be bool/null"
            )
        if (
            not isinstance(self.observed_symbols, int)
            or isinstance(self.observed_symbols, bool)
            or self.observed_symbols < 0
        ):
            raise CiboCapitalManagementError(
                "T17 structural-disable observed_symbols invalid"
            )
        partitions = (
            self.gsl_supported_symbols
            + self.gsl_unsupported_symbols
            + self.gsl_unknown_symbols
        )
        if (
            len(partitions) != len(set(partitions))
            or len(partitions) != self.observed_symbols
        ):
            raise CiboCapitalManagementError(
                "T17 structural-disable GSL partition drift"
            )
        expected = _structurally_disabled(
            taxonomy_binding_complete=self.taxonomy_binding_complete,
            option_taxonomy_candidates=self.option_taxonomy_candidates,
            account_limited_risk=self.account_limited_risk,
            observed_symbols=self.observed_symbols,
            gsl_supported_symbols=self.gsl_supported_symbols,
            gsl_unsupported_symbols=self.gsl_unsupported_symbols,
            gsl_unknown_symbols=self.gsl_unknown_symbols,
            provider_universe_gsl_coverage_complete=(
                self.provider_universe_gsl_coverage_complete
            ),
            limited_risk_candidate_identified=(
                self.limited_risk_candidate_identified
            ),
        )
        if self.structurally_disabled_for_current_account != expected:
            raise CiboCapitalManagementError(
                "T17 structural-disable verdict drift"
            )
        if expected and self.blockers:
            raise CiboCapitalManagementError(
                "T17 structurally-disabled evidence cannot retain blockers"
            )
        if not expected and not self.blockers:
            raise CiboCapitalManagementError(
                "T17 open structural-disable evidence requires blockers"
            )
        if (
            self.broker_mutation_performed
            or self.holdout_outcomes_used
            or self.productive_authority
        ):
            raise CiboCapitalManagementError(
                "T17 structural-disable evidence cannot mutate/promote authority"
            )

    def fingerprint(self) -> str:
        raw = json.dumps(
            _canonical(asdict(self)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(raw).hexdigest()


def assess_t17_structural_disable(
    *,
    provider_key: str,
    environment: str,
    account_fingerprint_sha256: str,
    taxonomy_binding_complete: bool,
    option_taxonomy_candidates: tuple[str, ...],
    account_limited_risk: bool | None,
    observed_symbols: int,
    gsl_supported_symbols: tuple[str, ...],
    gsl_unsupported_symbols: tuple[str, ...],
    gsl_unknown_symbols: tuple[str, ...],
    provider_universe_gsl_coverage_complete: bool,
    limited_risk_candidate_identified: bool,
) -> CiboT17StructuralDisableEvidence:
    blockers: list[str] = []
    if not taxonomy_binding_complete:
        blockers.append("T17_STRUCTURAL_DISABLE_TAXONOMY_INCOMPLETE")
    if option_taxonomy_candidates:
        blockers.append("T17_STRUCTURAL_DISABLE_OPTION_TAXONOMY_PRESENT")
    if account_limited_risk is not False:
        blockers.append("T17_STRUCTURAL_DISABLE_LIMITED_RISK_NOT_EXPLICITLY_FALSE")
    if observed_symbols <= 0:
        blockers.append("T17_STRUCTURAL_DISABLE_PROVIDER_UNIVERSE_EMPTY")
    if not provider_universe_gsl_coverage_complete or gsl_unknown_symbols:
        blockers.append("T17_STRUCTURAL_DISABLE_GSL_COVERAGE_INCOMPLETE")
    if gsl_supported_symbols:
        blockers.append("T17_STRUCTURAL_DISABLE_GSL_SUPPORT_PRESENT")
    if len(gsl_unsupported_symbols) != observed_symbols:
        blockers.append("T17_STRUCTURAL_DISABLE_GSL_UNAVAILABLE_NOT_UNIVERSAL")
    if limited_risk_candidate_identified:
        blockers.append("T17_STRUCTURAL_DISABLE_LIMITED_RISK_CANDIDATE_PRESENT")

    structural = not blockers
    return CiboT17StructuralDisableEvidence(
        evidence_id=T17_STRUCTURAL_DISABLE_EVIDENCE_ID,
        provider_key=provider_key,
        environment=environment,
        account_fingerprint_sha256=account_fingerprint_sha256,
        taxonomy_binding_complete=taxonomy_binding_complete,
        option_taxonomy_candidates=option_taxonomy_candidates,
        account_limited_risk=account_limited_risk,
        observed_symbols=observed_symbols,
        gsl_supported_symbols=gsl_supported_symbols,
        gsl_unsupported_symbols=gsl_unsupported_symbols,
        gsl_unknown_symbols=gsl_unknown_symbols,
        provider_universe_gsl_coverage_complete=(
            provider_universe_gsl_coverage_complete
        ),
        limited_risk_candidate_identified=limited_risk_candidate_identified,
        structurally_disabled_for_current_account=structural,
        blockers=tuple(blockers),
    )


def _structurally_disabled(
    *,
    taxonomy_binding_complete: bool,
    option_taxonomy_candidates: tuple[str, ...],
    account_limited_risk: bool | None,
    observed_symbols: int,
    gsl_supported_symbols: tuple[str, ...],
    gsl_unsupported_symbols: tuple[str, ...],
    gsl_unknown_symbols: tuple[str, ...],
    provider_universe_gsl_coverage_complete: bool,
    limited_risk_candidate_identified: bool,
) -> bool:
    return all(
        (
            taxonomy_binding_complete,
            not option_taxonomy_candidates,
            account_limited_risk is False,
            observed_symbols > 0,
            provider_universe_gsl_coverage_complete,
            not gsl_supported_symbols,
            not gsl_unknown_symbols,
            len(gsl_unsupported_symbols) == observed_symbols,
            not limited_risk_candidate_identified,
        )
    )


def _canonical(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value
