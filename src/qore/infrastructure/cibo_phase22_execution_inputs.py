"""Typed reconstruction of the two sealed inputs to Phase22 execution.

Fresh Trader lane artifacts and the provider numeric freeze are serialized for
GitHub orchestration. This module rehydrates them while recomputing the
canonical fingerprints used by the in-process contracts; malformed or
incomplete JSON therefore fails closed before policy evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_fresh_capital_projection import (
    Phase22FreshCapitalProjection,
    project_phase22_fresh_capital_input,
)
from qore.infrastructure.cibo_phase22_fresh_opportunity_batch import (
    Phase22FreshOpportunity,
    Phase22FreshOpportunityBatch,
    Phase22FreshTraderEvidence,
    build_phase22_fresh_opportunity_batch,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_receipt import (
    CANDIDATE_ID,
)
from qore.infrastructure.cibo_phase22_provider_numeric_execution import (
    Phase22ProviderAccountLineageReceipt,
    Phase22ProviderNumericExecutionSpec,
)
from qore.infrastructure.cibo_phase22_trader_parity_manifest import (
    CANONICAL_PHASE22_TRADER_IDS,
)


@dataclass(frozen=True, slots=True)
class Phase22SealedFreshBatchInput:
    batch: Phase22FreshOpportunityBatch
    declared_batch_sha256: str

    def __post_init__(self) -> None:
        if self.declared_batch_sha256 != self.batch.fingerprint():
            raise CiboCapitalManagementError(
                "Phase22 serialized fresh batch fingerprint drift"
            )


@dataclass(frozen=True, slots=True)
class Phase22SealedProviderNumericInput:
    account_lineage: Phase22ProviderAccountLineageReceipt
    specs: tuple[Phase22ProviderNumericExecutionSpec, ...]

    def __post_init__(self) -> None:
        expected = (
            "AUDJPY",
            "EURUSD",
            "GBPJPY",
            "GBPUSD",
            "NAS100",
            "XAUUSD",
        )
        if tuple(item.qore_symbol for item in self.specs) != expected:
            raise CiboCapitalManagementError(
                "Phase22 serialized provider numeric surface drift"
            )
        if len({item.qore_symbol for item in self.specs}) != len(self.specs):
            raise CiboCapitalManagementError(
                "Phase22 serialized provider numeric duplicate symbol"
            )

    def spec_for(self, qore_symbol: str) -> Phase22ProviderNumericExecutionSpec:
        matches = tuple(
            item for item in self.specs if item.qore_symbol == qore_symbol
        )
        if len(matches) != 1:
            raise CiboCapitalManagementError(
                f"Phase22 provider numeric spec missing: {qore_symbol}"
            )
        return matches[0]


def _required_dict(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CiboCapitalManagementError(
            f"Phase22 execution input {name} must be object"
        )
    return value


def _required_list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise CiboCapitalManagementError(
            f"Phase22 execution input {name} must be list"
        )
    return value


def _decimal(value: object, name: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as error:
        raise CiboCapitalManagementError(
            f"Phase22 execution input {name} invalid"
        ) from error
    if not parsed.is_finite():
        raise CiboCapitalManagementError(
            f"Phase22 execution input {name} must be finite"
        )
    return parsed


def _fresh_from_payload(raw: dict[str, Any]) -> Phase22FreshOpportunity:
    evidence = tuple(str(item) for item in _required_list(
        raw.get("source_evidence_ids"),
        "source_evidence_ids",
    ))
    return Phase22FreshOpportunity(
        trader_id=TraderLineage(str(raw["trader_id"])),
        qore_symbol=str(raw["qore_symbol"]),
        signal_fingerprint=str(raw["signal_fingerprint"]),
        signal_at=datetime.fromisoformat(str(raw["signal_at"])),
        entry_at=datetime.fromisoformat(str(raw["entry_at"])),
        exit_at=datetime.fromisoformat(str(raw["exit_at"])),
        side=str(raw["side"]),
        entry_price=_decimal(raw["entry_price"], "entry_price"),
        structural_stop=_decimal(raw["structural_stop"], "structural_stop"),
        technical_target=_decimal(raw["technical_target"], "technical_target"),
        exit_reason=str(raw["exit_reason"]),
        gross_structural_outcome_r=_decimal(
            raw["gross_structural_outcome_r"],
            "gross_structural_outcome_r",
        ),
        methodology_sha256=str(raw["methodology_sha256"]),
        source_evidence_ids=evidence,
    )


def load_phase22_sealed_fresh_batch(
    payload: dict[str, Any],
) -> Phase22SealedFreshBatchInput:
    if payload.get("schema") != "qore.cibo.phase22.fresh-batch-assembly.v1":
        raise CiboCapitalManagementError(
            "Phase22 serialized fresh batch schema drift"
        )
    if payload.get("candidate_id") != CANDIDATE_ID:
        raise CiboCapitalManagementError(
            "Phase22 serialized fresh batch candidate drift"
        )
    if (
        payload.get("legacy_trader_sizing_used_for_cibo") is not False
        or payload.get("productive_authority") is not False
    ):
        raise CiboCapitalManagementError(
            "Phase22 serialized fresh batch governance contamination"
        )
    opportunity_rows = _required_list(
        payload.get("opportunities"),
        "opportunities",
    )
    opportunities = tuple(
        _fresh_from_payload(_required_dict(row, "opportunity"))
        for row in opportunity_rows
    )
    trader_rows = _required_list(payload.get("traders"), "traders")
    if tuple(
        str(_required_dict(row, "trader")["trader_id"])
        for row in trader_rows
    ) != CANONICAL_PHASE22_TRADER_IDS:
        raise CiboCapitalManagementError(
            "Phase22 serialized fresh batch Trader surface drift"
        )

    traders: list[Phase22FreshTraderEvidence] = []
    for raw_row in trader_rows:
        row = _required_dict(raw_row, "trader")
        trader_id = str(row["trader_id"])
        trader_opportunities = tuple(
            item
            for item in opportunities
            if item.trader_id.value == trader_id
        )
        if int(row["opportunity_count"]) != len(trader_opportunities):
            raise CiboCapitalManagementError(
                "Phase22 serialized fresh batch opportunity count drift"
            )
        evidence = Phase22FreshTraderEvidence(
            trader_id=trader_id,
            source_artifact_sha256=str(row["lane_artifact_sha256"]),
            opportunities=trader_opportunities,
            fresh_outcomes_executed=True,
            methodology_changed=False,
            legacy_trader_sizing_used_for_cibo=False,
        )
        if evidence.fingerprint() != str(row["evidence_sha256"]):
            raise CiboCapitalManagementError(
                "Phase22 serialized fresh Trader evidence fingerprint drift"
            )
        traders.append(evidence)

    batch = build_phase22_fresh_opportunity_batch(tuple(traders))
    declared = str(payload["batch_sha256"])
    return Phase22SealedFreshBatchInput(
        batch=batch,
        declared_batch_sha256=declared,
    )


def _lineage_from_payload(
    raw: dict[str, Any],
) -> Phase22ProviderAccountLineageReceipt:
    return Phase22ProviderAccountLineageReceipt(
        provider_key=str(raw["provider_key"]),
        legacy_account_fingerprint_sha256=str(
            raw["legacy_account_fingerprint_sha256"]
        ),
        phase22_account_fingerprint_sha256=str(
            raw["phase22_account_fingerprint_sha256"]
        ),
        same_account_proven=bool(raw["same_account_proven"]),
        broker_mutation_performed=bool(
            raw.get("broker_mutation_performed", False)
        ),
        holdout_outcomes_used=bool(raw.get("holdout_outcomes_used", False)),
        productive_authority=bool(raw.get("productive_authority", False)),
    )


def _spec_from_payload(raw: dict[str, Any]) -> Phase22ProviderNumericExecutionSpec:
    return Phase22ProviderNumericExecutionSpec(
        qore_symbol=str(raw["qore_symbol"]),
        provider_symbol=str(raw["provider_symbol"]),
        observed_at=datetime.fromisoformat(str(raw["observed_at"])),
        bid=_decimal(raw["bid"], "bid"),
        ask=_decimal(raw["ask"], "ask"),
        display_digits=int(raw["display_digits"]),
        contract_size_per_volume=_decimal(
            raw["contract_size_per_volume"],
            "contract_size_per_volume",
        ),
        minimum_volume=_decimal(raw["minimum_volume"], "minimum_volume"),
        maximum_volume=_decimal(raw["maximum_volume"], "maximum_volume"),
        volume_step=_decimal(raw["volume_step"], "volume_step"),
        margin_per_volume_usd=_decimal(
            raw["margin_per_volume_usd"],
            "margin_per_volume_usd",
        ),
        commission_per_volume_usd=_decimal(
            raw["commission_per_volume_usd"],
            "commission_per_volume_usd",
        ),
        worst_adverse_slippage_bps=_decimal(
            raw["worst_adverse_slippage_bps"],
            "worst_adverse_slippage_bps",
        ),
        quote_to_usd=_decimal(raw["quote_to_usd"], "quote_to_usd"),
        usd_value_per_price_unit_per_volume=_decimal(
            raw["usd_value_per_price_unit_per_volume"],
            "usd_value_per_price_unit_per_volume",
        ),
        derived_price_quantum=_decimal(
            raw["derived_price_quantum"],
            "derived_price_quantum",
        ),
        derived_value_per_quantum_usd=_decimal(
            raw["derived_value_per_quantum_usd"],
            "derived_value_per_quantum_usd",
        ),
        source_provider_terms_artifact_sha256=str(
            raw["source_provider_terms_artifact_sha256"]
        ),
        source_empirical_execution_artifact_sha256=str(
            raw["source_empirical_execution_artifact_sha256"]
        ),
        derivation_kind=str(raw["derivation_kind"]),
        historical_exact_claimed=bool(
            raw.get("historical_exact_claimed", False)
        ),
        holdout_outcomes_used=bool(raw.get("holdout_outcomes_used", False)),
        productive_authority=bool(raw.get("productive_authority", False)),
    )


def load_phase22_sealed_provider_numeric(
    payload: dict[str, Any],
) -> Phase22SealedProviderNumericInput:
    if (
        payload.get("schema")
        != "qore.cibo.phase22.provider-numeric-execution-freeze.v1"
        or payload.get("status") != "READY"
    ):
        raise CiboCapitalManagementError(
            "Phase22 serialized provider numeric freeze not READY"
        )
    for field in (
        "holdout_market_data_read",
        "holdout_outcomes_used",
        "broker_mutation_performed",
        "historical_provider_economics_claimed",
        "productive_authority",
    ):
        if payload.get(field) is not False:
            raise CiboCapitalManagementError(
                f"Phase22 provider numeric freeze governance drift: {field}"
            )
    lineage = _lineage_from_payload(
        _required_dict(payload.get("account_lineage"), "account_lineage")
    )
    if lineage.fingerprint() != str(payload["account_lineage_sha256"]):
        raise CiboCapitalManagementError(
            "Phase22 provider numeric account lineage fingerprint drift"
        )
    specs = tuple(
        _spec_from_payload(_required_dict(item, "provider_spec"))
        for item in _required_list(payload.get("specs"), "specs")
    )
    return Phase22SealedProviderNumericInput(
        account_lineage=lineage,
        specs=specs,
    )


def project_phase22_execution_inputs(
    *,
    fresh: Phase22SealedFreshBatchInput,
    provider: Phase22SealedProviderNumericInput,
    provider_numeric_freeze_sha256: str,
) -> tuple[Phase22FreshCapitalProjection, ...]:
    return tuple(
        project_phase22_fresh_capital_input(
            fresh=opportunity,
            spec=provider.spec_for(opportunity.qore_symbol),
            provider_numeric_freeze_sha256=provider_numeric_freeze_sha256,
        )
        for opportunity in fresh.batch.opportunities
    )
