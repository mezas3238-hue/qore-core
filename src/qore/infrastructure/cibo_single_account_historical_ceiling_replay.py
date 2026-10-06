"""Chronological single-account historical replay for CIBO ceiling discovery.

This is the non-certifying economic replay core.  It preserves one USD60 account
across every historical decision epoch, settles only outcomes whose exit time has
arrived, reconstructs account-dependent regime utilization causally, executes
Native MAX over the complete simultaneous opportunity surface, and lets QORE
Risk remain the sole authorization authority.

Historical outcomes are never passed to a predecision API.  The provider budget
is an explicit counterfactual research assumption and is not represented as
observed broker history.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from qore.infrastructure.account_wide_risk import (
    AccountWideRiskEngine,
    RiskDecision,
)
from qore.infrastructure.cibo_account_capital_mission import (
    CiboAccountCapitalIdentity,
    derive_cibo_capital_mission,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_regime_selector import (
    CiboCapitalRegimeState,
    CorrelationState,
    LiquidityState,
    ProviderCondition,
    VolatilityState,
)
from qore.infrastructure.cibo_single_account_ceiling_state import (
    CiboCeilingOpenExposure,
)
from qore.infrastructure.cibo_single_account_historical_capital_ledger import (
    CiboHistoricalResearchCapitalState,
    initialize_historical_research_capital,
    reserve_historical_authorization,
    settle_historical_deployment,
)
from qore.infrastructure.cibo_single_account_historical_ceiling_epoch import (
    CiboHistoricalProviderAssumption,
    run_predecision_historical_sovereign_ceiling_epoch,
)
from qore.infrastructure.cibo_single_account_manifest_economics import (
    manifest_row_to_ceiling_opportunity_evidence,
)
from qore.infrastructure.cibo_single_account_manifest_integrity import (
    validate_single_account_manifest_sha256,
)
from qore.infrastructure.cibo_single_account_manifest_settlement import (
    manifest_row_to_sovereign_settlement,
)
from qore.infrastructure.cibo_single_account_sovereign_ceiling_run import (
    CiboSovereignCeilingDecisionReceipt,
    CiboSovereignCeilingSettlementReceipt,
)
from qore.infrastructure.cibo_trader_capability_profile import CiboEvidenceRef
from qore.infrastructure.market_test_environment import MarketRuntimeEnvironment


_INITIAL_CAPITAL_USD = Decimal("60")


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CiboCapitalManagementError(f"{name} must be mapping")
    return value


def _dt(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise CiboCapitalManagementError(f"{name} must be string")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise CiboCapitalManagementError(f"{name} must be timezone-aware")
    return result


def _boolish(value: object, name: str) -> bool:
    if type(value) is bool:
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no", ""}:
            return False
    if value is None:
        return False
    raise CiboCapitalManagementError(f"{name} must be bool-compatible")


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal(0) if numerator <= 0 else Decimal(1)
    return min(Decimal(1), max(Decimal(0), numerator / denominator))


@dataclass(frozen=True, slots=True)
class _RegimeSemantics:
    liquidity: LiquidityState
    volatility: VolatilityState
    correlation: CorrelationState
    provider_condition: ProviderCondition
    position_path_adverse: bool
    evidence_stale: bool


@dataclass(frozen=True, slots=True)
class _PendingHistoricalSettlement:
    exit_at: datetime
    row: Mapping[str, Any]
    decision: CiboSovereignCeilingDecisionReceipt


@dataclass(frozen=True, slots=True)
class CiboHistoricalCeilingReplayResult:
    source_manifest_sha256: str
    decision_epoch_count: int
    decision_receipts: tuple[CiboSovereignCeilingDecisionReceipt, ...]
    settlement_receipts: tuple[CiboSovereignCeilingSettlementReceipt, ...]
    final_capital: CiboHistoricalResearchCapitalState
    final_open_exposures: tuple[CiboCeilingOpenExposure, ...]
    regime_reconstruction_count: int
    provider_assumption: CiboHistoricalProviderAssumption
    external_ai_call_count: int
    outcome_used_for_predecision: bool = False
    account_reset_count: int = 0
    economic_era_reset_count: int = 0
    broker_mutation: bool = False
    certification_claimed: bool = False

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_manifest_sha256, str)
            or not self.source_manifest_sha256.startswith("sha256:")
            or len(self.source_manifest_sha256) != 71
        ):
            raise CiboCapitalManagementError(
                "historical ceiling replay manifest digest invalid"
            )
        if (
            not isinstance(self.decision_epoch_count, int)
            or isinstance(self.decision_epoch_count, bool)
            or self.decision_epoch_count <= 0
        ):
            raise CiboCapitalManagementError(
                "historical ceiling replay epoch count must be positive"
            )
        if any(
            not isinstance(item, CiboSovereignCeilingDecisionReceipt)
            for item in self.decision_receipts
        ):
            raise CiboCapitalManagementError(
                "historical ceiling replay decision receipt invalid"
            )
        if any(
            not isinstance(item, CiboSovereignCeilingSettlementReceipt)
            for item in self.settlement_receipts
        ):
            raise CiboCapitalManagementError(
                "historical ceiling replay settlement receipt invalid"
            )
        if not isinstance(
            self.final_capital,
            CiboHistoricalResearchCapitalState,
        ):
            raise CiboCapitalManagementError(
                "historical ceiling replay final capital invalid"
            )
        if self.final_open_exposures:
            raise CiboCapitalManagementError(
                "historical ceiling replay ended with unsettled open exposure"
            )
        if self.final_capital.open_deployments:
            raise CiboCapitalManagementError(
                "historical ceiling replay ended with unsettled deployment"
            )
        for name in (
            "regime_reconstruction_count",
            "external_ai_call_count",
            "account_reset_count",
            "economic_era_reset_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise CiboCapitalManagementError(
                    f"historical ceiling replay {name} must be non-negative int"
                )
        if self.regime_reconstruction_count != self.decision_epoch_count:
            raise CiboCapitalManagementError(
                "historical ceiling replay regime/epoch count drift"
            )
        if self.external_ai_call_count != 0:
            raise CiboCapitalManagementError(
                "historical ceiling replay forbids external AI"
            )
        if self.account_reset_count or self.economic_era_reset_count:
            raise CiboCapitalManagementError(
                "historical ceiling replay forbids account/era resets"
            )
        if (
            self.outcome_used_for_predecision
            or self.broker_mutation
            or self.certification_claimed
        ):
            raise CiboCapitalManagementError(
                "historical ceiling replay governance violated"
            )

    @property
    def ending_capital_usd(self) -> Decimal:
        return self.final_capital.realized_capital_usd

    @property
    def peak_capital_usd(self) -> Decimal:
        return self.final_capital.peak_realized_capital_usd

    @property
    def net_pnl_usd(self) -> Decimal:
        return self.ending_capital_usd - _INITIAL_CAPITAL_USD


def _regime_semantics(row: Mapping[str, Any]) -> _RegimeSemantics:
    ce2i = _mapping(
        row.get("ce2i_predecision_evidence"),
        "ce2i_predecision_evidence",
    )
    receipts = ce2i.get("runtime_receipts")
    if not isinstance(receipts, (list, tuple)):
        raise CiboCapitalManagementError(
            "historical ceiling regime receipts missing"
        )
    matches = tuple(
        item
        for item in receipts
        if isinstance(item, Mapping)
        and item.get("engine_name") == "select_ce2i_tools_for_regime"
    )
    if len(matches) != 1:
        raise CiboCapitalManagementError(
            "historical ceiling requires exact CE2I regime receipt"
        )
    payload = _mapping(
        matches[0].get("input_payload"),
        "CE2I regime input_payload",
    )
    return _RegimeSemantics(
        liquidity=LiquidityState(str(payload["liquidity"])),
        volatility=VolatilityState(str(payload["volatility"])),
        correlation=CorrelationState(str(payload["correlation"])),
        provider_condition=ProviderCondition(
            str(payload["provider_condition"])
        ),
        position_path_adverse=_boolish(
            payload.get("position_path_adverse"),
            "position_path_adverse",
        ),
        evidence_stale=_boolish(
            payload.get("evidence_stale"),
            "evidence_stale",
        ),
    )


def _causal_regime(
    *,
    rows: tuple[Mapping[str, Any], ...],
    capital: CiboHistoricalResearchCapitalState,
    provider_assumption: CiboHistoricalProviderAssumption,
) -> CiboCapitalRegimeState:
    semantics = tuple(_regime_semantics(row) for row in rows)
    regime = semantics[0]
    if any(item != regime for item in semantics[1:]):
        raise CiboCapitalManagementError(
            "historical ceiling mixed market-regime semantics inside epoch"
        )

    realized = capital.realized_capital_usd
    provider_cost_reserve = capital.open_provider_cost_reserve_usd
    internal_stop_capacity = max(
        Decimal(0),
        realized - provider_cost_reserve,
    )
    risk_capacity = min(
        internal_stop_capacity,
        realized * provider_assumption.risk_headroom_multiple_of_equity,
        realized * provider_assumption.max_risk_multiple_of_equity,
    )
    margin_capacity = max(
        Decimal(0),
        (
            realized
            * provider_assumption.margin_capacity_multiple_of_equity
            - provider_cost_reserve
        ),
    )
    drawdown = max(
        Decimal(0),
        capital.peak_realized_capital_usd - realized,
    )
    return CiboCapitalRegimeState(
        liquidity=regime.liquidity,
        volatility=regime.volatility,
        correlation=regime.correlation,
        provider_condition=regime.provider_condition,
        risk_utilization=_ratio(capital.open_stop_risk_usd, risk_capacity),
        margin_utilization=_ratio(capital.open_margin_usd, margin_capacity),
        drawdown_utilization=_ratio(
            drawdown,
            capital.peak_realized_capital_usd,
        ),
        opportunity_count=len(rows),
        position_path_adverse=regime.position_path_adverse,
        evidence_stale=regime.evidence_stale,
    )


def _group_epochs(
    rows: list[Mapping[str, Any]],
) -> tuple[tuple[Mapping[str, Any], ...], ...]:
    grouped: dict[tuple[datetime, str], list[Mapping[str, Any]]] = defaultdict(
        list
    )
    for row in rows:
        decision_at = _dt(
            row.get("market_decision_at"),
            "market_decision_at",
        )
        epoch_id = row.get("decision_epoch_id")
        if not isinstance(epoch_id, str) or not epoch_id:
            raise CiboCapitalManagementError(
                "historical ceiling decision_epoch_id is required"
            )
        grouped[(decision_at, epoch_id)].append(row)

    result: list[tuple[Mapping[str, Any], ...]] = []
    for (decision_at, epoch_id), epoch_rows in grouped.items():
        signals = tuple(
            str(row.get("signal_fingerprint")) for row in epoch_rows
        )
        if len(signals) != len(set(signals)):
            raise CiboCapitalManagementError(
                "historical ceiling duplicate signal inside epoch"
            )
        result.append(
            tuple(
                sorted(
                    epoch_rows,
                    key=lambda row: (
                        str(row.get("trader_id")),
                        str(row.get("qore_symbol")),
                        str(row.get("signal_fingerprint")),
                    ),
                )
            )
        )
    return tuple(
        sorted(
            result,
            key=lambda epoch: (
                _dt(epoch[0]["market_decision_at"], "market_decision_at"),
                str(epoch[0]["decision_epoch_id"]),
            ),
        )
    )


def run_historical_ceiling_replay(
    manifest: Mapping[str, Any],
    *,
    provider_assumption: CiboHistoricalProviderAssumption = (
        CiboHistoricalProviderAssumption()
    ),
    progress_hook: Any | None = None,
) -> CiboHistoricalCeilingReplayResult:
    """Run one continuous USD60 historical Native MAX ceiling replay."""

    source_manifest_sha256 = validate_single_account_manifest_sha256(manifest)
    if manifest.get("initial_capital_usd") != "60":
        raise CiboCapitalManagementError(
            "historical ceiling replay must start from exactly USD60"
        )
    if (
        manifest.get("account_count") != 1
        or manifest.get("account_reset_count") != 0
        or manifest.get("economic_era_reset_count") != 0
    ):
        raise CiboCapitalManagementError(
            "historical ceiling replay requires one continuous account"
        )
    if manifest.get("target_capital_used_for_tuning") is not False:
        raise CiboCapitalManagementError(
            "historical ceiling replay forbids target-capital tuning"
        )
    rows_raw = manifest.get("opportunities")
    if not isinstance(rows_raw, list) or not rows_raw:
        raise CiboCapitalManagementError(
            "historical ceiling replay requires manifest opportunities"
        )
    rows = [
        _mapping(row, "manifest opportunity")
        for row in rows_raw
    ]
    if len(rows) != manifest.get("opportunity_decision_count"):
        raise CiboCapitalManagementError(
            "historical ceiling manifest decision count drift"
        )
    epochs = _group_epochs(rows)
    declared_epoch_count = manifest.get("decision_epoch_count")
    if (
        not isinstance(declared_epoch_count, int)
        or isinstance(declared_epoch_count, bool)
        or declared_epoch_count != len(epochs)
    ):
        raise CiboCapitalManagementError(
            "historical ceiling manifest epoch count drift"
        )

    identity = CiboAccountCapitalIdentity(
        provider_key="cibo-historical-ceiling-research",
        account_ref="cibo-ceiling-usd60-single-account",
        environment=MarketRuntimeEnvironment.DEMO,
    )
    mission_policy = derive_cibo_capital_mission(identity)
    risk_engine = AccountWideRiskEngine()
    capital = initialize_historical_research_capital()
    open_exposures: dict[str, CiboCeilingOpenExposure] = {}
    pending: list[_PendingHistoricalSettlement] = []
    decisions: list[CiboSovereignCeilingDecisionReceipt] = []
    settlements: list[CiboSovereignCeilingSettlementReceipt] = []
    external_ai_calls = 0
    regime_reconstructions = 0

    def settle_due(up_to: datetime | None) -> None:
        nonlocal capital, pending
        due = tuple(
            sorted(
                (
                    item
                    for item in pending
                    if up_to is None or item.exit_at <= up_to
                ),
                key=lambda item: (
                    item.exit_at,
                    item.decision.signal_fingerprint,
                ),
            )
        )
        if not due:
            return
        due_ids = {id(item) for item in due}
        pending = [item for item in pending if id(item) not in due_ids]
        for item in due:
            settlement = manifest_row_to_sovereign_settlement(
                row=item.row,
                decision=item.decision,
            )
            capital = settle_historical_deployment(
                capital,
                settlement=settlement,
            )
            settlements.append(settlement.receipt)
            open_exposures.pop(
                settlement.signal_fingerprint,
                None,
            )

    for epoch_index, epoch_rows in enumerate(epochs, start=1):
        decision_at = _dt(
            epoch_rows[0]["market_decision_at"],
            "market_decision_at",
        )
        settle_due(decision_at)
        if capital.realized_capital_usd <= 0:
            raise CiboCapitalManagementError(
                "historical ceiling account exhausted before population end"
            )

        evidence = tuple(
            manifest_row_to_ceiling_opportunity_evidence(row)
            for row in epoch_rows
        )
        regime = _causal_regime(
            rows=epoch_rows,
            capital=capital,
            provider_assumption=provider_assumption,
        )
        regime_reconstructions += 1
        epoch_id = str(epoch_rows[0]["decision_epoch_id"])
        prepared = run_predecision_historical_sovereign_ceiling_epoch(
            decision_epoch_id=epoch_id,
            decision_at=decision_at,
            expires_at=decision_at + timedelta(minutes=1),
            account_identity=identity,
            historical_capital=capital,
            open_exposures=tuple(
                sorted(
                    open_exposures.values(),
                    key=lambda item: item.signal_fingerprint,
                )
            ),
            opportunities=evidence,
            regime_state=regime,
            evidence_ref=CiboEvidenceRef(
                "cibo:historical-ceiling:" + epoch_id
            ),
            mission_policy=mission_policy,
            risk_engine=risk_engine,
            provider_assumption=provider_assumption,
            survival_capital_usd=_INITIAL_CAPITAL_USD,
            protected_capital_usd=Decimal(0),
        )
        execution = prepared.execution
        decisions.extend(execution.decision_receipts)
        external_ai_calls += sum(
            item.external_ai_call_count
            for item in execution.decision_receipts
        )

        authorization_by_signal = dict(
            zip(
                execution.risk_submission_order,
                execution.risk_authorizations,
                strict=True,
            )
        )
        row_by_signal = {
            str(row["signal_fingerprint"]): row for row in epoch_rows
        }
        evidence_by_signal = {
            item.opportunity.signal_fingerprint: item for item in evidence
        }
        receipt_by_signal = {
            item.signal_fingerprint: item
            for item in execution.decision_receipts
        }

        # The complete simultaneous epoch has already been decided.  Only now
        # may the simulator inspect postdecision settlement scheduling.
        for signal in execution.risk_submission_order:
            authorization = authorization_by_signal[signal]
            if authorization.decision not in {
                RiskDecision.ALLOW,
                RiskDecision.REDUCE,
            }:
                continue
            item = evidence_by_signal[signal]
            provider_cost = (
                item.provider_cost_per_volume_usd
                * authorization.authorized_volume
            )
            capital = reserve_historical_authorization(
                capital,
                authorization=authorization,
                provider_cost_usd=provider_cost,
            )
            # Historical replay treats an authorization as immediately opened.
            # Move risk ownership from Risk's in-flight reservation into the
            # chronological account snapshot so later epochs cannot double count.
            risk_engine.record_full_fill(authorization.authorization_id)
            risk_engine.reconcile_fill(authorization.authorization_id)

            opportunity = item.opportunity
            exposure = CiboCeilingOpenExposure(
                signal_fingerprint=signal,
                trader_id=opportunity.trader_id,
                qore_symbol=opportunity.qore_symbol,
                side=opportunity.side,
                entry_at=decision_at,
                volume=authorization.authorized_volume,
                stop_risk_usd=authorization.monetary_stop_loss,
                margin_usd=authorization.margin_reserved,
                provider_cost_usd=provider_cost,
                entry_price=opportunity.intended_entry,
                structural_stop=opportunity.stop_loss,
                technical_target=opportunity.take_profit,
                entry_expected_net_value_usd=item.expected_net_value_usd,
                entry_expected_capital_minutes=(
                    item.expected_capital_minutes
                ),
                expectation_evidence_sha256=(
                    item.expectation_evidence_sha256
                ),
            )
            open_exposures[signal] = exposure

            row = row_by_signal[signal]
            outcome = _mapping(
                row.get("settlement_outcome_research_only"),
                "settlement_outcome_research_only",
            )
            if (
                outcome.get("not_available_to_predecision") is not True
                or outcome.get("used_for_decision") is not False
            ):
                raise CiboCapitalManagementError(
                    "historical ceiling settlement governance flags invalid"
                )
            exit_at = _dt(outcome.get("exit_at"), "settlement exit_at")
            if exit_at < decision_at:
                raise CiboCapitalManagementError(
                    "historical ceiling settlement predates decision"
                )
            pending.append(
                _PendingHistoricalSettlement(
                    exit_at=exit_at,
                    row=row,
                    decision=receipt_by_signal[signal],
                )
            )

        if progress_hook is not None:
            progress_hook(
                {
                    "epoch_index": epoch_index,
                    "decision_epoch_count": len(epochs),
                    "decision_count": len(decisions),
                    "settled_count": len(settlements),
                    "open_count": len(open_exposures),
                    "realized_capital_usd": format(
                        capital.realized_capital_usd,
                        "f",
                    ),
                    "peak_realized_capital_usd": format(
                        capital.peak_realized_capital_usd,
                        "f",
                    ),
                }
            )

    settle_due(None)
    return CiboHistoricalCeilingReplayResult(
        source_manifest_sha256=source_manifest_sha256,
        decision_epoch_count=len(epochs),
        decision_receipts=tuple(decisions),
        settlement_receipts=tuple(settlements),
        final_capital=capital,
        final_open_exposures=tuple(
            sorted(
                open_exposures.values(),
                key=lambda item: item.signal_fingerprint,
            )
        ),
        regime_reconstruction_count=regime_reconstructions,
        provider_assumption=provider_assumption,
        external_ai_call_count=external_ai_calls,
        outcome_used_for_predecision=False,
        account_reset_count=0,
        economic_era_reset_count=0,
        broker_mutation=False,
        certification_claimed=False,
    )
