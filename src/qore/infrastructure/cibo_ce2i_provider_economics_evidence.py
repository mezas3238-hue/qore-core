"""Sealed point-in-time cTrader DEMO provider-economics evidence.

This evidence proves current provider-native terms only. It is not historical
2017 economics and does not calibrate slippage or authorize an execution model.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CiboProviderEconomicsEvidence:
    workflow_run_id: int
    artifact_id: int
    artifact_sha256: str
    source_git_sha: str
    observed_at: str
    provider_key: str
    symbols: tuple[str, ...]
    provider_terms_ready: bool
    slippage_empirically_calibrated: bool
    historical_exact_claimed: bool
    execution_model_ready: bool
    broker_mutation_performed: bool
    holdout_outcomes_used: bool
    target_aware: bool


CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS = CiboProviderEconomicsEvidence(
    workflow_run_id=36810489106,
    artifact_id=11139835744,
    artifact_sha256=(
        "dc9bb7a969c12fabfca4ce7ea1ca1c015298b8f3817035d39ed24597d993fa02"
    ),
    source_git_sha="9e2301edf7bbdf141050965c252b51697a3a94db",
    observed_at="2026-10-01T03:38:43.983528+00:00",
    provider_key="ctrader-demo",
    symbols=(
        "AUDJPY",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "XAUUSD",
    ),
    provider_terms_ready=True,
    slippage_empirically_calibrated=False,
    historical_exact_claimed=False,
    execution_model_ready=False,
    broker_mutation_performed=False,
    holdout_outcomes_used=False,
    target_aware=False,
)


def provider_economics_evidence_ref() -> str:
    evidence = CURRENT_CTRADER_DEMO_PROVIDER_ECONOMICS
    return (
        f"provider-economics:artifact:{evidence.artifact_id}:"
        f"sha256:{evidence.artifact_sha256}:"
        "POINT_IN_TIME_TERMS_READY_HISTORICAL_EXACT_FALSE"
    )
