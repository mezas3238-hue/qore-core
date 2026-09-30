"""Source-bound evidence artifact for CIBO T17 provider capability observation.

PASS in this artifact means only that account capability, provider economics,
instrument taxonomy and the fail-closed T17 assessment are internally
consistent and bound to one integrated Git HEAD/policy identity.

It never means T17 is economically valid, supported by options/spreads, or
ready for certification/production.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_t17_limited_risk_capability import (
    CiboT17LimitedRiskCapabilityAssessment,
    assess_t17_limited_risk_capability,
)
from qore.infrastructure.cibo_crossboundary_evidence_receipt import (
    CiboCrossBoundaryEvidenceReceipt,
    bind_cross_boundary_pass_artifact,
)
from qore.infrastructure.cibo_ctrader_demo_account_capability import (
    CTraderDemoAccountCapabilityObservation,
)
from qore.infrastructure.cibo_ctrader_demo_instrument_taxonomy import (
    CTraderDemoInstrumentTaxonomyObservation,
    assert_taxonomy_bound_to_capability,
)
from qore.infrastructure.cibo_ctrader_demo_provider_economics import (
    CTraderProviderEconomicsProbe,
)

_T17_GATE_ID = "QORE_CIBO_T17_PROVIDER_CAPABILITY_OBSERVATION_V1"
_T17_SCHEMA = "qore.cibo.t17.provider-capability-observation.v1"


def build_t17_provider_capability_source_artifact(
    *,
    account: CTraderDemoAccountCapabilityObservation,
    provider: CTraderProviderEconomicsProbe,
    taxonomy: CTraderDemoInstrumentTaxonomyObservation,
    assessment: CiboT17LimitedRiskCapabilityAssessment,
    integrated_git_sha: str,
    policy_identity_sha256: str,
) -> str:
    if not isinstance(account, CTraderDemoAccountCapabilityObservation):
        raise CiboCapitalManagementError(
            "T17 receipt requires canonical account capability observation"
        )
    if not isinstance(provider, CTraderProviderEconomicsProbe):
        raise CiboCapitalManagementError(
            "T17 receipt requires canonical provider economics observation"
        )
    if not isinstance(taxonomy, CTraderDemoInstrumentTaxonomyObservation):
        raise CiboCapitalManagementError(
            "T17 receipt requires canonical taxonomy observation"
        )
    if not isinstance(assessment, CiboT17LimitedRiskCapabilityAssessment):
        raise CiboCapitalManagementError(
            "T17 receipt requires canonical capability assessment"
        )
    if account.account_ref != provider.account_ref:
        raise CiboCapitalManagementError(
            "T17 receipt account/provider binding mismatch"
        )
    enabled_provider_symbols = {
        item.symbol_name for item in account.symbols if item.enabled
    }
    observed_provider_symbols = {item.provider_symbol for item in provider.symbols}
    if not observed_provider_symbols.issubset(enabled_provider_symbols):
        raise CiboCapitalManagementError(
            "T17 receipt provider universe not contained in enabled account catalog"
        )
    assert_taxonomy_bound_to_capability(
        capability=account,
        taxonomy=taxonomy,
    )
    if taxonomy.account_ref != account.account_ref:
        raise CiboCapitalManagementError(
            "T17 receipt taxonomy/account binding mismatch"
        )

    recomputed = assess_t17_limited_risk_capability(
        account=account,
        provider=provider,
    )
    if assessment != recomputed:
        raise CiboCapitalManagementError(
            "T17 receipt assessment does not match canonical recomputation"
        )

    _git_sha(integrated_git_sha)
    _sha256(policy_identity_sha256, "policy_identity_sha256")
    observed_at = max(
        account.observed_at,
        provider.observed_at,
        taxonomy.observed_at,
    )
    _aware(observed_at, "observed_at")

    payload: dict[str, Any] = {
        "schema": _T17_SCHEMA,
        "producer_gate_id": _T17_GATE_ID,
        "integrated_git_sha": integrated_git_sha,
        "policy_identity_sha256": policy_identity_sha256,
        "observed_at": observed_at.isoformat(),
        "status": "PASS",
        "failures": [],
        "holdout_outcomes_inspected": False,
        "productive_authority": False,
        "synthetic_evidence_used": False,
        "holdout_mining_used": False,
        "outcome_aware_refit": False,
        "operational_authority_claimed": False,
        "account_fingerprint_sha256": account.fingerprint(),
        "provider_economics_sha256": _provider_fingerprint(provider),
        "taxonomy_fingerprint_sha256": taxonomy.fingerprint(),
        "assessment_sha256": _assessment_fingerprint(assessment),
        "provider_universe_gsl_coverage_complete": (
            assessment.provider_universe_gsl_coverage_complete
        ),
        "limited_risk_candidate_identified": (
            assessment.limited_risk_candidate_identified
        ),
        "option_structure_proven": assessment.option_structure_proven,
        "defined_risk_spread_proven": assessment.defined_risk_spread_proven,
        "gsl_execution_economics_proven": (
            assessment.gsl_execution_economics_proven
        ),
        "fresh_oos_utility_demonstrated": (
            assessment.fresh_oos_utility_demonstrated
        ),
        "t17_policy_ready": assessment.t17_policy_ready,
        "assessment_blockers": list(assessment.blockers),
    }
    if (
        payload["option_structure_proven"]
        or payload["defined_risk_spread_proven"]
        or payload["gsl_execution_economics_proven"]
        or payload["fresh_oos_utility_demonstrated"]
        or payload["t17_policy_ready"]
    ):
        raise CiboCapitalManagementError(
            "T17 observation receipt cannot promote unresolved capability"
        )
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def bind_t17_provider_capability_receipt(
    *,
    account: CTraderDemoAccountCapabilityObservation,
    provider: CTraderProviderEconomicsProbe,
    taxonomy: CTraderDemoInstrumentTaxonomyObservation,
    assessment: CiboT17LimitedRiskCapabilityAssessment,
    integrated_git_sha: str,
    policy_identity_sha256: str,
) -> CiboCrossBoundaryEvidenceReceipt:
    artifact = build_t17_provider_capability_source_artifact(
        account=account,
        provider=provider,
        taxonomy=taxonomy,
        assessment=assessment,
        integrated_git_sha=integrated_git_sha,
        policy_identity_sha256=policy_identity_sha256,
    )
    return bind_cross_boundary_pass_artifact(
        receipt_id="T17_PROVIDER_CAPABILITY_OBSERVATION",
        evidence_kind="T17_PROVIDER_CAPABILITY_OBSERVATION",
        source_artifact_json=artifact,
    )


def _provider_fingerprint(probe: CTraderProviderEconomicsProbe) -> str:
    return _digest(asdict(probe))


def _assessment_fingerprint(
    assessment: CiboT17LimitedRiskCapabilityAssessment,
) -> str:
    return _digest(asdict(assessment))


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_json_default,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"unsupported canonical T17 evidence value: {type(value)!r}")


def _git_sha(value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise CiboCapitalManagementError(
            "T17 receipt integrated Git SHA must be lowercase 40-hex"
        )


def _sha256(value: str, name: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(char not in "0123456789abcdef" for char in value[7:])
    ):
        raise CiboCapitalManagementError(
            f"T17 receipt {name} must be canonical SHA-256"
        )


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"T17 receipt {name} must be timezone-aware"
        )
