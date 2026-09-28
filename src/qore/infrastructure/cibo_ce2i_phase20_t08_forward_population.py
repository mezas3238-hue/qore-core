"""Forward population audit for CE2I T08 monetary factor magnitude.

The audit reads only durable, frozen-forward decision evidence. It measures
whether candidate factor magnitude can be reconstructed causally from sealed
opportunity/provider facts. It does not convert factor notional into risk,
estimate correlation, authorize portfolio offsets, or promote T08.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_ce2i_phase20_forward_store import (
    Phase20ForwardDecisionSeal,
    VersionedPhase20ForwardEvidenceBook,
)
from qore.infrastructure.cibo_ce2i_phase20_qualification_plan import (
    FROZEN_PHASE20D_QUALIFICATION_PLAN,
)
from qore.infrastructure.cibo_ce2i_phase20_t08_factor_magnitude import (
    assess_minimum_seed_factor_magnitude,
)
from qore.infrastructure.cibo_provider_economic_normalization import (
    ProviderEconomicObservation,
)


@dataclass(frozen=True, slots=True)
class Phase20T08ForwardMagnitudePopulation:
    usable_forward_epochs: int
    candidate_epochs: int
    candidate_instances: int
    native_magnitude_instances: int
    usd_magnitude_complete_instances: int
    blocked_candidate_instances: int
    candidate_lineages: tuple[TraderLineage, ...]
    magnitude_lineages: tuple[TraderLineage, ...]
    candidate_symbols: tuple[str, ...]
    magnitude_symbols: tuple[str, ...]
    blocked_by_symbol: tuple[tuple[str, int], ...]
    source_decision_sha256s: tuple[str, ...]
    risk_equivalent_instances: int
    correlation_state_instances: int
    netting_credit_authorized: bool
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "usable_forward_epochs",
            "candidate_epochs",
            "candidate_instances",
            "native_magnitude_instances",
            "usd_magnitude_complete_instances",
            "blocked_candidate_instances",
            "risk_equivalent_instances",
            "correlation_state_instances",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"T08 forward population {name} must be non-negative int"
                )
        if self.candidate_epochs > self.usable_forward_epochs:
            raise CiboCapitalManagementError(
                "T08 candidate epochs cannot exceed usable epochs"
            )
        if self.native_magnitude_instances > self.candidate_instances:
            raise CiboCapitalManagementError(
                "T08 native magnitude count cannot exceed candidates"
            )
        if (
            self.usd_magnitude_complete_instances
            > self.native_magnitude_instances
        ):
            raise CiboCapitalManagementError(
                "T08 USD magnitude count cannot exceed native magnitude"
            )
        if (
            self.usd_magnitude_complete_instances
            + self.blocked_candidate_instances
            != self.candidate_instances
        ):
            raise CiboCapitalManagementError(
                "T08 candidate magnitude accounting does not close"
            )
        if (
            self.risk_equivalent_instances != 0
            or self.correlation_state_instances != 0
            or self.netting_credit_authorized
        ):
            raise CiboCapitalManagementError(
                "T08 population audit cannot grant risk/correlation/netting"
            )
        if not self.blockers:
            raise CiboCapitalManagementError(
                "T08 population audit must retain non-promotion blockers"
            )


def assess_phase20_t08_forward_magnitude_population(
    *,
    evidence_book: VersionedPhase20ForwardEvidenceBook,
) -> Phase20T08ForwardMagnitudePopulation:
    """Audit causal T08 factor-magnitude coverage in durable forward evidence."""

    if not isinstance(evidence_book, VersionedPhase20ForwardEvidenceBook):
        raise CiboCapitalManagementError(
            "T08 forward population requires canonical evidence book"
        )

    usable_forward_epochs = 0
    candidate_epochs = 0
    candidate_instances = 0
    native_magnitude_instances = 0
    usd_magnitude_complete_instances = 0
    blocked_candidate_instances = 0
    candidate_lineages: set[TraderLineage] = set()
    magnitude_lineages: set[TraderLineage] = set()
    candidate_symbols: set[str] = set()
    magnitude_symbols: set[str] = set()
    blocked_by_symbol: dict[str, int] = {}
    source_decision_sha256s: list[str] = []

    for decision in sorted(
        evidence_book.decisions,
        key=lambda item: (item.decision_at, item.evidence_sha256),
    ):
        payload = _usable_forward_payload(decision)
        if payload is None:
            continue
        usable_forward_epochs += 1
        candidates = _candidate_evidence(payload)
        if not candidates:
            continue
        candidate_epochs += 1
        source_decision_sha256s.append(decision.evidence_sha256)

        for item in candidates:
            opportunity = _opportunity(item)
            provider = _provider_observation(item)
            _validate_candidate_identity(item, opportunity)
            candidate_instances += 1
            candidate_lineages.add(opportunity.trader_id)
            candidate_symbols.add(opportunity.qore_symbol)
            audit = assess_minimum_seed_factor_magnitude(
                opportunity=opportunity,
                observation=provider,
                decision_at=decision.decision_at,
                provider_evidence_ref=_string(
                    item.get("provider_evidence_id"),
                    name="provider_evidence_id",
                ),
            )
            if audit.native_magnitude_identified:
                native_magnitude_instances += 1
            if audit.usd_magnitude_complete:
                usd_magnitude_complete_instances += 1
                magnitude_lineages.add(opportunity.trader_id)
                magnitude_symbols.add(opportunity.qore_symbol)
            else:
                blocked_candidate_instances += 1
                blocked_by_symbol[opportunity.qore_symbol] = (
                    blocked_by_symbol.get(opportunity.qore_symbol, 0) + 1
                )

    blockers: list[str] = []
    if candidate_instances == 0:
        blockers.append("NO_FORWARD_CANDIDATE_INSTANCES")
    elif blocked_candidate_instances > 0:
        blockers.append("USD_FACTOR_MAGNITUDE_COVERAGE_INCOMPLETE")
    blockers.extend(
        (
            "FACTOR_NOTIONAL_TO_SIGNED_RISK_USD_MAPPING_NOT_IDENTIFIED",
            "CAUSAL_CORRELATION_STATE_NOT_IDENTIFIED",
            "FRESH_OOS_NETTING_UTILITY_ANALYSIS_REQUIRED",
        )
    )
    return Phase20T08ForwardMagnitudePopulation(
        usable_forward_epochs=usable_forward_epochs,
        candidate_epochs=candidate_epochs,
        candidate_instances=candidate_instances,
        native_magnitude_instances=native_magnitude_instances,
        usd_magnitude_complete_instances=usd_magnitude_complete_instances,
        blocked_candidate_instances=blocked_candidate_instances,
        candidate_lineages=tuple(sorted(candidate_lineages, key=lambda item: item.value)),
        magnitude_lineages=tuple(sorted(magnitude_lineages, key=lambda item: item.value)),
        candidate_symbols=tuple(sorted(candidate_symbols)),
        magnitude_symbols=tuple(sorted(magnitude_symbols)),
        blocked_by_symbol=tuple(sorted(blocked_by_symbol.items())),
        source_decision_sha256s=tuple(source_decision_sha256s),
        risk_equivalent_instances=0,
        correlation_state_instances=0,
        netting_credit_authorized=False,
        blockers=tuple(blockers),
    )


def _usable_forward_payload(
    decision: Phase20ForwardDecisionSeal,
) -> dict[str, Any] | None:
    if decision.sealed_at is None:
        return None
    if (
        decision.seal_deadline_at is not None
        and not decision.sealed_within_deadline
    ):
        return None
    if decision.decision_at < FROZEN_PHASE20D_QUALIFICATION_PLAN.frozen_at:
        return None
    payload = _payload(decision)
    if payload.get("evidence_kind") != "FORWARD_OBSERVED":
        return None
    return payload


def _payload(decision: Phase20ForwardDecisionSeal) -> dict[str, Any]:
    try:
        payload = json.loads(decision.canonical_payload_json)
    except json.JSONDecodeError as error:
        raise CiboCapitalManagementError(
            "T08 forward decision payload is invalid JSON"
        ) from error
    if not isinstance(payload, dict):
        raise CiboCapitalManagementError(
            "T08 forward decision payload must be object"
        )
    return payload


def _candidate_evidence(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    raw = payload.get("candidates")
    if not isinstance(raw, list):
        raise CiboCapitalManagementError(
            "T08 forward candidates must be list"
        )
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise CiboCapitalManagementError(
                "T08 forward candidate evidence must be object"
            )
        result.append(item)
    return tuple(result)


def _opportunity(item: dict[str, Any]) -> TraderOpportunityEnvelope:
    raw = item.get("opportunity")
    if not isinstance(raw, dict):
        raise CiboCapitalManagementError(
            "T08 forward opportunity payload must be object"
        )
    try:
        trader_id = TraderLineage(
            _string(raw.get("trader_id"), name="opportunity.trader_id")
        )
    except ValueError as error:
        raise CiboCapitalManagementError(
            "T08 forward opportunity Trader lineage is invalid"
        ) from error
    context_raw = raw.get("decision_context", [])
    if not isinstance(context_raw, list):
        raise CiboCapitalManagementError(
            "T08 forward opportunity decision_context must be list"
        )
    context: list[tuple[str, str]] = []
    for row in context_raw:
        if (
            not isinstance(row, list)
            or len(row) != 2
            or not isinstance(row[0], str)
            or not isinstance(row[1], str)
        ):
            raise CiboCapitalManagementError(
                "T08 forward opportunity decision_context row is invalid"
            )
        context.append((row[0], row[1]))
    return TraderOpportunityEnvelope(
        trader_id=trader_id,
        signal_fingerprint=_string(
            raw.get("signal_fingerprint"),
            name="opportunity.signal_fingerprint",
        ),
        qore_symbol=_string(
            raw.get("qore_symbol"),
            name="opportunity.qore_symbol",
        ),
        provider_symbol=_string(
            raw.get("provider_symbol"),
            name="opportunity.provider_symbol",
        ),
        side=_string(raw.get("side"), name="opportunity.side"),
        entry_type=_string(
            raw.get("entry_type"),
            name="opportunity.entry_type",
        ),
        intended_entry=_decimal(
            raw.get("intended_entry"),
            name="opportunity.intended_entry",
        ),
        stop_loss=_decimal(
            raw.get("stop_loss"),
            name="opportunity.stop_loss",
        ),
        take_profit=_decimal(
            raw.get("take_profit"),
            name="opportunity.take_profit",
        ),
        stop_loss_per_volume=_decimal(
            raw.get("stop_loss_per_volume"),
            name="opportunity.stop_loss_per_volume",
        ),
        margin_per_volume=_decimal(
            raw.get("margin_per_volume"),
            name="opportunity.margin_per_volume",
        ),
        volume_step=_decimal(
            raw.get("volume_step"),
            name="opportunity.volume_step",
        ),
        minimum_volume=_decimal(
            raw.get("minimum_volume"),
            name="opportunity.minimum_volume",
        ),
        maximum_volume=_decimal(
            raw.get("maximum_volume"),
            name="opportunity.maximum_volume",
        ),
        minimum_execution_steps=_integer(
            raw.get("minimum_execution_steps", 1),
            name="opportunity.minimum_execution_steps",
        ),
        decision_context=tuple(context),
    )


def _provider_observation(
    item: dict[str, Any],
) -> ProviderEconomicObservation:
    raw = item.get("provider_observation")
    if not isinstance(raw, dict):
        raise CiboCapitalManagementError(
            "T08 forward provider payload must be object"
        )
    return ProviderEconomicObservation(
        provider_key=_string(
            raw.get("provider_key"),
            name="provider.provider_key",
        ),
        qore_symbol=_string(
            raw.get("qore_symbol"),
            name="provider.qore_symbol",
        ),
        provider_symbol=_string(
            raw.get("provider_symbol"),
            name="provider.provider_symbol",
        ),
        bid=_decimal(raw.get("bid"), name="provider.bid"),
        ask=_decimal(raw.get("ask"), name="provider.ask"),
        contract_size=_decimal(
            raw.get("contract_size"),
            name="provider.contract_size",
        ),
        tick_size=_decimal(
            raw.get("tick_size"),
            name="provider.tick_size",
        ),
        tick_value=_decimal(
            raw.get("tick_value"),
            name="provider.tick_value",
        ),
        minimum_volume=_decimal(
            raw.get("minimum_volume"),
            name="provider.minimum_volume",
        ),
        maximum_volume=_decimal(
            raw.get("maximum_volume"),
            name="provider.maximum_volume",
        ),
        volume_step=_decimal(
            raw.get("volume_step"),
            name="provider.volume_step",
        ),
        margin_per_volume=_decimal(
            raw.get("margin_per_volume"),
            name="provider.margin_per_volume",
        ),
        commission_per_volume_usd=_decimal(
            raw.get("commission_per_volume_usd"),
            name="provider.commission_per_volume_usd",
            allow_zero=True,
        ),
        slippage_reserve_per_volume_usd=_decimal(
            raw.get("slippage_reserve_per_volume_usd"),
            name="provider.slippage_reserve_per_volume_usd",
            allow_zero=True,
        ),
        observed_at=_datetime(
            raw.get("observed_at"),
            name="provider.observed_at",
        ),
    )


def _validate_candidate_identity(
    item: dict[str, Any],
    opportunity: TraderOpportunityEnvelope,
) -> None:
    candidate = item.get("candidate")
    if not isinstance(candidate, dict):
        raise CiboCapitalManagementError(
            "T08 forward candidate payload must be object"
        )
    expected = (
        ("signal_fingerprint", opportunity.signal_fingerprint),
        ("qore_symbol", opportunity.qore_symbol),
        ("provider_symbol", opportunity.provider_symbol),
        ("trader_id", opportunity.trader_id.value),
    )
    for name, value in expected:
        if candidate.get(name) != value:
            raise CiboCapitalManagementError(
                f"T08 forward candidate {name} identity mismatch"
            )


def _string(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise CiboCapitalManagementError(
            f"T08 forward {name} must be non-empty string"
        )
    return value


def _decimal(
    value: object,
    *,
    name: str,
    allow_zero: bool = False,
) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise CiboCapitalManagementError(
            f"T08 forward {name} must be Decimal-compatible"
        ) from error
    if (
        not result.is_finite()
        or result < 0
        or (result == 0 and not allow_zero)
    ):
        raise CiboCapitalManagementError(
            f"T08 forward {name} has invalid numeric value"
        )
    return result


def _integer(value: object, *, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise CiboCapitalManagementError(
            f"T08 forward {name} must be positive int"
        )
    return value


def _datetime(value: object, *, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(
            f"T08 forward {name} must be ISO datetime string"
        )
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise CiboCapitalManagementError(
            f"T08 forward {name} must be valid ISO datetime"
        ) from error
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(
            f"T08 forward {name} must be timezone-aware"
        )
    return result
