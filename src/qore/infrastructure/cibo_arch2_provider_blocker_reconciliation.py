"""Architect-2 reconciliation of stale provider-dependent CIBO blockers.

This module is intentionally read-only with respect to the canonical CIBO
ledger. It consumes the immutable current cTrader DEMO empirical provider
receipt and determines which recorded external blockers are already satisfied
by that receipt.

It does not consume Phase22 V2 outcomes, does not claim historical fills, does
not grant productive authority, and does not assign terminal dispositions.
"""

from __future__ import annotations

from dataclasses import dataclass

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_demo_empirical_provider_receipt import (
    ARTIFACT_DIGEST,
    ARTIFACT_ID,
    PHASE22_DEMO_EMPIRICAL_PROVIDER_RECEIPT,
    RUN_HEAD_SHA,
    RUN_ID,
    STATUS,
)

T11_LEDGER_BLOCKERS = (
    "REAL_EXECUTION_POPULATION_REQUIRED",
    "EMPIRICAL_SLIPPAGE_CALIBRATION_REQUIRED",
    "REAL_CALIBRATED_FRESH_OOS_GROSS_EDGE_MODEL_REQUIRED",
    "REAL_PROVIDER_BOUND_MARKET_IMPACT_MODEL_REQUIRED",
)

PROVIDER_ECONOMICS_LEDGER_BLOCKERS = (
    "REAL_FORWARD_SLIPPAGE_COST_CALIBRATION_REQUIRED",
    "HISTORICAL_2017_PROVIDER_USD_ECONOMICS_UNAVAILABLE",
)


@dataclass(frozen=True, slots=True)
class Architect2ProviderBlockerReconciliation:
    workstream_id: str
    observed_ledger_blockers: tuple[str, ...]
    resolved_blockers: tuple[str, ...]
    remaining_blockers: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    terminal_disposition_assigned: bool = False
    productive_authority: bool = False

    def __post_init__(self) -> None:
        if not self.workstream_id:
            raise CiboCapitalManagementError(
                "Architect-2 provider reconciliation workstream id required"
            )
        observed = set(self.observed_ledger_blockers)
        resolved = set(self.resolved_blockers)
        remaining = set(self.remaining_blockers)
        if resolved & remaining:
            raise CiboCapitalManagementError(
                "Architect-2 provider reconciliation overlap"
            )
        if resolved | remaining != observed:
            raise CiboCapitalManagementError(
                "Architect-2 provider reconciliation must partition blockers"
            )
        if not self.evidence_refs:
            raise CiboCapitalManagementError(
                "Architect-2 provider reconciliation evidence refs required"
            )
        if self.terminal_disposition_assigned or self.productive_authority:
            raise CiboCapitalManagementError(
                "Architect-2 provider reconciliation cannot assign ledger authority"
            )


def _provider_receipt_ready() -> bool:
    receipt = PHASE22_DEMO_EMPIRICAL_PROVIDER_RECEIPT
    return (
        STATUS == "EMPIRICAL_PROVIDER_CALIBRATION_READY"
        and receipt.qore_deals_found == receipt.observation_count
        and receipt.qore_deals_found > 0
        and receipt.empirical_slippage_calibrated
        and receipt.execution_model_ready
        and not receipt.blockers
        and not receipt.deal_history_truncated
        and not receipt.broker_mutation_performed
        and not receipt.holdout_outcomes_used
        and not receipt.historical_provider_economics_claimed
        and not receipt.target_aware
        and not receipt.productive_authority
    )


def reconcile_current_empirical_provider_plane(
) -> tuple[Architect2ProviderBlockerReconciliation, ...]:
    """Reconcile only blockers satisfied by the immutable provider receipt."""

    if not _provider_receipt_ready():
        raise CiboCapitalManagementError(
            "Architect-2 current empirical provider receipt is not ready"
        )

    evidence = (
        "src/qore/infrastructure/cibo_phase22_demo_empirical_provider_receipt.py",
        f"github-actions://{RUN_ID}/SUCCESS",
        f"github-artifact://{ARTIFACT_ID}/{ARTIFACT_DIGEST}",
        f"git://{RUN_HEAD_SHA}",
        "scope://CURRENT_CTRADER_DEMO_ONLY__NO_HISTORICAL_FILL_CLAIM",
    )

    return (
        Architect2ProviderBlockerReconciliation(
            workstream_id="T11",
            observed_ledger_blockers=T11_LEDGER_BLOCKERS,
            resolved_blockers=(
                "REAL_EXECUTION_POPULATION_REQUIRED",
                "EMPIRICAL_SLIPPAGE_CALIBRATION_REQUIRED",
            ),
            remaining_blockers=(
                "REAL_CALIBRATED_FRESH_OOS_GROSS_EDGE_MODEL_REQUIRED",
                "REAL_PROVIDER_BOUND_MARKET_IMPACT_MODEL_REQUIRED",
            ),
            evidence_refs=evidence,
        ),
        Architect2ProviderBlockerReconciliation(
            workstream_id="PROVIDER_ECONOMICS",
            observed_ledger_blockers=PROVIDER_ECONOMICS_LEDGER_BLOCKERS,
            resolved_blockers=(
                "REAL_FORWARD_SLIPPAGE_COST_CALIBRATION_REQUIRED",
            ),
            remaining_blockers=(
                "HISTORICAL_2017_PROVIDER_USD_ECONOMICS_UNAVAILABLE",
            ),
            evidence_refs=evidence,
        ),
    )
